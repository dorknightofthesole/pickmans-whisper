Scriptname PickmansWhisperVictimTradePerkScript extends Perk
{PERK PW_VictimTradeActivate — Activate/Add Activate Choice "Trade".
Forwards to Main façade; keep this fragment path thin (FO4 perk events can re-fire).}

PickmansWhisperMainQuestScript Property MainQuest Auto Const

Event OnEntryRun(Int auiEntryID, ObjectReference akTarget, Actor akOwner)
	If !MainQuest
		Debug.Trace("PickmansWhisper: ERROR trade perk OnEntryRun — MainQuest unbound")
		Debug.Notification("PickmansWhisper: Trade perk misconfigured (Main unbound)")
		Return
	EndIf
	MainQuest.TryForceVictimTradeFromActivate(akTarget as Actor)
EndEvent
