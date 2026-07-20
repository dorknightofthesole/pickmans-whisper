Scriptname PickmansWhisperDecayWoundLabScript extends Quest
{Slice H P0.1/P0.2 — debug wound + Porcupine skin + face lab. Sticky bed corpse.}

; Spawn = copy of BedGift DebugForceBedGift / CreateBedCorpseAt / PresentBedCorpseOnWake with only:
;   - button trigger (not sleep / not every-sleep setting / not bond-cooldown gates)
;   - LabCorpse reference (not BedCorpse)
;   - no 6s despawn timer — Clear wound lab corpse only
; Soft apply via CorpseDecayScript (banks stack). Does NOT share BedCorpse.

Int FID_BED_SPAWN_NPC = 0x00004DEC ; Fallout4.esm DiamondCityResidentF01NoodleMarket
Int FID_KYWD_ANIM_FURN_BED = 0x000BC262 ; AnimFurnBedAnims
Int FID_KYWD_ANIM_FURN_FLOOR_BED = 0x0003ADA2 ; AnimFurnFloorBedAnims
String MOD_NAME = "PickmansWhisper"
String WOUND_FILE = "DecayWoundOverlays.txt"
String SKIN_FILE = "DecaySkinOverlays.txt"
String FACE_FILE = "DecayFaceOverlays.txt"
String CONFIG_PATH = ".\\Data\\PickmansWhisper\\config\\"
Float BED_SPAWN_OFFSET_X = 0.0
Float BED_SPAWN_OFFSET_Y = 8.0
Float BED_SPAWN_OFFSET_Z = 36.0

Actor LabCorpse = None
ObjectReference LabAnchor = None
Bool LabSpawnBusy = False
String[] LabWoundTemplates
Int LabWoundTemplateCount = 0
Bool LabWoundBankLoaded = False
String[] LabSkinTemplates
Int LabSkinTemplateCount = 0
Bool LabSkinBankLoaded = False
String[] LabFaceTemplates
Int LabFaceTemplateCount = 0
Bool LabFaceBankLoaded = False
String Property LastWoundLabStatus = "" Auto

PickmansWhisperMainQuestScript Function Main()
	; Caprica forbids Self-as-sibling; Quest intermediate is the FO4 co-script cast.
	Return (Self as Quest) as PickmansWhisperMainQuestScript
EndFunction

PickmansWhisperCorpseDecayScript Function CorpseDecay()
	Return (Self as Quest) as PickmansWhisperCorpseDecayScript
EndFunction

Function SetWoundLabStatus(String reason)
	LastWoundLabStatus = reason
	PickmansWhisperMainQuestScript m = Main()
	If m
		m.LastWoundLabStatus = reason
	EndIf
	; Status is Trace + MCM string only — overlay Apply must not spam the HUD.
	Debug.Trace("PickmansWhisper: wound lab | " + reason)
EndFunction

Bool Function EnsureLabWoundBank()
	If LabWoundBankLoaded && LabWoundTemplateCount > 0
		Return True
	EndIf
	PickmansWhisperMainQuestScript m = Main()
	If !m
		SetWoundLabStatus("ERROR: Main script missing — cannot load " + WOUND_FILE)
		Return False
	EndIf
	LabWoundTemplates = new String[64]
	LabWoundTemplateCount = m.LoadStageBankAt(WOUND_FILE, LabWoundTemplates, CONFIG_PATH)
	LabWoundBankLoaded = True
	If LabWoundTemplateCount <= 0
		SetWoundLabStatus("ERROR: " + WOUND_FILE + " — " + m.GetLastStageLoadStatus())
		Debug.Notification("Pickman's Whisper: " + WOUND_FILE + " missing or empty")
		Return False
	EndIf
	Return True
EndFunction

Bool Function EnsureLabSkinBank()
	If LabSkinBankLoaded && LabSkinTemplateCount > 0
		Return True
	EndIf
	PickmansWhisperMainQuestScript m = Main()
	If !m
		SetWoundLabStatus("ERROR: Main script missing — cannot load " + SKIN_FILE)
		Return False
	EndIf
	LabSkinTemplates = new String[64]
	LabSkinTemplateCount = m.LoadStageBankAt(SKIN_FILE, LabSkinTemplates, CONFIG_PATH)
	LabSkinBankLoaded = True
	If LabSkinTemplateCount <= 0
		SetWoundLabStatus("ERROR: " + SKIN_FILE + " — " + m.GetLastStageLoadStatus())
		Debug.Notification("Pickman's Whisper: " + SKIN_FILE + " missing or empty")
		Return False
	EndIf
	Return True
EndFunction

