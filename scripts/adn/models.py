"""Pydantic models for ADN."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class AgentProfile(BaseModel):
    """Agent registration profile."""
    
    nickname: str = Field(..., description="Unique agent nickname")
    pubkey: str = Field(..., description="Ed25519 public key (base64url)")
    x25519_pub: Optional[str] = Field(None, description="X25519 public key (base64url)")
    capabilities: list[str] = Field(default_factory=list, description="Agent capabilities")
    registered_at: int = Field(default_factory=int, description="Unix timestamp")
    
    @field_validator("nickname")
    @classmethod
    def validate_nickname(cls, v: str) -> str:
        if not v.startswith("@"):
            v = f"@{v}"
        return v


class Intent(BaseModel):
    """Intent to connect with another agent."""
    
    id: str = Field(..., description="Intent ID")
    from_pubkey: str = Field(..., description="Sender Ed25519 pubkey")
    to_pubkey: Optional[str] = Field(None, description="Recipient Ed25519 pubkey")
    message: str = Field(default="", description="Intro message")
    x25519_pub: Optional[str] = Field(None, description="Sender's X25519 pubkey for E2E")
    nickname: Optional[str] = Field(None, description="Sender's nickname")
    status: str = Field(default="pending", description="pending/delivered/accepted/rejected")
    created_at: int = Field(default_factory=lambda: int(datetime.now().timestamp() * 1000))
    
    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        allowed = {"pending", "delivered", "accepted", "rejected"}
        if v not in allowed:
            raise ValueError(f"Status must be one of: {allowed}")
        return v


class Match(BaseModel):
    """Mutual connection between two agents."""
    
    id: str = Field(..., description="Match ID")
    agent_a: str = Field(..., description="First agent pubkey")
    agent_b: str = Field(..., description="Second agent pubkey")
    created_at: int = Field(default_factory=lambda: int(datetime.now().timestamp() * 1000))
    
    def get_peer(self, my_pubkey: str) -> str:
        """Get the other agent's pubkey."""
        if self.agent_a == my_pubkey:
            return self.agent_b
        return self.agent_a


class Message(BaseModel):
    """Encrypted message in a match."""
    
    id: str = Field(..., description="Message ID")
    match_id: str = Field(..., description="Match ID")
    from_pubkey: str = Field(..., description="Sender pubkey")
    ciphertext: str = Field(..., description="Encrypted message (base64)")
    nonce: str = Field(default="", description="Nonce if needed")
    sender_pk: Optional[str] = Field(None, description="Sender's pubkey for routing")
    status: str = Field(default="sent", description="sent/delivered/read")
    created_at: int = Field(default_factory=lambda: int(datetime.now().timestamp() * 1000))
    # Decrypted text (not from API)
    text: Optional[str] = Field(None, exclude=True)


class ApiResponse(BaseModel):
    """Generic API response wrapper."""
    
    ok: bool = Field(..., description="Success flag")
    error: Optional[str] = Field(None, description="Error message")
    data: Optional[dict] = Field(None, description="Response data")


class BootstrapConfig(BaseModel):
    """Network bootstrap configuration."""
    
    endpoint: str = Field(..., description="API endpoint URL")
    version: str = Field(..., description="Protocol version")
    ttl_seconds: int = Field(..., description="Heartbeat TTL in seconds")
