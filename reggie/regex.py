"""A small regular-expression engine: parser -> bytecode -> Pike VM.

The interesting property is *how* it matches. Most backtracking engines (including
Python's `re`) can blow up to exponential time on adversarial patterns like
`(a*)*b` against a long string of `a`s. Reggie compiles the pattern to a tiny
bytecode program and runs it on a Thompson/Pike virtual machine that advances a
*set* of threads through the text in lockstep — one pass, left to right. That
makes matching linear in the length of the text no matter how pathological the
pattern, with no catastrophic backtracking, ever.

Capturing groups still work: each VM thread carries its own array of saved
positions, and when two threads collide on the same instruction the
higher-priority one wins, which reproduces ordinary leftmost-greedy semantics.

Supported syntax
    literals, `.` (any char except newline)
    `*  +  ?`  and their lazy forms `*?  +?  ??`
    `{m}  {m,}  {m,n}` bounded repetition (greedy or lazy)
    `|` alternation,  `( )` capturing,  `(?: )` non-capturing groups
    `[abc]  [a-z]  [^...]` character classes
    `\d \D \w \W \s \S` shorthands (also valid inside classes)
    escapes `\n \t \r` and any escaped metacharacter
    anchors `^` (start of string) and `$` (end of string)

Only the standard library is used. See README.md for the full story.
"""

from __future__ import annotations

from dataclasses import dataclass


class RegexError(Exception):
    """Raised for any error compiling a pattern. The message is safe to show to
    a user and, where useful, points at the offending position."""


# ==========================================================================
# AST
# ==========================================================================

@dataclass
class Empty:
    """Matches the empty string (e.g. the right side of `a|`)."""

@dataclass
class Char:
    ch: str

@dataclass
class AnyChar:
    """`.` — any character except a newline."""

@dataclass
class CharClass:
    negated: bool
    # Each member is one of: ("lit", ch), ("range", lo, hi), ("shorthand", code)
    members: list

@dataclass
class Anchor:
    where: str  # "start" or "end"

@dataclass
class Concat:
    parts: list

@dataclass
class Alt:
    branches: list

@dataclass
class Repeat:
    node: object
    min: int
    max: int | None   # None == unbounded
    greedy: bool

@dataclass
class Group:
    node: object
    index: int | None   # capture slot, or None for (?:...)


# ==========================================================================
# Parser  (recursive descent; precedence: alternation < concat < repetition)
# ==========================================================================

_SHORTHANDS = set("dDwWsS")


