"""Minimal client for the Legacy TMS line protocol.

Wire rules encoded here:
  - one request per connection (open, send, read, close)
  - lines are ASCII, terminated by CRLF, max 4096 bytes
  - success = zero or more record lines, then a line "END"
  - error   = a single line "ERR|CODE:<code>|MSG:<msg>"
  - fixed-width values are right-padded with spaces
"""

import socket
import time

CRLF = "\r\n"
MAX_FRAME = 4096
IDLE_TIMEOUT = 30
RETRYABLE = {"SERVER_ERROR"}


class TMSError(Exception):
    def __init__(self, code, msg):
        super().__init__(f"{code}: {msg}")
        self.code = code
        self.msg = msg


def _encode(cmd, auth, **fields):
    """Build the request line. CMD first, AUTH second, then the rest."""
    parts = [f"CMD:{cmd}", f"AUTH:{auth}"]
    parts += [f"{k.upper()}:{v}" for k, v in fields.items() if v is not None]
    line = "|".join(parts) + CRLF

    for part in parts:
        if "|" in part[part.index(":") + 1:]:
            raise ValueError(f"value contains a delimiter: {part}")
    if len(line.encode("ascii")) > MAX_FRAME:
        raise ValueError("request exceeds 4096 bytes")
    return line.encode("ascii")


def _parse_line(line):
    """'A:1|B:foo  ' -> {'A': '1', 'B': 'foo'}, stripping width padding."""
    record = {}
    for pair in line.split("|"):
        key, _, value = pair.partition(":")
        record[key.strip()] = value.rstrip()
    return record


def _read_all(sock):
    """Read until the server closes. It always does, after one response."""
    chunks = []
    while True:
        chunk = sock.recv(MAX_FRAME)
        if not chunk:
            return b"".join(chunks).decode("ascii")
        chunks.append(chunk)


def send(host, port, cmd, auth, timeout=IDLE_TIMEOUT, **fields):
    """Send one command, return a list of record dicts. Raises TMSError."""
    payload = _encode(cmd, auth, **fields)

    with socket.create_connection((host, port), timeout=timeout) as sock:
        sock.sendall(payload)
        raw = _read_all(sock)

    lines = [ln for ln in raw.split(CRLF) if ln]
    if not lines:
        raise TMSError("EMPTY_RESPONSE", "server closed without replying")

    if lines[0].startswith("ERR|"):
        err = _parse_line(lines[0])
        raise TMSError(err.get("CODE", "UNKNOWN"), err.get("MSG", ""))

    if lines[-1] != "END":
        raise TMSError("MALFORMED", "response is missing its END terminator")

    return [_parse_line(ln) for ln in lines[:-1]]


def send_with_retry(host, port, cmd, auth, attempts=3, **fields):
    """Same as send(), but rides out injected faults with backoff."""
    for attempt in range(attempts):
        try:
            return send(host, port, cmd, auth, **fields)
        except (socket.timeout, ConnectionError) as exc:
            last = exc
        except TMSError as exc:
            if exc.code not in RETRYABLE:
                raise  # AUTH_FAILED, UNKNOWN_LOAD etc. won't improve with time
            last = exc
        time.sleep(0.5 * (2 ** attempt))
    raise last


if __name__ == "__main__":
    import os

    HOST = os.environ["TMS_HOST"]
    PORT = int(os.environ["TMS_PORT"])
    AUTH = os.environ["TMS_AUTH"]

    print(send(HOST, PORT, "DEBUG_ECHO", AUTH, msg="ping"))
    print(send_with_retry(HOST, PORT, "LOAD_QUERY", AUTH, orig_city="Atlanta", dest_city="Fort Worth"))
    print(send_with_retry(HOST, PORT, "LOAD_GET", AUTH, load_id="LD00527"))