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
        
        table = Table(title=f"Results for '{query}'")
        table.add_column("Nickname", style="cyan")
        table.add_column("Capabilities", style="green")
        table.add_column("Pubkey", style="dim", overflow="fold")
        
        for agent in agents:
            caps = ", ".join(agent.capabilities[:3])
            if len(agent.capabilities) > 3:
                caps += "..."
            nick = getattr(agent, 'nickname', None) or agent.pubkey[:16] + "..."
            table.add_row(nick, caps or "-", agent.pubkey[:32] + "...")
        
        console = Console()
        console.print(table)
        
        return 0
    except Exception as e:
        print(f"[red]Search failed: {e}[/red]")
        return 1
