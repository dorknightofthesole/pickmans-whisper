Scriptname PickmansWhisperKillerScanScript extends Quest
{Killer Orchestrator — sole recurring timer. Builds TargetSnapshot (living + dead
neighborhood), then dispatches ROADMAP listeners. Voice sync first; knife/overlays
NoWait. No feature side effects beyond scan + dispatch.}

Int TIMER_KILLER_SCAN = 16
Float KILLER_SCAN_SECONDS = 2.0
; While TickBusy, skip RunKillerScanTick this many times; on the next busy
; pulse, force-clear and run (prior tick likely aborted without clearing).
Int BUSY_MAX_SKIPS = 2
Float FACING_DEG = 75.0

; TargetSnapshot — listeners read these; KillerScan is the only FindActors producer.
Actor[] Property ScanAlive Auto
Int Property ScanAliveCount = 0 Auto
Actor[] Property ScanDead Auto
Int Property ScanDeadCount = 0 Auto
Actor[] Property ScanDetecting Auto
Int Property ScanDetectCount = 0 Auto
Actor Property FacedLiving Auto
Actor Property FacedDead Auto
Actor Property CombatTarget Auto
Actor Property CameraActor Auto
Bool Property BladeKillReady = False Auto
Bool Property BladeDrawn = False Auto
Int Property ScanTick = 0 Auto

Bool ScanArmAnnounced = False
Bool VoiceMissingToasted = False
Bool VersionBannerLogged = False
Bool TickBusy = False
Int BusySkipCount = 0
Actor PlayerRef

PickmansWhisperMainQuestScript Function Main()
	Return (Self as Quest) as PickmansWhisperMainQuestScript
EndFunction

PickmansWhisperCorpseDecayScript Function CorpseDecay()
	Return (Self as Quest) as PickmansWhisperCorpseDecayScript
EndFunction

PickmansWhisperTargetScanScript Function TargetScan()
	Return (Self as Quest) as PickmansWhisperTargetScanScript
EndFunction

PickmansWhisperVictimsScript Function Victims()
	Return (Self as Quest) as PickmansWhisperVictimsScript
EndFunction

PickmansWhisperBuffTrackerScript Function BuffTracker()
	Return (Self as Quest) as PickmansWhisperBuffTrackerScript
EndFunction

PickmansWhisperBeatBeforeKillScript Function BeatBeforeKill()
	Return (Self as Quest) as PickmansWhisperBeatBeforeKillScript
EndFunction

PickmansWhisperDesperateRenameScript Function DesperateRename()
	Return (Self as Quest) as PickmansWhisperDesperateRenameScript
EndFunction

Function StartKillerScanLoop()
	Debug.Notification("PW Error: StartKillerScanLoop is being called")
	Debug.Trace("PW Error: StartKillerScanLoop is being called")
	; CancelTimer(TIMER_KILLER_SCAN)
	; StartTimer(KILLER_SCAN_SECONDS, TIMER_KILLER_SCAN)
EndFunction

Function AnnounceKillerScanArmed()
	If ScanArmAnnounced
		Return
	EndIf
	ScanArmAnnounced = True
	PickmansWhisperMainQuestScript m = Main()
	If m
		m.ToastDebug("PW KillerScan armed")
	EndIf
	Debug.Trace("PickmansWhisper: KillerScan armed (Killer Orchestrator)")
EndFunction

Function LogVersionBannerOnce()
	If VersionBannerLogged
		Return
	EndIf
	VersionBannerLogged = True
	Debug.Trace("PickmansWhisper: === v1.3.0 Killer Orchestrator loaded ===")
EndFunction

