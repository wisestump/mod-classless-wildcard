"""Generate localized .classless/.wildcard command help.

The AzerothCore ChatCommandBuilder accepts an AcoreStrings ID, so help text is
loaded from acore_string by the player's SQL locale. The Russian strings live
in data/locales/ruRU.json; this file owns the English defaults, command paths,
symbols and the reserved module ID range.
"""
from __future__ import print_function

import io
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, os.pardir, os.pardir, os.pardir))
RU_PATH = os.path.join(ROOT, "data", "locales", "ruRU.json")
SQL_PATH = os.path.join(ROOT, "data", "sql", "db-world", "cw_world_commands.sql")
HEADER_PATH = os.path.join(ROOT, "src", "ClasslessCommandHelp.h")
COMMAND_SOURCE_PATH = os.path.join(ROOT, "src", "ClasslessCommands.cpp")

# Reserved for this module. AzerothCore currently uses ids through 35482 in
# Language.h. 15,990,000..15,990,018 is below the acore_string MEDIUMINT-safe
# ceiling requested by the module and is not used anywhere else in this repo.
ID_MIN = 15_990_000
ID_MAX = 15_990_018
MEDIUMINT_UNSIGNED_MAX = 16_777_215

# command, symbol suffix, id, enUS help (the ruRU text is canonical in JSON)
COMMANDS = [
    ("classless status", "CLASSLESS_STATUS", 15_990_000,
     "Syntax: .classless status\nShows your path, abilities and talents, essence, reroll charges and reroll cooldowns."),
    ("classless mode", "CLASSLESS_MODE", 15_990_001,
     "Syntax: .classless mode classless|wildcard\nChooses your path. Only before your path locks."),
    ("classless learn", "CLASSLESS_LEARN", 15_990_002,
     "Syntax: .classless learn $spellId\nBuys an ability with Ability Essence. Classless path only."),
    ("classless unlearn", "CLASSLESS_UNLEARN", 15_990_003,
     "Syntax: .classless unlearn $spellId\nUnlearns an ability and refunds its Ability Essence. Classless path only."),
    ("classless talent", "CLASSLESS_TALENT", 15_990_004,
     "Syntax: .classless talent $talentId\nBuys the next rank of a talent with Talent Essence. Classless path only."),
    ("classless respec", "CLASSLESS_RESPEC", 15_990_005,
     "Syntax: .classless respec\nUnlearns every ability and talent and refunds all essence. Free. Classless path only."),
    ("classless stats", "CLASSLESS_STATS", 15_990_006,
     "Syntax: .classless stats\nShows your primary stat allocation and unspent points."),
    ("classless stat", "CLASSLESS_STAT", 15_990_007,
     "Syntax: .classless stat str|agi|sta|int|spi $points\nPuts points into a primary stat. Reallocating is free."),
    ("classless bar", "CLASSLESS_BAR", 15_990_008,
     "Syntax: .classless bar mana|rage|energy|default\nChooses which resource the main power bar shows."),
    ("classless archetypes", "CLASSLESS_ARCHETYPES", 15_990_009,
     "Syntax: .classless archetypes\nLists the archetypes and their IDs."),
    ("classless archetype", "CLASSLESS_ARCHETYPE", 15_990_010,
     "Syntax: .classless archetype $id\nFollows an archetype, replacing your build. 0 stops following. Classless path only."),
    ("classless rebirth", "CLASSLESS_REBIRTH", 15_990_011,
     "Syntax: .classless rebirth [$abilityId ...] confirm\nAt the level cap: back to level 1 on your path with a permanent Rebirth rank, carrying the listed heirloom abilities. Without confirm, shows what it will do."),
    ("classless challenges", "CLASSLESS_CHALLENGES", 15_990_012,
     "Syntax: .classless challenges\nLists the challenge runs with their IDs, lives and rewards."),
    ("classless run", "CLASSLESS_RUN", 15_990_013,
     "Syntax: .classless run $id\nStarts a challenge run on a new character, before its path is locked in. .classless challenges lists the IDs."),
    ("classless nemesis", "CLASSLESS_NEMESIS", 15_990_014,
     "Syntax: .classless nemesis\nShows your Nemesis and the available actions for the current challenge run."),
    ("wildcard status", "WILDCARD_STATUS", 15_990_015,
     "Syntax: .wildcard status\nShows your path, abilities and talents, reroll charges, synergy chance and reroll cooldowns."),
    ("wildcard reroll", "WILDCARD_REROLL", 15_990_016,
     "Syntax: .wildcard reroll $spellId\nRerolls an ability you own. Free below the free-reroll level, then a reroll charge or a Reroll Scroll."),
    ("wildcard rerolltalent", "WILDCARD_REROLLTALENT", 15_990_017,
     "Syntax: .wildcard rerolltalent $talentId [$scrolls]\nRerolls a talent you own. Each staked scroll adds a chance to keep the talent and raise its rank instead."),
    ("wildcard lock", "WILDCARD_LOCK", 15_990_018,
     "Syntax: .wildcard lock $spellId\nPadlocks or unlocks an ability in your Starting Hand."),
]


def sql_quote(value):
    return value.replace("'", "''").replace("\\", "\\\\").replace("\n", "\\r\\n")


