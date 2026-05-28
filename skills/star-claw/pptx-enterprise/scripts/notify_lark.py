#!/usr/bin/env python3
"""Send a progress message to Lark/Feishu. Prefers a configured Lark-CLI, falls back to a webhook; no-op if neither."""
import base64
import hashlib
import hmac
import json
import os
import shlex
import subprocess
import sys
import time
import urllib.request


def via_cli(message: str) -> bool:
    # LARK_CLI_CMD is a command template; the message is appended as the final argv (no shell, injection-safe).
    # e.g. LARK_CLI_CMD="lark-cli message send --chat oc_xxx --text"
    tmpl = os.environ.get("LARK_CLI_CMD")
    if not tmpl:
        return False
    try:
        subprocess.run(shlex.split(tmpl) + [message], check=True)
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"lark-cli failed: {exc}", file=sys.stderr)
        return False


def via_webhook(message: str) -> bool:
    url = os.environ.get("LARK_WEBHOOK")
    if not url:
        return False
    body = {"msg_type": "text", "content": {"text": message}}
    secret = os.environ.get("LARK_SECRET")
    if secret:
        ts = str(int(time.time()))
        digest = hmac.new(f"{ts}\n{secret}".encode("utf-8"), digestmod=hashlib.sha256).digest()
        body["timestamp"] = ts
        body["sign"] = base64.b64encode(digest).decode("utf-8")
    req = urllib.request.Request(
        url, data=json.dumps(body).encode("utf-8"), headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            print(resp.read().decode("utf-8")[:200], file=sys.stderr)
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"webhook failed: {exc}", file=sys.stderr)
        return False


def main() -> None:
    if len(sys.argv) < 2:
        print("usage: notify_lark.py <message>", file=sys.stderr)
        sys.exit(2)
    msg = sys.argv[1]
    if not (via_cli(msg) or via_webhook(msg)):
        print("skip: set LARK_CLI_CMD or LARK_WEBHOOK to enable notifications", file=sys.stderr)


if __name__ == "__main__":
    main()
