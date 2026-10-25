#!/usr/bin/env python3
"""Generate repeatable ruRU text overlays for elemental spell variants.

Run after gen_elemental_variants.py with an extracted Spell.dbc from the ruRU
client. The English generator manifest supplies the stable base IDs and source
templates; the client DBC supplies the stock ruRU base names and ranks.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MODULE = os.path.abspath(os.path.join(HERE, os.pardir, os.pardir, os.pardir))
CLIENT_PATCH = os.path.join(MODULE, "client-patch")
sys.path.insert(0, CLIENT_PATCH)

from lib import locales  # noqa: E402

MANIFEST = os.path.join(CLIENT_PATCH, "elemental_manifest.json")
OUTPUT = os.path.join(HERE, os.pardir, "db-world", "cw_zz_elemental_locale_ruRU.sql")
SPELL_TOKEN = re.compile(
    r"\$\{[^}]+\}(?:\.\d+)?|\$/(?:\d+;)?(?:\d{6})?[A-Za-z]+\d*"
    r"|\$(?:\d{6})?[A-Za-z]+(?::[A-Za-z]+;|\d*;?)")


def spell_tokens_match(source: str, translated: str) -> bool:
    source_tokens = sorted(SPELL_TOKEN.findall(source))
    translated_tokens = sorted(SPELL_TOKEN.findall(translated))
    if source_tokens == translated_tokens:
        return True
    if ("$lpoint:points;" in source_tokens and
            "$lpoint:points;" not in translated_tokens and
            "серии приёмов" in translated.lower() and
            source_tokens.count("$lpoint:points;") == 1):
        source_tokens.remove("$lpoint:points;")
        return source_tokens == translated_tokens
    return False


class DbcFiles:
    """The minimal ClientFiles interface needed by locale support."""

    def __init__(self, folder: str):
        self.folder = folder

    def find(self, name: str):
        if name != "DBFilesClient\\Spell.dbc":
            raise FileNotFoundError(name)
        path = os.path.join(self.folder, "Spell.dbc")
        with open(path, "rb") as source:
            return source.read(), path


def sql(value: str) -> str:
    return "'" + value.replace("\\", "\\\\").replace("'", "''") + "'"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dbc", required=True,
                        help="directory containing Spell.dbc from a ruRU client")
    parser.add_argument("--manifest", default=MANIFEST)
    parser.add_argument("--out", default=OUTPUT)
    args = parser.parse_args(argv)

    with open(args.manifest, "r", encoding="utf-8") as source:
        manifest = json.load(source)
    catalog = locales.load_catalog()
    locales.apply_ruRU(manifest, catalog, "variants", files=DbcFiles(args.dbc))

    variants = manifest.get("variants", [])
    seen, missing = set(), []
    for variant in variants:
        ident = int(variant["id"])
        if ident in seen:
            raise SystemExit("duplicate elemental spell id %d" % ident)
        seen.add(ident)
        localized = variant.get("ruRU", {})
        for field in ("name", "rank_text", "description", "tooltip"):
            text = variant.get(field, "")
            if text and not localized.get(field):
                missing.append((ident, field))
            if text and not spell_tokens_match(text, localized.get(field, "")):
                raise SystemExit("placeholder mismatch in elemental spell %d %s" % (ident, field))
    if missing:
        raise SystemExit("missing elemental ruRU fields: %s" % missing[:12])

    ids = sorted(seen)
    listed = ", ".join(str(ident) for ident in ids)
    fields = (("Name_Lang_ruRU", "name"),
              ("NameSubtext_Lang_ruRU", "rank_text"),
              ("Description_Lang_ruRU", "description"),
              ("AuraDescription_Lang_ruRU", "tooltip"))
    lines = ["-- Generated from elemental_manifest.json and the ruRU client Spell.dbc.",
             "SET NAMES utf8mb4;", ""]
    lines.append("UPDATE `spell_dbc` SET")
    for field_index, (column, key) in enumerate(fields):
        lines.append("  `%s` = CASE `ID`" % column)
        for variant in variants:
            lines.append("    WHEN %d THEN %s" %
                         (variant["id"], sql(variant.get("ruRU", {}).get(key, ""))))
        lines.append("    ELSE `%s` END%s" %
                     (column, "," if field_index + 1 < len(fields) else ""))
    lines.append("WHERE `ID` IN (%s);" % listed)
    lines.append("")

    with open(args.out, "w", encoding="utf-8", newline="\n") as output:
        output.write("\n".join(lines))
    with open(args.manifest, "w", encoding="utf-8", newline="\n") as output:
        json.dump(manifest, output, ensure_ascii=False, indent=1)
        output.write("\n")
    print("localized %d/%d elemental spell rows; wrote %s" %
          (len(ids), len(variants), os.path.normpath(args.out)))
    print("updated %s" % os.path.normpath(args.manifest))
    return 0


if __name__ == "__main__":
    sys.exit(main())
