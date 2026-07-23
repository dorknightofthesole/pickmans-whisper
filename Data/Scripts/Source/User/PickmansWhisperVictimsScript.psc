Scriptname PickmansWhisperVictimsScript extends Quest
{C5 Victims MCM + aim cache. Own script lock so CallFunction is not starved by Main killscan.}

; MCM buttons CallFunction this script (not MainQuestScript).
; Aim cache filled from WorldScan / knife / Tick via Main façades → NoteVictimsAimActor.
; Naming table + decay clocks stay on Main; this script owns aim + MCM push + advance timer.

String MOD_NAME = "PickmansWhisper"
Int TIMER_DECAY_ADVANCE = 17
Float DECAY_ADVANCE_DELAY = 0.35

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

PickmansWhisperCorpseDecayScript Function CorpseDecay()
	Return (Self as Quest) as PickmansWhisperCorpseDecayScript
EndFunction

Event OnInit()
	EnsureMcmEventsRegistered()
EndEvent

Event OnTimer(Int aiTimerID)
	If aiTimerID == TIMER_DECAY_ADVANCE
		RunPendingDecayAdvance()
	EndIf
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

; Flush queued Victims decay apply after MCM closes (timer alone used to drop pending in-menu).
Function OnMCMMenuClose(String modName)
	If modName != MOD_NAME
		Return
	EndIf
	If PendingDecayAdvanceStage < 0 || !PendingDecayAdvanceActor
		Return
	EndIf
	CancelTimer(TIMER_DECAY_ADVANCE)
	StartTimer(0.15, TIMER_DECAY_ADVANCE)
	Debug.Trace("PickmansWhisper: Victims OnMCMMenuClose — arm decay apply timer")
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

; WorldScan CallFunctionNoWait — fills aim cache without waiting on Main.
Function NoteFromWorldScanSnapshot()
	PickmansWhisperWorldScanScript scan = (Self as Quest) as PickmansWhisperWorldScanScript
	If !scan
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

; MCM CallFunction — Refresh aimed / list (own lock; must not wait on Main killscan).
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
		Debug.MessageBox("Pickman's Whisper — Name aimed\n\nMain script missing.")
		Return
	EndIf
	Actor player = Game.GetPlayer()
	Actor aimed = ResolveVictimsAimActor()
	If !aimed || aimed == player
		m.LastVictimStatus = "no aim cache — face her in-world ~2s, then Name aimed"
		PushVictimsPanelStrings()
		If MCM.IsInstalled()
			MCM.RefreshMenu()
			WriteVictimsAimedToMcm()
			m.WriteVictimsStatusToMcm()
		EndIf
		Debug.MessageBox("Pickman's Whisper — Name aimed\n\nNo aim cache.\nFace her in-world for ~2s (killscan), then open MCM and try again.")
		Return
	EndIf
	String name = ""
	If MCM.IsInstalled()
		name = MCM.GetModSettingString(MOD_NAME, "sVictimName:Victims")
	EndIf
	If m.ApplyVictimName(aimed, name)
		String shown = m.TrimString(name)
		Debug.MessageBox("Pickman's Whisper — Name aimed\n\nShe is " + shown + " now.")
	Else
		Debug.MessageBox("Pickman's Whisper — Name aimed\n\nFailed:\n" + m.LastVictimStatus)
	EndIf
	RefreshVictimsPanel(True)
EndFunction

; Stamp + backdate kill clock for target stage. No overlays / no pending timer.
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
	; Leave LastStage one below target so WorldScan SyncDecayForKnifeCorpse applies overlays.
	If targetStage <= 0
		m.SetDecayKillLastStage(formId, -1)
	Else
		m.SetDecayKillLastStage(formId, targetStage - 1)
	EndIf
	PickmansWhisperCorpseDecayScript decay = CorpseDecay()
	If decay
		decay.NoteForcedDecayClockForTest()
	EndIf
	m.LastVictimStatus = "kill clock → stage " + targetStage + " " + m.GetDecayStageName(targetStage) + " — WorldScan will apply"
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
	m.LastVictimStatus = "queued stage " + targetStage + " " + m.GetDecayStageName(targetStage) + " — close MCM to apply"
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

