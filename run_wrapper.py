import os
import sys
import time
import logging
from pathlib import Path

# -------------------------------------------------------------------
# 1) Environment (must be set before importing Django settings usage)
# -------------------------------------------------------------------
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "restaurant.settings")

# -------------------------------------------------------------------
# 2) Logging (works even when console=False in PyInstaller)
# -------------------------------------------------------------------
def setup_logging():
    """
    In PyInstaller noconsole/windowed mode on Windows, sys.stdout/sys.stderr may be None,
    so printing or stdout reconfigure can crash. Use file logging instead. [web:106][web:162]
    """
    appdata = os.environ.get("APPDATA") or str(Path.home())
    log_dir = Path(appdata) / "RestaurantBilling"
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / "backend.log"

    logger = logging.getLogger("backend")
    logger.setLevel(logging.INFO)

    # Avoid duplicate handlers if something imports this twice
    if not logger.handlers:
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
        fh.setFormatter(fmt)
        logger.addHandler(fh)

    return logger, str(log_file)

log, log_path = setup_logging()
log.info("Backend boot starting. Log file: %s", log_path)

# Optional: if you still want safe stdout for rare cases, guard it.
# (Not required if you stop using print.)
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")

# -------------------------------------------------------------------
# 3) Django + server
# -------------------------------------------------------------------
import django
from django.core.management import call_command
from waitress import serve


def migrations_needed():
    """
    Check if there are unapplied migrations.
    Uses MigrationExecutor and a migration plan to decide. [web:178]
    """
    try:
        from django.db.migrations.executor import MigrationExecutor
        from django.db import connections, DEFAULT_DB_ALIAS

        connection = connections[DEFAULT_DB_ALIAS]
        executor = MigrationExecutor(connection)
        targets = executor.loader.graph.leaf_nodes()
        plan = executor.migration_plan(targets)
        return bool(plan)
    except Exception as e:
        log.exception("Migration check failed; will attempt migrate anyway. Error: %s", e)
        return True


def run_migrations_if_needed():
    try:
        if migrations_needed():
            log.info("Running migrations...")
            call_command("migrate", interactive=False)
            log.info("Migrations completed.")
        else:
            log.info("Database is up to date. No migrations needed.")
    except Exception as e:
        log.exception("Migration step failed: %s", e)
        raise


def start_server(host="127.0.0.1", port=8000, threads=4):
    """
    Start Waitress serving your Django WSGI application. [web:177]
    """
    from restaurant.wsgi import application

    log.info("Starting Waitress on http://%s:%s (threads=%s)", host, port, threads)
    serve(application, host=host, port=port, threads=threads)


def main():
    try:
        log.info("Initializing Django...")
        django.setup()

        run_migrations_if_needed()

        # Small delay can help in some cases where DB is just created / file locks etc.
        time.sleep(0.2)

        start_server(host="127.0.0.1", port=8000, threads=4)

    except Exception as e:
        log.exception("Backend crashed: %s", e)
        # Exit with non-zero so Electron knows backend failed.
        raise SystemExit(1)


if __name__ == "__main__":
    main()
