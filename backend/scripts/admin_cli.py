#!/usr/bin/env python3
"""
TV-Bridge Admin CLI Tool

Kommandozeilen-Tool für Admin-Aufgaben.
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Backend-Pfad hinzufügen
sys.path.insert(0, str(Path(__file__).parent.parent / "app"))

from config_store import config_store
from pairing_service import pairing_service


async def list_devices():
    """Liste alle Geräte auf."""
    await config_store.initialize()
    devices = await config_store.list_devices()
    
    if not devices:
        print("No devices found.")
        return
    
    print(f"\n{'ID':<40} {'Name':<20} {'Status':<10} {'Last Seen'}")
    print("-" * 90)
    
    for device in devices:
        status = "Revoked" if not device.allowed else "Active"
        last_seen = device.last_seen_at or "Never"
        print(f"{device.id:<40} {device.name:<20} {status:<10} {last_seen}")
    
    print()


async def revoke_device(device_id: str):
    """Widerrufe ein Gerät."""
    await config_store.initialize()
    await config_store.revoke_device(device_id, "Revoked by admin CLI")
    print(f"Device {device_id} revoked.")


async def allow_device(device_id: str):
    """Erlaube ein Gerät wieder."""
    await config_store.initialize()
    await config_store.allow_device(device_id)
    print(f"Device {device_id} allowed.")


async def start_pairing():
    """Starte Pairing-Modus."""
    await config_store.initialize()
    await pairing_service.initialize(config_store)
    
    code, token = await pairing_service.start_pairing()
    print(f"\nPairing started!")
    print(f"Code: {code}")
    print(f"Valid for: {pairing_service.pairing_timeout} seconds")
    print()


async def stop_pairing():
    """Stoppe Pairing-Modus."""
    await config_store.initialize()
    await pairing_service.initialize(config_store)
    await pairing_service.stop_pairing()
    print("Pairing stopped.")


async def show_logs(limit: int = 50):
    """Zeige Audit-Logs."""
    await config_store.initialize()
    
    async with config_store.db.execute(
        "SELECT timestamp, event_type, device_id, details "
        "FROM audit_log ORDER BY timestamp DESC LIMIT ?",
        (limit,)
    ) as cursor:
        logs = await cursor.fetchall()
    
    if not logs:
        print("No logs found.")
        return
    
    print(f"\n{'Timestamp':<20} {'Event':<20} {'Device ID':<40}")
    print("-" * 90)
    
    for log in logs:
        timestamp, event_type, device_id, _ = log
        device_id = device_id or "-"
        print(f"{timestamp:<20} {event_type:<20} {device_id:<40}")
    
    print()


def main():
    parser = argparse.ArgumentParser(description="TV-Bridge Admin CLI")
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # List devices
    subparsers.add_parser("list", help="List all devices")
    
    # Revoke device
    revoke_parser = subparsers.add_parser("revoke", help="Revoke a device")
    revoke_parser.add_argument("device_id", help="Device ID to revoke")
    
    # Allow device
    allow_parser = subparsers.add_parser("allow", help="Allow a device")
    allow_parser.add_argument("device_id", help="Device ID to allow")
    
    # Start pairing
    subparsers.add_parser("pair", help="Start pairing mode")
    
    # Stop pairing
    subparsers.add_parser("unpair", help="Stop pairing mode")
    
    # Show logs
    logs_parser = subparsers.add_parser("logs", help="Show audit logs")
    logs_parser.add_argument("-n", "--limit", type=int, default=50, help="Number of logs to show")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Ausführen
    if args.command == "list":
        asyncio.run(list_devices())
    elif args.command == "revoke":
        asyncio.run(revoke_device(args.device_id))
    elif args.command == "allow":
        asyncio.run(allow_device(args.device_id))
    elif args.command == "pair":
        asyncio.run(start_pairing())
    elif args.command == "unpair":
        asyncio.run(stop_pairing())
    elif args.command == "logs":
        asyncio.run(show_logs(args.limit))


if __name__ == "__main__":
    main()
