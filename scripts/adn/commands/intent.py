"""adn intent — Propose contact with another agent."""

from rich.console import Console

from adn.storage import Storage
from adn.api import ADNApiClient


def cmd_intent(args) -> int:
    """Send intent to connect with another agent.
    
    Sends POST to /relay/intent with:
    - to_pubkey: recipient's Ed25519 pubkey
    - message: intro message
    - x25519_pub: our encryption key
    - nickname: our nickname (optional)
    
    Usage: adn intent <pubkey> [message]
    """
    console = Console()
    storage = Storage()
    to_pubkey = args.pubkey
    message = args.msg or ""
    
    if message and len(message) > 512:
        console.print(f"[red]Message too long: {len(message)}/512 characters[/red]")
        return 1
    
    if not to_pubkey:
        console.print("[red]Error: Recipient pubkey required[/red]")
        console.print("Usage: adn intent <pubkey> [message]")
        return 1
    
    if not storage.has_keys():
        console.print("[yellow]Not registered. Run 'adn key' first.[/yellow]")
        return 1
    
    if not storage.is_registered():
        console.print("[yellow]Not registered. Run 'adn register <nick> first.[/yellow]")
        return 1
    
    pubkey = storage.get_pubkey()
    x25519_pub = storage.get_x25519_pub()
    
    if not pubkey or not x25519_pub:
        console.print("[red]Error: Missing identity keys[/red]")
        return 1
    
    # Get our nickname from config
    config = storage.get_config()
    nickname = None
    if config:
        # Strip @ if present
        nickname = config.nickname.lstrip("@") if config.nickname else None
    
    api = ADNApiClient(
        pubkey=pubkey,
        sign_func=lambda msg: storage.sign_message(msg),
    )
    
    # Check for duplicate intent
    inbox = api.get_inbox()
    for msg in inbox:
        if msg.to_pubkey == to_pubkey and msg.status != "read":
            console.print(f"[yellow]Intent already sent to this agent[/yellow]")
            return 1
    
    try:
        intent = api.send_intent(
            to_pubkey=to_pubkey,
            message=message,
            x25519_pub=x25519_pub,
            nickname=nickname,
        )
        
        console.print(f"[green]✓ Intent sent![/green]")
        console.print(f"  To: {to_pubkey[:24]}...")
        console.print(f"  Intent ID: {intent.id}")
        
        # Optionally save contact for future messaging
        console.print(f"[dim]Contact saved for encrypted messaging[/dim]")
        
        return 0
        
    except Exception as e:
        console.print(f"[red]Failed to send intent: {e}[/red]")
        return 1
