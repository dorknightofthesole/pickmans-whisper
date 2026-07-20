Scriptname PickmansWhisperWorldScanScript extends Quest
{Single neighborhood scanner — FindActors once, snapshot, then DIRECT listener dispatch.
Same-quest CustomEvent delivery proved unreliable for VoiceScan (whispers stayed dead).
Voice runs sync first; knife/overlays use CallFunctionNoWait (LooksMenu Utility.Wait).}

; Kept for optional external mods — internal listeners use direct/NoWait dispatch.
CustomEvent OnWorldScan

Int TIMER_WORLD_SCAN = 16
Float WORLD_SCAN_SECONDS = 2.0
Float KILL_WATCH_RADIUS = 800.0
Float KILL_CORPSE_RADIUS = 400.0
Float FACING_DEG = 75.0

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
Actor PlayerRef

PickmansWhisperMainQuestScript Function Main()
	Return (Self as Quest) as PickmansWhisperMainQuestScript
EndFunction

PickmansWhisperVoiceScanScript Function VoiceScan()
	Return (Self as Quest) as PickmansWhisperVoiceScanScript
EndFunction

PickmansWhisperCorpseDecayScript Function CorpseDecay()
	Return (Self as Quest) as PickmansWhisperCorpseDecayScript
EndFunction

Function StartWorldScanLoop()
	CancelTimer(TIMER_WORLD_SCAN)
	StartTimer(WORLD_SCAN_SECONDS, TIMER_WORLD_SCAN)
EndFunction

Function AnnounceWorldScanArmed()
	If ScanArmAnnounced
		Return
	EndIf
	ScanArmAnnounced = True
	PickmansWhisperMainQuestScript m = Main()
	If m
		m.ToastDebug("PW world scan armed")
	EndIf
	Debug.Trace("PickmansWhisper: world scan armed")
EndFunction

Event OnTimer(Int aiTimerID)
	If aiTimerID != TIMER_WORLD_SCAN
		Return
	EndIf
	; Re-arm FIRST — mid-tick abort must not silence ambient forever.
	StartWorldScanLoop()
	RunWorldScanTick()
EndEvent

Function RunWorldScanTick()
	PlayerRef = Game.GetPlayer()
	If !PlayerRef
		Return
	EndIf

	AnnounceWorldScanArmed()

	PickmansWhisperMainQuestScript m = Main()
	If !m
		Debug.Trace("PickmansWhisper: ERROR WorldScan — Main script missing")
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

	; --- Living / detecting / dead (single producer) ---------------------------
	Actor[] alive = GardenOfEden.FindActors(None, None, -1, -1, PlayerRef, KILL_WATCH_RADIUS, 1, -1, -1, -1, -1, -1, None, None, "", 0, 1, 0)
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

	Actor[] dead = GardenOfEden.FindActors(None, None, -1, -1, PlayerRef, KILL_CORPSE_RADIUS, 0, 1, -1, -1, -1, -1, None, None, "", 0, 1, 1)
	ScanDead = dead
	ScanDeadCount = 0
	If dead
		ScanDeadCount = dead.Length
	EndIf

	FacedLiving = ResolveFacedLiving()
	FacedDead = ResolveFacedDead()

	ScanTick += 1
	m.NoteWorldScanCounts(ScanTick, ScanAliveCount, ScanDeadCount, ScanDetectCount)

	; Direct dispatch — do NOT rely on same-quest CustomEvent for voice.
	DispatchListeners()
EndFunction

; Voice sync first; knife/overlays NoWait so LooksMenu Wait cannot starve whispers.
Function DispatchListeners()
	PickmansWhisperVoiceScanScript voice = VoiceScan()
	If voice
		voice.HandleWorldScanVoice(Self)
	ElseIf !VoiceMissingToasted
		VoiceMissingToasted = True
		Debug.Notification("Pickman's Whisper: VoiceScan script missing — rebuild esp")
		Debug.Trace("PickmansWhisper: ERROR VoiceScan script missing on Main quest")
	EndIf

	PickmansWhisperMainQuestScript m = Main()
	If m
		m.CallFunctionNoWait("HandleWorldScanKnifeAimWarm", None)
	EndIf

	; Overlays throttled — LooksMenu Wait must never run on this stack.
	If (ScanTick % 4) == 0
		PickmansWhisperCorpseDecayScript decay = CorpseDecay()
		If decay
			decay.CallFunctionNoWait("SyncOverlaysFromWorldScanSnapshot", None)
		EndIf
	EndIf
EndFunction

Actor Function ResolveFacedLiving()
	If CameraActor && !CameraActor.IsDisabled() && !CameraActor.IsDead()
		Return CameraActor
	EndIf
	If !PlayerRef || !ScanAlive || ScanAliveCount <= 0
		Return None
	EndIf
	Actor best = None
	Float bestDist = KILL_WATCH_RADIUS + 1.0
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
				If d <= KILL_WATCH_RADIUS && d < bestDist
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
	Actor best = None
	Float bestDist = KILL_CORPSE_RADIUS + 1.0
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
				If d <= KILL_CORPSE_RADIUS && d < bestDist
					bestDist = d
					best = ak
				EndIf
			EndIf
		EndIf
		i += 1
	EndWhile
	Return best
EndFunction
