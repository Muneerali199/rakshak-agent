# RakshakAI datasets

The dataset family behind the [RakshakAI code-security model](./MODEL_CARD.md)
(`Muneerali199/rakshak-cwe-14b-sft-final`). These are **code-security / CWE** supervised-fine-tuning
data — they train the model that reviews RAKSHAK's own code. They are **not** criminal-network data.

Owner: [`Muneerali199`](https://huggingface.co/Muneerali199/datasets)

| Dataset | Rows (approx.) | Inferred purpose |
| --- | --- | --- |
| `rakshak-sft-dataset` | ~259k | Consolidated SFT data (final training mixture) |
| `RakshakAI-phase-b` | ~400k | Phase-B training data (largest split) |
| `RakshakAI-v4-instruct` | ~163k | Instruction-tuning data (chat/instruct format) |
| `rakshak-cwe-v3-data` | ~80k | CWE-labeled vulnerability examples |
| `RakshakAI-v3-dataset` | preview | Earlier version of the training data |
| `RakshakAI-v2-Phase-B` | preview | Earlier Phase-B version |

> Row counts are read from the Hugging Face dataset listing and are approximate. Purposes are
> **inferred from the names** — confirm and correct each below.

---

## What each dataset card should contain

The dataset pages currently use the default template. For each dataset, paste a card like the one
below into its `README.md` on Hugging Face and fill the TODOs. Publishing filled cards is a major
credibility win for SIH judging and for reproducibility.

```markdown
---
license: apache-2.0            # TODO confirm
task_categories:
  - text-generation
language:
  - en
tags:
  - code
  - security
  - cwe
  - vulnerability-detection
size_categories:
  - 100K<n<1M                  # TODO pick the right bucket
---

# <dataset-name>

## Summary
TODO: one paragraph — what this dataset is and what it trains RakshakAI to do.

## Structure
- **Format:** TODO (e.g., chat messages / instruction-response / prompt-completion)
- **Fields:** TODO (e.g., `instruction`, `input` (code), `output` (review + CWE), `cwe_id`, `language`)
- **Rows:** TODO
- **Example:**
  ```json
  { "instruction": "...", "input": "<code>", "output": "CWE-89 (SQL Injection): ...", "cwe_id": "CWE-89" }
  ```

## Sources & construction
TODO: where the data came from (e.g., public CWE corpora, synthetic generation, transformed
open-source samples), and how labels were produced/verified.

## Intended use
Fine-tuning security code-review models (see `Muneerali199/rakshak-cwe-14b-sft-final`).

## Limitations & bias
TODO: language/framework coverage, label-noise notes, dedup vs. the model's eval set to avoid leakage.

## License
TODO — ensure it is compatible with any upstream sources.
```

---

## To verify before publishing

- [ ] Confirm the **purpose and schema** of each dataset (replace the inferred rows above).
- [ ] State **provenance** for each (synthetic vs. derived from public corpora) and its license.
- [ ] Check for **train/eval leakage** — the CWE benchmark set must not overlap with training rows.
- [ ] Confirm which are actively used by `rakshak-cwe-14b-sft-final` vs. superseded (v2/v3).
