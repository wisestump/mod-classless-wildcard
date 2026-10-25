/*
 * mod-classless-wildcard
 * Copyright (C) 2026 Dustin Hendrickson
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
 * General Public License for more details.
 *
 * .classless and .wildcard command families — the scriptable counterpart
 * of the Hero Advancement NPC (also the surface a client addon would drive).
 */

#include "Chat.h"
#include "ChatCommand.h"
#include "ClasslessCommandHelp.h"
#include "ClasslessLocale.h"
#include "ClasslessMgr.h"
#include "Player.h"
#include "ScriptMgr.h"
#include "SpellInfo.h"
#include "SpellMgr.h"
#include "StringConvert.h"
#include "StringFormat.h"
#include "Tokenize.h"

#include <algorithm>

using namespace Acore::ChatCommands;
using namespace ClasslessWildcard;

namespace
{
    template <typename... Args>
    void SendFormatted(ChatHandler* handler, std::string const& format, Args const&... args)
    {
        handler->SendSysMessage(Acore::StringFormat(format, args...));
    }
}

class classless_commandscript : public CommandScript
{
public:
    classless_commandscript() : CommandScript("classless_commandscript") { }

    ChatCommandTable GetCommands() const override
    {
        static ChatCommandTable classlessTable =
        {
            { "status",  HandleStatus,        CW_HELP_CLASSLESS_STATUS, SEC_PLAYER, Console::No },
            { "mode",    HandleMode,          CW_HELP_CLASSLESS_MODE, SEC_PLAYER, Console::No },
            { "learn",   HandleLearn,         CW_HELP_CLASSLESS_LEARN, SEC_PLAYER, Console::No },
            { "unlearn", HandleUnlearn,       CW_HELP_CLASSLESS_UNLEARN, SEC_PLAYER, Console::No },
            { "talent",  HandleTalent,        CW_HELP_CLASSLESS_TALENT, SEC_PLAYER, Console::No },
            { "respec",  HandleRespec,        CW_HELP_CLASSLESS_RESPEC, SEC_PLAYER, Console::No },
            { "stats",   HandleStats,         CW_HELP_CLASSLESS_STATS, SEC_PLAYER, Console::No },
            { "stat",    HandleStat,          CW_HELP_CLASSLESS_STAT, SEC_PLAYER, Console::No },
            { "bar",     HandleBar,           CW_HELP_CLASSLESS_BAR, SEC_PLAYER, Console::No },
            { "archetypes", HandleArchetypes, CW_HELP_CLASSLESS_ARCHETYPES, SEC_PLAYER, Console::No },
            { "archetype", HandleArchetype,   CW_HELP_CLASSLESS_ARCHETYPE, SEC_PLAYER, Console::No },
            { "rebirth", HandleRebirth,       CW_HELP_CLASSLESS_REBIRTH, SEC_PLAYER, Console::No },
            { "challenges", HandleChallenges, CW_HELP_CLASSLESS_CHALLENGES, SEC_PLAYER, Console::No },
            { "run",     HandleRun,           CW_HELP_CLASSLESS_RUN, SEC_PLAYER, Console::No },
            { "nemesis", HandleNemesis,       CW_HELP_CLASSLESS_NEMESIS, SEC_PLAYER, Console::No },
        };
        static ChatCommandTable wildcardTable =
        {
            { "status",  HandleStatus,        CW_HELP_WILDCARD_STATUS, SEC_PLAYER, Console::No },
            { "reroll",  HandleReroll,        CW_HELP_WILDCARD_REROLL, SEC_PLAYER, Console::No },
            { "rerolltalent", HandleRerollTalent, CW_HELP_WILDCARD_REROLLTALENT, SEC_PLAYER, Console::No },
            { "lock",    HandleLock,          CW_HELP_WILDCARD_LOCK, SEC_PLAYER, Console::No },
        };
        static ChatCommandTable root =
        {
            { "classless", classlessTable },
            { "wildcard",  wildcardTable },
        };
        return root;
    }

