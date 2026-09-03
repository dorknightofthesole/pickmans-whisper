Scriptname PickmansWhisperCorpseDecayScript extends Quest
{Slice H — corpse decay visuals via LooksMenu overlays.}

; Soft deps (no ESP master): LooksMenu.esp + DeadOverlays / porcOverlays.esl / SFT.esp.
; Optional strip bank: CumOverlays.esp template ids (CumOverlayIds.txt) — PW never applies cum.
; Uses Overlays.Add (not AddEntry) so we can tint — AddEntry hardcodes rgba 0.
; Wound ids: DecayWoundOverlays.txt | Skin ids: DecaySkinOverlays.txt
; Face ids: DecayFaceOverlays.txt — SFT Damage FULL names (LooksMenu body overlays cannot paint faces).
; Slice I face decals: DecayFaceStages.txt (stage→color) + DecayFaceArmorIds.txt (color→ARMO FormID).

String PLUGIN_LOOKSMENU = "LooksMenu.esp"
String PLUGIN_DEAD_OVERLAYS = "INVB_OverlayFramework_DeadOverlays.esp"
String PLUGIN_PORC_OVERLAYS = "porcOverlays.esl"
String PLUGIN_SFT = "SFT.esp"
String PLUGIN_TATTOOS = "SlaveTattoos.esp"
String PLUGIN_PW = "PickmansWhisper.esp"
; Cut Off Tits — slot-33 body ARMO + weighted MISC prop (builder FormIDs; contract-locked).
Int FID_MUTILATED_BODY_ARMO = 0x0000087D
Int FID_CUT_OFF_TITS_MISC = 0x0000087E
Int CUT_OFF_TITS_ONCE_MAX = 32
Float CUT_OFF_TITS_PROP_OFFSET_XY = 64.0
Float CUT_OFF_TITS_PROP_OFFSET_Z = 6.0
; SFT.esp FormLists of Damage / Boxer headparts (female / male). Soft dep — no ESP master.
Int FID_SFT_DAMAGE_F = 0x000008D ; SFT_Damage
Int FID_SFT_DAMAGE_M = 0x00000B2 ; SFT_Damage_M
String WOUND_FILE = "DecayWoundOverlays.txt"
String SKIN_FILE = "DecaySkinOverlays.txt"
String FACE_FILE = "DecayFaceOverlays.txt"
String FACE_STAGE_FILE = "DecayFaceStages.txt"
String FACE_ARMOR_IDS_FILE = "DecayFaceArmorIds.txt"
String CUM_FILE = "CumOverlayIds.txt"
String CONFIG_PATH = ".\\Data\\PickmansWhisper\\config\\"
String MOD_NAME = "PickmansWhisper"
Int BED_GIFT_WOUND_COUNT = 6 ; doubled for coverage / progression look-test (was 3)
; Bed gift applies ModConfig decayStage4 (Black Putrefaction) after DeathMarks wounds.
Int BED_GIFT_DECAY_STAGE = 4
Int WOUND_PRIORITY = 40
Int SKIN_PRIORITY = 30 ; under wounds so DeathMarks stay readable
Int TATTOO_PRIORITY = 20 ; under skin/wounds — tattoos are the base body-art layer
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
String[] CumTemplates
Int CumTemplateCount = 0
Bool CumBankLoaded = False
String[] FaceTemplates
Int FaceTemplateCount = 0
Bool FaceBankLoaded = False
; Captive Tattoos lab — multi-select: the player can set an item on any number of
; the 20 category chunks (not just one), and Apply applies every chunk that isn't
; left at its "(none)" default. Tracked per-chunk-index UID (not a bank clear) since
; the catalog is split across 20 chunk banks — no single array can hold every id to
; check membership against for a clear pass. Re-applying replaces exactly what this
; script itself applied last time (only for the same target); it never touches
; overlays it didn't add.
Actor LastTattooTarget = None
Int[] LastTattooUids
Int TATTOO_CHUNK_COUNT = 20
; Slice I — color label → local ARMO FormID (from DecayFaceArmorIds.txt).
String[] FaceArmorLabels
Int[] FaceArmorArmoFids
Int FaceArmorCount = 0
; Per ModConfig stage 0..4 — resolved ARMO local FormID (0 = missing).
Int[] FaceStageArmoFids
Bool FaceArmorBanksLoaded = False
String FaceArmorLoadStatus = ""
String Property LastCorpseDecayStatus = "" Auto

; Slice H P4 — eat-ripe nag cooldown (shared across all ripe corpses).
Float LastEatRipeCorpseToastGameTime = 0.0
Float EAT_RIPE_CORPSE_TOAST_MIN_GAME_HOURS = 1.0

; Slice H P5 — set by Cannibal heal MGEF (Main.HandlePlayerMagicEffectApply); claimed by
; MaybeRewardEatenRipeCorpse(akCorpse) from HandleCorpseDecay so the corpse is the one
; TargetScan already handed us (no KillerScan ScanDead). Idle ticks leave this False.
Bool PendingEatRipeReward = False

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

; CallFunctionNoWait + LooksMenu Utility.Wait re-enters this script — overlapping
; SyncOverlays thrashed LastStage / never finished stage 4 Black. One flight at a time.
Bool OverlaySyncBusy = False
Float OverlaySyncBusySince = 0.0
Float OVERLAY_SYNC_BUSY_MAX_SECONDS = 90.0
; REVERTED — tried periodically re-painting body skins on a per-corpse cooldown to
; self-heal since no LooksMenu call reports back "the overlay actually rendered."
; Confirmed it does NOT help: QueueUpdate still never composites a new body texture
; onto an already-loaded, never-disabled corpse — the retry just visibly flickered
; (Overlays.Add succeeding internally, LooksMenu.Update triggering a real mesh
; refresh pass) and then settled back to the base skin every time. Disable/Enable
; is the only thing that ever actually rendered it, and that was reverted for
; causing a fake re-kill (see ForceCorpseMeshRefresh above). Ambient body-texture
; decay is out of reach without a refresh method that doesn't touch the skeleton —
; same call as Bed Gift textures being "a stretch." Face masks + the decay clock
; are unaffected and keep working.
; MCM Set/Reset queues THIS actor — paint on menu close / next sync (no feature StartTimer).
Actor PendingAimedDecayActor = None
Actor PendingDismemberStripActor = None
; Session latch — Cut Off Tits applied once per corpse FormID (no second prop).
Int[] CutOffTitsDoneIds
Int CutOffTitsDoneCount = 0
Int AimedDecayApplyCode = 2 ; bump when apply path changes — prove PEX loaded in log

; Victims MCM Set/Reset moves the kill clock, then QueueAimedDecayApply paints that corpse
; after MCM closes. Ambient progression: TargetScan / RegisterTarget → HandleCorpseDecay.
; MCM harness: latch aimed corpse; kick NoWait if already out of menus, else OnMCMMenuClose.
Function QueueAimedDecayApply(Actor akCorpse)
	If !akCorpse
		Debug.Trace("PickmansWhisper: ERROR QueueAimedDecayApply — no corpse")
		Return
	EndIf
	PendingAimedDecayActor = akCorpse
	Debug.Trace("PickmansWhisper: QueueAimedDecayApply formId=" + akCorpse.GetFormID() + " code=" + AimedDecayApplyCode)
	If !Utility.IsInMenuMode()
		CallFunctionNoWait("RunPendingAimedDecayApply", None)
	EndIf
EndFunction

; Victims OnMCMMenuClose + optional out-of-menu Queue — LooksMenu must not run under MCM Wait freeze.
Function RunPendingAimedDecayApply()
	Actor ak = PendingAimedDecayActor
	If !ak
		Debug.Trace("PickmansWhisper: AimedDecayApply skip | no pending corpse")
		Return
	EndIf
	If Utility.IsInMenuMode()
		Debug.Trace("PickmansWhisper: AimedDecayApply defer | still in menu formId=" + ak.GetFormID())
		Return
	EndIf
	Float now = Utility.GetCurrentRealTime()
	; Real-time resets to ~0 on every new game process, but these are saved fields —
	; a stale value from a longer previous session makes (now - stale) negative,
	; permanently reading as "still within the window" for the rest of THIS session.
	If OverlaySyncBusySince > now
		OverlaySyncBusySince = 0.0
	EndIf
	If OverlaySyncBusy
		If (now - OverlaySyncBusySince) < OVERLAY_SYNC_BUSY_MAX_SECONDS
			Debug.Trace("PickmansWhisper: AimedDecayApply defer | OverlaySyncBusy formId=" + ak.GetFormID())
			Return
		EndIf
		Debug.Trace("PickmansWhisper: WARN AimedDecayApply force-clear OverlaySyncBusy after " + OVERLAY_SYNC_BUSY_MAX_SECONDS + "s")
		OverlaySyncBusy = False
	EndIf
	PendingAimedDecayActor = None
	OverlaySyncBusy = True
	OverlaySyncBusySince = now
	Int formId = ak.GetFormID()
	Debug.Trace("PickmansWhisper: AimedDecayApply begin formId=" + formId + " code=" + AimedDecayApplyCode)
	SyncDecayForKnifeCorpse(ak)
	OverlaySyncBusy = False
	PickmansWhisperMainQuestScript m = Main()
	If m
		WriteDecayStageStatusToMcmForActor(ak, False)
	EndIf
	Debug.Trace("PickmansWhisper: AimedDecayApply done formId=" + formId + " | " + LastCorpseDecayStatus)
EndFunction

; MCM Set/Reset queues via QueueAimedDecayApply; OnMCMMenuClose may fire RunPendingAimedDecayApply.
; Safety net: HandleCorpseDecay (TargetScan / RegisterTarget) drains pending when menus close.
Function CheckPendingAimedDecayApply()
	If !PendingAimedDecayActor || Utility.IsInMenuMode()
		Return
	EndIf
	Debug.Trace("PickmansWhisper: CheckPendingAimedDecayApply → RunPendingAimedDecayApply formId=" + PendingAimedDecayActor.GetFormID())
	RunPendingAimedDecayApply()
EndFunction

