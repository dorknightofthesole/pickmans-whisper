Scriptname PickmansWhisperBedGiftScript extends Quest
{Slice G — bed corpse hallucination. Attached to PickmansWhisperMain alongside MainQuestScript.}

; Sleep events register on PlayerAlias; alias → Main façades → this script.
; ONE PlaceAtMe site for gameplay: MaybeWarmBedGiftBody (killscan while awake).
; SleepStart/Stop never spawn — Start saves bed, Stop Presents or skips. No retries.

Int TIMER_BED_DESPAWN = 8
Int FID_BED_SPAWN_LVLN = 0x000D39F5 ; Fallout4.esm LCharRaiderFemale
Int FID_KYWD_ANIM_FURN_BED = 0x000BC262 ; AnimFurnBedAnims
Int FID_KYWD_ANIM_FURN_FLOOR_BED = 0x0003ADA2 ; AnimFurnFloorBedAnims
String MOD_NAME = "PickmansWhisper"

Actor BedCorpse = None
ObjectReference BedAnchor = None
Bool BedPresentedThisSleep = False
Bool BedCorpseWarmed = False
Bool BedSpawnBusy = False
Float LastBedGiftGameTime = -999.0
Float BED_DESPAWN_SECONDS = 6.0
Float BED_SPAWN_OFFSET_X = 0.0
Float BED_SPAWN_OFFSET_Y = 8.0
Float BED_SPAWN_OFFSET_Z = 36.0
Float BED_WARM_PARK_Z = -2000.0
String Property LastBedGiftStatus = "" Auto

PickmansWhisperMainQuestScript Function Main()
	; Caprica forbids Self-as-sibling; Quest intermediate is the FO4 co-script cast.
	Return (Self as Quest) as PickmansWhisperMainQuestScript
EndFunction

Event OnTimer(Int aiTimerID)
	If aiTimerID == TIMER_BED_DESPAWN
		ClearBedCorpse(False)
		BedAnchor = None
		BedPresentedThisSleep = False
		SetBedGiftStatus("despawned (timer)")
	EndIf
EndEvent

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
		Utility.Wait(0.5)
		corpse.KillSilent()
		StripBedCorpse(corpse)
		SetBedGiftStatus("posed via SnapIntoInteraction + KillSilent")
		Return True
	EndIf
	Debug.Notification("Pickman's Whisper: bed SnapIntoInteraction FAILED — ragdoll fallback")
	Debug.Trace("PickmansWhisper: ERROR bed SnapIntoInteraction failed — ragdoll fallback")
	corpse.KillSilent()
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
	Form spawnForm = Game.GetFormFromFile(FID_BED_SPAWN_LVLN, "Fallout4.esm")
	If !spawnForm
		SetBedGiftStatus("ERROR: LCharRaiderFemale missing")
		Debug.Notification("Pickman's Whisper: bed gift spawn form missing (LCharRaiderFemale)")
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
	If abParkUnderPlayer
		ParkWarmedBedCorpse(corpse)
	Else
		PoseBedCorpseInFurniture(corpse, akAnchor)
		If !corpse.IsDisabled()
			corpse.Disable(False)
		EndIf
	EndIf
	BedCorpse = corpse
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
		SetBedGiftStatus("warmed (awaiting sleep)")
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
	SetBedGiftStatus("spawned (debug force)")
	Return True
EndFunction

Function ClearBedCorpse(Bool abStampCooldown = False)
	CancelTimer(TIMER_BED_DESPAWN)
	BedCorpseWarmed = False
	BedSpawnBusy = False
	If BedCorpse
		Actor c = BedCorpse
		BedCorpse = None
		If c
			If !c.IsDead()
				c.KillSilent()
			EndIf
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
	If BedCorpse.IsDisabled()
		BedCorpse.Enable(False)
	EndIf
	If BedAnchor && !BedCorpse.IsDead()
		PoseBedCorpseInFurniture(BedCorpse, BedAnchor)
	ElseIf BedAnchor && BedCorpse.IsDead()
		StripBedCorpse(BedCorpse)
	ElseIf !BedCorpse.IsDead()
		BedCorpse.KillSilent()
		StripBedCorpse(BedCorpse)
	Else
		StripBedCorpse(BedCorpse)
	EndIf
	LastBedGiftGameTime = Utility.GetCurrentGameTime()
	MaybeSpeakBedGiftWakeToast()
	CancelTimer(TIMER_BED_DESPAWN)
	StartTimer(BED_DESPAWN_SECONDS, TIMER_BED_DESPAWN)
	SetBedGiftStatus("presented; despawn timer " + BED_DESPAWN_SECONDS + "s | " + LastBedGiftStatus)
EndFunction

Function HandlePlayerSleepStart(Float afSleepStartTime, Float afDesiredSleepEndTime, ObjectReference akBed)
	BedPresentedThisSleep = False
	ObjectReference anchor = ResolveBedAnchor(akBed)
	If anchor
		BedAnchor = anchor
		If HasLiveBedCorpse()
			SetBedGiftStatus("sleep start — bed saved; warmed body ready")
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