Function RunPendingDecayAdvance()
	PickmansWhisperMainQuestScript m = Main()
	Actor aimed = PendingDecayAdvanceActor
	Int stage = PendingDecayAdvanceStage
	Int formId = PendingDecayAdvanceFormId
	If !m || !aimed || stage < 0 || formId == 0
		Debug.Trace("PickmansWhisper: RunPendingDecayAdvance skip — empty pending")
		Return
	EndIf
	; Do NOT clear pending while MCM/Pause is open — old path wiped the queue then returned,
	; so face/body never applied after "close MCM to apply".
	If Utility.IsInMenuMode()
		CancelTimer(TIMER_DECAY_ADVANCE)
		StartTimer(DECAY_ADVANCE_DELAY, TIMER_DECAY_ADVANCE)
		Debug.Trace("PickmansWhisper: RunPendingDecayAdvance defer — still in menu; pending kept stage=" + stage)
		Return
	EndIf
	; Owned only after we leave menu and commit to apply (or fail hard).
	PendingDecayAdvanceActor = None
	PendingDecayAdvanceStage = -1
	PendingDecayAdvanceFormId = 0
	If !aimed.Is3DLoaded() || aimed.IsDisabled() || !aimed.IsDead()
		m.LastVictimStatus = "advance decay: corpse gone before apply"
		Debug.Notification("Pickman's Whisper: advance decay — corpse gone before apply")
		Debug.Trace("PickmansWhisper: ERROR RunPendingDecayAdvance — corpse invalid")
		Return
	EndIf
	PickmansWhisperCorpseDecayScript decay = CorpseDecay()
	If !decay
		m.LastVictimStatus = "advance decay: CorpseDecay script missing"
		Debug.Notification("Pickman's Whisper: CorpseDecay script missing")
		Debug.Trace("PickmansWhisper: ERROR RunPendingDecayAdvance — CorpseDecay missing")
		Return
	EndIf
	If !decay.ApplyDecayStageOverlays(aimed, stage)
		m.LastVictimStatus = "advance decay: apply failed — " + m.LastCorpseDecayStatus
		Debug.Notification("Pickman's Whisper: advance decay apply failed — " + m.LastCorpseDecayStatus)
		Debug.Trace("PickmansWhisper: ERROR RunPendingDecayAdvance apply — " + m.LastCorpseDecayStatus)
		Return
	EndIf
	m.SetDecayKillLastStage(formId, stage)
	m.LastVictimStatus = "advanced to " + stage + " " + m.GetDecayStageName(stage) + " | " + m.LastCorpseDecayStatus
	Debug.Notification("Pickman's Whisper: decay stage " + stage + " " + m.GetDecayStageName(stage))
	Debug.Trace("PickmansWhisper: RunPendingDecayAdvance ok stage=" + stage + " id=0x" + GardenOfEden.GetHexFormID(aimed))
EndFunction

Bool Function AdvanceAimedDecayStage()
	If !QueueAimedDecayAdvance()
		Return False
	EndIf
	Int formId = PendingDecayAdvanceFormId
	Int stage = PendingDecayAdvanceStage
	RunPendingDecayAdvance()
	PickmansWhisperMainQuestScript m = Main()
	If !m || formId == 0
		Return False
	EndIf
	Return m.GetDecayKillLastStage(formId) == stage
EndFunction

