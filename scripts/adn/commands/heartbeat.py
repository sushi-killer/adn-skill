"""adn heartbeat — Stay alive in network."""

from adn.storage import Storage
from adn.api import ADNApiClient


def cmd_heartbeat(args) -> int:
    """Send heartbeat to stay registered."""
    storage = Storage()
    
    if not storage.is_registered():
        print("[yellow]Not registered. Run 'adn register' first.[/yellow]")
        return 1
    
    pubkey = storage.get_pubkey()
    if not pubkey:
        print("[red]Error: Missing identity[/red]")
        return 1
    
    api = ADNApiClient(
        pubkey=pubkey,
        sign_func=lambda msg: storage.sign_message(msg),
    )
    
    try:
        success = api.heartbeat()
        if success:
            print("[green]✓ Heartbeat sent[/green]")
            return 0
        else:
            print("[yellow]Heartbeat failed[/yellow]")
            return 1
    except Exception as e:
        print(f"[red]Error: {e}[/red]")
        return 1
