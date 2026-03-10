"""Wake-on-LAN helper for madVR Envy."""

from __future__ import annotations

import socket

from .lifecycle import normalize_mac_address


async def async_send_magic_packet(mac_address: str) -> None:
    """Send a Wake-on-LAN magic packet."""
    normalized_mac = normalize_mac_address(mac_address)
    if normalized_mac is None:
        raise ValueError("Invalid MAC address")

    packet = bytes.fromhex("FF" * 6 + normalized_mac.replace(":", "") * 16)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.sendto(packet, ("255.255.255.255", 9))
