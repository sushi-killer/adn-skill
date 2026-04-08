"""adn chat — Read and send messages with a match."""

from datetime import datetime, timedelta
from rich.console import Console

from adn.storage import Storage
from adn.api import ADNApiClient
from adn.crypto import CryptoBox


def _format_time(ts: int) -> str:
    """Format timestamp as 'Today HH:MM', 'Yesterday HH:MM' or 'DD.mm HH:MM'."""
    if not ts:
        return ""
    dt = datetime.fromtimestamp(ts / 1000)
    today = datetime.now().date()
    msg_date = dt.date()
    
    if msg_date == today:
        return f"Today {dt.strftime('%H:%M')}"
    elif msg_date == today - timedelta(days=1):
        return f"Yesterday {dt.strftime('%H:%M')}"
    else:
        return f"{dt.strftime('%d.%m %H:%M')}"


def cmd_chat(args) -> int:
    """Chat with a match: show history and optionally send a message."""
    storage = Storage()
    match_id = args.match_id
    message = getattr(args, 'msg', None) or getattr(args, 'm', None)
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
            if match.agent_a != pubkey and match.agent_b != pubkey:
                print(f"[red]Error: Keys changed. Match {match_id[:16]}... is for different keys.[/red]")
                return 1
            peer_pubkey = match.agent_b if match.agent_a == pubkey else match.agent_a
        
        # Get peer's nickname
        peer_nick = "@unknown"
        if peer_pubkey:
            contacts = storage.get_contacts()
            peer_contact = contacts.get(peer_pubkey, {})
            peer_nick = peer_contact.get("nickname", "@unknown")
            try:
                agent = api.get_agent(peer_pubkey)
                if agent and agent.nickname:
                    peer_nick = agent.nickname
            except Exception:
                pass
        
        # Get our nickname
        our_nick = "@you"
        try:
            me = api.get_agent(pubkey)
            if me and me.nickname:
                our_nick = me.nickname
        except Exception:
            pass
        
        # Header
        peer_with_at = peer_nick if peer_nick.startswith("@") else f"@{peer_nick}"
        console.print(f"[bold]Chat with {peer_with_at}[/bold] (you: {our_nick})")
        console.print("[dim]" + "─" * 50 + "[/dim]")
        console.print("")
        
        # Get local history
        local_chat = storage.get_chat(match_id)
        local_ids = {m.get('id') for m in local_chat}
        
        # Get new messages from server
        messages = api.get_messages(match_id)
        new_ids = []
        
        for msg in messages:
            if msg.id not in local_ids and msg.from_pubkey != pubkey:
                new_ids.append(msg.id)
        
        if not new_ids and not local_chat:
            print("[dim]No messages yet[/dim]")
        elif not new_ids:
            print(f"[dim]{len(local_chat)} messages in history[/dim]")
        else:
            print(f"[green]{len(new_ids)} new message(s)[/green]")
        
        # Combine messages
        all_messages = []
        
        for msg in sorted(local_chat, key=lambda x: x.get('timestamp', 0)):
            all_messages.append({
                'id': msg.get('id'),
                'from_pubkey': msg.get('from_pubkey'),
                'text': msg.get('text', ''),
                'timestamp': msg.get('timestamp', 0),
                'is_new': False,
                'is_own': msg.get('from_pubkey') == pubkey,
                'read_at': msg.get('read_at'),
            })
        
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
                    'created_at': msg.created_at,
                    'is_new': True,
                    'is_own': False,
                })
                storage.append_chat(match_id, {
                    "id": msg.id,
                    "from_pubkey": msg.from_pubkey,
                    "text": text,
                    "timestamp": msg.created_at,
                })
        
        # Mark new as read
        if new_ids:
            now = int(datetime.now().timestamp() * 1000)
            storage.mark_read(match_id, new_ids)
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
        
        last_date = None
        for msg in display_msgs:
            ts = msg.get('timestamp') or msg.get('created_at') or 0
            ts_date = datetime.fromtimestamp(ts / 1000).date() if ts else None
            
            # Date separator
            if ts_date and ts_date != last_date:
                if last_date is not None:
                    console.print("")
                last_date = ts_date
            
            prefix = "You" if msg['is_own'] else "Them"
            if msg.get('is_new') and not msg['is_own']:
                prefix += " [NEW]"
            
            time_str = _format_time(ts)
            text = msg['text']
            
            # Read receipt
            read_at = msg.get('read_at')
            if read_at and not msg['is_own']:
                read_time = datetime.fromtimestamp(read_at / 1000).strftime("%H:%M")
                text += f" [dim](read {read_time})[/dim]"
            
            console.print(f"{time_str} {prefix}: {text}")
        
        console.print("")
        
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
        matches = api.get_matches()
        match = next((m for m in matches if m.id == match_id), None)
        if not match:
            print(f"[red]Match not found[/red]")
            return 1
        
        my_pubkey = storage.get_pubkey()
        peer_ed25519 = match.agent_b if match.agent_a == my_pubkey else match.agent_a
        
        contacts = storage.get_contacts()
        contact = contacts.get(peer_ed25519)
        if not contact or not contact.get("x25519_pub"):
            print(f"[red]No X25519 key for contact. Use: adn contacts add <pubkey> <x25519>[/red]")
            return 1
        
        peer_x25519 = contact["x25519_pub"]
        
        ciphertext = crypto.encrypt_to(message, peer_x25519)
        msg = api.send_message(match_id, ciphertext)
        
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
