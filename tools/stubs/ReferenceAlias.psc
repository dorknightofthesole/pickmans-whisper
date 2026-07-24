Scriptname ReferenceAlias extends Alias Native

Event OnAliasInit()
EndEvent

Event OnPlayerLoadGame()
EndEvent

Event OnCombatStateChanged(Actor akTarget, Int aeCombatState)
EndEvent

Event OnDeath(Actor akKiller)
EndEvent

Event OnHit(ObjectReference akTarget, ObjectReference akAggressor, Form akSource, Projectile akProjectile, Bool abPowerAttack, Bool abSneakAttack, Bool abBashAttack, Bool abHitBlocked, String asMaterialName)
EndEvent

Function ForceRefTo(ObjectReference akNewRef) Native
ObjectReference Function GetReference() Native
; Real FO4 — non-native convenience wrapper (not a Native).
Actor Function GetActorReference()
	Return GetReference() as Actor
EndFunction
Function Clear() Native
