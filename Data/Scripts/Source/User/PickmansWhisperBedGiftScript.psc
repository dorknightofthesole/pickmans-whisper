Scriptname PickmansWhisperBedGiftScript extends Quest
{Slice G — bed corpse hallucination. Attached to PickmansWhisperMain alongside MainQuestScript.}

; Self-contained Slice G — sleep events + own timers. No KillerScan coupling.
; SleepStart: PlaceAtMe (blade/bond/MCM/cooldown gates via Main). SleepStop: Present.
; Overlay / pose / despawn: TIMER_BED_* oneshots (LooksMenu never on sleep stack).
; Main helpers only: OnBedGiftStatus, SetKnifeKillCreditSuppressed, NoteBackgroundDead,
; BondStarted / IsBladeEquipped / ModConfigAlias / VoiceAlias.

Int FID_BED_SPAWN_NPC = 0x00004DEC ; Fallout4.esm DiamondCityResidentF01NoodleMarket (unnamed Resident)
Int FID_KYWD_ANIM_FURN_BED = 0x000BC262 ; AnimFurnBedAnims
Int FID_KYWD_ANIM_FURN_FLOOR_BED = 0x0003ADA2 ; AnimFurnFloorBedAnims
String MOD_NAME = "PickmansWhisper"
Int TIMER_BED_OVERLAYS = 20
; One-shot re-arming pose timer — polls Is3DLoaded / settles after Snap without
; ever blocking the SleepStop wake stack (Utility.Wait does not re-arm itself).
Int TIMER_BED_POSE = 21
Int TIMER_BED_DESPAWN = 22
Int BED_POSE_MAX_TRIES = 20
Float BED_POSE_POLL_SECONDS = 0.1
Float BED_POSE_SETTLE_SECONDS = 0.5
; ~former 2 KillerScan pulses; real-time oneshot after Present.
Float BED_DESPAWN_SECONDS = 4.0
Float BED_DESPAWN_BUSY_RETRY_SECONDS = 0.5

Actor BedCorpse = None
ObjectReference BedAnchor = None
Bool BedPresentedThisSleep = False
Bool BedWakeHandledThisSleep = False ; Present ran (or interrupted) — ignore late duplicate SleepStop
Bool BedCorpseWarmed = False ; True only when parked under player (legacy park path)
Bool BedSpawnBusy = False
Bool BedOverlaysApplied = False ; True once Black Putrefaction path ran (pre-Enable when possible)
Bool BedOverlaysBusy = False ; LooksMenu apply in flight — blocks re-entry
Float BedOverlaysBusySinceReal = 0.0 ; real-time BedOverlaysBusy went True; despawn timeout basis
Float LastBedGiftGameTime = -999.0
; BedOverlaysBusy can get stuck True if a save loads mid-apply. Short watchdog so a
; stuck busy flag cannot block every later sleep from spawning a fresh body.
Float BED_OVERLAY_BUSY_TIMEOUT_SECONDS = 8.0
Float BED_OVERLAY_DELAY = 0.25 ; real-time after PlaceAtMe before LooksMenu oneshot
Float BED_SPAWN_OFFSET_X = 0.0
Float BED_SPAWN_OFFSET_Y = 8.0
Float BED_SPAWN_OFFSET_Z = 36.0
; -200 (≈2.9m) hides a parked body below floor/furniture while staying in the loaded bubble.
Float BED_WARM_PARK_Z = -200.0
String Property LastBedGiftStatus = "" Auto
Int BedPoseTriesRemaining = -1 ; -1 = no pose sequence in flight
Bool BedPoseAwaitingSettle = False
ObjectReference BedPoseAnchor = None
Bool BedSleepRegistered = False

PickmansWhisperMainQuestScript Function Main()
	; Caprica forbids Self-as-sibling; Quest intermediate is the FO4 co-script cast.
	Return (Self as Quest) as PickmansWhisperMainQuestScript
