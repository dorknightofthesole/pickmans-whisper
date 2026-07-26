Scriptname PickmansWhisperVictimsScript extends Quest
{C5 Victims MCM + aim cache. Own script lock so CallFunction is not starved by Main killscan.}

; MCM buttons CallFunction this script (not MainQuestScript).
; Aim cache filled from KillerScan / knife / Tick via Main façades → NoteVictimsAimActor.
; Naming table + decay clocks stay on Main; this script owns aim + MCM push.
; Decay advance timer still cancelled (no StartTimer here). H P2: Set/Reset only
; move the kill clock; KillerScan → CorpseDecay SyncOverlays owns LooksMenu apply.

String MOD_NAME = "PickmansWhisper"
Int TIMER_DECAY_ADVANCE = 17 ; CancelTimer only (stale saves)

Actor LastVictimsAimActor = None
Int Property LastVictimsAimId = 0 Auto
String Property LastVictimsAimLine = "" Auto

Actor PendingDecayAdvanceActor = None
Int PendingDecayAdvanceStage = -1
Int PendingDecayAdvanceFormId = 0
Bool McmEventsRegistered = False

PickmansWhisperMainQuestScript Function Main()
	Return (Self as Quest) as PickmansWhisperMainQuestScript
EndFunction

; Former Debug.MessageBox — no pause; full text in Papyrus.0.log (filter PickmansWhisper).
Function DiagNotify(String msg)
	If msg == ""
		Return
	EndIf
	Debug.Trace("PickmansWhisper: DIAG " + msg)
	Debug.Notification(msg)
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
	; Always re-register — one-shot flag can leave open/close dead for the session.
	RegisterForExternalEvent("OnMCMMenuOpen|PickmansWhisper", "OnMCMMenuOpen")
	RegisterForExternalEvent("OnMCMMenuClose|PickmansWhisper", "OnMCMMenuClose")
	If !McmEventsRegistered
		McmEventsRegistered = True
		Debug.Trace("PickmansWhisper: Victims MCM open/close events registered")
	EndIf
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
	ClearPendingDecayAdvance()
	; Set/Reset queued PendingAimedDecayActor while MCM was open — paint now (NoWait).
	PickmansWhisperCorpseDecayScript decay = CorpseDecay()
	If decay
		decay.CallFunctionNoWait("RunPendingAimedDecayApply", None)
	EndIf
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

; Prefer player override when SetDisplayName failed: "Jenny (Resident) id=0x…"
String Function FormatVictimsAimLine(Actor aimed)
	If !aimed
		Return "(face her in-world ~2s, then open MCM — no scan while menu open)"
	EndIf
	String baseLabel = LocalActorLabel(aimed)
	String personal = ""
	PickmansWhisperMainQuestScript m = Main()
	If m
		personal = m.GetVictimOverrideName(aimed)
	EndIf
	String label = baseLabel
	If personal
		If personal != baseLabel
			label = personal + " (" + baseLabel + ")"
		Else
			label = personal
		EndIf
	EndIf
	Return label + " id=0x" + GardenOfEden.GetHexFormID(aimed)
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

; Aimed row only — never waits on Main for the push itself (Refresh was hanging).
Function PushVictimsAimedOnly()
	Actor aimed = ResolveVictimsAimActor()
	LastVictimsAimLine = FormatVictimsAimLine(aimed)
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
	; RefreshMenu reloads settings.ini and wipes live sDecayStage / Pick stage.
	; Write aux SYNC (not CallFunctionNoWait) so Decay row + dialog match now.
	Actor aimed = ResolveVictimsAimActor()
	PushVictimsAimedOnly()
	If MCM.IsInstalled()
		MCM.RefreshMenu()
		PushVictimsAimedOnly()
		aimed = ResolveVictimsAimActor()
	EndIf
	PickmansWhisperMainQuestScript m = Main()
	String decayLine = "(Main missing)"
	If m
		m.WriteVictimsMcmAuxRows()
		decayLine = m.FormatDecayStageStatusForActor(aimed)
		If MCM.IsInstalled() && decayLine
			MCM.SetModSettingString(MOD_NAME, "sDecayStage:Victims", decayLine)
		EndIf
	EndIf
	If !decayLine
		decayLine = "(empty decay status)"
	EndIf
	Debug.Trace("PickmansWhisper: MCMRefreshVictimsPanel decayUI=" + decayLine)
	Debug.Notification("PW Victims — " + LastVictimsAimLine)
	DiagNotify("Pickman's Whisper — Victims\n\nAimed:\n" + LastVictimsAimLine + "\n\nDecay:\n" + decayLine + "\n\ncacheId=" + LastVictimsAimId)
