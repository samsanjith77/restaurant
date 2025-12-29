import os
import sys
sys.stdout.reconfigure(encoding='utf-8')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "restaurant.settings")

import django
from django.core.management import call_command
from waitress import serve

def migrations_needed():
    """Check if migrations need to be applied"""
    try:
        from django.db.migrations.executor import MigrationExecutor
        from django.db import connections, DEFAULT_DB_ALIAS
        
        connection = connections[DEFAULT_DB_ALIAS]
        executor = MigrationExecutor(connection)
        targets = executor.loader.graph.leaf_nodes()
        plan = executor.migration_plan(targets)
        return bool(plan)
    except Exception as e:
        print(f"Migration check failed: {e}")
        return True

def main():
    print("Initializing Django...")
    django.setup()

    # Run migrations only if needed
    if migrations_needed():
        print("Running migrations...")
        call_command("migrate", interactive=False)
    else:
        print("Database is up to date.")

    # Import WSGI application
    from restaurant.wsgi import application
    
    print("Starting Waitress production server on 127.0.0.1:8000...")
    serve(application, host='127.0.0.1', port=8000, threads=4)

if __name__ == "__main__":
    main()
