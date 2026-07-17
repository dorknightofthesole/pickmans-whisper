Scriptname PickmansWhisperPlayerAliasScript extends ReferenceAlias

; Optional backup: forward combat target into the main living-scan list.
; Primary kill detect is the main quest living→dead proximity poll (B14+).
; OnPlayerLoadGame here is the reliable FO4 load hook — forward into main so
; killscan/notice timers arm without opening MCM Debug.

Int FID_MAIN_QUEST = 0x00000800

Event OnAliasInit()
	EnsurePlayerFill()
	PickmansWhisperMainQuestScript main = GetMain()
	If main
		main.EnsurePlayerCombatQuest()
		main.ArmRuntimeLoops()
		main.ScheduleBootArm()
	Else
		Debug.Trace("PickmansWhisper: alias OnAliasInit — main quest script not found")
	EndIf
EndEvent

Event OnPlayerLoadGame()
	EnsurePlayerFill()
	PickmansWhisperMainQuestScript main = GetMain()
	If main
		main.HandlePlayerLoadFromAlias()
	Else
		Debug.Trace("PickmansWhisper: alias OnPlayerLoadGame — main quest script not found (timers not armed)")
	EndIf
EndEvent

Function EnsurePlayerFill()
	Actor p = Game.GetPlayer()
	If !p
		Return
	EndIf
	ObjectReference cur = GetReference()
	If cur != (p as ObjectReference)
		ForceRefTo(p)
	EndIf
EndFunction

PickmansWhisperMainQuestScript Function GetMain()
	Quest q = Game.GetFormFromFile(FID_MAIN_QUEST, "PickmansWhisper.esp") as Quest
	If !q
		Debug.Trace("PickmansWhisper: GetFormFromFile main quest 0x800 failed")
		Return None
	EndIf
	PickmansWhisperMainQuestScript main = q as PickmansWhisperMainQuestScript
	If !main
		Debug.Trace("PickmansWhisper: main quest cast to PickmansWhisperMainQuestScript failed")
	EndIf
	Return main
EndFunction

Event OnCombatStateChanged(Actor akTarget, Int aeCombatState)
	If aeCombatState != 1 || !akTarget
		Return
	EndIf
	PickmansWhisperMainQuestScript main = GetMain()
	If main
		main.ArmCombatTarget(akTarget)
	EndIf
EndEvent
