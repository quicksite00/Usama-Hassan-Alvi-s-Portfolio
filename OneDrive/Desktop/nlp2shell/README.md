# NLP2Shell — Natural Language to Shell Assistant

**NLP2Shell** is a local desktop tool that accepts natural language (voice or text) and converts it into executable shell/bash commands using a fine-tuned language model.

## 🚀 Features
- **Voice & Text Input:** Transcribe speech using OpenAI Whisper (Tiny) or type instructions directly.
- **Fine-tuned LLM:** Powered by a quantized **Qwen2.5-0.5B-Instruct** model with a LoRA adapter trained on the NL2Bash dataset.
- **Safety First:** Multi-layered security check including blocklists for dangerous patterns (`rm -rf`, `mkfs`, etc.) and restricted system paths (`/etc`, `/boot`).
- **Windows & Linux Support:** Native WSL (Windows Subsystem for Linux) integration to run Bash commands seamlessly on Windows.
- **Rich CLI:** Polished terminal interface with real-time status, colored panels, and execution history logging.

---

## 🛠️ System Architecture

```text
Voice/Text Input → Whisper STT (if voice) → Fine-tuned Qwen2.5-0.5B → Safety Guardrails → WSL/Bash Execution
```

---

## 📦 Installation

### 1. Prerequisites
- **Python 3.10+**
- **WSL (optional but recommended for Windows):** To run Bash commands natively.
- **Microphone:** For voice input mode.

### 2. Setup
```bash
# Clone the repository
git clone https://github.com/HassanNawaz14/NLP2Shell-Voice-Assistant.git
cd nlp2shell

# Install dependencies
pip install -r requirements.txt
```

### 3. Model Weights
The LoRA adapter should be placed in `models/qwen_final_adapter/`. The base model will be downloaded automatically from HuggingFace on first run.

---

## 🚀 Usage

Run the assistant using the CLI entry point:

```bash
# Voice mode (default)
python cli/main.py

# Text input mode
python cli/main.py --text

# Safe mode (Dry-run, won't execute commands)
python cli/main.py --text --safe
```

---

## 🛡️ Safety Guardrails
NLP2Shell is designed with safety as a priority. Every command is:
1. **Predicted** by the AI.
2. **Scanned** for blocked patterns (e.g., `rm -rf /`, `curl | bash`).
3. **Checked** for restricted paths (e.g., `/etc`, `/dev`).
4. **Confirmed** by the user before execution.

---

## 📝 Project Structure
- `cli/main.py`: Enhanced terminal UI.
- `src/stt.py`: Speech-to-text with Whisper.
- `src/predictor.py`: AI inference engine.
- `src/safety.py`: Command validation guardrails.
- `src/executor.py`: Command execution with WSL/Bash mapping.
- `src/pipeline.py`: Main orchestration logic.

---

## 👨‍💻 Developer
Developed by **Hassan**, BS Data Science student. Focused on efficient, CPU-friendly local AI applications.