    static bool CheckEnabled(ChatHandler* handler)
    {
        if (!sClasslessMgr->cfg.enabled)
        {
            handler->SendSysMessage(LocaleText(handler->GetSession()->GetPlayer(), "Hero Advancement is disabled on this realm.", "Развитие героя отключено на этом игровом мире."));
            return false;
        }
        return true;
    }

    static bool HandleStatus(ChatHandler* handler)
    {
        if (!CheckEnabled(handler))
            return true;
        Player* player = handler->GetSession()->GetPlayer();
        CharState& st = sClasslessMgr->GetState(player);

        SendFormatted(handler, LocaleText(player, "Path: {}", "Путь: {}"), st.mode == Mode::Wildcard
            ? LocaleText(player, "Wildcard", "Случайный") : (st.mode == Mode::Classless
                ? LocaleText(player, "Classless", "Свободный") : LocaleText(player, "not chosen yet", "ещё не выбран")));
        SendFormatted(handler, LocaleText(player, "Abilities: {} | Talents: {}", "Способностей: {} | талантов: {}"),
            st.abilities.size(), st.talents.size());
        if (st.mode == Mode::Classless)
        {
            SendFormatted(handler, LocaleText(player, "Ability Essence: {} | Talent Essence: {}", "Эссенция способностей: {} | эссенция талантов: {}"),
                st.abilityEssence, st.talentEssence);
            if (st.archetype)
            {
                std::string next;
                auto queue = sClasslessMgr->ArchetypeQueue(player);
                if (!queue.empty())
                    next = queue.front().second > player->GetLevel()
                        ? Acore::StringFormat(LocaleText(player, " (next: {} at level {})", " (далее: {} на уровне {})"),
                            sClasslessMgr->SpellNameOf(queue.front().first, player), uint32(queue.front().second))
                        : Acore::StringFormat(LocaleText(player, " (next: {}, when you have the Ability Essence)",
                            " (далее: {}, когда будет эссенция способностей)"), sClasslessMgr->SpellNameOf(queue.front().first, player));
                SendFormatted(handler, LocaleText(player, "Following: |cffffff00{}|r{}", "Выбран архетип: |cffffff00{}|r{}"),
                    sClasslessMgr->ArchetypeName(st, player), next);
            }
        }
        if (st.mode == Mode::Wildcard)
        {
            SendFormatted(handler, LocaleText(player,
                "Reroll charges: {} (you earn {} every level from level {}; each rerolls an ability or a talent)",
                "Заряды переброса: {} (вы получаете {} за уровень, начиная с уровня {}; каждый позволяет перебросить способность или талант)"),
                st.rerolls, sClasslessMgr->cfg.wcRerollsPerLevel, sClasslessMgr->cfg.wcRollStartLevel);
            SendFormatted(handler, LocaleText(player, "Synergy chance: {}% (rises each time you reroll)",
                "Шанс синергии: {}% (увеличивается после каждого переброса)"),
                std::min<uint32>(sClasslessMgr->cfg.wcSynergyBaseChance + st.pity * sClasslessMgr->cfg.wcSynergyIncrement, 100));
            if (st.bans.empty())
                SendFormatted(handler, LocaleText(player, "On reroll cooldown: none", "Ожидающих переброса способностей нет."));
            else
            {
                // Show the shortest remaining wait, so the number means
                // something: cooldowns run in ROLLS, and on the shipped cadence
                // a Hero gets one roll per level.
                int32 soonest = st.bans.front().rollsLeft;
                for (auto const& ban : st.bans)
                    soonest = std::min(soonest, ban.rollsLeft);
                uint32 const wait = uint32(std::max<int32>(0, soonest));
                SendFormatted(handler,
                    LocaleText(player,
                        "On reroll cooldown: {} (things you rerolled; the next one returns in {} roll{})",
                        "На перезарядке переброса: {} (следующая способность вернётся через {} переброс{})"),
                    uint32(st.bans.size()), wait, "");
            }
        }
        return true;
    }

