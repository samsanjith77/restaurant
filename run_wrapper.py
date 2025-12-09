import os
import sys
sys.stdout.reconfigure(encoding='utf-8')
# ✅ Ensure Django settings are available inside EXE
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "restaurant.settings")

import django
from django.core.management import call_command

def main():
    print("Initializing Django...")
    django.setup()

    print("Running migrations once...")
    call_command("migrate", interactive=False)

    print("Starting Django server (no auto-reloader)...")
    call_command("runserver", "127.0.0.1:8000", use_reloader=False)

if __name__ == "__main__":
    main()
