Scriptname PickmansWhisperCorpseDecayScript extends Quest
{Slice H — corpse decay visuals via LooksMenu overlays.}

; Soft deps (no ESP master): LooksMenu.esp + DeadOverlays / porcOverlays.esl / SFT.esp.
; Uses Overlays.Add (not AddEntry) so we can tint — AddEntry hardcodes rgba 0.
; Wound ids: DecayWoundOverlays.txt | Skin ids: DecaySkinOverlays.txt
; Face ids: DecayFaceOverlays.txt — SFT Damage FULL names (LooksMenu body overlays cannot paint faces).
; Slice I face decals: DecayFaceStages.txt (stage→color) + DecayFaceArmorIds.txt (color→ARMO FormID).

String PLUGIN_LOOKSMENU = "LooksMenu.esp"
String PLUGIN_DEAD_OVERLAYS = "INVB_OverlayFramework_DeadOverlays.esp"
String PLUGIN_PORC_OVERLAYS = "porcOverlays.esl"
String PLUGIN_SFT = "SFT.esp"
String PLUGIN_PW = "PickmansWhisper.esp"
; SFT.esp FormLists of Damage / Boxer headparts (female / male). Soft dep — no ESP master.
Int FID_SFT_DAMAGE_F = 0x000008D ; SFT_Damage
Int FID_SFT_DAMAGE_M = 0x00000B2 ; SFT_Damage_M
String WOUND_FILE = "DecayWoundOverlays.txt"
String SKIN_FILE = "DecaySkinOverlays.txt"
String FACE_FILE = "DecayFaceOverlays.txt"
String FACE_STAGE_FILE = "DecayFaceStages.txt"
String FACE_ARMOR_IDS_FILE = "DecayFaceArmorIds.txt"
String CONFIG_PATH = ".\\Data\\PickmansWhisper\\config\\"
Int BED_GIFT_WOUND_COUNT = 6 ; doubled for coverage / progression look-test (was 3)
; Bed gift applies ModConfig decayStage4 (Black Putrefaction) after DeathMarks wounds.
Int BED_GIFT_DECAY_STAGE = 4
Int WOUND_PRIORITY = 40
Int SKIN_PRIORITY = 30 ; under wounds so DeathMarks stay readable
; Locked P1 tint — lighten dark DeathMarks (LooksMenu Entry RGB/A). DebugForce pale path only.
Float WOUND_TINT_R = 1.0
Float WOUND_TINT_G = 0.92
Float WOUND_TINT_B = 0.88
Float WOUND_TINT_A = 0.75
Int FACE_ARMOR_MAX = 16
Int DECAY_STAGE_COUNT = 5

String[] WoundTemplates
Int WoundTemplateCount = 0
Bool WoundBankLoaded = False
String[] SkinTemplates
Int SkinTemplateCount = 0
Bool SkinBankLoaded = False
String[] FaceTemplates
Int FaceTemplateCount = 0
Bool FaceBankLoaded = False
; Slice I — color label → local ARMO FormID (from DecayFaceArmorIds.txt).
String[] FaceArmorLabels
Int[] FaceArmorArmoFids
Int FaceArmorCount = 0
; Per ModConfig stage 0..4 — resolved ARMO local FormID (0 = missing).
Int[] FaceStageArmoFids
Bool FaceArmorBanksLoaded = False
String FaceArmorLoadStatus = ""
String Property LastCorpseDecayStatus = "" Auto

PickmansWhisperMainQuestScript Function Main()
	Return (Self as Quest) as PickmansWhisperMainQuestScript
EndFunction

PickmansWhisperWorldScanScript Function WorldScan()
	Return (Self as Quest) as PickmansWhisperWorldScanScript
EndFunction

Float LastOverlaySyncReal = 0.0
Float OVERLAY_SYNC_MIN_SECONDS = 8.0

; Victims MCM test harness: after ForceDecayKillClockToStage, drop rate-limit / fail backoff
; so the next WorldScan snapshot can SyncDecayForKnifeCorpse instead of waiting 8–30s.
Function NoteForcedDecayClockForTest()
	LastOverlaySyncReal = 0.0
	PickmansWhisperMainQuestScript m = Main()
	If m
		m.DecaySyncBackoffUntil = 0.0
	EndIf
EndFunction

; Kicked via WorldScan CallFunctionNoWait — LooksMenu Utility.Wait must not run on voice stack.
; Consumes WorldScan.ScanDead — never FindActors here.
Function SyncOverlaysFromWorldScanSnapshot()
	If Utility.IsInMenuMode()
		Return
	EndIf
	PickmansWhisperMainQuestScript m = Main()
	If !m || !m.BondStarted
		Return
	EndIf
	Float now = Utility.GetCurrentRealTime()
	If now < m.DecaySyncBackoffUntil
		Return
	EndIf
	If (now - LastOverlaySyncReal) < OVERLAY_SYNC_MIN_SECONDS
		Return
	EndIf
	LastOverlaySyncReal = now

	PickmansWhisperWorldScanScript scan = WorldScan()
	If !scan
		Return
	EndIf
	Actor[] dead = scan.ScanDead
	Int deadCount = scan.ScanDeadCount
	If !dead || deadCount <= 0
		Return
	EndIf
	Actor player = Game.GetPlayer()
	Int n = deadCount
	If n > 16
		n = 16
	EndIf
	Int i = 0
	Bool anyFail = False
	While i < n
		Actor ak = dead[i]
		If ak && ak != player && ak.IsDead() && ak.Is3DLoaded() && !ak.IsDisabled()
			Int id = ak.GetFormID()
			If m.FindDecayKillSlot(id) < 0
				m.EnsureDecayForTrackedVictim(ak, False)
			EndIf
			If m.FindDecayKillSlot(id) >= 0
				Int want = m.ResolveDecayStageForKill(id)
				Int before = m.GetDecayKillLastStage(id)
				SyncDecayForKnifeCorpse(ak)
				Int after = m.GetDecayKillLastStage(id)
				If want >= 0 && before != want && after != want
					anyFail = True
				EndIf
			EndIf
		EndIf
		i += 1
	EndWhile
	If anyFail
		m.DecaySyncBackoffUntil = now + 30.0
		Debug.Trace("PickmansWhisper: decay overlay sync backoff 30s (LooksMenu apply failed — voice path stays free)")
	EndIf
EndFunction

Function SetCorpseDecayStatus(String reason)
	LastCorpseDecayStatus = reason
	PickmansWhisperMainQuestScript m = Main()
	If m
		m.LastCorpseDecayStatus = reason
	EndIf
	; Status is Trace + MCM string only — overlay Apply must not spam the HUD.
	Debug.Trace("PickmansWhisper: corpse decay | " + reason)