EndFunction

; Re-register every load (alias OnAliasInit / OnPlayerLoadGame → GetBedGift).
Function RegisterBedGiftSleep()
	If BedSleepRegistered
		UnregisterForPlayerSleep()
	EndIf
	RegisterForPlayerSleep()
	BedSleepRegistered = True
	Debug.Trace("PickmansWhisper: BedGift registered PlayerSleep")
EndFunction

Event OnPlayerSleepStart(Float afSleepStartTime, Float afDesiredSleepEndTime, ObjectReference akBed)
	HandlePlayerSleepStart(afSleepStartTime, afDesiredSleepEndTime, akBed)
EndEvent

Event OnPlayerSleepStop(Bool abInterrupted, ObjectReference akBed)
	HandlePlayerSleepStop(abInterrupted, akBed)
EndEvent

; Arm one-shot overlay timer. Does not reschedule from OnTimer.
Function KickBedOverlayOnesHot(Float afDelay)
	If !HasLiveBedCorpse()
		Debug.Trace("PickmansWhisper: bed overlay oneshot skip | no live corpse")
		Return
	EndIf
	If BedOverlaysBusy
		Debug.Trace("PickmansWhisper: bed overlay oneshot skip | apply busy")
		Return
	EndIf
	Float d = afDelay
	If d < 0.01
		d = 0.01
	EndIf
	CancelTimer(TIMER_BED_OVERLAYS)
	StartTimer(d, TIMER_BED_OVERLAYS)
	Debug.Trace("PickmansWhisper: bed overlay oneshot armed delay=" + d)
EndFunction

Event OnTimer(Int aiTimerID)
	If aiTimerID == TIMER_BED_OVERLAYS
		; One-shot — never StartTimer here (that would be a re-arm, not this exception).
		MaybeApplyBedGiftDecayOverlays()
		Return
	EndIf
	If aiTimerID == TIMER_BED_POSE
		AdvanceBedPoseSequence()
		Return
	EndIf
	If aiTimerID == TIMER_BED_DESPAWN
		OnBedDespawnTimer()
		Return
	EndIf
EndEvent

; Arm despawn oneshot after Present. Cancelled by ClearBedCorpse.
Function ArmBedDespawnTimer()
	CancelTimer(TIMER_BED_DESPAWN)
	Float d = BED_DESPAWN_SECONDS
	If d < 0.1
		d = 0.1
	EndIf
	StartTimer(d, TIMER_BED_DESPAWN)
	Debug.Trace("PickmansWhisper: bed despawn armed delay=" + d)
EndFunction

Function OnBedDespawnTimer()
	If !HasLiveBedCorpse()
		Return
	EndIf
	Float now = Utility.GetCurrentRealTime()
	If BedOverlaysBusySinceReal > now
		BedOverlaysBusySinceReal = 0.0
	EndIf
	If BedOverlaysBusy
		Float busyElapsed = now - BedOverlaysBusySinceReal
		If busyElapsed > BED_OVERLAY_BUSY_TIMEOUT_SECONDS
			Debug.Trace("PickmansWhisper: bed despawn busy watchdog — force clear after " + busyElapsed + "s busy")
			BedOverlaysBusy = False
			ClearBedCorpse(False)
			BedAnchor = None
			BedPresentedThisSleep = False
			SetBedGiftStatus("despawned (timer, busy watchdog)")
			Return
		EndIf
		; LooksMenu still in flight — retry shortly instead of yanking the actor.
		CancelTimer(TIMER_BED_DESPAWN)
		StartTimer(BED_DESPAWN_BUSY_RETRY_SECONDS, TIMER_BED_DESPAWN)
		Debug.Trace("PickmansWhisper: bed despawn hold | overlay apply in flight (" + busyElapsed + "s/" + BED_OVERLAY_BUSY_TIMEOUT_SECONDS + "s)")
		Return
	EndIf
	ClearBedCorpse(False)
	BedAnchor = None
	BedPresentedThisSleep = False
	SetBedGiftStatus("despawned (timer " + BED_DESPAWN_SECONDS + "s)")