    static bool HandleMode(ChatHandler* handler, std::string modeArg)
    {
        if (!CheckEnabled(handler))
            return true;
        Player* player = handler->GetSession()->GetPlayer();

        std::string err;
        if (modeArg == "classless")
            sClasslessMgr->SetMode(player, Mode::Classless, &err);
        else if (modeArg == "wildcard")
            sClasslessMgr->SetMode(player, Mode::Wildcard, &err);
        else
        {
            handler->SendSysMessage(LocaleText(player, "Usage: .classless mode classless | wildcard",
                "Использование: .classless mode classless | wildcard"));
            return true;
        }
        if (!err.empty())
            handler->SendSysMessage(LocaleError(handler->GetSession()->GetPlayer(), err));
        return true;
    }

    static bool HandleLearn(ChatHandler* handler, uint32 spellId)
    {
        if (!CheckEnabled(handler))
            return true;
        std::string err;
        if (!sClasslessMgr->BuyAbility(handler->GetSession()->GetPlayer(), spellId, &err) && !err.empty())
            handler->SendSysMessage(LocaleError(handler->GetSession()->GetPlayer(), err));
        return true;
    }

    static bool HandleUnlearn(ChatHandler* handler, uint32 spellId)
    {
        if (!CheckEnabled(handler))
            return true;
        std::string err;
        if (!sClasslessMgr->UnlearnAbility(handler->GetSession()->GetPlayer(), spellId, &err) && !err.empty())
            handler->SendSysMessage(LocaleError(handler->GetSession()->GetPlayer(), err));
        return true;
    }

    static bool HandleTalent(ChatHandler* handler, uint32 talentId)
    {
        if (!CheckEnabled(handler))
            return true;
        std::string err;
        if (!sClasslessMgr->BuyTalentRank(handler->GetSession()->GetPlayer(), talentId, &err) && !err.empty())
            handler->SendSysMessage(LocaleError(handler->GetSession()->GetPlayer(), err));
        return true;
    }

    static bool HandleRespec(ChatHandler* handler)
    {
        if (!CheckEnabled(handler))
            return true;
        std::string err;
        if (!sClasslessMgr->Respec(handler->GetSession()->GetPlayer(), &err) && !err.empty())
            handler->SendSysMessage(LocaleError(handler->GetSession()->GetPlayer(), err));
        return true;
    }

    static int8 StatIndexFromName(std::string const& name)
    {
        if (name == "str") return 0;
        if (name == "agi") return 1;
        if (name == "sta") return 2;
        if (name == "int") return 3;
        if (name == "spi") return 4;
        return -1;
    }

    static bool HandleBar(ChatHandler* handler, std::string barName)
    {
        if (!CheckEnabled(handler))
            return true;
        Player* player = handler->GetSession()->GetPlayer();
        uint8 idx = 255;
        if (barName == "mana") idx = 0;
        else if (barName == "rage") idx = 1;
        else if (barName == "energy") idx = 3;
        else if (barName != "default")
        {
            handler->SendSysMessage(LocaleText(player, "Usage: .classless bar mana|rage|energy|default",
                "Использование: .classless bar mana|rage|energy|default"));
            return true;
        }
        std::string err;
        if (sClasslessMgr->SetDisplayPower(player, idx, &err))
            SendFormatted(handler, LocaleText(player, "Main resource bar set to {}.", "Основная шкала ресурса: {}."), barName);
        else
            SendFormatted(handler, "{}", LocaleError(player, err));
        return true;
    }

    static bool HandleStats(ChatHandler* handler)
    {
        if (!CheckEnabled(handler))
            return true;
        Player* player = handler->GetSession()->GetPlayer();
        CharState& st = sClasslessMgr->GetState(player);
        uint32 budget = sClasslessMgr->StatBudget(player);
        uint32 spent = sClasslessMgr->SpentStatPoints(st);
        uint32 v = sClasslessMgr->cfg.statValuePerPoint;
        SendFormatted(handler, LocaleText(player,
            "Stat points: {} spent / {} total ({} unspent). Each point grants +{} stat.",
            "Очки характеристик: потрачено {} из {} (свободно {}). Каждое очко даёт +{} к характеристике."),
            spent, budget, budget > spent ? budget - spent : 0, v);
        SendFormatted(handler, LocaleText(player, "STR {} | AGI {} | STA {} | INT {} | SPI {} (points)",
            "СИЛ {} | ЛОВ {} | ВЫН {} | ИНТ {} | ДУХ {} (очков)"),
            st.statAlloc[0], st.statAlloc[1], st.statAlloc[2], st.statAlloc[3], st.statAlloc[4]);
        handler->SendSysMessage(LocaleText(player,
            "Set one with: .classless stat str|agi|sta|int|spi <points>. Reallocation is free.",
            "Задать значения: .classless stat str|agi|sta|int|spi <points>. Перераспределение бесплатно."));
        return true;
    }

