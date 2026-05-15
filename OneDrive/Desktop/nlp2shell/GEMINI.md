# GEMINI.md — NLP2Shell Project Context

> This file is the single source of truth for the Gemini CLI agent working on this project.
> Read this fully before writing any code, suggesting any change, or answering any question.
> Update this file whenever the project structure, decisions, or conventions change.

---

## What This Project Is

**NLP2Shell** is a local desktop tool that accepts natural language (voice or text) and converts
it into executable shell/bash commands using a fine-tuned language model. It runs entirely on
the user's machine at inference time. No cloud calls during execution.

**Core user flow:**

```
Voice/Text Input → Whisper STT (if voice) → Fine-tuned Qwen2.5-0.5B → Bash Command → Confirm → Execute
```

**Example:**

```
User says : "move all PDFs from Downloads to Documents"
Tool runs : mv ~/Downloads/*.pdf ~/Documents/
```

---

## Developer Profile (Read This — It Affects How You Should Help)

- **Name:** Hassan
- **Level:** 4th semester BS Data Science student
- **Coding style:** Vibe coding — AI-assisted development, not writing everything from scratch
- **Primary agent:** Gemini CLI (this file)
- **Secondary tools:** GitHub Copilot, Antigravity (used occasionally in/out VS Code)
- **Hardware:** Core i5 6th gen, 8GB RAM, 256GB SSD (30-40GB free), Intel HD 520 (no CUDA)
- **Cloud GPU:** Kaggle free tier (T4, 30hrs/week) — used ONLY for training
- **OS:** Windows

### What This Means For You (Gemini):

- Do NOT suggest solutions that require a dedicated GPU locally
- Do NOT suggest paid APIs (OpenAI, Cohere, etc.) unless explicitly asked
- Always prefer CPU-friendly, quantized model approaches for local inference
- Keep dependencies minimal — storage is limited (30-40GB free)
- When writing notebooks, assume they will be pushed to Kaggle via CLI, not run locally
- Prefer `transformers` with 4-bit quantization or CPU-only loading for local model loading
- When in doubt, write simpler code — understanding > cleverness here

---

## Project Structure

```
nlp2shell/
│
├── GEMINI.md                        ← You are here
├── README.md                        ← Project overview + demo results
├── requirements.txt                 ← Pinned dependencies
├── requirements-dev.txt             ← Dev/test dependencies
├── config.yaml                      ← User-editable settings
├── setup.py                         ← For pip install -e .
│
├── data/
│   ├── raw/                         ← NL2Bash dataset + any downloads, untouched
│   ├── processed/                   ← Cleaned, formatted, split datasets
│   │   ├── train.jsonl
│   │   ├── val.jsonl
│   │   └── test.jsonl
│   └── augmented/                   ← Custom examples added manually
│       └── custom_pairs.jsonl
│
├── training/                        ← KAGGLE-BOUND code only
│   ├── kernel-metadata.json         ← Kaggle kernel config (GPU: true)
│   ├── finetune.ipynb               ← Main LoRA fine-tuning notebook
│   ├── evaluate.ipynb               ← Post-training evaluation notebook
│   └── export_model.ipynb           ← Quantize + export trained weights
│
├── models/                          ← Downloaded model weights (gitignored)
│   └── qwen_final_adapter/          ← Fine-tuned LoRA adapter weights (Qwen2.5-0.5B)
│
├── src/                             ← Core application modules
│   ├── __init__.py
│   ├── stt.py                       ← Whisper speech-to-text
│   ├── predictor.py                 ← Model loading + inference
│   ├── safety.py                    ← Command allowlist + danger detection
│   ├── executor.py                  ← Confirm + subprocess execution
│   └── pipeline.py                  ← Connects all modules
│
├── cli/
│   ├── __init__.py
│   └── main.py                      ← Entry point, Rich terminal UI
│
└── tests/
    ├── test_safety.py               ← Priority #1 — always keep passing
    ├── test_predictor.py
    └── test_pipeline.py
```

---

## Module Contracts (Interfaces Between Files)

These are fixed. Do NOT change function signatures without updating this file.

### `src/stt.py`

```python
def listen() -> str:
    """Record from mic until 2s silence. Return transcribed text string."""

def text_mode() -> str:
    """Read from stdin. Return text string. Used as fallback / --text flag."""
```

### `src/predictor.py`

```python
def load_model(model_path: str) -> None:
    """Load fine-tuned LoRA model from disk into memory. Call once at startup."""

def predict(natural_language: str) -> str:
    """Take NL string, return predicted bash command string."""
```

### `src/safety.py`

```python
def check(command: str) -> bool:
    """Return True if command is safe to show user, False if it should be blocked."""

def explain_block(command: str) -> str:
    """Return human-readable reason why a command was blocked."""
```

### `src/executor.py`