EndFunction

Bool Function EnsureWoundBank()
	If WoundBankLoaded && WoundTemplateCount > 0
		Return True
	EndIf
	PickmansWhisperMainQuestScript m = Main()
	If !m
		SetCorpseDecayStatus("ERROR: Main script missing — cannot load " + WOUND_FILE)
		Return False
	EndIf
	WoundTemplates = new String[64]
	WoundTemplateCount = m.LoadStageBankAt(WOUND_FILE, WoundTemplates, CONFIG_PATH)
	WoundBankLoaded = True
	If WoundTemplateCount <= 0
		SetCorpseDecayStatus("ERROR: " + WOUND_FILE + " — " + m.GetLastStageLoadStatus())
		Debug.Notification("Pickman's Whisper: " + WOUND_FILE + " missing or empty")
		Debug.Trace("PickmansWhisper: ERROR DecayWoundOverlays load failed — " + m.GetLastStageLoadStatus())
		Return False
	EndIf
	Return True
EndFunction

Bool Function EnsureSkinBank()
	If SkinBankLoaded && SkinTemplateCount > 0
		Return True
	EndIf
	PickmansWhisperMainQuestScript m = Main()
	If !m
		SetCorpseDecayStatus("ERROR: Main script missing — cannot load " + SKIN_FILE)
		Return False
	EndIf
	SkinTemplates = new String[64]
	SkinTemplateCount = m.LoadStageBankAt(SKIN_FILE, SkinTemplates, CONFIG_PATH)
	SkinBankLoaded = True
	If SkinTemplateCount <= 0
		SetCorpseDecayStatus("ERROR: " + SKIN_FILE + " — " + m.GetLastStageLoadStatus())
		Debug.Notification("Pickman's Whisper: " + SKIN_FILE + " missing or empty")
		Debug.Trace("PickmansWhisper: ERROR DecaySkinOverlays load failed — " + m.GetLastStageLoadStatus())
		Return False
	EndIf
	Return True
EndFunction

Bool Function EnsureFaceBank()
	If FaceBankLoaded && FaceTemplateCount > 0
		Return True
	EndIf
	PickmansWhisperMainQuestScript m = Main()
	If !m
		SetCorpseDecayStatus("ERROR: Main script missing — cannot load " + FACE_FILE)
		Return False
	EndIf
	FaceTemplates = new String[64]
	FaceTemplateCount = m.LoadStageBankAt(FACE_FILE, FaceTemplates, CONFIG_PATH)
	FaceBankLoaded = True
	If FaceTemplateCount <= 0
		SetCorpseDecayStatus("ERROR: " + FACE_FILE + " — " + m.GetLastStageLoadStatus())
		Debug.Notification("Pickman's Whisper: " + FACE_FILE + " missing or empty")
		Debug.Trace("PickmansWhisper: ERROR DecayFaceOverlays load failed — " + m.GetLastStageLoadStatus())
		Return False
	EndIf
	Return True
EndFunction

Int Function FindCharIndex(String s, String ch)
	If !s || !ch
		Return -1
	EndIf
	Int i = 0
	Int n = GardenOfEden.StrLength(s)
	While i < n
		If GardenOfEden.SubStr(s, i, 1) == ch
			Return i
		EndIf
		i += 1
	EndWhile
	Return -1
EndFunction

Int Function FindFaceArmorLabelIndex(String label)
	If !label
		Return -1
	EndIf
	Int i = 0
	While i < FaceArmorCount
		If FaceArmorLabels[i] == label
			Return i
		EndIf
		i += 1
	EndWhile
	Return -1
EndFunction