EndFunction

Function SetBedGiftStatus(String reason)
	LastBedGiftStatus = reason
	PickmansWhisperMainQuestScript m = Main()
	If m
		m.OnBedGiftStatus(reason)
	EndIf
	Debug.Trace("PickmansWhisper: bed gift | " + reason)
EndFunction

Bool Function IsBedGiftEnabled()
	Bool on = True
	If MCM.IsInstalled()
		on = MCM.GetModSettingBool(MOD_NAME, "bBedGift:Voice")
	EndIf
	Return on
EndFunction

Bool Function IsBedGiftEverySleep()
	If MCM.IsInstalled()
		Return MCM.GetModSettingBool(MOD_NAME, "bBedGiftEverySleep:Debug")
	EndIf
	Return False
EndFunction

Bool Function BedGiftCooldownReady()
	If IsBedGiftEverySleep()
		Return True
	EndIf
	PickmansWhisperMainQuestScript m = Main()
	If !m
		Return False
	EndIf
	If !m.ModConfigAlias
		Return False
	EndIf
	Float cooldownDays = m.ModConfigAlias.GetBedGiftCooldownDays()
	If cooldownDays <= 0.0
		Return False
	EndIf
	Float now = Utility.GetCurrentGameTime()
	If LastBedGiftGameTime < 0.0
		Return True
	EndIf
	Return (now - LastBedGiftGameTime) >= cooldownDays
EndFunction

Bool Function HasLiveBedCorpse()
	If !BedCorpse
		Return False
	EndIf
	Return True
EndFunction

; Wake toast from ModConfig.txt → bedGiftWakeToast (files-only; empty = skip).
Function MaybeSpeakBedGiftWakeToast()
	PickmansWhisperMainQuestScript m = Main()
	If !m
		Return
	EndIf
	If !m.VoiceAlias || !m.VoiceAlias.IsVoiceEnabled()
		Return
	EndIf
	If !m.VoiceAlias.IsVoiceWeaponReady()
		Return
	EndIf
	If !m.ModConfigAlias
		Return
	EndIf
	String line = m.ModConfigAlias.GetBedGiftWakeToast()
	If !line || GardenOfEden.StrLength(line) < 1
		Return
	EndIf
	m.VoiceAlias.ShowVoiceToast(line)
	Debug.Trace("PickmansWhisper: bed gift wake toast | " + line)
EndFunction

Function StripBedCorpse(Actor corpse)
	If !corpse
		Return
	EndIf
	corpse.UnequipAll()
	corpse.RemoveAllItems(None, False)
EndFunction

Bool Function IsBedFurniture(ObjectReference akRef)
	If !akRef
		Return False
	EndIf
	Keyword bedKw = Game.GetFormFromFile(FID_KYWD_ANIM_FURN_BED, "Fallout4.esm") as Keyword
	If bedKw && akRef.HasKeyword(bedKw)
		Return True
	EndIf
	Keyword floorKw = Game.GetFormFromFile(FID_KYWD_ANIM_FURN_FLOOR_BED, "Fallout4.esm") as Keyword
	If floorKw && akRef.HasKeyword(floorKw)
		Return True
	EndIf
	PickmansWhisperMainQuestScript m = Main()
	String n = akRef.GetName()
	If m && n && (m.StrContains(n, "Bed") || m.StrContains(n, "Mattress") || m.StrContains(n, "Sleeping") || m.StrContains(n, "Cot"))
		Return True
	EndIf
	Return False
EndFunction

