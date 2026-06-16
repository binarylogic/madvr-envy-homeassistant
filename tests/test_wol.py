"""Tests for madVR Envy Wake-on-LAN helper."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from custom_components.madvr_envy.wol import async_send_magic_packet


class _FakeSocket:
    """Minimal socket context manager for magic packet tests."""

    def __init__(self) -> None:
        self.options: list[tuple[int, int, int]] = []
        self.sent: list[tuple[bytes, tuple[str, int]]] = []

    def __enter__(self) -> _FakeSocket:
        return self

    def __exit__(self, *_exc: object) -> None:
        return None

    def setsockopt(self, level: int, option: int, value: int) -> None:
        self.options.append((level, option, value))

    def sendto(self, packet: bytes, target: tuple[str, int]) -> None:
        self.sent.append((packet, target))


async def test_async_send_magic_packet_sends_global_and_subnet_broadcasts() -> None:
    """Wake-on-LAN should send the expected packet to broadcast targets."""
    fake_socket = _FakeSocket()

    with patch("custom_components.madvr_envy.wol.socket.socket", return_value=fake_socket):
        await async_send_magic_packet("00-11-22-33-44-55", "192.168.1.100")

    assert [target for _packet, target in fake_socket.sent] == [
        ("255.255.255.255", 9),
        ("192.168.1.255", 9),
    ]
    assert all(packet == fake_socket.sent[0][0] for packet, _target in fake_socket.sent)
    assert fake_socket.sent[0][0].startswith(bytes.fromhex("FF" * 6))
    assert len(fake_socket.sent[0][0]) == 102


async def test_async_send_magic_packet_rejects_invalid_mac() -> None:
    """Invalid MAC addresses should fail before opening a socket."""
    with (
        patch("custom_components.madvr_envy.wol.socket.socket") as socket_factory,
        pytest.raises(ValueError, match="Invalid MAC address"),
    ):
        await async_send_magic_packet("invalid")

    socket_factory.assert_not_called()
