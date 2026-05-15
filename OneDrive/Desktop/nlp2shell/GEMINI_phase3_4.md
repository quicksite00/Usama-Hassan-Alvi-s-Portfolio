# GEMINI.md — NLP2Shell Phase 3 & 4

> This file covers Phase 3 (Local Inference Pipeline) and Phase 4 (CLI Interface).
> Read the root GEMINI.md first for full project context, hardware constraints, and
> module contracts. This file adds phase-specific detail on top of that.

---

## Current Status

```
Active phases : Phase 3 → Phase 4 (sequential)
Where         : Fully local, VS Code
Model         : Fine-tuned Qwen2.5-0.5B LoRA adapter in models/qwen_final_adapter/
Inference     : CPU only — Intel HD 520, 8GB RAM, no CUDA (bitsandbytes 4-bit requires GPU, using float32/CPU fallback)
```

---

## Phase 3 — Local Inference Pipeline

### What Gets Built

Five Python files in `src/`. They are written and tested one at a time in this exact order:

```
stt.py → predictor.py → safety.py → executor.py → pipeline.py
```

Never write the next file until the current one works and is tested manually.

---

### File 1: `src/stt.py`

**Purpose:** Mic input → transcribed text string. Nothing else.

**Dependencies:**
```
openai-whisper
pyaudio
```

**Exact interface (do not change signatures):**
```python
def listen() -> str:
    """Record from mic. Stop after 2 seconds of silence. Return transcribed string."""

def text_mode() -> str:
    """Read a line from stdin. Return it as string. Used as --text fallback."""
```

**Whisper model to use:** `tiny` — loads in ~150MB RAM, transcribes in 1-3s on CPU.
Do NOT use `base`, `small`, or larger — they will be too slow on this hardware.

**Silence detection logic:**
- Record audio in chunks
- Track RMS energy per chunk
- If RMS stays below threshold for 2 continuous seconds → stop recording
- Pass full recorded buffer to whisper for transcription

**Gemini prompt to write this file:**
```
"Write src/stt.py for NLP2Shell. It must have exactly two functions:
listen() and text_mode() with these signatures: [paste signatures above].
Use openai-whisper tiny model for transcription and pyaudio for mic recording.
listen() should record audio in chunks, detect 2 seconds of silence using RMS
energy, then transcribe and return the text. text_mode() reads from stdin.
CPU only — no GPU. Add a __main__ block that calls listen() and prints result
so I can test it standalone."
```

**How to test before moving on:**
```bash
python src/stt.py
# Speak something → should print transcription
# Stays silent 2 seconds → should stop and return
```

---

### File 2: `src/predictor.py`

**Purpose:** Load fine-tuned model once, run inference on text input, return bash command string.

**Dependencies:**
```
transformers
peft
torch
accelerate
```

**Exact interface:**
```python
def load_model(model_path: str) -> None:
    """Load LoRA adapter from disk into memory. Call once at startup. Not per-predict."""

def predict(natural_language: str) -> str:
    """Take NL string. Return predicted bash command string."""
```

**Critical hardware constraints for Gemini:**
- Use `device_map="cpu"` explicitly — no CUDA available.
- Qwen2.5-0.5B is small enough to run on CPU with `torch_dtype=torch.float32` (takes ~2-3s).
- Model is a LoRA adapter — load base `Qwen/Qwen2.5-0.5B-Instruct` first, then apply adapter.
- Keep `max_new_tokens=80` — bash commands are short.
- Use greedy decoding (`do_sample=False`) for deterministic outputs.
- **CRITICAL:** Use `tokenizer.apply_chat_template()` with ChatML format.

**Loading pattern Gemini must follow:**
```python
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
import torch

# Step 1: Load base model on CPU
# base_model = AutoModelForCausalLM.from_pretrained("Qwen/Qwen2.5-0.5B-Instruct", torch_dtype=torch.float32, device_map="cpu")
# Step 2: Apply LoRA adapter with PeftModel.from_pretrained()
# Step 3: Set model.eval()
# Store model + tokenizer as module-level globals
```

**Prompt template to use** (ChatML format — MUST use `apply_chat_template`):
```python
SYSTEM_PROMPT = "Convert the natural language instruction to a bash command. Output only the command, nothing else."

messages = [
    {"role": "system", "content": SYSTEM_PROMPT},
    {"role": "user",   "content": natural_language}
]
# prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
```