; Apply MCM stepper iVictimDecayStage:Victims (any stage 0–4) — sync like Wound Lab.
Function MCMApplyAimedDecayStage()
	Debug.Notification("PW Victims — Apply decay CallFunction hit")
	Debug.Trace("PickmansWhisper: MCMApplyAimedDecayStage OK")
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
	; Cancel any leftover deferred queue so timer cannot double-apply after sync.
	ClearPendingDecayAdvance()
	Bool ok = PrepAimedDecayStage(stage)
	Actor aimed = ResolveVictimsAimActor()
	Int formId = 0
	If aimed
		formId = aimed.GetFormID()
	EndIf
	If ok
		PickmansWhisperCorpseDecayScript decay = CorpseDecay()
		If !decay
			ok = False
			If m
				m.LastVictimStatus = "set decay: CorpseDecay script missing"
			EndIf
		ElseIf !decay.ApplyDecayStageOverlays(aimed, stage)
			ok = False
			If m
				m.LastVictimStatus = "set decay: apply failed — " + m.LastCorpseDecayStatus
			EndIf
		Else
			If m && formId != 0
				m.SetDecayKillLastStage(formId, stage)
				m.LastVictimStatus = "applied stage " + stage + " " + m.GetDecayStageName(stage) + " | " + m.LastCorpseDecayStatus
			EndIf
			Debug.Trace("PickmansWhisper: MCMApplyAimedDecayStage sync ok stage=" + stage)
		EndIf
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
		Debug.MessageBox("Pickman's Whisper — Set decay stage\n\n" + status + "\n\nClose MCM to look at the body.")
	Else
		Debug.MessageBox("Pickman's Whisper — Set decay stage\n\nFailed / skipped:\n" + status)
	EndIf
EndFunction

; Legacy +1 MCM entry — sync apply (same as Apply; no close-MCM timer).
Function MCMAdvanceAimedDecayStage()
	Debug.Notification("PW Victims — Advance decay CallFunction hit")
	Debug.Trace("PickmansWhisper: MCMAdvanceAimedDecayStage OK")
	PickmansWhisperMainQuestScript m = Main()
	ClearPendingDecayAdvance()
	Actor aimed = ResolveVictimsAimActor()
	Int formId = 0
	If aimed
		formId = aimed.GetFormID()
	EndIf
	Int visual = 0
	Bool ok = False
	If m && aimed && formId != 0 && aimed.IsDead()
		If m.FindDecayKillSlot(formId) < 0
			m.StampDecayKill(aimed)
		EndIf
		Int applied = m.GetDecayKillLastStage(formId)
		Int resolved = m.ResolveDecayStageForKill(formId)
		visual = applied
		If visual < 0
			visual = resolved
		EndIf
		If visual < 0
			visual = 0
		EndIf
		If visual >= 4
			m.LastVictimStatus = "advance decay: already " + m.GetDecayStageName(4) + " (stage 4)"
		Else
			Int nextStage = visual + 1
			ok = PrepAimedDecayStage(nextStage)
			If ok
				PickmansWhisperCorpseDecayScript decay = CorpseDecay()
				If !decay
					ok = False
					m.LastVictimStatus = "advance decay: CorpseDecay script missing"
				ElseIf !decay.ApplyDecayStageOverlays(aimed, nextStage)
					ok = False
					m.LastVictimStatus = "advance decay: apply failed — " + m.LastCorpseDecayStatus
				Else
					m.SetDecayKillLastStage(formId, nextStage)
					m.LastVictimStatus = "applied stage " + nextStage + " " + m.GetDecayStageName(nextStage) + " | " + m.LastCorpseDecayStatus
					Debug.Trace("PickmansWhisper: MCMAdvanceAimedDecayStage sync ok stage=" + nextStage)
				EndIf
			EndIf
		EndIf
	ElseIf m
		m.LastVictimStatus = "advance decay: no aim — face a corpse in-world ~2s, then retry"
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
		Debug.MessageBox("Pickman's Whisper — Advance decay\n\n" + status + "\n\nClose MCM to look at the body.")
	Else
		Debug.MessageBox("Pickman's Whisper — Advance decay\n\nFailed / skipped:\n" + status)
	EndIf
EndFunction
