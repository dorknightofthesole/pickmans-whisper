Scriptname PickmansWhisperVictimsScript extends Quest
{C5 Victims MCM + aim cache. Own script lock so CallFunction is not starved by Main killscan.}

; MCM buttons CallFunction this script (not MainQuestScript).
; Aim cache filled from KillerScan / knife / Tick via Main façades → NoteVictimsAimActor.
; Naming table + decay clocks stay on Main; this script owns aim + MCM push.
; Decay MCM nudge timer PARKED (Killer Orchestrator 1.3.0) — KillerScan owns overlay sync.

String MOD_NAME = "PickmansWhisper"
Int TIMER_DECAY_ADVANCE = 17 ; CancelTimer only (stale saves)

Actor LastVictimsAimActor = None
Int Property LastVictimsAimId = 0 Auto
String Property LastVictimsAimLine = "" Auto

Actor PendingDecayAdvanceActor = None
Int PendingDecayAdvanceStage = -1
Int PendingDecayAdvanceFormId = 0
Bool McmEventsRegistered = False
; MCM can fire CallFunction dozens of times per click; ignore re-entry until MessageBox returns.
Bool McmDecayButtonBusy = False

PickmansWhisperMainQuestScript Function Main()
	Return (Self as Quest) as PickmansWhisperMainQuestScript
EndFunction

PickmansWhisperCorpseDecayScript Function CorpseDecay()
	Return (Self as Quest) as PickmansWhisperCorpseDecayScript
EndFunction

Event OnInit()
	EnsureMcmEventsRegistered()
EndEvent

Event OnTimer(Int aiTimerID)
	; Stale decay-advance timers from older builds — cancel only (nudge parked).
	CancelTimer(aiTimerID)
	Debug.Trace("PickmansWhisper: Victims OnTimer id=" + aiTimerID + " cancelled (decay nudge parked)")
EndEvent

Function EnsureMcmEventsRegistered()
	If McmEventsRegistered
		Return
	EndIf
	RegisterForExternalEvent("OnMCMMenuOpen|PickmansWhisper", "OnMCMMenuOpen")
	RegisterForExternalEvent("OnMCMMenuClose|PickmansWhisper", "OnMCMMenuClose")
	McmEventsRegistered = True
EndFunction

; Compat name — older callers / saves.
Function EnsureMcmOpenRegistered()
	EnsureMcmEventsRegistered()
EndFunction

; Light push only — Main OnMCMMenuOpen may still be locked; this path must stay free.
Function OnMCMMenuOpen(String modName)
	If modName != MOD_NAME
		Return
	EndIf
	EnsureMcmEventsRegistered()
	Debug.Trace("PickmansWhisper: Victims OnMCMMenuOpen")
	RefreshVictimsPanel(False)
EndFunction

Function OnMCMMenuClose(String modName)
	If modName != MOD_NAME
		Return
	EndIf
	; Decay MCM nudge parked — KillerScan SyncOverlays applies after menu close.
	ClearPendingDecayAdvance()
	Debug.Trace("PickmansWhisper: Victims OnMCMMenuClose — decay nudge parked (Killer Orchestrator)")
EndFunction

; Remember world aim — GetCameraTargetReference is usually None while Pause/MCM is open.
Function NoteVictimsAimActor(Actor ak)
	EnsureMcmOpenRegistered()
	Actor player = Game.GetPlayer()
	If !ak || ak == player
		Return
	EndIf
	If ak.IsDisabled()
		Return
	EndIf
	LastVictimsAimActor = ak
	LastVictimsAimId = ak.GetFormID()
EndFunction

; Live GoE aim without calling Main (Main lock was wedging MCM Refresh).
Actor Function GetLiveAimActor()
	Actor player = Game.GetPlayer()
	ObjectReference cam = GardenOfEden3.GetCameraTargetReference()
	Actor ak = cam as Actor
	If ak && ak != player && !ak.IsDisabled()
		Return ak
	EndIf
	ObjectReference pick = GardenOfEden2.GetLastActivateTargetRef()
	ak = pick as Actor
	If ak && ak != player && !ak.IsDisabled()
		Return ak
	EndIf
	Return None
EndFunction