```python
def confirm_and_run(command: str) -> dict:
    """Show command to user, ask y/n, execute if yes. Return result dict:
    {"command": str, "executed": bool, "stdout": str, "stderr": str, "returncode": int}
    """
```

### `src/pipeline.py`

```python
def run(voice_mode: bool = True, dry_run: bool = False) -> None:
    """Main loop. voice_mode toggles STT vs text input. dry_run skips execution."""
```

---

## Technology Stack

### Local (Your Laptop)

| Purpose           | Library/Tool                         | Notes                   |
| ----------------- | ------------------------------------ | ----------------------- |
| Speech-to-text    | `openai-whisper` (tiny model)        | CPU inference, ~1-3s    |
| Model inference   | `transformers` + `peft`              | Load LoRA adapter       |
| Quantization      | `bitsandbytes`                       | 4-bit (if GPU available) |
| Fallback          | `torch` (float32)                    | CPU inference for Qwen  |
| Terminal UI       | `rich`                               | Panels, colors, prompts |
| Audio recording   | `pyaudio`                            | Mic input               |
| Command execution | `subprocess` (stdlib)                | No extra lib needed     |
| Config            | `pyyaml`                             | Load config.yaml        |
| Testing           | `pytest`                             | Run tests/ folder       |

### Kaggle (Training Only)

| Purpose      | Library/Tool              | Notes                   |
| ------------ | ------------------------- | ----------------------- |
| Base model   | `Qwen/Qwen2.5-0.5B-Instruct` | Alibaba, 0.5B params    |
| Fine-tuning  | `trl` (SFTTrainer)        | Handles training loop   |
| LoRA         | `peft`                    | Adapter training only   |
| Quantization | `bitsandbytes`            | 4-bit for T4 memory     |
| Dataset      | `nlp2shell-processed`     | ~26k NL→Bash pairs      |

### Dataset Format (Alpaca Instruction Format)

```json
{
  "instruction": "move all PDFs from Downloads to Documents",
  "input": "",
  "output": "mv ~/Downloads/*.pdf ~/Documents/"
}
```

---

## Inference Prompt Format (CRITICAL)

The model uses **Qwen ChatML format**. Always use `tokenizer.apply_chat_template()`.

**System prompt:**
```
Convert the natural language instruction to a bash command. Output only the command, nothing else.
```

**Structure:**
```
<|im_start|>system
Convert the natural language instruction to a bash command. Output only the command, nothing else.<|im_end|>
<|im_start|>user
{instruction}<|im_end|>
<|im_start|>assistant
```

---

## Safety Rules (Non-Negotiable — Never Relax These)

The safety module is the most critical part of this project. A mistake here can destroy files.

### Hardcoded Blocklist (always block, no exceptions):

```python
BLOCKED_PATTERNS = [
    "rm -rf",
    "rm -r /",
    ":(){ :|:& };:",    # fork bomb
    "dd if=",
    "mkfs",
    "curl | bash",
    "curl | sh",
    "wget | bash",
    "> /dev/sda",
    "chmod -R 777 /",
    "sudo rm",
    "shutdown",
    "reboot",
    "halt",
]
```

### Blocked Paths (never allow commands targeting these):

```python
BLOCKED_PATHS = ["/etc", "/sys", "/boot", "/dev", "/proc", "/usr/bin", "/usr/lib"]
```

### Confirm-Always Commands (show extra warning, still require y/n):

```python
CONFIRM_ALWAYS = ["sudo", "chmod", "chown", "kill", "pkill", "systemctl"]
```

### Safe Command Prefixes (MVP allowlist — only these run without extra warning):

```python
SAFE_PREFIXES = ["mv", "cp", "mkdir", "ls", "find", "echo", "cat", "open", "touch", "cd"]
```

**Rule for Gemini:** When writing or modifying `safety.py`, never remove items from
BLOCKED_PATTERNS or BLOCKED_PATHS. You may only add to them.

---

## Kaggle Workflow (How Training Notebooks Get Deployed)

The developer does NOT run training notebooks locally. This is the exact workflow:

```bash
# Step 1: Write/edit notebook in VS Code locally
# File: training/finetune.ipynb

# Step 2: Push to Kaggle
kaggle kernels push -p training/

# Step 3: Monitor run
kaggle kernels status <username>/nlp2shell-finetune

# Step 4: Download output (trained model weights)
kaggle kernels output <username>/nlp2shell-finetune -p models/
```

### Rules for Writing Kaggle Notebooks:

- Always install dependencies in the first cell with `!pip install ...`
- Load dataset from `/kaggle/input/` not from relative paths
- Save all outputs to `/kaggle/working/` — this is what gets downloaded
- Add a cell at the end that prints 5-10 example predictions vs ground truth
- Cells must be runnable top-to-bottom without any manual input
- Do NOT use `input()` or any interactive prompts inside notebooks

