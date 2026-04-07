# Changelog

## [1.0.0] - 2026-04-08

### Added
- Python CLI v2.0 with modular commands
- E2E encryption via libsodium (crypto_box_seal)
- Timestamps from server in chat
- Smart dates (today/yesterday/dd.mm)
- Real nicknames from server in chat header
- Match pubkey validation
- Local message storage in ~/.adn/chats/
- Commands: key, register, search, inbox, intent, respond, matches, chat, send, messages, contacts, heartbeat

### Architecture
- Cloudflare Workers backend
- D1 SQLite database
- KV for session state
- R2 for encrypted blobs
