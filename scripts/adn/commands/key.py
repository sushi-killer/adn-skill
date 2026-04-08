"""adn key — Show/generate identity."""

from adn.storage import Storage
from adn.crypto import generate_keypair


def cmd_key(args) -> int:
    """Show identity or generate new keypair."""
    storage = Storage()
    
    pubkey = storage.get_pubkey()
    if not pubkey:
        print("[yellow]No identity found. Generating Ed25519 keypair...[/yellow]")
        keys = generate_keypair()
        storage.save_keys(
            ed25519_pub=keys["ed25519_pub"],
            ed25519_priv=keys["ed25519_priv"],
            x25519_pub=keys["x25519_pub"],
            x25519_priv=keys["x25519_priv"],
        )
        pubkey = keys["ed25519_pub"]
        x25519_pub = keys["x25519_pub"]
        print("[green]Keypair generated![/green]")
    else:
        x25519_pub = storage.get_x25519_pub()
    
    print(f"\n[bold]Ed25519 Public Key:[/bold]")
    print(f"  {pubkey}")
    
    if x25519_pub:
        print(f"\n[bold]X25519 Public Key (Encryption):[/bold]")
        print(f"  {x25519_pub}")
    
    config = storage.get_config()
    if config:
        print(f"\n[bold]Nickname:[/bold] {config.nickname}")
        print(f"[bold]Capabilities:[/bold] {config.capabilities}")
    
    return 0
