#!/usr/bin/env python3
"""Write repeatable ruRU rows for the module's own world objects."""

from __future__ import annotations

import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
MODULE = os.path.abspath(os.path.join(HERE, os.pardir, os.pardir, os.pardir))
SOURCE = os.path.join(MODULE, "data", "locales", "ruRU.json")
OUTPUT = os.path.join(MODULE, "data", "sql", "db-world", "cw_zz_locale_ruRU.sql")
WORLD = os.path.join(MODULE, "data", "sql", "db-world")
ARCHETYPE_OUTPUT = os.path.join(WORLD, "cw_archetypes_locale.sql")
ITEM_FILES = ["cw_world_base.sql", "cw_items_pack.sql", "cw_items_pack2.sql",
              "cw_items_heirlooms.sql", "cw_items_tiered.sql",
              "cw_world_nemesis_items.sql"]


def sql(value: str) -> str:
    return "'" + value.replace("\\", "\\\\").replace("'", "''") + "'"


def split_values(text: str) -> list[str]:
    """Split one SQL VALUES tuple without splitting quoted commas."""
    parts, current, quoted, index = [], [], False, 0
    while index < len(text):
        char = text[index]
        if quoted:
            current.append(char)
            if char == "'":
                if index + 1 < len(text) and text[index + 1] == "'":
                    current.append("'")
                    index += 1
                else:
                    quoted = False
        elif char == "'":
            quoted = True
            current.append(char)
        elif char == ",":
            parts.append("".join(current).strip())
            current = []
        else:
            current.append(char)
        index += 1
    parts.append("".join(current).strip())
    return parts


def read_insert_rows(path: str, table: str) -> tuple[list[str], list[list[str]]]:
    """Read rows from a simple generated INSERT INTO ... VALUES statement."""
    with open(path, "r", encoding="utf-8") as source:
        text = source.read()
    text = re.sub(r"(?m)^\s*--.*$", "", text)
    match = re.search(r"INSERT INTO `?" + re.escape(table) +
                      r"`?\s*\((.*?)\)\s*VALUES\s*", text, re.S | re.I)
    if not match:
        return [], []
    columns = [column.strip().strip("`") for column in
               match.group(1).replace("\n", " ").split(",")]
    body = text[match.end():]
    quoted = False
    terminator = -1
    cursor = 0
    while cursor < len(body):
        char = body[cursor]
        if quoted:
            if char == "'":
                if cursor + 1 < len(body) and body[cursor + 1] == "'":
                    cursor += 1
                else:
                    quoted = False
        elif char == "'":
            quoted = True
        elif char == ";":
            terminator = cursor
            break
        cursor += 1
    if terminator >= 0:
        body = body[:terminator]
    rows, index = [], 0
    while index < len(body):
        start = body.find("(", index)
        if start < 0:
            break
        quoted, depth, end = False, 1, start + 1
        while end < len(body) and depth:
            char = body[end]
            if quoted:
                if char == "'":
                    if end + 1 < len(body) and body[end + 1] == "'":
                        end += 1
                    else:
                        quoted = False
            elif char == "'":
                quoted = True
            elif char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
            end += 1
        if depth:
            raise ValueError("unclosed VALUES tuple in " + path)
        rows.append(split_values(body[start + 1:end - 1]))
        index = end
    return columns, rows


def unquote(value: str) -> str:
    value = value.strip()
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1].replace("''", "'").replace("\\'", "'").replace("\\\\", "\\")
    return value


def item_rows() -> list[dict[str, object]]:
    rows = []
    for filename in ITEM_FILES:
        columns, values = read_insert_rows(os.path.join(WORLD, filename), "item_template")
        if not columns:
            continue
        positions = {name: index for index, name in enumerate(columns)}
        for value in values:
            if len(value) != len(columns):
                raise ValueError("malformed item_template row in " + filename)
            rows.append({
                "entry": int(value[positions["entry"]]),
                "name": unquote(value[positions["name"]]),
                "description": unquote(value[positions["description"]])
                if "description" in positions else "",
            })
    return rows