; Sole gameplay entry for knife-corpse decay check/apply (one Actor).
; Callers: Main.RegisterTarget (dead+blade) and TargetScan already-tracked dead — always
; CallFunctionNoWait so LooksMenu Utility.Wait never runs on the scan/register stack.
Function HandleCorpseDecay(Actor akCorpse)
	If !akCorpse
		Debug.Trace("PickmansWhisper: HandleCorpseDecay skip | no corpse")
		Return
	EndIf
	If !akCorpse.IsDead()
		Debug.Trace("PickmansWhisper: HandleCorpseDecay skip | not dead formId=" + akCorpse.GetFormID())
		Return
	EndIf
	If Utility.IsInMenuMode()
		Debug.Trace("PickmansWhisper: HandleCorpseDecay skip | in menu formId=" + akCorpse.GetFormID())
		Return
	EndIf
	; MCM Set left a pending aimed corpse — paint that one first.
	If PendingAimedDecayActor
		Debug.Trace("PickmansWhisper: HandleCorpseDecay → AimedDecayApply pending formId=" + PendingAimedDecayActor.GetFormID())
		CheckPendingAimedDecayApply()
		Return
	EndIf
	PickmansWhisperMainQuestScript m = Main()
	If !m
		Debug.Trace("PickmansWhisper: ERROR HandleCorpseDecay — Main missing")
		Return
	EndIf
	If !m.BondStarted
		Debug.Trace("PickmansWhisper: HandleCorpseDecay skip | not bonded")
		Return
	EndIf
	Actor player = Game.GetPlayer()
	If akCorpse == player || !akCorpse.Is3DLoaded() || akCorpse.IsDisabled()
		Debug.Trace("PickmansWhisper: HandleCorpseDecay skip | player/unloaded/disabled formId=" + akCorpse.GetFormID())
		Return
	EndIf
	Float now = Utility.GetCurrentRealTime()
	If OverlaySyncBusySince > now
		OverlaySyncBusySince = 0.0
	EndIf
	If OverlaySyncBusy
		If (now - OverlaySyncBusySince) < OVERLAY_SYNC_BUSY_MAX_SECONDS
			Debug.Trace("PickmansWhisper: HandleCorpseDecay skip | already running formId=" + akCorpse.GetFormID())
			Return
		EndIf
		Debug.Trace("PickmansWhisper: WARN HandleCorpseDecay OverlaySyncBusy force-clear after " + OVERLAY_SYNC_BUSY_MAX_SECONDS + "s")
		OverlaySyncBusy = False
	EndIf
	OverlaySyncBusy = True
	OverlaySyncBusySince = now
	Int id = akCorpse.GetFormID()
	Debug.Trace("PickmansWhisper: HandleCorpseDecay begin formId=" + id + " code=" + AimedDecayApplyCode)
	If id != 0 && FindDecayKillSlot(id) < 0
		EnsureDecayForTrackedVictim(akCorpse, False)
	EndIf
	If id != 0 && FindDecayKillSlot(id) >= 0
		SyncDecayForKnifeCorpse(akCorpse)
		If ResolveDecayStageForKill(id) == (DECAY_STAGE_COUNT - 1)
			MaybeToastEatRipeCorpse(akCorpse)
			MaybeRewardEatenRipeCorpse(akCorpse)
		EndIf
	Else
		Debug.Trace("PickmansWhisper: HandleCorpseDecay skip | no kill slot formId=" + id)
	EndIf
	OverlaySyncBusy = False
	Debug.Trace("PickmansWhisper: HandleCorpseDecay done formId=" + id + " | " + LastCorpseDecayStatus)
EndFunction

; Slice H P4 — Cannibal-perk nag at Black Putrefaction. Once-per-game-hour shared
; cooldown across all ripe corpses (not gated on stage-changed). Shared helpers via Main().
Function MaybeToastEatRipeCorpse(Actor akCorpse)
	If !akCorpse
		Return
	EndIf
	PickmansWhisperMainQuestScript m = Main()
	If !m
		Debug.Trace("PickmansWhisper: eat-ripe-corpse skip | Main missing")
		Return
	EndIf
	If !m.ModConfigAlias || !m.ModConfigAlias.EatRipeCorpseToast || GardenOfEden.StrLength(m.ModConfigAlias.EatRipeCorpseToast) < 1
		Debug.Trace("PickmansWhisper: eat-ripe-corpse skip | no eatRipeCorpseToast (ModConfig not loaded / key empty)")
		Return
	EndIf
	If !m.PlayerHasCannibalPerk()
		Debug.Trace("PickmansWhisper: eat-ripe-corpse skip | player lacks Cannibal perk")
		Return
	EndIf
	Float now = Utility.GetCurrentGameTime()
	If (now - LastEatRipeCorpseToastGameTime) < (EAT_RIPE_CORPSE_TOAST_MIN_GAME_HOURS / 24.0)
		Debug.Trace("PickmansWhisper: eat-ripe-corpse skip | cooldown formId=" + akCorpse.GetFormID())
		Return
	EndIf
	String overrideName = m.GetVictimOverrideName(akCorpse)
	If !overrideName
		overrideName = "her"
	EndIf
	If !m.VoiceAlias
		Debug.Trace("PickmansWhisper: eat-ripe-corpse skip | VoiceAlias unbound")
		Return
	EndIf
	String line = m.ApplyNamePlaceholder(m.ModConfigAlias.EatRipeCorpseToast, overrideName)
	If !line || GardenOfEden.StrLength(line) < 1
		Debug.Trace("PickmansWhisper: eat-ripe-corpse skip | empty line after placeholder")
		Return
	EndIf
	LastEatRipeCorpseToastGameTime = now
	; MessageBox — Notification was easy to miss under LooksMenu decay spam (confirmed live).
	Debug.MessageBox(line)
	Debug.Trace("PickmansWhisper: eat-ripe-corpse toast | " + line)
EndFunction

; Named/tracked victim with no decay clock → stamp Freshly Deceased.
; Kill registry lives on this script; Victims list stays on Main.
; abApplyOverlays=False from HandleCorpseDecay / MCM format; True for explicit apply paths.
Bool Function EnsureDecayForTrackedVictim(Actor ak, Bool abApplyOverlays = True)
	If !ak || !ak.IsDead()
		Return False
	EndIf
	Actor player = Game.GetPlayer()
	If ak == player
		Return False
	EndIf
	PickmansWhisperMainQuestScript m = Main()
	If !m
		Debug.Trace("PickmansWhisper: ERROR EnsureDecayForTrackedVictim — Main missing")
		Return False
	EndIf
	If m.IsNonGameplayCorpse(ak)
		Return False
	EndIf
	Int formId = ak.GetFormID()
	If formId == 0 || m.FindVictimSlot(formId) < 0
		Return False
	EndIf
	If FindDecayKillSlot(formId) >= 0
		Return False
	EndIf
	StampDecayKill(ak)
	; Never LooksMenu-apply from MCM / hot TargetScan — stalls voice + menu.
	If !abApplyOverlays || Utility.IsInMenuMode()
		Debug.Trace("PickmansWhisper: decay clock stamped (tracked victim, overlays deferred) id=0x" + GardenOfEden.GetHexFormID(ak))
		Return True
	EndIf
	SyncDecayForKnifeCorpse(ak)
	If GetDecayKillLastStage(formId) < 0
		Debug.Notification("Pickman's Whisper: Freshly Deceased overlays failed — " + LastCorpseDecayStatus)
		Debug.Trace("PickmansWhisper: ERROR EnsureDecayForTrackedVictim overlays pending id=0x" + GardenOfEden.GetHexFormID(ak) + " | " + LastCorpseDecayStatus)
	Else
		Debug.Trace("PickmansWhisper: decay clock + stage overlays started (tracked victim) id=0x" + GardenOfEden.GetHexFormID(ak) + " applied=" + GetDecayKillLastStage(formId))
	EndIf
	Return True
EndFunction


; Knife-kill decay registry (credited ProcessKnifeKill only). Cap + FIFO eviction.
Int DECAY_KILL_MAX = 32
Int[] DecayKillIds
Float[] DecayKillGameTime
Int[] DecayKillLastStage ; -1 = never applied
Int DecayKillSlotCount = 0

Int Function GetDecayKillSlotCount()
	EnsureDecayKillLists()
	Return DecayKillSlotCount
EndFunction


String Function FormatNoAimVictimsAimLine()
	EnsureDecayKillLists()
	If DecayKillSlotCount < 1
		Return ""
	EndIf
	Int lastId = DecayKillIds[DecayKillSlotCount - 1]
	String hexId = "" + lastId
	Form lastForm = Game.GetForm(lastId)
	If lastForm
		hexId = GardenOfEden.GetHexFormID(lastForm)
	EndIf
	Return "(no aim cache) last knife kill id=0x" + hexId
EndFunction


Function WriteDecayStageStatusToMcmForActor(Actor ak, Bool abSyncStepper = True)
	If !MCM.IsInstalled()
		Return
	EndIf
	If ak
		String line = FormatDecayStageStatusForActor(ak)
		MCM.SetModSettingString(MOD_NAME, "sDecayStage:Victims", line)
		Debug.Trace("PickmansWhisper: WriteDecayStageStatus aim id=0x" + GardenOfEden.GetHexFormID(ak) + " syncStepper=" + abSyncStepper + " | " + line)
		If abSyncStepper
			SyncVictimDecayStageStepper(ak.GetFormID())
		EndIf
		Return
	EndIf
	EnsureDecayKillLists()
	If DecayKillSlotCount > 0
		Int lastId = DecayKillIds[DecayKillSlotCount - 1]
		String line = FormatDecayStageStatusForFormId(lastId, "last kill") + " (no aim)"
		MCM.SetModSettingString(MOD_NAME, "sDecayStage:Victims", line)
		Debug.Trace("PickmansWhisper: WriteDecayStageStatus no-aim lastId=" + lastId + " syncStepper=" + abSyncStepper + " | " + line)
		If abSyncStepper
			SyncVictimDecayStageStepper(lastId)
		EndIf
		Return
	EndIf
	MCM.SetModSettingString(MOD_NAME, "sDecayStage:Victims", "(no aim / no knife kills tracked)")
	Debug.Trace("PickmansWhisper: WriteDecayStageStatus empty (no aim / no knife kills)")
EndFunction


Function EnsureDecayKillLists()
	If !DecayKillIds || DecayKillIds.Length != DECAY_KILL_MAX
		DecayKillIds = new Int[32]
		DecayKillGameTime = new Float[32]
		DecayKillLastStage = new Int[32]
		DecayKillSlotCount = 0
	EndIf
EndFunction


Int Function FindDecayKillSlot(Int formId)
	If formId == 0
		Return -1
	EndIf
	EnsureDecayKillLists()
	Int i = 0
	While i < DecayKillSlotCount
		If DecayKillIds[i] == formId
			Return i
		EndIf
		i += 1
	EndWhile
	Return -1
EndFunction


Function EvictOldestDecayKill()
	EnsureDecayKillLists()
	If DecayKillSlotCount <= 0
		Return
	EndIf
	Int j = 0
	While j < DecayKillSlotCount - 1
		DecayKillIds[j] = DecayKillIds[j + 1]
		DecayKillGameTime[j] = DecayKillGameTime[j + 1]
		DecayKillLastStage[j] = DecayKillLastStage[j + 1]
		j += 1
	EndWhile
	DecayKillSlotCount -= 1
EndFunction


Function StampDecayKill(Actor victim)
	If !victim
		Return
	EndIf
	Int formId = victim.GetFormID()
	If formId == 0
		Return
	EndIf
	EnsureDecayKillLists()
	Float now = Utility.GetCurrentGameTime()
	Int slot = FindDecayKillSlot(formId)
	If slot >= 0
		DecayKillGameTime[slot] = now
		DecayKillLastStage[slot] = -1
		Return
	EndIf
	If DecayKillSlotCount >= DECAY_KILL_MAX
		EvictOldestDecayKill()
	EndIf
	If DecayKillSlotCount >= DECAY_KILL_MAX
		Return
	EndIf
	DecayKillIds[DecayKillSlotCount] = formId
	DecayKillGameTime[DecayKillSlotCount] = now
	DecayKillLastStage[DecayKillSlotCount] = -1
	DecayKillSlotCount += 1
EndFunction


Float Function GetDecayKillGameTime(Int formId)
	Int slot = FindDecayKillSlot(formId)
	If slot < 0
		Return -1.0
	EndIf
	Return DecayKillGameTime[slot]
EndFunction


Int Function GetDecayKillLastStage(Int formId)
	Int slot = FindDecayKillSlot(formId)
	If slot < 0
		Return -1
	EndIf
	Return DecayKillLastStage[slot]
EndFunction


Function SetDecayKillLastStage(Int formId, Int aiStage)
	Int slot = FindDecayKillSlot(formId)
	If slot < 0
		Return
	EndIf
	DecayKillLastStage[slot] = aiStage
EndFunction


Function SyncVictimDecayStageStepper(Int formId)
	If !MCM.IsInstalled() || formId == 0
		Return
	EndIf
	If FindDecayKillSlot(formId) < 0
		Return
	EndIf
	PickmansWhisperMainQuestScript m = Main()
	If !m || !m.ModConfigAlias || !m.ModConfigAlias.DecayStagesReady()
		Return
	EndIf
	Int resolved = ResolveDecayStageForKill(formId)
	Int applied = GetDecayKillLastStage(formId)
	Int visual = resolved
	If visual < 0
		visual = applied
	EndIf
	If visual < 0
		visual = 0
	ElseIf visual > 4
		visual = 4
	EndIf
	MCM.SetModSettingInt(MOD_NAME, "iVictimDecayStage:Victims", visual)