def placeholders(value):
    return sorted(set(re.findall(r"\$[A-Za-z][A-Za-z0-9]*", value)))


def validate(translations):
    commands = [row[0] for row in COMMANDS]
    ids = [row[2] for row in COMMANDS]
    symbols = [row[1] for row in COMMANDS]
    if len(set(commands)) != len(commands):
        raise ValueError("duplicate command path")
    if len(set(ids)) != len(ids) or len(set(symbols)) != len(symbols):
        raise ValueError("duplicate command-help ID/symbol")
    if set(ids) != set(range(ID_MIN, ID_MAX + 1)):
        raise ValueError("command-help ID range changed without updating reservation")
    if max(ids) > MEDIUMINT_UNSIGNED_MAX:
        raise ValueError("command-help ID exceeds unsigned MEDIUMINT")
    if set(translations) != set(commands):
        missing = sorted(set(commands) - set(translations))
        extra = sorted(set(translations) - set(commands))
        raise ValueError("command-help catalog mismatch (missing=%r extra=%r)" % (missing, extra))
    for command, _symbol, _ident, default in COMMANDS:
        translated = translations[command]
        if not isinstance(translated, str) or not translated.strip():
            raise ValueError("empty ruRU help for %s" % command)
        if placeholders(default) != placeholders(translated):
            raise ValueError("placeholder mismatch in command help for %s" % command)

    with io.open(COMMAND_SOURCE_PATH, "r", encoding="utf-8") as source:
        cpp = source.read()
    actual = {}
    for table, prefix in (("classlessTable", "classless"), ("wildcardTable", "wildcard")):
        match = re.search(r"static ChatCommandTable %s\s*=\s*\{(.*?)\n\s*\};" % table,
                          cpp, re.S)
        if not match:
            raise ValueError("cannot find %s in ClasslessCommands.cpp" % table)
        for row in re.finditer(
                r'\{\s*"([^"]+)"\s*,\s*\w+\s*,\s*(CW_HELP_[A-Z_]+)\s*,\s*SEC_PLAYER\s*,\s*Console::No\s*\}',
                match.group(1)):
            actual[prefix + " " + row.group(1)] = row.group(2)
    expected_symbols = {command: "CW_HELP_" + symbol
                        for command, symbol, _ident, _default in COMMANDS}
    if actual != expected_symbols:
        raise ValueError("ChatCommandBuilder/help catalog mismatch (builder=%r catalog=%r)" %
                         (actual, expected_symbols))


def write_sql(translations):
    ids = ", ".join(str(row[2]) for row in COMMANDS)
    lines = [
        "-- Generated by data/sql/generators/gen_command_help.py from",
        "-- data/locales/ruRU.json. IDs 15990000-15990018 are owned by this module.",
        "-- Command permissions are supplied by ChatCommandBuilder in C++; this",
        "-- sidecar deliberately does not insert English into command.help.",
        "DELETE FROM `command` WHERE `name` IN (",
        "    'classless', 'classless status', 'classless mode', 'classless learn',",
        "    'classless unlearn', 'classless talent', 'classless respec', 'classless stats',",
        "    'classless stat', 'classless bar', 'classless archetypes', 'classless archetype',",
        "    'classless rebirth', 'classless challenges', 'classless run', 'classless nemesis',",
        "    'wildcard', 'wildcard status', 'wildcard reroll', 'wildcard rerolltalent', 'wildcard lock'",
        ");",
        "DELETE FROM `acore_string` WHERE `entry` IN (%s);" % ids,
        "INSERT INTO `acore_string` (`entry`, `content_default`, `locale_ruRU`) VALUES",
    ]
    rows = []
    for command, _symbol, ident, default in COMMANDS:
        ru = translations[command]
        rows.append("(%d, '%s', '%s')" %
                    (ident, sql_quote(default), sql_quote(ru)))
    lines.append(",\n".join(rows) + ";")
    with io.open(SQL_PATH, "w", encoding="utf-8", newline="\n") as out:
        out.write("\n".join(lines) + "\n")


def write_header():
    lines = [
        "/* Generated by data/sql/generators/gen_command_help.py. Do not edit. */",
        "#ifndef MOD_CW_CLASSLESS_COMMAND_HELP_H",
        "#define MOD_CW_CLASSLESS_COMMAND_HELP_H",
        "",
        '#include "Language.h"',
        "",
        "namespace ClasslessWildcard",
        "{",
        "    // Reserved acore_string IDs: 15,990,000-15,990,018 (unsigned MEDIUMINT-safe).",
    ]
    for _command, symbol, ident, _default in COMMANDS:
        lines.append("    constexpr AcoreStrings CW_HELP_%s = static_cast<AcoreStrings>(%d);" % (symbol, ident))
    lines.extend(["}", "", "#endif // MOD_CW_CLASSLESS_COMMAND_HELP_H", ""])
    with io.open(HEADER_PATH, "w", encoding="utf-8", newline="\n") as out:
        out.write("\n".join(lines))


def main():
    with io.open(RU_PATH, "r", encoding="utf-8") as source:
        data = json.load(source)
    translations = data.get("command_help", {})
    validate(translations)
    write_sql(translations)
    write_header()
    print("generated %d localized command-help strings" % len(COMMANDS))


if __name__ == "__main__":
    main()
