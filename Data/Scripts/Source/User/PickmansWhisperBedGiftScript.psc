Scriptname PickmansWhisperBedGiftScript extends Quest
{Slice G — bed corpse hallucination. Attached to PickmansWhisperMain alongside MainQuestScript.}

; Sleep events register on PlayerAlias; alias → Main façades → this script.
; ONE PlaceAtMe site for gameplay: MaybeWarmBedGiftBody (KillerScan NoWait while awake).
; SleepStart/Stop never spawn — Start saves bed, Stop Presents or skips. No retries.
; Deadlines checked on KillerScan tick — no feature StartTimer (Killer Orchestrator).

Int FID_BED_SPAWN_NPC = 0x00004DEC ; Fallout4.esm DiamondCityResidentF01NoodleMarket (unnamed Resident)
Int FID_KYWD_ANIM_FURN_BED = 0x000BC262 ; AnimFurnBedAnims
Int FID_KYWD_ANIM_FURN_FLOOR_BED = 0x0003ADA2 ; AnimFurnFloorBedAnims
String MOD_NAME = "PickmansWhisper"

Actor BedCorpse = None
ObjectReference BedAnchor = None
Bool BedPresentedThisSleep = False
Bool BedCorpseWarmed = False
Bool BedSpawnBusy = False
Bool BedOverlaysApplied = False ; True once Black Putrefaction path ran (pre-Enable when possible)
Float LastBedGiftGameTime = -999.0
Float BED_DESPAWN_SECONDS = 6.0
Float BED_OVERLAY_DELAY = 0.25 ; real-time after PlaceAtMe; keeps KillerScan snappy
Float BedDespawnAtReal = 0.0
Float BedOverlaysAtReal = 0.0
Float BED_SPAWN_OFFSET_X = 0.0
Float BED_SPAWN_OFFSET_Y = 8.0
Float BED_SPAWN_OFFSET_Z = 36.0
Float BED_WARM_PARK_Z = -2000.0
String Property LastBedGiftStatus = "" Auto

PickmansWhisperMainQuestScript Function Main()
	; Caprica forbids Self-as-sibling; Quest intermediate is the FO4 co-script cast.
	Return (Self as Quest) as PickmansWhisperMainQuestScript
EndFunction

; KillerScan cadence — fire overdue bed deadlines (replaces StartTimer 8/9).
Function OnKillerScanDeadlines()
	Float now = Utility.GetCurrentRealTime()
	If BedOverlaysAtReal > 0.0 && now >= BedOverlaysAtReal
		BedOverlaysAtReal = 0.0
		If HasLiveBedCorpse()
			MaybeApplyBedGiftDecayOverlays()
		Else
			Debug.Trace("PickmansWhisper: bed overlay deadline skip | no live corpse")
		EndIf
	EndIf
	If BedDespawnAtReal > 0.0 && now >= BedDespawnAtReal
		BedDespawnAtReal = 0.0
		ClearBedCorpse(False)
		BedAnchor = None
		BedPresentedThisSleep = False
		SetBedGiftStatus("despawned (KillerScan deadline)")
	EndIf
EndFunction

Function ScheduleBedGiftDecayOverlays()
	BedOverlaysAtReal = Utility.GetCurrentRealTime() + BED_OVERLAY_DELAY
EndFunction

Function SetBedGiftStatus(String reason)
	LastBedGiftStatus = reason
	PickmansWhisperMainQuestScript m = Main()
	If m
		m.LastBedGiftStatus = reason
		m.ToastDebug("PW bed: " + reason)
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
	Float cooldownDays = m.GetBedGiftCooldownDays()
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
	If !m.IsVoiceEnabled()
		Return
	EndIf
	If !m.IsVoiceWeaponReady()
		Return
	EndIf
	String line = m.GetBedGiftWakeToast()
	If !line || GardenOfEden.StrLength(line) < 1
		Return
	EndIf
	m.ShowVoiceToast(line)
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

Bool Function PoseBedCorpseInFurniture(Actor corpse, ObjectReference akBed)
	If !corpse || !akBed
		Return False
	EndIf
	If corpse.IsDisabled()
		corpse.Enable(False)
	EndIf
	corpse.SetGhost(False)
	StripBedCorpse(corpse)
	Bool snapped = corpse.SnapIntoInteraction(akBed)
	If snapped
		; Utility.Wait freezes while MCM is open — skip settle delay in menus.
		If !Utility.IsInMenuMode()
			Utility.Wait(0.5)
		EndIf
		KillBedCorpse(corpse)
		StripBedCorpse(corpse)
		SetBedGiftStatus("posed via SnapIntoInteraction + KillSilent")
		Return True
	EndIf
	Debug.Notification("Pickman's Whisper: bed SnapIntoInteraction FAILED — ragdoll fallback")
	Debug.Trace("PickmansWhisper: ERROR bed SnapIntoInteraction failed — ragdoll fallback")
	KillBedCorpse(corpse)
	StripBedCorpse(corpse)
	SnapBedCorpseToAnchor(corpse, akBed)
	SetBedGiftStatus("ERROR: SnapIntoInteraction failed — ragdoll fallback")
	Return False
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
	; Assign before park/pose so killscan never tracks or satiates on this body.
	BedCorpse = corpse
	BedOverlaysApplied = False
	If abParkUnderPlayer
		ParkWarmedBedCorpse(corpse)
	Else
		PoseBedCorpseInFurniture(corpse, akAnchor)
		If !corpse.IsDisabled()
			corpse.Disable(False)
		EndIf
	EndIf
	BedCorpseWarmed = True
	BedSpawnBusy = False
	Return True
EndFunction

