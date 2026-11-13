#!/usr/bin/env python3
"""Tests of the peer broker, with no VM, no container and no Claude.

    python3 dev/test-peer-broker.py

Starts the broker on sockets in a temporary directory and talks MCP to it. See
dev/linting.md, "The peer broker".
"""
import json
import os
import socket
import subprocess
import sys
import tempfile
import time

BROKER = os.path.join(os.path.dirname(__file__), "..", "roles", "agentbox", "files", "agentbox-peer-broker")


class Session:
    def __init__(self, base, project):
        self.sock = socket.socket(socket.AF_UNIX)
        self.sock.connect(f"{base}/{project}/peer.sock")
        self.sock.settimeout(2)
        self.file = self.sock.makefile("r")
        self.next = 0
        self.inbox = []

    def call(self, method, params=None):
        self.next += 1
        self.raw({"jsonrpc": "2.0", "id": self.next, "method": method, "params": params or {}})
        while True:
            message = self.line()
            if message.get("id") == self.next:
                return message
            self.inbox.append(message)

    def raw(self, message):
        self.sock.sendall((json.dumps(message) + "\n").encode())

    def read(self):
        return self.inbox.pop(0) if self.inbox else self.line()

    def line(self):
        line = self.file.readline()
        if not line:
            raise EOFError
        return json.loads(line)

    def send(self, to, text, **extra):
        reply = self.call("tools/call", {"name": "send", "arguments": {"to": to, "text": text, **extra}})
        return reply["result"]["content"][0]["text"]


def main():
    with tempfile.TemporaryDirectory() as base:
        config = f"{base}/config.json"
        with open(config, "w", encoding="utf-8") as handle:
            json.dump({
                "links": {"a": ["b"], "b": ["a"], "c": ["a"], "d": []},
                "budget": 4, "max_bytes": 100, "run_dir": base,
            }, handle)
        broker = subprocess.Popen([sys.executable, BROKER, config], stdout=subprocess.PIPE, text=True)
        try:
            for _ in range(50):
                if os.path.exists(f"{base}/d/peer.sock"):
                    break
                time.sleep(0.05)
            run(base)
        finally:
            broker.terminate()
            log = broker.communicate(timeout=5)[0]
        events = [json.loads(line) for line in log.splitlines()]
        assert any(e["event"] == "sent" and e["sender"] == "a" and e["text"] == "hello" for e in events)
        assert any(e["event"] == "refused" and e.get("reason") == "second connection" for e in events)
    print("ok")


def run(base):
    a, b = Session(base, "a"), Session(base, "b")

    # The handshake: a channel, never permission relay, an old enough protocol.
    init = a.call("initialize")["result"]
    assert "claude/channel" in init["capabilities"]["experimental"]
    assert "claude/channel/permission" not in init["capabilities"]["experimental"]
    assert init["protocolVersion"] < "2026-07-28"

    # The tool names exactly the project's own links.
    tool = a.call("tools/list")["result"]["tools"][0]
    assert tool["inputSchema"]["properties"]["to"]["enum"] == ["b"]

    # The sender comes from the socket; the message carries the way to answer.
    assert a.send("b", "hello", sender="c", **{"from": "c"}) == "sent"
    event = b.read()
    assert event["method"] == "notifications/claude/channel"
    assert event["params"]["meta"]["sender"] == "a"
    assert event["params"]["content"].startswith("hello\n")
    assert 'to="a"' in event["params"]["content"]

    # Control characters go, newlines stay.
    assert a.send("b", "x\x1b[2Jy\nz") == "sent"
    assert b.read()["params"]["content"].startswith("x[2Jy\nz")

    # No link, wrong arguments, too long.
    assert a.send("c", "no").startswith("refused: no link")
    assert a.send("nobody", "no").startswith("refused: no link")
    assert a.send("b", "x" * 101).startswith("refused: longer")
    assert a.call("tools/call", {"name": "send", "arguments": {"to": 1, "text": 2}})["result"]["isError"]
    assert "error" in a.call("nonsense")

    # A one-way link: c reaches a, and a is told no answer can get back.
    c = Session(base, "c")
    assert c.send("a", "one way") == "sent"
    assert "no link back" in a.read()["params"]["content"]
    assert c.send("b", "no").startswith("refused: no link")

    # A second connection neither works nor disturbs the first.
    second = Session(base, "a")
    try:
        second.read()
        raise AssertionError("second connection was served")
    except (EOFError, ConnectionError, OSError):
        pass
    assert a.call("ping")["result"] == {}

    # A closed session.
    b.sock.close()
    b.file.close()
    time.sleep(0.2)
    assert a.send("b", "gone").startswith("refused: the session in b")

    # Reopening b reset the 2 spent above. It stops at 4, and both sides hear.
    b = Session(base, "b")
    time.sleep(0.1)
    for number in range(4):
        assert a.send("b", str(number)) == "sent"
        assert b.read()["params"]["meta"]["sender"] == "a"
    assert b.read()["params"]["meta"]["sender"] == "broker"
    assert a.read()["params"]["meta"]["sender"] == "broker"
    assert b.send("a", "more").startswith("refused: this conversation")

    # A person starts the session again: it resets.
    b.sock.close()
    b.file.close()
    time.sleep(0.2)
    b = Session(base, "b")
    time.sleep(0.1)
    assert a.send("b", "again") == "sent"


main()
