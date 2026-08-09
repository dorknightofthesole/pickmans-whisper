Scriptname PickmansWhisperSlaveryPerkScript extends Perk
{PERK PW_SlaveryActivate — Activate choices Enslave / Free (labels for menu).
Both choices toggle: Free if she is already our slave, else Enslave.
auiEntryID is not trusted (shared EPFB on both entries).}

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
	; Either menu label — Free when already ours (Trade pacify auto-enslaves).
	If MainQuest.IsOurSlave(target)
		MainQuest.TryFreeSlaveFromActivate(target)
	Else
		MainQuest.TryEnslaveFromActivate(target)
	EndIf
EndEvent