; Cheap resolve — live GoE aim when available, else cache. No FindActors / no Main.
Actor Function ResolveVictimsAimActor()
	Actor player = Game.GetPlayer()
	Actor live = GetLiveAimActor()
	If live && live != player && !live.IsDisabled()
		NoteVictimsAimActor(live)
		Return live
	EndIf
	If LastVictimsAimActor && LastVictimsAimId != 0
		If LastVictimsAimActor.GetFormID() == LastVictimsAimId && !LastVictimsAimActor.IsDisabled()
			Return LastVictimsAimActor
		EndIf
	EndIf
	Return None
EndFunction

; KillerScan CallFunctionNoWait — fills aim cache without waiting on Main.
Function NoteFromKillerScanSnapshot()
	PickmansWhisperKillerScanScript scan = (Self as Quest) as PickmansWhisperKillerScanScript
	If !scan
		Debug.Trace("PickmansWhisper: ERROR Victims NoteFromKillerScanSnapshot — KillerScan missing")
		Return
	EndIf
	Actor cam = scan.CameraActor
	Actor facedDead = scan.FacedDead
	If cam
		NoteVictimsAimActor(cam)
	EndIf
	If facedDead
		NoteVictimsAimActor(facedDead)
	EndIf
EndFunction

String Function LocalActorLabel(Actor ak)
	If !ak
		Return "unnamed"
	EndIf
	String nm = ak.GetDisplayName()
	If nm
		Return nm
	EndIf
	ActorBase base = ak.GetLeveledActorBase()
	If base
		nm = base.GetName()
		If nm
			Return nm
		EndIf
	EndIf
	Return "unnamed"
EndFunction

Function WriteVictimsAimedToMcm()
	If !MCM.IsInstalled()
		Return
	EndIf
	If !LastVictimsAimLine
		MCM.SetModSettingString(MOD_NAME, "sVictimAimed:Victims", "(look at an adult woman, then open MCM)")
	Else
		MCM.SetModSettingString(MOD_NAME, "sVictimAimed:Victims", LastVictimsAimLine)
	EndIf
EndFunction

; Aimed row only — never waits on Main (Refresh was hanging in Push → Main).
Function PushVictimsAimedOnly()
	Actor aimed = ResolveVictimsAimActor()
	LastVictimsAimLine = "(face her in-world ~2s, then open MCM — no scan while menu open)"
	If aimed
		String src = "cache"
		Actor live = GetLiveAimActor()
		If live && live == aimed
			src = "aim"
		EndIf
		LastVictimsAimLine = LocalActorLabel(aimed) + "  id=0x" + GardenOfEden.GetHexFormID(aimed) + " (" + src + ")"
	EndIf
	WriteVictimsAimedToMcm()
	Debug.Trace("PickmansWhisper: Victims aimed | " + LastVictimsAimLine + " cacheId=" + LastVictimsAimId)
EndFunction

Function PushVictimsPanelStrings()
	PushVictimsAimedOnly()
	; Best-effort Main rows — CallFunctionNoWait so a wedged Main cannot stall Refresh.
	PickmansWhisperMainQuestScript m = Main()
	If m
		m.CallFunctionNoWait("WriteVictimsMcmAuxRows", None)
	EndIf
EndFunction

Function RefreshVictimsPanel(Bool refreshMenu = True)
	PushVictimsAimedOnly()
	If refreshMenu && MCM.IsInstalled()
		MCM.RefreshMenu()
		PushVictimsAimedOnly()
	EndIf
	PickmansWhisperMainQuestScript m = Main()
	If m
		m.CallFunctionNoWait("WriteVictimsMcmAuxRows", None)
	EndIf
EndFunction

Function TickVictimsAimCache()
	Actor ak = GetLiveAimActor()
	If ak
		NoteVictimsAimActor(ak)
	EndIf
EndFunction

; MCM CallFunction — "Load targeted corpse" (own lock; must not wait on Main killscan).
Function MCMRefreshVictimsPanel()
	Debug.Notification("PW Victims Refresh — CallFunction hit")
	Debug.Trace("PickmansWhisper: MCMRefreshVictimsPanel OK")
	; Aimed push + MessageBox first — never block on Main for the proof dialog.
	PushVictimsAimedOnly()
	If MCM.IsInstalled()
		MCM.RefreshMenu()
		PushVictimsAimedOnly()
	EndIf
	String decayLine = "(pending Main)"
	If MCM.IsInstalled()
		decayLine = MCM.GetModSettingString(MOD_NAME, "sDecayStage:Victims")
		If !decayLine
			decayLine = "(empty — Main aux pending)"
		EndIf
	EndIf
	Debug.MessageBox("Pickman's Whisper — Victims\n\nAimed:\n" + LastVictimsAimLine + "\n\nDecay:\n" + decayLine + "\n\ncacheId=" + LastVictimsAimId)
	PickmansWhisperMainQuestScript m = Main()
	If m
		m.CallFunctionNoWait("WriteVictimsMcmAuxRows", None)
	EndIf