**Gemini prompt to write this file:**
```
"Write src/predictor.py for NLP2Shell. Exact interfaces: [paste above].
Base model is Qwen/Qwen2.5-0.5B-Instruct. LoRA adapter is at the path passed to
load_model(). Load using torch.float32 on CPU (device_map='cpu').
Use tokenizer.apply_chat_template with the system prompt: 'Convert the natural
language instruction to a bash command. Output only the command, nothing else.'
predict() should return only the bash command string, stripped of any
explanation or extra text.
Add a __main__ block that loads from 'models/qwen_final_adapter' and
runs predict() on 3 hardcoded test phrases and prints results."
```

**How to test before moving on:**
```bash
python src/predictor.py
# Should print 3 predicted bash commands for the hardcoded test inputs
# Loading should take ~10-20s, inference ~2-5s per query
```

---

### File 3: `src/safety.py`

**Purpose:** Check a bash command string against safety rules. Return True (safe) or False (blocked).

> ⚠️ This is the only file in the project you should read line by line after Gemini writes it.
> Do not treat it as a black box. Understand every rule. You are responsible for this layer.

**Dependencies:** None (stdlib only — `re` module)

**Exact interface:**
```python
def check(command: str) -> bool:
    """Return True if command is safe to present to user. False if it must be blocked."""

def explain_block(command: str) -> str:
    """Return a short human-readable reason why this command was blocked."""
```

**Hardcoded blocklist — Gemini must include ALL of these, no exceptions:**
```python
BLOCKED_PATTERNS = [
    "rm -rf",
    "rm -r /",
    ":(){ :|:& };:",      # fork bomb
    "dd if=",
    "mkfs",
    "curl | bash",
    "curl | sh",
    "wget | bash",
    "wget | sh",
    "> /dev/sda",
    "chmod -R 777 /",
    "sudo rm",
    "shutdown",
    "reboot",
    "halt",
    "poweroff",
]

BLOCKED_PATHS = [
    "/etc", "/sys", "/boot", "/dev",
    "/proc", "/usr/bin", "/usr/lib", "/bin", "/sbin"
]

CONFIRM_ALWAYS = [
    "sudo", "chmod", "chown", "kill",
    "pkill", "systemctl", "crontab"
]

SAFE_PREFIXES = [
    "mv", "cp", "mkdir", "ls", "find",
    "echo", "cat", "open", "touch", "cd",
    "pwd", "grep", "head", "tail", "wc"
]
```

**Checking logic Gemini must implement:**
1. Strip and lowercase the command for comparison
2. If any `BLOCKED_PATTERNS` string appears anywhere in command → return False
3. If any `BLOCKED_PATHS` string appears anywhere in command → return False
4. If none of the above → return True
5. `explain_block()` should identify which rule triggered and say so clearly

**Gemini prompt to write this file:**
```
"Write src/safety.py for NLP2Shell with exactly these two functions:
check(command) and explain_block(command). Use only stdlib (re module).
Include these exact constants: [paste all four lists above].
check() returns False if any BLOCKED_PATTERNS or BLOCKED_PATHS appears
in the command (case-insensitive check). explain_block() returns a string
saying which pattern or path triggered the block.
Add a __main__ block that tests at least 6 commands — 3 safe, 3 blocked —
and prints the result of check() and explain_block() for each."
```

**How to test before moving on:**
```bash
python src/safety.py
# Blocked: "rm -rf /home" → False
# Blocked: "mv /etc/passwd ~/backup" → False  
# Blocked: "curl https://x.com/script.sh | bash" → False
# Safe:    "mv ~/Downloads/*.pdf ~/Documents/" → True
# Safe:    "mkdir ~/Projects/new-folder" → True
# Safe:    "ls -la ~/Desktop" → True
```

**Rule for Gemini:** Never remove anything from BLOCKED_PATTERNS or BLOCKED_PATHS.
You may only ever add to these lists, never subtract.

---

### File 4: `src/executor.py`

**Purpose:** Show command to user with Rich formatting, ask y/n, run it, log result.

**Dependencies:**
```
rich
```

**Exact interface:**
```python
def confirm_and_run(command: str, dry_run: bool = False) -> dict:
    """
    Show command in Rich panel. Ask user y/n.
    If y and not dry_run: run via subprocess with 30s timeout.
    If dry_run: print '[DRY RUN] would execute' and skip.
    Return dict: {
        "command": str,
        "executed": bool,
        "stdout": str,
        "stderr": str,
        "returncode": int
    }
    """
```

