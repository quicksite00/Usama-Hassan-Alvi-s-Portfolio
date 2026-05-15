import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
import os

# Configuration from GEMINI.md and GEMINI_phase3_4.md
BASE_MODEL_NAME = "Qwen/Qwen2.5-0.5B-Instruct"
SYSTEM_PROMPT = "Convert the natural language instruction to a bash command. Output only the command, nothing else."

# Global model and tokenizer
_model = None
_tokenizer = None

def load_model(model_path: str) -> None:
    """Load Qwen base model and apply LoRA adapter on CPU."""
    global _model, _tokenizer
    
    print(f"Loading base model: {BASE_MODEL_NAME}...")
    # Load base model on CPU
    _model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL_NAME,
        torch_dtype=torch.float32,
        device_map="cpu"
    )
    
    print(f"Applying LoRA adapter from: {model_path}...")
    # Apply LoRA adapter
    _model = PeftModel.from_pretrained(_model, model_path)
    _model.eval()
    
    print("Loading tokenizer...")
    _tokenizer = AutoTokenizer.from_pretrained(model_path)
    
    print("Model loaded successfully on CPU.")

def predict(natural_language: str) -> str:
    """Take NL string, return predicted bash command string using ChatML format."""
    global _model, _tokenizer
    
    if _model is None or _tokenizer is None:
        raise RuntimeError("Model not loaded. Call load_model() first.")

    # Prepare ChatML prompt
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": natural_language}
    ]
    
    prompt = _tokenizer.apply_chat_template(
        messages, 
        tokenize=False, 
        add_generation_prompt=True
    )
    
    inputs = _tokenizer(prompt, return_tensors="pt").to(_model.device)
    
    with torch.no_grad():
        outputs = _model.generate(
            **inputs,
            max_new_tokens=80,
            do_sample=False, # Greedy decoding
            eos_token_id=_tokenizer.eos_token_id,
            pad_token_id=_tokenizer.eos_token_id,
        )
    
    # Extract only the generated assistant response
    generated_ids = outputs[0][inputs["input_ids"].shape[1]:]
    command = _tokenizer.decode(generated_ids, skip_special_tokens=True).strip()
    
    # Simple post-processing: often models might wrap in backticks or add "Bash:" 
    command = command.replace("```bash", "").replace("```", "").strip()
    if command.lower().startswith("bash:"):
        command = command[5:].strip()
        
    return command

if __name__ == "__main__":
    # Standalone test
    ADAPTER_PATH = "models/qwen_final_adapter"
    
    if not os.path.exists(ADAPTER_PATH):
        print(f"Error: Adapter not found at {ADAPTER_PATH}")
        print("Please ensure you have downloaded the adapter from Kaggle.")
    else:
        load_model(ADAPTER_PATH)
        
        test_phrases = [
            "move all pdf files from downloads to documents",
            "list all files including hidden ones",
            "find all files larger than 100mb"
        ]
        
        print("\n--- Testing Predictions ---")
        for phrase in test_phrases:
            print(f"Input: {phrase}")
            cmd = predict(phrase)
            print(f"Predicted: {cmd}\n")