EndFunction

Function MCMNameAimedVictim()
	PickmansWhisperMainQuestScript m = Main()
	If !m
		DiagNotify("Pickman's Whisper — Apply name\n\nMain script missing.")
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
		DiagNotify("Pickman's Whisper — Apply name\n\nNo aim cache.\nFace her in-world for ~2s (killscan), then open MCM and try again.")
		Return
	EndIf
	String name = ""
	If MCM.IsInstalled()
		name = MCM.GetModSettingString(MOD_NAME, "sVictimName:Victims")
	EndIf
	If m.ApplyVictimName(aimed, name)
		String shown = m.TrimString(name)
		DiagNotify("Pickman's Whisper — Apply name\n\nShe is " + shown + " now.")
	Else
		DiagNotify("Pickman's Whisper — Apply name\n\nFailed:\n" + m.LastVictimStatus)
	EndIf
	RefreshVictimsPanel(True)
EndFunction

; Shared aim+validity gate for the two decay clock mutators below (Reset kill clock /
; Set decay stage) — same requirements either way: a live aim cache pointing at a dead,
; gameplay-eligible corpse with a usable FormID. Sets m.LastVictimStatus and traces a
; reason on failure so both callers report through the same DiagNotify path; returns
; None on any failure.
Actor Function ResolveValidDecayTarget(PickmansWhisperMainQuestScript m, String asStatusLabel, String asFnName)
	Actor player = Game.GetPlayer()
	Actor aimed = ResolveVictimsAimActor()
	If !aimed || aimed == player
		m.LastVictimStatus = asStatusLabel + ": no aim — face a corpse in-world ~2s, then retry"
		Debug.Trace("PickmansWhisper: ERROR " + asFnName + " — no aim cache")
		Return None
	EndIf
	If !aimed.IsDead()
		m.LastVictimStatus = asStatusLabel + ": " + m.GetActorDisplayName(aimed) + " is alive"
		Debug.Trace("PickmansWhisper: " + asFnName + " skip — target alive")
		Return None
	EndIf
	If m.IsNonGameplayCorpse(aimed)
		m.LastVictimStatus = asStatusLabel + ": skip non-gameplay corpse"
		Debug.Trace("PickmansWhisper: " + asFnName + " skip — non-gameplay")
		Return None
	EndIf
	If aimed.GetFormID() == 0
		m.LastVictimStatus = asStatusLabel + ": bad FormID"
		Return None
	EndIf
	Return aimed
EndFunction

; Murder time = now; LastStage = -1; MCM stage selector → 0. No overlays here.
Bool Function ResetAimedDecayKillClock()
	PickmansWhisperMainQuestScript m = Main()
	If !m
		Debug.Trace("PickmansWhisper: ERROR ResetAimedDecayKillClock — Main missing")
		Return False
	EndIf
	Actor aimed = ResolveValidDecayTarget(m, "reset kill clock", "ResetAimedDecayKillClock")
	If !aimed
		Return False
	EndIf
	Int formId = aimed.GetFormID()
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
	m.LastVictimStatus = "kill clock reset to now (stage 0 Freshly Deceased) — overlays on next KillerScan sync"
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
	Actor aimed = ResolveValidDecayTarget(m, "set decay", "PrepAimedDecayStage")
	If !aimed
		Return False
	EndIf
	Int formId = aimed.GetFormID()
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
	m.LastVictimStatus = "kill clock → stage " + targetStage + " " + m.GetDecayStageName(targetStage) + " — overlays on next KillerScan sync"
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
	m.LastVictimStatus = "kill clock → stage " + targetStage + " " + m.GetDecayStageName(targetStage) + " — overlays on next KillerScan sync"
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

