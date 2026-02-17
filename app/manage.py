#!/usr/bin/env python3
"""Django's command-line utility for administrative tasks."""

import os
import sys
from pathlib import Path


def main() -> None:
    root_env = Path(__file__).resolve().parent.parent / ".env"
    if root_env.exists():
        try:
            from dotenv import load_dotenv

            load_dotenv(root_env)
        except Exception:
            pass
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "babybuddy.settings.local")
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