    static bool HandleStat(ChatHandler* handler, std::string statName, uint32 points)
    {
        if (!CheckEnabled(handler))
            return true;
        int8 index = StatIndexFromName(statName);
        if (index < 0)
        {
            handler->SendSysMessage(LocaleText(handler->GetSession()->GetPlayer(),
                "Usage: .classless stat str|agi|sta|int|spi <points>",
                "Использование: .classless stat str|agi|sta|int|spi <points>"));
            return true;
        }
        Player* player = handler->GetSession()->GetPlayer();
        std::array<uint32, 5> alloc = sClasslessMgr->GetState(player).statAlloc;
        alloc[index] = points;
        std::string err;
        if (!sClasslessMgr->SetStatAllocation(player, alloc, &err) && !err.empty())
            handler->SendSysMessage(LocaleError(handler->GetSession()->GetPlayer(), err));
        return true;
    }

    static bool HandleArchetypes(ChatHandler* handler)
    {
        if (!CheckEnabled(handler))
            return true;
        uint32 following = sClasslessMgr->GetState(handler->GetSession()->GetPlayer()).archetype;
        for (auto const& [id, arch] : sClasslessMgr->Archetypes())
        {
            uint32 const ranks = arch.TalentRanks();
            SendFormatted(handler, LocaleText(handler->GetSession()->GetPlayer(),
                "{}. |cffffff00{}|r: {} ({} abilities, {} talent ranks, level 1 to 80){}",
                "{}. |cffffff00{}|r: {} (способностей: {}, рангов талантов: {}, уровни 1–80){}"),
                id, sClasslessMgr->ArchetypeName(id, handler->GetSession()->GetPlayer()),
                sClasslessMgr->ArchetypeDescription(id, handler->GetSession()->GetPlayer()),
                uint32(arch.abilities.size()), ranks,
                following == id ? " |cff00ff00following|r" : "");
        }
        if (sClasslessMgr->Archetypes().empty())
            handler->SendSysMessage(LocaleText(handler->GetSession()->GetPlayer(), "No archetypes are available.", "Нет доступных архетипов."));
        else
            handler->SendSysMessage(LocaleText(handler->GetSession()->GetPlayer(),
                "Follow one with: .classless archetype <id>   Stop with: .classless archetype 0",
                "Выбрать: .classless archetype <id>. Отключить: .classless archetype 0"));
        return true;
    }

    static bool HandleArchetype(ChatHandler* handler, uint32 archetypeId)
    {
        if (!CheckEnabled(handler))
            return true;
        std::string err;
        if (!sClasslessMgr->ApplyArchetype(handler->GetSession()->GetPlayer(), archetypeId, &err) && !err.empty())
            handler->SendSysMessage(LocaleError(handler->GetSession()->GetPlayer(), err));
        return true;
    }

    static bool ParsePath(std::string const& modeArg, Mode& target)
    {
        if (modeArg == "classless")
            target = Mode::Classless;
        else if (modeArg == "wildcard")
            target = Mode::Wildcard;
        else
            return false;
        return true;
    }

