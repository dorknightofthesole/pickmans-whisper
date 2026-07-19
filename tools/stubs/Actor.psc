Scriptname Actor extends ObjectReference Native

Bool Function IsDead() Native
Bool Function IsInCombat() Native
Bool Function IsGhost() Native
Bool Function IsChild() Native
Bool Function IsPlayerTeammate() Native
Bool Function IsHostileToActor(Actor akActor) Native
Bool Function HasKeyword(Keyword akKeyword) Native
Actor Function GetCombatTarget() Native
Bool Function HasSpell(Form akSpell) Native
Bool Function HasMagicEffect(MagicEffect akEffect) Native
Bool Function AddSpell(Spell akSpell, Bool abVerbose = True) Native
Bool Function RemoveSpell(Spell akSpell) Native
Function DispelSpell(Spell akSpell) Native
Function DoCombatSpellApply(Spell akSpell, ObjectReference akTarget) Native
Float Function GetValue(ActorValue akAV) Native
Function SetValue(ActorValue akAV, Float afValue) Native
Function ModValue(ActorValue akAV, Float afAmount) Native
Float Function GetHeadingAngle(ObjectReference akOther) Native
ActorBase Function GetLeveledActorBase() Native
Function StartCombat(Actor akTarget) Native
Function StopCombat() Native
Function EvaluatePackage() Native
Function SetGhost(Bool abIsGhost) Native
Function SetRestrained(Bool abRestrained) Native
Function SetUnconscious(Bool abUnconscious) Native
Function Resurrect() Native
Function Kill(Actor akKiller = None) Native
Function Disable(Bool abFadeOut = False) Native
Function Enable(Bool abFadeIn = False) Native
Bool Function IsDisabled() Native
Bool Function Is3DLoaded() Native
; FO4 native — 0 not sleeping, 2 wants sleep, 3 sleeping, 4 wants wake.
Int Function GetSleepState() Native

; FO4 native — body part strings match CK Body Part Data (e.g. "Head1", "LeftArm1").
; For corpses: abForceDismember=True, abForceExplode=False. Prefer abForceBloodyMess=False —
; True often gibs/explodes the head instead of a clean sever.
Function Dismember(String asBodyPart, Bool abForceExplode = False, Bool abForceDismember = False, Bool abForceBloodyMess = False) Native
Bool Function IsDismembered(String asBodyPart) Native
Event OnPlayerLoadGame()
EndEvent
Weapon Function GetEquippedWeapon(Int aiEquipIndex = 0) Native
Bool Function IsEquipped(Form akItem) Native
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