Event OnTimer(Int aiTimerID)
	Debug.Notification("PW Error: KillerScan OnTimer is being called")
	Debug.Trace("PW Error: KillerScan OnTimer is being called")

	If aiTimerID != TIMER_KILLER_SCAN
		Debug.Trace("PickmansWhisper: KillerScan OnTimer ignore id=" + aiTimerID)
		Return
	EndIf
	; Re-arm FIRST — mid-tick abort must not silence ambient forever.
	; Busy flag never blocks re-arm; it only skips overlapping work.
	StartKillerScanLoop()

	If TickBusy
		BusySkipCount += 1
		If BusySkipCount <= BUSY_MAX_SKIPS
			Debug.Trace("PickmansWhisper: KillerScan skip — tick busy (" + BusySkipCount + "/" + BUSY_MAX_SKIPS + ")")
			Return
		EndIf
		; Prior tick likely died without clearing — fail-open and run.
		Debug.Trace("PickmansWhisper: KillerScan busy watchdog — force clear after " + BusySkipCount + " busy pulses")
		TickBusy = False
		BusySkipCount = 0
	EndIf

	TickBusy = True
	BusySkipCount = 0
	RunKillerScanTick()
	TickBusy = False
EndEvent

Function RunKillerScanTick()
	LogVersionBannerOnce()
	PlayerRef = Game.GetPlayer()
	If !PlayerRef
		Debug.Trace("PickmansWhisper: ERROR KillerScan — no player")
		Return
	EndIf

	AnnounceKillerScanArmed()
	BuildTargetSnapshot()
	DispatchListeners()
EndFunction

; Sole FindActors producer — TargetSnapshot for all listeners.
Function BuildTargetSnapshot()
	PickmansWhisperMainQuestScript m = Main()
	If !m
		Debug.Trace("PickmansWhisper: ERROR KillerScan BuildTargetSnapshot — Main missing")
		Return
	EndIf

	BladeDrawn = m.IsBladeEquipped()
	BladeKillReady = m.IsBladeKillWeaponReady()
	CombatTarget = PlayerRef.GetCombatTarget()

	ObjectReference cam = GardenOfEden3.GetCameraTargetReference()
	CameraActor = cam as Actor
	If CameraActor == PlayerRef
		CameraActor = None
	EndIf

	PickmansWhisperTargetScanScript ts = TargetScan()
	If !ts
		Debug.Trace("PickmansWhisper: ERROR KillerScan BuildTargetSnapshot — TargetScan missing")
		Return
	EndIf
	Float watchR = ts.KILL_WATCH_RADIUS
	Float corpseR = ts.KILL_CORPSE_RADIUS

	Actor[] alive = GardenOfEden.FindActors(None, None, -1, -1, PlayerRef, watchR, 1, -1, -1, -1, -1, -1, None, None, "", 0, 1, 0)
	ScanAlive = alive
	ScanAliveCount = 0
	If alive
		ScanAliveCount = alive.Length
	EndIf

	Actor[] detecting = GardenOfEden2.GetActorsDetecting(PlayerRef, False)
	ScanDetecting = detecting
	ScanDetectCount = 0
	If detecting
		ScanDetectCount = detecting.Length
	EndIf

	Actor[] dead = GardenOfEden.FindActors(None, None, -1, -1, PlayerRef, corpseR, 0, 1, -1, -1, -1, -1, None, None, "", 0, 1, 1)
	ScanDead = dead
	ScanDeadCount = 0
	If dead
		ScanDeadCount = dead.Length
	EndIf

	FacedLiving = ResolveFacedLiving()
	FacedDead = ResolveFacedDead()

	ScanTick += 1
	m.NoteKillerScanCounts(ScanTick, ScanAliveCount, ScanDeadCount, ScanDetectCount)
EndFunction

