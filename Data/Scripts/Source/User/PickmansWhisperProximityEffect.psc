Scriptname PickmansWhisperProximityEffect extends ActiveMagicEffect
{Glowing One cloak clone — hit MGEF script. Attached (via VMAD) to
PickmansWhisperProximityHitEffect, the Script MGEF applied by the Assoc SPEL when an actor
enters the player's aura (Ability SPEL → Cloak MGEF Archetype=35, no script → Hit SPEL →
this MGEF). OnEffectStart/OnEffectFinish fire natively per-actor as they enter/leave.
Phase 1 proves the aura fires; no gameplay logic lives here yet.}

Event OnEffectStart(Actor akTarget, Actor akCaster)
	Debug.Notification("PW Cloak: OnEffectStart")
	Debug.Trace("PickmansWhisper: ProximityCloak OnEffectStart raw | target=" + akTarget + " caster=" + akCaster)

	If !akTarget || akTarget == akCaster
		Return
	EndIf
	String nm = akTarget.GetDisplayName()
	If !nm || nm == ""
		nm = "(unnamed)"
	EndIf
	Debug.Notification("PW Cloak: " + nm + " entered radius")
	Debug.Trace("PickmansWhisper: ProximityCloak OnEffectStart | " + nm + " id=" + akTarget.GetFormID())
EndEvent

Event OnEffectFinish(Actor akTarget, Actor akCaster)
	If !akTarget || akTarget == akCaster
		Return
	EndIf
	String nm = akTarget.GetDisplayName()
	If !nm || nm == ""
		nm = "(unnamed)"
	EndIf
	Debug.Notification("PW Cloak: " + nm + " left radius")
	Debug.Trace("PickmansWhisper: ProximityCloak OnEffectFinish | " + nm + " id=" + akTarget.GetFormID())
EndEvent
