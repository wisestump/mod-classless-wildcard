/*
 * mod-classless-wildcard
 * Copyright (C) 2026 Dustin Hendrickson
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 */

#ifndef MOD_CW_CLASSLESS_LOCALE_H
#define MOD_CW_CLASSLESS_LOCALE_H

#include "DBCStores.h"
#include "Player.h"
#include "StringFormat.h"

#include <string>
#include <unordered_map>
#include <utility>

namespace ClasslessWildcard
{
    inline bool IsRussian(Player* player)
    {
        // Module-authored text follows the player's requested locale. The DBC
        // locale may be remapped to the server's default when this host does
        // not have the requested locale's DBC files installed.
        return player && player->GetSession()
            && player->GetSession()->GetSessionDbLocaleIndex() == LOCALE_ruRU;
    }

    inline std::string LocaleText(Player* player, char const* english, char const* russian)
    {
        return IsRussian(player) ? russian : english;
    }

    inline std::string LocaleError(Player* player, std::string const& error)
    {
        if (!IsRussian(player))
            return error;
        static std::unordered_map<std::string, std::string> const translations = {
            { "Archetypes are build templates for the Classless path.", "Архетипы доступны только на свободном пути." },
            { "You are not following an archetype.", "Вы не следуете архетипу." },
            { "Unknown archetype.", "Неизвестный архетип." },
            { "No archetype has that id.", "Архетип с таким идентификатором не найден." },
            { "This character does not walk the Hero's path.", "Этот персонаж не следует пути героя." },
            { "Choose your path first.", "Сначала выберите путь." },
            { "Rebirth is disabled on this realm.", "Перерождение отключено на этом игровом мире." },
            { "You can only carry an ability you own.", "Можно сохранить только уже изученную способность." },
            { "You already hold an extra life for your next run.", "У вас уже есть дополнительная жизнь для следующего испытания." },
            { "Buying scrolls is disabled on this realm.", "Покупка свитков отключена на этом игровом мире." },
            { "Your bags are full.", "Ваши сумки полны." },
            { "This character is not a Hero.", "Этот персонаж не является Героем." },
            { "Pick mana, rage or energy.", "Выберите ману, ярость или энергию." },
            { "That challenge does not exist.", "Такого испытания не существует." },
            { "You already know that ability.", "Вы уже знаете эту способность." },
            { "Elemental variants are not available on this realm.", "Элементальные варианты способностей недоступны на этом игровом мире." },
            { "You do not own that ability.", "У вас нет этой способности." },
            { "You do not own that talent.", "У вас нет этого таланта." },
            { "That ability came with a talent and leaves with it. Respec to give it up.",
              "Эта способность получена вместе с талантом и исчезнет вместе с ним. Сбросьте таланты, чтобы отказаться от неё." },
            { "That came free with another ability. Unlearn the one it came with instead.",
              "Эта способность получена бесплатно вместе с другой. Забудьте исходную способность." },
            { "That came free with another ability. Reroll the one it came with instead.",
              "Эта способность получена бесплатно вместе с другой. Перебросьте исходную способность." },
            { "That is an heirloom carried through Rebirth. It stays with you.",
              "Это унаследованная способность, сохранённая при Перерождении. Она останется с вами." },
            { "That is an heirloom carried through Rebirth. It is not rerolled.",
              "Это унаследованная способность, сохранённая при Перерождении. Её нельзя перебросить." },
            { "Unlearning is a Classless-path feature. Wildcard Heroes reroll instead.",
              "Забывание способностей доступно на свободном пути. Герои случайного пути могут перебрасывать их." },
            { "Respec is only available on the Classless path (Wildcard Heroes reroll instead).",
              "Сброс доступен только на свободном пути. Герои случайного пути могут перебрасывать способности." },
            { "That talent is already at max rank.", "Этот талант уже достиг максимального ранга." },
            { "Unknown talent.", "Неизвестный талант." },
            { "Rerolls are a Wildcard mechanic.", "Перебросы доступны только на случайном пути." },
            { "No rerolls on Dealt Hand. You play what you are dealt.", "В испытании «Сданная рука» перебросы запрещены. Играйте тем, что получили." },
            { "That ability is locked. Unlock it first.", "Эта способность закреплена. Сначала открепите её." },
            { "That ability came with a talent. Reroll the talent instead.",
              "Эта способность получена вместе с талантом. Перебросьте сам талант." },
            { "That is already your path.", "Вы уже выбрали этот путь." },
            { "Stat allocation is disabled on this realm.", "Распределение характеристик отключено на этом игровом мире." },
            { "Nothing to reroll: everything is locked.", "Нечего перебрасывать: все способности закреплены." },
            { "That is a talent you cannot buy.", "Этот талант нельзя изучить." }
        };
        auto itr = translations.find(error);
        return itr == translations.end() ? error : itr->second;
    }

    inline std::string LocaleCount(Player* player, uint32 count, char const* englishOne, char const* englishOther,
                                   char const* russianOne, char const* russianFew, char const* russianMany)
    {
        if (!IsRussian(player))
            return count == 1 ? englishOne : englishOther;
        uint32 const lastTwo = count % 100;
        uint32 const last = count % 10;
        if (last == 1 && lastTwo != 11)
            return russianOne;
        if (last >= 2 && last <= 4 && (lastTwo < 12 || lastTwo > 14))
            return russianFew;
        return russianMany;
    }

    template <typename... Args>
    std::string LocaleFormat(Player* player, char const* english, char const* russian, Args&&... args)
    {
        return Acore::StringFormat(IsRussian(player) ? russian : english, std::forward<Args>(args)...);
    }
}

#endif
