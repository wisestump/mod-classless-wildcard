/*
 * mod-classless-wildcard -- vendor list layout (GENERATED)
 *
 * Do not hand-edit: regenerate with
 * data/sql/generators/gen_vendor_lists.py, which writes this header and
 * data/sql/db-world/cw_world_vendor_lists.sql from one description of the
 * shop, so the gossip menu and the npc_vendor rows cannot disagree.
 */

#ifndef MOD_CLASSLESS_VENDOR_LISTS_H
#define MOD_CLASSLESS_VENDOR_LISTS_H

#include <cstdint>

namespace ClasslessWildcard
{
    struct VendorList
    {
        uint32_t    entry;    // npc_vendor.entry
        uint8_t     category; // index into VENDOR_CATEGORIES
        char const* label;
        char const* labelRu;
        uint32_t    count;    // items in the list, for the menu text
        bool        whole;    // the category's everything-at-once list
    };

    struct VendorCategory
    {
        char const* name;
        char const* blurb;
        char const* nameRu;
        char const* blurbRu;
    };

    constexpr VendorCategory VENDOR_CATEGORIES[] =
    {
        { "Weapons", "every blade, bow, staff and wand", "Оружие", "все клинки, луки, посохи и жезлы" },
        { "Armor", "chest, legs, shoulders, cloaks and shields", "Доспехи", "нагрудники, поножи, наплечники, плащи и щиты" },
        { "Jewelry & off-hand", "necks, rings, trinkets and held items", "Украшения и предметы в левой руке", "ожерелья, кольца, аксессуары и предметы в левой руке" },
        { "Heirloom gear", "bought once, it scales with you to 80", "Наследуемое снаряжение", "покупается один раз и растёт вместе с вами до 80-го уровня" },
    };

    constexpr VendorList VENDOR_LISTS[] =
    {
        { 991000, 0, "Levels 1-20", "Уровни 1–20", 30, false },
        { 991001, 0, "Levels 21-40", "Уровни 21–40", 32, false },
        { 991002, 0, "Levels 41-60", "Уровни 41–60", 20, false },
        { 991003, 0, "Levels 61-80", "Уровни 61–80", 20, false },
        { 991004, 0, "All levels", "Все уровни", 102, true },
        { 991010, 1, "Levels 1-20", "Уровни 1–20", 36, false },
        { 991011, 1, "Levels 21-40", "Уровни 21–40", 34, false },
        { 991012, 1, "Levels 41-60", "Уровни 41–60", 24, false },
        { 991013, 1, "Levels 61-80", "Уровни 61–80", 24, false },
        { 991014, 1, "All levels", "Все уровни", 118, true },
        { 991020, 2, "Levels 1-20", "Уровни 1–20", 12, false },
        { 991021, 2, "Levels 21-40", "Уровни 21–40", 14, false },
        { 991022, 2, "Levels 41-60", "Уровни 41–60", 8, false },
        { 991023, 2, "Levels 61-80", "Уровни 61–80", 8, false },
        { 991024, 2, "All levels", "Все уровни", 42, true },
        { 991034, 3, "Heirloom gear", "Наследуемое снаряжение", 23, true },
    };

    // The supplies counter is the creature's own list, which
    // SendListInventory reaches with a vendor entry of 0.
    constexpr uint32_t VENDOR_LIST_SUPPLIES = 0;
}

#endif // MOD_CLASSLESS_VENDOR_LISTS_H
