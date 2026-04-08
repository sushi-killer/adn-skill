"""adn inbox — Check pending intents."""

from rich.console import Console

from adn.storage import Storage
from adn.api import ADNApiClient
from adn.crypto import CryptoBox


def cmd_inbox(args) -> int:
    """Check pending intents."""
    storage = Storage()
    status = getattr(args, 'status', None)
    
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
    
    crypto = CryptoBox(storage.config_dir)
    
    try:
        intents = api.get_inbox(status)
        
        if not intents:
            print("[yellow]No pending intents[/yellow]")
            return 0
        
        console = Console()
        
        console.print(f"\n[bold cyan]Inbox ({len(intents)} messages)[/bold cyan]")
        
        for i, intent in enumerate(intents, 1):
            console.print(f"\n[cyan]--- Message {i}/{len(intents)} ---" if len(intents) > 1 else "")
            console.print(f"[cyan]ID:[cyan] {intent.id}")
            console.print(f"[green]From:[green] {intent.from_pubkey}")
            console.print(f"[yellow]Status:[yellow] {intent.status}")
            if intent.x25519_pub:
                console.print(f"[white]x25519:[white] {intent.x25519_pub}")
            if intent.message:
                # Try to decrypt the message
                try:
                    plaintext = crypto.decrypt(intent.message)
                    console.print(f"[white]Message:[white]\n{plaintext}")
                except Exception:
                    # If decryption fails, show as-is
                    console.print(f"[white]Message:[white]\n{intent.message}")
        
        # Save to inbox.json
        storage.save_inbox([i.model_dump() for i in intents])
        
        return 0
    except Exception as e:
        print(f"[red]Error: {e}[/red]")
        return 1
