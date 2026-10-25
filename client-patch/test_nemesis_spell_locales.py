#!/usr/bin/env python3
"""Regression coverage for localized stock Nemesis aura names and tooltips."""

from __future__ import annotations

import json
import os
import struct
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from lib import dbc


def synthetic_spell_dbc():
    strings = bytearray(b"\0")

    def add(text):
        offset = len(strings)
        strings.extend(text.encode("utf-8") + b"\0")
        return offset

    records = bytearray(len(dbc.SPELL_RENAMES) * dbc.SPELL_FIELDS * 4)
    for index, (spell_id, (name, tooltip)) in enumerate(dbc.SPELL_RENAMES.items()):
        base = index * dbc.SPELL_FIELDS * 4
        struct.pack_into("<I", records, base, spell_id)
        name_offset, tooltip_offset = add("Stock " + name), add("Stock " + tooltip)
        for locale in range(dbc.SPELL_LOCALES):
            struct.pack_into("<I", records,
                             base + (dbc.SPELL_NAME_COLUMN + locale) * 4, name_offset)
            struct.pack_into("<I", records,
                             base + (dbc.SPELL_DESCRIPTION_COLUMN + locale) * 4,
                             tooltip_offset)
            struct.pack_into("<I", records,
                             base + (dbc.SPELL_TOOLTIP_COLUMN + locale) * 4,
                             tooltip_offset)
    header = dbc.WDBC_MAGIC + struct.pack(
        "<4I", len(dbc.SPELL_RENAMES), dbc.SPELL_FIELDS,
        dbc.SPELL_FIELDS * 4, len(strings))
    return header + bytes(records) + bytes(strings)


def field_text(records, strings, row, column):
    offset = struct.unpack_from("<I", records, row * dbc.SPELL_FIELDS * 4 + column * 4)[0]
    return dbc.read_string(strings, offset)


class NemesisSpellLocaleTests(unittest.TestCase):
    def test_packaged_locale_matches_authored_source(self):
        root = os.path.abspath(os.path.join(HERE, os.pardir))
        with open(os.path.join(root, "data", "locales", "nemesis_spell_texts_ruRU.json"),
                  "r", encoding="utf-8") as source:
            authored = json.load(source)
        with open(os.path.join(HERE, "locales", "nemesis_spell_texts_ruRU.json"),
                  "r", encoding="utf-8") as source:
            packaged = json.load(source)
        self.assertEqual(authored, packaged)
        self.assertEqual(set(authored["spells"]),
                         {str(spell_id) for spell_id in dbc.SPELL_RENAMES})

    def test_ru_names_and_tooltips_reach_only_ru_locale_columns(self):
        patched, renamed = dbc.rename_spells(synthetic_spell_dbc())
        self.assertEqual(renamed, len(dbc.SPELL_RENAMES))
        rows, fields, record_size, string_size = dbc.parse_header(patched)
        self.assertEqual(rows, len(dbc.SPELL_RENAMES))
        records = patched[20:20 + rows * record_size]
        strings = patched[20 + rows * record_size:]
        ru = dbc.SPELL_LOCALE_RURU

        for index, (spell_id, (name, tooltip)) in enumerate(dbc.SPELL_RENAMES.items()):
            localized_name, localized_tooltip = dbc.SPELL_RENAMES_RURU[spell_id]
            self.assertEqual(field_text(records, strings, index, dbc.SPELL_NAME_COLUMN), name)
            self.assertEqual(field_text(records, strings, index, dbc.SPELL_DESCRIPTION_COLUMN), tooltip)
            self.assertEqual(field_text(records, strings, index, dbc.SPELL_TOOLTIP_COLUMN), tooltip)
            self.assertEqual(field_text(records, strings, index,
                                        dbc.SPELL_NAME_COLUMN + ru), localized_name)
            self.assertEqual(field_text(records, strings, index,
                                        dbc.SPELL_DESCRIPTION_COLUMN + ru), localized_tooltip)
            self.assertEqual(field_text(records, strings, index,
                                        dbc.SPELL_TOOLTIP_COLUMN + ru), localized_tooltip)

        again, changed = dbc.rename_spells(patched)
        self.assertEqual(changed, 0)
        self.assertEqual(again, patched)


if __name__ == "__main__":
    unittest.main()
