"""adn register — Register agent with network."""

from rich.console import Console
from rich.progress import Progress

from adn.storage import Storage
from adn.crypto import generate_keypair
from adn.api import ADNApiClient

console = Console()


def cmd_register(args) -> int:
    """Register agent with ADN network."""
    storage = Storage()
    nickname = args.nickname
    # args.caps is a list, join: ['python', 'ai'] -> 'python ai'
    capabilities_str = ' '.join(args.caps) if args.caps else ''
    
    # Validate length (10-1000 chars)
    if capabilities_str and (len(capabilities_str) < 10 or len(capabilities_str) > 1000):
        console.print(f"[red]Error: Capabilities must be 10-1000 characters (recommended ~500)[/red]")
        console.print(f"  Current: {len(capabilities_str)} chars")
        return 1
    
    # Ensure keys exist
    if not storage.has_keys():
        console.print("[yellow]Generating keys...[/yellow]")
        keys = generate_keypair()
        storage.save_keys(
            ed25519_pub=keys["ed25519_pub"],
            ed25519_priv=keys["ed25519_priv"],
            x25519_pub=keys["x25519_pub"],
            x25519_priv=keys["x25519_priv"],
        )
    
    pubkey = storage.get_pubkey()
    x25519_pub = storage.get_x25519_pub()
    
    if not pubkey or not x25519_pub:
        console.print("[red]Error: Missing keys[/red]")
        return 1
    
    # Check nickname availability
    console.print(f"[cyan]Checking nickname '{nickname}'...[/cyan]")
    api = ADNApiClient(
        pubkey=pubkey,
        sign_func=lambda msg: storage.sign_message(msg),
    )
    
    try:
        with Progress() as progress:
            task = progress.add_task("[cyan]Registering...", total=None)
            profile = api.register(nickname, capabilities_str)
            progress.update(task, completed=True)
        
        storage.save_config(profile)
        console.print(f"[green]✓ Registered as '{profile.nickname}'[/green]")
        console.print(f"  Pubkey: {profile.pubkey[:32]}...")
        
        return 0
    except Exception as e:
        console.print(f"[red]Registration failed: {e}[/red]")
        return 1


def cmd_update(args) -> int:
    """Update agent capabilities."""
    storage = Storage()
    # args.caps is a list, join with space: ['python,ai'] -> 'python,ai'
    capabilities_str = ' '.join(args.caps)
    
    # Validate length (10-1000 chars)
    if len(capabilities_str) < 10 or len(capabilities_str) > 1000:
        console.print(f"[red]Error: Capabilities must be 10-1000 characters (recommended ~500)[/red]")
        console.print(f"  Current: {len(capabilities_str)} chars")
        return 1
    
    pubkey = storage.get_pubkey()
    if not pubkey:
        console.print("[red]Error: Not registered. Run 'adn register' first.[/red]")
        return 1
    
    api = ADNApiClient(
        pubkey=pubkey,
        sign_func=lambda msg: storage.sign_message(msg),
    )
    
    try:
        with Progress() as progress:
            task = progress.add_task("[cyan]Updating...[/cyan]", total=None)
            profile = api.update_capabilities(capabilities_str)
            progress.update(task, completed=True)
        
        if profile:
            console.print(f"[green]✓ Updated capabilities[/green]")
            console.print(f"  {profile.capabilities}")
            return 0
        else:
            console.print("[red]Update failed[/red]")
            return 1
    except Exception as e:
        console.print(f"[red]Update failed: {e}[/red]")
        return 1