    // The ability ids in a command's tail, and whether it ends in "confirm".
    // Rebirth wipes the build, so the
    // command describes what will happen until it is repeated with confirm.
    static std::vector<uint32> ParseIdsAndConfirm(Tail args, bool& confirmed)
    {
        std::vector<uint32> ids;
        confirmed = false;
        for (std::string_view token : Acore::Tokenize(args, ' ', false))
        {
            if (token == "confirm")
                confirmed = true;
            else if (Optional<uint32> id = Acore::StringTo<uint32>(token))
                ids.push_back(*id);
        }
        return ids;
    }

    static std::string IdList(std::vector<uint32> const& ids)
    {
        std::string out;
        for (uint32 id : ids)
            out += Acore::StringFormat(" {}", id);
        return out;
    }

    static void DescribeRebirth(ChatHandler* handler, Player* player, std::string const& command, bool keepQuests)
    {
        SendFormatted(handler, LocaleText(player,
            "This sends you back to level 1 for {} gold. Your build is wiped{} and your worn "
            "gear goes into your bags (by mail if they are full); gold, bank, reputation, riding, flight paths and the heirlooms you list stay.",
            "Вы начнёте новую жизнь с 1-го уровня за {} золотых. Сборка будет сброшена{}, а надетое снаряжение попадёт в сумки (или будет отправлено почтой, если сумки полны); золото, банк, репутация, навык верховой езды, маршруты полёта и указанные унаследованные способности сохранятся."),
            sClasslessMgr->RebirthCost(sClasslessMgr->GetState(player)),
            LocaleText(player, keepQuests ? ", your quests are kept," : " along with your quest progress,",
                keepQuests ? ", задания сохраняются," : " вместе с вашим прогрессом заданий,"));
        if (!keepQuests)
            SendFormatted(handler, LocaleText(player, "To keep your quests, add keepquests: {} keepquests confirm",
                "Чтобы сохранить задания, добавьте keepquests: {} keepquests confirm"), command);
        SendFormatted(handler, LocaleText(player, "Type {}{} confirm to go ahead.", "Для подтверждения введите {}{} confirm."),
            command, keepQuests ? " keepquests" : "");
    }

    // ".classless rebirth [heirloom ability id ...] [keepquests] [confirm]":
    // New Game Plus, at the level cap, on the character's own path. The ids
    // are owned ability lines carried through; keepquests keeps the quest
    // log. The panel is the friendlier way to choose them.
    static bool HandleRebirth(ChatHandler* handler, Tail heirloomArgs)
    {
        if (!CheckEnabled(handler))
            return true;
        std::string err;
        bool confirmed;
        std::vector<uint32> heirlooms = ParseIdsAndConfirm(heirloomArgs, confirmed);
        bool keepQuests = false;
        for (std::string_view token : Acore::Tokenize(heirloomArgs, ' ', false))
            if (token == "keepquests")
                keepQuests = true;
        Player* player = handler->GetSession()->GetPlayer();
        if (!confirmed && sClasslessMgr->RebirthEligible(player))
        {
            DescribeRebirth(handler, player, ".classless rebirth" + IdList(heirlooms), keepQuests);
            return true;
        }
        if (!sClasslessMgr->Rebirth(player, heirlooms, keepQuests, &err) && !err.empty())
            handler->SendSysMessage(LocaleError(handler->GetSession()->GetPlayer(), err));
        return true;
    }

