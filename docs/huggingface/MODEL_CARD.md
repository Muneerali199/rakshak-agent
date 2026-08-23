<!--
  This is the model card for https://huggingface.co/Muneerali199/rakshak-cwe-14b-sft-final
  Copy the contents below (including the YAML frontmatter) into the model's README.md on
  Hugging Face to replace the empty default template. Fill every TODO before submission.
-->
---
base_model: Qwen/Qwen2.5-Coder-14B-Instruct
library_name: peft
pipeline_tag: text-generation
license: apache-2.0   # TODO: confirm — must be compatible with the Qwen2.5-Coder-14B base license
tags:
  - code
  - security
  - vulnerability-detection
  - cwe
  - static-analysis
  - lora
  - peft
  - qwen2.5-coder
datasets:
  - Muneerali199/rakshak-cwe-v3-data
  - Muneerali199/rakshak-sft-dataset
  - Muneerali199/RakshakAI-v4-instruct
  - Muneerali199/RakshakAI-phase-b
language:
  - en
---

# RakshakAI — CWE Vulnerability Detection (14B)

`rakshak-cwe-14b-sft-final` is a **security-focused code model** that reviews source code, flags
vulnerabilities, and maps them to **CWE** (Common Weakness Enumeration) identifiers. It is the
**RakshakAI** secure-by-design component of the [RAKSHAK](https://github.com/Muneerali199/rakshak-agent)
platform (Smart India Hackathon 2026, problem SIH26189).

> RakshakAI reviews **code**. It is **not** used for criminal-network analysis, surveillance, or any
> decision about people. Within RAKSHAK it scans the platform's own codebase before deployment.

## Model details

- **Base model:** [`Qwen/Qwen2.5-Coder-14B-Instruct`](https://huggingface.co/Qwen/Qwen2.5-Coder-14B-Instruct) (~14B params)
- **Adapter type:** LoRA (PEFT) — supervised fine-tuning (SFT)
- **Task:** text-generation — security code review, vulnerability explanation, CWE classification
- **Language:** English (code + natural-language rationale)
- **Developed by:** Muneer Ali ([@Muneerali199](https://huggingface.co/Muneerali199))
- **License:** TODO (confirm; must respect the base model's license)

## Intended use

- Reviewing source code for security weaknesses and mapping findings to CWE IDs
- Explaining *why* a snippet is vulnerable and suggesting a secure rewrite
- Reviewing authentication / authorization logic and flagging risky dependency usage
- Assisting secure-by-design development for sensitive (e.g., government) infrastructure

### Out of scope / limitations

- **Supplementary, not authoritative.** Use alongside established static-analysis tools (Semgrep,
  SonarQube, Bandit) and human review — not as the sole security gate. A comparative benchmark
  (CWE detection rate, false-positive rate) is **pending**; do not cite accuracy numbers until then.
- May miss vulnerabilities or produce false positives; can hallucinate. Do not deploy code based on
  its output without human verification.
- Best on the languages/frameworks emphasized during fine-tuning. TODO: list them (e.g., Python /
  FastAPI). Performance on other stacks is unverified.

## Usage

```python
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

BASE = "Qwen/Qwen2.5-Coder-14B-Instruct"
ADAPTER = "Muneerali199/rakshak-cwe-14b-sft-final"

tokenizer = AutoTokenizer.from_pretrained(BASE)
model = AutoModelForCausalLM.from_pretrained(BASE, torch_dtype=torch.bfloat16, device_map="auto")
model = PeftModel.from_pretrained(model, ADAPTER)   # load the RakshakAI LoRA adapter

messages = [
    {"role": "system", "content": "You are RakshakAI, a security code reviewer. Identify vulnerabilities, cite the CWE ID, and suggest a fix."},
    {"role": "user", "content": "Review this code:\n\n@app.get('/user')\ndef get_user(id):\n    return db.execute(f\"SELECT * FROM users WHERE id = {id}\")"},
]
inputs = tokenizer.apply_chat_template(messages, add_generation_prompt=True, return_tensors="pt").to(model.device)
outputs = model.generate(inputs, max_new_tokens=512, temperature=0.2)
print(tokenizer.decode(outputs[0][inputs.shape[-1]:], skip_special_tokens=True))
# Expected: flags CWE-89 (SQL Injection), explains the f-string interpolation, suggests parameterized queries.
```

### Serving (vLLM)

```bash
vllm serve Qwen/Qwen2.5-Coder-14B-Instruct \
  --enable-lora \
  --lora-modules rakshak=Muneerali199/rakshak-cwe-14b-sft-final
```

## Training

- **Method:** LoRA supervised fine-tuning with PEFT (`peft` 0.18.x)
- **Data:** the RakshakAI dataset family (see `datasets` above) — CWE/vulnerability examples and
  instruction data. See [DATASETS.md](./DATASETS.md).
- **Hyperparameters:** TODO (LoRA rank/alpha/dropout, target modules, LR, epochs, batch size, seq len)
- **Compute:** TODO (hardware, hours)

## Evaluation

TODO — pending. Planned: CWE detection rate and false-positive rate on intentionally vulnerable
codebases, benchmarked against Semgrep / SonarQube / Bandit. Report precision, recall, and F1 per CWE.
**No evaluation numbers should be published until this is complete.**

## Citation

If you use RakshakAI, please cite the RAKSHAK-NET SIH 2026 proposal (SIH26189) and this repository:
https://github.com/Muneerali199/rakshak-agent