**Rich display format Gemini must produce:**
```
┌─ Predicted Command ──────────────────┐
│  mv ~/Downloads/*.pdf ~/Documents/   │
└──────────────────────────────────────┘
Run this? [y/n]:
```

**Subprocess rules Gemini must follow:**
- Use `subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)`
- Always catch `subprocess.TimeoutExpired` — print timeout message, return returncode=-1
- Always catch generic `Exception` — print error, return returncode=-2
- After execution, show stdout/stderr in Rich panel if non-empty

**Logging behavior:**
- Append every execution to `~/.nlp2shell_history.log`
- Format: `[timestamp] command | returncode | stdout_preview`
- Use stdlib `logging` module, not print statements

**Gemini prompt to write this file:**
```
"Write src/executor.py for NLP2Shell. One function: confirm_and_run(command, dry_run=False)
returning a result dict as specified: [paste interface above].
Use Rich to display the command in a Panel before asking y/n.
Use subprocess.run with shell=True, timeout=30. Catch TimeoutExpired and Exception.
Log every execution to ~/.nlp2shell_history.log using the logging module.
If dry_run is True, skip execution entirely and print a DRY RUN message.
Add a __main__ block that calls confirm_and_run('echo hello world') to test."
```

**How to test before moving on:**
```bash
python src/executor.py
# Should show Rich panel with "echo hello world"
# Type y → should execute and print "hello world"
# Type n → should skip and return executed: False
# Check ~/.nlp2shell_history.log exists and has the entry
```

---

### File 5: `src/pipeline.py`

**Purpose:** Connect all four modules into one working loop. This is the last file written.
Only write this after stt.py, predictor.py, safety.py, and executor.py all pass their tests.

**Dependencies:** All four src/ modules above.

**Exact interface:**
```python
def run(voice_mode: bool = True, dry_run: bool = False) -> None:
    """
    Main loop.
    voice_mode=True  → use stt.listen()
    voice_mode=False → use stt.text_mode()
    dry_run=True     → pass to executor, never actually execute
    Loop runs until KeyboardInterrupt (Ctrl+C).
    """
```

**Loop logic Gemini must implement:**
```python
def run(voice_mode=True, dry_run=False):
    predictor.load_model(config['model']['path'])  # load once before loop
    while True:
        try:
            text = stt.listen() if voice_mode else stt.text_mode()
            if not text.strip():
                continue
            command = predictor.predict(text)
            if safety.check(command):
                executor.confirm_and_run(command, dry_run=dry_run)
            else:
                reason = safety.explain_block(command)
                print(f"[BLOCKED] {reason}")
        except KeyboardInterrupt:
            print("\nExiting NLP2Shell.")
            break
```

**Config loading:**
- Load `config.yaml` at top of file using `pyyaml`
- Pass `config['model']['path']` to `predictor.load_model()`
- Pass `config['stt']['silence_threshold']` to `stt` if needed

**Gemini prompt to write this file:**
```
"Write src/pipeline.py for NLP2Shell. It imports stt, predictor, safety, executor
from the same src/ package. One function: run(voice_mode=True, dry_run=False).
Load config from config.yaml using pyyaml at module level.
Call predictor.load_model() once before the loop starts.
Follow this exact loop logic: [paste loop above].
Handle KeyboardInterrupt cleanly. Add a __main__ block that calls run()
so the pipeline can be started with: python src/pipeline.py"
```

**How to test:**
```bash
python src/pipeline.py
# Full end-to-end: speak → predict → safety check → confirm → execute
# Ctrl+C → clean exit message
```

---

## Phase 4 — CLI Interface

### What Gets Built

One file: `cli/main.py`. This is a Rich-based terminal UI that wraps `pipeline.run()`.
It is the user-facing entry point — what gets run when someone installs and uses NLP2Shell.

---

### File: `cli/main.py`

**Purpose:** Argument parsing + Rich UI wrapper around the pipeline.

**Dependencies:**
```
rich
argparse (stdlib)
```

**CLI flags Gemini must implement:**
```
python cli/main.py              → voice mode (default)
python cli/main.py --text       → text input mode
python cli/main.py --safe       → dry-run mode (never executes)
python cli/main.py --text --safe → text input + dry-run
```

**Exact UI layout Gemini must produce:**