; Voice sync first; knife/overlays/cadence NoWait so LooksMenu Wait cannot starve whispers.
Function DispatchListeners()
	PickmansWhisperMainQuestScript m = Main()
	If m && m.VoiceAlias
		m.VoiceAlias.HandleWhisperVoice(FacedLiving)
	ElseIf !VoiceMissingToasted
		VoiceMissingToasted = True
		Debug.Notification("Pickman's Whisper: VoiceAlias unbound — rebuild esp")
		Debug.Trace("PickmansWhisper: ERROR VoiceAlias unbound on Main quest")
	EndIf

	If m
		m.CallFunctionNoWait("HandleKillerScanKnifeAimWarm", None)
		m.CallFunctionNoWait("OnKillerScanCadence", None)
	Else
		Debug.Trace("PickmansWhisper: ERROR KillerScan Dispatch — Main missing (knife/cadence skipped)")
	EndIf

	PickmansWhisperVictimsScript victims = Victims()
	If victims
		victims.CallFunctionNoWait("NoteFromKillerScanSnapshot", None)
	Else
		Debug.Trace("PickmansWhisper: ERROR KillerScan Dispatch — Victims missing")
	EndIf

	; Slice H corpse decay: TargetScan / RegisterTarget → HandleCorpseDecay (not KillerScan).

	; Slice H P5 — buff expiry check. Cheap (two Float comparisons unless a buff is
	; both active and past expiry); no StartTimer of its own (Killer Orchestrator).
	PickmansWhisperBuffTrackerScript buffs = BuffTracker()
	If buffs
		buffs.CallFunctionNoWait("TickEndBuffExpiry", None)
	Else
		Debug.Trace("PickmansWhisper: ERROR KillerScan Dispatch — BuffTracker missing")
	EndIf

	; Slice K2-K5 — beat-before-kill ambient safety net: re-checks player weapon
	; state only (clears all if re-armed but OnItemEquipped somehow missed it). Does NOT
	; re-check combat state — that raced with an essential actor's own protected-
	; collapse moment and actively broke the feature (see BeatBeforeKillScript header).
	PickmansWhisperBeatBeforeKillScript beat = BeatBeforeKill()
	If beat
		beat.CallFunctionNoWait("TickEssentialReconcile", None)
	Else
		Debug.Trace("PickmansWhisper: ERROR KillerScan Dispatch — BeatBeforeKill missing")
	EndIf

	; BedGift is sleep/timer self-contained — no KillerScan dispatch.

	; Slice I desperate rename is aim-driven: Main.LookingAtTarget → DesperateRename(ak).
EndFunction

Actor Function ResolveFacedLiving()
	If CameraActor && !CameraActor.IsDisabled() && !CameraActor.IsDead()
		Return CameraActor
	EndIf
	If !PlayerRef || !ScanAlive || ScanAliveCount <= 0
		Return None
	EndIf
	PickmansWhisperTargetScanScript ts = TargetScan()
	If !ts
		Return None
	EndIf
	Float watchR = ts.KILL_WATCH_RADIUS
	Actor best = None
	Float bestDist = watchR + 1.0
	Int i = 0
	Int n = ScanAliveCount
	If n > 24
		n = 24
	EndIf
	While i < n
		Actor ak = ScanAlive[i]
		If ak && ak != PlayerRef && !ak.IsDead() && ak.Is3DLoaded() && !ak.IsDisabled()
			If Math.abs(PlayerRef.GetHeadingAngle(ak)) <= FACING_DEG
				Float d = PlayerRef.GetDistance(ak)
				If d <= watchR && d < bestDist
					bestDist = d
					best = ak
				EndIf
			EndIf
		EndIf
		i += 1
	EndWhile
	Return best
EndFunction

Actor Function ResolveFacedDead()
	If !PlayerRef || !ScanDead || ScanDeadCount <= 0
		Return None
	EndIf
	PickmansWhisperTargetScanScript ts = TargetScan()
	If !ts
		Return None
	EndIf
	Float corpseR = ts.KILL_CORPSE_RADIUS
	Actor best = None
	Float bestDist = corpseR + 1.0
	Int i = 0
	Int n = ScanDeadCount
	If n > 16
		n = 16
	EndIf
	While i < n
		Actor ak = ScanDead[i]
		If ak && ak != PlayerRef && ak.IsDead() && ak.Is3DLoaded() && !ak.IsDisabled()
			If Math.abs(PlayerRef.GetHeadingAngle(ak)) <= FACING_DEG
				Float d = PlayerRef.GetDistance(ak)
				If d <= corpseR && d < bestDist
					bestDist = d
					best = ak
				EndIf
			EndIf
		EndIf
		i += 1
	EndWhile
	Return best
EndFunction