; DecayFaceArmorIds.txt + DecayFaceStages.txt — fail loud if missing/incomplete.
Bool Function EnsureDecayFaceArmorBanks()
	If FaceArmorBanksLoaded && FaceArmorCount > 0
		Return True
	EndIf
	PickmansWhisperMainQuestScript m = Main()
	If !m
		FaceArmorLoadStatus = "ERROR: Main missing"
		SetCorpseDecayStatus(FaceArmorLoadStatus)
		Return False
	EndIf
	FaceArmorLabels = new String[16]
	FaceArmorArmoFids = new Int[16]
	FaceArmorCount = 0
	FaceStageArmoFids = new Int[5]
	Int si = 0
	While si < DECAY_STAGE_COUNT
		FaceStageArmoFids[si] = 0
		si += 1
	EndWhile
	FaceArmorBanksLoaded = False
	FaceArmorLoadStatus = "READ FAILED"

	If !GardenOfEden2.DoesFileExist(FACE_ARMOR_IDS_FILE, CONFIG_PATH)
		FaceArmorLoadStatus = "MISSING " + FACE_ARMOR_IDS_FILE
		SetCorpseDecayStatus("ERROR: " + FaceArmorLoadStatus + " — rebuild ESP")
		Debug.Notification("Pickman's Whisper: " + FACE_ARMOR_IDS_FILE + " missing — rebuild ESP")
		Debug.Trace("PickmansWhisper: ERROR " + FACE_ARMOR_IDS_FILE + " missing at " + CONFIG_PATH)
		Return False
	EndIf
	If !GardenOfEden2.DoesFileExist(FACE_STAGE_FILE, CONFIG_PATH)
		FaceArmorLoadStatus = "MISSING " + FACE_STAGE_FILE
		SetCorpseDecayStatus("ERROR: " + FaceArmorLoadStatus)
		Debug.Notification("Pickman's Whisper: " + FACE_STAGE_FILE + " missing")
		Debug.Trace("PickmansWhisper: ERROR " + FACE_STAGE_FILE + " missing at " + CONFIG_PATH)
		Return False
	EndIf

	String[] idRaw = GardenOfEden2.GetLinesFromFile(FACE_ARMOR_IDS_FILE, CONFIG_PATH)
	If !idRaw || idRaw.Length == 0
		FaceArmorLoadStatus = "EMPTY " + FACE_ARMOR_IDS_FILE
		SetCorpseDecayStatus("ERROR: " + FaceArmorLoadStatus)
		Debug.Notification("Pickman's Whisper: " + FACE_ARMOR_IDS_FILE + " empty — rebuild ESP")
		Debug.Trace("PickmansWhisper: ERROR " + FACE_ARMOR_IDS_FILE + " empty")
		Return False
	EndIf
	Int i = 0
	While i < idRaw.Length && FaceArmorCount < FACE_ARMOR_MAX
		String line = m.TrimString(idRaw[i])
		i += 1
		If line == ""
			; skip
		ElseIf GardenOfEden.SubStr(line, 0, 1) == "#"
			; comment
		Else
			Int eq = FindCharIndex(line, "=")
			If eq > 0
				String label = m.TrimString(GardenOfEden.SubStr(line, 0, eq))
				String val = m.TrimString(GardenOfEden.SubStr(line, eq + 1, -1))
				Int comma = FindCharIndex(val, ",")
				If label != "" && comma > 0
					String armoStr = m.TrimString(GardenOfEden.SubStr(val, comma + 1, -1))
					Int armoFid = m.ParsePositiveInt(armoStr)
					If armoFid > 0
						FaceArmorLabels[FaceArmorCount] = label
						FaceArmorArmoFids[FaceArmorCount] = armoFid
						FaceArmorCount += 1
					EndIf
				EndIf
			EndIf
		EndIf
	EndWhile
	If FaceArmorCount <= 0
		FaceArmorLoadStatus = "EMPTY rows " + FACE_ARMOR_IDS_FILE
		SetCorpseDecayStatus("ERROR: " + FaceArmorLoadStatus)
		Debug.Notification("Pickman's Whisper: " + FACE_ARMOR_IDS_FILE + " has no ARMO rows")
		Debug.Trace("PickmansWhisper: ERROR " + FACE_ARMOR_IDS_FILE + " parsed 0 ARMOs")
		Return False
	EndIf

	String[] stageRaw = GardenOfEden2.GetLinesFromFile(FACE_STAGE_FILE, CONFIG_PATH)
	If !stageRaw || stageRaw.Length == 0
		FaceArmorLoadStatus = "EMPTY " + FACE_STAGE_FILE
		SetCorpseDecayStatus("ERROR: " + FaceArmorLoadStatus)
		Debug.Notification("Pickman's Whisper: " + FACE_STAGE_FILE + " empty")
		Debug.Trace("PickmansWhisper: ERROR " + FACE_STAGE_FILE + " empty")
		Return False
	EndIf
	Int mapped = 0
	i = 0
	While i < stageRaw.Length
		String sline = m.TrimString(stageRaw[i])
		i += 1
		If sline == ""
			; skip
		ElseIf GardenOfEden.SubStr(sline, 0, 1) == "#"
			; comment
		Else
			Int seq = FindCharIndex(sline, "=")
			If seq > 0
				String stageStr = m.TrimString(GardenOfEden.SubStr(sline, 0, seq))
				String label = m.TrimString(GardenOfEden.SubStr(sline, seq + 1, -1))
				Int stage = m.ParsePositiveInt(stageStr)
				; ParsePositiveInt rejects 0? Check - for stage 0 need to allow 0
				If stageStr == "0"
					stage = 0
				EndIf
				If stage >= 0 && stage < DECAY_STAGE_COUNT && label != ""
					Int li = FindFaceArmorLabelIndex(label)
					If li < 0
						FaceArmorLoadStatus = "UNKNOWN label " + label + " (stage " + stage + ")"
						SetCorpseDecayStatus("ERROR: " + FaceArmorLoadStatus + " — rebuild ESP / check " + FACE_ARMOR_IDS_FILE)
						Debug.Notification("Pickman's Whisper: face stage " + stage + " label " + label + " has no ARMO")
						Debug.Trace("PickmansWhisper: ERROR face stage map — " + FaceArmorLoadStatus)
						Return False
					EndIf
					FaceStageArmoFids[stage] = FaceArmorArmoFids[li]
					mapped += 1
				EndIf
			EndIf
		EndIf
	EndWhile
	si = 0
	While si < DECAY_STAGE_COUNT
		If FaceStageArmoFids[si] <= 0
			FaceArmorLoadStatus = "MISSING stage " + si + " in " + FACE_STAGE_FILE
			SetCorpseDecayStatus("ERROR: " + FaceArmorLoadStatus)
			Debug.Notification("Pickman's Whisper: " + FACE_STAGE_FILE + " missing stage " + si)
			Debug.Trace("PickmansWhisper: ERROR " + FaceArmorLoadStatus)
			Return False
		EndIf
		si += 1
	EndWhile
	FaceArmorBanksLoaded = True
	FaceArmorLoadStatus = FaceArmorCount + " ARMOs / " + mapped + " stages"
	Debug.Trace("PickmansWhisper: decay face armor banks loaded — " + FaceArmorLoadStatus)
	Return True
EndFunction

Function StripDecayFaceArmors(Actor akCorpse)
	If !akCorpse || FaceArmorCount <= 0
		Return
	EndIf
	Int i = 0
	While i < FaceArmorCount
		Form f = Game.GetFormFromFile(FaceArmorArmoFids[i], PLUGIN_PW)
		If f
			Int n = akCorpse.GetItemCount(f)
			If n > 0
				akCorpse.UnequipItem(f, False, True)
				akCorpse.RemoveItem(f, n, True)
			EndIf
		EndIf
		i += 1
	EndWhile
EndFunction

; Equip playable slot-54 face decal for ModConfig stage. Removable (abPreventRemoval=false).
Bool Function ApplyDecayFaceArmorForStage(Actor akCorpse, Int aiStage)
	If !akCorpse
		SetCorpseDecayStatus("skip: no corpse for face armor")
		Return False
	EndIf
	If aiStage < 0 || aiStage >= DECAY_STAGE_COUNT
		SetCorpseDecayStatus("ERROR: face armor stage index " + aiStage)
		Debug.Trace("PickmansWhisper: ERROR ApplyDecayFaceArmorForStage — bad stage " + aiStage)
		Return False
	EndIf
	If !EnsureDecayFaceArmorBanks()
		Return False
	EndIf
	Int fid = FaceStageArmoFids[aiStage]
	If fid <= 0
		SetCorpseDecayStatus("ERROR: no face ARMO FormID for stage " + aiStage)
		Debug.Notification("Pickman's Whisper: no face ARMO for decay stage " + aiStage)
		Debug.Trace("PickmansWhisper: ERROR ApplyDecayFaceArmorForStage — fid 0 stage " + aiStage)
		Return False
	EndIf
	Form armor = Game.GetFormFromFile(fid, PLUGIN_PW)
	If !armor
		SetCorpseDecayStatus("ERROR: GetFormFromFile face ARMO 0x" + fid + " failed")
		Debug.Notification("Pickman's Whisper: face ARMO FormID missing — rebuild ESP")
		Debug.Trace("PickmansWhisper: ERROR ApplyDecayFaceArmorForStage GetFormFromFile fid=" + fid)
		Return False
	EndIf
	StripDecayFaceArmors(akCorpse)
	akCorpse.AddItem(armor, 1, True)
	; Playable / removable — do not lock with abPreventRemoval.
	akCorpse.EquipItem(armor, False, True)
	; Dead actors often report IsEquipped=false even when the item is on them — trust inventory.
	Int held = akCorpse.GetItemCount(armor)
	If held <= 0
		SetCorpseDecayStatus("ERROR: face ARMO AddItem failed stage " + aiStage + " fid=" + fid)
		Debug.Notification("Pickman's Whisper: face armor AddItem failed (stage " + aiStage + ")")
		Debug.Trace("PickmansWhisper: ERROR ApplyDecayFaceArmorForStage AddItem stage=" + aiStage + " fid=" + fid)
		Return False
	EndIf
	Bool worn = akCorpse.IsEquipped(armor)
	If !worn
		; Retry once — some corpses need a second EquipItem after AddItem.
		akCorpse.EquipItem(armor, False, True)
		worn = akCorpse.IsEquipped(armor)
	EndIf
	If worn
		SetCorpseDecayStatus("face ARMO stage " + aiStage + " fid=" + fid + " equipped")
		Debug.Trace("PickmansWhisper: decay face ARMO equipped stage=" + aiStage + " fid=" + fid)
	Else
		; Inventory has it; visuals may still show. Do not fail the whole decay stage on IsEquipped.
		SetCorpseDecayStatus("face ARMO stage " + aiStage + " fid=" + fid + " in inventory (IsEquipped=0 on corpse)")
		Debug.Trace("PickmansWhisper: WARN decay face ARMO IsEquipped=0 on corpse stage=" + aiStage + " fid=" + fid + " count=" + held + " — kept (dead IsEquipped often lies)")
	EndIf
	Return True