EndFunction

Bool Function ForceDecayKillClockToStage(Int formId, Int aiStage)
	PickmansWhisperMainQuestScript m = Main()
	If !m || !m.ModConfigAlias || formId == 0 || aiStage < 0 || aiStage >= m.ModConfigAlias.DECAY_STAGE_COUNT
		Return False
	EndIf
	If !m.ModConfigAlias.DecayStagesReady()
		Return False
	EndIf
	Int slot = FindDecayKillSlot(formId)
	If slot < 0
		Return False
	EndIf
	Float needH = m.ModConfigAlias.GetDecayStageStartHours(aiStage)
	If needH < 0.0
		Return False
	EndIf
	; Subtract startHours from now. Tiny pad when > 0 so Float round-trip still
	; lands at/above the threshold (ResolveDecayStage uses elapsed >= startHours).
	Float elapsedH = needH
	If needH > 0.0
		elapsedH = needH + 0.001
	EndIf
	DecayKillGameTime[slot] = Utility.GetCurrentGameTime() - (elapsedH / 24.0)
	Return True
EndFunction

String Function FormatDecayStageStatusForFormId(Int formId, String label)
	If formId == 0 || FindDecayKillSlot(formId) < 0
		If label
			Return label + " — no decay clock (Name her, then Refresh)"
		EndIf
		Return "(no decay clocks yet)"
	EndIf
	If !label
		label = "kill"
	EndIf
	PickmansWhisperMainQuestScript m = Main()
	If !m || !m.ModConfigAlias || !m.ModConfigAlias.DecayStagesReady()
		Return label + " — ModConfig stages missing"
	EndIf
	Int stage = ResolveDecayStageForKill(formId)
	If stage < 0
		Return label + " — resolve failed"
	EndIf
	Float killTime = GetDecayKillGameTime(formId)
	Float elapsedH = (Utility.GetCurrentGameTime() - killTime) * 24.0
	If elapsedH < 0.0
		elapsedH = 0.0
	EndIf
	Int applied = GetDecayKillLastStage(formId)
	String stageName = m.ModConfigAlias.GetDecayStageName(stage)
	String line = stage + " " + stageName + " | " + elapsedH + "h"
	If applied < 0
		line = line + " | overlays pending"
	ElseIf applied != stage
		line = line + " | applied " + applied + " (stale)"
	Else
		line = line + " | applied " + applied
	EndIf
	Return line
EndFunction

String Function FormatDecayStageStatusForActor(Actor ak)
	If !ak
		Return "(face a corpse, then open MCM)"
	EndIf
	PickmansWhisperMainQuestScript m = Main()
	If !m
		Return "(Main missing)"
	EndIf
	If ak == m.PlayerRef
		Return "(player)"
	EndIf
	String label = ""
	If m.VoiceAlias
		label = m.VoiceAlias.GetActorDisplayName(ak)
	EndIf
	If !label
		label = "corpse"
	EndIf
	If !ak.IsDead()
		Return label + " — alive (decay starts when she dies)"
	EndIf
	; Stamp only while MCM open; overlays sync in-world after voice.
	EnsureDecayForTrackedVictim(ak, False)
	Return FormatDecayStageStatusForFormId(ak.GetFormID(), label)
EndFunction

Function WriteDecayStageStatusToMcm()
	PickmansWhisperMainQuestScript m = Main()
	Actor aimed = None
	If m
		aimed = m.ResolveVictimsAimActor()
	EndIf
	WriteDecayStageStatusToMcmForActor(aimed)
EndFunction

Int Function ResolveDecayStageForKill(Int formId)
	PickmansWhisperMainQuestScript m = Main()
	If !m || !m.ModConfigAlias || !m.ModConfigAlias.DecayStagesReady()
		Return -1
	EndIf
	Float killTime = GetDecayKillGameTime(formId)
	If killTime < 0.0
		Return -1
	EndIf
	Float elapsedHours = (Utility.GetCurrentGameTime() - killTime) * 24.0
	Return m.ModConfigAlias.ResolveDecayStageFromElapsedHours(elapsedHours)
EndFunction

; Latch from Main after RestoreHealthGeneric (Cannibal heal). HandleCorpseDecay claims it.
Function NotePendingEatRipeReward()
	PendingEatRipeReward = True
	Debug.Trace("PickmansWhisper: eaten-ripe-corpse pending | waiting for HandleCorpseDecay")
EndFunction

; Slice H P5 — reward one max-stage corpse after a pending Cannibal heal. Called from
; HandleCorpseDecay with that corpse (no KillerScan ScanDead / nearest search).
Function MaybeRewardEatenRipeCorpse(Actor akCorpse)
	If !PendingEatRipeReward
		Return
	EndIf
	If !akCorpse
		Debug.Trace("PickmansWhisper: eaten-ripe-corpse skip | no corpse")
		Return
	EndIf
	PickmansWhisperMainQuestScript m = Main()
	If !m || !m.PlayerRef || !m.PlayerHasCannibalPerk()
		PendingEatRipeReward = False
		Debug.Trace("PickmansWhisper: eaten-ripe-corpse skip | no Cannibal perk (heal was not from eating)")
		Return
	EndIf
	; Match Main BUTCHER_CORPSE_RADIUS (shared butcher/eat range).
	Float butcherR = 500.0
	If m.PlayerRef.GetDistance(akCorpse) > butcherR
		Debug.Trace("PickmansWhisper: eaten-ripe-corpse skip | corpse out of butcher range formId=" + akCorpse.GetFormID())
		Return
	EndIf
	Int formId = akCorpse.GetFormID()
	If FindDecayKillSlot(formId) < 0
		Debug.Trace("PickmansWhisper: eaten-ripe-corpse skip | corpse untracked formId=" + formId)
		Return
	EndIf
	If ResolveDecayStageForKill(formId) != (DECAY_STAGE_COUNT - 1)
		Debug.Trace("PickmansWhisper: eaten-ripe-corpse skip | corpse not max stage formId=" + formId)
		Return
	EndIf
	PendingEatRipeReward = False
	ToastAteRipeCorpse(akCorpse)
	ApplyEatRipeCorpseBonus(akCorpse)
EndFunction

Function ToastAteRipeCorpse(Actor akCorpse)
	If !akCorpse
		Return
	EndIf
	PickmansWhisperMainQuestScript m = Main()
	If !m || !m.ModConfigAlias || !m.ModConfigAlias.AteRipeCorpseToast || GardenOfEden.StrLength(m.ModConfigAlias.AteRipeCorpseToast) < 1
		Debug.Trace("PickmansWhisper: eaten-ripe-corpse skip | no ateRipeCorpseToast (ModConfig not loaded / key empty)")
		Return
	EndIf
	String overrideName = m.GetVictimOverrideName(akCorpse)
	If !overrideName
		overrideName = "She"
	EndIf
	If !m.VoiceAlias
		Debug.Trace("PickmansWhisper: eaten-ripe-corpse skip | VoiceAlias unbound")
		Return
	EndIf
	String line = m.ApplyNamePlaceholder(m.ModConfigAlias.AteRipeCorpseToast, overrideName)
	If !line || GardenOfEden.StrLength(line) < 1
		Debug.Trace("PickmansWhisper: eaten-ripe-corpse skip | empty line after placeholder")
		Return
	EndIf
	Debug.Notification(line)
	Debug.Trace("PickmansWhisper: eaten-ripe-corpse toast | " + line + " formId=" + akCorpse.GetFormID())
EndFunction

Function ApplyEatRipeCorpseBonus(Actor akCorpse)
	PickmansWhisperMainQuestScript m = Main()
	If !m
		Debug.Trace("PickmansWhisper: ERROR ApplyEatRipeCorpseBonus — Main missing")
		Return
	EndIf
	PickmansWhisperBuffTrackerScript buffs = m.BuffTracker()
	If !buffs
		Debug.Trace("PickmansWhisper: ERROR ApplyEatRipeCorpseBonus — BuffTracker missing")
		Return
	EndIf
	buffs.ApplyEatRipeCorpseEndBuff()
EndFunction

Function SetCorpseDecayStatus(String reason)
	LastCorpseDecayStatus = reason
	; Status is Trace + MCM string only — overlay Apply must not spam the HUD.
	Debug.Trace("PickmansWhisper: corpse decay | " + reason)
EndFunction

Bool Function EnsureWoundBank()
	If WoundBankLoaded && WoundTemplateCount > 0
		Return True
	EndIf
	PickmansWhisperMainQuestScript m = Main()
	If !m || !m.VoiceAlias
		SetCorpseDecayStatus("ERROR: Main/VoiceAlias missing — cannot load " + WOUND_FILE)
		Return False
	EndIf
	WoundTemplates = new String[64]
	WoundTemplateCount = m.VoiceAlias.LoadStageBankAt(WOUND_FILE, WoundTemplates, CONFIG_PATH)
	WoundBankLoaded = True
	If WoundTemplateCount <= 0
		SetCorpseDecayStatus("ERROR: " + WOUND_FILE + " — " + m.VoiceAlias.GetLastStageLoadStatus())
		Debug.Notification("Pickman's Whisper: " + WOUND_FILE + " missing or empty")
		Debug.Trace("PickmansWhisper: ERROR DecayWoundOverlays load failed — " + m.VoiceAlias.GetLastStageLoadStatus())
		Return False
	EndIf
	Return True
EndFunction

Bool Function EnsureSkinBank()
	If SkinBankLoaded && SkinTemplateCount > 0
		Return True
	EndIf
	PickmansWhisperMainQuestScript m = Main()
	If !m || !m.VoiceAlias
		SetCorpseDecayStatus("ERROR: Main/VoiceAlias missing — cannot load " + SKIN_FILE)
		Return False
	EndIf
	SkinTemplates = new String[64]
	SkinTemplateCount = m.VoiceAlias.LoadStageBankAt(SKIN_FILE, SkinTemplates, CONFIG_PATH)
	SkinBankLoaded = True
	If SkinTemplateCount <= 0
		SetCorpseDecayStatus("ERROR: " + SKIN_FILE + " — " + m.VoiceAlias.GetLastStageLoadStatus())
		Debug.Notification("Pickman's Whisper: " + SKIN_FILE + " missing or empty")
		Debug.Trace("PickmansWhisper: ERROR DecaySkinOverlays load failed — " + m.VoiceAlias.GetLastStageLoadStatus())
		Return False
	EndIf
	Return True
EndFunction

Bool Function EnsureFaceBank()
	If FaceBankLoaded && FaceTemplateCount > 0
		Return True
	EndIf
	PickmansWhisperMainQuestScript m = Main()
	If !m || !m.VoiceAlias
		SetCorpseDecayStatus("ERROR: Main/VoiceAlias missing — cannot load " + FACE_FILE)
		Return False
	EndIf
	FaceTemplates = new String[64]
	FaceTemplateCount = m.VoiceAlias.LoadStageBankAt(FACE_FILE, FaceTemplates, CONFIG_PATH)
	FaceBankLoaded = True
	If FaceTemplateCount <= 0
		SetCorpseDecayStatus("ERROR: " + FACE_FILE + " — " + m.VoiceAlias.GetLastStageLoadStatus())
		Debug.Notification("Pickman's Whisper: " + FACE_FILE + " missing or empty")
		Debug.Trace("PickmansWhisper: ERROR DecayFaceOverlays load failed — " + m.VoiceAlias.GetLastStageLoadStatus())
		Return False
	EndIf
	Return True
EndFunction