; Shared tail for the Set/Reset decay-stage MCM buttons below — both prep the kill
; clock differently, then report identically: push status, latch the stepper, queue
; the paint, DiagNotify the result. RefreshMenu wipes live MCM rows, so status must
; be pushed AFTER it, not before (same order as OnMCMMenuOpen).
Function FinishMcmDecayStageAction(String asFnName, String asTitle, String asSuccessDetail, Bool abOk, Int aiStepperValue)
	PickmansWhisperMainQuestScript m = Main()
	Actor aimed = ResolveVictimsAimActor()
	If MCM.IsInstalled() && m
		MCM.RefreshMenu()
		PushVictimsAimedOnly()
		m.WriteVictimsStatusToMcm()
		m.WriteDecayStageStatusToMcmForActor(aimed, False)
		MCM.SetModSettingInt(MOD_NAME, "iVictimDecayStage:Victims", aiStepperValue)
	Else
		PushVictimsAimedOnly()
	EndIf
	If abOk && aimed
		PickmansWhisperCorpseDecayScript decay = CorpseDecay()
		If decay
			decay.QueueAimedDecayApply(aimed)
		Else
			Debug.Trace("PickmansWhisper: ERROR " + asFnName + " — CorpseDecay missing")
			Debug.Notification("Pickman's Whisper: CorpseDecay missing — rebuild ESP")
		EndIf
	EndIf
	String status = "(Main missing)"
	If m
		status = m.LastVictimStatus
	EndIf
	If abOk
		DiagNotify("Pickman's Whisper — " + asTitle + "\n\n" + status + "\n\n" + asSuccessDetail)
	Else
		DiagNotify("Pickman's Whisper — " + asTitle + "\n\nFailed / skipped:\n" + status)
	EndIf
EndFunction

; MCM test harness — murder time = now; stage selector → 0; KillerScan sync applies.
; Idempotent — no busy flag (swallowing clicks hid real apply failures).
Function MCMResetAimedDecayKillClock()
	Debug.Notification("PW Victims — Reset decay stage CallFunction hit")
	Debug.Trace("PickmansWhisper: MCMResetAimedDecayKillClock OK")
	ClearPendingDecayAdvance()
	Bool ok = ResetAimedDecayKillClock()
	FinishMcmDecayStageAction("MCMResetAimedDecayKillClock", "Reset decay stage", "Close MCM — overlays apply to the aimed corpse within ~1s (stage 0 = no body skins).", ok, 0)
EndFunction

; MCM test harness — set kill age only; core KillerScan sync applies the stage.
; Idempotent — double-click re-Preps the same stage; never swallow the click.
Function MCMApplyAimedDecayStage()
	Debug.Notification("PW Victims — Set decay stage CallFunction hit")
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
	FinishMcmDecayStageAction("MCMApplyAimedDecayStage", "Set decay stage", "Close MCM — overlays apply to the aimed corpse within ~1s (not via KillerScan wait).", ok, stage)
EndFunction

; Legacy +1 MCM — clock +1; KillerScan sync applies overlays.
Function MCMAdvanceAimedDecayStage()
	Debug.Notification("PW Victims — Advance decay clock CallFunction hit")
	Debug.Trace("PickmansWhisper: MCMAdvanceAimedDecayStage OK")
	PickmansWhisperMainQuestScript m = Main()
	ClearPendingDecayAdvance()
	Bool ok = QueueAimedDecayAdvance()
	Actor aimed = ResolveVictimsAimActor()
	If MCM.IsInstalled() && m
		MCM.RefreshMenu()
		PushVictimsAimedOnly()
		m.WriteVictimsStatusToMcm()
		m.WriteDecayStageStatusToMcmForActor(aimed)
	Else
		PushVictimsAimedOnly()
	EndIf
	String status = "(Main missing)"
	If m
		status = m.LastVictimStatus
	EndIf
	If ok
		DiagNotify("Pickman's Whisper — Advance decay clock\n\n" + status + "\n\nClose MCM — KillerScan applies overlays on the next sync.")
	Else
		DiagNotify("Pickman's Whisper — Advance decay clock\n\nFailed / skipped:\n" + status)

	EndIf
EndFunction