class _Parser:
    def __init__(self, pattern: str):
        self.src = pattern
        self.i = 0
        self.n = len(pattern)
        self.ngroups = 0   # number of capturing groups seen

    # -- low-level cursor helpers ------------------------------------------
    def peek(self) -> str | None:
        return self.src[self.i] if self.i < self.n else None

    def next(self) -> str:
        c = self.src[self.i]
        self.i += 1
        return c

    def eat(self, c: str) -> None:
        if self.peek() != c:
            raise RegexError(f"expected {c!r} at position {self.i}")
        self.i += 1

    # -- grammar -----------------------------------------------------------
    def parse(self) -> object:
        node = self.parse_alt()
        if self.i != self.n:
            # The only way to get here is an unbalanced ')'.
            raise RegexError(f"unexpected {self.src[self.i]!r} at position {self.i}")
        return node

    def parse_alt(self) -> object:
        branches = [self.parse_concat()]
        while self.peek() == "|":
            self.next()
            branches.append(self.parse_concat())
        return branches[0] if len(branches) == 1 else Alt(branches)

    def parse_concat(self) -> object:
        parts = []
        while True:
            c = self.peek()
            if c is None or c in "|)":
                break
            parts.append(self.parse_repeat())
        if not parts:
            return Empty()
        return parts[0] if len(parts) == 1 else Concat(parts)

    def parse_repeat(self) -> object:
        atom = self.parse_atom()
        while True:
            c = self.peek()
            if c == "*":
                self.next()
                atom = Repeat(atom, 0, None, self._greedy())
            elif c == "+":
                self.next()
                atom = Repeat(atom, 1, None, self._greedy())
            elif c == "?":
                self.next()
                atom = Repeat(atom, 0, 1, self._greedy())
            elif c == "{":
                rep = self._parse_brace(atom)
                if rep is None:
                    break          # a literal '{', already handled
                atom = rep
            else:
                break
        return atom

    def _greedy(self) -> bool:
        """A trailing `?` after a quantifier makes it lazy."""
        if self.peek() == "?":
            self.next()
            return False
        return True

    def _parse_brace(self, atom):
        """Parse `{m}`, `{m,}`, `{m,n}`. If what follows `{` is not a valid
        counted-repetition spec, treat the brace as an ordinary literal so that
        a pattern like `a{b}` still works."""
        save = self.i
        self.next()  # consume '{'
        lo = self._read_int()
        hi: int | None
        if self.peek() == "}":
            if lo is None:
                self.i = save
                return None
            hi = lo
        elif self.peek() == ",":
            self.next()
            hi = self._read_int()  # may be None -> unbounded
        else:
            self.i = save
            return None
        if self.peek() != "}" or lo is None:
            self.i = save
            return None
        self.next()  # consume '}'
        if hi is not None and hi < lo:
            raise RegexError(f"repetition range out of order: {{{lo},{hi}}}")
        return Repeat(atom, lo, hi, self._greedy())

    def _read_int(self) -> int | None:
        start = self.i
        while self.peek() is not None and self.peek().isdigit():
            self.next()
        if self.i == start:
            return None
        return int(self.src[start:self.i])

    def parse_atom(self) -> object:
        c = self.peek()
        if c is None:
            raise RegexError("unexpected end of pattern")
        if c in "*+?":
            raise RegexError(f"nothing to repeat at position {self.i}")
        if c == "(":
            return self._parse_group()
        if c == "[":
            return self._parse_class()
        if c == ".":
            self.next()
            return AnyChar()
        if c == "^":
            self.next()
            return Anchor("start")
        if c == "$":
            self.next()
            return Anchor("end")
        if c == "\\":
            return self._parse_escape()
        if c == ")":
            raise RegexError(f"unbalanced ')' at position {self.i}")
        self.next()
        return Char(c)

    def _parse_group(self):
        self.eat("(")
        capturing = True
        if self.peek() == "?":
            # Only non-capturing groups (?:...) are supported.
            self.next()
            if self.peek() != ":":
                raise RegexError(
                    f"unsupported group syntax '(?{self.peek() or ''}' "
                    f"at position {self.i - 1}"
                )
            self.next()
            capturing = False
        index = None
        if capturing:
            self.ngroups += 1
            index = self.ngroups
        inner = self.parse_alt()
        self.eat(")")
        return Group(inner, index)

    def _parse_escape(self):
        self.eat("\\")
        c = self.peek()
        if c is None:
            raise RegexError("trailing backslash")
        self.next()
        if c in _SHORTHANDS:
            return CharClass(False, [("shorthand", c)])
        return Char(_escape_char(c))

    def _parse_class(self):
        self.eat("[")
        negated = False
        if self.peek() == "^":
            self.next()
            negated = True
        members: list = []
        if self.peek() == "]":   # a leading ']' is a literal
            self.next()
            members.append(("lit", "]"))
        while True:
            c = self.peek()
            if c is None:
                raise RegexError("unterminated character class")
            if c == "]":
                self.next()
                break
            lo = self._class_member()
            # A range like a-z: only when '-' is followed by a real member.
            if (isinstance(lo, str) and self.peek() == "-"
                    and self.i + 1 < self.n and self.src[self.i + 1] != "]"):
                self.next()  # consume '-'
                hi = self._class_member()
                if not isinstance(hi, str):
                    raise RegexError("bad character range (shorthand in range)")
                if ord(hi) < ord(lo):
                    raise RegexError(f"character range out of order: {lo}-{hi}")
                members.append(("range", lo, hi))
            elif isinstance(lo, str):
                members.append(("lit", lo))
            else:
                members.append(lo)  # a ("shorthand", code) tuple
        if not members:
            raise RegexError("empty character class")
        return CharClass(negated, members)

    def _class_member(self):
        """Return a single class member: a literal character (str) or a
        ('shorthand', code) tuple."""
        c = self.next()
        if c == "\\":
            e = self.peek()
            if e is None:
                raise RegexError("trailing backslash in character class")
            self.next()
            if e in _SHORTHANDS:
                return ("shorthand", e)
            return _escape_char(e)
        return c