; Soft strip bank for CumOverlays.esp — empty/missing is OK (no white-halo cleanup).
Bool Function EnsureCumBank()
	If CumBankLoaded && CumTemplateCount > 0
		Return True
	EndIf
	If CumBankLoaded
		Return False
	EndIf
	PickmansWhisperMainQuestScript m = Main()
	If !m || !m.VoiceAlias
		Debug.Trace("PickmansWhisper: EnsureCumBank skip — Main/VoiceAlias missing")
		Return False
	EndIf
	CumTemplates = new String[64]
	CumTemplateCount = m.VoiceAlias.LoadStageBankAt(CUM_FILE, CumTemplates, CONFIG_PATH)
	CumBankLoaded = True
	If CumTemplateCount <= 0
		Debug.Trace("PickmansWhisper: CumOverlayIds empty/missing — cum stump strip disabled | " + m.VoiceAlias.GetLastStageLoadStatus())
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

; Space-only edge trim. Do NOT use Main.TrimString — GetWords mangles key=value.
; Trailing CR on CRLF lines is handled by ConfigLabelKey / ParsePositiveInt (digits prefix).
String Function ConfigTrim(String s)
	If !s || s == ""
		Return ""
	EndIf
	Int len = GardenOfEden.StrLength(s)
	Int start = 0
	While start < len && GardenOfEden.SubStr(s, start, 1) == " "
		start += 1
	EndWhile
	Int endPos = len
	While endPos > start && GardenOfEden.SubStr(s, endPos - 1, 1) == " "
		endPos -= 1
	EndWhile
	If start >= endPos
		Return ""
	EndIf
	Return GardenOfEden.SubStr(s, start, endPos - start)
EndFunction

; Face color keys: keep letters only + lower — drops CRLF leftover CR/LF/TAB/digits noise.
String Function ConfigLabelKey(String s)
	If !s || s == ""
		Return ""
	EndIf
	String out = ""
	Int i = 0
	Int n = GardenOfEden.StrLength(s)
	While i < n
		String c = GardenOfEden.SubStr(s, i, 1)
		If c == "A" || c == "a"
			out += "a"
		ElseIf c == "B" || c == "b"
			out += "b"
		ElseIf c == "C" || c == "c"
			out += "c"
		ElseIf c == "D" || c == "d"
			out += "d"
		ElseIf c == "E" || c == "e"
			out += "e"
		ElseIf c == "F" || c == "f"
			out += "f"
		ElseIf c == "G" || c == "g"
			out += "g"
		ElseIf c == "H" || c == "h"
			out += "h"
		ElseIf c == "I" || c == "i"
			out += "i"
		ElseIf c == "J" || c == "j"
			out += "j"
		ElseIf c == "K" || c == "k"
			out += "k"
		ElseIf c == "L" || c == "l"
			out += "l"
		ElseIf c == "M" || c == "m"
			out += "m"
		ElseIf c == "N" || c == "n"
			out += "n"
		ElseIf c == "O" || c == "o"
			out += "o"
		ElseIf c == "P" || c == "p"
			out += "p"
		ElseIf c == "Q" || c == "q"
			out += "q"
		ElseIf c == "R" || c == "r"
			out += "r"
		ElseIf c == "S" || c == "s"
			out += "s"
		ElseIf c == "T" || c == "t"
			out += "t"
		ElseIf c == "U" || c == "u"
			out += "u"
		ElseIf c == "V" || c == "v"
			out += "v"
		ElseIf c == "W" || c == "w"
			out += "w"
		ElseIf c == "X" || c == "x"
			out += "x"
		ElseIf c == "Y" || c == "y"
			out += "y"
		ElseIf c == "Z" || c == "z"
			out += "z"
		EndIf
		i += 1
	EndWhile
	Return out
EndFunction

; Compat name — label keys go through ConfigLabelKey (letters + lower only).
String Function ConfigLowerAscii(String s)
	Return ConfigLabelKey(s)
EndFunction

Int Function FindFaceArmorLabelIndex(String label)
	String want = ConfigLowerAscii(ConfigTrim(label))
	If want == ""
		Return -1
	EndIf
	Int i = 0
	While i < FaceArmorCount
		If FaceArmorLabels[i] == want
			Return i
		EndIf
		i += 1
	EndWhile
	Return -1
EndFunction

String Function FaceArmorLabelsDebugList()
	String out = ""
	Int i = 0
	While i < FaceArmorCount
		If i > 0
			out += ","
		EndIf
		out += FaceArmorLabels[i]
		i += 1
	EndWhile
	Return out
EndFunction

; True when FaceStageArmoFids has a valid row for every stage (0 = none is valid).
Bool Function FaceStageMapReady()
	If !FaceStageArmoFids || FaceStageArmoFids.Length != DECAY_STAGE_COUNT
		Return False
	EndIf
	Int i = 0
	While i < DECAY_STAGE_COUNT
		If FaceStageArmoFids[i] < 0
			Return False
		EndIf
		i += 1
	EndWhile
	Return True
EndFunction

; Drop cached face banks so next Ensure re-reads DecayFaceArmorIds + DecayFaceStages.
; Only flips the "needs refresh" flag. Must NOT touch FaceArmorLoadBusy / FaceArmorCount /
; FaceArmorLabels / FaceStageArmoFids directly — this runs on every LoadModConfig (i.e.
; every game load), and an EnsureDecayFaceArmorBanks call already in flight elsewhere
; reads those same arrays. Wiping them out from under it produced "UNKNOWN label ...
; known=[]" when a reload landed mid-apply. Setting FaceArmorBanksLoaded=False alone is
; enough to force the next Ensure call to do a full, properly-guarded reload.
Function InvalidateDecayFaceArmorBanks()
	FaceArmorBanksLoaded = False
	FaceArmorLoadStatus = "invalidated"
	Debug.Trace("PickmansWhisper: decay face armor banks invalidated")
EndFunction

; Re-read DecayFaceStages.txt. Builds a TEMP map and only commits if all stages parse —
; never leaves FaceStageArmoFids wiped mid-reload (that raced KillerScan + scar applies).
; none → 0 (strip masks); missing stage → fail without clobbering the live map.
Bool Function ReloadDecayFaceStageMap()
	PickmansWhisperMainQuestScript m = Main()
	If !m
		FaceArmorLoadStatus = "ERROR: Main missing"
		SetCorpseDecayStatus(FaceArmorLoadStatus)
		Return False
	EndIf
	If FaceArmorCount <= 0
		FaceArmorLoadStatus = "ERROR: face ARMO id bank empty — cannot map stages"
		SetCorpseDecayStatus(FaceArmorLoadStatus)
		Return False
	EndIf
	If !GardenOfEden2.DoesFileExist(FACE_STAGE_FILE, CONFIG_PATH)
		FaceArmorLoadStatus = "MISSING " + FACE_STAGE_FILE
		SetCorpseDecayStatus("ERROR: " + FaceArmorLoadStatus)
		Debug.Notification("Pickman's Whisper: " + FACE_STAGE_FILE + " missing")
		Debug.Trace("PickmansWhisper: ERROR " + FACE_STAGE_FILE + " missing at " + CONFIG_PATH)
		Return False
	EndIf
	; Temp map only — live FaceStageArmoFids stays valid until commit.
	Int[] nextFids = new Int[5]
	Int si = 0
	While si < DECAY_STAGE_COUNT
		nextFids[si] = -1
		si += 1
	EndWhile
	String[] stageRaw = GardenOfEden2.GetLinesFromFile(FACE_STAGE_FILE, CONFIG_PATH)
	If !stageRaw || stageRaw.Length == 0
		FaceArmorLoadStatus = "EMPTY " + FACE_STAGE_FILE
		SetCorpseDecayStatus("ERROR: " + FaceArmorLoadStatus)
		Debug.Notification("Pickman's Whisper: " + FACE_STAGE_FILE + " empty")
		Debug.Trace("PickmansWhisper: ERROR " + FACE_STAGE_FILE + " empty")
		Return False
	EndIf
	Int mapped = 0
	Int i = 0
	While i < stageRaw.Length
		String sline = ConfigTrim(stageRaw[i])
		i += 1
		If sline == ""
			; skip
		ElseIf GardenOfEden.SubStr(sline, 0, 1) == "#"
			; comment
		Else
			Int seq = FindCharIndex(sline, "=")
			If seq > 0
				String stageStr = ConfigTrim(GardenOfEden.SubStr(sline, 0, seq))
				String label = ConfigLowerAscii(ConfigTrim(GardenOfEden.SubStr(sline, seq + 1, -1)))
				Int stage = m.VoiceAlias.ParsePositiveInt(stageStr)
				If stageStr == "0"
					stage = 0
				EndIf
				If stage >= 0 && stage < DECAY_STAGE_COUNT && label != ""
					If label == "none"
						nextFids[stage] = 0
						mapped += 1
					Else
						Int li = FindFaceArmorLabelIndex(label)
						If li < 0
							FaceArmorLoadStatus = "UNKNOWN label " + label + " (stage " + stage + ") known=[" + FaceArmorLabelsDebugList() + "]"
							SetCorpseDecayStatus("ERROR: " + FaceArmorLoadStatus + " — rebuild ESP / check " + FACE_ARMOR_IDS_FILE)
							Debug.Notification("Pickman's Whisper: face stage " + stage + " label " + label + " has no ARMO")
							Debug.Trace("PickmansWhisper: ERROR face stage map — " + FaceArmorLoadStatus)
							Return False
						EndIf
						nextFids[stage] = FaceArmorArmoFids[li]
						mapped += 1
					EndIf
				EndIf
			EndIf
		EndIf
	EndWhile
	si = 0
	While si < DECAY_STAGE_COUNT
		If nextFids[si] < 0
			FaceArmorLoadStatus = "MISSING stage " + si + " in " + FACE_STAGE_FILE
			SetCorpseDecayStatus("ERROR: " + FaceArmorLoadStatus)
			Debug.Notification("Pickman's Whisper: " + FACE_STAGE_FILE + " missing stage " + si)
			Debug.Trace("PickmansWhisper: ERROR " + FaceArmorLoadStatus)
			Return False
		EndIf
		si += 1
	EndWhile
	; Commit only after a complete good map.
	FaceStageArmoFids = nextFids
	FaceArmorLoadStatus = FaceArmorCount + " ARMOs / " + mapped + " stages"
	Debug.Trace("PickmansWhisper: decay face stage map loaded — " + FaceArmorLoadStatus)
	Return True
EndFunction

Bool FaceArmorLoadBusy = False ; blocks re-entrant wipe of FaceArmorLabels mid-parse
; Can get stuck True forever if a save loads mid-call (the in-flight load that would
; clear it is gone) — every later apply then silently skips the face ARMO (busy —
; skip re-enter) for the rest of the session. Same class of bug as BedOverlaysBusy;
; same fix: a real-time staleness check so a stuck flag clears instead of persisting.
; 8.0s was too short: this load can legitimately take 20s+ under load (confirmed in
; logs), and force-clearing while the original call was still genuinely mid-parse
; caused a SECOND concurrent load into the same shared FaceArmorLabels/ArmoFids
; arrays — doubled/corrupted entries (e.g. 10 entries for a 5-label file) and
; "UNKNOWN label ... known=[]" errors. Match OverlaySyncBusy's 90s in this same
; file: give the legitimately-slow call room to finish before ANY retry, since a
; too-short timeout here doesn't just delay, it actively corrupts shared state.
Float FaceArmorLoadBusySinceReal = 0.0
Float FACE_ARMOR_LOAD_BUSY_TIMEOUT_SECONDS = 90.0

