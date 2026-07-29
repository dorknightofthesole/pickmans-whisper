Scriptname PickmansWhisperProximityEffect extends ActiveMagicEffect
{Glowing One cloak clone — hit MGEF script. Attached (via VMAD) to
PickmansWhisperProximityHitEffect, the Script MGEF applied by the Assoc SPEL when an actor
enters the player's aura (Ability SPEL → Cloak MGEF Archetype=35, no script → Hit SPEL →
this MGEF). Forwards enter to Main.RegisterTarget (TrackedNPCs + OnDeath).
Main is Auto Const — filled once from hit MGEF VMAD.}

PickmansWhisperMainQuestScript Property Main Auto Const

Event OnEffectStart(Actor akTarget, Actor akCaster)
	If !akTarget || akTarget == akCaster
		Return
	EndIf

	If !Main
		Debug.Trace("PickmansWhisper: ProximityEffect OnEffectStart — Main property None")
		Debug.Notification("PW: ProximityEffect Main unbound")
		Return
	EndIf

	Debug.Notification("PickmansWhisper: ProximityEffect OnEffectStart target=" + akTarget.GetDisplayName())
	Debug.Trace("PickmansWhisper: ProximityEffect OnEffectStart target=" + akTarget.GetDisplayName())
	Main.RegisterTarget(akTarget, akCaster)
EndEvent

Event OnEffectFinish(Actor akTarget, Actor akCaster)
	Debug.Notification("PickmansWhisper: ProximityEffect OnEffectFinish target=" + akTarget.GetDisplayName())
	; The function below should only deregister is the NPC is out of range
	; Main.UnRegisterTarget(akTarget, akCaster)
EndEvent
