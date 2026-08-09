Scriptname Actor extends ObjectReference Native

Bool Function IsDead() Native
Bool Function IsInCombat() Native
Bool Function IsEssential() Native
Function SetEssential(Bool abEssential) Native
Bool Function IsGhost() Native
Bool Function IsChild() Native
Bool Function IsPlayerTeammate() Native
; FO4 native — teammate follow/sneak; not CurrentCompanionFaction / Followers quest.
Function SetPlayerTeammate(Bool abTeammate = True, Bool abCanDoFavor = True, Bool abGivePlayerXP = False) Native
Bool Function IsInFaction(Faction akFaction) Native
Bool Function IsHostileToActor(Actor akActor) Native
; FO4 native — fires on this actor when their location changes (player alias warp hook).
Event OnLocationChange(Location akOldLoc, Location akNewLoc)
EndEvent
; HasKeyword / GetValue / SetValue / ModValue / GetHeadingAngle / Is3DLoaded /
; Disable / Enable / IsDisabled live on ObjectReference — do not redeclare here.
Actor Function GetCombatTarget() Native
Bool Function HasSpell(Form akSpell) Native
Bool Function HasMagicEffect(MagicEffect akEffect) Native
Bool Function HasPerk(Perk akPerk) Native
; FO4 native — abNotify shows the perk unlock UI when true.
Function AddPerk(Perk akPerk, Bool abNotify = False) Native
; FO4 native — remove a perk previously added with AddPerk.
Function RemovePerk(Perk akPerk) Native
; FO4 native — opens the barter/trade menu with this actor.
Function ShowBarterMenu() Native
; FO4 native — companion/container inventory UI (not barter prices).
Function OpenInventory(Bool abForceOpen = False) Native
Bool Function AddSpell(Spell akSpell, Bool abVerbose = True) Native
Bool Function RemoveSpell(Spell akSpell) Native
Function DispelSpell(Spell akSpell) Native
Function DoCombatSpellApply(Spell akSpell, ObjectReference akTarget) Native
ActorBase Function GetLeveledActorBase() Native
Function StartCombat(Actor akTarget, Bool abPreferredTarget = False) Native
Function StopCombat() Native
Function StopCombatAlarm() Native
Function SetAttackActorOnSight(Bool abAttackOnSight = True) Native
Function SetRelationshipRank(Actor akOther, Int aiRank) Native
Function EvaluatePackage(Bool abResetAI = False) Native
; FO4 native — latent path to a ref. afWalkRunPercent 0..1 (1.0 = run).
Bool Function PathToReference(ObjectReference aTarget, Float afWalkRunPercent) Native
Function SetGhost(Bool abIsGhost) Native
Function SetRestrained(Bool abRestrained) Native
Function SetUnconscious(Bool abUnconscious) Native
Function Resurrect() Native
Function Kill(Actor akKiller = None) Native
; FO4 native — kill without OnDeath kill-event attribution noise.
Function KillSilent(Actor akKiller = None) Native
; FO4 native — add/remove HeadPart (SFT face bruises). Often needs QueueUpdate; weak on frozen corpses.
Function ChangeHeadPart(HeadPart apHeadPart, Bool abRemovePart = False, Bool abRemoveExtraParts = False) Native
; F4SE native — rebuild actor 3D. First arg is equipment refresh; flags=0 is full/expensive.
Function QueueUpdate(Bool bDoEquipment = False, Int flags = 0) Native
; FO4 native — near-instantly enter furniture/mount (fails if seat occupied / no 3D).
Bool Function SnapIntoInteraction(ObjectReference akTarget) Native
; FO4 native — 0 not sleeping, 2 wants sleep, 3 sleeping, 4 wants wake.
Int Function GetSleepState() Native
; FO4 native — detection LOS (player may check non-actors). Not Skyrim HasLOS.
Bool Function HasDetectionLOS(ObjectReference akOther) Native

; FO4 native — body part strings match CK Body Part Data (e.g. "Head1", "LeftArm1").
; For corpses: abForceDismember=True, abForceExplode=False. Prefer abForceBloodyMess=False —
; True often gibs/explodes the head instead of a clean sever.
Function Dismember(String asBodyPart, Bool abForceExplode = False, Bool abForceDismember = False, Bool abForceBloodyMess = False) Native
Bool Function IsDismembered(String asBodyPart) Native
Event OnPlayerLoadGame()
EndEvent
Weapon Function GetEquippedWeapon(Int aiEquipIndex = 0) Native
Bool Function IsEquipped(Form akItem) Native
; FO4 native — forces equip; abPreventRemoval=false keeps playable gear removable.
Function EquipItem(Form akItem, Bool abPreventRemoval = False, Bool abSilent = False) Native
; FO4 native — unequip worn gear (pair with RemoveAllItems to strip corpses).
Function UnequipAll() Native
Function UnequipItem(Form akItem, Bool abPreventEquip = False, Bool abSilent = False) Native
; FO4 native — set this actor's worn outfit (ref-level; prefer over ActorBase.SetOutfit).
Function SetOutfit(Outfit akOutfit, Bool abSleepOutfit = False) Native
; FO4 native — true if any currently worn/equipped item has the keyword (incl. OMOD-injected).
Bool Function WornHasKeyword(Keyword akKeyword) Native
Event OnItemEquipped(Form akBaseObject, ObjectReference akReference)
EndEvent
Event OnItemUnequipped(Form akBaseObject, ObjectReference akReference)
EndEvent
Event OnItemAdded(Form akBaseItem, Int aiItemCount, ObjectReference akItemReference, ObjectReference akSourceContainer)
EndEvent
Event OnItemRemoved(Form akBaseItem, Int aiItemCount, ObjectReference akItemReference, ObjectReference akDestContainer)
EndEvent
Event OnDeath(Actor akKiller)
EndEvent
Event OnCombatStateChanged(Actor akTarget, Int aeCombatState)
EndEvent
