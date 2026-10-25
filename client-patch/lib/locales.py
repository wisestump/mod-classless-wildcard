"""Load authored game text translations and overlay generated manifests."""

from __future__ import annotations

import json
import os
import re
import struct


def catalog_path():
    package = os.path.abspath(os.path.join(
        os.path.dirname(__file__), "..", "locales", "ruRU.json"))
    repository = os.path.abspath(os.path.join(
        os.path.dirname(__file__), "..", "..", "data", "locales", "ruRU.json"))
    # Player packages contain client-patch and client-addon only. Keep a
    # package-local catalog for those installs, while retaining the authored
    # module catalog as the source when working in a developer checkout.
    return package if os.path.isfile(package) else repository


def load_catalog():
    with open(catalog_path(), "r", encoding="utf-8") as source:
        catalog = json.load(source)
    spell_path = os.path.join(os.path.dirname(catalog_path()), "spell_texts_ruRU.json")
    if os.path.isfile(spell_path):
        with open(spell_path, "r", encoding="utf-8") as source:
            catalog["spell_texts"] = json.load(source)
    elemental_path = os.path.join(os.path.dirname(catalog_path()), "elemental_texts_ruRU.json")
    if os.path.isfile(elemental_path):
        with open(elemental_path, "r", encoding="utf-8") as source:
            catalog["elemental_texts"] = json.load(source)
    return catalog


def _normalize_spell_text(text):
    return re.sub(r"(?<=[;$])\d{6}(?=[a-zA-Z])", "@ID@", text)


def _restore_spell_ids(template, source_text):
    references = re.findall(r"(?<=[;$])(\d{6})(?=[a-zA-Z])", source_text)
    localized = template
    for reference in references:
        localized = localized.replace("@ID@", reference, 1)
    if "@ID@" in localized:
        raise ValueError("localized spell text has more numeric tokens than its source")
    return localized


def _spell_text_translation(source, field, text_catalog):
    if not source:
        return ""
    if field == "name":
        translation = text_catalog.get("names", {}).get(source)
    elif field == "rank_text":
        translation = text_catalog.get("rank_texts", {}).get(source)
    else:
        translation = text_catalog.get("texts", {}).get(_normalize_spell_text(source))
    if translation is None:
        raise ValueError("missing ruRU forged spell %s translation: %s" % (field, source))
    return _restore_spell_ids(translation, source)


def _base_spell_locale_strings(files):
    """Read ruRU base names/ranks from the client's own Spell.dbc."""
    from . import dbc

    data, _archive = files.find("DBFilesClient\\Spell.dbc")
    rows, fields, record_size, string_size = dbc.parse_header(data)
    if fields != 234 or record_size != 936:
        raise ValueError("client Spell.dbc layout is not 3.3.5a")
    records_start = 20
    strings_start = records_start + rows * record_size
    strings = data[strings_start:strings_start + string_size]
    result = {}
    # The client's DBC locale list places ruRU at slot 8. This differs from
    # AzerothCore's generated SQL column order, which is handled by its writer.
    locale = 8
    for row_index in range(rows):
        offset = records_start + row_index * record_size
        spell_id = struct.unpack_from("<I", data, offset)[0]
        name_at = struct.unpack_from("<I", data, offset + (136 + locale) * 4)[0]
        rank_at = struct.unpack_from("<I", data, offset + (153 + locale) * 4)[0]
        result[spell_id] = (dbc.read_string(strings, name_at),
                            dbc.read_string(strings, rank_at))
    return result


def _elemental_variant_translation(record, catalog, base_spell_text):
    text_catalog = catalog.get("elemental_texts", {})
    element_key = record.get("element")
    element = text_catalog.get("elements", {}).get(element_key)
    if not element:
        raise ValueError("missing ruRU elemental text for element %s" % element_key)

    base_name = record.get("base_name")
    if not base_name:
        base_name = text_catalog.get("source_name_overrides", {}).get(record.get("name"))
    if not base_name:
        prefix = text_catalog.get("source_prefixes", {}).get(element_key)
        if prefix and record.get("name", "").startswith(prefix + " "):
            base_name = record["name"][len(prefix) + 1:]
    if not base_name or base_name not in text_catalog.get("descriptions", {}):
        raise ValueError("missing ruRU elemental description template for %s" %
                         (base_name or record.get("name")))

    ru_name, ru_rank = base_spell_text.get(int(record["base"]), ("", ""))
    if not ru_name:
        raise ValueError("ruRU client Spell.dbc has no base name for spell %s" % record["base"])
    # Keep the base ability recognizable at the start of the name; the element
    # is a modifier and follows it after the colon. Lowercase only its first
    # word so proper names such as "Свет" retain their capitalization.
    prefix = element["prefix"]
    prefix = prefix[:1].lower() + prefix[1:]
    name = "%s: %s" % (ru_name, prefix)
    rank = ru_rank if record.get("rank_text") else ""
    if record.get("rank_text") and not rank:
        rank = "Ранг %d" % int(record.get("rank", 1))

    description = text_catalog["descriptions"][base_name]
    description = description.replace("{E}", element["word"])
    source_words = {"fire": "Fire", "frost": "Frost", "earth": "Nature",
                    "poison": "Nature", "arcane": "Arcane", "shadow": "Shadow",
                    "holy": "Holy"}
    hit_clause = "plus $s2 %s damage" % source_words[element_key] in record.get("description", "")
    if element_key in ("arcane", "holy") or hit_clause:
        inline = text_catalog["hit_text"].replace("{E}", element["word"])
        description = description.replace("{payload}", inline)
    else:
        description = description.replace("{payload}", "")
        if record.get("tooltip"):
            description += element["payload"].replace("{E}", element["word"])
    if element_key == "holy":
        description += text_catalog["heal_text"].replace("{percent}", "25")
    tooltip = element.get("aura_tip", "").replace("{E}", element["word"])
    return {"name": name, "rank_text": rank,
            "description": description, "tooltip": tooltip}


def apply_ruRU(manifest: dict, catalog: dict, section: str, id_field: str = "id",
               files=None):
    """Overlay localized fields by stable numeric ID; English source stays intact."""
    translations = catalog.get(section, {})
    base_spell_text = _base_spell_locale_strings(files) if section == "variants" and files else None
    for record in manifest.get(section, []):
        localized = translations.get(str(record.get(id_field, "")))
        if section == "spells" and not localized:
            text_catalog = catalog.get("spell_texts", {})
            localized = {}
            for field in ("name", "rank_text", "description", "tooltip"):
                value = record.get(field, "")
                if value:
                    localized[field] = _spell_text_translation(value, field, text_catalog)
            if not localized:
                continue
        elif section == "variants":
            if base_spell_text is None and record.get("ruRU"):
                continue
            if base_spell_text is None:
                raise ValueError("ruRU elemental variants require the recipient client's Spell.dbc")
            localized = _elemental_variant_translation(record, catalog, base_spell_text)
        if localized:
            record["ruRU"] = dict(localized)
    return manifest


def clear_ruRU(manifest: dict, section: str) -> dict:
    """Keep ruRU overlays out of a patch built for another locale."""
    for record in manifest.get(section, []):
        record.pop("ruRU", None)
    return manifest