Bool Function EnsureLabFaceBank()
	If LabFaceBankLoaded && LabFaceTemplateCount > 0
		Return True
	EndIf
	PickmansWhisperMainQuestScript m = Main()
	If !m
		SetWoundLabStatus("ERROR: Main script missing — cannot load " + FACE_FILE)
		Return False
	EndIf
	LabFaceTemplates = new String[64]
	LabFaceTemplateCount = m.LoadStageBankAt(FACE_FILE, LabFaceTemplates, CONFIG_PATH)
	LabFaceBankLoaded = True
	If LabFaceTemplateCount <= 0
		SetWoundLabStatus("ERROR: " + FACE_FILE + " — " + m.GetLastStageLoadStatus())
		Debug.Notification("Pickman's Whisper: " + FACE_FILE + " missing or empty")
		Return False
	EndIf
	Return True
EndFunction

; --- Spawn block: copied from PickmansWhisperBedGiftScript (Force path), Lab* names, sticky ---

Function StripLabCorpse(Actor corpse)
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
	If LabAnchor
		Return LabAnchor
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

Function SnapLabCorpseToAnchor(Actor corpse, ObjectReference akAnchor)
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

Bool Function IsWoundLabCorpse(Actor ak)
	Return ak && ak == LabCorpse
EndFunction

Bool Function HasLiveLabCorpse()
	If !LabCorpse
		Return False
	EndIf
	Return True
EndFunction

; Some ActorBases are Protected — KillSilent() with no killer can leave them alive.
; Pass the player as killer; never clear Protected on the shared ActorBase.
; Suppress knife-kill credit — lab KillSilent must not satiate hunger.
Function KillLabCorpse(Actor corpse)
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

Bool Function PoseLabCorpseInFurniture(Actor corpse, ObjectReference akBed)
	If !corpse || !akBed
		Return False
	EndIf
	If corpse.IsDisabled()
		corpse.Enable(False)
	EndIf
	corpse.SetGhost(False)
	StripLabCorpse(corpse)
	Bool snapped = corpse.SnapIntoInteraction(akBed)
	If snapped
		; Utility.Wait freezes while MCM is open — skip settle delay in menus.
		If !Utility.IsInMenuMode()
			Utility.Wait(0.5)
		EndIf
		KillLabCorpse(corpse)
		StripLabCorpse(corpse)
		SetWoundLabStatus("posed via SnapIntoInteraction + KillSilent")
		Return True
	EndIf
	Debug.Notification("Pickman's Whisper: wound lab SnapIntoInteraction FAILED — ragdoll fallback")
	Debug.Trace("PickmansWhisper: ERROR wound lab SnapIntoInteraction failed — ragdoll fallback")
	KillLabCorpse(corpse)
	StripLabCorpse(corpse)
	SnapLabCorpseToAnchor(corpse, akBed)
	SetWoundLabStatus("ERROR: SnapIntoInteraction failed — ragdoll fallback")
	Return False
EndFunction

; BedGift CreateBedCorpseAt(akAnchor, abParkUnderPlayer=False) — park/warm path omitted (no sleep).
Bool Function CreateLabCorpseAt(ObjectReference akAnchor)
	If !akAnchor
		Return False
	EndIf
	If LabSpawnBusy
		SetWoundLabStatus("skip: spawn already in progress")
		Return False
	EndIf
	If HasLiveLabCorpse()
		SetWoundLabStatus("skip: corpse already present")
		Return False
	EndIf
	Actor player = Game.GetPlayer()
	If !player
		Return False
	EndIf
	Form spawnForm = Game.GetFormFromFile(FID_BED_SPAWN_NPC, "Fallout4.esm")
	If !spawnForm
		SetWoundLabStatus("ERROR: DiamondCityResidentF01NoodleMarket missing")
		Debug.Notification("Pickman's Whisper: wound lab spawn form missing (DiamondCityResidentF01NoodleMarket)")
		Return False
	EndIf
	LabSpawnBusy = True
	ObjectReference placed = akAnchor.PlaceAtMe(spawnForm, 1, False, False)
	Actor corpse = placed as Actor
	If !corpse
		If placed
			placed.Delete()
		EndIf
		LabSpawnBusy = False
		SetWoundLabStatus("ERROR: PlaceAtMe failed")
		Debug.Notification("Pickman's Whisper: wound lab PlaceAtMe failed")
		Return False
	EndIf
	; Assign before park/pose so killscan never tracks or satiates on this body.
	LabCorpse = corpse
	PoseLabCorpseInFurniture(corpse, akAnchor)
	If !corpse.IsDisabled()
		corpse.Disable(False)
	EndIf
	LabSpawnBusy = False
	Return True
EndFunction

