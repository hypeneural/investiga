"""Operational CLI commands for managing sessions and dead letters."""

import argparse

from investiga_repositories.postgres.models.ops import SourceSession, DeadLetter
from investiga_repositories.postgres.session import SessionLocal


def list_blocked(args: argparse.Namespace) -> None:
    """List all currently blocked source sessions."""
    with SessionLocal() as db:
        blocked = db.query(SourceSession).filter(SourceSession.status == "blocked").all()
        
        if not blocked:
            print("✅ No blocked sessions found.")
            return
            
        print(f"⚠️  Found {len(blocked)} BLOCKED sessions:")
        for s in blocked:
            print(f"  [{s.id}] {s.source_name} (Mode: {s.session_mode}) - Error: {s.last_error_code} - {s.last_error_message}")


def resume_session(args: argparse.Namespace) -> None:
    """Resume a blocked session after human intervention."""
    with SessionLocal() as db:
        session = db.query(SourceSession).get(args.session_id)
        if not session:
            print(f"❌ Session {args.session_id} not found.")
            return
            
        if session.status != "blocked":
            print(f"ℹ️  Session {args.session_id} is already '{session.status}'. Not blocked.")
            return
            
        # Resume it
        session.status = "ready"
        session.last_error_code = None
        session.last_error_message = None
        db.commit()
        print(f"✅ Session {args.session_id} ({session.source_name}) has been RESUMED.")


def inspect_dlq(args: argparse.Namespace) -> None:
    """Inspect Dead Letter Queue (DLQ) records."""
    with SessionLocal() as db:
        query = db.query(DeadLetter)
        if args.queue:
            query = query.filter(DeadLetter.original_queue == args.queue)
            
        dead_letters = query.order_by(DeadLetter.dead_lettered_at.desc()).limit(args.limit).all()
        
        if not dead_letters:
            print("✅ DLQ is empty.")
            return
            
        print(f"📮 Found {len(dead_letters)} Dead Letters (Limit: {args.limit}):")
        for dl in dead_letters:
            print(f"  [{dl.id}] Queue: {dl.original_queue} - Job: {dl.job_id} - Error: {dl.failure_type}")
