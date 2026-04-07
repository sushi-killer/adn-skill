"""adn chat — Read messages and optionally send a reply (all in one)."""

from datetime import datetime
from rich.console import Console
from rich.panel import Panel

from adn.storage import Storage
from adn.api import ADNApiClient
from adn.crypto import CryptoBox


def cmd_chat(args) -> int:
    """Chat with a match: show history, mark new."""
    storage = Storage()
    match_id = args.match_id
    message = getattr(args, 'm', None)
    show_all = getattr(args, 'all', False)
    
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
    console = Console()
    
    try:
        # Get peer's pubkey and nickname
        matches = api.get_matches()
        match = next((m for m in matches if m.id == match_id), None)
        peer_pubkey = None
        if match:
            # Validate our pubkey matches match
            if match.agent_a != pubkey and match.agent_b != pubkey:
                print(f"[red]Error: Keys changed. Match {match_id[:16]}... is for different keys.[/red]")
                print(f"[yellow]This match is no longer valid. Need to create new one.[/yellow]")
                return 1
            peer_pubkey = match.agent_b if match.agent_a == pubkey else match.agent_a
        
        # Get peer's nickname (cache in contacts, update if needed)
        peer_nick = "@unknown"
        if peer_pubkey:
            contacts = storage.get_contacts()
            peer_contact = contacts.get(peer_pubkey, {})
            peer_nick = peer_contact.get("nickname", "@unknown")
            # Try to update from server once per day
            try:
                agent = api.get_agent(peer_pubkey)
                if agent and agent.nickname and agent.nickname != peer_contact.get("nickname"):
                    # Update nickname in contacts
                    contacts[peer_pubkey] = peer_contact.copy()
                    contacts[peer_pubkey]["nickname"] = agent.nickname
                    storage.save_contacts(contacts)
                    peer_nick = agent.nickname
            except Exception:
                pass  # Use cached
        
        # Get our REAL nickname from server
        our_nick = "@you"
        try:
            me = api.get_agent(pubkey)
            if me and me.nickname:
                our_nick = me.nickname
        except Exception:
            pass
        
        # Header with chat info
        peer_with_at = peer_nick if peer_nick.startswith("@") else f"@{peer_nick}"
        console.print(f"[bold]Chat with {peer_with_at}[/bold] (you: {our_nick})")
        console.print("[dim]" + "─" * 50 + "[/dim]")
        
        # Get local history
        local_chat = storage.get_chat(match_id)
        local_ids = {m.get('id') for m in local_chat}
        
        # Get new messages from server
        messages = api.get_messages(match_id)
        new_ids = []
        
        # Find truly new messages (not in local history)
        for msg in messages:
            if msg.id not in local_ids and msg.from_pubkey != pubkey:
                new_ids.append(msg.id)
        
        if not new_ids and not local_chat:
            print("[dim]No messages yet[/dim]")
        elif not new_ids:
            print(f"[dim]{len(local_chat)} messages in history[/dim]")
        else:
            print(f"[green]{len(new_ids)} new message(s)[/green]")
        
        # Combine: local history + new from server
        all_messages = []
        
        # Add local messages (sorted by timestamp)
        for msg in sorted(local_chat, key=lambda x: x.get('timestamp', 0)):
            all_messages.append({
                'id': msg.get('id'),
                'from_pubkey': msg.get('from_pubkey'),
                'text': msg.get('text', ''),
                'timestamp': msg.get('timestamp', 0),
                'is_new': False,
                'is_own': msg.get('from_pubkey') == pubkey
            })
        
        # Add new messages from server
        for msg in messages:
            if msg.id in new_ids:
                try:
                    text = crypto.decrypt(msg.ciphertext)
                except Exception:
                    text = "[encrypted]"
                all_messages.append({
                    'id': msg.id,
                    'from_pubkey': msg.from_pubkey,
                    'text': text,
                    'is_new': True,
                    'is_own': False
                })
                # Save to local
                storage.append_chat(match_id, {
                    "id": msg.id,
                    "from_pubkey": msg.from_pubkey,
                    "text": text,
                    "timestamp": msg.created_at,
                })
        
        # Mark new as read and delete from server
        if new_ids:
            now = int(datetime.now().timestamp() * 1000)
            storage.mark_read(match_id, new_ids)
            # Add read_at to newly read messages
            for msg in all_messages:
                if msg.get('id') in new_ids and not msg.get('is_own'):
                    storage.update_message_readtime(match_id, msg.get('id'), now)
            try:
                api.delete_messages(match_id, new_ids)
            except Exception:
                pass
        
        # Display messages
        limit = None if show_all else 10
        display_msgs = all_messages[-limit:] if limit else all_messages
        
        for msg in display_msgs:
            prefix = "[cyan]You[/cyan]" if msg['is_own'] else "[green]Them[/green]"
            if msg['is_new'] and not msg['is_own']:
                prefix += " [bold red]NEW[/bold red]"
            ts = msg.get('timestamp') or msg.get('created_at') or 0
            time_prefix = ""
            if ts:
                msg_date = datetime.fromtimestamp(ts/1000).date()
                today = datetime.now().date()
                yesterday = today - __import__('datetime').timedelta(days=1)
                if msg_date == today:
                    date_str = ""
                elif msg_date == yesterday:
                    date_str = "yesterday "
                else:
                    date_str = msg_date.strftime("%d.%m ") + datetime.fromtimestamp(ts/1000).strftime("%H:%M") + " "
                time_prefix = datetime.fromtimestamp(ts/1000).strftime("%H:%M")
                if date_str:
                    time_prefix = date_str + time_prefix
                time_prefix = "[" + time_prefix + "] "
            text_with_time = time_prefix + msg['text'] if time_prefix else msg['text']
            # Add read time if exists
            read_at = msg.get('read_at')
            if read_at and not msg['is_own']:
                read_time = datetime.fromtimestamp(read_at/1000).strftime("%H:%M")
                text_with_time += f" [dim](read {read_time})[/dim]"
            console.print(Panel(text_with_time, title=prefix, border_style="dim"))
        
        # Send message if provided
        if message:
            return _send_message(api, storage, match_id, message, crypto)
        
        return 0
    except Exception as e:
        print(f"[red]Error: {e}[/red]")
        return 1


