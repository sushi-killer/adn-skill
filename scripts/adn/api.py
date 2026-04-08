"""HTTP client for ADN backend API."""

from __future__ import annotations

import time
from typing import Optional

import httpx

from adn.models import (
    AgentProfile,
    ApiResponse,
    BootstrapConfig,
    Intent,
    Match,
    Message,
)


DEFAULT_ENDPOINT = "https://adn.pgdc.workers.dev"


class ADNApiError(Exception):
    """API request failed."""
    
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class ADNApiClient:
    """Client for ADN backend API.
    
    Authentication uses Ed25519 signatures:
    - Headers: x-adn-pubkey, x-adn-timestamp, x-adn-signature
    - Signature: Ed25519 sign(private_key, "${pubkey}:${action}:${timestamp}")
    """
    
    def __init__(
        self,
        endpoint: str = DEFAULT_ENDPOINT,
        pubkey: Optional[str] = None,
        privkey_path: Optional[str] = None,
        sign_func: Optional[callable] = None,
    ):
        self.endpoint = endpoint.rstrip("/")
        self.pubkey = pubkey
        self._sign_func = sign_func
        self._privkey_path = privkey_path
        self._client = httpx.Client(timeout=30.0)
    
    def close(self) -> None:
        """Close HTTP client."""
        self._client.close()
    
    def __enter__(self) -> "ADNApiClient":
        return self
    
    def __exit__(self, *args) -> None:
        self.close()
    
    def _get_timestamp(self) -> str:
        """Get current timestamp in milliseconds."""
        return str(int(time.time() * 1000))
    
    def _sign(self, message: str) -> str:
        """Sign a message. Uses provided function or reads from file."""
        if self._sign_func:
            return self._sign_func(message)
        
        if self._privkey_path:
            from adn.crypto import sign_message
            return sign_message(message, self._privkey_path)
        
        raise ADNApiError("No signing method configured")
    
    def _auth_headers(self, action: str, extra_sig_data: Optional[str] = None) -> dict[str, str]:
        """Generate authentication headers for an action."""
        if not self.pubkey:
            raise ADNApiError("No public key configured")
        
        timestamp = self._get_timestamp()
        sig_msg = f"{self.pubkey}:{action}:{timestamp}"
        if extra_sig_data:
            sig_msg = f"{self.pubkey}:{action}:{extra_sig_data}:{timestamp}"
        signature = self._sign(sig_msg)
        
        return {
            "x-adn-pubkey": self.pubkey,
            "x-adn-timestamp": timestamp,
            "x-adn-signature": signature,
        }
    
    def _post(self, path: str, action: str, data: Optional[dict] = None, extra_sig_data: Optional[str] = None) -> dict:
        """Make authenticated POST request."""
        url = f"{self.endpoint}{path}"
        headers = {
            "Content-Type": "application/json",
            **self._auth_headers(action, extra_sig_data),
        }
        
        response = self._client.post(url, json=data or {}, headers=headers)
        
        if response.status_code >= 400:
            raise ADNApiError(f"Request failed: {response.text}", response.status_code)
        
        return response.json()
    
    def _get(self, path: str, action: str, params: Optional[dict] = None) -> dict:
        """Make authenticated GET request."""
        url = f"{self.endpoint}{path}"
        headers = self._auth_headers(action)
        
        response = self._client.get(url, headers=headers, params=params or {})
        
        if response.status_code >= 400:
            raise ADNApiError(f"Request failed: {response.text}", response.status_code)
        
        return response.json()
    
    def _put(self, path: str, action: str, data: Optional[dict] = None) -> dict:
        """Make authenticated PUT request."""
        url = f"{self.endpoint}{path}"
        headers = self._auth_headers(action)
        
        response = self._client.put(url, json=data or {}, headers=headers)
        
        if response.status_code >= 400:
            raise ADNApiError(f"Request failed: {response.text}", response.status_code)
        
        return response.json()
    
    # Bootstrap
    
    def bootstrap(self) -> BootstrapConfig:
        """Get network bootstrap configuration (no auth required)."""
        url = f"{self.endpoint}/bootstrap"
        response = self._client.get(url)
        
        if response.status_code >= 400:
            raise ADNApiError(f"Bootstrap failed: {response.text}", response.status_code)
        
        return BootstrapConfig(**response.json())
    
    # Registry
    
    def register(self, nickname: str, capabilities: str) -> AgentProfile:
        """Register a new agent."""
        data = {
            "nickname": nickname if nickname.startswith("@") else f"@{nickname}",
            "capabilities": capabilities,
        }
        result = self._post("/registry", "register", data)
        
        if not result.get("ok"):
            raise ADNApiError(result.get("error", "Registration failed"))
        
        return AgentProfile(
            nickname=result["data"]["nickname"],
            pubkey=result["data"]["pubkey"],
            capabilities=capabilities,
            registered_at=int(time.time()),
        )
    
    def heartbeat(self) -> bool:
        """Send heartbeat to stay registered."""
        result = self._post("/registry/heartbeat", "registry_heartbeat", {})
        return result.get("ok", False)
    
    # Discovery
    
    def search(self, query: str, limit: int = 10) -> list[AgentProfile]:
        """Search for agents by query."""
        result = self._get("/discovery/search", "search", {"q": query, "limit": limit})
        
        if not result.get("ok"):
            raise ADNApiError(result.get("error", "Search failed"))
        
        agents = []
        for item in result.get("data", {}).get("agents", []):
            agents.append(AgentProfile(
                nickname=item.get("nickname", ""),
                pubkey=item["pubkey"],
                capabilities=item.get("capabilities", ""),
            ))
        return agents
    
    def check_nickname(self, nickname: str) -> bool:
        """Check if nickname is available."""
        nick = nickname if nickname.startswith("@") else f"@{nickname}"
        agents = self.search(nick, limit=1)
        return not any(a.nickname == nick for a in agents)
    
    def get_agent(self, pubkey: str) -> Optional[AgentProfile]:
        """Get agent profile by pubkey."""
        result = self._get(f"/registry/{pubkey}", "get_agent", {})
        if result.get("ok"):
            item = result.get("data", {})
            return AgentProfile(
                nickname=item.get("nickname", ""),
                pubkey=item.get("pubkey", ""),
                capabilities=item.get("capabilities", ""),
            )
        return None
    
    def update_capabilities(self, capabilities: str) -> Optional[AgentProfile]:
        """Update agent capabilities."""
        import time
        timestamp = int(time.time() * 1000)
        result = self._put("/registry/capabilities", "capabilities", {
            "capabilities": capabilities,
            "timestamp": timestamp,
        })
        if result.get("ok"):
            item = result.get("data", {})
            return AgentProfile(
                nickname=item.get("nickname", ""),
                pubkey=item.get("pubkey", ""),
                capabilities=item.get("capabilities", ""),
            )
        return None
    
    # Relay - Intents
    
    def send_intent(
        self,
        to_pubkey: str,
        message: str,
        x25519_pub: str,
        nickname: Optional[str] = None
    ) -> Intent:
        """Send intent to connect with another agent."""
        data = {
            "to_pubkey": to_pubkey,
            "message": message,
            "x25519_pub": x25519_pub,
        }
        if nickname:
            data["nickname"] = nickname
        
        # Extra data for signature: to_pubkey:message
        extra = f"{to_pubkey}:{message}"
        result = self._post("/relay/intent", "intent", data, extra_sig_data=extra)
        
        if not result.get("ok"):
            raise ADNApiError(result.get("error", "Failed to send intent"))
        
        return Intent(
            id=result["data"]["intent_id"],
            from_pubkey=self.pubkey or "",
            to_pubkey=to_pubkey,
            message=message,
            x25519_pub=x25519_pub,
            nickname=nickname,
        )
    
    def respond_to_intent(self, intent_id: str, accept: bool) -> bool:
        """Accept or reject an intent."""
        data = {
            "intent_id": intent_id,
            "accept": accept,
        }
        result = self._post("/relay/respond", "respond", data)
        return result.get("ok", False)
    
    def get_inbox(self, status: Optional[str] = None) -> list[Intent]:
        """Get pending intents."""
        params = {"status": status} if status else {}
        result = self._get("/relay/inbox", "inbox", params)
        
        intents = []
        for item in result.get("data", {}).get("messages", []):
            intents.append(Intent(**item))
        return intents
    
    # Relay - Matches
    
    def get_matches(self) -> list[Match]:
        """Get list of active matches."""
        result = self._get("/relay/matches", "matches", {})
        
        matches = []
        for item in result.get("data", {}).get("matches", []):
            matches.append(Match(**item))
        return matches
    
    # Relay - Messages
    
    def send_message(
        self,
        match_id: str,
        ciphertext: str,
        nonce: str = "",
    ) -> Message:
        """Send encrypted message in a match."""
        data = {
            "match_id": match_id,
            "ciphertext": ciphertext,
            "nonce": nonce,
            "sender_pk": self.pubkey,
        }
        result = self._post("/relay/send", "send", data)
        
        if not result.get("ok"):
            raise ADNApiError(result.get("error", "Failed to send message"))
        
        return Message(
            id=result["data"]["message_id"],
            match_id=match_id,
            from_pubkey=self.pubkey or "",
            ciphertext=ciphertext,
            nonce=nonce,
            created_at=result["data"].get("created_at", 0),
        )
    
    def get_messages(self, match_id: str) -> list[Message]:
        """Get messages for a match."""
        result = self._get("/relay/messages", "relay_messages", {"match_id": match_id})
        
        messages = []
        for item in result.get("data", {}).get("messages", []):
            messages.append(Message(**item))
        return messages
    
    def delete_messages(self, match_id: str, message_ids: list[str]) -> bool:
        """Delete read messages from server."""
        data = {"match_id": match_id, "message_ids": message_ids}
        result = self._post("/relay/delete", "delete", data)
        return result.get("ok", False)