EndFunction

Bool Function SoftLooksMenuReady()
	If !Game.IsPluginInstalled(PLUGIN_LOOKSMENU)
		SetCorpseDecayStatus("skip: LooksMenu.esp not installed")
		Debug.Notification("Pickman's Whisper: LooksMenu required for corpse decay overlays")
		Debug.Trace("PickmansWhisper: ERROR LooksMenu.esp missing — decay overlays skipped")
		Return False
	EndIf
	Return True
EndFunction

Bool Function SoftDepsReady()
	If !SoftLooksMenuReady()
		Return False
	EndIf
	If !Game.IsPluginInstalled(PLUGIN_DEAD_OVERLAYS)
		SetCorpseDecayStatus("skip: INVB_OverlayFramework_DeadOverlays.esp not installed")
		Debug.Notification("Pickman's Whisper: ROF DeadOverlays required for corpse decay")
		Debug.Trace("PickmansWhisper: ERROR DeadOverlays.esp missing — decay overlays skipped")
		Return False
	EndIf
	Return True
EndFunction

Bool Function SoftSkinDepsReady()
	If !SoftLooksMenuReady()
		Return False
	EndIf
	If !Game.IsPluginInstalled(PLUGIN_PORC_OVERLAYS)
		SetCorpseDecayStatus("skip: porcOverlays.esl not installed")
		Debug.Notification("Pickman's Whisper: Porcupine Skin Overlays (porcOverlays.esl) required")
		Debug.Trace("PickmansWhisper: ERROR porcOverlays.esl missing — skin overlays skipped")
		Return False
	EndIf
	Return True
EndFunction

; Soft dep Scripted Face Tints — same path SFT itself uses: GoE2 FULL-name lookup + ChangeHeadPart.
; Sex FormLists filter so we do not slap male HDPTs onto female lab corpses (and vice versa).
Bool Function IsFemaleActor(Actor akActor)
	If !akActor
		Return False
	EndIf
	ActorBase base = akActor.GetLeveledActorBase()
	If !base
		Return True
	EndIf
	Return base.GetSex() == 1
EndFunction

FormList Function SoftSFTDamageList(Actor akActor)
	If !Game.IsPluginInstalled(PLUGIN_SFT)
		Return None
	EndIf
	Int fid = FID_SFT_DAMAGE_F
	If akActor && !IsFemaleActor(akActor)
		fid = FID_SFT_DAMAGE_M
	EndIf
	Return Game.GetFormFromFile(fid, PLUGIN_SFT) as FormList
EndFunction

Bool Function SoftFaceDepsReady()
	If !Game.IsPluginInstalled(PLUGIN_SFT)
		SetCorpseDecayStatus("skip: SFT.esp not installed")
		Debug.Notification("Pickman's Whisper: Scripted Face Tints (SFT.esp) required for face lab")
		Debug.Trace("PickmansWhisper: ERROR SFT.esp missing — face lab skipped")
		Return False
	EndIf
	FormList fl = Game.GetFormFromFile(FID_SFT_DAMAGE_F, PLUGIN_SFT) as FormList
	If !fl || fl.GetSize() <= 0
		SetCorpseDecayStatus("skip: SFT_Damage FormList missing")
		Debug.Notification("Pickman's Whisper: SFT_Damage FormList missing — check SFT.esp")
		Debug.Trace("PickmansWhisper: ERROR SFT_Damage FormList 0x8D missing/empty")
		Return False
	EndIf
	Return True
EndFunction

; Resolve Boxer/Damage HDPTs the way SFT does (GoE2 FULL name → HeadPart[]).
; Prefer sex FormList membership; if none match, apply all GoE hits (SFT default).
HeadPart[] Function ResolveSFTHeadParts(Actor akActor, String tintName)
	If !tintName || tintName == ""
		Return None
	EndIf
	HeadPart[] found = GardenOfEden2.GetHeadPartsByFullName(tintName)
	If !found || found.Length <= 0
		Return None
	EndIf
	FormList fl = SoftSFTDamageList(akActor)
	If !fl
		Return found
	EndIf
	Int matchCount = 0
	Int i = 0
	While i < found.Length
		If found[i] && fl.HasForm(found[i])
			matchCount += 1
		EndIf
		i += 1
	EndWhile
	If matchCount <= 0
		; GoE can return both sexes for one FULL name — prefer FormList filter, else SFT-style apply-all.
		Return found
	EndIf
	HeadPart[] matched = new HeadPart[matchCount]
	Int w = 0
	i = 0
	While i < found.Length
		If found[i] && fl.HasForm(found[i])
			matched[w] = found[i]
			w += 1
		EndIf
		i += 1
	EndWhile
	Return matched
EndFunction

; ChangeHeadPart often no-ops visually on already-dead PlaceAtMe corpses — briefly revive, apply, re-kill.
Function PrepareActorForSFTFace(Actor akActor)
	If !akActor
		Return
	EndIf
	If akActor.IsDead()
		akActor.Resurrect()
	EndIf
	If akActor.IsDisabled()
		akActor.Enable(False)
	EndIf
	; Let 3D settle after revive (skipped while MCM open — Wait freezes in menus).
	If !Utility.IsInMenuMode()
		Utility.Wait(0.15)
	EndIf
EndFunction

