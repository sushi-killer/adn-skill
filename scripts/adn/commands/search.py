"""adn search — Search for agents."""

from rich.console import Console
from rich.table import Table

from adn.storage import Storage
from adn.api import ADNApiClient


def cmd_search(args) -> int:
    """Search for agents in the network."""
    storage = Storage()
    query = args.query
    limit = args.limit
    
    pubkey = storage.get_pubkey()
    if not pubkey:
        print("[yellow]No identity. Run 'adn key' first.[/yellow]")
        return 1
    
    api = ADNApiClient(
        pubkey=pubkey,
        sign_func=lambda msg: storage.sign_message(msg),
    )
    
    try:
        agents = api.search(query, limit)
        
        if not agents:
            print(f"[yellow]No agents found for '{query}'[/yellow]")
            return 0
        
        console = Console()
        console.print(f"\n[bold cyan]Search results for '{query}' ({len(agents)} found)[/bold cyan]")
        
        for i, agent in enumerate(agents, 1):
            nick = getattr(agent, 'nickname', None) or "-"
            console.print(f"\n[cyan]--- Agent {i}/{len(agents)} ---")
            console.print(f"[green]Nickname:[green] {nick}")
            console.print(f"[yellow]Pubkey:[yellow] {agent.pubkey}")
            console.print(f"[white]Capabilities:[white]\n{agent.capabilities or '-'}")
        
        return 0
    except Exception as e:
        print(f"[red]Search failed: {e}[/red]")
        return 1
