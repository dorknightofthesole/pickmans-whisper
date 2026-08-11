Scriptname PickmansWhisperSlaveSceneScript extends Quest
{Slice U — two-actor AAF scene (player + enslaved NPC), 4th activate choice ("Take Her",
replaces Free). Gated on MainQuest.IsOurSlave(target). Clones Necromantic's own approach
100% (D:\GitHub\aaf-necromantic) rather than tag-based auto-select: our own AAF data
(Data\AAF\PickmansWhisper_positionData.xml / _animationData.xml) defines a small, curated
set of genuine two-actor positions — Necromantic's exact 7-position list, paired instead
of solo, using verified real F+M idleForm pairs from rxl_bp70_animations.esp (the same
plugin Necromantic already depends on — checked directly against the installed "BP70s
Fallout 4 Sex anims 2.8" pack's own animationData.xml, not guessed). settings.position is
an exact id chosen at random (Utility.RandomInt) from every line in
Data\PickmansWhisper\config\SlaveScenePositions.txt on each scene start — no in-game
cycling. AAF's own in-scene "Wizard" (Home to open, Delete/Backspace to cycle, confirmed
via AAF_settings.ini [HOTKEYS] + AAF_En.TXT strings) was tried live first — it opened but
did not change position, likely because these positions are isHidden="true"; random pick
per scene is the fallback that still gives variety without needing to un-hide them.
Tag-based auto-select (settings.includeTags) was tried first and abandoned — checked
several real installed 2-actor packs (Leito, Atomic Lust, rufGT's: 140 positions) and
almost none carry any tags at all, so any tag filter matched ~nothing and every attempt
failed AAF's OnSceneInit validation regardless of which tag was tried. No corpse/ghost
alignment logic (unlike Necromantic's solo scenes) — both actors are real AAF
participants; AAF's own StartScene positioning handles placement. CTD-avoidance patterns
(interior-only default, EnsureAAFStoppedForRestart checking BOTH actors' busy state,
watchdog + max-duration timers, careful event re-registration) mirror that mod's
hard-won production experience with the same AAF Papyrus API.}

; Bump on every meaningful change to this script and include in the key trace lines below
; (LoadAAF ready, StartScene, OnSceneInit failure) — the fastest way to confirm from the
; log alone whether a fresh deploy is actually the one running, instead of guessing from
; message text that hasn't changed between builds.
String SCENE_BUILD_TAG = "U-2026-08-10.1-exactpos"

AAF:AAF_API AAF_API
Keyword AAF_ActorBusy

Actor SceneTarget
Bool SceneActive
Int SceneGeneration = 0
Bool SceneEndSent = False
String ScenePhase = "Idle" ; Idle | Starting | Playing | Cancelling
String LastPositionId = "" ; what StartSlaveScene actually passed AAF last attempt
Float LastDuration = -1.0
Int LastOnSceneInitStatus = -1 ; -1 = no attempt yet this session

; Slice U position bank — Data\PickmansWhisper\config\SlaveScenePositions.txt. Every
; StartSlaveScene picks a fresh random index (Utility.RandomInt); no persisted cycling
; state, unlike the Wound Lab template banks or Necromantic's own U/P-driven PositionIndex.
String[] SlaveScenePositions
Int SlaveScenePositionCount = 0
Bool SlaveScenePositionBankLoaded = False
String SLAVE_SCENE_POSITIONS_FILE = "SlaveScenePositions.txt"
String SLAVE_SCENE_POSITIONS_PATH = ".\\Data\\PickmansWhisper\\config\\"

; Own OnTimer id space — a co-script's timers only ever fire its own OnTimer, never a
; sibling's, so these don't need to avoid collisions with other Main co-scripts.
Int TIMER_SCENE_WATCHDOG = 1
Int TIMER_SCENE_MAX = 2
Float WATCHDOG_POLL_SECONDS = 0.5
Float MAX_DURATION_PAD_SECONDS = 2.0

PickmansWhisperMainQuestScript Function Main()
	Return (Self as Quest) as PickmansWhisperMainQuestScript
EndFunction

PickmansWhisperSlaveryScript Function Slavery()
	Return (Self as Quest) as PickmansWhisperSlaveryScript
EndFunction

; File is the single source — no hardcoded fallback id. Same LoadStageBankAt loader every
; other bank in this mod uses (Wound/Skin/Face/Tattoo templates); we just never advance
; past index 0 (no U/P cycling, per spec — this is a fixed, script-driven choice).
Bool Function EnsureSlaveScenePositionBank()
	If SlaveScenePositionBankLoaded && SlaveScenePositionCount > 0
		Return True
	EndIf
	PickmansWhisperMainQuestScript m = Main()
	If !m || !m.VoiceAlias
		Debug.Trace("PickmansWhisper: ERROR slave scene — Main/VoiceAlias missing — cannot load " + SLAVE_SCENE_POSITIONS_FILE)
		Return False
	EndIf
	SlaveScenePositions = new String[16]
	SlaveScenePositionCount = m.VoiceAlias.LoadStageBankAt(SLAVE_SCENE_POSITIONS_FILE, SlaveScenePositions, SLAVE_SCENE_POSITIONS_PATH)
	SlaveScenePositionBankLoaded = True
	If SlaveScenePositionCount <= 0
		Debug.Trace("PickmansWhisper: ERROR slave scene — " + SLAVE_SCENE_POSITIONS_FILE + " — " + m.VoiceAlias.GetLastStageLoadStatus())
		Return False
	EndIf
	Return True
EndFunction

; Fresh random pick every call — no persisted index, no in-game cycling (see class doc
; comment: AAF's own in-scene Wizard was tried live and didn't change position for these
; isHidden positions, so a random pick per scene is the variety fallback).
String Function GetSlaveScenePositionId()
	If !EnsureSlaveScenePositionBank()
		Return ""
	EndIf
	Int idx = Utility.RandomInt(0, SlaveScenePositionCount - 1)
	Return SlaveScenePositions[idx]
EndFunction

; Called from Main.RegisterFeatureScripts on OnQuestInit + every load-game resume (same
; pattern Necromantic uses for LoadAAF — AAF re-fires OnAAFReady on its own re-init, so
; re-registering here and again inside OnAAFReady is intentional, not redundant).
Function LoadAAF()
	AAF_API = Game.GetFormFromFile(0x00000F99, "AAF.esm") as AAF:AAF_API
	AAF_ActorBusy = Game.GetFormFromFile(0x0000915A, "AAF.esm") as Keyword
	If AAF_API
		UnregisterForCustomEvent(AAF_API, "OnAAFReady")
		UnregisterForCustomEvent(AAF_API, "OnSceneInit")
		UnregisterForCustomEvent(AAF_API, "OnSceneEnd")
		UnregisterForCustomEvent(AAF_API, "OnAnimationStart")
		UnregisterForCustomEvent(AAF_API, "OnAnimationStop")
		RegisterForCustomEvent(AAF_API, "OnAAFReady")
		RegisterForCustomEvent(AAF_API, "OnSceneInit")
		RegisterForCustomEvent(AAF_API, "OnSceneEnd")
		RegisterForCustomEvent(AAF_API, "OnAnimationStart")
		RegisterForCustomEvent(AAF_API, "OnAnimationStop")
		Debug.Trace("PickmansWhisper: slave scene [" + SCENE_BUILD_TAG + "] — AAF API ready, version " + AAF_API.GetVersion())
	Else
		Debug.Trace("PickmansWhisper: slave scene [" + SCENE_BUILD_TAG + "] — AAF API not found (AAF.esm absent?)")
	EndIf
EndFunction

Event AAF:AAF_API.OnAAFReady(AAF:AAF_API akSender, Var[] akArgs)
	Debug.Trace("PickmansWhisper: slave scene — OnAAFReady, refreshing event binds")
	If !AAF_API
		Return
	EndIf
	UnregisterForCustomEvent(AAF_API, "OnSceneInit")
	UnregisterForCustomEvent(AAF_API, "OnSceneEnd")
	UnregisterForCustomEvent(AAF_API, "OnAnimationStart")
	UnregisterForCustomEvent(AAF_API, "OnAnimationStop")
	RegisterForCustomEvent(AAF_API, "OnSceneInit")
	RegisterForCustomEvent(AAF_API, "OnSceneEnd")
	RegisterForCustomEvent(AAF_API, "OnAnimationStart")
	RegisterForCustomEvent(AAF_API, "OnAnimationStop")
EndEvent

Bool Function IsPlayerAAFBusy()
	If !AAF_ActorBusy
		Return False
	EndIf
	Actor player = Game.GetPlayer()
	If !player
		Return False
	EndIf
	Return player.HasKeyword(AAF_ActorBusy)
EndFunction

; CumOverlay (a third-party AAF-integrated mod, confirmed via its own source) just echoes
; the same OnSceneInit status we already see — not the cause of a failed start. A real
; candidate: IsPlayerAAFBusy only ever checked the player, never the target — if she was
; left holding a stale AAF_ActorBusy keyword from a prior aborted attempt (every attempt
; here reused the same target), EnsureAAFStoppedForRestart would never have noticed or
; cleared it, since it never looked at her side at all.
Bool Function IsActorAAFBusy(Actor ak)
	If !AAF_ActorBusy || !ak
		Return False
	EndIf
	Return ak.HasKeyword(AAF_ActorBusy)
EndFunction

; Exteriors are CTD-prone for AAF scene starts (same finding Necromantic's own testing
; produced) — interior-only unless the MCM debug toggle allows it.
Bool Function CanStartSceneInCurrentCell()
	Actor player = Game.GetPlayer()
	If !player
		Return False
	EndIf
	Cell c = player.GetParentCell()
	If !c
		Return False
	EndIf
	If c.IsInterior()
		Return True
	EndIf
	If MCM.IsInstalled() && MCM.GetModSettingBool("PickmansWhisper", "bAllowExteriorSlaveScene:Debug")
		Return True
	EndIf
	Return False
EndFunction

Function EnsureAAFStoppedForRestart(Actor akOther)
	If !AAF_API
		Return
	EndIf
	If IsPlayerAAFBusy() || IsActorAAFBusy(akOther)
		Debug.Trace("PickmansWhisper: slave scene — stopping leftover AAF before new scene (player busy=" + IsPlayerAAFBusy() + " target busy=" + IsActorAAFBusy(akOther) + ")")
		AAF_API.StopSceneWithAbruptStop()
		AAF_API.StopScene()
		Utility.Wait(0.35)
	EndIf
EndFunction

; Gameplay entry from the Slavery perk (OnEntryRun, via MainQuestScript facade). Re-
; validates everything — auiEntryID isn't trusted (see SlaveryPerkScript), and this may
; be reached from a stale menu state.
Function TryStartSlaveSceneFromActivate(Actor akTarget)
	If !akTarget
		Debug.Trace("PickmansWhisper: slave scene skip | no activate target")
		Debug.Notification("PickmansWhisper: Slavery — no target")
		Return
	EndIf
	PickmansWhisperMainQuestScript m = Main()
	If !m
		Debug.Trace("PickmansWhisper: ERROR slave scene — Main missing")
		Return
	EndIf
	If m.IsBladeEquipped()
		Debug.Trace("PickmansWhisper: slave scene skip | blade drawn")
		Debug.Notification("PickmansWhisper: Slavery — sheath the blade first")
		Return
	EndIf
	PickmansWhisperSlaveryScript slavery = Slavery()
	If !slavery || !slavery.IsOurSlave(akTarget)
		Debug.Trace("PickmansWhisper: slave scene skip | not our slave id=" + akTarget.GetFormID())
		Debug.Notification("PickmansWhisper: Slavery — she is not yours")
		Return
	EndIf
	If akTarget.IsDead()
		Debug.Trace("PickmansWhisper: slave scene skip | target dead id=" + akTarget.GetFormID())
		Debug.Notification("PickmansWhisper: Slavery — target is dead")
		Return
	EndIf
	If SceneActive
		Debug.Trace("PickmansWhisper: slave scene skip | already active")
		Debug.Notification("PickmansWhisper: Slavery — scene already in progress")
		Return
	EndIf
	If !CanStartSceneInCurrentCell()
		Debug.Trace("PickmansWhisper: slave scene skip | exterior cell not allowed")
		Debug.Notification("PickmansWhisper: Slavery — indoors only (CTD risk outside)")
		Return
	EndIf
	If !AAF_API
		LoadAAF()
	EndIf
	If !AAF_API
		Debug.Trace("PickmansWhisper: slave scene skip | AAF not ready")
		Debug.Notification("PickmansWhisper: Slavery — AAF not ready (AAF.esm installed?)")
		Return
	EndIf
	Float duration = -1.0
	If m.ModConfigAlias
		duration = m.ModConfigAlias.GetAafSlaveSceneDurationSeconds()
	EndIf
	If duration <= 0.0
		Debug.Trace("PickmansWhisper: ERROR slave scene — ModConfig aafSlaveSceneDurationSeconds missing/invalid")
		Debug.Notification("PickmansWhisper: Slavery — ModConfig aafSlaveSceneDurationSeconds missing")
		Return
	EndIf
	String positionId = GetSlaveScenePositionId()
	If !positionId || positionId == ""
		Debug.Trace("PickmansWhisper: ERROR slave scene — " + SLAVE_SCENE_POSITIONS_FILE + " missing/empty")
		Debug.Notification("PickmansWhisper: Slavery — SlaveScenePositions.txt missing/empty")
		Return
	EndIf
	StartSlaveScene(akTarget, duration, positionId)
EndFunction

Function StartSlaveScene(Actor akTarget, Float afDuration, String asPositionId)
	EnsureAAFStoppedForRestart(akTarget)
	Actor[] actors = new Actor[2]
	actors[0] = Game.GetPlayer()
	actors[1] = akTarget

	AAF:AAF_API:SceneSettings settings = AAF_API.GetSceneSettings()
	settings.duration = afDuration
	settings.skipWalk = True
	settings.preventFurniture = True ; every PW TakeHer position is ground/"NoFurn" — matches Necromantic
	settings.usePackages = False ; matches Necromantic's solo scene setting
	settings.isNPCControlled = False ; matches Necromantic's solo scene setting
	settings.position = asPositionId ; exact id from Data\AAF\PickmansWhisper_positionData.xml — no tag matching
	settings.locationObject = Game.GetPlayer()

	SceneTarget = akTarget
	SceneGeneration += 1
	SceneEndSent = False
	ScenePhase = "Starting"
	SceneActive = True
	LastPositionId = asPositionId
	LastDuration = afDuration
	LastOnSceneInitStatus = -1 ; reset — OnSceneInit will set the real value for this attempt
	StartTimer(WATCHDOG_POLL_SECONDS, TIMER_SCENE_WATCHDOG)
	StartTimer(afDuration + MAX_DURATION_PAD_SECONDS, TIMER_SCENE_MAX)
	Debug.Trace("PickmansWhisper: slave scene [" + SCENE_BUILD_TAG + "] — StartScene gen=" + SceneGeneration + " position='" + asPositionId + "' duration=" + afDuration + " isNPCControlled=" + settings.isNPCControlled + " preventFurniture=" + settings.preventFurniture + " usePackages=" + settings.usePackages + " target=0x" + GardenOfEden.GetHexFormID(akTarget) + " playerBusy=" + IsPlayerAAFBusy() + " targetBusy=" + IsActorAAFBusy(akTarget))
	If !AAF_ActorBusy
		Debug.Trace("PickmansWhisper: slave scene [" + SCENE_BUILD_TAG + "] — WARNING AAF_ActorBusy keyword missing, relying on duration timer")
	EndIf
	AAF_API.StartScene(actors, settings)
EndFunction

; Teardown — idempotent (SceneEndSent guards against OnAnimationStop + OnSceneEnd both
; firing, or the max-duration timer racing a real end signal).
Function EndSlaveScene(Bool abNatural)
	If SceneEndSent
		Return
	EndIf
	SceneEndSent = True
	CancelTimer(TIMER_SCENE_WATCHDOG)
	CancelTimer(TIMER_SCENE_MAX)
	; Same gap as EnsureAAFStoppedForRestart had — check the target too, not just the
	; player, before deciding a stop is unnecessary.
	If AAF_API && (IsPlayerAAFBusy() || IsActorAAFBusy(SceneTarget))
		AAF_API.StopSceneWithAbruptStop()
		AAF_API.StopScene()
	EndIf
	SceneActive = False
	ScenePhase = "Idle"
	SceneTarget = None
	Debug.Trace("PickmansWhisper: slave scene [" + SCENE_BUILD_TAG + "] — ended gen=" + SceneGeneration + " natural=" + abNatural + " lastStatus=" + LastOnSceneInitStatus)
	Debug.Notification("PickmansWhisper: Slavery — scene ended")
EndFunction

; MCM Debug "Cancel slave scene" button.
Function CancelSlaveScene()
	If !SceneActive
		Return
	EndIf
	ScenePhase = "Cancelling"
	If AAF_API
		AAF_API.StopSceneWithAbruptStop()
		AAF_API.StopScene()
	EndIf
	EndSlaveScene(False)
	Debug.Notification("PickmansWhisper: Slavery — scene cancelled")
EndFunction

Event OnTimer(Int aiTimerID)
	If aiTimerID == TIMER_SCENE_WATCHDOG
		If !SceneActive
			Return
		EndIf
		If IsPlayerAAFBusy()
			ScenePhase = "Playing"
		EndIf
		StartTimer(WATCHDOG_POLL_SECONDS, TIMER_SCENE_WATCHDOG)
	ElseIf aiTimerID == TIMER_SCENE_MAX
		If !SceneActive
			Return
		EndIf
		Debug.Trace("PickmansWhisper: slave scene — max-duration timer fired (OnSceneEnd flaky fallback)")
		EndSlaveScene(False)
	EndIf
EndEvent

Event AAF:AAF_API.OnSceneInit(AAF:AAF_API akSender, Var[] akArgs)
	If !SceneActive
		Return
	EndIf
	Int status = 0
	Int argCount = 0
	If akArgs
		argCount = akArgs.Length
	EndIf
	If argCount > 0
		status = akArgs[0] as Int
	EndIf
	LastOnSceneInitStatus = status
	; NOTE: akArgs[0]=status is the only index this script (or Necromantic's own real,
	; tested code) has ever read from OnSceneInit — every other akArgs read anywhere in
	; either codebase always casts a KNOWN index to a KNOWN type (never a generic dump),
	; because a Var cast to the wrong type silently yields empty/None rather than erroring
	; or stringifying — a blind per-index "as String" loop here would misreport missing
	; data as present-but-empty. argCount alone is honestly all that's safely knowable
	; about akArgs without first confirming AAF's real OnSceneInit signature.
	If status != 0
		Debug.Trace("PickmansWhisper: slave scene [" + SCENE_BUILD_TAG + "] — OnSceneInit failed status=" + status + " gen=" + SceneGeneration + " position='" + LastPositionId + "' duration=" + LastDuration + " argCount=" + argCount)
		Debug.Notification("PickmansWhisper: Slavery — scene failed to start, status=" + status + " (position '" + LastPositionId + "' — is BP70's rxl_bp70_animations.esp installed and active?)")
		EndSlaveScene(False)
		Return
	EndIf
	ScenePhase = "Playing"
	Debug.Trace("PickmansWhisper: slave scene [" + SCENE_BUILD_TAG + "] — OnSceneInit ok gen=" + SceneGeneration + " argCount=" + argCount)
EndEvent

Event AAF:AAF_API.OnAnimationStart(AAF:AAF_API akSender, Var[] akArgs)
	If !SceneActive
		Return
	EndIf
	ScenePhase = "Playing"
	Debug.Trace("PickmansWhisper: slave scene — OnAnimationStart")
EndEvent

; 1P scenes often skip OnSceneEnd (Necromantic's own finding) — treat anim-stop as end
; once AAF no longer reports the player busy.
Event AAF:AAF_API.OnAnimationStop(AAF:AAF_API akSender, Var[] akArgs)
	If !SceneActive
		Return
	EndIf
	If !IsPlayerAAFBusy()
		Debug.Trace("PickmansWhisper: slave scene — OnAnimationStop, player no longer busy -> treat as end")
		EndSlaveScene(True)
	EndIf
EndEvent

Event AAF:AAF_API.OnSceneEnd(AAF:AAF_API akSender, Var[] akArgs)
	If !SceneActive
		Return
	EndIf
	Debug.Trace("PickmansWhisper: slave scene — OnSceneEnd")
	EndSlaveScene(True)
EndEvent

; Includes SCENE_BUILD_TAG + last OnSceneInit status so the MCM Victims status row alone
; (no log dive needed) confirms which build is live and what the last failure was.
String Function GetSlaveSceneStatusLine()
	String tail = " [" + SCENE_BUILD_TAG + "] last status=" + LastOnSceneInitStatus
	If !SceneActive
		Return "Idle" + tail
	EndIf
	If SceneTarget
		Return ScenePhase + " (0x" + GardenOfEden.GetHexFormID(SceneTarget) + ")" + tail
	EndIf
	Return ScenePhase + tail
EndFunction