def item_locale(row: dict[str, object], catalog: dict) -> dict[str, str] | None:
    """Resolve explicit id translations, reusable templates, and tier suffixes."""
    entry, name, description = str(row["entry"]), str(row["name"]), str(row["description"])
    explicit = catalog.get("items", {}).get(entry)
    if explicit:
        return {"name": explicit["name"], "description": explicit.get("description", "")}

    templates = catalog.get("item_templates", {})
    if name in templates.get("special_names", {}):
        return {"name": templates["special_names"][name],
                "description": templates.get("special_descriptions", {}).get(description, "")}

    tier_suffixes = templates.get("tier_suffixes", {})
    for prefix in sorted(tier_suffixes, key=len, reverse=True):
        marker = prefix + " "
        if name.startswith(marker):
            base = name[len(marker):]
            translated = templates.get("names", {}).get(base)
            translated_desc = templates.get("descriptions", {}).get(description)
            if translated and (not description or translated_desc):
                return {"name": translated + " " + tier_suffixes[prefix],
                        "description": translated_desc or ""}
            return None

    trophy = re.fullmatch(r"Trophy of (Bloodlust|Ironhide|Spellward|Venomous|Unyielding|Warband|Relentless) (I{1,3})", name)
    if trophy:
        trophy_map = templates.get("nemesis_trophies", {})
        title = templates.get("nemesis_trophy_genitives", {}).get(trophy.group(1))
        description_match = re.match(r"(\d+) stars? of (.+?)\. Works from your bags on a Nemesis run\. It cannot leave your bags\.", description)
        if title and description_match:
            effects = trophy_map.get("effects", {})
            effect = effects.get(description_match.group(2))
            if effect:
                count = description_match.group(1)
                return {"name": "Трофей " + title + " " + trophy.group(2),
                        "description": "%s звезда: %s. Действует из сумки во время похода Немезиды. Нельзя вынести из похода." % (count, effect)}
        return None

    translated_name = templates.get("names", {}).get(name)
    translated_desc = templates.get("descriptions", {}).get(description)
    if not translated_name:
        return None
    if description and not translated_desc:
        return None
    return {"name": translated_name, "description": translated_desc or ""}


def expected_creature_entries() -> set[int]:
    """IDs defined by the module's own fixed creature SQL and generated vendor lists."""
    entries: set[int] = set()
    for filename in ("cw_world_base.sql", "cw_world_challenges.sql",
                     "cw_z_summon_templates.sql"):
        columns, rows = read_insert_rows(os.path.join(WORLD, filename), "creature_template")
        if columns:
            entry_column = columns.index("entry")
            entries.update(int(row[entry_column]) for row in rows)
    vendor_sql = os.path.join(WORLD, "cw_world_vendor_lists.sql")
    with open(vendor_sql, "r", encoding="utf-8") as source:
        text = source.read()
    entries.update(int(entry) for entry in re.findall(
        r"UPDATE `cw_vlist` SET `entry`\s*=\s*(\d+)", text))
    return entries


def archetype_rows(catalog: dict) -> list[tuple[int, dict[str, str]]]:
    columns, rows = read_insert_rows(os.path.join(WORLD, "cw_archetypes.sql"), "cw_archetypes")
    if not columns:
        raise SystemExit("cw_archetypes.sql has no generated archetype rows")
    positions = {name: index for index, name in enumerate(columns)}
    expected = {int(row[positions["id"]]) for row in rows}
    local = catalog.get("archetypes", {})
    supplied = {int(entry) for entry in local}
    if expected != supplied:
        raise SystemExit("archetype locale catalog mismatch; missing=%s stale=%s" %
                         (sorted(expected - supplied), sorted(supplied - expected)))
    result = []
    for row in rows:
        entry = int(row[positions["id"]])
        value = local[str(entry)]
        if len(value["name"]) > 64 or len(value["description"]) > 255:
            raise SystemExit("archetype ruRU text exceeds schema limits at id %d" % entry)
        result.append((entry, value))
    return result


