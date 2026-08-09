Scriptname PickmansWhisperSlaveryPerkScript extends Perk
{PERK PW_SlaveryActivate — Activate choices Enslave (entry 0) / Free (entry 1).
Forwards to Main façades; keep this fragment path thin.}

PickmansWhisperMainQuestScript Property MainQuest Auto Const

Event OnEntryRun(Int auiEntryID, ObjectReference akTarget, Actor akOwner)
	If !MainQuest
		Debug.Trace("PickmansWhisper: ERROR slavery perk OnEntryRun — MainQuest unbound")
		Debug.Notification("PickmansWhisper: Slavery perk misconfigured (Main unbound)")
		Return
	EndIf
	Actor target = akTarget as Actor
	If auiEntryID == 0
		MainQuest.TryEnslaveFromActivate(target)
	ElseIf auiEntryID == 1
		MainQuest.TryFreeSlaveFromActivate(target)
	Else
		Debug.Trace("PickmansWhisper: slavery perk unknown entry id=" + auiEntryID)
	EndIf
EndEvent
