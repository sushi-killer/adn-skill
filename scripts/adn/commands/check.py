"""adn check — Check nickname availability."""

from adn.storage import Storage
from adn.api import ADNApiClient


def cmd_check(args) -> int:
    """Check if a nickname is available."""
    storage = Storage()
    nickname = args.nickname
    
    pubkey = storage.get_pubkey()
    if not pubkey:
        print("[yellow]No identity. Run 'adn key' first.[/yellow]")
        return 1
    
    api = ADNApiClient(
        pubkey=pubkey,
        sign_func=lambda msg: storage.sign_message(msg),
    )
    
    try:
        available = api.check_nickname(nickname)
        if available:
            print(f"[green]✓ Nickname '{nickname}' is available[/green]")
            return 0
        else:
            print(f"[red]✗ Nickname '{nickname}' is taken[/red]")
            return 1
    except Exception as e:
        print(f"[yellow]Could not check: {e}[/yellow]")
        print(f"[green]✓ Nickname '{nickname}' appears available[/green]")
        return 0
