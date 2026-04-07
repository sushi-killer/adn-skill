"""Local storage for ADN keys and data."""

from __future__ import annotations

import json
import time as time_module
from pathlib import Path
from typing import Optional

from adn.models import AgentProfile


class Storage:
    """Local storage manager for ADN."""
    
    DEFAULT_DIR = Path.home() / ".adn"
    
    def __init__(self, config_dir: Optional[Path] = None):
        self.config_dir = config_dir or self.DEFAULT_DIR
        self.key_pub_path = self.config_dir / "key_pub"
        self.key_path = self.config_dir / "key"
        self.x25519_pub_path = self.config_dir / "x25519_pub"
        self.x25519_priv_path = self.config_dir / "x25519_priv"
        self.config_path = self.config_dir / "config.json"
        self.contacts_path = self.config_dir / "contacts.json"
        self.inbox_path = self.config_dir / "inbox.json"
        self.chats_dir = self.config_dir / "chats"
    
    def ensure_config_dir(self) -> None:
        """Create config directory if it doesn't exist."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.chats_dir.mkdir(parents=True, exist_ok=True)
    
    # Key file operations
    
    def get_pubkey(self) -> Optional[str]:
        """Get Ed25519 public key."""
        if self.key_pub_path.exists():
            return self.key_pub_path.read_text().strip()
        return None
    
    def get_privkey(self) -> Optional[str]:
        """Get Ed25519 private key."""
        if self.key_path.exists():
            return self.key_path.read_text().strip()
        return None
    
    def get_x25519_pub(self) -> Optional[str]:
        """Get X25519 public key."""
        if self.x25519_pub_path.exists():
            return self.x25519_pub_path.read_text().strip()
        return None
    
    def get_x25519_priv(self) -> Optional[str]:
        """Get X25519 private key."""
        if self.x25519_priv_path.exists():
            return self.x25519_priv_path.read_text().strip()
        return None
    
    def has_keys(self) -> bool:
        """Check if keys exist."""
        return (
            self.key_pub_path.exists() and 
            self.key_path.exists() and
            self.x25519_pub_path.exists() and 
            self.x25519_priv_path.exists()
        )
    
    def save_keys(
        self,
        ed25519_pub: str,
        ed25519_priv: str,
        x25519_pub: str,
        x25519_priv: str
    ) -> None:
        """Save all keys to files."""
        self.ensure_config_dir()
        self.key_pub_path.write_text(ed25519_pub)
        self.key_path.write_text(ed25519_priv)
        self.x25519_pub_path.write_text(x25519_pub)
        self.x25519_priv_path.write_text(x25519_priv)
        # Secure permissions
        self.key_path.chmod(0o600)
        self.x25519_priv_path.chmod(0o600)
    
    # Config operations
    
    def get_config(self) -> Optional[AgentProfile]:
        """Load registration config."""
        if self.config_path.exists():
            try:
                data = json.loads(self.config_path.read_text())
                return AgentProfile(**data)
            except (json.JSONDecodeError, ValueError):
                return None
        return None
    
    def save_config(self, profile: AgentProfile) -> None:
        """Save registration config."""
        self.ensure_config_dir()
        self.config_path.write_text(profile.model_dump_json(indent=2))
    
    def is_registered(self) -> bool:
        """Check if agent is registered."""
        config = self.get_config()
        return config is not None and config.pubkey is not None
    
    def get_nickname(self) -> Optional[str]:
        """Get our nickname."""
        config = self.get_config()
        if config:
            return config.nickname
        return None
    
    # Contacts operations
    
    def get_contacts(self) -> dict[str, dict]:
        """Load contacts dictionary.
        
        Returns:
            {ed25519_pub: {x25519_pub, nickname, added_at}}
        """
        if self.contacts_path.exists():
            try:
                return json.loads(self.contacts_path.read_text())
            except json.JSONDecodeError:
                return {}
        return {}
    
    def save_contacts(self, contacts: dict[str, dict]) -> None:
        """Save contacts dictionary."""
        self.ensure_config_dir()
        self.contacts_path.write_text(json.dumps(contacts, indent=2))
    
    def add_contact(self, ed25519_pub: str, x25519_pub: str, nickname: Optional[str] = None) -> None:
        """Add or update a contact."""
        contacts = self.get_contacts()
        contacts[ed25519_pub] = {
            "x25519_pub": x25519_pub,
            "nickname": nickname,
            "added_at": int(time_module.time())
        }
        self.save_contacts(contacts)
    
    def sign_message(self, message: str) -> str:
        """Sign a message with Ed25519 private key.
        
        Args:
            message: Message to sign
            
        Returns:
            Base64 signature
        """
        from adn.crypto import sign_message as crypto_sign
        return crypto_sign(message, str(self.key_path))
    
    def get_contact_x25519(self, ed25519_pub: str) -> Optional[str]:
        """Get X25519 key for a contact."""
        contacts = self.get_contacts()
        return contacts.get(ed25519_pub, {}).get("x25519_pub")
    
    # Inbox operations
    
    def get_inbox(self) -> list[dict]:
        """Load saved inbox messages."""
        if self.inbox_path.exists():
            try:
                return json.loads(self.inbox_path.read_text())
            except json.JSONDecodeError:
                return []
        return []
    
    def save_inbox(self, messages: list[dict]) -> None:
        """Save inbox messages (merge with existing)."""
        self.ensure_config_dir()
        existing = self.get_inbox()
        # Merge, preferring new data
        seen_ids = {m.get("id") for m in existing}
        for msg in messages:
            if msg.get("id") not in seen_ids:
                existing.append(msg)
        self.inbox_path.write_text(json.dumps(existing, indent=2))
    
    # Chat history operations
    
    def get_chat_path(self, match_id: str) -> Path:
        """Get path for chat history file."""
        return self.chats_dir / f"{match_id}.json"
    
    def get_chat(self, match_id: str) -> list[dict]:
        """Load chat history for a match."""
        path = self.get_chat_path(match_id)
        if path.exists():
            try:
                return json.loads(path.read_text())
            except json.JSONDecodeError:
                return []
        return []
    
    def append_chat(self, match_id: str, message: dict) -> None:
        """Append message to chat history."""
        chat = self.get_chat(match_id)
        chat.append(message)
        path = self.get_chat_path(match_id)
        path.write_text(json.dumps(chat, indent=2))
    
    def get_match_x25519(self, peer_pubkey: str) -> Optional[str]:
        """Get peer's X25519 key for encryption."""
        return self.get_contact_x25519(peer_pubkey)
    
    def save_chat(self, match_id: str, messages: list[dict]) -> None:
        """Save complete chat history for a match."""
        self.ensure_config_dir()
        path = self.get_chat_path(match_id)
        path.write_text(json.dumps(messages, indent=2))
    
    # Track read messages per match
    def get_read_ids_path(self, match_id: str) -> Path:
        """Get path for read message IDs file."""
        return self.chats_dir / f"{match_id}_read.json"
    
    def get_read_ids(self, match_id: str) -> set:
        """Get set of read message IDs for a match."""
        path = self.get_read_ids_path(match_id)
        if path.exists():
            try:
                return set(json.loads(path.read_text()))
            except json.JSONDecodeError:
                return set()
        return set()
    
    def mark_read(self, match_id: str, msg_ids: list[str]) -> None:
        """Mark message IDs as read."""
        read_ids = self.get_read_ids(match_id)
        read_ids.update(msg_ids)
        path = self.get_read_ids_path(match_id)
        path.write_text(json.dumps(list(read_ids)))
    
    def update_message_readtime(self, match_id: str, msg_id: str, read_at: int) -> None:
        """Update read time for a message."""
        chat = self.get_chat(match_id)
        for msg in chat:
            if msg.get('id') == msg_id:
                msg['read_at'] = read_at
                break
        path = self.get_chat_path(match_id)
        path.write_text(json.dumps(chat))