EndFunction

Function MCMNameAimedVictim()
	PickmansWhisperMainQuestScript m = Main()
	If !m
		Debug.MessageBox("Pickman's Whisper — Apply name\n\nMain script missing.")
		Return
	EndIf
	Actor player = Game.GetPlayer()
	Actor aimed = ResolveVictimsAimActor()
	If !aimed || aimed == player
		m.LastVictimStatus = "no aim cache — face her in-world ~2s, then Apply name"
		PushVictimsPanelStrings()
		If MCM.IsInstalled()
			MCM.RefreshMenu()
			WriteVictimsAimedToMcm()
			m.WriteVictimsStatusToMcm()
		EndIf
		Debug.MessageBox("Pickman's Whisper — Apply name\n\nNo aim cache.\nFace her in-world for ~2s (killscan), then open MCM and try again.")
		Return
	EndIf
	String name = ""
	If MCM.IsInstalled()
		name = MCM.GetModSettingString(MOD_NAME, "sVictimName:Victims")
	EndIf
	If m.ApplyVictimName(aimed, name)
		String shown = m.TrimString(name)
		Debug.MessageBox("Pickman's Whisper — Apply name\n\nShe is " + shown + " now.")
	Else
		Debug.MessageBox("Pickman's Whisper — Apply name\n\nFailed:\n" + m.LastVictimStatus)
	EndIf
	RefreshVictimsPanel(True)
EndFunction

; Murder time = now; LastStage = -1; MCM stage selector → 0. No overlays here.
Bool Function ResetAimedDecayKillClock()
	PickmansWhisperMainQuestScript m = Main()
	If !m
		Debug.Trace("PickmansWhisper: ERROR ResetAimedDecayKillClock — Main missing")
		Return False
	EndIf
	Actor player = Game.GetPlayer()
	Actor aimed = ResolveVictimsAimActor()
	If !aimed || aimed == player
		m.LastVictimStatus = "reset kill clock: no aim — face a corpse in-world ~2s, then retry"
		Debug.Trace("PickmansWhisper: ERROR ResetAimedDecayKillClock — no aim cache")
		Return False
	EndIf
	If !aimed.IsDead()
		m.LastVictimStatus = "reset kill clock: " + m.GetActorDisplayName(aimed) + " is alive"
		Debug.Trace("PickmansWhisper: ResetAimedDecayKillClock skip — target alive")
		Return False
	EndIf
	If m.IsNonGameplayCorpse(aimed)
		m.LastVictimStatus = "reset kill clock: skip non-gameplay corpse"
		Debug.Trace("PickmansWhisper: ResetAimedDecayKillClock skip — non-gameplay")
		Return False
	EndIf
	Int formId = aimed.GetFormID()
	If formId == 0
		m.LastVictimStatus = "reset kill clock: bad FormID"
		Return False
	EndIf
	; StampDecayKill upserts kill time to now and LastStage = -1.
	m.StampDecayKill(aimed)
	If m.FindDecayKillSlot(formId) < 0
		m.LastVictimStatus = "reset kill clock: failed to stamp"
		Debug.Notification("Pickman's Whisper: could not reset decay clock")
		Debug.Trace("PickmansWhisper: ERROR ResetAimedDecayKillClock — stamp failed id=0x" + GardenOfEden.GetHexFormID(aimed))
		Return False
	EndIf
	If MCM.IsInstalled()
		MCM.SetModSettingInt(MOD_NAME, "iVictimDecayStage:Victims", 0)
	EndIf
	PickmansWhisperCorpseDecayScript decay = CorpseDecay()
	If decay
		decay.NoteForcedDecayClockForTest()
	EndIf
	m.LastVictimStatus = "kill clock reset to now (stage 0 Freshly Deceased) — KillerScan will apply"
	Debug.Trace("PickmansWhisper: ResetAimedDecayKillClock ok id=0x" + GardenOfEden.GetHexFormID(aimed))
	Return True
