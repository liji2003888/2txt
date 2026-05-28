#!/usr/bin/env python3
"""Post a progress message to a Lark/Feishu custom-bot webhook. No-op if LARK_WEBHOOK is unset."""
import base64
import hashlib
import hmac
import json
import os
import sys
import time
import urllib.request


def main() -> None:
    if len(sys.argv) < 2:
        print("usage: notify_lark.py <message>", file=sys.stderr)
        sys.exit(2)
    url = os.environ.get("LARK_WEBHOOK")
    if not url:
        print("skip: LARK_WEBHOOK not set", file=sys.stderr)
        return
    body = {"msg_type": "text", "content": {"text": sys.argv[1]}}
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
    except Exception as exc:  # noqa: BLE001
        print(f"notify failed: {exc}", file=sys.stderr)


if __name__ == "__main__":
    main()
