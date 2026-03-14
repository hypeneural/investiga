"""Investiga CLI Entrypoint."""

import argparse
import sys

from investiga_cli.commands.doctor import run_doctor
from investiga_cli.commands.ops import inspect_dlq, list_blocked, resume_session


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Investiga Tijucas Admin CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Doctor
    subparsers.add_parser("doctor", help="Run system diagnostics (PG, RabbitMQ, Redis, Env)")
    
    # Ops: list-blocked
    subparsers.add_parser("list-blocked", help="List all blocked source sessions (e.g., pending CAPTCHAs)")
    
    # Ops: resume-session
    resume_parser = subparsers.add_parser("resume-session", help="Resume a blocked session")
    resume_parser.add_argument("session_id", type=int, help="ID of the blocked session")
    
    # Ops: inspect-dlq
    dlq_parser = subparsers.add_parser("inspect-dlq", help="Inspect Dead Letter Queue")
    dlq_parser.add_argument("--queue", type=str, help="Filter by original queue name")
    dlq_parser.add_argument("--limit", type=int, default=20, help="Max letters to show")
    
    # Legacy Import placeholder
    subparsers.add_parser("import-legacy-json", help="Import legacy JSON datasets into PostgreSQL")

    return parser


def app() -> None:
    """Main CLI execution."""
    parser = create_parser()
    args = parser.parse_args()
    
    if args.command == "doctor":
        run_doctor()
    elif args.command == "list-blocked":
        list_blocked(args)
    elif args.command == "resume-session":
        resume_session(args)
    elif args.command == "inspect-dlq":
        inspect_dlq(args)
    elif args.command == "import-legacy-json":
        print("🚧 Legacy import job not implemented yet. (Phase 4)")
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    app()