; BedGift TrySpawnBedCorpse(akAnchor, abForce=True) — no bond / MCM / cooldown gates.
Bool Function TrySpawnLabCorpse(ObjectReference akAnchor)
	If !akAnchor
		SetWoundLabStatus("skip: no bed anchor")
		Return False
	EndIf
	If LabSpawnBusy || HasLiveLabCorpse()
		SetWoundLabStatus("skip: corpse already present")
		Return False
	EndIf
	If !CreateLabCorpseAt(akAnchor)
		Return False
	EndIf
	LabAnchor = akAnchor
	SetWoundLabStatus("spawned (wound lab)")
	Return True
EndFunction

; Mirror BedGift ClearBedCorpse — no overlay strip (LooksMenu RemoveAll from MCM hung Spawn).
Function ClearLabCorpse()
	LabSpawnBusy = False
	If LabCorpse
		Actor c = LabCorpse
		LabCorpse = None
		If c
			KillLabCorpse(c)
			If !c.IsDisabled()
				c.Disable(False)
			EndIf
			c.Delete()
		EndIf
		Debug.Trace("PickmansWhisper: wound lab corpse cleared")
	EndIf
	LabCorpse = None
EndFunction

; BedGift PresentBedCorpseOnWake — no wake toast, no decay auto-apply, no despawn timer.
Function PresentLabCorpse()
	If !HasLiveLabCorpse()
		Return
	EndIf
	If LabCorpse.IsDisabled()
		LabCorpse.Enable(False)
	EndIf
	If LabAnchor && !LabCorpse.IsDead()
		PoseLabCorpseInFurniture(LabCorpse, LabAnchor)
	ElseIf LabAnchor && LabCorpse.IsDead()
		StripLabCorpse(LabCorpse)
	ElseIf !LabCorpse.IsDead()
		KillLabCorpse(LabCorpse)
		StripLabCorpse(LabCorpse)
	Else
		StripLabCorpse(LabCorpse)
	EndIf
	SetWoundLabStatus("presented (sticky) | " + LastWoundLabStatus)
EndFunction

; Exact BedGift DebugForceBedGift sequence (Lab* names only).
Function DebugSpawnWoundLabCorpse()
	Actor player = Game.GetPlayer()
	If !player
		Debug.MessageBox("Pickman's Whisper\n\nNo player.")
		Return
	EndIf
	ClearLabCorpse()
	ObjectReference anchor = ResolveBedAnchor(None)
	If !anchor
		anchor = player
	EndIf
	LabAnchor = anchor
	If !TrySpawnLabCorpse(anchor)
		Debug.MessageBox("Pickman's Whisper\n\nWound lab spawn failed.\n" + LastWoundLabStatus)
		Return
	EndIf
	PresentLabCorpse()
	Debug.MessageBox("Pickman's Whisper\n\nWound lab corpse spawned.\n" + LastWoundLabStatus + "\nClear wound lab corpse to remove. Apply wounds when ready.")
EndFunction

; BedGift DebugClearBedGift — only cleanup path (no auto despawn).
Function DebugClearWoundLabCorpse()
	ClearLabCorpse()
	LabAnchor = None
	SetWoundLabStatus("cleared (debug)")
	Debug.MessageBox("Pickman's Whisper\n\nWound lab corpse cleared.\n" + LastWoundLabStatus)
EndFunction

Int Function ClampLabCount(Int n)
	If n < 1
		Return 1
	ElseIf n > 16
		Return 16
	EndIf
	Return n
EndFunction

; MCM Tint preset menu → writes fWoundLabTintR/G/B (alpha unchanged).
; Indices match config.json options order (single source for labels; RGB only here).
Function ApplyWoundLabTintPreset()
	If !MCM.IsInstalled()
		Return
	EndIf
	Int preset = MCM.GetModSettingInt(MOD_NAME, "iWoundLabTintPreset:WoundLab")
	Float r = 1.0
	Float g = 0.92
	Float b = 0.88
	String label = "P1 pale"
	If preset == 1
		; Death decay green — sickly corpse green
		r = 0.35
		g = 0.55
		b = 0.30
		label = "Death decay green"
	ElseIf preset == 2
		; Body decay red — meat / livid red
		r = 0.78
		g = 0.22
		b = 0.20
		label = "Body decay red"
	ElseIf preset == 3
		; Ashen gray — cool drained gray
		r = 0.52
		g = 0.52
		b = 0.55
		label = "Ashen gray"
	Else
		; 0 / unknown → P1 locked pale
		preset = 0
		r = 1.0
		g = 0.92
		b = 0.88
		label = "P1 pale"
	EndIf
	MCM.SetModSettingFloat(MOD_NAME, "fWoundLabTintR:WoundLab", r)
	MCM.SetModSettingFloat(MOD_NAME, "fWoundLabTintG:WoundLab", g)
	MCM.SetModSettingFloat(MOD_NAME, "fWoundLabTintB:WoundLab", b)
	SetWoundLabStatus("tint preset: " + label + " RGB=" + r + "/" + g + "/" + b)
	MCM.RefreshMenu()