EndFunction

; Stamp + backdate kill clock for target stage (now - startHours). No overlays here.
Bool Function PrepAimedDecayStage(Int targetStage)
	PickmansWhisperMainQuestScript m = Main()
	If !m
		Debug.Trace("PickmansWhisper: ERROR PrepAimedDecayStage — Main missing")
		Return False
	EndIf
	If targetStage < 0 || targetStage > 4
		m.LastVictimStatus = "set decay: stage must be 0..4 (got " + targetStage + ")"
		Debug.Trace("PickmansWhisper: ERROR PrepAimedDecayStage — bad stage " + targetStage)
		Return False
	EndIf
	Actor player = Game.GetPlayer()
	Actor aimed = ResolveVictimsAimActor()
	If !aimed || aimed == player
		m.LastVictimStatus = "set decay: no aim — face a corpse in-world ~2s, then retry"
		Debug.Trace("PickmansWhisper: ERROR PrepAimedDecayStage — no aim cache")
		Return False
	EndIf
	If !aimed.IsDead()
		m.LastVictimStatus = "set decay: " + m.GetActorDisplayName(aimed) + " is alive"
		Debug.Trace("PickmansWhisper: PrepAimedDecayStage skip — target alive")
		Return False
	EndIf
	If m.IsNonGameplayCorpse(aimed)
		m.LastVictimStatus = "set decay: skip non-gameplay corpse"
		Debug.Trace("PickmansWhisper: PrepAimedDecayStage skip — non-gameplay")
		Return False
	EndIf
	Int formId = aimed.GetFormID()
	If formId == 0
		m.LastVictimStatus = "set decay: bad FormID"
		Return False
	EndIf
	If !m.DecayStagesReady()
		m.LoadModConfig()
	EndIf
	If !m.DecayStagesReady()
		m.LastVictimStatus = "set decay: ModConfig decayStage0..4 — " + m.ModConfigLoadStatus
		Debug.Notification("Pickman's Whisper: decay stages not loaded — check ModConfig.txt")
		Debug.Trace("PickmansWhisper: ERROR PrepAimedDecayStage — " + m.LastVictimStatus)
		Return False
	EndIf
	If m.FindDecayKillSlot(formId) < 0
		m.StampDecayKill(aimed)
	EndIf
	If m.FindDecayKillSlot(formId) < 0
		m.LastVictimStatus = "set decay: failed to stamp decay clock"
		Debug.Notification("Pickman's Whisper: could not stamp decay clock")
		Debug.Trace("PickmansWhisper: ERROR PrepAimedDecayStage — stamp failed id=0x" + GardenOfEden.GetHexFormID(aimed))
		Return False
	EndIf
	If !m.ForceDecayKillClockToStage(formId, targetStage)
		m.LastVictimStatus = "set decay: failed to set clock for stage " + targetStage
		Debug.Notification("Pickman's Whisper: failed to set decay clock for stage " + targetStage)
		Debug.Trace("PickmansWhisper: ERROR PrepAimedDecayStage — ForceDecayKillClockToStage failed")
		Return False
	EndIf
	; Leave LastStage one below target so KillerScan SyncDecayForKnifeCorpse applies overlays.
	If targetStage <= 0
		m.SetDecayKillLastStage(formId, -1)
	Else
		m.SetDecayKillLastStage(formId, targetStage - 1)
	EndIf
	PickmansWhisperCorpseDecayScript decay = CorpseDecay()
	If decay
		decay.NoteForcedDecayClockForTest()
	EndIf
	m.LastVictimStatus = "kill clock → stage " + targetStage + " " + m.GetDecayStageName(targetStage) + " — KillerScan will apply"
	Debug.Trace("PickmansWhisper: PrepAimedDecayStage ok stage=" + targetStage + " id=0x" + GardenOfEden.GetHexFormID(aimed))
	Return True
EndFunction

Function ClearPendingDecayAdvance()
	CancelTimer(TIMER_DECAY_ADVANCE)
	PendingDecayAdvanceActor = None
	PendingDecayAdvanceStage = -1
	PendingDecayAdvanceFormId = 0
EndFunction

