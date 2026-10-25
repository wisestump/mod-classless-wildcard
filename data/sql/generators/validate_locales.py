#!/usr/bin/env python3
"""Check ruRU catalog coverage against generated module data sources."""

from __future__ import annotations

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MODULE = os.path.abspath(os.path.join(HERE, os.pardir, os.pardir, os.pardir))
sys.path.insert(0, HERE)

import gen_locales  # noqa: E402
import gen_command_help  # noqa: E402
sys.path.insert(0, os.path.join(MODULE, "client-patch"))
from lib import locales as locale_support  # noqa: E402


SPELL_TOKEN = re.compile(
    r"\$\{[^}]+\}(?:\.\d+)?|\$/(?:\d+;)?(?:\d{6})?[A-Za-z]+\d*"
    r"|\$(?:\d{6})?[A-Za-z]+(?::[A-Za-z]+;|\d*;?)")
QUESTION_CONDITIONAL = re.compile(r"\$\?s\d+\[[^\]]*\](?:\[[^\]]*\])?")


def spell_tokens_match(source: str, translated: str) -> bool:
    source_tokens = sorted(SPELL_TOKEN.findall(source))
    translated_tokens = sorted(SPELL_TOKEN.findall(translated))
    if source_tokens == translated_tokens:
        return True

    # These Russian descriptions keep the numeric spell token and express
    # the count in words, avoiding English plural forms and awkward declension.
    # Permit only these known count-form omissions, and only when the matching
    # localized wording is present; all numeric/effect tokens must still match.
    allowed_omissions = {
        "$lpoint:points;": "серии приёмов",
        "$ltime:times;": "дополнительных рикошетов",
        "$lenemy:enemies;": "противников рядом с телом",
    }
    for token, russian_anchor in allowed_omissions.items():
        if (source_tokens.count(token) == 1 and
                translated_tokens.count(token) == 0 and
                russian_anchor in translated.lower()):
            source_tokens.remove(token)
    return source_tokens == translated_tokens


def reject_question_corruption(value, path: str) -> None:
    """Catch lossy ANSI writes without rejecting ordinary question punctuation.

    A single '?' may be prose punctuation or part of WoW's `$?s...[]` tooltip
    conditional. Lost Cyrillic usually becomes a long run of question marks or
    a string made mostly of question marks, so only those patterns are errors.
    """
    if isinstance(value, dict):
        for key, nested in value.items():
            reject_question_corruption(nested, "%s/%s" % (path, key))
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            reject_question_corruption(nested, "%s/%d" % (path, index))
    elif isinstance(value, str):
        candidate = QUESTION_CONDITIONAL.sub("", value)
        question_count = candidate.count("?")
        visible_count = sum(not char.isspace() for char in candidate)
        if "???" in candidate or (
                question_count >= 3 and visible_count and
                question_count / visible_count >= 0.3):
            raise SystemExit("likely lost characters in ruRU translation at %s: %r" %
                             (path, value))