EndFunction

Function DebugApplyWoundLabOverlays()
	If !EnsureLabWoundBank()
		Debug.MessageBox("Pickman's Whisper\n\n" + LastWoundLabStatus)
		Return
	EndIf
	Int idx = 0
	Float tintR = 1.0
	Float tintG = 0.92
	Float tintB = 0.88
	Float tintA = 0.75
	; stepper options are "1".."16" → stored index 0..15; count = index + 1
	Int countIdx = 0
	If MCM.IsInstalled()
		idx = MCM.GetModSettingInt(MOD_NAME, "iWoundLabTemplate:WoundLab")
		tintR = MCM.GetModSettingFloat(MOD_NAME, "fWoundLabTintR:WoundLab")
		tintG = MCM.GetModSettingFloat(MOD_NAME, "fWoundLabTintG:WoundLab")
		tintB = MCM.GetModSettingFloat(MOD_NAME, "fWoundLabTintB:WoundLab")
		tintA = MCM.GetModSettingFloat(MOD_NAME, "fWoundLabTintA:WoundLab")
		countIdx = MCM.GetModSettingInt(MOD_NAME, "iWoundLabCount:WoundLab")
	EndIf
	Int count = ClampLabCount(countIdx + 1)
	If idx < 0
		idx = 0
	ElseIf idx >= LabWoundTemplateCount
		idx = LabWoundTemplateCount - 1
	EndIf
	String templateId = LabWoundTemplates[idx]
	If !templateId || templateId == ""
		SetWoundLabStatus("ERROR: empty template at index " + idx)
		Debug.MessageBox("Pickman's Whisper\n\n" + LastWoundLabStatus)
		Return
	EndIf
	Actor target = LabCorpse
	If !target
		PickmansWhisperMainQuestScript m = Main()
		If m
			target = m.GetLookAimActor()
		EndIf
	EndIf
	If !target || target == Game.GetPlayer()
		Debug.MessageBox("Pickman's Whisper\n\nNo wound lab corpse.\nSpawn on Wound Lab page, or aim a corpse then Apply.")
		Return
	EndIf
	; Keep strip fresh so body overlays can show.
	StripLabCorpse(target)
	PickmansWhisperCorpseDecayScript decay = CorpseDecay()
	If !decay
		SetWoundLabStatus("ERROR: CorpseDecay script missing")
		Debug.MessageBox("Pickman's Whisper\n\nCorpseDecay script missing on Main quest.")
		Return
	EndIf
	decay.ApplyTintedWoundTemplateN(target, templateId, count, tintR, tintG, tintB, tintA, LabWoundTemplates, LabWoundTemplateCount)
	SetWoundLabStatus(decay.LastCorpseDecayStatus)
	Debug.MessageBox("Pickman's Whisper\n\nWound lab apply\nidx=" + idx + " count=" + count + "\n" + templateId + "\n" + LastWoundLabStatus + "\nClose MCM and look at the body.")
EndFunction

Actor Function ResolveLabApplyTarget()
	Actor target = LabCorpse
	If !target
		PickmansWhisperMainQuestScript m = Main()
		If m
			target = m.GetLookAimActor()
		EndIf
	EndIf
	If !target || target == Game.GetPlayer()
		Return None
	EndIf
	Return target
EndFunction

; Apply every DecayWoundOverlays.txt template with current tint.
; Apply count stepper = times each template (capped in CorpseDecay).
Function DebugApplyAllWoundLabOverlays()
	If !EnsureLabWoundBank()
		Debug.MessageBox("Pickman's Whisper\n\n" + LastWoundLabStatus)
		Return
	EndIf
	Actor target = ResolveLabApplyTarget()
	If !target
		Debug.MessageBox("Pickman's Whisper\n\nNo wound lab corpse.\nSpawn on Wound Lab page, or aim a corpse then Apply all.")
		Return
	EndIf
	Float tintR = 1.0
	Float tintG = 0.92
	Float tintB = 0.88
	Float tintA = 0.75
	Int timesEach = 1
	If MCM.IsInstalled()
		tintR = MCM.GetModSettingFloat(MOD_NAME, "fWoundLabTintR:WoundLab")
		tintG = MCM.GetModSettingFloat(MOD_NAME, "fWoundLabTintG:WoundLab")
		tintB = MCM.GetModSettingFloat(MOD_NAME, "fWoundLabTintB:WoundLab")
		tintA = MCM.GetModSettingFloat(MOD_NAME, "fWoundLabTintA:WoundLab")
		timesEach = ClampLabCount(MCM.GetModSettingInt(MOD_NAME, "iWoundLabCount:WoundLab") + 1)
	EndIf
	StripLabCorpse(target)
	PickmansWhisperCorpseDecayScript decay = CorpseDecay()
	If !decay
		SetWoundLabStatus("ERROR: CorpseDecay script missing")
		Debug.MessageBox("Pickman's Whisper\n\nCorpseDecay script missing on Main quest.")
		Return
	EndIf
	decay.ApplyTintedAllWoundTemplates(target, LabWoundTemplates, LabWoundTemplateCount, timesEach, tintR, tintG, tintB, tintA)
	SetWoundLabStatus(decay.LastCorpseDecayStatus)
	Debug.MessageBox("Pickman's Whisper\n\nWound lab apply ALL\ntemplates=" + LabWoundTemplateCount + " x" + timesEach + "\n" + LastWoundLabStatus + "\nClose MCM and look at the body.")