ObjectReference Function ResolveBedAnchor(ObjectReference akBed)
	If akBed
		Return akBed
	EndIf
	If BedAnchor
		Return BedAnchor
	EndIf
	Actor player = Game.GetPlayer()
	If !player
		Return None
	EndIf
	String[] types = new String[1]
	types[0] = "FURN"
	ObjectReference near = GardenOfEden3.FindClosestReferencesWithFormType(types, player, 320.0)
	If near && IsBedFurniture(near)
		Return near
	EndIf
	Return None
EndFunction

Function ParkWarmedBedCorpse(Actor corpse)
	Actor player = Game.GetPlayer()
	If !corpse || !player
		Return
	EndIf
	corpse.SetGhost(True)
	GardenOfEden3.DisableCollision(corpse, True)
	corpse.SetPosition(player.GetPositionX(), player.GetPositionY(), player.GetPositionZ() + BED_WARM_PARK_Z)
	If !corpse.IsDisabled()
		corpse.Disable(False)
	EndIf
EndFunction

Function SnapBedCorpseToAnchor(Actor corpse, ObjectReference akAnchor)
	If !corpse || !akAnchor
		Return
	EndIf
	Float ang = akAnchor.GetAngleZ()
	Float lx = BED_SPAWN_OFFSET_X
	Float ly = BED_SPAWN_OFFSET_Y
	Float wx = akAnchor.GetPositionX() + (lx * Math.Cos(ang)) + (ly * Math.Sin(ang))
	Float wy = akAnchor.GetPositionY() + (lx * (-Math.Sin(ang))) + (ly * Math.Cos(ang))
	Float wz = akAnchor.GetPositionZ() + BED_SPAWN_OFFSET_Z
	GardenOfEden3.DisableCollision(corpse, True)
	corpse.SetAngle(0.0, 0.0, ang)
	corpse.SetPosition(wx, wy, wz)
	corpse.ForceAddRagdollToWorld()
	corpse.ApplyHavokImpulse(0.0, 0.0, -1.0, 2.0)
	GardenOfEden3.DisableCollision(corpse, False)
EndFunction

Bool Function IsBedGiftCorpse(Actor ak)
	Return ak && ak == BedCorpse
EndFunction

; Some ActorBases are Protected — KillSilent() with no killer can leave them alive.
; Pass the player as killer; never clear Protected on the shared ActorBase.
; Suppress knife-kill credit — hallucination must not satiate hunger.
Function KillBedCorpse(Actor corpse)
	If !corpse || corpse.IsDead()
		Return
	EndIf
	PickmansWhisperMainQuestScript m = Main()
	If m
		m.SetKnifeKillCreditSuppressed(True)
	EndIf
	Actor player = Game.GetPlayer()
	If player
		corpse.KillSilent(player)
	Else
		corpse.KillSilent()
	EndIf
	If m
		m.SetKnifeKillCreditSuppressed(False)
		m.NoteBackgroundDead(corpse.GetFormID())
	EndIf
EndFunction

; Enable leaves the actor without 3D for a beat — SnapIntoInteraction then hard-errors.
; Poll Is3DLoaded (real FO4 native) via the re-arming TIMER_BED_POSE one-shot — never
; Utility.Wait here; that would block the SleepStop wake stack for up to ~2.5s.
Function PoseBedCorpseInFurniture(Actor corpse, ObjectReference akBed)
	If !corpse || !akBed
		FinishBedPresentTail()
		Return
	EndIf
	BedPoseAnchor = akBed
	BedPoseTriesRemaining = BED_POSE_MAX_TRIES
	BedPoseAwaitingSettle = False
	If corpse.IsDisabled()
		corpse.Enable(False)
	EndIf
	If corpse.Is3DLoaded()
		DoBedPoseSnap()
	Else
		CancelTimer(TIMER_BED_POSE)
		StartTimer(BED_POSE_POLL_SECONDS, TIMER_BED_POSE)
	EndIf
EndFunction