def _escape_char(c: str) -> str:
    return {"n": "\n", "t": "\t", "r": "\r", "f": "\f", "v": "\v", "0": "\0"}.get(c, c)


# ==========================================================================
# Bytecode
# ==========================================================================
# Each instruction is a small dataclass. A compiled program is a flat list of
# them; control flow is by absolute index (`x`, `y` fields).

@dataclass
class IChar:
    ch: str
@dataclass
class IAny:
    pass
@dataclass
class IClass:
    negated: bool
    members: list
@dataclass
class IMatch:
    pass
@dataclass
class IJmp:
    x: int = 0
@dataclass
class ISplit:
    x: int = 0    # preferred (higher priority) branch
    y: int = 0
@dataclass
class ISave:
    slot: int
@dataclass
class IAssert:
    where: str    # "start" or "end"


# The largest expansion we'll allow for bounded repetition, to keep a pattern
# like `a{1,100000}{1,100000}` from generating an enormous program.
_MAX_REPEAT_EXPANSION = 100_000


class _Compiler:
    def __init__(self):
        self.prog: list = []

    def emit(self, inst) -> int:
        self.prog.append(inst)
        return len(self.prog) - 1

    def compile(self, ast) -> list:
        # Slot 0/1 are the whole-match span; group k uses slots 2k / 2k+1.
        self.emit(ISave(0))
        self._gen(ast)
        self.emit(ISave(1))
        self.emit(IMatch())
        return self.prog

    def _gen(self, node) -> None:
        if isinstance(node, Empty):
            return
        if isinstance(node, Char):
            self.emit(IChar(node.ch))
        elif isinstance(node, AnyChar):
            self.emit(IAny())
        elif isinstance(node, CharClass):
            self.emit(IClass(node.negated, node.members))
        elif isinstance(node, Anchor):
            self.emit(IAssert(node.where))
        elif isinstance(node, Concat):
            for part in node.parts:
                self._gen(part)
        elif isinstance(node, Alt):
            self._gen_alt(node.branches)
        elif isinstance(node, Group):
            self._gen_group(node)
        elif isinstance(node, Repeat):
            self._gen_repeat(node)
        else:  # pragma: no cover - parser never produces anything else
            raise RegexError("internal: unknown AST node")

    def _gen_group(self, node: Group) -> None:
        if node.index is None:
            self._gen(node.node)
            return
        self.emit(ISave(2 * node.index))
        self._gen(node.node)
        self.emit(ISave(2 * node.index + 1))

    def _gen_alt(self, branches: list) -> None:
        # split L1, L2 ; L1: <b0> jmp END ; L2: split ... ; END:
        jmp_ends: list[int] = []
        for k, branch in enumerate(branches):
            last = k == len(branches) - 1
            split = None
            if not last:
                split = self.emit(ISplit())
            self._gen(branch)
            if not last:
                jmp_ends.append(self.emit(IJmp()))
                self.prog[split].x = split + 1
                self.prog[split].y = len(self.prog)
        end = len(self.prog)
        for j in jmp_ends:
            self.prog[j].x = end

    def _gen_repeat(self, node: Repeat) -> None:
        lo, hi = node.min, node.max
        if hi is not None and (hi > _MAX_REPEAT_EXPANSION or lo > _MAX_REPEAT_EXPANSION):
            raise RegexError("repetition count too large")
        # `lo` mandatory copies up front.
        for _ in range(lo):
            self._gen(node.node)
        if hi is None:
            # Unbounded tail: `node*`. (With lo>0 the mandatory copies above
            # already enforce the minimum, so a plain star is exactly right.)
            self._gen_star(node.node, node.greedy)
        else:
            # (hi - lo) optional copies, each guarded by its own split so the
            # whole tail can be skipped.
            optional = hi - lo
            splits: list[int] = []
            for _ in range(optional):
                splits.append(self.emit(ISplit()))
                self._gen(node.node)
            end = len(self.prog)
            for s in splits:
                if node.greedy:
                    self.prog[s].x = s + 1
                    self.prog[s].y = end
                else:
                    self.prog[s].x = end
                    self.prog[s].y = s + 1

    def _gen_star(self, body, greedy: bool) -> None:
        # L1: split L2, L3 ; L2: <body> jmp L1 ; L3:
        l1 = self.emit(ISplit())
        self._gen(body)
        self.emit(IJmp(l1))
        l3 = len(self.prog)
        if greedy:
            self.prog[l1].x = l1 + 1
            self.prog[l1].y = l3
        else:
            self.prog[l1].x = l3
            self.prog[l1].y = l1 + 1