EndFunction

; P0.2 — Porcupine Scars/SkinTexture (DecaySkinOverlays.txt). Stacks with wounds.
; Skin template 2: MCM index 0 = (none)/skip; 1..N map to LabSkinTemplates[0..N-1].
Function DebugApplySkinLabOverlays()
	If !EnsureLabSkinBank()
		Debug.MessageBox("Pickman's Whisper\n\n" + LastWoundLabStatus)
		Return
	EndIf
	Int idx = 0
	Int idx2 = 0
	Float tintR = 1.0
	Float tintG = 0.92
	Float tintB = 0.88
	Float tintA = 0.75
	Int countIdx = 0
	If MCM.IsInstalled()
		idx = MCM.GetModSettingInt(MOD_NAME, "iSkinLabTemplate:WoundLab")
		idx2 = MCM.GetModSettingInt(MOD_NAME, "iSkinLabTemplate2:WoundLab")
		tintR = MCM.GetModSettingFloat(MOD_NAME, "fWoundLabTintR:WoundLab")
		tintG = MCM.GetModSettingFloat(MOD_NAME, "fWoundLabTintG:WoundLab")
		tintB = MCM.GetModSettingFloat(MOD_NAME, "fWoundLabTintB:WoundLab")
		tintA = MCM.GetModSettingFloat(MOD_NAME, "fWoundLabTintA:WoundLab")
		countIdx = MCM.GetModSettingInt(MOD_NAME, "iWoundLabCount:WoundLab")
	EndIf
	Int count = ClampLabCount(countIdx + 1)
	If idx < 0
		idx = 0
	ElseIf idx >= LabSkinTemplateCount
		idx = LabSkinTemplateCount - 1
	EndIf
	String templateId = LabSkinTemplates[idx]
	If !templateId || templateId == ""
		SetWoundLabStatus("ERROR: empty skin template at index " + idx)
		Debug.MessageBox("Pickman's Whisper\n\n" + LastWoundLabStatus)
		Return
	EndIf
	; idx2: 0 = (none); 1..count map to bank 0..count-1
	String templateId2 = ""
	If idx2 > 0
		Int bankIdx2 = idx2 - 1
		If bankIdx2 >= LabSkinTemplateCount
			bankIdx2 = LabSkinTemplateCount - 1
		EndIf
		If bankIdx2 >= 0
			templateId2 = LabSkinTemplates[bankIdx2]
		EndIf
	EndIf
	Actor target = ResolveLabApplyTarget()
	If !target
		Debug.MessageBox("Pickman's Whisper\n\nNo wound lab corpse.\nSpawn on Wound Lab page, or aim a corpse then Apply skin.")
		Return
	EndIf
	StripLabCorpse(target)
	PickmansWhisperCorpseDecayScript decay = CorpseDecay()
	If !decay
		SetWoundLabStatus("ERROR: CorpseDecay script missing")
		Debug.MessageBox("Pickman's Whisper\n\nCorpseDecay script missing on Main quest.")
		Return
	EndIf
	; Clear skin bank once, then layer template 1 (+ optional template 2 without re-clear).
	decay.ApplyTintedSkinTemplateN(target, templateId, count, tintR, tintG, tintB, tintA, LabSkinTemplates, LabSkinTemplateCount)
	String status2 = "(none)"
	If templateId2 != ""
		; clearCount 0 → RemoveMatchingOverlays no-ops; keeps first skin layered.
		decay.ApplyTintedSkinTemplateN(target, templateId2, count, tintR, tintG, tintB, tintA, LabSkinTemplates, 0)
		status2 = templateId2
	EndIf
	SetWoundLabStatus(decay.LastCorpseDecayStatus + " +2=" + status2)
	Debug.MessageBox("Pickman's Whisper\n\nSkin lab apply\n1=" + templateId + "\n2=" + status2 + "\ncount=" + count + "\n" + LastWoundLabStatus + "\nClose MCM and look at the body.")
EndFunction