; Fires every BED_POSE_POLL_SECONDS while waiting for 3D, or once after the settle delay.
Function AdvanceBedPoseSequence()
	If BedPoseAwaitingSettle
		FinishBedPoseSnap()
		Return
	EndIf
	If !HasLiveBedCorpse()
		; Corpse cleared mid-sequence (interrupted sleep / despawn race) — abort quietly.
		BedPoseTriesRemaining = -1
		Return
	EndIf
	If BedCorpse.Is3DLoaded()
		DoBedPoseSnap()
		Return
	EndIf
	BedPoseTriesRemaining -= 1
	If BedPoseTriesRemaining <= 0
		RagdollBedPoseFallback("actor 3D not loaded")
		Return
	EndIf
	CancelTimer(TIMER_BED_POSE)
	StartTimer(BED_POSE_POLL_SECONDS, TIMER_BED_POSE)
EndFunction

Function DoBedPoseSnap()
	If !HasLiveBedCorpse()
		BedPoseTriesRemaining = -1
		Return
	EndIf
	BedCorpse.SetGhost(False)
	StripBedCorpse(BedCorpse)
	Bool snapped = BedCorpse.SnapIntoInteraction(BedPoseAnchor)
	If !snapped
		RagdollBedPoseFallback("SnapIntoInteraction failed")
		Return
	EndIf
	BedPoseAwaitingSettle = True
	CancelTimer(TIMER_BED_POSE)
	StartTimer(BED_POSE_SETTLE_SECONDS, TIMER_BED_POSE)
EndFunction

; Settle delay elapsed — safe to KillSilent without a mid-animation snap glitch.
Function FinishBedPoseSnap()
	BedPoseAwaitingSettle = False
	BedPoseTriesRemaining = -1
	If HasLiveBedCorpse()
		KillBedCorpse(BedCorpse)
		StripBedCorpse(BedCorpse)
	EndIf
	SetBedGiftStatus("posed via SnapIntoInteraction + KillSilent")
	FinishBedPresentTail()
EndFunction

Function RagdollBedPoseFallback(String reason)
	BedPoseAwaitingSettle = False
	BedPoseTriesRemaining = -1
	Debug.Notification("Pickman's Whisper: bed SnapIntoInteraction FAILED — ragdoll fallback")
	Debug.Trace("PickmansWhisper: ERROR bed pose fallback (" + reason + ") — ragdoll fallback")
	If HasLiveBedCorpse()
		KillBedCorpse(BedCorpse)
		StripBedCorpse(BedCorpse)
		SnapBedCorpseToAnchor(BedCorpse, BedPoseAnchor)
	EndIf
	SetBedGiftStatus("ERROR: " + reason + " — ragdoll fallback")
	FinishBedPresentTail()
EndFunction

Bool Function CreateBedCorpseAt(ObjectReference akAnchor, Bool abParkUnderPlayer)
	If !akAnchor
		Return False
	EndIf
	If BedSpawnBusy
		SetBedGiftStatus("skip: spawn already in progress")
		Return False
	EndIf
	If HasLiveBedCorpse()
		SetBedGiftStatus("skip: corpse already present")
		Return False
	EndIf
	Actor player = Game.GetPlayer()
	If !player
		Return False
	EndIf
	Form spawnForm = Game.GetFormFromFile(FID_BED_SPAWN_NPC, "Fallout4.esm")
	If !spawnForm
		SetBedGiftStatus("ERROR: DiamondCityResidentF01NoodleMarket missing")
		Debug.Notification("Pickman's Whisper: bed gift spawn form missing (DiamondCityResidentF01NoodleMarket)")
		Return False
	EndIf
	BedSpawnBusy = True
	ObjectReference placed = akAnchor.PlaceAtMe(spawnForm, 1, False, False)
	Actor corpse = placed as Actor
	If !corpse
		If placed
			placed.Delete()
		EndIf
		BedSpawnBusy = False
		SetBedGiftStatus("ERROR: PlaceAtMe failed")
		Debug.Notification("Pickman's Whisper: bed gift PlaceAtMe failed")
		Return False
	EndIf
	; Assign before park/pose so kill-credit ignore sees this body.
	BedCorpse = corpse
	BedOverlaysApplied = False
	; Never Pose/Wait here — SleepStart must stay snappy. Present poses on wake.
	If abParkUnderPlayer
		ParkWarmedBedCorpse(corpse)
		BedCorpseWarmed = True
	Else
		SnapBedCorpseToAnchor(corpse, akAnchor)
		corpse.SetGhost(True)
		If !corpse.IsDisabled()
			corpse.Disable(False)
		EndIf
		BedCorpseWarmed = False
	EndIf
	BedSpawnBusy = False
	Return True
