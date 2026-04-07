"""adn log — Show local chat history."""

from rich.console import Console
from rich.panel import Panel

from adn.storage import Storage


def cmd_log(args) -> int:
    """Show local chat history for a match."""
    storage = Storage()
    match_id = args.match_id
    
    chat = storage.get_chat(match_id)
    
    if not chat:
        print(f"[yellow]No local history for match '{match_id}'[/yellow]")
        return 0
    
    console = Console()
    pubkey = storage.get_pubkey()
    
    for msg in chat[-50:]:  # Last 50
        is_own = msg.get("from") == pubkey or msg.get("from_pubkey") == pubkey
        prefix = "[cyan]You[/cyan]" if is_own else "[green]Them[/green]"
        text = msg.get("text", msg.get("ciphertext", "[no text]"))
        console.print(Panel(text, title=prefix, border_style="dim"))
    
    return 0


def cmd_history(args) -> int:
    """Show all local chat history."""
    storage = Storage()
    pubkey = storage.get_pubkey()
    
    contacts = storage.get_contacts()
    inbox = storage.get_inbox()
    
    console = Console()
    
    # Show contacts
    if contacts:
        console.print("\n[bold]Contacts:[/bold]")
        for ed_pub, contact in contacts.items():
            nick = contact.get("nickname", ed_pub[:16] + "...")
            console.print(f"  • {nick} ({ed_pub[:24]}...)")
    
    # Show inbox count
    if inbox:
        console.print(f"\n[bold]Inbox:[/bold] {len(inbox)} messages")
    
    # Show chat files
    chats = list(storage.chats_dir.glob("*.json"))
    if chats:
        console.print(f"\n[bold]Chat History:[/bold]")
        for chat_file in sorted(chats)[:10]:
            match_id = chat_file.stem
            messages = storage.get_chat(match_id)
            console.print(f"  • {match_id}: {len(messages)} messages")
    
    return 0
