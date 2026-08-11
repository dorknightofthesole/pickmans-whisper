Scriptname PickmansWhisperSlaveryPerkScript extends Perk
{PERK PW_SlaveryActivate — Activate choices Enslave (entry_id=0) / Take Her (entry_id=1).
auiEntryID now IS trusted: tools/build_hunger_spell_esp.py's _activate_choice_entry gives
each entry its own real EPFB (xEdit: "Perk Entry ID [unique]") — verified byte-for-byte in
the built ESP (Enslave EPFB=0000, Take Her EPFB=0100). The old "auiEntryID is unreliable"
claim described the symptom of both entries sharing EPFB=0000, not an engine limitation.
IsOurSlave-based routing is kept ONLY as a fallback for an unrecognized auiEntryID value.
Free is no longer reachable from this activate menu — see
PickmansWhisperVictimsScript.MCMFreeAimedSlave (Victims MCM page) for the direct one-click
free path; Force Trade + removing her slave-named item still auto-frees via
SyncSlaveryFromSlaveGear either way.}

PickmansWhisperMainQuestScript Property MainQuest Auto Const

Event OnEntryRun(Int auiEntryID, ObjectReference akTarget, Actor akOwner)
	If !MainQuest
		Debug.Trace("PickmansWhisper: ERROR slavery perk OnEntryRun — MainQuest unbound")
		Debug.Notification("PickmansWhisper: Slavery perk misconfigured (Main unbound)")
		Return
	EndIf
	Actor target = akTarget as Actor
	If !target
		Debug.Trace("PickmansWhisper: slavery perk skip | no actor target entry=" + auiEntryID)
		Debug.Notification("PickmansWhisper: Slavery — no target")
		Return
	EndIf
	If auiEntryID == 0
		Debug.Trace("PickmansWhisper: slavery perk OnEntryRun | Enslave (entry_id=0) id=" + target.GetFormID())
		MainQuest.TryEnslaveFromActivate(target)
	ElseIf auiEntryID == 1
		Debug.Trace("PickmansWhisper: slavery perk OnEntryRun | Take Her (entry_id=1) id=" + target.GetFormID())
		MainQuest.TryStartSlaveSceneFromActivate(target)
	Else
		; Should not happen now that entries have distinct EPFB — safety net only.
		Debug.Trace("PickmansWhisper: slavery perk OnEntryRun | unexpected entry=" + auiEntryID + ", falling back to IsOurSlave state")
		If MainQuest.IsOurSlave(target)
			MainQuest.TryStartSlaveSceneFromActivate(target)
		Else
			MainQuest.TryEnslaveFromActivate(target)
		EndIf
	EndIf
EndEvent
