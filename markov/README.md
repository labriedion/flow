# markov

A tiny, dependency-free **Markov-chain text generator**. Train it on any text
and it will babble in the same style — coherent locally, surprising globally.
Works on **words** (prose-like output) or **characters** (pronounceable
invented words). Pure Python standard library, with a real test suite.

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
step the generator emits was a transition actually seen in training. It also
checks seeded determinism, the weighted distribution, both tokenization modes,
and graceful handling of corpora too small for the requested order.
