"""Wake-on-LAN helper for madVR Envy."""

from __future__ import annotations

import ipaddress
import socket

from .lifecycle import normalize_mac_address


async def async_send_magic_packet(mac_address: str, host: str | None = None) -> None:
    """Send a Wake-on-LAN magic packet."""
    normalized_mac = normalize_mac_address(mac_address)
    if normalized_mac is None:
        raise ValueError("Invalid MAC address")

    packet = bytes.fromhex("FF" * 6 + normalized_mac.replace(":", "") * 16)
    targets = ["255.255.255.255"]
    if host is not None:
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            address = None
        if isinstance(address, ipaddress.IPv4Address):
            octets = host.split(".")
            targets.append(".".join([*octets[:3], "255"]))

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        for target in dict.fromkeys(targets):
            sock.sendto(packet, (target, 9))
