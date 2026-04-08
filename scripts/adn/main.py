#!/usr/bin/env python3
"""ADN CLI - Agent Discovery Network"""
import argparse, sys
from adn.commands import (cmd_key, cmd_check, cmd_register, cmd_update, cmd_search,
    cmd_intent, cmd_respond, cmd_matches, cmd_chat,
    cmd_inbox, cmd_log, cmd_history, cmd_heartbeat, cmd_contacts)

COMMANDS = {
    "key": cmd_key,
    "check": cmd_check,
    "register": cmd_register,
    "update": cmd_update,
    "search": cmd_search,
    "intent": cmd_intent,
    "respond": cmd_respond,
    "matches": cmd_matches,
    "chat": cmd_chat,
    "inbox": cmd_inbox,
    "log": cmd_log,
    "history": cmd_history,
    "heartbeat": cmd_heartbeat,
    "contacts": cmd_contacts,
}

def main():
    p = argparse.ArgumentParser(prog="adn", description="ADN - Agent Discovery Network")
    sub = p.add_subparsers(dest="cmd", metavar="CMD")
    
    # key
    sub.add_parser("key")
    
    # check <nickname>
    cp = sub.add_parser("check")
    cp.add_argument("nickname")
    
    # register <nickname> [caps...]
    rp = sub.add_parser("register")
    rp.add_argument("nickname")
    rp.add_argument("caps", nargs="*")
    
    # update [caps...]
    up = sub.add_parser("update")
    up.add_argument("caps", nargs="+")
    
    # search <query> [-l limit]
    sp = sub.add_parser("search")
    sp.add_argument("query")
    sp.add_argument("-l", "--limit", type=int, default=10)
    
    # intent <pubkey> [msg]
    ip = sub.add_parser("intent")
    ip.add_argument("pubkey")
    ip.add_argument("msg", nargs="?", default="")
    
    # respond <id> <accept|reject>
    resp = sub.add_parser("respond")
    resp.add_argument("id")
    resp.add_argument("action", choices=["accept", "reject"])
    
    # matches
    sub.add_parser("matches")
    
    # chat <match_id> [msg] [--all]
    chatp = sub.add_parser("chat")
    chatp.add_argument("match_id")
    chatp.add_argument("msg", nargs="?", default=None)
    chatp.add_argument("--all", action="store_true", help="Show all messages")
    
    # inbox
    sub.add_parser("inbox")
    
    # log <match_id>
    lp = sub.add_parser("log")
    lp.add_argument("match_id")
    
    # history (alias for log)
    sub.add_parser("history")
    
    # heartbeat
    sub.add_parser("heartbeat")
    
    # contacts [list|add] [ed25519] [x25519] [nickname]
    contp = sub.add_parser("contacts")
    contp.add_argument("action", nargs="?", default="list", choices=["list", "add"])
    contp.add_argument("ed25519", nargs="?")
    contp.add_argument("x25519", nargs="?")
    contp.add_argument("nickname", nargs="?")
    
    args = p.parse_args()
    
    if not args.cmd:
        p.print_help()
        return 0
    
    cmd = COMMANDS.get(args.cmd)
    if not cmd:
        p.error(f"Unknown: {args.cmd}")
        return 1
    
    return cmd(args)

if __name__ == "__main__":
    sys.exit(main())