Function DebugApplyAllSkinLabOverlays()
	If !EnsureLabSkinBank()
		Debug.MessageBox("Pickman's Whisper\n\n" + LastWoundLabStatus)
		Return
	EndIf
	Actor target = ResolveLabApplyTarget()
	If !target
		Debug.MessageBox("Pickman's Whisper\n\nNo wound lab corpse.\nSpawn on Wound Lab page, or aim a corpse then Apply all skin.")
		Return
	EndIf
	Float tintR = 1.0
	Float tintG = 0.92
	Float tintB = 0.88
	Float tintA = 0.75
	Int timesEach = 1
	If MCM.IsInstalled()
		tintR = MCM.GetModSettingFloat(MOD_NAME, "fWoundLabTintR:WoundLab")
		tintG = MCM.GetModSettingFloat(MOD_NAME, "fWoundLabTintG:WoundLab")
		tintB = MCM.GetModSettingFloat(MOD_NAME, "fWoundLabTintB:WoundLab")
		tintA = MCM.GetModSettingFloat(MOD_NAME, "fWoundLabTintA:WoundLab")
		timesEach = ClampLabCount(MCM.GetModSettingInt(MOD_NAME, "iWoundLabCount:WoundLab") + 1)
	EndIf
	StripLabCorpse(target)
	PickmansWhisperCorpseDecayScript decay = CorpseDecay()
	If !decay
		SetWoundLabStatus("ERROR: CorpseDecay script missing")
		Debug.MessageBox("Pickman's Whisper\n\nCorpseDecay script missing on Main quest.")
		Return
	EndIf
	decay.ApplyTintedAllSkinTemplates(target, LabSkinTemplates, LabSkinTemplateCount, timesEach, tintR, tintG, tintB, tintA)
	SetWoundLabStatus(decay.LastCorpseDecayStatus)
	Debug.MessageBox("Pickman's Whisper\n\nSkin lab apply ALL\ntemplates=" + LabSkinTemplateCount + " x" + timesEach + "\n" + LastWoundLabStatus + "\nClose MCM and look at the body.")
EndFunction

Bool Function IsScarSkinTemplate(String templateId)
	If !templateId || templateId == ""
		Return False
	EndIf
	; Bank convention: Scars_01..Scars_20 (prefix only — keeps SkinTexture_* out).
	If GardenOfEden.StrLength(templateId) < 6
		Return False
	EndIf
	Return GardenOfEden.SubStr(templateId, 0, 6) == "Scars_"
EndFunction

; Clear Porcupine overlays, then apply ModConfig decayStage* SkinTextures + tint (+ scars if flagged).
Function DebugApplyDecayStageLab()
	If !EnsureLabSkinBank()
		Debug.MessageBox("Pickman's Whisper\n\n" + LastWoundLabStatus)
		Return
	EndIf
	PickmansWhisperMainQuestScript m = Main()
	If !m
		Debug.MessageBox("Pickman's Whisper\n\nMain script missing.")
		Return
	EndIf
	If !m.DecayStagesReady()
		m.LoadModConfig()
	EndIf
	If !m.DecayStagesReady()
		SetWoundLabStatus("ERROR: ModConfig decayStage0..4 — " + m.ModConfigLoadStatus)
		Debug.MessageBox("Pickman's Whisper\n\nDecay stages not loaded from ModConfig.txt.\n" + LastWoundLabStatus + "\nReload line banks / check decayStage0..4.")
		Return
	EndIf
	Actor target = ResolveLabApplyTarget()
	If !target
		Debug.MessageBox("Pickman's Whisper\n\nNo wound lab corpse.\nSpawn on Wound Lab page, or aim a corpse then Apply stage.")
		Return
	EndIf
	Int stage = 0
	If MCM.IsInstalled()
		stage = MCM.GetModSettingInt(MOD_NAME, "iDecayLabStage:WoundLab")
	EndIf
	If stage < 0
		stage = 0
	ElseIf stage > 4
		stage = 4
	EndIf
	Float tintR = m.GetDecayStageTintR(stage)
	Float tintG = m.GetDecayStageTintG(stage)
	Float tintB = m.GetDecayStageTintB(stage)
	Float tintA = m.GetDecayStageTintA(stage)
	String stageName = m.GetDecayStageName(stage)
	If MCM.IsInstalled()
		MCM.SetModSettingFloat(MOD_NAME, "fWoundLabTintR:WoundLab", tintR)
		MCM.SetModSettingFloat(MOD_NAME, "fWoundLabTintG:WoundLab", tintG)
		MCM.SetModSettingFloat(MOD_NAME, "fWoundLabTintB:WoundLab", tintB)
		MCM.SetModSettingFloat(MOD_NAME, "fWoundLabTintA:WoundLab", tintA)
	EndIf
	StripLabCorpse(target)
	PickmansWhisperCorpseDecayScript decay = CorpseDecay()
	If !decay
		SetWoundLabStatus("ERROR: CorpseDecay script missing")
		Debug.MessageBox("Pickman's Whisper\n\nCorpseDecay script missing on Main quest.")
		Return
	EndIf
	; Wipe prior Porcupine Scars + SkinTexture; keep DeathMarks wounds.
	decay.ClearSkinBankOverlays(target, LabSkinTemplates, LabSkinTemplateCount)
	; Same ModConfig stage apply as bed gift (skins + optional scars).
	decay.ApplyDecayStageOverlays(target, stage)
	SetWoundLabStatus("stage " + stage + " " + stageName + " RGB=" + tintR + "/" + tintG + "/" + tintB + " A=" + tintA + " | " + decay.LastCorpseDecayStatus)
	; Do not refresh MCM mid-CallFunction — that has stalled later Spawn/Clear buttons.
	Debug.MessageBox("Pickman's Whisper\n\nDecay stage applied\n" + stageName + "\n" + LastWoundLabStatus + "\nClose MCM and look at the body.")
