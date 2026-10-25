-- Generated from gen_forged_spells.py; reapply summon records after legacy vendor cleanup.
-- The creatures the Hero line summons. Markers carry no AI and the spell's
-- own area effect does the work; the Reclaimed Sentry is driven by
-- npc_cw_reclaimed_sentry, and the Venom Beetle is a pet.
DELETE FROM `creature_template` WHERE `entry` IN (990110, 990111, 990118, 990119, 990112, 990113, 990114, 990115, 990117);
INSERT INTO `creature_template`
  (`entry`, `name`, `subname`, `minlevel`, `maxlevel`, `faction`, `npcflag`, `unit_class`,
   `unit_flags`, `type`, `type_flags`, `RegenHealth`, `flags_extra`, `speed_walk`, `speed_run`, `DamageModifier`, `HealthModifier`, `ScriptName`, `VerifiedBuild`)
VALUES
(990110, 'Bulwark Anchor', '', 1, 80, 35, 0, 1, 33554438, 11, 0, 1, 66, 1.0, 1.14286, 1.00, 1.00, '', 12340),
(990111, 'Reclaimed Sentry', '', 1, 80, 35, 0, 1, 33554438, 11, 0, 1, 66, 1.0, 1.14286, 1.00, 1.00, 'npc_cw_reclaimed_sentry', 12340),
(990118, 'Reclaimed Sentry', '', 1, 80, 35, 0, 1, 33554438, 11, 0, 1, 66, 1.0, 1.14286, 1.00, 1.00, 'npc_cw_reclaimed_sentry', 12340),
(990119, 'Reclaimed Sentry', '', 1, 80, 35, 0, 1, 33554438, 11, 0, 1, 66, 1.0, 1.14286, 1.00, 1.00, 'npc_cw_reclaimed_sentry', 12340),
(990112, 'Cairn', '', 1, 80, 35, 0, 1, 33554438, 11, 0, 1, 66, 1.0, 1.14286, 1.00, 1.00, '', 12340),
(990113, 'Waystone', '', 1, 80, 35, 0, 1, 33554438, 11, 0, 1, 66, 1.0, 1.14286, 1.00, 1.00, '', 12340),
(990114, 'Signal Fire', '', 1, 80, 35, 0, 1, 33554438, 11, 0, 1, 66, 1.0, 1.14286, 1.00, 1.00, '', 12340),
(990115, 'Rally Point', '', 1, 80, 35, 0, 1, 33554438, 11, 0, 1, 66, 1.0, 1.14286, 1.00, 1.00, '', 12340),
(990117, 'Venom Beetle', '', 1, 80, 35, 0, 1, 0, 3, 0, 1, 64, 1.0, 1.0, 1.00, 1.00, '', 12340);

-- Models live in their own table. Without a row here a summon
-- spawns invisible.
DELETE FROM `creature_template_model` WHERE `CreatureID` IN (990110, 990111, 990118, 990119, 990112, 990113, 990114, 990115, 990117);
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`, `VerifiedBuild`) VALUES
(990110, 0, 31124, 0.90, 1, 12340),
(990111, 0, 19218, 1.00, 1, 12340),
(990118, 0, 19218, 1.00, 1, 12340),
(990119, 0, 19218, 1.00, 1, 12340),
(990112, 0, 25931, 1.00, 1, 12340),
(990113, 0, 30886, 1.00, 1, 12340),
(990114, 0, 22993, 0.50, 1, 12340),
(990115, 0, 27399, 1.00, 1, 12340),
(990117, 0, 15464, 0.33, 1, 12340);

-- What the pet knows. Creature.cpp copies these into m_spells, and
-- InitCharmCreateSpells puts each one on the pet bar with an autocast
-- toggle. A creature holds ONE list, so each rank is its own creature.
DELETE FROM `creature_template_spell` WHERE `CreatureID` IN (990111, 990117, 990118, 990119);
INSERT INTO `creature_template_spell` (`CreatureID`, `Index`, `Spell`, `VerifiedBuild`) VALUES
(990117, 0, 961040, 12340),
(990117, 1, 961041, 12340),
(990117, 2, 961042, 12340),
(990117, 3, 961043, 12340),
(990111, 0, 960336, 12340),
(990118, 0, 960337, 12340),
(990119, 0, 960338, 12340);

