"""adn respond — Accept or reject an intent."""

from rich.console import Console

from adn.storage import Storage
from adn.api import ADNApiClient


def cmd_respond(args) -> int:
    """Respond to an incoming intent (accept or reject).
    
    Sends POST to /relay/respond with:
    - intent_id: the intent to respond to
    - accept: true/false
    
    Usage: adn respond <intent_id> [accept|reject]
    """
    console = Console()
    storage = Storage()
    intent_id = args.id
    accept = args.action == "accept"
    
    if not intent_id:
        console.print("[red]Error: Intent ID required[/red]")
        console.print("Usage: adn respond <intent_id> [accept|reject]")
        return 1
    
    if not storage.has_keys():
        console.print("[yellow]Not registered. Run 'adn key' first.[/yellow]")
        return 1
    
    if not storage.is_registered():
        console.print("[yellow]Not registered. Run 'adn register' first.[/yellow]")
        return 1
    
    pubkey = storage.get_pubkey()
    if not pubkey:
        console.print("[red]Error: Missing identity[/red]")
        return 1
    
    api = ADNApiClient(
        pubkey=pubkey,
        sign_func=lambda msg: storage.sign_message(msg),
    )
    
    try:
        success = api.respond_to_intent(intent_id, accept)
        
        if success:
            action = "accepted" if accept else "rejected"
            console.print(f"[green]✓ Intent {action}[/green]")
            console.print(f"  Intent ID: {intent_id}")
            return 0
        else:
            console.print("[red]Failed to respond to intent[/red]")
            return 1
            
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        return 1