EndFunction

; Porcupine Scars_* only — additive (no overlay clear) so SkinTexture_* already on the body stay.
Function DebugApplyAllScarLabOverlays()
	If !EnsureLabSkinBank()
		Debug.MessageBox("Pickman's Whisper\n\n" + LastWoundLabStatus)
		Return
	EndIf
	Actor target = ResolveLabApplyTarget()
	If !target
		Debug.MessageBox("Pickman's Whisper\n\nNo wound lab corpse.\nSpawn on Wound Lab page, or aim a corpse then Apply all scars.")
		Return
	EndIf
	String[] scars = new String[64]
	Int scarCount = 0
	Int i = 0
	While i < LabSkinTemplateCount
		String id = LabSkinTemplates[i]
		If IsScarSkinTemplate(id)
			scars[scarCount] = id
			scarCount += 1
		EndIf
		i += 1
	EndWhile
	If scarCount <= 0
		SetWoundLabStatus("ERROR: no Scars_* templates in " + SKIN_FILE)
		Debug.MessageBox("Pickman's Whisper\n\n" + LastWoundLabStatus)
		Return
	EndIf
	Float tintR = 1.0
	Float tintG = 0.92
	Float tintB = 0.88
	Float tintA = 0.75
	Int timesEach = 1
	If MCM.IsInstalled()
		tintR = MCM.GetModSettingFloat(MOD_NAME, "fWoundLabTintR:WoundLab")
		tintG = MCM.GetModSettingFloat(MOD_NAME, "fWoundLabTintG:WoundLab")
		tintB = MCM.GetModSettingFloat(MOD_NAME, "fWoundLabTintB:WoundLab")
		tintA = MCM.GetModSettingFloat(MOD_NAME, "fWoundLabTintA:WoundLab")
		timesEach = ClampLabCount(MCM.GetModSettingInt(MOD_NAME, "iWoundLabCount:WoundLab") + 1)
	EndIf
	StripLabCorpse(target)
	PickmansWhisperCorpseDecayScript decay = CorpseDecay()
	If !decay
		SetWoundLabStatus("ERROR: CorpseDecay script missing")
		Debug.MessageBox("Pickman's Whisper\n\nCorpseDecay script missing on Main quest.")
		Return
	EndIf
	decay.ApplyTintedAllSkinTemplatesKeepExisting(target, scars, scarCount, timesEach, tintR, tintG, tintB, tintA)
	SetWoundLabStatus(decay.LastCorpseDecayStatus)
	Debug.MessageBox("Pickman's Whisper\n\nSkin lab apply ALL SCARS (keep SkinTexture)\ntemplates=" + scarCount + " x" + timesEach + "\n" + LastWoundLabStatus + "\nClose MCM and look at the body.")
EndFunction