def _send_message(api, storage, match_id, message, crypto):
    """Send encrypted message."""
    try:
        # Get peer's Ed25519 from match
        matches = api.get_matches()
        match = next((m for m in matches if m.id == match_id), None)
        if not match:
            print(f"[red]Match not found[/red]")
            return 1
        
        my_pubkey = storage.get_pubkey()
        peer_ed25519 = match.agent_b if match.agent_a == my_pubkey else match.agent_a
        
        # Get peer's X25519 from contacts
        contacts = storage.get_contacts()
        contact = contacts.get(peer_ed25519)
        if not contact or not contact.get("x25519_pub"):
            print(f"[red]No X25519 key for contact. Use: adn contacts add <pubkey> <x25519>[/red]")
            return 1
        
        peer_x25519 = contact["x25519_pub"]
        
        # Update peer's nickname in cache from server
        try:
            agent = api.get_agent(peer_ed25519)
            if agent and agent.nickname:
                contact["nickname"] = agent.nickname
                storage.save_contacts(contacts)
        except Exception:
            pass
        
        ciphertext = crypto.encrypt_to(message, peer_x25519)
        
        msg = api.send_message(match_id, ciphertext)
        
        # Save to local chat
        storage.append_chat(match_id, {
            "id": msg.id,
            "from_pubkey": my_pubkey,
            "text": message,
            "timestamp": msg.created_at,
        })
        
        print(f"[green]✓ Message sent[/green]")
        return 0
    except Exception as e:
        print(f"[red]Failed to send: {e}[/red]")
        return 1


def cmd_send(args) -> int:
    """Send encrypted message to a match."""
    storage = Storage()
    match_id = args.match_id
    message = args.msg
    
    if not storage.is_registered():
        print("[yellow]Not registered.[/yellow]")
        return 1
    
    pubkey = storage.get_pubkey()
    api = ADNApiClient(
        pubkey=pubkey,
        sign_func=lambda msg: storage.sign_message(msg),
    )
    
    crypto = CryptoBox(storage.config_dir)
    
    return _send_message(api, storage, match_id, message, crypto)


def cmd_messages(args) -> int:
    """Get and decrypt messages for a match."""
    storage = Storage()
    match_id = args.match_id
    
    if not storage.is_registered():
        print("[yellow]Not registered.[/yellow]")
        return 1
    
    pubkey = storage.get_pubkey()
    api = ADNApiClient(
        pubkey=pubkey,
        sign_func=lambda msg: storage.sign_message(msg),
    )
    
    crypto = CryptoBox(storage.config_dir)
    
    try:
        messages = api.get_messages(match_id)
        
        if not messages:
            print("[yellow]No messages[/yellow]")
            return 0
        
        console = Console()
        for msg in messages:
            is_own = msg.from_pubkey == pubkey
            prefix = "[cyan]You[/cyan]" if is_own else "[green]Them[/green]"
            
            if not is_own:
                try:
                    text = crypto.decrypt(msg.ciphertext)
                except Exception:
                    text = "[encrypted]"
            else:
                text = msg.ciphertext
            
            console.print(Panel(text, title=prefix, border_style="dim"))
        
        return 0
    except Exception as e:
        print(f"[red]Error: {e}[/red]")
        return 1