EndFunction

Bool Function TrySpawnBedCorpse(ObjectReference akAnchor, Bool abForce = False)
	If !akAnchor
		SetBedGiftStatus("skip: no bed anchor")
		Return False
	EndIf
	If BedSpawnBusy || HasLiveBedCorpse()
		SetBedGiftStatus("skip: corpse already present")
		Return False
	EndIf
	If !abForce
		PickmansWhisperMainQuestScript m = Main()
		If !m || !m.BondStarted
			SetBedGiftStatus("skip: not bonded")
			Return False
		EndIf
		If !m.IsBladeEquipped()
			SetBedGiftStatus("skip: Pickman's Blade not equipped")
			Return False
		EndIf
		If !IsBedGiftEnabled()
			SetBedGiftStatus("skip: MCM bed gift off")
			Return False
		EndIf
		If !BedGiftCooldownReady()
			SetBedGiftStatus("skip: cooldown (~12 game hours)")
			Return False
		EndIf
	EndIf
	If !CreateBedCorpseAt(akAnchor, False)
		Return False
	EndIf
	BedAnchor = akAnchor
	; Arm LooksMenu oneshot — never sync-apply on sleep stack.
	KickBedOverlayOnesHot(BED_OVERLAY_DELAY)
	If abForce
		SetBedGiftStatus("spawned (debug force); decay armed")
	Else
		SetBedGiftStatus("spawned (sleep start); decay armed")
	EndIf
	Return True
EndFunction

Function ClearBedCorpse(Bool abStampCooldown = False)
	CancelTimer(TIMER_BED_OVERLAYS)
	CancelTimer(TIMER_BED_POSE)
	CancelTimer(TIMER_BED_DESPAWN)
	BedPoseTriesRemaining = -1
	BedPoseAwaitingSettle = False
	BedPoseAnchor = None
	BedCorpseWarmed = False
	BedSpawnBusy = False
	BedOverlaysBusy = False
	BedOverlaysApplied = False
	If BedCorpse
		Actor c = BedCorpse
		BedCorpse = None
		If c
			KillBedCorpse(c)
			If !c.IsDisabled()
				c.Disable(False)
			EndIf
			c.Delete()
		EndIf
		Debug.Trace("PickmansWhisper: bed corpse cleared")
	EndIf
	BedCorpse = None
	If abStampCooldown
		LastBedGiftGameTime = Utility.GetCurrentGameTime()
	EndIf
EndFunction

