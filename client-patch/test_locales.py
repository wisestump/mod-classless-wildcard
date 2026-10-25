#!/usr/bin/env python3
"""Regression checks for the player package's locale catalogs and DBC merge."""

import importlib.util
import io
import os
import struct
import sys
import tempfile
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
MODULE = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from lib import dbc, locales
import install


CATALOGS = ("ruRU.json", "spell_texts_ruRU.json", "elemental_texts_ruRU.json")


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def test_player_catalogs_load_from_package():
    package_dir = os.path.join(HERE, "locales")
    source_dir = os.path.join(MODULE, "data", "locales")
    check(os.path.abspath(locales.catalog_path()) == os.path.join(package_dir, "ruRU.json"),
          "the player install must prefer its bundled ruRU catalog")
    for name in CATALOGS:
        packaged = os.path.join(package_dir, name)
        authored = os.path.join(source_dir, name)
        check(os.path.isfile(packaged), "missing packaged locale catalog: " + name)
        with open(packaged, "rb") as file:
            package_bytes = file.read()
        with open(authored, "rb") as file:
            source_bytes = file.read()
        check(package_bytes == source_bytes, "packaged catalog is stale: " + name)

    catalog = locales.load_catalog()
    check(catalog.get("spell_texts") and catalog.get("elemental_texts"),
          "the install must load spell and elemental text catalogs too")


def test_updater_delivers_bundled_catalogs():
    updater_path = os.path.join(HERE, "update.py")
    spec = importlib.util.spec_from_file_location("classless_update_for_test", updater_path)
    updater = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(updater)

    old_targets, old_manifest = updater.TARGETS, updater.MANIFEST_FILE
    try:
        with tempfile.TemporaryDirectory() as temp:
            target = os.path.join(temp, "client-patch")
            updater.TARGETS = {"client-patch": target}
            updater.MANIFEST_FILE = os.path.join(target, "update_manifest.txt")
            blob = io.BytesIO()
            with zipfile.ZipFile(blob, "w", zipfile.ZIP_DEFLATED) as archive:
                for name in CATALOGS:
                    source = os.path.join(HERE, "locales", name)
                    with open(source, "rb") as file:
                        archive.writestr("repository/client-patch/locales/" + name,
                                         file.read())
            with zipfile.ZipFile(io.BytesIO(blob.getvalue())) as archive:
                written, changed, pending, removed = updater.apply(archive)
            check((written, changed, pending, removed) == (3, 3, [], 0),
                  "updater should install each package catalog")
            check(all(os.path.isfile(os.path.join(target, "locales", name)) for name in CATALOGS),
                  "updater omitted bundled locale catalogs")
    finally:
        updater.TARGETS, updater.MANIFEST_FILE = old_targets, old_manifest


def synthetic_chrclasses():
    classes = ((2, "PALADIN"), (6, "DEATHKNIGHT"), (7, "SHAMAN"), (11, "DRUID"))
    strings = bytearray(b"Stock class\0")
    records = bytearray()
    for class_id, token in classes:
        token_offset = len(strings)
        strings.extend(token.encode("ascii") + b"\0")
        row = [0] * dbc.CHRCLASSES_FIELDS
        row[0] = class_id
        for field in (4, 21, 38):
            row[field] = 0
        row[dbc.CHRCLASSES_TOKEN_FIELD] = token_offset
        row[dbc.CHRCLASSES_FLAGS_FIELD] = dbc.CHRCLASSES_FLAG_RELIC_SLOT
        records.extend(struct.pack("<%dI" % dbc.CHRCLASSES_FIELDS, *row))
    header = struct.pack("<4s4I", dbc.WDBC_MAGIC, len(classes), dbc.CHRCLASSES_FIELDS,
                         dbc.CHRCLASSES_FIELDS * 4, len(strings))
    return header + records + strings


def test_locale_names_preserve_ranged_slot_patch():
    stock = synthetic_chrclasses()
    patched, _renamed = dbc.rename_all_classes(stock, "Hero")
    patched, changed = dbc.clear_relic_slot(patched)
    check({row[0] for row in changed} == {2, 6, 7, 11},
          "synthetic source must exercise all four relic classes")
    locale_payload = {install.CHRCLASSES: patched}

    for locale in ("enUS", "ruRU"):
        final = install.build_locale_class_table(locale_payload, "Hero", locale)
        count, fields, size, _string_size = dbc.parse_header(final)
        strings = final[20 + count * size:]
        for index in range(count):
            row = struct.unpack_from("<%dI" % fields, final, 20 + index * size)
            check(not (row[dbc.CHRCLASSES_FLAGS_FIELD] & dbc.CHRCLASSES_FLAG_RELIC_SLOT),
                  "%s locale payload restored class %d's relic slot" % (locale, row[0]))
            expected = "Герой" if locale == "ruRU" else "Hero"
            check(all(dbc.read_string(strings, row[field]) == expected
                      for field in (12, 29, 46)),
                  "%s locale name columns were not applied" % locale)
            check(dbc.read_string(strings, row[dbc.CHRCLASSES_TOKEN_FIELD]) in
                  {"PALADIN", "DEATHKNIGHT", "SHAMAN", "DRUID"},
                  "%s locale changed a technical class token" % locale)


def test_elemental_name_puts_modifier_after_base_ability():
    catalog = locales.load_catalog()
    record = {
        "id": 950000,
        "base": 78,
        "element": "frost",
        "base_name": "Heroic Strike",
        "name": "Frozen Heroic Strike",
        "description": "",
        "rank_text": "",
    }
    translated = locales._elemental_variant_translation(
        record, catalog, {78: ("Удар героя", "")})
    check(translated["name"] == "Удар героя: ледяная магия",
          "elemental modifier should follow the translated base ability")


if __name__ == "__main__":
    test_player_catalogs_load_from_package()
    test_updater_delivers_bundled_catalogs()
    test_locale_names_preserve_ranged_slot_patch()
    test_elemental_name_puts_modifier_after_base_ability()
    print("all locale package and DBC merge checks passed")