; Legacy deferred queue — prep clock + pending for TIMER_DECAY_ADVANCE / AdvanceAimedDecayStage.
Bool Function QueueAimedDecayStage(Int targetStage)
	PickmansWhisperMainQuestScript m = Main()
	If !PrepAimedDecayStage(targetStage)
		Return False
	EndIf
	Actor aimed = ResolveVictimsAimActor()
	If !aimed || !m
		Return False
	EndIf
	Int formId = aimed.GetFormID()
	PendingDecayAdvanceActor = aimed
	PendingDecayAdvanceStage = targetStage
	PendingDecayAdvanceFormId = formId
	m.LastVictimStatus = "kill clock → stage " + targetStage + " " + m.GetDecayStageName(targetStage) + " — close MCM; KillerScan sync applies"
	Debug.Trace("PickmansWhisper: QueueAimedDecayStage ok stage=" + targetStage + " id=0x" + GardenOfEden.GetHexFormID(aimed))
	Return True
EndFunction

; Legacy +1 wrapper (tests / callers). Fails at stage 4.
Bool Function QueueAimedDecayAdvance()
	PickmansWhisperMainQuestScript m = Main()
	If !m
		Debug.Trace("PickmansWhisper: ERROR QueueAimedDecayAdvance — Main missing")
		Return False
	EndIf
	Actor aimed = ResolveVictimsAimActor()
	If !aimed
		m.LastVictimStatus = "advance decay: no aim — face a corpse in-world ~2s, then retry"
		Return False
	EndIf
	If !aimed.IsDead()
		m.LastVictimStatus = "advance decay: " + m.GetActorDisplayName(aimed) + " is alive"
		Return False
	EndIf
	Int formId = aimed.GetFormID()
	If formId == 0
		m.LastVictimStatus = "advance decay: bad FormID"
		Return False
	EndIf
	If m.FindDecayKillSlot(formId) < 0
		m.StampDecayKill(aimed)
	EndIf
	If m.FindDecayKillSlot(formId) < 0
		m.LastVictimStatus = "advance decay: failed to stamp decay clock"
		Return False
	EndIf
	Int applied = m.GetDecayKillLastStage(formId)
	Int resolved = m.ResolveDecayStageForKill(formId)
	Int visual = applied
	If visual < 0
		visual = resolved
	EndIf
	If visual < 0
		visual = 0
	EndIf
	If visual >= 4
		m.LastVictimStatus = "advance decay: already " + m.GetDecayStageName(4) + " (stage 4)"
		Debug.Trace("PickmansWhisper: QueueAimedDecayAdvance — already max stage")
		Return False
	EndIf
	Return QueueAimedDecayStage(visual + 1)
EndFunction

; Parked — kept for stale CallFunction / save stacks; does not StartTimer.
Function RunPendingDecayAdvance()
	ClearPendingDecayAdvance()
	Debug.Trace("PickmansWhisper: RunPendingDecayAdvance parked (Killer Orchestrator — use KillerScan sync)")
EndFunction

; Non-MCM: backdate clock; KillerScan SyncDecayForKnifeCorpse owns overlays.
Bool Function AdvanceAimedDecayStage()
	Return QueueAimedDecayAdvance()
EndFunction

; MCM test harness — murder time = now; stage selector → 0; KillerScan sync applies.
Function MCMResetAimedDecayKillClock()
	If McmDecayButtonBusy
		Debug.Trace("PickmansWhisper: MCMResetAimedDecayKillClock ignored (busy)")
		Return
	EndIf
	McmDecayButtonBusy = True
	Debug.Notification("PW Victims — Reset decay stage CallFunction hit")
	Debug.Trace("PickmansWhisper: MCMResetAimedDecayKillClock OK")
	PickmansWhisperMainQuestScript m = Main()
	ClearPendingDecayAdvance()
	Bool ok = ResetAimedDecayKillClock()
	Actor aimed = ResolveVictimsAimActor()
	PickmansWhisperCorpseDecayScript decay = CorpseDecay()
	If ok && decay
		decay.NoteForcedDecayClockForTest()
	EndIf
	PushVictimsPanelStrings()
	If MCM.IsInstalled() && m
		; Keep selector at 0; do not Resolve→sync stepper (can race with Set).
		MCM.SetModSettingInt(MOD_NAME, "iVictimDecayStage:Victims", 0)
		m.WriteVictimsStatusToMcm()
		m.WriteDecayStageStatusToMcmForActor(aimed, False)
		MCM.SetModSettingInt(MOD_NAME, "iVictimDecayStage:Victims", 0)
	EndIf
	String status = "(Main missing)"
	If m
		status = m.LastVictimStatus
	EndIf
	If ok
		Debug.MessageBox("Pickman's Whisper — Reset decay stage\n\n" + status + "\n\nKill clock set. MCM overlay nudge PARKED (v1.3.0 Killer Orchestrator). Close MCM — KillerScan applies overlays.")
	Else
		Debug.MessageBox("Pickman's Whisper — Reset decay stage\n\nFailed / skipped:\n" + status)
	EndIf
	McmDecayButtonBusy = False