# ==========================================================================
# Character-class membership
# ==========================================================================

def _shorthand_matches(code: str, ch: str) -> bool:
    if code == "d":
        return ch.isdigit()
    if code == "D":
        return not ch.isdigit()
    if code == "w":
        return ch.isalnum() or ch == "_"
    if code == "W":
        return not (ch.isalnum() or ch == "_")
    if code == "s":
        return ch.isspace()
    if code == "S":
        return not ch.isspace()
    raise RegexError(f"internal: bad shorthand {code!r}")  # pragma: no cover


def _class_matches(negated: bool, members: list, ch: str) -> bool:
    hit = False
    for m in members:
        kind = m[0]
        if kind == "lit":
            if ch == m[1]:
                hit = True
                break
        elif kind == "range":
            if m[1] <= ch <= m[2]:
                hit = True
                break
        else:  # shorthand
            if _shorthand_matches(m[1], ch):
                hit = True
                break
    return (not hit) if negated else hit


# ==========================================================================
# Pike VM  (parallel threads, leftmost-greedy, linear time in len(text))
# ==========================================================================

@dataclass
class _Thread:
    pc: int
    saved: list


class _ThreadList:
    """An ordered, de-duplicated set of threads. Order encodes priority, so the
    first thread to reach IMatch in a step is the leftmost-greedy winner."""

    def __init__(self, size: int):
        self.threads: list[_Thread] = []
        self._seen = [False] * size

    def add(self, prog, pc: int, saved: list, pos: int, text: str) -> None:
        """Add the thread at `pc`, following all zero-width instructions (the
        epsilon closure) so the list only ever holds threads parked on a
        character-consuming instruction or on IMatch."""
        stack = [(pc, saved)]
        while stack:
            pc, saved = stack.pop()
            if self._seen[pc]:
                continue
            self._seen[pc] = True
            inst = prog[pc]
            if isinstance(inst, IJmp):
                stack.append((inst.x, saved))
            elif isinstance(inst, ISplit):
                # Preserve priority: x must be explored before y. Because we use
                # a stack, push y first then x so x is popped (and thus seen)
                # first.
                stack.append((inst.y, saved))
                stack.append((inst.x, saved))
            elif isinstance(inst, ISave):
                nsaved = saved.copy()
                nsaved[inst.slot] = pos
                stack.append((pc + 1, nsaved))
            elif isinstance(inst, IAssert):
                ok = (inst.where == "start" and pos == 0) or (
                    inst.where == "end" and pos == len(text))
                if ok:
                    stack.append((pc + 1, saved))
            else:
                # A character-consuming instruction or IMatch: park it.
                self.threads.append(_Thread(pc, saved))


def _run(prog: list, text: str, start: int) -> list | None:
    """Run the program over `text` beginning at index `start`. Returns the
    saved-positions array of the matching thread, or None."""
    nslots = max((i.slot for i in prog if isinstance(i, ISave)), default=1) + 1
    clist = _ThreadList(len(prog))
    init = [None] * nslots
    clist.add(prog, 0, init, start, text)

    matched: list | None = None
    pos = start
    while True:
        if not clist.threads:
            break  # every thread died; no match is possible from here
        nlist = _ThreadList(len(prog))
        ch = text[pos] if pos < len(text) else None
        for th in clist.threads:
            inst = prog[th.pc]
            if isinstance(inst, IMatch):
                matched = th.saved
                # Lower-priority threads can't beat this one, so drop them.
                break
            if ch is None:
                continue  # nothing left to consume
            if isinstance(inst, IChar):
                if ch == inst.ch:
                    nlist.add(prog, th.pc + 1, th.saved, pos + 1, text)
            elif isinstance(inst, IAny):
                if ch != "\n":
                    nlist.add(prog, th.pc + 1, th.saved, pos + 1, text)
            elif isinstance(inst, IClass):
                if _class_matches(inst.negated, inst.members, ch):
                    nlist.add(prog, th.pc + 1, th.saved, pos + 1, text)
        clist = nlist
        if pos >= len(text):
            break
        pos += 1
    return matched


