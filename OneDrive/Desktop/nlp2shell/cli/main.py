import argparse
import sys
import os
import platform
import shutil
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.live import Live
from rich.align import Align

# Add root directory to path to import src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src import pipeline

console = Console()

def show_banner():
    """Display a professional ASCII-style banner."""
    banner = Text()
    banner.append(" █▄▄ █   █▀█ ▀█▀ █▀█ █▀█ █ █ █▀▀ █   █  \n", style="bold bright_blue")
    banner.append(" █ █ █▄▄ █▀▀  █  ▀▀█ ▀▀█ █▀█ ██▄ █▄▄ █▄▄\n", style="bold cyan")
    banner.append("   Natural Language to Shell Assistant  ", style="italic dim")
    
    console.print(Align.center(Panel(banner, border_style="bright_blue", padding=(1, 4))))
    console.print()

def show_system_info(args):
    """Display a summary of the current system configuration."""
    table = Table(show_header=False, box=None, padding=(0, 2))
    
    # Model info
    model_name = "Qwen2.5-0.5B (LoRA)"
    device = "CPU (Intel HD 520)"
    
    # Mode info
    mode = "⌨  [bold cyan]Text Input[/bold cyan]" if args.text else "🎤 [bold green]Voice Input[/bold green]"
    safe = " [bold yellow][SAFE MODE][/bold yellow]" if args.safe else ""
    
    # WSL info
    wsl_status = "[green]Enabled[/green]" if shutil.which("wsl") else "[red]Disabled[/red]"
    
    table.add_row("[bold]Model:[/bold]", model_name)
    table.add_row("[bold]Device:[/bold]", device)
    table.add_row("[bold]Input:[/bold]", f"{mode}{safe}")
    table.add_row("[bold]WSL:[/bold]", wsl_status)
    table.add_row("[bold]OS:[/bold]", platform.system())
    
    console.print(Align.center(Panel(table, title="System Configuration", border_style="dim", width=60)))
    console.print(Align.center("[dim]Type 'exit' or 'quit' to close • Ctrl+C for emergency stop[/dim]"))
    console.print()

def main():
    parser = argparse.ArgumentParser(description="NLP2Shell: Voice/Text to Bash Command Assistant")
    parser.add_argument("--text", action="store_true", help="Use text input mode instead of voice")
    parser.add_argument("--safe", action="store_true", help="Dry-run mode (never execute commands)")
    
    args = parser.parse_args()
    
    console.clear()
    show_banner()
    show_system_info(args)
    
    try:
        # Run the pipeline
        pipeline.run(voice_mode=not args.text, dry_run=args.safe)
    except KeyboardInterrupt:
        console.print("\n[yellow]Goodbye![/yellow]")
    except Exception as e:
        console.print(f"\n[bold red]Critical Error:[/bold red] {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