def main() -> int:
    catalog_path = os.path.join(MODULE, "data", "locales", "ruRU.json")
    with open(catalog_path, "r", encoding="utf-8") as source:
        catalog = json.load(source)

    for filename in ("ruRU.json", "spell_texts_ruRU.json",
                     "elemental_texts_ruRU.json"):
        path = os.path.join(MODULE, "data", "locales", filename)
        with open(path, "r", encoding="utf-8") as source:
            reject_question_corruption(json.load(source), filename)

    command_catalog = catalog.get("command_help", {})
    gen_command_help.validate(command_catalog)
    command_help_sql = os.path.join(MODULE, "data", "sql", "db-world",
                                    "cw_world_commands.sql")
    command_columns, command_rows = gen_locales.read_insert_rows(
        command_help_sql, "acore_string")
    command_positions = {name: index for index, name in enumerate(command_columns)}
    command_sql = {int(row[command_positions["entry"]]): row
                   for row in command_rows}
    expected_ids = set()
    for command, _symbol, ident, default in gen_command_help.COMMANDS:
        expected_ids.add(ident)
        row = command_sql.get(ident)
        if not row:
            raise SystemExit("missing AcoreString command help for %s" % command)
        default_sql = gen_locales.unquote(
            row[command_positions["content_default"]]).replace("\\r\\n", "\n")
        russian_sql = gen_locales.unquote(
            row[command_positions["locale_ruRU"]]).replace("\\r\\n", "\n")
        if default_sql != default or russian_sql != command_catalog[command]:
            raise SystemExit("command-help SQL differs from catalog at %s" % command)
    if set(command_sql) != expected_ids:
        raise SystemExit("command-help AcoreString IDs differ from reserved module set")
    with open(command_help_sql, "r", encoding="utf-8") as source:
        command_sql_text = source.read()
    if re.search(r"INSERT\s+INTO\s+`command`", command_sql_text, re.I):
        raise SystemExit("module command help must not seed command.help text")

    world_locale_sql = os.path.join(MODULE, "data", "sql", "db-world",
                                    "cw_zz_locale_ruRU.sql")
    for table, text_fields in (
            ("creature_template_locale", (2, 3)),
            ("item_template_locale", (2, 3))):
        columns, rows = gen_locales.read_insert_rows(world_locale_sql, table)
        for row in rows:
            for index in text_fields:
                reject_question_corruption(gen_locales.unquote(row[index]),
                                           "%s/%s" % (table, row[0]))

    archetype_locale_sql = os.path.join(MODULE, "data", "sql", "db-world",
                                        "cw_archetypes_locale.sql")
    _, archetype_locale_rows = gen_locales.read_insert_rows(
        archetype_locale_sql, "cw_archetypes_locale")
    for row in archetype_locale_rows:
        for index in (2, 3):
            reject_question_corruption(gen_locales.unquote(row[index]),
                                       "cw_archetypes_locale/%s" % row[0])

    source_items = gen_locales.item_rows()
    if len({row["entry"] for row in source_items}) != len(source_items):
        raise SystemExit("duplicate item IDs in module SQL")
    missing_items = [row for row in source_items
                     if gen_locales.item_locale(row, catalog) is None]
    if missing_items:
        raise SystemExit("missing item translations: %s" %
                         ", ".join("%s %s" % (row["entry"], row["name"])
                                   for row in missing_items[:20]))
    for row in source_items:
        localized = gen_locales.item_locale(row, catalog)
        if len(localized["name"]) > 255 or len(localized["description"]) > 255:
            raise SystemExit("item locale exceeds field length at ID %s" % row["entry"])

    creature_ids = gen_locales.expected_creature_entries()
    catalog_creature_ids = {int(entry) for entry in catalog.get("creatures", {})}
    if creature_ids != catalog_creature_ids:
        raise SystemExit("creature locale IDs differ; missing=%s stale=%s" %
                         (sorted(creature_ids - catalog_creature_ids),
                          sorted(catalog_creature_ids - creature_ids)))

    archetypes = gen_locales.archetype_rows(catalog)
    if not archetypes:
        raise SystemExit("no translated archetypes")

    forged_path = os.path.join(MODULE, "client-patch", "forged_manifest.json")
    with open(forged_path, "r", encoding="utf-8") as source:
        forged = json.load(source)
    skill_line_id = str(forged.get("skill_line", {}).get("id", ""))
    skill_line_ru = catalog.get("skill_lines", {}).get(skill_line_id)
    if (not skill_line_ru or
            forged.get("skill_line", {}).get("ruRU") != skill_line_ru):
        raise SystemExit("forged client skill line ruRU name differs from the catalog")
    spell_rows = forged.get("spells", [])
    locale_support.apply_ruRU(forged, locale_support.load_catalog(), "spells")
    for row in spell_rows:
        localized = row.get("ruRU", {})
        for field in ("name", "rank_text", "description", "tooltip"):
            original = row.get(field, "")
            if original and not localized.get(field):
                raise SystemExit("missing forged spell %s translation at %s" %
                                 (field, row["id"]))
            if original:
                source_tokens = sorted(SPELL_TOKEN.findall(original))
                translated_tokens = sorted(SPELL_TOKEN.findall(localized[field]))
                if not spell_tokens_match(original, localized[field]):
                    raise SystemExit("spell placeholders differ at %s (%s): %r != %r" %
                                     (row["id"], field, source_tokens, translated_tokens))
    translated_spell_count = sum(bool(row.get("ruRU")) for row in spell_rows)

    forged_sql = os.path.join(MODULE, "data", "sql", "db-world", "cw_spells_forged.sql")
    sql_columns, sql_rows = gen_locales.read_insert_rows(forged_sql, "spell_dbc")
    sql_positions = {name: index for index, name in enumerate(sql_columns)}
    server_forged = {int(row[sql_positions["ID"]]): row for row in sql_rows}
    if set(server_forged) != {int(row["id"]) for row in spell_rows}:
        raise SystemExit("forged server SQL IDs differ from the client manifest")
    for row in spell_rows:
        ident = int(row["id"])
        server_row = server_forged[ident]
        for sql_field, locale_field in (
                ("Name_Lang_ruRU", "name"),
                ("NameSubtext_Lang_ruRU", "rank_text"),
                ("Description_Lang_ruRU", "description"),
                ("AuraDescription_Lang_ruRU", "tooltip")):
            server_text = gen_locales.unquote(server_row[sql_positions[sql_field]])
            reject_question_corruption(server_text,
                                       "forged_spell/%s/%s" % (ident, locale_field))
            if server_text != row.get("ruRU", {}).get(locale_field, ""):
                raise SystemExit("forged server/client ruRU mismatch at %s %s" %
                                 (ident, locale_field))

    title_sql_path = os.path.join(MODULE, "data", "sql", "db-world", "cw_spells_forged.sql")
    title_columns, title_rows = gen_locales.read_insert_rows(title_sql_path, "chartitles_dbc")
    title_positions = {name: index for index, name in enumerate(title_columns)}
    title_catalog = catalog.get("titles", {})
    if len(title_rows) != len(title_catalog):
        raise SystemExit("forged server title row count differs from ruRU title catalog")
    for row in title_rows:
        ident = str(int(row[title_positions["ID"]]))
        value = title_catalog[ident]
        reject_question_corruption(gen_locales.unquote(
            row[title_positions["Name_Lang_ruRU"]]), "title/%s/male" % ident)
        reject_question_corruption(gen_locales.unquote(
            row[title_positions["Name1_Lang_ruRU"]]), "title/%s/female" % ident)
        if (gen_locales.unquote(row[title_positions["Name_Lang_ruRU"]]) != value["male"]
                or gen_locales.unquote(row[title_positions["Name1_Lang_ruRU"]]) != value["female"]):
            raise SystemExit("forged server title ruRU form mismatch at id %s" % ident)

    elemental_path = os.path.join(MODULE, "client-patch", "elemental_manifest.json")
    with open(elemental_path, "r", encoding="utf-8") as source:
        elemental = json.load(source)
    locale_support.apply_ruRU(elemental, locale_support.load_catalog(), "variants")
    elemental_rows = elemental.get("variants", [])
    translated_elemental = sum(bool(row.get("ruRU")) for row in elemental_rows)
    for row in elemental_rows:
        localized = row.get("ruRU", {})
        for field in ("name", "rank_text", "description", "tooltip"):
            original = row.get(field, "")
            if original and not localized.get(field):
                raise SystemExit("missing elemental spell %s translation at %s" %
                                 (field, row["id"]))
            if original:
                source_tokens = sorted(SPELL_TOKEN.findall(original))
                translated_tokens = sorted(SPELL_TOKEN.findall(localized[field]))
                if source_tokens != translated_tokens and not spell_tokens_match(original, localized[field]):
                    raise SystemExit("elemental spell placeholders differ at %s (%s)" %
                                     (row["id"], field))

    elemental_sql_path = os.path.join(MODULE, "data", "sql", "db-world",
                                      "cw_zz_elemental_locale_ruRU.sql")
    with open(elemental_sql_path, "r", encoding="utf-8") as source:
        elemental_sql = source.read()
    for sql_field, locale_field in (
            ("Name_Lang_ruRU", "name"),
            ("NameSubtext_Lang_ruRU", "rank_text"),
            ("Description_Lang_ruRU", "description"),
            ("AuraDescription_Lang_ruRU", "tooltip")):
        match = re.search(r"`%s`\s*=\s*CASE `ID`(.*?)\s+ELSE" % sql_field,
                          elemental_sql, re.S)
        if not match:
            raise SystemExit("elemental locale SQL is missing %s" % sql_field)
        values = {int(ident): gen_locales.unquote(value)
                  for ident, value in re.findall(
                      r"WHEN\s+(\d+)\s+THEN\s+('(?:''|[^'])*')", match.group(1))}
        for row in elemental_rows:
            ident = int(row["id"])
            reject_question_corruption(values.get(ident, ""),
                                       "elemental_spell/%s/%s" % (ident, locale_field))
            if values.get(ident, "") != row.get("ruRU", {}).get(locale_field, ""):
                raise SystemExit("elemental server/client ruRU mismatch at %s %s" %
                                 (ident, locale_field))

    print("ruRU item coverage: %d/%d names and nonempty descriptions" %
          (len(source_items), len(source_items)))
    print("ruRU creature coverage: %d/%d names and titles" %
          (len(creature_ids), len(creature_ids)))
    print("ruRU archetype coverage: %d/%d names and descriptions" %
          (len(archetypes), len(archetypes)))
    print("ruRU command help coverage: %d/%d command nodes have locale-aware AcoreStrings" %
          (len(expected_ids), len(expected_ids)))
    print("ruRU forged spell coverage: %d/%d rows have localized fields and preserved placeholders" %
          (translated_spell_count, len(spell_rows)))
    print("ruRU forged skill line coverage: 1/1 name matches the locale catalog")
    print("ruRU elemental spell coverage: %d/%d rows currently have locale overlays" %
          (translated_elemental, len(elemental_rows)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
