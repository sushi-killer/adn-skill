"""adn contacts — Manage contacts."""

from rich.console import Console
from rich.table import Table

from adn.storage import Storage


def cmd_contacts(args) -> int:
    """List or add contacts."""
    storage = Storage()
    action = args.action
    
    if action == "list" or action is None:
        return _list_contacts(storage)
    elif action == "add":
        return _add_contact(storage, args.ed25519, args.x25519, args.nickname)
    else:
        print(f"[yellow]Unknown action: {action}[/yellow]")
        return 1


def _list_contacts(storage) -> int:
    """List all contacts."""
    contacts = storage.get_contacts()
    
    if not contacts:
        print("[yellow]No contacts saved.[/yellow]")
        return 0
    
    table = Table(title="Contacts")
    table.add_column("Ed25519 Pubkey", style="cyan")
    table.add_column("X25519 Pubkey", style="green")
    table.add_column("Nickname", style="white")
    
    for ed_pub, contact in contacts.items():
        x_pub = contact.get("x25519_pub", "")
        nick = contact.get("nickname", "-")
        table.add_row(ed_pub, x_pub, nick)
    
    console = Console()
    console.print(table)
    
    return 0


def _add_contact(storage, ed25519, x25519, nickname) -> int:
    """Add a new contact."""
    if not ed25519 or not x25519:
        print("[red]Usage: adn contacts add <ed25519_pub> <x25519_pub> [nickname][/red]")
        return 1
    
    storage.add_contact(ed25519, x25519, nickname)
    print(f"[green]✓ Contact added[/green]")
    
    return 0
