import subprocess
import logging
import os
import platform
import shutil
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm

# Setup logging to home directory
LOG_FILE = os.path.expanduser("~/.nlp2shell_history.log")
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="[%(asctime)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

console = Console()

def get_shell_prefix():
    """Determine if we need a prefix to run bash commands on Windows."""
    if platform.system() == "Windows":
        # Check for wsl first as user confirmed it's available
        if shutil.which("wsl"):
            return "wsl "
        # Fallback to git bash
        if shutil.which("bash"):
            return "bash -c "
    return ""

def translate_path_for_wsl(command: str) -> str:
    """
    Attempt to translate Windows-style paths (~/Desktop, C:\...) 
    to WSL-compatible paths (/mnt/c/Users/...)
    """
    # Replace ~/ with the actual WSL home if possible, 
    # but model often predicts ~/ assuming it's the Linux home.
    # On Windows, Desktop is usually at /mnt/c/Users/<User>/Desktop
    
    # Simple replacement for common desktop/documents patterns
    # This is a heuristic fix for the user's specific error
    user_name = os.getlogin()
    command = command.replace("~/Desktop", f"/mnt/c/Users/{user_name}/Desktop")
    command = command.replace("~/Downloads", f"/mnt/c/Users/{user_name}/Downloads")
    command = command.replace("~/Documents", f"/mnt/c/Users/{user_name}/Documents")
    
    return command

def confirm_and_run(command: str, dry_run: bool = False) -> dict:
    """
    Show command in Rich panel. Ask user y/n.
    If y and not dry_run: run via subprocess (wrapping in WSL/Bash if on Windows).
    """
    result = {
        "command": command,
        "executed": False,
        "stdout": "",
        "stderr": "",
        "returncode": None
    }

    # Display command in a nice Rich panel
    console.print(Panel(command, title="Predicted Command", border_style="green"))

    if dry_run:
        console.print("[yellow][DRY RUN][/yellow] Command would be executed here.")
        logging.info(f"DRY RUN | {command}")
        return result

    # Ask for confirmation
    if not Confirm.ask("Run this command?"):
        console.print("[yellow]Skipped.[/yellow]")
        logging.info(f"SKIPPED | {command}")
        return result

    result["executed"] = True
    
    # Apply Windows-specific shell wrapping
    prefix = get_shell_prefix()
    
    # Path translation for WSL
    if prefix == "wsl ":
        command = translate_path_for_wsl(command)
        console.print(f"[dim]Translated for WSL: {command}[/dim]")

    final_command = f"{prefix}'{command}'" if prefix == "bash -c " else f"{prefix}{command}"
    
    if prefix:
        console.print(f"[dim]Running via {prefix.strip()}...[/dim]")
    
    console.print("Executing...", style="bold yellow")

    try:
        # Run the command with explicit encoding to avoid "garbage" characters
        process = subprocess.run(
            final_command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
            encoding="utf-8",
            errors="replace"
        )
        
        result["stdout"] = process.stdout.strip()
        result["stderr"] = process.stderr.strip()
        result["returncode"] = process.returncode

        # Log and display output
        if result["stdout"]:
            console.print(Panel(result["stdout"], title="Output", border_style="blue"))
        if result["stderr"]:
            # Fix common WSL path error display
            error_msg = result["stderr"]
            console.print(Panel(error_msg, title="Error", border_style="red"))
            
        logging.info(f"EXECUTED | {command} | RC: {result['returncode']} | OUT: {result['stdout'][:50]}...")

    except subprocess.TimeoutExpired:
        result["returncode"] = -1
        result["stderr"] = "Error: Command timed out after 30 seconds."
        console.print(f"[red]{result['stderr']}[/red]")
        logging.error(f"TIMEOUT  | {command}")
    except Exception as e:
        result["returncode"] = -2
        result["stderr"] = f"Error: {str(e)}"
        console.print(f"[red]{result['stderr']}[/red]")
        logging.error(f"ERROR    | {command} | {str(e)}")

    return result

if __name__ == "__main__":
    # Standalone test
    console.print("[bold cyan]Testing Executor Module[/bold cyan]")
    
    # Test 1: Safe command execution
    console.print("\n[bold]Test 1: Normal Execution[/bold]")
    confirm_and_run("echo 'Hello from NLP2Shell Executor!'")
    
    # Test 2: Dry run
    console.print("\n[bold]Test 2: Dry Run[/bold]")
    confirm_and_run("ls -la", dry_run=True)
    
    console.print(f"\n[dim]Logs written to: {LOG_FILE}[/dim]")