Function FinalizeActorAfterSFTFace(Actor akActor, Bool abWasDead)
	If !akActor
		Return
	EndIf
	; Facegen rebuild (F4SE QueueUpdate first arg = facegen).
	akActor.QueueUpdate(True, 0)
	If !Utility.IsInMenuMode()
		Utility.Wait(0.25)
	EndIf
	If abWasDead && !akActor.IsDead()
		PickmansWhisperMainQuestScript m = Main()
		If m
			m.SetKnifeKillCreditSuppressed(True)
		EndIf
		Actor player = Game.GetPlayer()
		If player
			akActor.KillSilent(player)
		Else
			akActor.KillSilent()
		EndIf
		If m
			m.SetKnifeKillCreditSuppressed(False)
			m.NoteBackgroundDead(akActor.GetFormID())
		EndIf
	EndIf
EndFunction

Int Function ChangeSFTHeadParts(Actor akActor, HeadPart[] parts, Bool abRemove)
	Int applied = 0
	If !akActor || !parts
		Return 0
	EndIf
	Int i = 0
	While i < parts.Length
		If parts[i]
			If abRemove
				akActor.ChangeHeadPart(parts[i], True, True)
			Else
				akActor.ChangeHeadPart(parts[i], False, False)
			EndIf
			applied += 1
		EndIf
		i += 1
	EndWhile
	Return applied
EndFunction

Bool Function ApplySFTDamageHeadPart(Actor akActor, String tintName)
	If !akActor
		Return False
	EndIf
	HeadPart[] parts = ResolveSFTHeadParts(akActor, tintName)
	If !parts || parts.Length <= 0
		SetCorpseDecayStatus("ERROR: GoE2 no HeadPart for FULL name: " + tintName)
		Debug.Notification("Pickman's Whisper: SFT face name not found — " + tintName)
		Debug.Trace("PickmansWhisper: ERROR GetHeadPartsByFullName empty — " + tintName)
		Return False
	EndIf
	Bool wasDead = akActor.IsDead()
	PrepareActorForSFTFace(akActor)
	Int n = ChangeSFTHeadParts(akActor, parts, False)
	FinalizeActorAfterSFTFace(akActor, wasDead)
	If n <= 0
		SetCorpseDecayStatus("ERROR: ChangeHeadPart applied 0 for " + tintName)
		Return False
	EndIf
	Return True
EndFunction

Function RemoveAllSFTDamageHeadParts(Actor akActor)
	FormList fl = SoftSFTDamageList(akActor)
	If !fl || !akActor
		Return
	EndIf
	Bool wasDead = akActor.IsDead()
	PrepareActorForSFTFace(akActor)
	Int n = fl.GetSize()
	Int i = 0
	While i < n
		HeadPart hp = fl.GetAt(i) as HeadPart
		If hp
			akActor.ChangeHeadPart(hp, True, True)
		EndIf
		i += 1
	EndWhile
	FinalizeActorAfterSFTFace(akActor, wasDead)
EndFunction

Bool Function TemplateInBank(String templateId, String[] bank, Int bankCount)
	If !templateId || templateId == "" || !bank || bankCount <= 0
		Return False
	EndIf
	Int i = 0
	While i < bankCount
		If bank[i] == templateId
			Return True
		EndIf
		i += 1
	EndWhile
	Return False
EndFunction

; Remove only overlays whose template is in bank — keeps the other bank stacked.
Function RemoveMatchingOverlays(Actor akCorpse, Bool abFemale, String[] bank, Int bankCount)
	If !akCorpse || !bank || bankCount <= 0
		Return
	EndIf
	Overlays:Entry[] all = Overlays.GetAll(akCorpse, abFemale)
	If !all
		Return
	EndIf
	Int i = 0
	While i < all.Length
		If TemplateInBank(all[i].template, bank, bankCount)
			Overlays.Remove(akCorpse, abFemale, all[i].uid)
		EndIf
		i += 1
	EndWhile
EndFunction

; LooksMenu tinted add — brighter/lighter than AddEntry's zeroed rgba.
Int Function AddTintedOverlay(Actor akCorpse, String templateId, Float afR, Float afG, Float afB, Float afA, Bool abFemale, Int aiPriority)
	Overlays:Entry overlay = new Overlays:Entry
	overlay.priority = aiPriority
	overlay.template = templateId
	overlay.red = afR
	overlay.green = afG
	overlay.blue = afB
	overlay.alpha = afA
	overlay.offset_u = 0.0
	overlay.offset_v = 0.0
	overlay.scale_u = 1.0
	overlay.scale_v = 1.0
	Return Overlays.Add(akCorpse, abFemale, overlay)
EndFunction

; Compat name for wound path.
Int Function AddTintedWoundOverlay(Actor akCorpse, String templateId, Float afR, Float afG, Float afB, Float afA, Bool abFemale)
	Return AddTintedOverlay(akCorpse, templateId, afR, afG, afB, afA, abFemale, WOUND_PRIORITY)
EndFunction

Function PrepareCorpseForOverlays(Actor akCorpse)
	If akCorpse.IsDisabled()
		akCorpse.Enable(False)
	EndIf
	akCorpse.SetGhost(False)
EndFunction

; Apply one template aiCount times. Clears only templates in clearBank (stack-safe).
Function ApplyTintedTemplateN(Actor akCorpse, String templateId, Int aiCount, Float afR, Float afG, Float afB, Float afA, Int aiPriority, String[] clearBank, Int clearCount, String statusPrefix)
	If !akCorpse
		SetCorpseDecayStatus("skip: no corpse")
		Return
	EndIf
	If !templateId || templateId == ""
		SetCorpseDecayStatus("skip: empty overlay template")
		Return
	EndIf
	PrepareCorpseForOverlays(akCorpse)
	Bool isFemale = IsFemaleActor(akCorpse)
	RemoveMatchingOverlays(akCorpse, isFemale, clearBank, clearCount)
	Int n = aiCount
	If n < 1
		n = 1
	ElseIf n > 16
		n = 16
	EndIf
	Int applied = 0
	Int lastUid = -1
	Int i = 0
	While i < n
		lastUid = AddTintedOverlay(akCorpse, templateId, afR, afG, afB, afA, isFemale, aiPriority)
		If lastUid > 0
			applied += 1
		EndIf
		i += 1
	EndWhile
	Overlays.Update(akCorpse)
	; Wait freezes while MCM is open — skip so CallFunction apply finishes in-menu.
	If !Utility.IsInMenuMode()
		Utility.Wait(0.1)
		Overlays.Update(akCorpse)
	EndIf
	String sexLabel = "F"
	If !isFemale
		sexLabel = "M"
	EndIf
	SetCorpseDecayStatus(statusPrefix + " " + applied + "/" + n + "x " + templateId + " sex=" + sexLabel + " uid=" + lastUid + " a=" + afA)