def write_archetype_locales(entries: list[tuple[int, dict[str, str]]]) -> None:
    ids = ", ".join(str(entry) for entry, _value in entries)
    lines = ["-- Generated from data/locales/ruRU.json by gen_locales.py.",
             "SET NAMES utf8mb4;", "",
             "CREATE TABLE IF NOT EXISTS `cw_archetypes_locale` (",
             "  `archetype_id` INT UNSIGNED NOT NULL,",
             "  `locale` VARCHAR(4) NOT NULL,",
             "  `name` VARCHAR(64) NOT NULL,",
             "  `description` VARCHAR(255) NOT NULL DEFAULT '',",
             "  PRIMARY KEY (`archetype_id`, `locale`)",
             ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;",
             "DELETE FROM `cw_archetypes_locale` WHERE `locale` = 'ruRU' AND `archetype_id` IN (%s);" % ids,
             "INSERT INTO `cw_archetypes_locale` (`archetype_id`, `locale`, `name`, `description`) VALUES"]
    for index, (entry, value) in enumerate(entries):
        ending = ";" if index == len(entries) - 1 else ","
        lines.append("(%d, 'ruRU', %s, %s)%s" %
                     (entry, sql(value["name"]), sql(value["description"]), ending))
    with open(ARCHETYPE_OUTPUT, "w", encoding="utf-8", newline="\n") as output:
        output.write("\n".join(lines) + "\n")


def main() -> None:
    with open(SOURCE, "r", encoding="utf-8") as source:
        catalog = json.load(source)

    lines = ["-- Generated from data/locales/ruRU.json by gen_locales.py.",
             "SET NAMES utf8mb4;", ""]

    # Derive every current item ID from the English source SQL. This keeps
    # translated rows attached to regenerated items and makes missing strings
    # a hard error instead of silently shipping English tooltips.
    all_items = item_rows()
    translated_items = []
    missing_items = []
    for row in all_items:
        localized = item_locale(row, catalog)
        if localized is None:
            missing_items.append((row["entry"], row["name"], row["description"]))
        else:
            translated_items.append((int(row["entry"]), localized))
    if missing_items:
        preview = "; ".join("%s: %s" % (entry, name) for entry, name, _desc in missing_items[:12])
        raise SystemExit("missing ruRU item name/description translations for %d/%d items: %s" %
                         (len(missing_items), len(all_items), preview))

    expected_creatures = expected_creature_entries()
    creatures = catalog.get("creatures", {})
    missing_creatures = sorted(expected_creatures - {int(entry) for entry in creatures})
    stale_creatures = sorted({int(entry) for entry in creatures} - expected_creatures)
    if missing_creatures or stale_creatures:
        raise SystemExit("creature locale catalog mismatch; missing=%s stale=%s" %
                         (missing_creatures, stale_creatures))
    archetypes = archetype_rows(catalog)

    creatures = catalog.get("creatures", {})
    if creatures:
        entries = sorted(int(entry) for entry in creatures)
        listed = ", ".join(str(entry) for entry in entries)
        lines.append("DELETE FROM `creature_template_locale` "
                     "WHERE `locale` = 'ruRU' AND `entry` IN (%s);" % listed)
        lines.append("INSERT INTO `creature_template_locale` (`entry`, `locale`, `Name`, `Title`) VALUES")
        for index, entry in enumerate(entries):
            value = creatures[str(entry)]
            ending = ";" if index == len(entries) - 1 else ","
            lines.append("(%d, 'ruRU', %s, %s)%s" % (
                entry, sql(value["name"]), sql(value.get("subname", "")), ending))
        lines.append("")

    if translated_items:
        entries = sorted(translated_items, key=lambda item: item[0])
        ids = [entry for entry, _value in entries]
        listed = ", ".join(str(entry) for entry in ids)
        lines.append("DELETE FROM `item_template_locale` "
                     "WHERE `locale` = 'ruRU' AND `ID` IN (%s);" % listed)
        lines.append("INSERT INTO `item_template_locale` (`ID`, `locale`, `Name`, `Description`) VALUES")
        for index, (entry, value) in enumerate(entries):
            ending = ";" if index == len(entries) - 1 else ","
            lines.append("(%d, 'ruRU', %s, %s)%s" % (
                entry, sql(value["name"]), sql(value.get("description", "")), ending))
        lines.append("")

    with open(OUTPUT, "w", encoding="utf-8", newline="\n") as output:
        output.write("\n".join(lines))
    write_archetype_locales(archetypes)
    print("wrote %s (%d creature and %d item translations)" % (
        os.path.normpath(OUTPUT), len(creatures), len(translated_items)))
    print("wrote %s (%d translated archetypes)" %
          (os.path.normpath(ARCHETYPE_OUTPUT), len(archetypes)))


if __name__ == "__main__":
    main()