; DecayFaceArmorIds.txt + DecayFaceStages.txt — fail loud if missing/incomplete.
Bool Function EnsureDecayFaceArmorBanks()
	; Cache when valid. Do NOT re-read DecayFaceStages on every apply — that raced
	; KillerScan/scar applies and wiped FaceStageArmoFids mid-flight (MISSING stage 0).
	If FaceArmorBanksLoaded && FaceArmorCount > 0 && FaceStageMapReady()
		Return True
	EndIf
	; Another apply is loading — do not reset arrays underneath it (known=[] race).
	If FaceArmorLoadBusy
		Float nowFaceBusy = Utility.GetCurrentRealTime()
		; Real-time resets to ~0 on every new process; a stale saved value from a
		; longer previous session would make busyElapsed negative and never exceed
		; the timeout, permanently skipping the face ARMO for this whole session.
		If FaceArmorLoadBusySinceReal > nowFaceBusy
			FaceArmorLoadBusySinceReal = 0.0
		EndIf
		Float busyElapsed = nowFaceBusy - FaceArmorLoadBusySinceReal
		If busyElapsed <= FACE_ARMOR_LOAD_BUSY_TIMEOUT_SECONDS
			Debug.Trace("PickmansWhisper: EnsureDecayFaceArmorBanks busy — skip re-enter (" + busyElapsed + "s/" + FACE_ARMOR_LOAD_BUSY_TIMEOUT_SECONDS + "s)")
			Return False
		EndIf
		; Stuck true too long — most likely a save loaded mid-call and the in-flight
		; load that would clear it is gone. Force-clear and proceed with a fresh load
		; rather than skip the face ARMO for the rest of the session.
		Debug.Trace("PickmansWhisper: EnsureDecayFaceArmorBanks busy watchdog — force clear after " + busyElapsed + "s")
	EndIf
	FaceArmorLoadBusy = True
	FaceArmorLoadBusySinceReal = Utility.GetCurrentRealTime()
	PickmansWhisperMainQuestScript m = Main()
	If !m
		FaceArmorLoadStatus = "ERROR: Main missing"
		SetCorpseDecayStatus(FaceArmorLoadStatus)
		FaceArmorLoadBusy = False
		Return False
	EndIf
	; Parse into locals; commit to the live FaceArmorLabels/FaceArmorArmoFids/FaceArmorCount
	; only after a full successful parse. Wiping the live arrays up front (old behavior)
	; left them observably empty ("known=[]") for the whole file-read + parse duration —
	; long enough (20s+ confirmed under load, see FACE_ARMOR_LOAD_BUSY_TIMEOUT_SECONDS
	; above) for a second in-flight caller (e.g. after the busy watchdog force-clears a
	; stale flag post save-reload) to read the live arrays mid-wipe.
	String[] nextLabels = new String[16]
	Int[] nextArmoFids = new Int[16]
	Int nextCount = 0
	FaceArmorBanksLoaded = False
	FaceArmorLoadStatus = "READ FAILED"

	If !GardenOfEden2.DoesFileExist(FACE_ARMOR_IDS_FILE, CONFIG_PATH)
		FaceArmorLoadStatus = "MISSING " + FACE_ARMOR_IDS_FILE
		SetCorpseDecayStatus("ERROR: " + FaceArmorLoadStatus + " — rebuild ESP")
		Debug.Notification("Pickman's Whisper: " + FACE_ARMOR_IDS_FILE + " missing — rebuild ESP")
		Debug.Trace("PickmansWhisper: ERROR " + FACE_ARMOR_IDS_FILE + " missing at " + CONFIG_PATH)
		FaceArmorLoadBusy = False
		Return False
	EndIf

	String[] idRaw = GardenOfEden2.GetLinesFromFile(FACE_ARMOR_IDS_FILE, CONFIG_PATH)
	If !idRaw || idRaw.Length == 0
		FaceArmorLoadStatus = "EMPTY " + FACE_ARMOR_IDS_FILE
		SetCorpseDecayStatus("ERROR: " + FaceArmorLoadStatus)
		Debug.Notification("Pickman's Whisper: " + FACE_ARMOR_IDS_FILE + " empty — rebuild ESP")
		Debug.Trace("PickmansWhisper: ERROR " + FACE_ARMOR_IDS_FILE + " empty")
		FaceArmorLoadBusy = False
		Return False
	EndIf
	Int i = 0
	While i < idRaw.Length && nextCount < FACE_ARMOR_MAX
		String line = ConfigTrim(idRaw[i])
		i += 1
		If line == ""
			; skip
		ElseIf GardenOfEden.SubStr(line, 0, 1) == "#"
			; comment
		Else
			Int eq = FindCharIndex(line, "=")
			If eq > 0
				String label = ConfigLowerAscii(ConfigTrim(GardenOfEden.SubStr(line, 0, eq)))
				String val = ConfigTrim(GardenOfEden.SubStr(line, eq + 1, -1))
				Int comma = FindCharIndex(val, ",")
				If label != "" && comma > 0
					String armoStr = ConfigTrim(GardenOfEden.SubStr(val, comma + 1, -1))
					Int armoFid = m.VoiceAlias.ParsePositiveInt(armoStr)
					If armoFid > 0
						nextLabels[nextCount] = label
						nextArmoFids[nextCount] = armoFid
						nextCount += 1
					Else
						Debug.Trace("PickmansWhisper: WARN face ARMO id skip label=" + label + " bad armoFid from " + armoStr)
					EndIf
				EndIf
			EndIf
		EndIf
	EndWhile
	If nextCount <= 0
		FaceArmorLoadStatus = "EMPTY rows " + FACE_ARMOR_IDS_FILE
		SetCorpseDecayStatus("ERROR: " + FaceArmorLoadStatus)
		Debug.Notification("Pickman's Whisper: " + FACE_ARMOR_IDS_FILE + " has no ARMO rows")
		Debug.Trace("PickmansWhisper: ERROR " + FACE_ARMOR_IDS_FILE + " parsed 0 ARMOs")
		FaceArmorLoadBusy = False
		Return False
	EndIf
	; Commit now — ReloadDecayFaceStageMap() below reads FaceArmorLabels/FaceArmorArmoFids
	; live via FindFaceArmorLabelIndex, so they must be in place before it runs.
	FaceArmorLabels = nextLabels
	FaceArmorArmoFids = nextArmoFids
	FaceArmorCount = nextCount
	Debug.Trace("PickmansWhisper: face ARMO ids loaded n=" + FaceArmorCount + " labels=[" + FaceArmorLabelsDebugList() + "]")

	If !ReloadDecayFaceStageMap()
		FaceArmorLoadBusy = False
		Return False
	EndIf
	FaceArmorBanksLoaded = True
	FaceArmorLoadBusy = False
	Debug.Trace("PickmansWhisper: decay face armor banks loaded — " + FaceArmorLoadStatus + " stageFids Green(3)=" + FaceStageArmoFids[3] + " Black(4)=" + FaceStageArmoFids[4])
	Return True
EndFunction

; Unequip + remove every PW DecayFace ARMO on her (Base/Gray/Red/Green/Black).
Function StripDecayFaceArmors(Actor akCorpse)
	If !akCorpse
		Return
	EndIf
	If FaceArmorCount <= 0
		If !EnsureDecayFaceArmorBanks()
			Debug.Trace("PickmansWhisper: StripDecayFaceArmors skip — face ARMO bank unavailable")
			Return
		EndIf
	EndIf
	Int removed = 0
	Int i = 0
	While i < FaceArmorCount
		Form f = Game.GetFormFromFile(FaceArmorArmoFids[i], PLUGIN_PW)
		If f
			Int n = akCorpse.GetItemCount(f)
			If n > 0
				akCorpse.UnequipItem(f, False, True)
				akCorpse.RemoveItem(f, n, True)
				removed += n
			EndIf
		EndIf
		i += 1
	EndWhile
	If removed > 0
		Debug.Trace("PickmansWhisper: StripDecayFaceArmors removed " + removed + " face ARMO item(s)")
	EndIf
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
	If fid < 0
		SetCorpseDecayStatus("ERROR: face stage " + aiStage + " not mapped")
		Debug.Trace("PickmansWhisper: ERROR ApplyDecayFaceArmorForStage — unmapped stage " + aiStage)
		Return False
	EndIf
	; Stages 0–1 (DecayFaceStages none): cleanup — strip any DecayFace ARMO still on her.
	If fid == 0
		StripDecayFaceArmors(akCorpse)
		SetCorpseDecayStatus("face cleanup: stripped DecayFace masks (stage " + aiStage + " none)")
		Debug.Trace("PickmansWhisper: ApplyDecayFaceArmorForStage stage=" + aiStage + " — none cleanup strip")
		Return True
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
	; Refresh equipment 3D — without this, corpses often keep the ARMO in inventory only
	; (loot shows PW DecayFace Green while the head still looks vanilla).
	akCorpse.QueueUpdate(True, 0)
	worn = akCorpse.IsEquipped(armor)
	If worn
		SetCorpseDecayStatus("face ARMO stage " + aiStage + " fid=" + fid + " equipped")
		Debug.Trace("PickmansWhisper: decay face ARMO equipped stage=" + aiStage + " fid=" + fid)
	Else
		; Inventory has it; visuals may still show after QueueUpdate. Do not fail the stage.
		SetCorpseDecayStatus("face ARMO stage " + aiStage + " fid=" + fid + " in inventory (IsEquipped=0 on corpse)")
		Debug.Trace("PickmansWhisper: WARN decay face ARMO IsEquipped=0 on corpse stage=" + aiStage + " fid=" + fid + " count=" + held + " — QueueUpdate done (dead IsEquipped often lies)")
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

; Soft dep Captive Tattoos (SlaveTattoos.esp) — same shape as SoftSkinDepsReady, own plugin gate
; so tattoo apply never wrongly requires porcOverlays.esl (or vice versa).
Bool Function SoftTattooDepsReady()
	If !SoftLooksMenuReady()
		Return False
	EndIf
	If !Game.IsPluginInstalled(PLUGIN_TATTOOS)
		SetCorpseDecayStatus("skip: SlaveTattoos.esp not installed")
		Debug.Notification("Pickman's Whisper: Captive Tattoos (SlaveTattoos.esp) required")
		Debug.Trace("PickmansWhisper: ERROR SlaveTattoos.esp missing — tattoo overlay skipped")
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
		; Protected ActorBases: KillSilent() with no killer can leave them alive.
		; Pass player as killer (credit suppressed above); do not clear Protected on the base.
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

