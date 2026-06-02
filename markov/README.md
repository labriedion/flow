# markov

A tiny, dependency-free **Markov-chain text generator**. Train it on any text
and it will babble in the same style — coherent locally, surprising globally.
Works on **words** (prose-like output) or **characters** (pronounceable
invented words). Pure Python standard library, with a real test suite.

### Example output

Trained on the included `corpus.txt` (the opening of *Pride and Prejudice*):

```
$ python -m markov.cli corpus.txt --order 2 --length 50 --seed 11

It is a truth universally acknowledged, that a single man in possession of a
wife. However little known the feelings or views of such a man may be on his
first entering a neighbourhood, this truth is so well fixed in the minds of
the surrounding families, that he is
```

Notice how order 2 recombines the source into new-but-plausible sentences.
More samples (including character-level "invented words") are in
[`examples/sample_output.txt`](examples/sample_output.txt).

```
markov/
  markov.py        # the chain: training, sampling, two tokenization modes
  cli.py           # argparse command-line interface
  corpus.txt       # a sample corpus (opening of Pride and Prejudice)
  test_markov.py   # pytest suite (soundness, determinism, edge cases)
```

## Run it

```bash
python -m markov.cli markov/corpus.txt --order 2 --length 60
python -m markov.cli markov/corpus.txt --char --order 4 --length 200
cat your_text.txt | python -m markov.cli --order 3 --seed 7   # from stdin
```

| Flag | Default | Meaning |
| --- | --- | --- |
| `files...` | stdin | one or more training text files |
| `-o/--order` | 2 | context length — how many previous tokens predict the next |
| `-n/--length` | 100 | number of tokens to generate |
| `--char` | off | operate on characters instead of words |
| `--seed` | random | fix for reproducible output |

**Order** is the key dial: order 1 is near-random, order 2–3 reads
surprisingly fluent, and high orders quote the source nearly verbatim.

## Use it as a library

```python
from markov import MarkovChain

chain = MarkovChain(order=2, mode="word")
chain.train(open("corpus.txt").read())
print(chain.generate(length=80, seed=42))
```

## Test it

```bash
python -m pytest markov/ -q
```

The suite's core guarantee is **soundness**: every `(context → next token)`
step the generator emits was a transition actually seen in training — verified
on cyclic corpora where it holds throughout. It also checks seeded determinism,
the weighted distribution (within a tolerance band), both tokenization modes,
and graceful handling of corpora too small for the requested order.

### One caveat: restart seams

To always reach the requested length, generation **restarts** from a random
start state whenever it hits a dead end (a context with no learned successor).
That restart splices in a fresh state, creating a single "seam" transition the
model never learned. So soundness holds for every step *except across restart
seams* — a deliberate trade-off favouring full-length output. This behavior is
documented in `generate()` and covered by dedicated tests
(`test_restart_reaches_full_length_on_acyclic_corpus`,
`test_restart_can_introduce_an_unlearned_seam`).
