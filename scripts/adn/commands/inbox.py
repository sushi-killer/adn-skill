"""adn inbox — Check pending intents."""

from rich.console import Console
from rich.table import Table

from adn.storage import Storage
from adn.api import ADNApiClient


def cmd_inbox(args) -> int:
    """Check pending intents."""
    storage = Storage()
    status = args.status
    
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
        intents = api.get_inbox(status)
        
        if not intents:
            print("[yellow]No pending intents[/yellow]")
            return 0
        
        table = Table(title="Inbox")
        table.add_column("ID", style="cyan")
        table.add_column("From", style="green")
        table.add_column("Message", style="white")
        table.add_column("Status", style="yellow")
        
        for intent in intents:
            from_pub = intent.from_pubkey[:24] + "..."
            msg_preview = intent.message[:30] + "..." if len(intent.message) > 30 else intent.message
            table.add_row(intent.id, from_pub, msg_preview, intent.status)
        
        console = Console()
        console.print(table)
        
        # Save to inbox.json
        storage.save_inbox([i.model_dump() for i in intents])
        
        return 0
    except Exception as e:
        print(f"[red]Error: {e}[/red]")
        return 1
