"""Doctor command — system health diagnostics.

Usage: python -m investiga_cli.main doctor
"""

import sys


def check_postgres() -> bool:
    """Check PostgreSQL connectivity."""
    try:
        import psycopg

        from investiga_api.settings import settings

        conn = psycopg.connect(
            host=settings.postgres_host,
            port=settings.postgres_port,
            dbname=settings.postgres_db,
            user=settings.postgres_user,
            password=settings.postgres_password,
        )
        conn.execute("SELECT 1")
        conn.close()
        return True
    except Exception as e:
        print(f"  ❌ PostgreSQL: {e}")
        return False


def check_rabbitmq() -> bool:
    """Check RabbitMQ connectivity."""
    try:
        import urllib.request

        from investiga_api.settings import settings

        url = f"http://{settings.rabbitmq_host}:15672/api/healthchecks/node"
        req = urllib.request.Request(url)
        import base64

        credentials = base64.b64encode(
            f"{settings.rabbitmq_user}:{settings.rabbitmq_password}".encode()
        ).decode()
        req.add_header("Authorization", f"Basic {credentials}")
        resp = urllib.request.urlopen(req, timeout=5)
        return resp.status == 200
    except Exception as e:
        print(f"  ❌ RabbitMQ: {e}")
        return False


def check_redis() -> bool:
    """Check Redis connectivity."""
    try:
        import socket

        from investiga_api.settings import settings

        # Parse redis URL
        host = settings.redis_url.split("//")[1].split(":")[0]
        port = int(settings.redis_url.split(":")[-1].split("/")[0])
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3)
        s.connect((host, port))
        s.send(b"PING\r\n")
        resp = s.recv(64)
        s.close()
        return b"PONG" in resp
    except Exception as e:
        print(f"  ❌ Redis: {e}")
        return False


def check_env_vars() -> bool:
    """Check required environment variables."""
    from investiga_api.settings import settings

    issues = []
    if not settings.openrouter_api_key:
        issues.append("OPENROUTER_API_KEY not set")
    if not settings.sentry_dsn:
        issues.append("SENTRY_DSN not set (optional)")

    if issues:
        for i in issues:
            print(f"  ⚠️  {i}")
    return len([i for i in issues if "optional" not in i]) == 0


def run_doctor() -> None:
    """Run all diagnostic checks."""
    print("🩺 Investiga Tijucas — System Doctor")
    print("=" * 50)

    checks = [
        ("PostgreSQL", check_postgres),
        ("RabbitMQ", check_rabbitmq),
        ("Redis", check_redis),
        ("Environment", check_env_vars),
    ]

    results = []
    for name, check_fn in checks:
        try:
            ok = check_fn()
        except Exception:
            ok = False
        status = "✅" if ok else "❌"
        print(f"  {status} {name}")
        results.append(ok)

    print("=" * 50)
    all_ok = all(results)
    if all_ok:
        print("✅ All systems healthy!")
    else:
        print("⚠️  Some checks failed. Review above.")
        sys.exit(1)


if __name__ == "__main__":
    run_doctor()