### `kernel-metadata.json` format:

```json
{
  "id": "hassannawaz1423/nlp2shell-finetune",
  "title": "NLP2Shell Fine-tune",
  "code_file": "finetune.ipynb",
  "language": "python",
  "kernel_type": "notebook",
  "is_private": true,
  "enable_gpu": true,
  "enable_internet": true
}
```

---

## config.yaml Structure

```yaml
model:
  path: "models/qwen_final_adapter"
  quantization: "4bit"
  max_new_tokens: 80

stt:
  model_size: "tiny" # tiny | base | small
  language: "en"
  silence_threshold: 2.0 # seconds of silence to stop recording

safety:
  mode: "allowlist" # allowlist | blocklist | strict
  dry_run: false # if true, never execute — only show commands

ui:
  theme: "dark"
  show_confidence: true # show model confidence score with command
```

---

## Git Conventions

```bash
# Branch per phase
git checkout -b phase/1-data-prep
git checkout -b phase/2-training
git checkout -b phase/3-inference
git checkout -b phase/4-cli
git checkout -b phase/5-eval

# Commit style
git commit -m "feat(stt): add silence detection to listen()"
git commit -m "fix(safety): block commands with /etc path"
git commit -m "data: clean NL2Bash and export to processed/"
git commit -m "train: add LoRA config to finetune notebook"
```

### `.gitignore` must include:

```
models/                  # too large, download from Kaggle
data/raw/                # re-downloadable
__pycache__/
*.pyc
.env
config.local.yaml        # user's personal overrides
```

### git origin is:

https://github.com/HassanNawaz14/NLP2Shell-Voice-Assistant.git

---

## Current Project Status

> **Update this section yourself as you complete phases.**

```
[x] Phase 1 — Data Preparation
[x] Phase 2 — Fine-tuning on Kaggle (SUCCESS)
[/] Phase 3 — Local Inference Pipeline (IN PROGRESS)
[/] Phase 4 — CLI Interface (IN PROGRESS)
[ ] Phase 5 — Evaluation + Polish

Current active phase : Phase 3 & 4
Last completed task  : Successful fine-tuning of Qwen2.5-0.5B on Kaggle. Adapter downloaded.
Next task            : Implement src/safety.py and src/predictor.py
Blockers             : None

---

## Phase 2: Fine-tuning (Completed)

**Status:** Successfully trained Qwen2.5-0.5B-Instruct using LoRA on Kaggle.
- **Results:** 1 epoch completed, val loss ~0.85. 6/8 smoke tests passed perfectly.
- **Artifact:** LoRA adapter saved in `models/qwen_final_adapter/`.

---

## Phase 3 & 4: Local Development (Current)

Building the inference engine and user interface.
- **Safety Module (`src/safety.py`)**: Implementation of blocklists and path restrictions.
- **Predictor Wrapper (`src/predictor.py`)**: Loading Qwen model and running CPU inference.
- **CLI Interface (`cli/main.py`)**: Rich-based terminal UI.
```

---

## How to Ask Gemini For Help (Read This Too)

When asking Gemini CLI for help inside this project, structure your prompts like this
for best results:

**For a new module:**

```
"I'm in Phase 3 of NLP2Shell. Read GEMINI.md for full context.
Write src/stt.py following the exact interface defined in GEMINI.md.
Use openai-whisper tiny model and pyaudio. Must work on CPU only."
```

**For a Kaggle notebook:**

```
"I'm in Phase 2 of NLP2Shell. Read GEMINI.md for context.
Write training/finetune.ipynb for Kaggle GPU (T4).
Follow the Kaggle notebook rules in GEMINI.md exactly.
Base model: Phi-3-mini. Dataset format: Alpaca jsonl."
```

**For debugging:**

```
"I'm working on NLP2Shell (see GEMINI.md). Here is the error:
[paste full traceback]
Here is the relevant file:
[paste file content]
Fix it without changing the function signatures in GEMINI.md."
```

---

## Known Constraints Summary (Quick Reference)

| Constraint    | Detail                                                               |
| ------------- | -------------------------------------------------------------------- |
| No local GPU  | Intel HD 520 only, no CUDA                                           |
| RAM limit     | 8GB total — model + OS + app must fit                                |
| Storage limit | ~30-40GB free — models must be quantized                             |
| No paid APIs  | Free tools only unless explicitly decided otherwise                  |
| Kaggle limit  | 30 GPU hrs/week — don't waste runs on bugs, test logic locally first |
| Python 3.11.9 | 3.10+ (confirm with `python --version` and update here)              |
| Windows       | (fill in your OS here)                                               |

---

_Last updated: Saturday, May 16, 2026_
_Maintain this file like documentation — it is the agent's memory for this project._

gemini --resume 'ecaba33c-6f70-45f7-a4d4-65b126678d79'