EndFunction

Function ApplyTintedAllTemplates(Actor akCorpse, String[] templates, Int aiTemplateCount, Int aiTimesEach, Float afR, Float afG, Float afB, Float afA, Int aiPriority, String statusPrefix, Bool abClearMatching = True)
	If !akCorpse
		SetCorpseDecayStatus("skip: no corpse")
		Return
	EndIf
	If !templates || aiTemplateCount <= 0
		SetCorpseDecayStatus("skip: empty overlay bank")
		Return
	EndIf
	PrepareCorpseForOverlays(akCorpse)
	Bool isFemale = IsFemaleActor(akCorpse)
	If abClearMatching
		RemoveMatchingOverlays(akCorpse, isFemale, templates, aiTemplateCount)
	EndIf
	Int times = aiTimesEach
	If times < 1
		times = 1
	ElseIf times > 4
		times = 4
	EndIf
	Int applied = 0
	Int lastUid = -1
	Int t = 0
	While t < aiTemplateCount
		String templateId = templates[t]
		If templateId != ""
			Int i = 0
			While i < times
				lastUid = AddTintedOverlay(akCorpse, templateId, afR, afG, afB, afA, isFemale, aiPriority)
				If lastUid > 0
					applied += 1
				EndIf
				i += 1
			EndWhile
		EndIf
		t += 1
	EndWhile
	Overlays.Update(akCorpse)
	; Wait freezes while MCM is open — skip so CallFunction apply finishes in-menu.
	If !Utility.IsInMenuMode()
		Utility.Wait(0.1)
		Overlays.Update(akCorpse)
	EndIf
	String sexLabel = "F"
	If !isFemale
		sexLabel = "M"
	EndIf
	String clearLabel = "cleared"
	If !abClearMatching
		clearLabel = "keep"
	EndIf
	SetCorpseDecayStatus(statusPrefix + " ALL " + applied + " (" + aiTemplateCount + "x" + times + ") " + clearLabel + " sex=" + sexLabel + " uid=" + lastUid + " a=" + afA)
EndFunction

; P0.1 wound lab — clear wound bank only (keeps Porcupine skin overlays).
Function ApplyTintedWoundTemplateN(Actor akCorpse, String templateId, Int aiCount, Float afR, Float afG, Float afB, Float afA, String[] clearBank, Int clearCount)
	If !SoftDepsReady()
		Return
	EndIf
	ApplyTintedTemplateN(akCorpse, templateId, aiCount, afR, afG, afB, afA, WOUND_PRIORITY, clearBank, clearCount, "lab wound")
EndFunction

Function ApplyTintedAllWoundTemplates(Actor akCorpse, String[] templates, Int aiTemplateCount, Int aiTimesEach, Float afR, Float afG, Float afB, Float afA)
	If !SoftDepsReady()
		Return
	EndIf
	ApplyTintedAllTemplates(akCorpse, templates, aiTemplateCount, aiTimesEach, afR, afG, afB, afA, WOUND_PRIORITY, "lab wound")
EndFunction

; Remove Porcupine overlays whose template is in bank — keeps DeathMarks wounds.
Function ClearSkinBankOverlays(Actor akCorpse, String[] bank, Int bankCount)
	If !akCorpse
		Return
	EndIf
	If !SoftSkinDepsReady()
		Return
	EndIf
	PrepareCorpseForOverlays(akCorpse)
	RemoveMatchingOverlays(akCorpse, IsFemaleActor(akCorpse), bank, bankCount)
	Overlays.Update(akCorpse)
EndFunction

; Drop every LooksMenu overlay before Disable/Delete — heavy stage stacks can stall MCM CallFunction on Clear/Spawn.
Function StripAllOverlaysForActor(Actor akCorpse)
	If !akCorpse
		Return
	EndIf
	If !Game.IsPluginInstalled(PLUGIN_LOOKSMENU)
		Return
	EndIf
	Bool isFemale = IsFemaleActor(akCorpse)
	Overlays.RemoveAll(akCorpse, isFemale)
	; Also clear the other sex slot if anything was mis-tagged (cheap; Delete is worse).
	Overlays.RemoveAll(akCorpse, !isFemale)
	Overlays.Update(akCorpse)
EndFunction

; P0.2 skin lab — Porcupine Scars/SkinTexture; clear skin bank only (keeps wounds).
Function ApplyTintedSkinTemplateN(Actor akCorpse, String templateId, Int aiCount, Float afR, Float afG, Float afB, Float afA, String[] clearBank, Int clearCount)
	If !SoftSkinDepsReady()
		Return
	EndIf
	ApplyTintedTemplateN(akCorpse, templateId, aiCount, afR, afG, afB, afA, SKIN_PRIORITY, clearBank, clearCount, "lab skin")
EndFunction

Function ApplyTintedAllSkinTemplates(Actor akCorpse, String[] templates, Int aiTemplateCount, Int aiTimesEach, Float afR, Float afG, Float afB, Float afA)
	If !SoftSkinDepsReady()
		Return
	EndIf
	ApplyTintedAllTemplates(akCorpse, templates, aiTemplateCount, aiTimesEach, afR, afG, afB, afA, SKIN_PRIORITY, "lab skin", True)
EndFunction

; Additive Porcupine apply — never RemoveMatchingOverlays (keeps SkinTexture_* already on the body).
Function ApplyTintedAllSkinTemplatesKeepExisting(Actor akCorpse, String[] templates, Int aiTemplateCount, Int aiTimesEach, Float afR, Float afG, Float afB, Float afA)
	If !SoftSkinDepsReady()
		Return
	EndIf
	ApplyTintedAllTemplates(akCorpse, templates, aiTemplateCount, aiTimesEach, afR, afG, afB, afA, SKIN_PRIORITY, "lab skin", False)
EndFunction

