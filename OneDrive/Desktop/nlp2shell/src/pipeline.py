import os
import yaml
import sys
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.text import Text

# Import local modules
# Adding current dir to path to ensure imports work when run as script
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import stt
import predictor
import safety
import executor

console = Console()

def load_config():
    """Load configuration from config.yaml."""
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.yaml")
    with open(config_path, "r") as f:
        return yaml.safe_load(f)

def run(voice_mode: bool = True, dry_run: bool = False) -> None:
    """Main loop connecting all modules."""
    config = load_config()
    model_path = config.get("model", {}).get("path", "models/qwen_final_adapter")
    
    # Initialize predictor (load model once)
    with console.status("[bold blue]Initializing AI Model... (This takes ~20s on CPU)"):
        try:
            predictor.load_model(model_path)
        except Exception as e:
            console.print(f"[red]Error loading model: {e}[/red]")
            return

    console.print(Rule(style="dim"))
    console.print("[bold green]✓ System Ready![/bold green] Waiting for your command...")

    while True:
        try:
            # 1. Get input (Voice or Text)
            if voice_mode:
                text = stt.listen()
                if not text:
                    continue
                console.print(Panel(Text(text, style="cyan"), title="You Said", border_style="cyan"))
            else:
                console.print(Rule(style="dim"))
                text = stt.text_mode()
                if not text:
                    continue
            
            # Check for exit commands
            if text.lower() in ["exit", "quit", "q"]:
                console.print("[yellow]Exiting NLP2Shell...[/yellow]")
                break

            # 2. Predict Bash Command
            with console.status("[bold green]Thinking..."):
                command = predictor.predict(text)

            # 3. Safety Check
            if safety.check(command):
                # 4. Execute (with confirmation)
                executor.confirm_and_run(command, dry_run=dry_run)
            else:
                reason = safety.explain_block(command)
                console.print(Panel(
                    f"[bold red]Safety Block:[/bold red] {reason}\n[dim]Command: {command}[/dim]",
                    title="Security Alert",
                    border_style="red"
                ))

        except KeyboardInterrupt:
            console.print("\n[yellow]Exiting NLP2Shell...[/yellow]")
            break
        except Exception as e:
            console.print(f"[red]Pipeline Error: {e}[/red]")
            # Continue the loop instead of crashing
            continue

if __name__ == "__main__":
    # End-to-end test in text mode for verification
    print("Starting Pipeline Test (Text Mode, Dry Run)...")
    run(voice_mode=False, dry_run=True)