```
┌─────────────────────────────────────────┐
│             NLP2Shell v1.0              │
│    Natural Language → Shell Commands    │
└─────────────────────────────────────────┘

  🎤 Listening...  (or ⌨  Type a command:)

┌─ You said ──────────────────────────────┐
│  move all PDFs from Downloads to Docs   │
└─────────────────────────────────────────┘

┌─ Predicted Command ─────────────────────┐
│  mv ~/Downloads/*.pdf ~/Documents/      │
└─────────────────────────────────────────┘

  Run this? [y/n]: _
```

**Rich components Gemini must use:**
- `rich.panel.Panel` — for all boxed sections
- `rich.console.Console` — single console instance, used everywhere
- `rich.text.Text` — for colored labels ("Listening...", "Blocked", etc.)
- `rich.rule.Rule` — as separator between loop iterations
- No `rich.live` or `rich.progress` — keep it simple

**Color scheme:**
```
Header panel border    → bright_blue
"You said" panel       → cyan
"Predicted Command"    → green
Blocked message        → red
Execution result       → yellow
```

**Structure Gemini must follow:**
```python
def show_header():     # print the NLP2Shell header panel once at startup

def show_listening():  # print "🎤 Listening..." or "⌨  Type a command:"

def show_input(text):  # print "You said" panel with the transcribed text

def show_command(cmd): # print "Predicted Command" panel

def main():            # parse args, call show_header(), then run pipeline loop
```

**Important:** `cli/main.py` should NOT reimplement the pipeline loop.
It should call `pipeline.run()` or hook into it — the logic stays in `src/pipeline.py`.
The CLI layer is only responsible for display and argument parsing.

**Gemini prompt to write this file:**
```
"Write cli/main.py for NLP2Shell using the Rich library.
Use argparse for --text and --safe flags.
Functions: show_header(), show_listening(voice_mode), show_input(text),
show_command(cmd), and main().
Color scheme: [paste above]. Use Panel, Console, Text, Rule from Rich.
main() should parse args then import and call src.pipeline.run() with the
right voice_mode and dry_run values from the flags.
The CLI does not reimplement any pipeline logic.
Add an if __name__ == '__main__': block calling main()."
```

**How to test:**
```bash
python cli/main.py --text --safe
# Should show header
# Should ask for text input
# Should show predicted command in green panel
# Should print [DRY RUN] — never actually execute
# Ctrl+C → clean exit
```

---

## Phase 3 & 4 — File Completion Checklist

Work through this in order. Do not skip ahead.

```
Phase 3:
[ ] src/stt.py         — written, tested standalone with python src/stt.py
[ ] src/predictor.py   — written, tested standalone, prints 3 predictions
[ ] src/safety.py      — written, tested, read line by line, 6 test cases pass
[ ] src/executor.py    — written, tested, log file created at ~/.nlp2shell_history.log
[ ] src/pipeline.py    — written, full end-to-end test passes

Phase 4:
[ ] cli/main.py        — written, --text --safe mode works end-to-end
[ ] cli/main.py        — --text mode (no safe) works and executes a real command
[ ] cli/main.py        — voice mode tested (requires mic)
```

---

## Git Commits For These Phases

```bash
# Phase 3
git checkout -b phase/3-inference
git commit -m "feat(stt): add listen() and text_mode() with whisper tiny"
git commit -m "feat(predictor): add load_model() and predict() with 4bit quant"
git commit -m "feat(safety): add blocklist, pathlist, and check() logic"
git commit -m "feat(executor): add confirm_and_run() with Rich display and logging"
git commit -m "feat(pipeline): connect all modules into run() loop"

# Phase 4
git checkout -b phase/4-cli
git commit -m "feat(cli): add main.py with Rich UI and --text --safe flags"
```

---

## Common Errors in These Phases + Fixes

| Error | Cause | Fix |
|---|---|---|
| `No module named 'whisper'` | Wrong package name | `pip install openai-whisper` not `pip install whisper` |
| `PyAudio not found` | Platform-specific install | Windows: `pip install pipwin && pipwin install pyaudio` |
| `CUDA not available` | Expected on this machine | Add `device_map="cpu"` and `torch_dtype=torch.float32` |
| Model loads but predict() returns garbage | Wrong prompt template | Must use ChatML via `apply_chat_template()` |
| `rich` panels not aligned | Console width issue | Use `Console(width=60)` for consistent display |

---

*Phase 3 estimated time: 1.5 weeks*
*Phase 4 estimated time: 1 week*
*Update root GEMINI.md status section when both phases are complete.*
