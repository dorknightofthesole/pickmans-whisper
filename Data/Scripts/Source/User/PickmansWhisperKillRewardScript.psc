Scriptname PickmansWhisperKillRewardScript extends ReferenceAlias
{Missed-OnDeath settle timer on Main ALST KillRewardAlias (UniqueActor=Player).
Queue = PendingRewardTargets; due time stamped on each Actor via PW_KillRewardCheckTime.}

; Local to this alias script instance (not shared with Main/KillerScan ids).
; Repo convention: 22 is free of Main/BedGift/KillerScan/Victims timer constants.
Int TIMER_KILL_REWARD_CHECK = 22
Float KILL_REWARD_CHECK_SECONDS = 5.0

RefCollectionAlias Property PendingRewardTargets Auto Const
ActorValue Property PW_KillRewardCheckTime Auto Const

Bool IsCounterRunning = False

; CK/VMAD: bound to PickmansWhisperPlayerCombat ALST 0 (PickmansWhisperPlayerAliasScript).
PickmansWhisperPlayerAliasScript Property PlayerAlias Auto Const

Event OnAliasInit()
	PickmansWhisperMainQuestScript m = Main()
	If m
		m.ClearCollection(PendingRewardTargets)
	EndIf
	IsCounterRunning = False
EndEvent

PickmansWhisperMainQuestScript Function Main()
	Return GetOwningQuest() as PickmansWhisperMainQuestScript
EndFunction

Function RegisterKillRewardCheck(Actor akTarget, Int secondsTillCheck)
	If !akTarget || !PendingRewardTargets || !PW_KillRewardCheckTime
		Debug.Trace("PickmansWhisper: RegisterKillRewardCheck skip — unbound target/queue/AV")
		Return
	EndIf

	akTarget.SetValue(PW_KillRewardCheckTime, Utility.GetCurrentRealTime() + secondsTillCheck as Float)
	If PendingRewardTargets.Find(akTarget) < 0
		PendingRewardTargets.AddRef(akTarget)
	EndIf

	If !IsCounterRunning
		CancelTimer(TIMER_KILL_REWARD_CHECK)
		StartTimer(KILL_REWARD_CHECK_SECONDS, TIMER_KILL_REWARD_CHECK)
		IsCounterRunning = True
	EndIf
EndFunction

Event OnTimer(Int aiTimerID)
	If aiTimerID != TIMER_KILL_REWARD_CHECK
		Debug.Trace("PickmansWhisper Error: aiTimerID != TIMER_KILL_REWARD_CHECK")
		Return
	EndIf
    PickmansWhisperMainQuestScript main = Main()
    If !main
		Debug.Trace("PickmansWhisper Error: Main not initialized")
        Return
    EndIf

	If PendingRewardTargets
		Int i = PendingRewardTargets.GetCount()
		While i > 0
			i -= 1
			ObjectReference kRef = PendingRewardTargets.GetAt(i)
			Actor targetActor = kRef as Actor
			If !targetActor
				If kRef
					PendingRewardTargets.RemoveRef(kRef)
				EndIf
			ElseIf Utility.GetCurrentRealTime() >= targetActor.GetValue(PW_KillRewardCheckTime)
				Debug.Notification("Checking Kill Reward Eligibility for " + targetActor.GetDisplayName())
				main.RewardKill(targetActor)
                PendingRewardTargets.RemoveRef(kRef)
			EndIf
		EndWhile
	EndIf

	If PendingRewardTargets && PendingRewardTargets.GetCount() > 0
		StartTimer(KILL_REWARD_CHECK_SECONDS, TIMER_KILL_REWARD_CHECK)
		IsCounterRunning = True
	Else
		IsCounterRunning = False
	EndIf
EndEvent