EndFunction

; MCM test harness — set kill age only; core KillerScan sync applies the stage.
Function MCMApplyAimedDecayStage()
	If McmDecayButtonBusy
		Debug.Trace("PickmansWhisper: MCMApplyAimedDecayStage ignored (busy)")
		Return
	EndIf
	McmDecayButtonBusy = True
	Debug.Notification("PW Victims — Set decay stage CallFunction hit")
	PickmansWhisperMainQuestScript m = Main()
	Int stage = 0
	If MCM.IsInstalled()
		stage = MCM.GetModSettingInt(MOD_NAME, "iVictimDecayStage:Victims")
	EndIf
	If stage < 0
		stage = 0
	ElseIf stage > 4
		stage = 4
	EndIf
	; Latch chosen stage so MCM spam / status push cannot re-read a different value.
	If MCM.IsInstalled()
		MCM.SetModSettingInt(MOD_NAME, "iVictimDecayStage:Victims", stage)
	EndIf
	Debug.Trace("PickmansWhisper: MCMApplyAimedDecayStage OK read stage=" + stage)
	ClearPendingDecayAdvance()
	Bool ok = PrepAimedDecayStage(stage)
	Actor aimed = ResolveVictimsAimActor()
	PickmansWhisperCorpseDecayScript decay = CorpseDecay()
	If ok && decay
		decay.NoteForcedDecayClockForTest()
	EndIf
	PushVictimsPanelStrings()
	If MCM.IsInstalled() && m
		m.WriteVictimsStatusToMcm()
		m.WriteDecayStageStatusToMcmForActor(aimed, False)
		MCM.SetModSettingInt(MOD_NAME, "iVictimDecayStage:Victims", stage)
	EndIf
	String status = "(Main missing)"
	If m
		status = m.LastVictimStatus
	EndIf
	If ok
		Debug.MessageBox("Pickman's Whisper — Set decay stage\n\n" + status + "\n\nKill clock set. MCM overlay nudge PARKED (v1.3.0 Killer Orchestrator). Close MCM — KillerScan applies overlays.")
	Else
		Debug.MessageBox("Pickman's Whisper — Set decay stage\n\nFailed / skipped:\n" + status)
	EndIf
	McmDecayButtonBusy = False
EndFunction

; Legacy +1 MCM — clock only (+1), then KillerScan sync.
Function MCMAdvanceAimedDecayStage()
	Debug.Notification("PW Victims — Advance decay clock CallFunction hit")
	Debug.Trace("PickmansWhisper: MCMAdvanceAimedDecayStage OK")
	PickmansWhisperMainQuestScript m = Main()
	ClearPendingDecayAdvance()
	Bool ok = QueueAimedDecayAdvance()
	Actor aimed = ResolveVictimsAimActor()
	PickmansWhisperCorpseDecayScript decay = CorpseDecay()
	If ok && decay
		decay.NoteForcedDecayClockForTest()
	EndIf
	PushVictimsPanelStrings()
	If MCM.IsInstalled() && m
		m.WriteVictimsStatusToMcm()
		m.WriteDecayStageStatusToMcmForActor(aimed)
	EndIf
	String status = "(Main missing)"
	If m
		status = m.LastVictimStatus
	EndIf
	If ok
		Debug.MessageBox("Pickman's Whisper — Advance decay clock\n\n" + status + "\n\nMCM overlay nudge PARKED (v1.3.0). Close MCM — KillerScan applies overlays.")
	Else
		Debug.MessageBox("Pickman's Whisper — Advance decay clock\n\nFailed / skipped:\n" + status)
	EndIf
EndFunction
