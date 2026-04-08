"""ADN CLI commands."""

from adn.commands.key import cmd_key
from adn.commands.register import cmd_register, cmd_update
from adn.commands.search import cmd_search
from adn.commands.check import cmd_check
from adn.commands.intent import cmd_intent
from adn.commands.respond import cmd_respond
from adn.commands.matches import cmd_matches
from adn.commands.chat import cmd_chat
from adn.commands.inbox import cmd_inbox
from adn.commands.log import cmd_log, cmd_history
from adn.commands.heartbeat import cmd_heartbeat
from adn.commands.contacts import cmd_contacts

__all__ = [
    "cmd_key",
    "cmd_register",
    "cmd_update", 
    "cmd_search",
    "cmd_check",
    "cmd_intent",
    "cmd_respond",
    "cmd_matches",
    "cmd_chat",
    "cmd_inbox",
    "cmd_log",
    "cmd_history",
    "cmd_heartbeat",
    "cmd_contacts",
]
