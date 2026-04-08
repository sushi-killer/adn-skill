"""adn matches — List active matches."""

from datetime import datetime
from rich.console import Console

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
        
        console = Console()
        console.print(f"\n[bold cyan]Active Matches ({len(matches)})[/bold cyan]\n")
        
        for match in matches:
            peer_pubkey = match.get_peer(pubkey)
            
            # Get nickname from contacts or server
            contacts = storage.get_contacts()
            contact = contacts.get(peer_pubkey, {})
            nick = contact.get("nickname", "@unknown")
            
            # Try to fetch from server if not in contacts
            if not contact:
                try:
                    agent = api.get_agent(peer_pubkey)
                    if agent and agent.nickname:
                        nick = agent.nickname
                except Exception:
                    pass
            
            created = datetime.fromtimestamp(match.created_at / 1000).strftime("%Y-%m-%d %H:%M")
            
            nick_with_at = nick if nick.startswith("@") else f"@{nick}"
            console.print(f"[green]Nickname:[/green] {nick_with_at}")
            console.print(f"[cyan]Pubkey:[/cyan] {peer_pubkey}")
            console.print(f"[dim]Match ID:[/dim] {match.id}")
            console.print(f"[dim]Created:[/dim] {created}")
            console.print("")
        
        return 0
    except Exception as e:
        print(f"[red]Error: {e}[/red]")
        return 1