; Face lab — SFT Damage / Boxer headparts (DecayFaceOverlays.txt FULL names).
; Tint RGB unused (baked headpart materials — cannot share LooksMenu overlay tint).
; clearCount > 0 clears all SFT Damage headparts before apply (one revive cycle).
Function ApplyTintedFaceTemplateN(Actor akCorpse, String templateId, Int aiCount, Float afR, Float afG, Float afB, Float afA, String[] clearBank, Int clearCount)
	If !akCorpse
		SetCorpseDecayStatus("skip: no corpse")
		Return
	EndIf
	If !templateId || templateId == ""
		SetCorpseDecayStatus("skip: empty face template")
		Return
	EndIf
	If !SoftFaceDepsReady()
		Return
	EndIf
	PrepareCorpseForOverlays(akCorpse)
	HeadPart[] parts = ResolveSFTHeadParts(akCorpse, templateId)
	If !parts || parts.Length <= 0
		SetCorpseDecayStatus("ERROR: GoE2 no HeadPart for FULL name: " + templateId)
		Debug.Notification("Pickman's Whisper: SFT face name not found — " + templateId)
		Debug.Trace("PickmansWhisper: ERROR GetHeadPartsByFullName empty — " + templateId)
		Return
	EndIf
	Bool wasDead = akCorpse.IsDead()
	PrepareActorForSFTFace(akCorpse)
	If clearCount > 0
		FormList fl = SoftSFTDamageList(akCorpse)
		If fl
			Int n = fl.GetSize()
			Int i = 0
			While i < n
				HeadPart hp = fl.GetAt(i) as HeadPart
				If hp
					akCorpse.ChangeHeadPart(hp, True, True)
				EndIf
				i += 1
			EndWhile
		EndIf
	EndIf
	Int changed = ChangeSFTHeadParts(akCorpse, parts, False)
	FinalizeActorAfterSFTFace(akCorpse, wasDead)
	If changed > 0
		SetCorpseDecayStatus("lab face SFT ok " + templateId + " x" + changed + " (GoE2+revive+QueueUpdate)")
	Else
		SetCorpseDecayStatus("ERROR: ChangeHeadPart applied 0 for " + templateId)
		Debug.Notification("Pickman's Whisper: SFT face apply failed — " + templateId)
	EndIf
EndFunction

Function ApplyTintedAllFaceTemplates(Actor akCorpse, String[] templates, Int aiTemplateCount, Int aiTimesEach, Float afR, Float afG, Float afB, Float afA)
	If !akCorpse
		SetCorpseDecayStatus("skip: no corpse")
		Return
	EndIf
	If !templates || aiTemplateCount <= 0
		SetCorpseDecayStatus("skip: empty face bank")
		Return
	EndIf
	If !SoftFaceDepsReady()
		Return
	EndIf
	PrepareCorpseForOverlays(akCorpse)
	; One revive cycle: clear all Damage, apply every bank FULL name, then re-kill once.
	Bool wasDead = akCorpse.IsDead()
	PrepareActorForSFTFace(akCorpse)
	FormList fl = SoftSFTDamageList(akCorpse)
	If fl
		Int n = fl.GetSize()
		Int i = 0
		While i < n
			HeadPart hp = fl.GetAt(i) as HeadPart
			If hp
				akCorpse.ChangeHeadPart(hp, True, True)
			EndIf
			i += 1
		EndWhile
	EndIf
	Int applied = 0
	Int t = 0
	While t < aiTemplateCount
		String templateId = templates[t]
		If templateId != ""
			HeadPart[] parts = ResolveSFTHeadParts(akCorpse, templateId)
			If parts && ChangeSFTHeadParts(akCorpse, parts, False) > 0
				applied += 1
			EndIf
		EndIf
		t += 1
	EndWhile
	FinalizeActorAfterSFTFace(akCorpse, wasDead)
	SetCorpseDecayStatus("lab face SFT ALL " + applied + "/" + aiTemplateCount + " (GoE2 Boxer)")
EndFunction

; Apply up to aiCount random DeathMarks wound templates; then Overlays.Update.
Function ApplyDecayWoundOverlays(Actor akCorpse, Int aiCount)
	ApplyDecayWoundOverlaysTinted(akCorpse, aiCount, WOUND_TINT_R, WOUND_TINT_G, WOUND_TINT_B, WOUND_TINT_A)
EndFunction

Function ApplyDecayWoundOverlaysTinted(Actor akCorpse, Int aiCount, Float afR, Float afG, Float afB, Float afA)
	If !akCorpse
		SetCorpseDecayStatus("skip: no corpse")
		Return
	EndIf
	If !SoftDepsReady()
		Return
	EndIf
	If !EnsureWoundBank()
		Return
	EndIf
	Int n = aiCount
	If n < 1
		n = 1
	ElseIf n > 8
		n = 8
	EndIf
	If n > WoundTemplateCount
		n = WoundTemplateCount
	EndIf
	Int applied = 0
	Int guard = 0
	While applied < n && guard < 24
		Int pick = Utility.RandomInt(0, WoundTemplateCount - 1)
		String templateId = WoundTemplates[pick]
		If templateId != ""
			AddTintedWoundOverlay(akCorpse, templateId, afR, afG, afB, afA, True)
			applied += 1
		EndIf
		guard += 1
	EndWhile
	Overlays.Update(akCorpse)
	SetCorpseDecayStatus("wounds " + applied + "/" + n + " tint a=" + afA + " from " + WOUND_FILE)
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

