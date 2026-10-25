"""Rewrite the character-creation screen's class copy to the classless pitch.

The 3.3.5a creation screen reads two kinds of string out of
Interface\\GlueXML\\GlueStrings.lua:

    CLASS_<TOKEN>            the long paragraph, |n for line breaks
    CLASS_<TOKEN>_FEMALE     the same paragraph, female phrasing
    CLASS_INFO_<TOKEN><N>    the short bullet list, N = 0..5

Every class token gets the same Hero copy, so whichever chassis a player picks
reads identically. Only those keys are touched; the other ~860 strings in the
file are passed through byte for byte.
"""

from __future__ import annotations

import re

CLASS_TOKENS = ("WARRIOR", "PALADIN", "HUNTER", "ROGUE", "PRIEST",
                "DEATHKNIGHT", "SHAMAN", "MAGE", "WARLOCK", "DRUID")

PARAGRAPH = (
    "Every character is a {name}. Every spell, talent, weapon and armor type "
    "in the game is yours to learn: buy what you want with Ability Essence, "
    "or let the Wildcard deal abilities and talents to you as you level."
    "|n|n"
    "Every {name} shares the same base stats, health and resources, so "
    "nothing you can learn is ever locked away. Your race keeps its own "
    "racial traits, so choose the race and appearance you want to play."
)

BULLETS = (
    "- Role: anything. Tank, healer, caster or melee.",
    "- Wears every armor type and wields every weapon.",
    "- Carries mana, rage and energy at the same time.",
    "- Allocate your own primary stats, and reallocate them freely.",
    "- Learn any spell or talent from any class.",
    "- In game press N, or visit a Hero Advancement NPC in any major city.",
)

PARAGRAPH_RURU = (
    "Каждый персонаж — {name}. Вы можете изучить любое заклинание и талант, "
    "владеть любым оружием и носить любую броню: покупайте способности за "
    "эссенцию способностей или получайте их случайным образом в режиме "
    "«Случайный путь».|n|n"
    "У всех {name} одинаковые базовые характеристики, здоровье и ресурсы, "
    "поэтому доступ к способностям не зависит от класса. Расовые особенности "
    "сохраняются — выберите подходящие расу и внешность."
)

BULLETS_RURU = (
    "- Любая роль: танк, целитель, заклинатель или боец.",
    "- Доступны все типы брони и любое оружие.",
    "- Одновременно доступны мана, ярость и энергия.",
    "- Распределяйте основные характеристики и бесплатно меняйте их.",
    "- Изучайте заклинания и таланты любого класса.",
    "- Нажмите N в игре или найдите наставника героя в крупном городе.",
)

_ASSIGNMENT = re.compile(
    r'^(?P<key>[A-Z0-9_]+)(?P<gap>\s*=\s*)"(?P<value>(?:\\.|[^"\\])*)"',
    re.MULTILINE)


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def build_replacements(name: str = "Hero", locale: str = "enUS"):
    """Map every class string key to its Hero replacement."""
    out = {}
    russian = locale.lower() == "ruru"
    display_name = "Герой" if russian and name == "Hero" else name
    paragraph = (PARAGRAPH_RURU if russian else PARAGRAPH).format(name=display_name)
    bullets = BULLETS_RURU if russian else BULLETS
    for token in CLASS_TOKENS:
        out["CLASS_%s" % token] = paragraph
        out["CLASS_%s_FEMALE" % token] = paragraph
        for index, bullet in enumerate(bullets):
            out["CLASS_INFO_%s%d" % (token, index)] = bullet
    return out


def rewrite(text: str, name: str = "Hero", locale: str = "enUS"):
    """Return (new_text, keys_replaced).

    Keys already present are rewritten in place. Bullet slots a class does not
    have are not invented: the client only reads the indexes it knows about,
    and adding more would leave stray text nothing displays.
    """
    replacements = build_replacements(name, locale)
    replaced = []

    def substitute(match):
        key = match.group("key")
        if key not in replacements:
            return match.group(0)
        replaced.append(key)
        return '%s%s"%s"' % (key, match.group("gap"),
                             _escape(replacements[key]))

    new_text = _ASSIGNMENT.sub(substitute, text)
    return new_text, replaced
