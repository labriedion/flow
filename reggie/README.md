# reggie

A small **regular-expression engine**, built from scratch — pattern → AST →
bytecode → a virtual machine that runs it. Pure Python standard library, with a
real test suite that checks it against Python's own `re` on thousands of random
inputs.

The point isn't to replace `re`. It's to show *how* a regex engine can work, and
in particular how to build one that **never catastrophically backtracks**.

### The thing it does that `re` can't

A pattern like `(a+)+b` is a classic trap. Run it against a long string of `a`s
with no `b` and a backtracking engine — Python's `re`, PCRE, JavaScript — has to
try every way of splitting the `a`s among the nested `+`s, which is exponential.
The match can take longer than the age of the universe.

```
» python -m reggie.cli '(a+)+b' "$(python -c 'print("a"*40)')"
(no match — returned in a couple of milliseconds)
```

reggie returns instantly, because it doesn't backtrack at all.

## How it works

Three stages, mirroring a tiny compiler:

```
pattern  ──parse──▶  AST  ──compile──▶  bytecode  ──run──▶  Match
```

1. **Parse** (`_Parser`) — recursive descent into an AST. Precedence is the
   usual regex one: alternation binds loosest, then concatenation, then the
   postfix quantifiers.
2. **Compile** (`_Compiler`) — flatten the AST into a flat list of tiny
   instructions: `char`, `any`, `class`, `split`, `jmp`, `save`, `assert`,
   `match`. Alternation and `*`/`+`/`?` become `split` instructions (a fork in
   control flow); capturing groups become `save` instructions that record a
   position.
3. **Run** (`_run`) — a [Pike VM](https://swtch.com/~rsc/regexp/regexp2.html).
   Instead of backtracking, it walks the text once, left to right, advancing a
   *set* of threads in lockstep. At each character every live thread either
   survives or dies. Because the thread set is de-duplicated by program counter,
   it can never hold more threads than the program has instructions — so the
   whole match is **O(len(text) × len(program))**, guaranteed, with no blow-up.

Thread *order* encodes priority, which is how the linear-time VM still reproduces
ordinary leftmost-greedy semantics — including capture groups, which ride along
as a per-thread array of saved positions.

```
reggie/
  regex.py        # parser, compiler, Pike VM, and the public API
  cli.py          # grep-style command-line tool
  test_regex.py   # unit tests + a differential fuzzer against `re`
```

## Run it

```bash
# Highlight every match in some text (grep-style):
python -m reggie.cli '\d+' "order 66 shipped 1024 units"

# Print only the matches:
python -m reggie.cli -o '\w+@\w+' "mail bob@server and ann@host"

# Show capture groups:
python -m reggie.cli -g '(\w+)=(\d+)' "x=10 y=255"

# Read text from stdin, like grep:
printf 'the cat sat\non the mat\n' | python -m reggie.cli 'at'
```

It exits `0` if anything matched and `1` if not, so it composes in shell
pipelines. Like `grep`, the CLI searches each input line independently, so `^`
and `$` anchor to the start and end of a *line* there. (In the library, where
there are no lines, they anchor to the whole string — see below.)

## Use it as a library

The API deliberately echoes a small slice of `re`:

```python
import reggie

reggie.search(r"(\w+)@(\w+)", "to bob@server").groups()   # ('bob', 'server')
reggie.findall(r"\d+", "a1 b22 c333")                     # ['1', '22', '333']
reggie.fullmatch(r"(\d{1,3}\.){3}\d{1,3}", "192.168.0.1")  # a Match

rx = reggie.compile(r"a.*?b")        # compile once, reuse
rx.search("aXbYb").span()            # (0, 3)  — lazy quantifier
```

`Match` gives you `.group(n)`, `.span(n)`, `.start(n)`, `.end(n)`, and
`.groups()`. A full transcript is in [`examples/session.txt`](examples/session.txt).

## Supported syntax

| | |
| --- | --- |
| literals, `.` | any character except newline |
| `*` `+` `?` | greedy quantifiers; add `?` for the lazy forms `*?` `+?` `??` |
| `{m}` `{m,}` `{m,n}` | bounded repetition (greedy or lazy) |
| `\|` | alternation |
| `( )` `(?: )` | capturing and non-capturing groups |
| `[abc]` `[a-z]` `[^…]` | character classes, ranges, negation |
| `\d \D \w \W \s \S` | shorthands (also usable inside `[ ]`) |
| `\n \t \r`, `\.` `\*` … | escapes for whitespace and metacharacters |
| `^` `$` | anchors: start / end of the string |

`^` matches the start of the string and `$` the end — or, like `re`'s default
(non-multiline) behaviour, just before a single trailing newline. There's no
multiline mode. The `\d \w \s` shorthands use Python's own Unicode-aware
character tests, so `\d` matches any Unicode digit and `\w` any Unicode
letter/digit/underscore — not just ASCII.

## Test it

```bash
python -m pytest reggie/ -q
```

Alongside ordinary unit tests for every feature and a battery of bad patterns
that must raise a clean `RegexError`, the suite includes:

- a **differential fuzzer** that generates thousands of random patterns, compiles
  each with both reggie and `re`, and checks they agree on an anchored match at
  *every* offset of random input — the strongest evidence that the engine is
  actually correct, not just correct on the examples I thought of;
- a **performance guard** that matches `(a+)+b` against a wall of `a`s and asserts
  it finishes in well under a second, pinning down the no-catastrophic-
  backtracking promise.
