#!/usr/bin/env python3
"""Copy the authored Nemesis aura ruRU text into the client patch package."""

from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MODULE = os.path.abspath(os.path.join(HERE, os.pardir, os.pardir, os.pardir))
sys.path.insert(0, os.path.join(MODULE, "client-patch"))

from lib import dbc  # noqa: E402

SOURCE = os.path.join(MODULE, "data", "locales", "nemesis_spell_texts_ruRU.json")
OUTPUT = os.path.join(MODULE, "client-patch", "locales",
                      "nemesis_spell_texts_ruRU.json")


def main() -> int:
    with open(SOURCE, "r", encoding="utf-8") as source:
        document = json.load(source)
    entries = document.get("spells", {})
    expected = {str(spell_id) for spell_id in dbc.SPELL_RENAMES}
    if document.get("version") != 1 or set(entries) != expected:
        raise SystemExit("Nemesis spell ruRU IDs differ from client DBC renames")
    for spell_id, entry in entries.items():
        if not entry.get("name") or not entry.get("tooltip"):
            raise SystemExit("Nemesis spell ruRU name/tooltip missing at %s" % spell_id)
        if not any("\u0400" <= char <= "\u04ff" for char in entry["name"]):
            raise SystemExit("Nemesis spell ruRU name is not Cyrillic at %s" % spell_id)
        if not any("\u0400" <= char <= "\u04ff" for char in entry["tooltip"]):
            raise SystemExit("Nemesis spell ruRU tooltip is not Cyrillic at %s" % spell_id)

    packaged = {"version": 1,
                "spells": {key: entries[key] for key in sorted(entries, key=int)}}
    with open(OUTPUT, "w", encoding="utf-8", newline="\n") as target:
        json.dump(packaged, target, ensure_ascii=False, indent=2)
        target.write("\n")
    print("wrote ruRU text for %d/%d Nemesis aura spells" %
          (len(entries), len(dbc.SPELL_RENAMES)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
