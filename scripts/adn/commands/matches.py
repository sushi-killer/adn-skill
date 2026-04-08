"""adn matches — List active matches."""

from rich.console import Console
from rich.table import Table

from adn.storage import Storage
from adn.api import ADNApiClient


def cmd_matches(args) -> int:
    """List active matches."""
    storage = Storage()
    
    if not storage.is_registered():
        print("[yellow]Not registered.[/yellow]")
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
        matches = api.get_matches()
        
        if not matches:
            print("[yellow]No matches yet.[/yellow]")
            return 0
        
        table = Table(title="Active Matches")
        table.add_column("Match ID", style="cyan")
        table.add_column("Peer", style="green")
        table.add_column("Created", style="dim")
        
        from datetime import datetime
        for match in matches:
            peer = match.get_peer(pubkey)
            created = datetime.fromtimestamp(match.created_at / 1000).strftime("%Y-%m-%d %H:%M")
            table.add_row(match.id, peer, created)
        
        console = Console()
        console.print(table)
        
        return 0
    except Exception as e:
        print(f"[red]Error: {e}[/red]")
        return 1