Function PresentBedCorpseOnWake()
	If BedPresentedThisSleep
		Return
	EndIf
	If !HasLiveBedCorpse()
		Return
	EndIf
	BedPresentedThisSleep = True
	BedWakeHandledThisSleep = True
	BedCorpseWarmed = False
	; Cancel pending pre-present paint; FinishBedPresentTail re-arms after pose.
	CancelTimer(TIMER_BED_OVERLAYS)
	If BedCorpse.IsDisabled()
		BedCorpse.Enable(False)
	EndIf
	If BedAnchor && !BedCorpse.IsDead()
		; Async — PoseBedCorpseInFurniture finishes via FinishBedPresentTail on the
		; TIMER_BED_POSE one-shot (never blocks this wake stack).
		PoseBedCorpseInFurniture(BedCorpse, BedAnchor)
		Return
	ElseIf BedAnchor && BedCorpse.IsDead()
		; Corpse was already dead on arrival — most likely a stale save load resumed a
		; Present that already ran (pose/ragdoll) in an earlier session. No pose attempt
		; happens this cycle; surface that plainly instead of silently skipping to strip.
		Debug.Trace("PickmansWhisper: ERROR bed present skip — corpse already dead on arrival (stale reload?)")
		StripBedCorpse(BedCorpse)
	ElseIf !BedCorpse.IsDead()
		KillBedCorpse(BedCorpse)
		StripBedCorpse(BedCorpse)
	Else
		StripBedCorpse(BedCorpse)
	EndIf
	FinishBedPresentTail()
EndFunction

