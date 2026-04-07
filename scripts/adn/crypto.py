"""Crypto operations using libsodium via Node.js subprocess.

ADN uses:
- Ed25519 for signing/authentication
- X25519 for E2E encryption (crypto_box_seal)
"""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from adn.models import Message


# Node.js crypto script template
ENCRYPT_SCRIPT = """
const sodium = require('libsodium-wrappers');
const fs = require('fs');

async function main() {{
    await sodium.ready;
    
    const recipientPk = sodium.from_base64('{recipient_x25519}');
    const msg = `{message}`;
    
    const sealed = sodium.crypto_box_seal(msg, recipientPk);
    console.log(JSON.stringify({{
        ciphertext: sodium.to_base64(sealed)
    }}));
}}

main().catch(e => {{ console.error(e.message); process.exit(1); }});
"""

DECRYPT_SCRIPT = """
const sodium = require('libsodium-wrappers');
const fs = require('fs');

async function main() {{
    await sodium.ready;
    
    const ourPriv = fs.readFileSync('{x25519_priv}', 'utf8').trim();
    const ourPub = fs.readFileSync('{x25519_pub}', 'utf8').trim();
    const sealed = sodium.from_base64('{ciphertext}');
    
    try {{
        const plaintext = sodium.crypto_box_seal_open(sealed, sodium.from_base64(ourPub), sodium.from_base64(ourPriv));
        console.log(sodium.to_string(plaintext));
    }} catch(e) {{
        console.log('[encrypted]');
    }}
}}

main().catch(e => {{ console.error(e.message); process.exit(1); }});
"""

GENERATE_KEYS_SCRIPT = r"""
const sodium = require('libsodium-wrappers');

async function main() {
    await sodium.ready;
    
    const ed25519 = sodium.crypto_sign_keypair();
    const x25519 = sodium.crypto_box_keypair();
    
    console.log(JSON.stringify({
        ed25519_pub: sodium.to_base64(ed25519.publicKey),
        ed25519_priv: sodium.to_base64(ed25519.privateKey),
        x25519_pub: sodium.to_base64(x25519.publicKey),
        x25519_priv: sodium.to_base64(x25519.privateKey)
    }));
}

main().catch(e => { console.error(e.message); process.exit(1); });
"""

SIGN_SCRIPT = """
const sodium = require('libsodium-wrappers');
const fs = require('fs');

async function main() {{
    await sodium.ready;
    
    const priv = fs.readFileSync('{key_priv}', 'utf8').trim();
    const msg = '{message}';
    
    const sig = sodium.crypto_sign_detached(msg, sodium.from_base64(priv));
    console.log(sodium.to_base64(sig));
}}

main().catch(e => {{ console.error(e.message); process.exit(1); }});
"""


class CryptoError(Exception):
    """Crypto operation failed."""
    pass


def _run_node(script: str) -> str:
    """Run Node.js script and return stdout."""
    try:
        result = subprocess.run(
            ["node", "-e", script],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            raise CryptoError(f"Node.js error: {result.stderr}")
        return result.stdout.strip()
    except FileNotFoundError:
        raise CryptoError("Node.js not found. Install Node.js to use crypto features.")
    except subprocess.TimeoutExpired:
        raise CryptoError("Crypto operation timed out")


def generate_keypair() -> dict[str, str]:
    """Generate Ed25519 and X25519 keypairs.
    
    Returns:
        dict with ed25519_pub, ed25519_priv, x25519_pub, x25519_priv
    """
    result = _run_node(GENERATE_KEYS_SCRIPT)
    try:
        return json.loads(result)
    except json.JSONDecodeError:
        raise CryptoError(f"Invalid keypair response: {result}")


def encrypt_message(message: str, recipient_x25519_pub: str) -> str:
    """Encrypt message using crypto_box_seal.
    
    Args:
        message: Plaintext message
        recipient_x25519_pub: Recipient's X25519 public key (base64)
    
    Returns:
        Encrypted ciphertext (base64)
    """
    # Escape backticks and special chars for shell
    safe_message = message.replace("`", "\\`").replace("$", "\\$").replace("\\", "\\\\")
    
    script = ENCRYPT_SCRIPT.format(
        recipient_x25519=recipient_x25519_pub,
        message=safe_message
    )
    result = _run_node(script)
    try:
        data = json.loads(result)
        return data["ciphertext"]
    except (json.JSONDecodeError, KeyError):
        raise CryptoError(f"Invalid encrypt response: {result}")


def decrypt_message(ciphertext: str, x25519_priv_path: str, x25519_pub_path: str) -> str:
    """Decrypt message using crypto_box_seal_open.
    
    Args:
        ciphertext: Encrypted message (base64)
        x25519_priv_path: Path to X25519 private key file
        x25519_pub_path: Path to X25519 public key file
    
    Returns:
        Decrypted plaintext or "[encrypted]" if decryption fails
    """
    script = DECRYPT_SCRIPT.format(
        x25519_priv=x25519_priv_path,
        x25519_pub=x25519_pub_path,
        ciphertext=ciphertext
    )
    return _run_node(script)


def sign_message(message: str, ed25519_priv_path: str) -> str:
    """Sign a message with Ed25519.
    
    Args:
        message: Message to sign
        ed25519_priv_path: Path to Ed25519 private key file
    
    Returns:
        Ed25519 signature (base64)
    """
    safe_message = message.replace("`", "\\`").replace("$", "\\$").replace("\\", "\\\\")
    script = SIGN_SCRIPT.format(
        key_priv=ed25519_priv_path,
        message=safe_message
    )
    return _run_node(script)


class CryptoBox:
    """High-level crypto operations with stored key paths."""
    
    def __init__(self, config_dir: Path):
        self.config_dir = config_dir
        self.key_path = config_dir / "key"
        self.key_pub_path = config_dir / "key_pub"
        self.x25519_priv_path = config_dir / "x25519_priv"
        self.x25519_pub_path = config_dir / "x25519_pub"
    
    def encrypt_to(self, message: str, recipient_x25519_pub: str) -> str:
        """Encrypt message for recipient."""
        return encrypt_message(message, recipient_x25519_pub)
    
    def decrypt(self, ciphertext: str) -> str:
        """Decrypt message for ourselves."""
        return decrypt_message(
            ciphertext,
            str(self.x25519_priv_path),
            str(self.x25519_pub_path)
        )
    
    def sign(self, message: str) -> str:
        """Sign a message."""
        return sign_message(message, str(self.key_path))
    
    def encrypt_for_match(self, message: str, match_id: str, get_peer_key: callable) -> str:
        """Encrypt message for a match.
        
        Args:
            message: Plaintext message
            match_id: Match ID (unused, for API routing)
            get_peer_key: Callback to get peer's X25519 pubkey
            
        Returns:
            Encrypted ciphertext (base64)
        """
        peer_x25519 = get_peer_key(match_id)
        if not peer_x25519:
            raise CryptoError(f"No X25519 key for match {match_id}")
        return encrypt_message(message, peer_x25519)
