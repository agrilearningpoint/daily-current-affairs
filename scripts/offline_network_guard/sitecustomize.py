"""Test-only outbound-network guard, activated ONLY by explicit PYTHONPATH.

Example (after installing dependencies):
  PYTHONPATH="$PWD/scripts/offline_network_guard:$PWD" python -m pytest -q

Python propagates this guard into stage subprocesses through PYTHONPATH. Local
RSS fixture servers remain available; external DNS and socket connections fail
immediately. This is a verification aid, not a security sandbox for untrusted code.
"""
import ipaddress
import socket

_original_connect = socket.socket.connect
_original_connect_ex = socket.socket.connect_ex
_original_getaddrinfo = socket.getaddrinfo


def _local(host):
    if host in (None, "", "localhost", b"localhost"):
        return True
    try:
        if isinstance(host, bytes):
            host = host.decode("ascii")
        return ipaddress.ip_address(host).is_loopback
    except (ValueError, TypeError, UnicodeError):
        return False


def _check(address):
    # Unix-domain sockets are local; INET/INET6 addresses are tuples.
    if isinstance(address, tuple) and not _local(address[0]):
        raise OSError(f"offline verification blocked outbound connection: {address[0]}")


def _connect(self, address):
    _check(address)
    return _original_connect(self, address)


def _connect_ex(self, address):
    _check(address)
    return _original_connect_ex(self, address)


def _getaddrinfo(host, *args, **kwargs):
    if not _local(host):
        raise OSError(f"offline verification blocked external DNS: {host}")
    return _original_getaddrinfo(host, *args, **kwargs)


socket.socket.connect = _connect
socket.socket.connect_ex = _connect_ex
socket.getaddrinfo = _getaddrinfo
