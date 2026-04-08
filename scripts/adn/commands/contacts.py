"""adn contacts — Manage contacts."""

from rich.console import Console

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
    
    console = Console()
    console.print(f"\n[bold cyan]Contacts ({len(contacts)})[/bold cyan]")
    
    for ed_pub, contact in contacts.items():
        x_pub = contact.get("x25519_pub", "")
        nick = contact.get("nickname", "-") or "-"
        console.print(f"\n[green]Nickname:[green] {nick}")
        console.print(f"[cyan]Ed25519:[cyan] {ed_pub}")
        console.print(f"[yellow]X25519:[yellow] {x_pub}")
    
    return 0


def _add_contact(storage, ed25519, x25519, nickname) -> int:
    """Add a new contact."""
    if not ed25519 or not x25519:
        print("[red]Usage: adn contacts add <ed25519_pub> <x25519_pub> [nickname][/red]")
        return 1
    
    storage.add_contact(ed25519, x25519, nickname)
    print(f"[green]✓ Contact added[/green]")
    
    return 0
