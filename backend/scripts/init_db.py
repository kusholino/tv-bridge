#!/usr/bin/env python3
"""
TV-Bridge Database Initialization Script

Erstellt und initialisiert die SQLite-Datenbank.
"""

import asyncio
import sys
from pathlib import Path

# Füge Backend-Pfad hinzu
sys.path.insert(0, str(Path(__file__).parent.parent / "app"))

from config_store import config_store


async def main():
    print("Initializing TV-Bridge database...")
    print(f"Database path: {config_store.db_path}")
    
    # Initialisieren
    await config_store.initialize()
    
    print("Database initialized successfully!")
    print("\nCreated tables:")
    print("  - devices")
    print("  - profiles")
    print("  - pairing_sessions")
    print("  - audit_log")


if __name__ == "__main__":
    asyncio.run(main())