# ==========================================================================
# Public API
# ==========================================================================

class Match:
    """The result of a successful match. Group 0 is the whole match; groups
    1..n correspond to capturing parentheses, left to right by opening paren."""

    def __init__(self, text: str, saved: list, ngroups: int):
        self._text = text
        self._saved = saved
        self._ngroups = ngroups

    def _span(self, group: int) -> tuple[int, int] | None:
        if group < 0 or group > self._ngroups:
            raise IndexError(f"no such group: {group}")
        a = self._saved[2 * group]
        b = self._saved[2 * group + 1]
        if a is None or b is None:
            return None
        return (a, b)

    def group(self, group: int = 0) -> str | None:
        """The substring matched by `group`, or None if the group did not
        participate in the match."""
        span = self._span(group)
        if span is None:
            return None
        return self._text[span[0]:span[1]]

    def span(self, group: int = 0) -> tuple[int, int]:
        """The (start, end) indices of `group`. (-1, -1) if it didn't match."""
        span = self._span(group)
        return span if span is not None else (-1, -1)

    def start(self, group: int = 0) -> int:
        return self.span(group)[0]

    def end(self, group: int = 0) -> int:
        return self.span(group)[1]

    def groups(self) -> tuple:
        """All capturing groups (1..n) as a tuple; None for non-participants."""
        return tuple(self.group(i) for i in range(1, self._ngroups + 1))

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        return f"<Match span={self.span()} match={self.group()!r}>"


class Regex:
    """A compiled pattern. Reuse it across many searches — compilation happens
    once, here."""

    def __init__(self, pattern: str):
        self.pattern = pattern
        parser = _Parser(pattern)
        ast = parser.parse()
        self.ngroups = parser.ngroups
        self.prog = _Compiler().compile(ast)

    def match(self, text: str) -> Match | None:
        """Match anchored at the start of `text` (it need not reach the end)."""
        saved = _run(self.prog, text, 0)
        return Match(text, saved, self.ngroups) if saved is not None else None

    def fullmatch(self, text: str) -> Match | None:
        """Match only if the pattern consumes the entire string."""
        m = self.match(text)
        if m is not None and m.end() == len(text) and m.start() == 0:
            return m
        return None

    def search(self, text: str) -> Match | None:
        """Find the leftmost match anywhere in `text`."""
        for start in range(len(text) + 1):
            saved = _run(self.prog, text, start)
            if saved is not None:
                return Match(text, saved, self.ngroups)
        return None

    def finditer(self, text: str):
        """Yield non-overlapping matches left to right. A zero-width match still
        advances by one position so the loop always terminates."""
        pos = 0
        while pos <= len(text):
            saved = _run(self.prog, text, pos)
            if saved is None:
                pos += 1
                continue
            m = Match(text, saved, self.ngroups)
            yield m
            end = m.end()
            pos = end + 1 if end == m.start() else end

    def findall(self, text: str) -> list:
        """All matches as strings (group 0), non-overlapping, left to right."""
        return [m.group(0) for m in self.finditer(text)]


def compile(pattern: str) -> Regex:
    """Compile `pattern` into a reusable Regex."""
    return Regex(pattern)


def search(pattern: str, text: str) -> Match | None:
    return Regex(pattern).search(text)


def match(pattern: str, text: str) -> Match | None:
    return Regex(pattern).match(text)


def fullmatch(pattern: str, text: str) -> Match | None:
    return Regex(pattern).fullmatch(text)


def findall(pattern: str, text: str) -> list:
    return Regex(pattern).findall(text)