    // ".classless challenges": the list, with lives, reward and best result.
    static bool HandleChallenges(ChatHandler* handler)
    {
        if (!CheckEnabled(handler))
            return true;
        Player* player = handler->GetSession()->GetPlayer();
        CharState& st = sClasslessMgr->GetState(player);
        handler->SendSysMessage(Acore::StringFormat(LocaleText(player,
            "Challenge runs, started before level {} with .classless run <id>:",
            "Испытания. Начните до достижения {} уровня командой .classless run <id>:"),
            uint32(sClasslessMgr->cfg.modeChoiceDeadline)));
        for (Challenge const& ch : ClasslessMgr::Challenges())
        {
            auto best = st.runBest.find(ch.id);
            std::string const lives = ch.lives == UNLIMITED_LIVES
                ? LocaleText(player, "unlimited lives", "неограниченное число жизней")
                : Acore::StringFormat("{} {}", uint32(ch.lives),
                    LocaleCount(player, ch.lives, "life", "lives", "жизнь", "жизни", "жизней"));
            handler->SendSysMessage(Acore::StringFormat(LocaleText(player,
                "  {}. |cffffd100{}|r  {}, {} gold.  {}{}",
                "  {}. |cffffd100{}|r  {}, награда: {} золотых.  {}{}"),
                uint32(ch.id), sClasslessMgr->ChallengeName(ch, player), lives, ch.rewardGold,
                sClasslessMgr->ChallengeText(ch.rule, player),
                best == st.runBest.end() ? ""
                    : Acore::StringFormat(LocaleText(player, "  Best: level {}{}", "  Лучший результат: уровень {}{}"),
                        uint32(best->second.first), best->second.second
                            ? LocaleText(player, ", finished", " (пройдено)") : "")));
        }
        if (st.run)
            if (Challenge const* ch = ClasslessMgr::GetChallenge(st.run))
            {
                if (st.livesMax == UNLIMITED_LIVES)
                    handler->SendSysMessage(Acore::StringFormat(LocaleText(player,
                        "Current run: |cffffd100{}|r, unlimited lives.",
                        "Текущее испытание: |cffffd100{}|r, жизни не ограничены."),
                        sClasslessMgr->ChallengeName(*ch, player)));
                else
                    handler->SendSysMessage(Acore::StringFormat(LocaleText(player,
                        "Current run: |cffffd100{}|r, {} of {} left.",
                        "Текущее испытание: |cffffd100{}|r, осталось {} из {}."),
                        sClasslessMgr->ChallengeName(*ch, player), uint32(st.lives), uint32(st.livesMax)));
            }
        handler->SendSysMessage(Acore::StringFormat(LocaleText(player, "Shards: {}.", "Осколки: {}."), st.shards));
        return true;
    }

    // ".classless run <id>": start a challenge run, before ModeChoiceDeadline.
    // Each nemesis as the server sees it: where it is, its level and size,
    // and whether it carries your minimap mark.
    static bool HandleNemesis(ChatHandler* handler)
    {
        if (!CheckEnabled(handler))
            return true;
        for (std::string const& line : sClasslessMgr->NemesisReport(handler->GetSession()->GetPlayer()))
            handler->SendSysMessage(line);
        return true;
    }

    static bool HandleRun(ChatHandler* handler, uint32 challengeId)
    {
        if (!CheckEnabled(handler))
            return true;
        std::string err;
        Player* player = handler->GetSession()->GetPlayer();
        if (!sClasslessMgr->StartRun(player, uint8(challengeId), &err) && !err.empty())
            handler->SendSysMessage(LocaleError(handler->GetSession()->GetPlayer(), err));
        return true;
    }

    static bool HandleReroll(ChatHandler* handler, uint32 spellId)
    {
        if (!CheckEnabled(handler))
            return true;
        std::string err;
        if (!sClasslessMgr->Reroll(handler->GetSession()->GetPlayer(), false, spellId, &err) && !err.empty())
            handler->SendSysMessage(LocaleError(handler->GetSession()->GetPlayer(), err));
        return true;
    }

    static bool HandleRerollTalent(ChatHandler* handler, uint32 talentId, Optional<uint32> scrolls)
    {
        if (!CheckEnabled(handler))
            return true;
        std::string err;
        if (!sClasslessMgr->Reroll(handler->GetSession()->GetPlayer(), true, talentId, &err,
                                   scrolls.value_or(0)) && !err.empty())
            handler->SendSysMessage(LocaleError(handler->GetSession()->GetPlayer(), err));
        return true;
    }

    static bool HandleLock(ChatHandler* handler, uint32 spellId)
    {
        if (!CheckEnabled(handler))
            return true;
        std::string err;
        if (!sClasslessMgr->ToggleLock(handler->GetSession()->GetPlayer(), spellId, &err) && !err.empty())
            handler->SendSysMessage(LocaleError(handler->GetSession()->GetPlayer(), err));
        return true;
    }
};

void AddClasslessCommandScripts()
{
    new classless_commandscript();
}