; ModConfig decayStageN SkinTextures (+ scars if flagged) at stage RGBA. Soft deps; fail loud.
Bool Function ApplyDecayStageOverlays(Actor akCorpse, Int aiStage)
	If !akCorpse
		SetCorpseDecayStatus("skip: no corpse")
		Return False
	EndIf
	PickmansWhisperMainQuestScript m = Main()
	If !m
		SetCorpseDecayStatus("ERROR: Main script missing — cannot apply decay stage")
		Return False
	EndIf
	If !m.DecayStagesReady()
		m.LoadModConfig()
	EndIf
	If !m.DecayStagesReady()
		SetCorpseDecayStatus("ERROR: ModConfig decayStage0..4 — " + m.ModConfigLoadStatus)
		Debug.Notification("Pickman's Whisper: decay stages not loaded — check ModConfig.txt")
		Debug.Trace("PickmansWhisper: ERROR ApplyDecayStageOverlays — " + LastCorpseDecayStatus)
		Return False
	EndIf
	If aiStage < 0 || aiStage >= 5
		SetCorpseDecayStatus("ERROR: decay stage index " + aiStage)
		Return False
	EndIf
	; Body LooksMenu overlays FIRST, face ARMO LAST.
	; Overlays.Update (clear/add skins) unequips slot-54 face decals — that looked like
	; "face changed once, then snapped back" when face was applied before the body pass.
	Float tintR = m.GetDecayStageTintR(aiStage)
	Float tintG = m.GetDecayStageTintG(aiStage)
	Float tintB = m.GetDecayStageTintB(aiStage)
	Float tintA = m.GetDecayStageTintA(aiStage)
	String stageName = m.GetDecayStageName(aiStage)
	Bool bodyOk = False
	String bodyStatus = ""
	Int skinCount = 0
	Int scarCount = 0
	If !EnsureSkinBank()
		bodyStatus = LastCorpseDecayStatus
	ElseIf !SoftSkinDepsReady()
		bodyStatus = LastCorpseDecayStatus
	Else
		String[] stageBank = new String[64]
		Int n = 0
		String[] skins = new String[8]
		skinCount = m.FillDecayStageSkins(aiStage, skins)
		Int s = 0
		While s < skinCount
			If skins[s] != ""
				stageBank[n] = skins[s]
				n += 1
			EndIf
			s += 1
		EndWhile
		If m.GetDecayStageAllScars(aiStage)
			Int i = 0
			While i < SkinTemplateCount
				String id = SkinTemplates[i]
				If IsScarSkinTemplate(id)
					stageBank[n] = id
					n += 1
					scarCount += 1
				EndIf
				i += 1
			EndWhile
		EndIf
		If n <= 0
			bodyStatus = "empty skin bank"
			Debug.Notification("Pickman's Whisper: empty decay stage bank — " + stageName)
			Debug.Trace("PickmansWhisper: ERROR ApplyDecayStageOverlays empty skin bank stage=" + aiStage)
		Else
			; Wipe prior Porcupine Scars/SkinTexture so stage tint swaps (0–2 share SkinTexture_07).
			ClearSkinBankOverlays(akCorpse, SkinTemplates, SkinTemplateCount)
			ApplyTintedAllSkinTemplatesKeepExisting(akCorpse, stageBank, n, 1, tintR, tintG, tintB, tintA)
			bodyOk = True
			bodyStatus = LastCorpseDecayStatus
		EndIf
	EndIf

	; Slice I face decal — after LooksMenu Updates so it is not stripped.
	If !ApplyDecayFaceArmorForStage(akCorpse, aiStage)
		Return False
	EndIf
	String faceStatus = LastCorpseDecayStatus
	If bodyOk
		SetCorpseDecayStatus("stage " + aiStage + " " + stageName + " skins=" + skinCount + " scars=" + scarCount + " a=" + tintA + " | " + faceStatus + " | " + bodyStatus)
		Return True
	EndIf
	; Face stuck; stamp success so WorldScan does not Strip+retry every sync (face thrash).
	SetCorpseDecayStatus("stage " + aiStage + " " + stageName + " face ok | body skipped — " + bodyStatus)
	Debug.Notification("Pickman's Whisper: body decay skipped — " + bodyStatus)
	Debug.Trace("PickmansWhisper: WARN ApplyDecayStageOverlays body skipped — " + LastCorpseDecayStatus)
	Return True
EndFunction

; Slice H P2 — re-apply ModConfig stage if stamped knife kill advanced. Trace only.
Function SyncDecayForKnifeCorpse(Actor akCorpse)
	If !akCorpse
		Return
	EndIf
	PickmansWhisperMainQuestScript m = Main()
	If !m
		Return
	EndIf
	Int formId = akCorpse.GetFormID()
	If formId == 0 || m.FindDecayKillSlot(formId) < 0
		Return
	EndIf
	If !m.DecayStagesReady()
		m.LoadModConfig()
	EndIf
	If !m.DecayStagesReady()
		SetCorpseDecayStatus("ERROR: ModConfig decayStage0..4 — " + m.ModConfigLoadStatus)
		Debug.Trace("PickmansWhisper: ERROR SyncDecayForKnifeCorpse — " + LastCorpseDecayStatus)
		Return
	EndIf
	Int stage = m.ResolveDecayStageForKill(formId)
	If stage < 0
		Return
	EndIf
	Int last = m.GetDecayKillLastStage(formId)
	If stage == last
		Return
	EndIf
	If ApplyDecayStageOverlays(akCorpse, stage)
		m.SetDecayKillLastStage(formId, stage)
		SetCorpseDecayStatus("knife sync stage " + stage + " " + m.GetDecayStageName(stage) + " | " + LastCorpseDecayStatus)
	EndIf
EndFunction

; Bed gift present (deferred timer): darkened DeathMarks then Black Putrefaction stage.
; Safe to call after Present finishes — must not run inside Present/SleepStop/MCM Force sync.
Function ApplyBedGiftDecayOverlays(Actor akCorpse)
	If !akCorpse
		SetCorpseDecayStatus("skip: no corpse")
		Return
	EndIf
	PickmansWhisperMainQuestScript m = Main()
	If !m
		SetCorpseDecayStatus("ERROR: Main script missing — bed overlays skipped")
		Debug.Trace("PickmansWhisper: ERROR ApplyBedGiftDecayOverlays — Main missing")
		Return
	EndIf
	If !m.DecayStagesReady()
		m.LoadModConfig()
	EndIf
	Float woundA = m.GetBedGiftWoundAlpha()
	Int stage = BED_GIFT_DECAY_STAGE
	String woundStatus = ""
	If m.DecayStagesReady() && woundA >= 0.0
		; DeathMarks first; darken via stage RGB, opacity from ModConfig.
		ApplyDecayWoundOverlaysTinted(akCorpse, BED_GIFT_WOUND_COUNT, m.GetDecayStageTintR(stage), m.GetDecayStageTintG(stage), m.GetDecayStageTintB(stage), woundA)
		woundStatus = LastCorpseDecayStatus
		ApplyDecayStageOverlays(akCorpse, stage)
		SetCorpseDecayStatus("bed gift | " + woundStatus + " | " + LastCorpseDecayStatus)
		Return
	EndIf
	; Stage/alpha incomplete — still apply P1 DeathMarks so the vignette is not bare; fail loud.
	If !m.DecayStagesReady()
		Debug.Notification("Pickman's Whisper: bed gift decay stages missing — wounds only; check ModConfig.txt")
		Debug.Trace("PickmansWhisper: ERROR bed gift stage skip — " + m.ModConfigLoadStatus)
	ElseIf woundA < 0.0
		Debug.Notification("Pickman's Whisper: bedGiftWoundAlpha missing — pale wounds only; check ModConfig.txt")
		Debug.Trace("PickmansWhisper: ERROR bed gift wound alpha missing")
	EndIf
	ApplyDecayWoundOverlays(akCorpse, BED_GIFT_WOUND_COUNT)
	SetCorpseDecayStatus("bed gift wounds-only fallback | " + LastCorpseDecayStatus)
EndFunction

Function DebugForceCorpseDecayOverlays()
	PickmansWhisperMainQuestScript m = Main()
	If !m
		Debug.MessageBox("Pickman's Whisper\n\nMain script missing.")
		Return
	EndIf
	Actor aimed = m.GetLookAimActor()
	If !aimed || aimed == Game.GetPlayer()
		Debug.MessageBox("Pickman's Whisper\n\nAim / face a corpse (or look then open MCM), then retry.")
		Return
	EndIf
	ApplyBedGiftDecayOverlays(aimed)
	Debug.MessageBox("Pickman's Whisper\n\nDecay overlays forced (bed gift path).\n" + LastCorpseDecayStatus)
EndFunction