; Face — SFT Damage headparts (DecayFaceOverlays.txt FULL names). Soft dep SFT.esp.
; Face template 2: MCM index 0 = (none)/skip; 1..N map to LabFaceTemplates[0..N-1].
Function DebugApplyFaceLabOverlays()
	If !EnsureLabFaceBank()
		Debug.MessageBox("Pickman's Whisper\n\n" + LastWoundLabStatus)
		Return
	EndIf
	Int idx = 0
	Int idx2 = 0
	Float tintR = 1.0
	Float tintG = 0.92
	Float tintB = 0.88
	Float tintA = 0.75
	Int countIdx = 0
	If MCM.IsInstalled()
		idx = MCM.GetModSettingInt(MOD_NAME, "iFaceLabTemplate:WoundLab")
		idx2 = MCM.GetModSettingInt(MOD_NAME, "iFaceLabTemplate2:WoundLab")
		tintR = MCM.GetModSettingFloat(MOD_NAME, "fWoundLabTintR:WoundLab")
		tintG = MCM.GetModSettingFloat(MOD_NAME, "fWoundLabTintG:WoundLab")
		tintB = MCM.GetModSettingFloat(MOD_NAME, "fWoundLabTintB:WoundLab")
		tintA = MCM.GetModSettingFloat(MOD_NAME, "fWoundLabTintA:WoundLab")
		countIdx = MCM.GetModSettingInt(MOD_NAME, "iWoundLabCount:WoundLab")
	EndIf
	Int count = ClampLabCount(countIdx + 1)
	If idx < 0
		idx = 0
	ElseIf idx >= LabFaceTemplateCount
		idx = LabFaceTemplateCount - 1
	EndIf
	String templateId = LabFaceTemplates[idx]
	If !templateId || templateId == ""
		SetWoundLabStatus("ERROR: empty face template at index " + idx)
		Debug.MessageBox("Pickman's Whisper\n\n" + LastWoundLabStatus)
		Return
	EndIf
	String templateId2 = ""
	If idx2 > 0
		Int bankIdx2 = idx2 - 1
		If bankIdx2 >= LabFaceTemplateCount
			bankIdx2 = LabFaceTemplateCount - 1
		EndIf
		If bankIdx2 >= 0
			templateId2 = LabFaceTemplates[bankIdx2]
		EndIf
	EndIf
	Actor target = ResolveLabApplyTarget()
	If !target
		Debug.MessageBox("Pickman's Whisper\n\nNo wound lab corpse.\nSpawn on Wound Lab page, or aim a corpse then Apply face.")
		Return
	EndIf
	StripLabCorpse(target)
	PickmansWhisperCorpseDecayScript decay = CorpseDecay()
	If !decay
		SetWoundLabStatus("ERROR: CorpseDecay script missing")
		Debug.MessageBox("Pickman's Whisper\n\nCorpseDecay script missing on Main quest.")
		Return
	EndIf
	decay.ApplyTintedFaceTemplateN(target, templateId, count, tintR, tintG, tintB, tintA, LabFaceTemplates, LabFaceTemplateCount)
	String status2 = "(none)"
	If templateId2 != ""
		decay.ApplyTintedFaceTemplateN(target, templateId2, count, tintR, tintG, tintB, tintA, LabFaceTemplates, 0)
		status2 = templateId2
	EndIf
	SetWoundLabStatus(decay.LastCorpseDecayStatus + " +2=" + status2)
	Debug.MessageBox("Pickman's Whisper\n\nFace lab apply\n1=" + templateId + "\n2=" + status2 + "\ncount=" + count + "\n" + LastWoundLabStatus + "\nClose MCM and look at the face.")
EndFunction

Function DebugApplyAllFaceLabOverlays()
	If !EnsureLabFaceBank()
		Debug.MessageBox("Pickman's Whisper\n\n" + LastWoundLabStatus)
		Return
	EndIf
	Actor target = ResolveLabApplyTarget()
	If !target
		Debug.MessageBox("Pickman's Whisper\n\nNo wound lab corpse.\nSpawn on Wound Lab page, or aim a corpse then Apply all face.")
		Return
	EndIf
	Float tintR = 1.0
	Float tintG = 0.92
	Float tintB = 0.88
	Float tintA = 0.75
	Int timesEach = 1
	If MCM.IsInstalled()
		tintR = MCM.GetModSettingFloat(MOD_NAME, "fWoundLabTintR:WoundLab")
		tintG = MCM.GetModSettingFloat(MOD_NAME, "fWoundLabTintG:WoundLab")
		tintB = MCM.GetModSettingFloat(MOD_NAME, "fWoundLabTintB:WoundLab")
		tintA = MCM.GetModSettingFloat(MOD_NAME, "fWoundLabTintA:WoundLab")
		timesEach = ClampLabCount(MCM.GetModSettingInt(MOD_NAME, "iWoundLabCount:WoundLab") + 1)
	EndIf
	StripLabCorpse(target)
	PickmansWhisperCorpseDecayScript decay = CorpseDecay()
	If !decay
		SetWoundLabStatus("ERROR: CorpseDecay script missing")
		Debug.MessageBox("Pickman's Whisper\n\nCorpseDecay script missing on Main quest.")
		Return
	EndIf
	decay.ApplyTintedAllFaceTemplates(target, LabFaceTemplates, LabFaceTemplateCount, timesEach, tintR, tintG, tintB, tintA)
	SetWoundLabStatus(decay.LastCorpseDecayStatus)
	Debug.MessageBox("Pickman's Whisper\n\nFace lab apply ALL\ntemplates=" + LabFaceTemplateCount + " x" + timesEach + "\n" + LastWoundLabStatus + "\nClose MCM and look at the face.")
EndFunction
