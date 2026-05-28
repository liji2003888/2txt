#!/usr/bin/env python3
"""Validate a deck JSON against slide_schema.json. Exits non-zero on schema violations."""
import json
import sys
from pathlib import Path

SCHEMA = Path(__file__).resolve().parent.parent / "schema" / "slide_schema.json"


def main() -> None:
    if len(sys.argv) < 2:
        print("usage: validate.py <deck.json>", file=sys.stderr)
        sys.exit(2)
    deck = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        sys.exit("error: jsonschema not installed (pip install -r requirements.txt)")
    errors = sorted(Draft202012Validator(schema).iter_errors(deck), key=lambda e: e.path)
    if errors:
        for e in errors:
            loc = "/".join(str(p) for p in e.path) or "<root>"
            print(f"INVALID at {loc}: {e.message}", file=sys.stderr)
        sys.exit(1)
    print(f"OK: {len(deck.get('slides', []))} slide(s) valid")


if __name__ == "__main__":
    main()