; Common tail for both the async-posed path (TIMER_BED_POSE finish/fallback) and the
; synchronous no-pose-needed paths (dead-on-arrival / no anchor).
Function FinishBedPresentTail()
	; Arm despawn FIRST, before anything else in this function. Under heavy VM load a
	; function can stall partway through (Papyrus's per-frame budget defers the rest,
	; and the deferred continuation can starve for minutes until something resets the
	; VM's stack queue, e.g. a save load) — seen in logs as overlay-kick tracing fine
	; but despawn never arming. Whatever else in this tail stalls, despawn must not.
	ArmBedDespawnTimer()
	LastBedGiftGameTime = Utility.GetCurrentGameTime()
	; Pose/Kill/Strip can wipe LooksMenu — do not trust pre-present paint.
	BedOverlaysApplied = False
	; Never sync-apply here (stalls SleepStop). One-shot timer owns LooksMenu.
	; Slightly after pose settle / 3D wait so LooksMenu is not racing Enable.
	KickBedOverlayOnesHot(0.35)
	MaybeSpeakBedGiftWakeToast()
	SetBedGiftStatus("presented; despawn in " + BED_DESPAWN_SECONDS + "s | " + LastBedGiftStatus)
EndFunction

; Slice H — DeathMarks + Black Putrefaction. Prefer while disabled (pre-Enable).
; Runs from TIMER_BED_OVERLAYS OnTimer only — never on SleepStart/Stop stack.
Function MaybeApplyBedGiftDecayOverlays()
	If !BedCorpse || BedOverlaysApplied || BedOverlaysBusy
		Return
	EndIf
	PickmansWhisperCorpseDecayScript decay = (Self as Quest) as PickmansWhisperCorpseDecayScript
	If !decay
		Debug.Trace("PickmansWhisper: ERROR CorpseDecay script missing — bed overlays skipped")
		SetBedGiftStatus("ERROR: CorpseDecay script missing — overlays skipped")
		Return
	EndIf
	BedOverlaysBusy = True
	BedOverlaysBusySinceReal = Utility.GetCurrentRealTime()
	; LooksMenu Prepare may Enable — restore park/disable so the player never sees a fresh body.
	Bool keepParked = BedCorpseWarmed && !BedPresentedThisSleep
	Bool keepDisabled = BedCorpse.IsDisabled() && !BedPresentedThisSleep
	decay.ApplyBedGiftDecayOverlays(BedCorpse)
	BedOverlaysApplied = True
	BedOverlaysBusy = False
	If keepParked
		ParkWarmedBedCorpse(BedCorpse)
	ElseIf keepDisabled && BedCorpse && !BedCorpse.IsDisabled()
		BedCorpse.Disable(False)
	EndIf
	SetBedGiftStatus("decay applied | " + decay.LastCorpseDecayStatus)
	Debug.Trace("PickmansWhisper: bed gift overlays done | " + decay.LastCorpseDecayStatus)
EndFunction

Function HandlePlayerSleepStart(Float afSleepStartTime, Float afDesiredSleepEndTime, ObjectReference akBed)
	Debug.Notification("HandlePlayerSleepStart")
	Debug.Trace("HandlePlayerSleepStart")

	BedPresentedThisSleep = False
	BedWakeHandledThisSleep = False
	ObjectReference anchor = ResolveBedAnchor(akBed)
	If anchor
		BedAnchor = anchor
		If !HasLiveBedCorpse()
			; Sole gameplay spawn — place+disable only; no Pose/Wait/LooksMenu here.
			If TrySpawnBedCorpse(anchor, False)
				Debug.Trace("PickmansWhisper: bed gift spawned at SleepStart")
			EndIf
		ElseIf !BedOverlaysApplied
			KickBedOverlayOnesHot(BED_OVERLAY_DELAY)
		EndIf
		If HasLiveBedCorpse()
			SetBedGiftStatus("sleep start — bed saved; overlays=" + BedOverlaysApplied + " | " + LastBedGiftStatus)
		Else
			SetBedGiftStatus("sleep start — no body | " + LastBedGiftStatus)
		EndIf
	Else
		SetBedGiftStatus("sleep start: no bed anchor")
	EndIf
EndFunction

Function HandlePlayerSleepStop(Bool abInterrupted, ObjectReference akBed)
	Debug.Notification("HandlePlayerSleepStop")
	Debug.Trace("HandlePlayerSleepStop")

	If abInterrupted
		If BedPresentedThisSleep
			ClearBedCorpse(False)
		EndIf
		BedAnchor = None
		BedPresentedThisSleep = False
		BedWakeHandledThisSleep = False
		SetBedGiftStatus("sleep interrupted")
		Return
	EndIf
	ObjectReference anchor = ResolveBedAnchor(akBed)
	If anchor
		BedAnchor = anchor
	EndIf
	If HasLiveBedCorpse()
		PresentBedCorpseOnWake()
		Return
	EndIf
	; FO4 can fire a late second SleepStop after Present/despawn — don't clobber status.
	If BedWakeHandledThisSleep
		Debug.Trace("PickmansWhisper: bed gift | wake stop ignored (already handled this sleep)")
		Return
	EndIf
	SetBedGiftStatus("wake: no body — skip")
EndFunction

Function DebugForceBedGift()
	Actor player = Game.GetPlayer()
	If !player
		DiagNotify("Pickman's Whisper\n\nNo player.")
		Return
	EndIf
	BedPresentedThisSleep = False
	ClearBedCorpse(False)
	ObjectReference anchor = ResolveBedAnchor(None)
	If !anchor
		anchor = player
	EndIf
	BedAnchor = anchor
	If !TrySpawnBedCorpse(anchor, True)
		DiagNotify("Pickman's Whisper\n\nForce bed gift failed.\n" + LastBedGiftStatus)
		Return
	EndIf
	; PresentBedCorpseOnWake poses asynchronously (TIMER_BED_POSE) — do not read
	; LastBedGiftStatus for a final result here; ToastDebug reports it when it lands.
	PresentBedCorpseOnWake()
	DiagNotify("Pickman's Whisper\n\nBed gift forced.\nPosing... watch MCM Debug / Papyrus.0.log for the outcome.")
EndFunction

Function DebugClearBedGift()
	ClearBedCorpse(False)
	BedAnchor = None
	BedPresentedThisSleep = False
	SetBedGiftStatus("cleared (debug)")
	DiagNotify("Pickman's Whisper\n\nBed gift cleared.\n" + LastBedGiftStatus)
EndFunction

; Former Debug.MessageBox — no pause; full text in Papyrus.0.log (filter PickmansWhisper).
Function DiagNotify(String msg)
	If msg == ""
		Return
	EndIf
	Debug.Trace("PickmansWhisper: DIAG " + msg)
	Debug.Notification(msg)
EndFunction