Function MaybeWarmBedGiftBody()
	If BedSpawnBusy || HasLiveBedCorpse() || BedPresentedThisSleep
		Return
	EndIf
	PickmansWhisperMainQuestScript m = Main()
	If !m || !m.BondStarted || !IsBedGiftEnabled() || !BedGiftCooldownReady()
		Return
	EndIf
	Actor player = Game.GetPlayer()
	If !player
		Return
	EndIf
	If CreateBedCorpseAt(player, True)
		; Decay while parked/disabled so Enable on wake is already Black Putrefaction.
		ScheduleBedGiftDecayOverlays()
		SetBedGiftStatus("warmed (awaiting sleep); decay scheduled")
		Debug.Trace("PickmansWhisper: bed gift body pre-warmed while awake")
	EndIf
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
	; Disabled after pose — schedule decay before Present Enable when possible.
	ScheduleBedGiftDecayOverlays()
	SetBedGiftStatus("spawned (debug force); decay scheduled")
	Return True
EndFunction

Function ClearBedCorpse(Bool abStampCooldown = False)
	BedDespawnAtReal = 0.0
	BedOverlaysAtReal = 0.0
	BedCorpseWarmed = False
	BedSpawnBusy = False
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
	BedCorpseWarmed = False
	; Prefer decay already applied while disabled (warm / SleepStart). Clear pending overlay deadline.
	BedOverlaysAtReal = 0.0
	If BedCorpse.IsDisabled()
		BedCorpse.Enable(False)
	EndIf
	If BedAnchor && !BedCorpse.IsDead()
		PoseBedCorpseInFurniture(BedCorpse, BedAnchor)
	ElseIf BedAnchor && BedCorpse.IsDead()
		StripBedCorpse(BedCorpse)
	ElseIf !BedCorpse.IsDead()
		KillBedCorpse(BedCorpse)
		StripBedCorpse(BedCorpse)
	Else
		StripBedCorpse(BedCorpse)
	EndIf
	LastBedGiftGameTime = Utility.GetCurrentGameTime()
	; Fallback only — never sync-apply here (stalls SleepStop / MCM Force).
	If !BedOverlaysApplied
		ScheduleBedGiftDecayOverlays()
	EndIf
	MaybeSpeakBedGiftWakeToast()
	BedDespawnAtReal = Utility.GetCurrentRealTime() + BED_DESPAWN_SECONDS
	SetBedGiftStatus("presented; despawn deadline " + BED_DESPAWN_SECONDS + "s | " + LastBedGiftStatus)
EndFunction

; Slice H — DeathMarks + Black Putrefaction. Prefer while disabled (pre-Enable).
Function MaybeApplyBedGiftDecayOverlays()
	If !BedCorpse || BedOverlaysApplied
		Return
	EndIf
	PickmansWhisperCorpseDecayScript decay = (Self as Quest) as PickmansWhisperCorpseDecayScript
	If !decay
		Debug.Trace("PickmansWhisper: ERROR CorpseDecay script missing — bed overlays skipped")
		Return
	EndIf
	; LooksMenu Prepare may Enable — restore park/disable so the player never sees a fresh body.
	Bool keepParked = BedCorpseWarmed && !BedPresentedThisSleep
	Bool keepDisabled = BedCorpse.IsDisabled() && !BedPresentedThisSleep
	decay.ApplyBedGiftDecayOverlays(BedCorpse)
	BedOverlaysApplied = True
	If keepParked
		ParkWarmedBedCorpse(BedCorpse)
	ElseIf keepDisabled && BedCorpse && !BedCorpse.IsDisabled()
		BedCorpse.Disable(False)
	EndIf
	SetBedGiftStatus("decay applied pre-present | " + decay.LastCorpseDecayStatus)
EndFunction

Function HandlePlayerSleepStart(Float afSleepStartTime, Float afDesiredSleepEndTime, ObjectReference akBed)
	BedPresentedThisSleep = False
	ObjectReference anchor = ResolveBedAnchor(akBed)
	If anchor
		BedAnchor = anchor
		If HasLiveBedCorpse()
			; Sleep fade — finish decay while still disabled if warm timer has not fired yet.
			If !BedOverlaysApplied
				BedOverlaysAtReal = 0.0
				MaybeApplyBedGiftDecayOverlays()
			EndIf
			SetBedGiftStatus("sleep start — bed saved; overlays=" + BedOverlaysApplied + " | " + LastBedGiftStatus)
		Else
			SetBedGiftStatus("sleep start — bed saved; no warmed body")
		EndIf
	Else
		SetBedGiftStatus("sleep start: no bed anchor")
	EndIf
EndFunction

Function HandlePlayerSleepStop(Bool abInterrupted, ObjectReference akBed)
	If abInterrupted
		If BedPresentedThisSleep
			ClearBedCorpse(False)
		EndIf
		BedAnchor = None
		BedPresentedThisSleep = False
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
	SetBedGiftStatus("wake: no warmed body — skip")
EndFunction

Function DebugForceBedGift()
	Actor player = Game.GetPlayer()
	If !player
		Debug.MessageBox("Pickman's Whisper\n\nNo player.")
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
		Debug.MessageBox("Pickman's Whisper\n\nForce bed gift failed.\n" + LastBedGiftStatus)
		Return
	EndIf
	PresentBedCorpseOnWake()
	Debug.MessageBox("Pickman's Whisper\n\nBed gift forced.\n" + LastBedGiftStatus + "\nDespawns on timer.")
EndFunction

Function DebugClearBedGift()
	ClearBedCorpse(False)
	BedAnchor = None
	BedPresentedThisSleep = False
	SetBedGiftStatus("cleared (debug)")
	Debug.MessageBox("Pickman's Whisper\n\nBed gift cleared.\n" + LastBedGiftStatus)
EndFunction