; Ambient knife-kill victims (unlike Bed Gift's corpse) are never stripped. Worn
; armor/clothing would hide the DecaySkinOverlays body tint under the mesh even
; when LooksMenu reports a successful Add (appliedUids>0), so strip regardless of
; what she died wearing. Mirrors Bed Gift's StripBedCorpse; called once real body
; skins are about to render.
Function StripDecayCorpseClothing(Actor akCorpse)
	If !akCorpse
		Return
	EndIf
	akCorpse.UnequipAll()
	akCorpse.RemoveAllItems(None, False)
EndFunction

; REVERTED — a real Disable()/Enable() cycle (like Bed Gift's PrepareCorpseForOverlays
; gets for free from its own spawn-disabled corpse) did make the body overlay render,
; but on an ambient, never-disabled corpse it tears down and rebuilds her 3D/skeleton
; while she's actively ragdolled in the world. Confirmed in logs: IsDismembered started
; throwing "Cannot find limb" errors immediately after every Disable/Enable, and in
; testing it visibly looked like the NPC was being killed again. Worse than the
; original "no body texture" bug, so not worth it — QueueUpdate is the ceiling for
; ambient corpses until a refresh method is found that doesn't touch the skeleton.

; Ground truth from LooksMenu itself, not our own LastStage bookkeeping — Overlays.Add
; and QueueUpdate have both been caught reporting success while nothing visually
; changed. Queries the actor's live overlay list so the log shows what LooksMenu
; actually has attached at that moment, not what we assume happened.
Function TraceCorpseOverlayState(Actor akCorpse, String asLabel)
	If !akCorpse
		Return
	EndIf
	Bool isFemale = IsFemaleActor(akCorpse)
	Overlays:Entry[] entries = Overlays.GetAll(akCorpse, isFemale)
	Int count = 0
	If entries
		count = entries.Length
	EndIf
	Debug.Trace("PickmansWhisper: OverlayState " + asLabel + " formId=" + akCorpse.GetFormID() + " isFemale=" + (isFemale as Int) + " count=" + count)
	Int i = 0
	While entries && i < entries.Length
		Debug.Trace("PickmansWhisper: OverlayState " + asLabel + " [" + i + "] uid=" + entries[i].uid + " template=" + entries[i].template + " rgba=" + entries[i].red + "," + entries[i].green + "," + entries[i].blue + "," + entries[i].alpha)
		i += 1
	EndWhile
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

; Returns how many Overlays.Add calls returned a positive uid.
Int Function ApplyTintedAllTemplates(Actor akCorpse, String[] templates, Int aiTemplateCount, Int aiTimesEach, Float afR, Float afG, Float afB, Float afA, Int aiPriority, String statusPrefix, Bool abClearMatching = True)
	If !akCorpse
		SetCorpseDecayStatus("skip: no corpse")
		Return 0
	EndIf
	If !templates || aiTemplateCount <= 0
		SetCorpseDecayStatus("skip: empty overlay bank")
		Return 0
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
	Return applied
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

; Strip CumOverlays templates (LooksMenu only — no CumOverlays.esp master required).
Function ClearCumBankOverlays(Actor akCorpse)
	If !akCorpse
		Return
	EndIf
	If !Game.IsPluginInstalled(PLUGIN_LOOKSMENU)
		Return
	EndIf
	If !EnsureCumBank()
		Return
	EndIf
	PrepareCorpseForOverlays(akCorpse)
	Bool isFemale = IsFemaleActor(akCorpse)
	RemoveMatchingOverlays(akCorpse, isFemale, CumTemplates, CumTemplateCount)
	; CumOverlays tags some entries with the other sex slot — clear both cheaply.
	RemoveMatchingOverlays(akCorpse, !isFemale, CumTemplates, CumTemplateCount)
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

; Captive Tattoos lab — multi-select apply, three calls bracketing the caller's
; per-chunk loop (caller owns reading the 20 MCM steppers and resolving each
; chunk's bank; this owns LooksMenu bookkeeping):
;   BeginTattooApply   — remove whatever this script applied last time (same
;                         target only), reset per-chunk UID tracking
;   ApplyOneTattooChunk — add one chunk's selected overlay, record its UID
;   FinishTattooApply  — the double-Update render-refresh + status message
; Splitting the Update out of the per-chunk call matters: it must run once after
; every selected chunk is added, not once per chunk (matches ApplyTintedAllTemplates).
Bool Function BeginTattooApply(Actor akCorpse)
	If !akCorpse
		SetCorpseDecayStatus("skip: no corpse")
		Return False
	EndIf
	If !SoftTattooDepsReady()
		Return False
	EndIf
	If LastTattooTarget == akCorpse && LastTattooUids
		Bool wasFemale = IsFemaleActor(akCorpse)
		Int r = 0
		While r < LastTattooUids.Length
			If LastTattooUids[r] >= 0
				Overlays.Remove(akCorpse, wasFemale, LastTattooUids[r])
			EndIf
			r += 1
		EndWhile
	EndIf
	LastTattooTarget = akCorpse
	LastTattooUids = new Int[TATTOO_CHUNK_COUNT]
	Int z = 0
	While z < LastTattooUids.Length
		LastTattooUids[z] = -1
		z += 1
	EndWhile
	PrepareCorpseForOverlays(akCorpse)
	Return True
EndFunction

Function ApplyOneTattooChunk(Actor akCorpse, Int chunkIdx, String templateId)
	If !akCorpse || !templateId || templateId == ""
		Return
	EndIf
	Bool isFemale = IsFemaleActor(akCorpse)
	Int uid = AddTintedOverlay(akCorpse, templateId, 1.0, 1.0, 1.0, 1.0, isFemale, TATTOO_PRIORITY)
	If chunkIdx >= 0 && chunkIdx < LastTattooUids.Length
		LastTattooUids[chunkIdx] = uid
	EndIf
EndFunction

Function FinishTattooApply(Actor akCorpse, Int appliedCount)
	Overlays.Update(akCorpse)
	; A single Update right after Add has been caught (see TraceCorpseOverlayState)
	; reporting success with nothing visually changed — same second-Update-after-a-
	; short-wait workaround ApplyTintedTemplateN already relies on for Wound/Skin/Face.
	If !Utility.IsInMenuMode()
		Utility.Wait(0.1)
		Overlays.Update(akCorpse)
	EndIf
	SetCorpseDecayStatus("lab tattoo: " + appliedCount + " applied")
EndFunction

Int Function ApplyTintedAllSkinTemplates(Actor akCorpse, String[] templates, Int aiTemplateCount, Int aiTimesEach, Float afR, Float afG, Float afB, Float afA)
	If !SoftSkinDepsReady()
		Return 0
	EndIf
	Return ApplyTintedAllTemplates(akCorpse, templates, aiTemplateCount, aiTimesEach, afR, afG, afB, afA, SKIN_PRIORITY, "lab skin", True)
EndFunction

; Additive Porcupine apply — never RemoveMatchingOverlays (keeps SkinTexture_* already on the body).
Int Function ApplyTintedAllSkinTemplatesKeepExisting(Actor akCorpse, String[] templates, Int aiTemplateCount, Int aiTimesEach, Float afR, Float afG, Float afB, Float afA)
	If !SoftSkinDepsReady()
		Return 0
	EndIf
	Return ApplyTintedAllTemplates(akCorpse, templates, aiTemplateCount, aiTimesEach, afR, afG, afB, afA, SKIN_PRIORITY, "lab skin", False)
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

; Slice K beat-before-kill outcome — every SFT Damage/Boxer face overlay
; (DecayFaceOverlays.txt, same bank + call Wound Lab's "Apply all face overlays"
; button uses, confirmed rendering correctly in-game) applied to a living NPC.
; wasDead is always False here in practice (target is alive, mid/post-fight), so
; PrepareActorForSFTFace never Resurrects — this is just ApplyTintedAllFaceTemplates
; with the production FaceTemplates bank instead of the lab's separate copy.
Function ApplyBeatFaceOverlays(Actor akTarget)
	If !EnsureFaceBank()
		Return
	EndIf
	ApplyTintedAllFaceTemplates(akTarget, FaceTemplates, FaceTemplateCount, 1, 1.0, 0.92, 0.88, 0.75)
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

; True when head + four limbs are still attached. LooksMenu body overlays glow at
; stump UV edges after Dismember (decay tint = green; cum overlays = white).
Bool Function IsCorpseLimbsIntact(Actor akCorpse)
	If !akCorpse
		Return False
	EndIf
	If akCorpse.IsDismembered("Head1")
		Return False
	EndIf
	If akCorpse.IsDismembered("LeftArm1")
		Return False
	EndIf
	If akCorpse.IsDismembered("RightArm1")
		Return False
	EndIf
	If akCorpse.IsDismembered("LeftLeg1")
		Return False
	EndIf
	If akCorpse.IsDismembered("RightLeg1")
		Return False
	EndIf
	Return True
EndFunction

; Strip Porcupine decay + CumOverlays after butcher — stump UV glows (green / white).
Function StripBodyDecayOverlaysForDismember(Actor akCorpse)
	If !akCorpse
		Return
	EndIf
	Bool strippedSkin = False
	If EnsureSkinBank()
		ClearSkinBankOverlays(akCorpse, SkinTemplates, SkinTemplateCount)
		strippedSkin = True
	Else
		Debug.Trace("PickmansWhisper: StripBodyDecayOverlaysForDismember skin skip | " + LastCorpseDecayStatus)
	EndIf
	Bool strippedCum = False
	If EnsureCumBank()
		ClearCumBankOverlays(akCorpse)
		strippedCum = True
	EndIf
	SetCorpseDecayStatus("body/cum overlays stripped — limbs missing (stump halo) skin=" + (strippedSkin as Int) + " cum=" + (strippedCum as Int))
	Debug.Trace("PickmansWhisper: StripBodyDecayOverlaysForDismember formId=" + akCorpse.GetFormID() + " skin=" + (strippedSkin as Int) + " cum=" + (strippedCum as Int))
EndFunction

Function QueueStripBodyDecayAfterDismember(Actor akCorpse)
	If !akCorpse
		Return
	EndIf
	PendingDismemberStripActor = akCorpse
	CallFunctionNoWait("RunPendingDismemberStrip", None)
EndFunction

Function RunPendingDismemberStrip()
	Actor ak = PendingDismemberStripActor
	PendingDismemberStripActor = None
	If ak
		StripBodyDecayOverlaysForDismember(ak)
	EndIf
EndFunction

Bool Function WasCutOffTitsApplied(Actor akCorpse)
	If !akCorpse || !CutOffTitsDoneIds || CutOffTitsDoneCount <= 0
		Return False
	EndIf

	Int id = akCorpse.GetFormID()
	Int i = 0
	While i < CutOffTitsDoneCount
		If CutOffTitsDoneIds[i] == id
			Return True
		EndIf
		i += 1
	EndWhile

	Return False
EndFunction

Function MarkCutOffTitsApplied(Actor akCorpse)
	If !akCorpse
		Return
	EndIf

	If WasCutOffTitsApplied(akCorpse)
		Return
	EndIf

	If !CutOffTitsDoneIds
		CutOffTitsDoneIds = new Int[CUT_OFF_TITS_ONCE_MAX]
		CutOffTitsDoneCount = 0
	EndIf

	If CutOffTitsDoneCount >= CUT_OFF_TITS_ONCE_MAX
		Int i = 0
		While i < CUT_OFF_TITS_ONCE_MAX - 1
			CutOffTitsDoneIds[i] = CutOffTitsDoneIds[i + 1]
			i += 1
		EndWhile
		CutOffTitsDoneCount = CUT_OFF_TITS_ONCE_MAX - 1
	EndIf

	CutOffTitsDoneIds[CutOffTitsDoneCount] = akCorpse.GetFormID()
	CutOffTitsDoneCount += 1
EndFunction

Form Function ResolveMutilatedBodyArmor()
	Form armor = Game.GetFormFromFile(FID_MUTILATED_BODY_ARMO, PLUGIN_PW)
	If !armor
		SetCorpseDecayStatus("ERROR: mutilated body ARMO 0x87D missing — rebuild ESP")
		Debug.Notification("Pickman's Whisper: mutilated body ARMO missing — rebuild ESP")
		Debug.Trace("PickmansWhisper: ERROR ResolveMutilatedBodyArmor GetFormFromFile 0x" + FID_MUTILATED_BODY_ARMO)
	EndIf
	Return armor
EndFunction

Form Function ResolveCutOffTitsMisc()
	Form misc = Game.GetFormFromFile(FID_CUT_OFF_TITS_MISC, PLUGIN_PW)
	If !misc
		SetCorpseDecayStatus("ERROR: cut-off tits MISC 0x87E missing — rebuild ESP")
		Debug.Notification("Pickman's Whisper: cut-off tits prop missing — rebuild ESP")
		Debug.Trace("PickmansWhisper: ERROR ResolveCutOffTitsMisc GetFormFromFile 0x" + FID_CUT_OFF_TITS_MISC)
	EndIf
	Return misc
EndFunction

; Re-wear slot-33 ARMO after a later limb Dismember (3D rebuild can flash the default body).
; Does not PlaceAtMe — the MISC is spawned once on first Cut Off Tits.
Function ReequipMutilatedBodyIfNeeded(Actor akCorpse)
	If !akCorpse
		Return
	EndIf

	If !WasCutOffTitsApplied(akCorpse)
		Return
	EndIf

	Form armor = ResolveMutilatedBodyArmor()
	If !armor
		Return
	EndIf

	If akCorpse.GetItemCount(armor) <= 0
		akCorpse.AddItem(armor, 1, True)
	EndIf

	akCorpse.EquipItem(armor, True, True)
	Debug.Trace("PickmansWhisper: re-equip mutilated body after limb sever id=" + akCorpse.GetFormID())
EndFunction

; Decay paints body skins on bare skin, so StripDecayCorpseClothing UnequipAll +
; RemoveAllItems her — which also destroys the slot-33 Cut Off Tits body and reverts
; her to an intact one. Put the custom body back so decay layers on top of it instead
; of replacing it. Must run BEFORE QueueUpdate: that rebuilds the biped from whatever
; is equipped at that moment.
Function RestoreMutilatedBodyAfterDecay(Actor akCorpse)
	If !akCorpse || !WasCutOffTitsApplied(akCorpse)
		Return
	EndIf

	Form armor = ResolveMutilatedBodyArmor()
	If !armor
		Return
	EndIf

	; Trust inventory, not IsEquipped — dead actors report IsEquipped=false while worn.
	; Present means the decay strip did not take it; re-equipping every sync would
	; churn her 3D for nothing.
	If akCorpse.GetItemCount(armor) > 0
		Return
	EndIf

	akCorpse.AddItem(armor, 1, True)
	akCorpse.EquipItem(armor, True, True)

	If akCorpse.GetItemCount(armor) <= 0
		SetCorpseDecayStatus("ERROR: mutilated body restore failed after decay strip")
		Debug.Trace("PickmansWhisper Error: RestoreMutilatedBodyAfterDecay AddItem id=" + akCorpse.GetFormID())
		Return
	EndIf

	Debug.Trace("PickmansWhisper: restored mutilated body after decay strip id=" + akCorpse.GetFormID())
EndFunction

; PlaceAtMe disabled + MoveTo + Enable + wait for 3D + InitHavok so the MISC can fall like clutter.
Function DropHavokMiscBeside(Actor akCorpse, Form misc, Float offsetX, Float offsetY, Float offsetZ, String label)
	If !akCorpse
		Debug.Trace("PickmansWhisper Error: DropHavokMiscBeside — no corpse (" + label + ")")
		Return
	EndIf

	If !misc
		Debug.Trace("PickmansWhisper Error: DropHavokMiscBeside — no form (" + label + ")")
		Return
	EndIf

	; Initially disabled: MoveTo on a live 3D MISC keyframes it, and kicks never take.
	ObjectReference placed = akCorpse.PlaceAtMe(misc, 1, False, True)

	If !placed
		SetCorpseDecayStatus("ERROR: PlaceAtMe " + label + " failed")
		Debug.Notification("Pickman's Whisper: " + label + " failed to spawn")
		Debug.Trace("PickmansWhisper Error: DropHavokMiscBeside PlaceAtMe None " + label + " id=" + akCorpse.GetFormID())
		Return
	EndIf

	placed.MoveTo(akCorpse, offsetX, offsetY, offsetZ, False)
	placed.Enable(False)

	; Wait for 3D — InitHavok in the same frame as Enable no-ops if Havok is not ready.
	; Safe here: butcher-menu path, not a hot event stack.
	Int guard = 0

	While !placed.Is3DLoaded() && guard < 20
		Utility.Wait(0.1)
		guard += 1
	EndWhile

	If !placed.Is3DLoaded()
		Debug.Trace("PickmansWhisper: WARNING DropHavokMiscBeside — 3D never loaded " + label + " id=" + akCorpse.GetFormID())
	EndIf

	GardenOfEden.InitHavok(placed)
	placed.SetMotionType(placed.Motion_Dynamic, True)
	placed.ApplyHavokImpulse(0.0, 0.0, -1.0, 8.0)
	Debug.Trace("PickmansWhisper: spawned " + label + " beside id=" + akCorpse.GetFormID())
EndFunction

Function SpawnCutOffTitsProp(Actor akCorpse)
	If !akCorpse
		Debug.Trace("PickmansWhisper Error: SpawnCutOffTitsProp — no corpse")
		Return
	EndIf

	DropHavokMiscBeside(akCorpse, ResolveCutOffTitsMisc(), CUT_OFF_TITS_PROP_OFFSET_XY, 0.0, CUT_OFF_TITS_PROP_OFFSET_Z, "cut-off tits")
EndFunction

; Butcher Cut Off Tits — instance body swap + dropped MISC. Not Dismember (no breast gore bone).
Function ApplyMutilatedBodyOnCorpse(Actor akCorpse)
	If !akCorpse
		Debug.Trace("PickmansWhisper: ERROR ApplyMutilatedBodyOnCorpse — no corpse")
		Return
	EndIf

	If !akCorpse.Is3DLoaded()
		Debug.Notification("Pickman's Whisper: corpse 3D not loaded — try again")
		Debug.Trace("PickmansWhisper: cut-off tits skip | 3D not loaded id=" + akCorpse.GetFormID())
		Return
	EndIf

	If WasCutOffTitsApplied(akCorpse)
		Debug.Notification("Pickman's Whisper: already severed")
		Debug.Trace("PickmansWhisper: cut-off tits skip | already applied id=" + akCorpse.GetFormID())
		Return
	EndIf

	Form armor = ResolveMutilatedBodyArmor()
	If !armor
		Return
	EndIf

	Form misc = ResolveCutOffTitsMisc()
	If !misc
		Return
	EndIf

	akCorpse.AddItem(armor, 1, True)
	akCorpse.EquipItem(armor, True, True)

	If akCorpse.GetItemCount(armor) <= 0
		SetCorpseDecayStatus("ERROR: mutilated body ARMO AddItem failed")
		Debug.Notification("Pickman's Whisper: mutilated body AddItem failed")
		Debug.Trace("PickmansWhisper: ERROR ApplyMutilatedBodyOnCorpse AddItem id=" + akCorpse.GetFormID())
		Return
	EndIf

	SpawnCutOffTitsProp(akCorpse)
	MarkCutOffTitsApplied(akCorpse)
	QueueStripBodyDecayAfterDismember(akCorpse)
	SetCorpseDecayStatus("cut off tits id=" + akCorpse.GetFormID())
	Debug.Notification("Pickman's Whisper: cut off tits")
	Debug.Trace("PickmansWhisper: cut off tits id=" + akCorpse.GetFormID())
EndFunction

; MCM Victims — Corpse decay visuals (default OFF). Stage clock advances either way.
Bool Function IsDecayVisualsEnabled()
	If !MCM.IsInstalled()
		Return False
	EndIf
	Return MCM.GetModSettingBool(MOD_NAME, "bDecayVisuals:Victims")
EndFunction

; MCM Victims — Apply decay to missing limbs/head (default OFF). When off (default),
; ApplyDecayStageOverlays skips body decal decay on a corpse missing a limb or the
; head (stump-edge UV glow protection) — same as today. When on, overrides that skip
; so a dismembered corpse gets painted exactly like a fully-limbed one.
Bool Function IsDecayMissingLimbsAllowed()
	If !MCM.IsInstalled()
		Return False
	EndIf
	Return MCM.GetModSettingBool(MOD_NAME, "bDecayMissingLimbs:Victims")
EndFunction

; ModConfig decayStageN SkinTextures (+ scars if flagged) at stage RGBA. Soft deps; fail loud.
; Returns True when paint succeeds OR visuals are MCM-off (harmless for direct/force
; callers). SyncDecayForKnifeCorpse checks IsDecayVisualsEnabled() itself BEFORE
; calling this and skips without stamping LastStage — do not let this True-while-off
; return value be used to stamp a stage as "applied" (permanently skips repaint once
; she reaches max stage, since nothing above it triggers a fresh mismatch).
; abForcePaint=True: bed gift vignette — paint even when bDecayVisuals is off.
Bool Function ApplyDecayStageOverlays(Actor akCorpse, Int aiStage, Bool abForcePaint = False)
	If !akCorpse
		SetCorpseDecayStatus("skip: no corpse")
		Return False
	EndIf
	PickmansWhisperMainQuestScript m = Main()
	If !m
		SetCorpseDecayStatus("ERROR: Main script missing — cannot apply decay stage")
		Return False
	EndIf
	PickmansWhisperModConfigScript cfg = m.ModConfigAlias
	If !cfg || !cfg.EnsureDecayStagesLoaded()
		String st = ""
		If cfg
			st = cfg.ModConfigLoadStatus
		EndIf
		SetCorpseDecayStatus("ERROR: ModConfig decayStage0..4 — " + st)
		Debug.Notification("Pickman's Whisper: decay stages not loaded — check ModConfig.txt")
		Debug.Trace("PickmansWhisper: ERROR ApplyDecayStageOverlays — " + LastCorpseDecayStatus)
		Return False
	EndIf
	If aiStage < 0 || aiStage >= 5
		SetCorpseDecayStatus("ERROR: decay stage index " + aiStage)
		Return False
	EndIf
	If !abForcePaint && !IsDecayVisualsEnabled()
		String stageNameOff = cfg.GetDecayStageName(aiStage)
		SetCorpseDecayStatus("stage " + aiStage + " " + stageNameOff + " — visuals OFF (MCM; clock still advances)")
		Debug.Trace("PickmansWhisper: ApplyDecayStageOverlays skip paint — visuals OFF stage=" + aiStage + " formId=" + akCorpse.GetFormID())
		Return True
	EndIf
	Debug.Trace("PickmansWhisper: ApplyDecayStageOverlays begin stage=" + aiStage + " formId=" + akCorpse.GetFormID() + " force=" + (abForcePaint as Int))
	; Bed gift (force paint): IsDismembered errors on parked/disabled NPCs false-trigger
	; "limbs missing" and strip body textures — always paint body for vignette.
	; MCM bDecayMissingLimbs:Victims (default off) is the same kind of override for
	; the ambient/MCM path — when on, a dismembered corpse is treated exactly like a
	; fully-limbed one (paints body decals + face mask; skips the stump-edge UV glow
	; protection). Computed once and reused for every IsDismembered("Head1") gate below.
	Bool bypassLimbGate = abForcePaint || IsDecayMissingLimbsAllowed()
	Bool limbsIntact = True
	If !bypassLimbGate
		limbsIntact = IsCorpseLimbsIntact(akCorpse)
		If !limbsIntact
			Debug.Trace("PickmansWhisper: ApplyDecayStageOverlays body blocked — limbs missing formId=" + akCorpse.GetFormID())
		EndIf
	EndIf
	; Face ARMO FIRST — if LooksMenu body work stalls, mask is already on.
	; Re-equip face after body (Overlays.Update can strip slot-54).
	Float tintR = cfg.GetDecayStageTintR(aiStage)
	Float tintG = cfg.GetDecayStageTintG(aiStage)
	Float tintB = cfg.GetDecayStageTintB(aiStage)
	Float tintA = cfg.GetDecayStageTintA(aiStage)
	String stageName = cfg.GetDecayStageName(aiStage)
	Bool faceOk = False
	String faceStatus = "face skipped — head missing"
	Bool headOk = bypassLimbGate || !akCorpse.IsDismembered("Head1")
	If headOk
		faceOk = ApplyDecayFaceArmorForStage(akCorpse, aiStage)
		faceStatus = LastCorpseDecayStatus
		Debug.Trace("PickmansWhisper: ApplyDecayStageOverlays face-first stage=" + aiStage + " ok=" + (faceOk as Int) + " | " + faceStatus)
	Else
		Debug.Trace("PickmansWhisper: ApplyDecayStageOverlays face skip — Head1 missing formId=" + akCorpse.GetFormID())
	EndIf

	Bool bodyOk = False
	String bodyStatus = ""
	Int skinCount = 0
	Int scarCount = 0
	Int appliedUids = 0
	If !limbsIntact
		; Clear prior decay skins + cum so stump edges lose overlay glow (green / white).
		If EnsureSkinBank() && SoftSkinDepsReady()
			ClearSkinBankOverlays(akCorpse, SkinTemplates, SkinTemplateCount)
		EndIf
		ClearCumBankOverlays(akCorpse)
		bodyOk = True
		bodyStatus = "body skipped — limbs missing (stump halo; decay+cum cleared)"
		Debug.Trace("PickmansWhisper: ApplyDecayStageOverlays stage=" + aiStage + " " + stageName + " — " + bodyStatus)
	ElseIf !EnsureSkinBank()
		bodyStatus = LastCorpseDecayStatus
	ElseIf !SoftSkinDepsReady()
		bodyStatus = LastCorpseDecayStatus
	Else
		String[] stageBank = new String[64]
		Int n = 0
		String[] skins = new String[8]
		skinCount = cfg.FillDecayStageSkins(aiStage, skins)
		Int s = 0
		While s < skinCount
			If skins[s] != ""
				stageBank[n] = skins[s]
				n += 1
			EndIf
			s += 1
		EndWhile
		; Scars disabled for stage apply — ModConfig no longer sets scars; keep code path inert
		; so a stray scars flag cannot reintroduce 20-overlay hangs.
		ClearSkinBankOverlays(akCorpse, SkinTemplates, SkinTemplateCount)
		If n <= 0
			bodyOk = True
			bodyStatus = "body default (skins=none)"
			Debug.Trace("PickmansWhisper: ApplyDecayStageOverlays stage=" + aiStage + " " + stageName + " — no body skins")
		Else
			StripDecayCorpseClothing(akCorpse)
			appliedUids = ApplyTintedAllSkinTemplatesKeepExisting(akCorpse, stageBank, n, 1, tintR, tintG, tintB, tintA)
			bodyOk = True
			bodyStatus = LastCorpseDecayStatus
			Debug.Trace("PickmansWhisper: ApplyDecayStageOverlays stage=" + aiStage + " " + stageName + " skins=" + skinCount + " scars=" + scarCount + " rgb=" + tintR + "," + tintG + "," + tintB + " a=" + tintA + " appliedUids=" + appliedUids)
			If appliedUids <= 0
				Debug.Trace("PickmansWhisper: ERROR ApplyDecayStageOverlays — LooksMenu Add returned 0 uids (templates missing or wrong sex?)")
			EndIf
			TraceCorpseOverlayState(akCorpse, "right-after-body-apply")
		EndIf
	EndIf

	; LooksMenu Update may have stripped the face mask — put it back (head still present).
	If bypassLimbGate || !akCorpse.IsDismembered("Head1")
		Bool faceOkAfter = ApplyDecayFaceArmorForStage(akCorpse, aiStage)
		If faceOkAfter
			faceOk = True
			faceStatus = LastCorpseDecayStatus
		EndIf
	EndIf

	; Same reason as the face mask above: the body strip took her Cut Off Tits body.
	; Restore before the QueueUpdate below rebuilds the biped from equipped items.
	RestoreMutilatedBodyAfterDecay(akCorpse)

	; Overlays.Add/Update reliably shows on Bed Gift's corpse because it's always
	; disabled beforehand (PrepareCorpseForOverlays' Enable() call forces a mesh
	; refresh as a side effect). A naturally-dead, never-disabled corpse (e.g. a
	; tracked knife-kill victim found via ambient KillerScan sync) skips that
	; Enable() entirely, and Overlays.Update alone was not enough to visually
	; refresh her — LooksMenu reported success but the body tint never rendered.
	; QueueUpdate forces the same refresh without a Disable/Enable cycle, so it
	; doesn't risk popping an already-ragdolled corpse out of her death pose.
	; Gated on limbsIntact — QueueUpdate(bDoEquipment=True) rebuilds the biped from
	; the base race + currently-equipped items, which can regenerate a limb a native
	; Dismember() call already gibbed. Confirmed in testing: a severed limb visibly
	; came back (with a disappear/reappear pop) because this ran unconditionally on
	; every apply, even when the body branch above had already skipped for the exact
	; same "limbs missing" reason. No overlay work happens in that branch, so there's
	; nothing here that needs a mesh refresh anyway.
	If limbsIntact
		akCorpse.QueueUpdate(True, 0)
	EndIf
	TraceCorpseOverlayState(akCorpse, "end-of-function")

	If bodyOk
		If !faceOk && (bypassLimbGate || !akCorpse.IsDismembered("Head1"))
			SetCorpseDecayStatus("stage " + aiStage + " " + stageName + " skins=" + skinCount + " scars=" + scarCount + " rgb=" + tintR + "," + tintG + "," + tintB + " a=" + tintA + " | body ok | face FAILED — " + faceStatus)
			Debug.Notification("Pickman's Whisper: body decay applied; face mask failed — " + faceStatus)
			Debug.Trace("PickmansWhisper: WARN ApplyDecayStageOverlays face failed — " + LastCorpseDecayStatus)
		Else
			SetCorpseDecayStatus("stage " + aiStage + " " + stageName + " skins=" + skinCount + " scars=" + scarCount + " rgb=" + tintR + "," + tintG + "," + tintB + " a=" + tintA + " uids=" + appliedUids + " | " + faceStatus + " | " + bodyStatus)
		EndIf
		Return True
	EndIf
	If faceOk
		SetCorpseDecayStatus("stage " + aiStage + " " + stageName + " face ok | body skipped — " + bodyStatus)
		Debug.Notification("Pickman's Whisper: body decay skipped — " + bodyStatus)
		Debug.Trace("PickmansWhisper: WARN ApplyDecayStageOverlays body skipped — " + LastCorpseDecayStatus)
		Return True
	EndIf
	SetCorpseDecayStatus("ERROR: stage " + aiStage + " body+face failed | body=" + bodyStatus + " | face=" + faceStatus)
	Debug.Trace("PickmansWhisper: ERROR ApplyDecayStageOverlays — " + LastCorpseDecayStatus)
	Return False
EndFunction

; Slice H P2 — re-apply ModConfig stage if stamped knife kill advanced. Trace only.
Function SyncDecayForKnifeCorpse(Actor akCorpse)
	If !akCorpse
		Debug.Trace("PickmansWhisper: SyncDecay skip | no corpse")
		Return
	EndIf
	PickmansWhisperMainQuestScript m = Main()
	If !m
		Debug.Trace("PickmansWhisper: ERROR SyncDecayForKnifeCorpse — Main missing")
		Return
	EndIf
	Int formId = akCorpse.GetFormID()
	If formId == 0 || FindDecayKillSlot(formId) < 0
		Debug.Trace("PickmansWhisper: SyncDecay skip | no kill slot formId=" + formId)
		Return
	EndIf
	PickmansWhisperModConfigScript cfg = m.ModConfigAlias
	If !cfg || !cfg.EnsureDecayStagesLoaded()
		String st = ""
		If cfg
			st = cfg.ModConfigLoadStatus
		EndIf
		SetCorpseDecayStatus("ERROR: ModConfig decayStage0..4 — " + st)
		Debug.Trace("PickmansWhisper: ERROR SyncDecayForKnifeCorpse — " + LastCorpseDecayStatus)
		Return
	EndIf
	Int stage = ResolveDecayStageForKill(formId)
	If stage < 0
		Debug.Trace("PickmansWhisper: SyncDecay skip | resolve failed formId=" + formId)
		Return
	EndIf
	Int last = GetDecayKillLastStage(formId)
	If stage == last
		Debug.Trace("PickmansWhisper: SyncDecay skip | stage==last stage=" + stage + " formId=" + formId)
		Return
	EndIf
	Debug.Trace("PickmansWhisper: SyncDecayForKnifeCorpse apply stage=" + stage + " last=" + last + " formId=" + formId)
	If !IsDecayVisualsEnabled()
		; Do NOT stamp LastStage here. ApplyDecayStageOverlays's own visuals-off skip
		; returns True (harmless for its other callers), but stamping here would make
		; a later visuals-on toggle believe this stage already painted — permanently
		; skipping her repaint once she reaches the max stage (nothing above it to
		; trigger a fresh want!=last mismatch). Leave LastStage alone so the very next
		; sync after visuals turn on detects the mismatch and paints for real.
		SetCorpseDecayStatus("stage " + stage + " " + cfg.GetDecayStageName(stage) + " — visuals OFF (MCM; clock advances, paint deferred) formId=" + formId)
		Debug.Trace("PickmansWhisper: " + LastCorpseDecayStatus)
		Return
	EndIf
	If ApplyDecayStageOverlays(akCorpse, stage)
		; MCM may ForceDecay mid-LooksMenu Wait — only stamp LastStage if clock still matches.
		Int stageNow = ResolveDecayStageForKill(formId)
		If stageNow == stage
			SetDecayKillLastStage(formId, stage)
			SetCorpseDecayStatus("knife sync stage " + stage + " " + cfg.GetDecayStageName(stage) + " formId=" + formId + " | " + LastCorpseDecayStatus)
			Debug.Trace("PickmansWhisper: " + LastCorpseDecayStatus)
		Else
			SetCorpseDecayStatus("knife sync aborted (clock moved during apply) was=" + stage + " now=" + stageNow + " formId=" + formId)
			Debug.Trace("PickmansWhisper: " + LastCorpseDecayStatus)
		EndIf
	Else
		Debug.Trace("PickmansWhisper: ERROR SyncDecayForKnifeCorpse ApplyDecayStageOverlays failed stage=" + stage + " formId=" + formId + " | " + LastCorpseDecayStatus)
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
	; Bed gift vignette always paints (DeathMarks + Black stage) — not gated by bDecayVisuals.
	PickmansWhisperModConfigScript cfg = m.ModConfigAlias
	Float woundA = -1.0
	If cfg
		woundA = cfg.GetBedGiftWoundAlpha()
	EndIf
	Int stage = BED_GIFT_DECAY_STAGE
	String woundStatus = ""
	If cfg && cfg.DecayStagesReady() && woundA >= 0.0
		; DeathMarks first; darken via stage RGB, opacity from ModConfig.
		ApplyDecayWoundOverlaysTinted(akCorpse, BED_GIFT_WOUND_COUNT, cfg.GetDecayStageTintR(stage), cfg.GetDecayStageTintG(stage), cfg.GetDecayStageTintB(stage), woundA)
		woundStatus = LastCorpseDecayStatus
		ApplyDecayStageOverlays(akCorpse, stage, True)
		SetCorpseDecayStatus("bed gift | " + woundStatus + " | " + LastCorpseDecayStatus)
		Return
	EndIf
	; Stage/alpha incomplete — still apply P1 DeathMarks so the vignette is not bare; fail loud.
	If !cfg || !cfg.DecayStagesReady()
		String st = ""
		If cfg
			st = cfg.ModConfigLoadStatus
		EndIf
		Debug.Notification("Pickman's Whisper: bed gift decay stages missing — wounds only; check ModConfig.txt")
		Debug.Trace("PickmansWhisper: ERROR bed gift stage skip — " + st)
	ElseIf woundA < 0.0
		Debug.Notification("Pickman's Whisper: bedGiftWoundAlpha missing — pale wounds only; check ModConfig.txt")
		Debug.Trace("PickmansWhisper: ERROR bed gift wound alpha missing")
	EndIf
	ApplyDecayWoundOverlays(akCorpse, BED_GIFT_WOUND_COUNT)
	SetCorpseDecayStatus("bed gift wounds-only fallback | " + LastCorpseDecayStatus)
EndFunction