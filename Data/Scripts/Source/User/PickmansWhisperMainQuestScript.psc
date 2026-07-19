Scriptname PickmansWhisperMainQuestScript extends Quest

; Pickman's Whisper — Slice A+B: gallery/blade bond, toast voice, knife hunger, kill satiation.
; Soft companion to Necromantic (no AAF, no compile coupling). Soft deps: F4SE, MCM.

Actor PlayerRef
Form PickmansBlade ; LVLI CustomItem template 0x22595F — not the drawn WEAP
Weapon CombatKnifeBase ; WEAP Knife 0x913CA — what GetEquippedWeapon returns for Pickman's
ObjectMod OmodBleed ; mod_Legendary_Weapon_Bleed 0x1E7C20
ObjectMod OmodStealthBlade ; mod_melee_Knife_SerratedStealth 0x187A10
Cell PickmanGalleryCell

; --- Bond (Auto = saved with the quest) ----------------------------------------
Bool Property BondStarted = False Auto
Float Property BondStartGameTime = 0.0 Auto
Bool Property IntroToastShown = False Auto
Bool Property SeenGallery = False Auto
Bool Property SeenBlade = False Auto
; True once we've seen a unique Pickman's Blade instance (name match). Template FormID
; 0x22595F is CustomItem_DoNotPlaceDirectly_* — inventory copies often have other FormIDs.
Bool Property OwnedPickmansBlade = False Auto
Float Property BondIntensity = 0.0 Auto ; bumped on valid knife kills
Float Property LastKnifeActivityGameTime = 0.0 Auto
Int Property KnifeKillCount = 0 Auto ; valid blade kills that satiated hunger
String BLADE_NAME_NEEDLE = "Pickman's Blade"
; Runtime lofted form: for Pickman's this is usually the Combat Knife WEAP base (GetEquippedWeapon
; never returns LVLI 0x22595F / the display name). Captured when akReference name matches.
; Auto so load with blade already drawn can resync against GetEquippedWeapon(0).
Form Property RuntimeBladeForm Auto
; NOT Auto — runtime only; MCM bKillDebugToasts:Debug is the source of truth (default off).
Bool DebugKillToastsCached = False
Bool DebugKillToastsCacheValid = False

; Human / safety filters (Fallout4.esm keywords)
Keyword KW_ActorTypeNPC
Keyword KW_ActorTypeHuman
Keyword KW_ActorTypeChild ; 0x1157E8 — IsChild() alone misses many settlement kids
Keyword KW_ActorTypeGhoul
Keyword KW_ActorTypeSuperMutant
Keyword KW_ActorTypeSynth
Keyword KW_ActorTypeRobot
Keyword KW_ActorTypeAnimal
Keyword KW_ActorTypeCreature
Keyword KW_ActorTypeTurret

; Kill watch — combat/crosshair victim died while blade out (primary); hit-tag is optional backup
Actor PendingKillVictim
Actor[] KillWatchList
Int KillWatchCount = 0
Int KILL_WATCH_MAX = 12
Int[] BladeTaggedIds
Int BladeTaggedCount = 0
Int BLADE_TAGGED_MAX = 24
Float LastKnifeKillRealTime = 0.0
Float CombatGraceUntilRealTime = 0.0
Float KNIFE_KILL_COOLDOWN = 1.5
Float KILL_WATCH_RADIUS = 800.0
Float KILL_CORPSE_RADIUS = 400.0 ; Necromantic-ish close corpse window
String Property LastKillIgnoreReason = "" Auto
Int LastDeathToastId = 0
Int LastHandledKillId = 0
Cell LastBladeToastCell
Int[] AliveSeenIds
Int AliveSeenCount = 0
Int ALIVE_SEEN_MAX = 32
; FormIDs first seen while NOT hostile to player — settlers you later attack still count.
; Hostiles (raiders) seen already angry never get this stamp → no satiation.
Int[] FriendlySeenIds
Int FriendlySeenCount = 0
Int FRIENDLY_SEEN_MAX = 32
Int[] BackgroundDeadIds
Int BackgroundDeadCount = 0
Int BACKGROUND_DEAD_MAX = 48
Int LastGoeAliveCount = 0
Int LastGoeDeadCount = 0
Int LastDetectCount = 0
String DEBUG_BUILD = "C2-stable" ; detection = C2-pipe filters; Settler uses nameless whisper only
; Notice poll dialogs — OFF by default now that pick path works. Enable on Debug page if needed.
Bool NoticePollDebugDefault = False
Int NoticePollCount = 0
String LastNoticeDiag = ""
String LastNoticeBreakAt = "" ; short "where it broke" for dialog header
String LastNoticePollSource = ""
String LastNearbySummary = "" ; MCM Debug "Nearby NPC scan" — updated by every PickNoticeTarget
Float LastNoticeDiagRealTime = 0.0
Float NOTICE_DIAG_MIN_GAP = 5.0 ; real seconds between poll MessageBoxes
Bool RefreshDebugBusy = False
Int KillScanTickCount = 0
Bool KillScanArmAnnounced = False
; Drawn latch — refreshed by GoE scan + OnItemEquipped
Bool BladeCurrentlyDrawn = False
Bool DrawnWeaponStateValid = False

; --- Hunger / addiction stand-in ----------------------------------------------
Float Property HungerLevel = 0.0 Auto ; 0–100 once bonded
Float Property SatedUntilGameTime = 0.0 Auto
Float LastHungerPollGameTime = 0.0
Int LastHungerBand = 0 ; 0/25/50/70/90
Bool HungerWasSated
Bool Property HungerAddictionApplied = False Auto
Bool Property HungerStatPenaltyApplied = False Auto
Spell KnifeHungerSpell
MagicEffect KnifeHungerAgiEffect
MagicEffect KnifeHungerChaEffect
GlobalVariable KnifeHungerGlobal
Bool HungerSpellLoadWarned
Float HUNGER_POLL_SECONDS = 12.0
Float BOND_POLL_SECONDS = 4.0
Float TRUST_VOICE_SECONDS = 180.0
Float NOTICE_VOICE_SECONDS = 45.0 ; C2 nearby-female comments (slow ambient backup)
Float KILL_SCAN_SECONDS = 2.0 ; killscan / fixation poll (<10s); hunger toasts gated separately by game-hour

Int TIMER_HUNGER = 1
Int TIMER_BOND = 2
Int TIMER_TRUST = 3
Int TIMER_KILL = 4 ; legacy unused
Int TIMER_NOTICE = 5 ; C2 notice voice (slow ambient)
Int TIMER_NOTICE_APPROACH = 6 ; retired — CancelTimer only (0.5s poll silenced the quest)
Int TIMER_BOOT_ARM = 7 ; post-load delayed ArmRuntimeLoops (OnInit often skips on mid-game saves)
Int TIMER_KILL_SCAN = 13 ; match Necromantic TIMER_CRAVING id class
Int TIMER_RENAME_PROMPT = 14 ; delayed renamePromptFemaleNPC (avoid clobbering recognition toast)
Float RENAME_PROMPT_DELAY = 2.5
String PendingRenamePrompt = "" ; queued ModConfig line for TIMER_RENAME_PROMPT
Actor LastButcherCorpse = None ; last valid sever target (floor corpses miss camera rays)
Float BUTCHER_CORPSE_RADIUS = 500.0 ; slightly > Necromantic 350; floor corpses need slack
Float BUTCHER_FACING_DEG = 75.0 ; yaw cone for faced-corpse fallback
Float BOOT_ARM_SECONDS = 2.0

; Vanilla anchors (Fallout4.esm)
Int FID_PICKMANS_BLADE = 0x0022595F ; LVLI CustomItem template only
Int FID_COMBAT_KNIFE = 0x000913CA ; WEAP Knife — equipped base for Pickman's
Int FID_OMOD_BLEED = 0x001E7C20 ; mod_Legendary_Weapon_Bleed (Wounding)
Int FID_OMOD_STEALTH = 0x00187A10 ; mod_melee_Knife_SerratedStealth
Int FID_PICKMAN_GALLERY = 0x000379C5

; Local forms (PickmansWhisper.esp) — low word for GetFormFromFile
Int FID_HUNGER_SPEL = 0x00000801
Int FID_HUNGER_GLOB = 0x00000802
Int FID_HUNGER_MGEF_AGI = 0x00000803
Int FID_HUNGER_MGEF_CHA = 0x00000804
Int FID_PLAYER_COMBAT_QUEST = 0x00000805 ; alias OnPlayerLoadGame lives here
Int FID_SEVER_MSG = 0x00000806 ; PW_SeverLimbMenu — Slice F butcher menu
; D0-POC / D0.5 whisper SNDRs — EndIt is BASE+0; clones follow Desperate_Audio.txt order.
Int FID_WHISPER_ENDIT = 0x00000807
Int FID_WHISPER_BASE = 0x00000807
Message SeverLimbMenu

String MOD_NAME = "PickmansWhisper"
Int LINE_FILE_MAX = 64

String[] TrustLines
Int TrustLineCount = 0
String[] HungerLines
Int HungerLineCount = 0
String[] PraiseLines
Int PraiseLineCount = 0
; C3 — hunger-staged notice banks. Content lives ONLY in the editable config .txt
; files (no hardcoded builtin copies). Stage by hunger %: 0 calm / 1 restless /
; 2 hungry / 3 starving / 4 desperate. If a file fails to load, that stage stays
; silent and the failure is surfaced (load-time error toast + MCM Debug rows).
String[] NoticeCalmLines
Int NoticeCalmCount = 0
String[] NoticeRestlessLines
Int NoticeRestlessCount = 0
String[] NoticeHungryLines
Int NoticeHungryCount = 0
String[] NoticeStarvingLines
Int NoticeStarvingCount = 0
String[] NoticeDesperateLines
Int NoticeDesperateCount = 0
String LastNoticeLine = "" ; C3 no-immediate-repeat guard (raw template, pre-name)
Int LastNoticePickIndex = -1 ; bank index from last PickNoticeLine / audio-only roll
Int LastNoticePickStage = -1
; D1 — per-stage audio maps (*_Audio.txt). Filenames only (.xwm); FormIDs via WhisperSndrIds.txt.
String[] AudioCalmLines
Int AudioCalmCount = 0
String[] AudioRestlessLines
Int AudioRestlessCount = 0
String[] AudioHungryLines
Int AudioHungryCount = 0
String[] AudioStarvingLines
Int AudioStarvingCount = 0
String[] AudioDesperateLines
Int AudioDesperateCount = 0
String AudioCalmStatus = ""
String AudioRestlessStatus = ""
String AudioHungryStatus = ""
String AudioStarvingStatus = ""
String AudioDesperateStatus = ""
String LastAudioFile = "" ; no-immediate-repeat for audio-only rolls
String[] WhisperSndrFiles
Int[] WhisperSndrFids
Int WhisperSndrCount = 0
String WhisperSndrIdsStatus = ""
; Per-stage load status for MCM Debug rows (e.g. "8 lines", "MISSING FILE",
; "READ FAILED (GoE2?)", "EMPTY"). LastStageLoadStatus is set by LoadStageBank.
String NoticeCalmStatus = ""
String NoticeRestlessStatus = ""
String NoticeHungryStatus = ""
String NoticeStarvingStatus = ""
String NoticeDesperateStatus = ""
String LastStageLoadStatus = ""
; Step-by-step load trace (path/exists/raw/parsed/RESULT), shown in one MessageBox
; via ReportNoticeLoadStatus — mirrors Necromantic PosLoadDiag / InsLoadDiag.
String NoticeLoadDiag = ""
String LastStageLoadDiag = ""
Float LastTrustToastRealTime = 0.0
Float LastHungerToastRealTime = 0.0
Float LastNoticeToastRealTime = 0.0
Float LastNoticeToastGameTime = 0.0 ; hunger whisper cadence (game days)
Float TRUST_TOAST_COOLDOWN = 8.0
Float HUNGER_TOAST_COOLDOWN = 6.0
Float PRAISE_TOAST_COOLDOWN = 2.0
Float NOTICE_TOAST_COOLDOWN = 6.0 ; legacy real-s gap (kept for probes); ambient uses NOTICE_MIN_GAME_HOURS
Float NOTICE_MIN_GAME_HOURS = 1.0 ; max ~1 ambient hunger whisper per game hour
Float NOTICE_NPC_COOLDOWN = 12.0 ; per-NPC cool after a hunger toast (does NOT block fixation)
Float LastPraiseToastRealTime = 0.0
Float LastGameResumeRealTime = 0.0 ; debounce HandleGameResume when alias + remote both fire
Int[] NoticeCoolIds
Float[] NoticeCoolTimes
Int NoticeCoolCount = 0
Int NOTICE_COOL_MAX = 16
; C4 approach is parked — do not reintroduce FindActors/timers on the notice hot
; path until ambient killscan whispers are verified working again in-game.
String Property LastNoticeStatus = "" Auto ; MCM Debug — why notice did/didn't fire

; C5 look-fixation (additive). Aim-edge counts; does not alter ambient whispers.
; Aim via GoE camera/activate — NOT Game.GetCurrentCrosshairRef (not a FO4 native).
; Voice: 1st silent / 2nd hunger-stage line / 3rd+ RecognitionLines.txt
Int FIXATION_MAX = 32
Int[] FixationIds
Int[] FixationCounts
Int[] RecognitionToastCounts ; parallel — how many RecognitionLines toasts for this FormID
Int FixationSlotCount = 0
Int LastLookFixationId = 0 ; FormID under aim last tick; 0 = none
String Property LastFixationStatus = "" Auto ; MCM Debug — last look-fixation edge
String[] RecognitionLines
Int RecognitionLineCount = 0
String LastRecognitionLine = "" ; no-immediate-repeat (raw template)
String RecognitionLoadStatus = ""
; C5 P5 — sleep recognition bank (3rd+ look while GetSleepState >= 3).
String[] SleepRecognitionLines
Int SleepRecognitionLineCount = 0
String LastSleepRecognitionLine = "" ; no-immediate-repeat (raw template)
String SleepRecognitionLoadStatus = ""
; After this many recognition toasts on one NPC (still unnamed), nudge toward MCM Victims.
Int RECOGNITION_NAME_PROMPT_AT = 3
; Loaded from ModConfig.txt — files-only, no baked mirror.
String RenamePromptFemaleNPC = ""
String NamedKillToast = ""
String NamedKillAudio = "" ; optional .xwm filename; omit until clip + SNDR exist
String ModConfigLoadStatus = ""

; Slice E2–E5 — soft Necromantic scene CustomEvents (FormID 0x800). No esp master.
; E4/E5: Named toast banks + parallel Intimacy_*_Audio.txt (same-index delivery).
Int FID_NECROMANTIC_MAIN = 0x00000800
NecromanticMainQuestScript NecroQuestRef
Bool NecroEventsRegistered = False
Bool NecroSceneActive = False
String[] IntimacyStartNamedLines
Int IntimacyStartNamedCount = 0
String LastIntimacyStartLine = "" ; no-immediate-repeat (raw template)
String IntimacyStartNamedStatus = ""
Int LastIntimacyStartPickIndex = -1
String[] IntimacyEndNamedLines
Int IntimacyEndNamedCount = 0
String LastIntimacyEndLine = "" ; no-immediate-repeat (raw template)
String IntimacyEndNamedStatus = ""
Int LastIntimacyEndPickIndex = -1
String[] IntimacyStartAudioLines
Int IntimacyStartAudioCount = 0
String IntimacyStartAudioStatus = ""
String[] IntimacyEndAudioLines
Int IntimacyEndAudioCount = 0
String IntimacyEndAudioStatus = ""
String LastIntimacyAudioFile = "" ; no-immediate-repeat for audio-only intimacy rolls
Int WHISPER_SNDR_MAX = 128 ; Desperate + Necromantic intimacy maps

; C5 P3+P4 Potential Victims — FormID ↔ player name + SetDisplayName (world).
; RefCollectionAlias is optional (fill in CK / later ESP); FormID table is save truth.
Int VICTIM_MAX = 32
Int[] VictimIds
String[] VictimNames
Int VictimSlotCount = 0
RefCollectionAlias Property VictimsHold Auto ; optional hold; AddRef when present
String Property LastVictimStatus = "" Auto ; MCM Victims — last apply / aimed status
String Property LastVictimsSummary = "" Auto ; MCM Victims — short list
; Camera target is usually None while MCM is open — cache last world aim for Victims page.
Actor LastVictimsAimActor = None
Int LastVictimsAimId = 0
String LastVictimsAimLine = "" ; pushed to sVictimAimed (survives RefreshMenu re-push)

; TargetOverrides.txt — opt-in filter gates (default off = current safe blocks).
Bool AllowChildFemalesOverride = False
Bool AllowRobotsOverride = False
String Property LastTargetOverridesStatus = "" Auto ; MCM / trace — last load result

Event OnInit()
	; May fire on attach; often does NOT re-fire for mid-game saves — see HandleGameResume
	; + alias OnPlayerLoadGame + TIMER_BOOT_ARM. Never rely on MCM Scan to start timers.
	; Real-time clock resets each FO4 launch; clear saved debounce so load is not skipped.
	LastGameResumeRealTime = 0.0
	PlayerRef = Game.GetPlayer()
	If PlayerRef
		RegisterForRemoteEvent(PlayerRef, "OnCombatStateChanged")
		RegisterForRemoteEvent(PlayerRef, "OnPlayerLoadGame")
	EndIf

	EnsurePlayerCombatQuest()
	ArmRuntimeLoops()
	ScheduleBootArm()
EndEvent

Event OnQuestInit()
	DEBUG_BUILD = "C2-stable"
	KILL_WATCH_RADIUS = 800.0
	ToastDebug("PW OnQuestInit FIRED [" + DEBUG_BUILD + "]")
	PlayerRef = Game.GetPlayer()
	InvalidateDebugToastCache()
	ResolveVanillaForms()
	EnsureHungerSpell()
	RegisterForRemoteEvent(PlayerRef, "OnPlayerLoadGame")
	RegisterForRemoteEvent(PlayerRef, "OnItemEquipped")
	RegisterForRemoteEvent(PlayerRef, "OnItemUnequipped")
	RegisterForRemoteEvent(PlayerRef, "OnItemAdded")
	RegisterForRemoteEvent(PlayerRef, "OnItemRemoved")
	RegisterForRemoteEvent(PlayerRef, "OnCombatStateChanged")
	RegisterForExternalEvent("OnMCMMenuOpen|PickmansWhisper", "OnMCMMenuOpen")
	RegisterForExternalEvent("OnMCMSettingChange|PickmansWhisper", "OnMCMSettingChange")
	; Arm timers on init/load — no MessageBox here (MCM Debug buttons only).
	EnsurePlayerCombatQuest()
	ArmRuntimeLoops()
	ScheduleBootArm()
	EnsureCombatKillHooks()
	LoadLineBanks()
	RegisterNecromanticSceneEvents()
	EnsureSeverLimbMenu()
	ResyncDrawnBladeState()
	RefreshBladeOwnershipFromEquip()
	RefreshDebugStatus()
	RefreshHungerPanel(False)
	Debug.Trace("PickmansWhisper: quest init " + DEBUG_BUILD)
	ToastDebug("Pickman's Whisper ready [" + DEBUG_BUILD + "]")
	ToastBladeDetectStatus("load")
EndEvent

; Player-alias OnPlayerLoadGame is the reliable FO4 load hook; remote Actor event is backup.
Function HandlePlayerLoadFromAlias()
	HandleGameResume("alias-load")
EndFunction

Event Actor.OnPlayerLoadGame(Actor akSender)
	HandleGameResume("remote-load")
EndEvent

; Shared resume: game load / alias load. Idempotent; safe if both fire.
Function HandleGameResume(String reason)
	Float now = Utility.GetCurrentRealTime()
	; Saved LastGameResumeRealTime can outlive a FO4 process (real-time resets on
	; launch). Only debounce when the stamp is from THIS session (stamp <= now).
	If LastGameResumeRealTime > now
		LastGameResumeRealTime = 0.0
	EndIf
	If LastGameResumeRealTime > 0.0 && (now - LastGameResumeRealTime) < 2.0
		; Duplicate alias+remote load within 2s — still re-arm + boot timer.
		EnsurePlayerCombatQuest()
		ArmRuntimeLoops()
		ScheduleBootArm()
		EnsureSeverLimbMenu()
		Return
	EndIf
	LastGameResumeRealTime = now

	; Save games persist script vars — force build id from this PEX every load
	DEBUG_BUILD = "C2-stable"
	KILL_WATCH_RADIUS = 800.0
	PlayerRef = Game.GetPlayer()
	InvalidateDebugToastCache()
	ResolveVanillaForms()
	EnsureHungerSpell()
	RegisterForRemoteEvent(PlayerRef, "OnPlayerLoadGame")
	RegisterForRemoteEvent(PlayerRef, "OnItemEquipped")
	RegisterForRemoteEvent(PlayerRef, "OnItemUnequipped")
	RegisterForRemoteEvent(PlayerRef, "OnItemAdded")
	RegisterForRemoteEvent(PlayerRef, "OnItemRemoved")
	RegisterForRemoteEvent(PlayerRef, "OnCombatStateChanged")
	RegisterForExternalEvent("OnMCMMenuOpen|PickmansWhisper", "OnMCMMenuOpen")
	RegisterForExternalEvent("OnMCMSettingChange|PickmansWhisper", "OnMCMSettingChange")
	; Arm FIRST — MCM Debug must never be required to start the notice/killscan loops.
	; No MessageBox on load (ReportNoticeLoadStatus is MCM "Test notice file load" only).
	EnsurePlayerCombatQuest()
	ArmRuntimeLoops()
	ScheduleBootArm()
	EnsureCombatKillHooks()
	LoadLineBanks()
	RegisterNecromanticSceneEvents()
	EnsureSeverLimbMenu()
	ResyncDrawnBladeState()
	RefreshBladeOwnershipFromEquip()
	SyncHungerAddictionSpell()
	LastNoticeToastRealTime = 0.0
	LastNoticeDiagRealTime = 0.0
	NoticeCoolCount = 0
	NecroSceneActive = False
	RefreshDebugStatus()
	RefreshHungerPanel(False)
	; Potential Victims summary only — SetDisplayName re-applies lazily when she is seen.
	WriteVictimsSummaryToMcm()
	Debug.Trace("PickmansWhisper: game resume (" + reason + ") " + DEBUG_BUILD)
	ToastDebug("Pickman's Whisper load [" + DEBUG_BUILD + "]")
	ToastBladeDetectStatus("load")
EndFunction

; Slice F — butcher menu MSG (key RegisterForKey lives on PlayerAlias).
Function EnsureSeverLimbMenu()
	If SeverLimbMenu
		Return
	EndIf
	SeverLimbMenu = Game.GetFormFromFile(FID_SEVER_MSG, "PickmansWhisper.esp") as Message
	If !SeverLimbMenu
		Debug.Trace("PickmansWhisper: ERROR PW_SeverLimbMenu 0x806 missing — rebuild ESP")
	EndIf
EndFunction

; Butcher aim (no timer): activate → camera → last butcher (if still facing) → one FindActors.
; Dual FindActors was the hitch before Message.Show when the camera ray missed.
Actor Function ResolveSeverCorpseAim(Bool abAllowVictimsCache = False)
	If !PlayerRef
		PlayerRef = Game.GetPlayer()
	EndIf
	; Activate before camera: corpses on the floor often miss the camera ray.
	Actor aimed = GardenOfEden2.GetLastActivateTargetRef() as Actor
	If aimed && aimed != PlayerRef && IsSeverCorpseEligible(aimed) && IsWithinButcherRange(aimed)
		LastButcherCorpse = aimed
		Return aimed
	EndIf
	ObjectReference cam = GardenOfEden3.GetCameraTargetReference()
	aimed = cam as Actor
	If aimed && aimed != PlayerRef && IsSeverCorpseEligible(aimed) && IsWithinButcherRange(aimed)
		LastButcherCorpse = aimed
		Return aimed
	EndIf
	; Reuse last butcher before any FindActors (repeat presses / slight aim wobble).
	If LastButcherCorpse && IsSeverCorpseEligible(LastButcherCorpse) && IsWithinButcherRange(LastButcherCorpse)
		If Math.abs(PlayerRef.GetHeadingAngle(LastButcherCorpse)) <= BUTCHER_FACING_DEG
			Return LastButcherCorpse
		EndIf
	EndIf
	Actor faced = GetFacedSeverCorpse()
	If faced
		LastButcherCorpse = faced
		Return faced
	EndIf
	If abAllowVictimsCache
		aimed = ResolveVictimsAimActor()
		If aimed && IsSeverCorpseEligible(aimed) && IsWithinButcherRange(aimed)
			LastButcherCorpse = aimed
			Return aimed
		EndIf
	EndIf
	Return None
EndFunction

Bool Function IsWithinButcherRange(Actor ak)
	If !ak || !PlayerRef
		Return False
	EndIf
	Return PlayerRef.GetDistance(ak) <= BUTCHER_CORPSE_RADIUS
EndFunction

; One GoE scan (dead+female+3D) — pick nearest in yaw cone. No second FindActors.
Actor Function GetFacedSeverCorpse()
	If !PlayerRef
		Return None
	EndIf
	Actor[] found = GardenOfEden.FindActors(None, None, -1, -1, PlayerRef, BUTCHER_CORPSE_RADIUS, 0, 1, -1, 1, -1, -1, None, None, "", 0, 1, 1)
	If !found || found.Length == 0
		Return None
	EndIf
	Actor best = None
	Float bestDist = BUTCHER_CORPSE_RADIUS + 1.0
	Int i = 0
	While i < found.Length
		Actor ak = found[i]
		If ak && ak != PlayerRef && IsSeverCorpseEligible(ak)
			If Math.abs(PlayerRef.GetHeadingAngle(ak)) <= BUTCHER_FACING_DEG
				Float d = PlayerRef.GetDistance(ak)
				If d < bestDist
					bestDist = d
					best = ak
				EndIf
			EndIf
		EndIf
		i += 1
	EndWhile
	Return best
EndFunction

; Aim corpse + blade → butcher Message.Show → Dismember.
; abIgnoreMenuMode: True for MCM Debug (victims aim cache + allow while MCM open).
Function TrySeverAimedCorpse(Bool abIgnoreMenuMode = False)
	; Do not soft-fail on IsInMenuMode for the hotkey — some HUD mods leave it sticky.
	If NecroSceneActive
		Debug.Notification("Pickman's Whisper: butcher unavailable during Necromantic scene")
		Return
	EndIf
	If !IsBladeEquipped()
		Debug.Notification("Pickman's Whisper: draw Pickman's Blade for the butcher menu")
		Return
	EndIf
	If !PlayerRef
		PlayerRef = Game.GetPlayer()
	EndIf
	Actor aimed = ResolveSeverCorpseAim(abIgnoreMenuMode)
	If !aimed
		Debug.Notification("Pickman's Whisper: aim / face a corpse for the butcher menu")
		Return
	EndIf
	EnsureSeverLimbMenu()
	If !SeverLimbMenu
		Debug.Notification("Pickman's Whisper: butcher menu missing — rebuild ESP")
		Debug.Trace("PickmansWhisper: ERROR TrySeverAimedCorpse no MSG 0x806")
		Return
	EndIf
	Int btn = SeverLimbMenu.Show()
	; 0 Head / 1 LArm / 2 RArm / 3 LLeg / 4 RLeg / 5 Cancel
	If btn < 0
		Debug.Notification("Pickman's Whisper: butcher Show failed (btn=" + btn + ")")
		Debug.Trace("PickmansWhisper: ERROR SeverLimbMenu.Show returned " + btn)
		Return
	EndIf
	If btn >= 5
		Return
	EndIf
	String part = SeverButtonToPart(btn)
	If !part
		Return
	EndIf
	SeverCorpseLimb(aimed, part)
EndFunction

String Function SeverButtonToPart(Int btn)
	If btn == 0
		Return "Head1"
	ElseIf btn == 1
		Return "LeftArm1"
	ElseIf btn == 2
		Return "RightArm1"
	ElseIf btn == 3
		Return "LeftLeg1"
	ElseIf btn == 4
		Return "RightLeg1"
	EndIf
	Return ""
EndFunction

Bool Function IsSeverCorpseEligible(Actor ak)
	If !ak || ak == PlayerRef
		Return False
	EndIf
	If !ak.IsDead()
		Return False
	EndIf
	If !ak.Is3DLoaded() || ak.IsDisabled()
		Return False
	EndIf
	If !IsHumanNpc(ak)
		Return False
	EndIf
	If !IsAdultFemale(ak)
		Return False
	EndIf
	Return True
EndFunction

Function SeverCorpseLimb(Actor ak, String partName)
	If !ak || !partName
		Return
	EndIf
	If !ak.Is3DLoaded()
		Debug.Notification("Pickman's Whisper: corpse 3D not loaded — try again")
		Return
	EndIf
	If ak.IsDismembered(partName)
		Debug.Notification("Pickman's Whisper: already severed")
		Return
	EndIf
	; Force dismember only — ForceBloodyMess=True gibs/explodes heads; keep False so pieces sever clean.
	ak.Dismember(partName, False, True, False)
	Debug.Notification("Pickman's Whisper: severed " + partName)
	Debug.Trace("PickmansWhisper: severed " + partName + " id=0x" + GardenOfEden.GetHexFormID(ak))
EndFunction

; MCM Debug — open butcher menu (uses victims aim cache while MCM is open).
Function DebugOpenButcherMenu()
	TrySeverAimedCorpse(True)
EndFunction

; MCM Debug — sever aimed corpse head with no limb menu (spike / verify gore).
Function DebugTestSeverAimedHead()
	If !PlayerRef
		PlayerRef = Game.GetPlayer()
	EndIf
	If !IsBladeEquipped()
		Debug.MessageBox("Pickman's Whisper\n\nDraw Pickman's Blade first.")
		Return
	EndIf
	Actor aimed = ResolveSeverCorpseAim(True)
	If !aimed
		Debug.MessageBox("Pickman's Whisper\n\nAim / face a dead adult female (or look then open MCM), then retry.")
		Return
	EndIf
	SeverCorpseLimb(aimed, "Head1")
	Debug.MessageBox("Pickman's Whisper\n\nSever head requested on aimed corpse.")
EndFunction

; Soft E2 — register Necromantic scene CustomEvents when plugin present.
Function RegisterNecromanticSceneEvents()
	NecromanticMainQuestScript necro = Game.GetFormFromFile(FID_NECROMANTIC_MAIN, "Necromantic.esp") as NecromanticMainQuestScript
	If !necro
		Debug.Trace("PickmansWhisper: Necromantic.esp absent or 0x800 cast failed — scene events not registered")
		NecroEventsRegistered = False
		NecroQuestRef = None
		Return
	EndIf
	If NecroEventsRegistered && NecroQuestRef
		UnregisterForCustomEvent(NecroQuestRef, "OnNecroSceneStart")
		UnregisterForCustomEvent(NecroQuestRef, "OnNecroSceneEnd")
	EndIf
	RegisterForCustomEvent(necro, "OnNecroSceneStart")
	RegisterForCustomEvent(necro, "OnNecroSceneEnd")
	NecroQuestRef = necro
	NecroEventsRegistered = True
	Debug.Trace("PickmansWhisper: registered OnNecroSceneStart/End on Necromantic 0x800")
EndFunction

; Necromantic payload: [0] gen Int, [1] corpse Actor, [2] formId Int, [3] name String,
; [4] hexId String, [5] craving Float, [6] unlocked Bool, [7] sated Bool, [8] witnesses Bool,
; [9] positionId String, [10] completed Bool (End only; Start always False).
Event NecromanticMainQuestScript.OnNecroSceneStart(NecromanticMainQuestScript akSender, Var[] akArgs)
	If NecroSceneActive
		Return
	EndIf
	Actor corpse = None
	If akArgs && akArgs.Length > 1
		corpse = akArgs[1] as Actor
	EndIf
	If !corpse
		Debug.Trace("PickmansWhisper: OnNecroSceneStart — no corpse in akArgs[1]; skip")
		Return
	EndIf
	NecroSceneActive = True
	MaybeSpeakNamedIntimacyEvent(corpse, True)
EndEvent

Event NecromanticMainQuestScript.OnNecroSceneEnd(NecromanticMainQuestScript akSender, Var[] akArgs)
	Actor corpse = None
	If akArgs && akArgs.Length > 1
		corpse = akArgs[1] as Actor
	EndIf
	Bool completed = False
	If akArgs && akArgs.Length > 10
		completed = akArgs[10] as Bool
	EndIf
	; E5 — speak before clearing latch (same named-victim filter as start).
	If corpse
		MaybeSpeakNamedIntimacyEvent(corpse, False)
	EndIf
	NecroSceneActive = False
	Debug.Trace("PickmansWhisper: OnNecroSceneEnd completed=" + completed)
EndEvent

; Named Potential Victim + iVoiceDelivery (0 toast+audio / 1 audio / 2 toast).
; abStart=True → Start banks; False → End banks. Same-index toast/audio like notice D1.
Function MaybeSpeakNamedIntimacyEvent(Actor partner, Bool abStart)
	If !partner
		Return
	EndIf
	String overrideName = GetVictimOverrideName(partner)
	If !overrideName
		Return
	EndIf
	If !IsVoiceEnabled()
		Return
	EndIf
	If !IsVoiceWeaponReady()
		Return
	EndIf
	Int mode = GetVoiceDeliveryMode()
	If mode == 1
		Int aIdx = PickIntimacyAudioIndex(abStart)
		If aIdx < 0
			Return
		EndIf
		PlayIntimacyAudioAt(abStart, aIdx)
		Debug.Trace("PickmansWhisper: intimacy audio-only idx=" + aIdx + " start=" + abStart)
		Return
	EndIf
	Int tIdx = PickIntimacyNamedIndex(abStart)
	If tIdx < 0
		If abStart
			Debug.Notification("Pickman's Whisper: Intimacy_Start_Named.txt not loaded")
			Debug.Trace("PickmansWhisper: ERROR intimacy start bank empty — " + IntimacyStartNamedStatus)
		Else
			Debug.Notification("Pickman's Whisper: Intimacy_End_Named.txt not loaded")
			Debug.Trace("PickmansWhisper: ERROR intimacy end bank empty — " + IntimacyEndNamedStatus)
		EndIf
		Return
	EndIf
	String toastTemplate = ""
	If abStart
		toastTemplate = IntimacyStartNamedLines[tIdx]
	Else
		toastTemplate = IntimacyEndNamedLines[tIdx]
	EndIf
	String line = ApplyNamePlaceholder(toastTemplate, overrideName)
	If !line || GardenOfEden.StrLength(line) < 1
		Return
	EndIf
	ShowVoiceToast(line)
	If mode == 0
		PlayIntimacyAudioAt(abStart, tIdx)
	EndIf
	Debug.Trace("PickmansWhisper: named intimacy voice idx=" + tIdx + " start=" + abStart + " | " + line)
EndFunction

; PlayerCombat quest owns the alias OnPlayerLoadGame hook. Start Game Enabled does
; not always start new quests on mid-game saves — force it so load arming works.
Function EnsurePlayerCombatQuest()
	Quest pq = Game.GetFormFromFile(FID_PLAYER_COMBAT_QUEST, "PickmansWhisper.esp") as Quest
	If !pq
		Debug.Trace("PickmansWhisper: ERROR PlayerCombat quest 0x805 missing from esp")
		Return
	EndIf
	If !pq.IsRunning()
		pq.Start()
		Debug.Trace("PickmansWhisper: started PlayerCombat quest (load arming)")
	EndIf
EndFunction

; Bond / hunger / trust / notice / kill-scan — always-on loops. Call on init, load, bond.
Function ArmRuntimeLoops()
	StartBondPoll()
	StartHungerPoll()
	StartTrustVoice()
	StartNoticeVoice()
	CancelTimer(TIMER_NOTICE_APPROACH) ; kill any leftover C4 timer from older pex
	StartKillScanLoop()
EndFunction

; StartTimer during early load can be dropped; re-arm once after BOOT_ARM_SECONDS.
Function ScheduleBootArm()
	CancelTimer(TIMER_BOOT_ARM)
	StartTimer(BOOT_ARM_SECONDS, TIMER_BOOT_ARM)
EndFunction

Event Actor.OnItemEquipped(Actor akSender, Form akBaseObject, ObjectReference akReference)
	Weapon asW = akBaseObject as Weapon
	If !asW
		If FormLooksLikePickmansBlade(akBaseObject, akReference)
			RuntimeBladeForm = akBaseObject
			MarkOwnedBlade("equipped")
		EndIf
		Return
	EndIf
	DrawnWeaponStateValid = True
	Bool isPickmans = FormLooksLikePickmansBlade(akBaseObject, akReference)
	If !isPickmans && FormIsCombatKnife(akBaseObject)
		; akReference often None — GoE sees the real equipped instance name/mods
		isPickmans = (FindEquippedPickmansBladeIndex() >= 0)
	EndIf
	If isPickmans
		BladeCurrentlyDrawn = True
		RuntimeBladeForm = akBaseObject
		MarkOwnedBlade("equipped")
		Int idx = FindEquippedPickmansBladeIndex()
		String nm = "(goe)"
		If idx >= 0
			nm = GardenOfEden.GetNthItemName(PlayerRef, idx)
		EndIf
		ToastDebug("PW debug: blade DRAWN [" + DEBUG_BUILD + "] " + nm)
	Else
		BladeCurrentlyDrawn = False
		ClearKillWatchForWeaponSwap()
		ToastDebug("PW debug: other weapon DRAWN — " + akBaseObject.GetName())
	EndIf
EndEvent

Event Actor.OnItemUnequipped(Actor akSender, Form akBaseObject, ObjectReference akReference)
	; Drawn state cleared only when another weapon is equipped (FO4 unequip/re-equip flicker).
EndEvent

Event Actor.OnItemAdded(Actor akSender, Form akBaseItem, Int aiItemCount, ObjectReference akItemReference, ObjectReference akSourceContainer)
	If FormLooksLikePickmansBlade(akBaseItem, akItemReference)
		If akBaseItem as Weapon
			RuntimeBladeForm = akBaseItem
		EndIf
		MarkOwnedBlade("added")
	EndIf
EndEvent

Event Actor.OnItemRemoved(Actor akSender, Form akBaseItem, Int aiItemCount, ObjectReference akItemReference, ObjectReference akDestContainer)
	If FormLooksLikePickmansBlade(akBaseItem, akItemReference) || IsPickmansBladeForm(akBaseItem)
		If !IsBladeEquipped() && !HasTemplateBlade()
			OwnedPickmansBlade = False
			Debug.Trace("PickmansWhisper: blade ownership cleared (removed)")
		EndIf
	EndIf
EndEvent

Event OnTimer(Int aiTimerID)
	If aiTimerID == TIMER_BOND
		RunBondPoll()
		StartBondPoll()
	ElseIf aiTimerID == TIMER_HUNGER
		RunHungerTick()
		StartHungerPoll()
	ElseIf aiTimerID == TIMER_TRUST
		MaybeSpeakTrustLine()
		StartTrustVoice()
	ElseIf aiTimerID == TIMER_NOTICE
		MaybeSpeakNoticeLine("timer")
		StartNoticeVoice()
	ElseIf aiTimerID == TIMER_NOTICE_APPROACH
		; Legacy id — cancel and ignore (C4 parked; 0.5s poll silenced the quest).
		CancelTimer(TIMER_NOTICE_APPROACH)
	ElseIf aiTimerID == TIMER_BOOT_ARM
		; Delayed load arm — catches mid-game saves where OnInit skipped and early
		; StartTimer was dropped during the loading screen.
		EnsurePlayerCombatQuest()
		ArmRuntimeLoops()
		Debug.Trace("PickmansWhisper: boot-arm timer fired " + DEBUG_BUILD)
	ElseIf aiTimerID == TIMER_KILL || aiTimerID == TIMER_KILL_SCAN
		; Re-arm FIRST — if RunKillScanTick aborts (bad native / stack dump), the
		; quest must not go silent the way a mid-tick crash killed ambient before.
		StartKillScanLoop()
		RunKillScanTick()
	ElseIf aiTimerID == TIMER_RENAME_PROMPT
		; Fired after recognition toast so FO4 HUD does not replace the line bank toast.
		If PendingRenamePrompt
			ShowVoiceToast(PendingRenamePrompt)
			Debug.Trace("PickmansWhisper: name-her prompt (delayed) | " + PendingRenamePrompt)
			PendingRenamePrompt = ""
		EndIf
	EndIf
EndEvent

Event Actor.OnDeath(Actor akSender, Actor akKiller)
	ToastHumanKillDetected(akSender, "OnDeath")
	HandlePotentialKnifeKill(akSender, akKiller)
EndEvent

; Soft backup only — quiet settler kills often never raise combat state.
Event Actor.OnCombatStateChanged(Actor akSender, Actor akTarget, Int aeCombatState)
	If akSender != PlayerRef
		Return
	EndIf
	If aeCombatState == 1 && akTarget
		TrackLivingNear(akTarget)
	EndIf
EndEvent

Event OnHit(ObjectReference akTarget, ObjectReference akAggressor, Form akSource, Projectile akProjectile, Bool abPowerAttack, Bool abSneakAttack, Bool abBashAttack, Bool abHitBlocked, String asMaterialName)
	HandleBladeHit(akTarget, akAggressor, akSource)
EndEvent

Function ResolveVanillaForms()
	If !PickmansBlade
		PickmansBlade = Game.GetFormFromFile(FID_PICKMANS_BLADE, "Fallout4.esm")
		If PickmansBlade
			Debug.Trace("PickmansWhisper: blade LVLI template loaded")
		Else
			Debug.Trace("PickmansWhisper: ERROR Pickman's Blade LVLI missing")
		EndIf
	EndIf
	If !CombatKnifeBase
		CombatKnifeBase = Game.GetFormFromFile(FID_COMBAT_KNIFE, "Fallout4.esm") as Weapon
		If CombatKnifeBase
			Debug.Trace("PickmansWhisper: Combat Knife WEAP loaded")
		Else
			Debug.Trace("PickmansWhisper: ERROR Combat Knife WEAP 0x913CA missing")
		EndIf
	EndIf
	If !OmodBleed
		OmodBleed = Game.GetFormFromFile(FID_OMOD_BLEED, "Fallout4.esm") as ObjectMod
	EndIf
	If !OmodStealthBlade
		OmodStealthBlade = Game.GetFormFromFile(FID_OMOD_STEALTH, "Fallout4.esm") as ObjectMod
	EndIf
	If !PickmanGalleryCell
		PickmanGalleryCell = Game.GetFormFromFile(FID_PICKMAN_GALLERY, "Fallout4.esm") as Cell
		If PickmanGalleryCell
			Debug.Trace("PickmansWhisper: gallery cell loaded")
		Else
			Debug.Trace("PickmansWhisper: ERROR PickmanGallery01 missing")
		EndIf
	EndIf
EndFunction

; --- Bond / trigger ------------------------------------------------------------

Function StartBondPoll()
	CancelTimer(TIMER_BOND)
	StartTimer(BOND_POLL_SECONDS, TIMER_BOND)
EndFunction

Function RunBondPoll()
	If !PlayerRef
		PlayerRef = Game.GetPlayer()
	EndIf
	If !PlayerRef || Utility.IsInMenuMode()
		Return
	EndIf
	ResolveVanillaForms()

	; Bond poll survives save load — arm/run kill scan here (SingleUpdate does not).
	StartKillScanLoop()
	RunKillScanTick()

	Bool inGallery = IsPlayerInGallery()
	Bool hasBlade = PlayerHasBlade()
	Bool equipped = IsBladeEquipped()

	; Scene/cell change blade status toast (Caprica has no Location type for OnLocationChange)
	Cell curCell = PlayerRef.GetParentCell()
	If curCell && curCell != LastBladeToastCell
		LastBladeToastCell = curCell
		ToastBladeDetectStatus("scene")
	EndIf

	If inGallery && !SeenGallery
		SeenGallery = True
		Debug.Trace("PickmansWhisper: entered Pickman Gallery")
	EndIf
	If hasBlade && !SeenBlade
		SeenBlade = True
		Debug.Trace("PickmansWhisper: acquired Pickman's Blade")
	EndIf

	If !BondStarted && (inGallery || hasBlade || equipped)
		StartBond("trigger")
	EndIf
EndFunction

Bool Function IsPlayerInGallery()
	If !PlayerRef
		Return False
	EndIf
	Cell cur = PlayerRef.GetParentCell()
	If !cur
		Return False
	EndIf
	If PickmanGalleryCell && cur == PickmanGalleryCell
		Return True
	EndIf
	Int id = cur.GetFormID()
	Int low = id - (id / 0x01000000) * 0x01000000
	Return low == FID_PICKMAN_GALLERY
EndFunction

Bool Function NameLooksLikePickmansBlade(String n)
	If n == ""
		Return False
	EndIf
	Return StringUtil.Find(n, BLADE_NAME_NEEDLE) >= 0
EndFunction

Bool Function FormIsCombatKnife(Form f)
	If !f
		Return False
	EndIf
	If CombatKnifeBase && (f == CombatKnifeBase || f.GetFormID() == CombatKnifeBase.GetFormID())
		Return True
	EndIf
	; Fallback FormID if resolve failed
	Int id = f.GetFormID()
	Int low = id - (id / 0x01000000) * 0x01000000
	Return low == FID_COMBAT_KNIFE
EndFunction

; GoE inventory slot: Pickman's = display name OR (Knife base + bleed + stealth OMODs).
Bool Function InventorySlotIsPickmansBlade(Int aiItemIndex)
	If !PlayerRef || aiItemIndex < 0
		Return False
	EndIf
	String itemName = GardenOfEden.GetNthItemName(PlayerRef, aiItemIndex)
	If NameLooksLikePickmansBlade(itemName)
		Return True
	EndIf
	Int formId = GardenOfEden.GetNthItemFormID(PlayerRef, aiItemIndex)
	Int low = formId - (formId / 0x01000000) * 0x01000000
	If low != FID_COMBAT_KNIFE && !(CombatKnifeBase && formId == CombatKnifeBase.GetFormID())
		Return False
	EndIf
	; CustomItemMods_DN101PickmansBlade: bleed legendary + serrated stealth
	If OmodBleed && OmodStealthBlade
		If GardenOfEden.GetNthItemHasMod(PlayerRef, aiItemIndex, OmodBleed) > 0
			If GardenOfEden.GetNthItemHasMod(PlayerRef, aiItemIndex, OmodStealthBlade) > 0
				Return True
			EndIf
		EndIf
	EndIf
	; Legendary-only soft match on knife (weaker — any Wounding knife)
	ObjectMod leg = GardenOfEden.GetNthItemLegendaryMod(PlayerRef, aiItemIndex)
	If OmodBleed && leg && leg == OmodBleed && OmodStealthBlade
		If GardenOfEden.GetNthItemHasMod(PlayerRef, aiItemIndex, OmodStealthBlade) > 0
			Return True
		EndIf
	EndIf
	Return False
EndFunction

; Returns equipped inventory index of Pickman's Blade, or -1.
Int Function FindEquippedPickmansBladeIndex()
	If !PlayerRef
		Return -1
	EndIf
	ResolveVanillaForms()
	; Fast path: name lookup
	Int[] byName = GardenOfEden.GetItemIndexesByName(PlayerRef, BLADE_NAME_NEEDLE, False, False)
	If byName
		Int n = byName.Length
		Int i = 0
		While i < n
			Int idx = byName[i]
			If GardenOfEden.GetNthItemIsEquipped(PlayerRef, idx) > 0
				Return idx
			EndIf
			i += 1
		EndWhile
	EndIf
	; Equipped slots: Combat Knife + Pickman's OMOD pair
	Int[] eq = GardenOfEden.GetEquippedItemIndexes(PlayerRef)
	If !eq
		Return -1
	EndIf
	Int e = 0
	While e < eq.Length
		Int idx = eq[e]
		If GardenOfEden.GetNthItemIsEquipped(PlayerRef, idx) > 0
			If InventorySlotIsPickmansBlade(idx)
				Return idx
			EndIf
		EndIf
		e += 1
	EndWhile
	Return -1
EndFunction

Bool Function PlayerOwnsPickmansBladeInstance()
	If !PlayerRef
		Return False
	EndIf
	ResolveVanillaForms()
	Int[] byName = GardenOfEden.GetItemIndexesByName(PlayerRef, BLADE_NAME_NEEDLE, False, False)
	If byName && byName.Length > 0
		Return True
	EndIf
	; Scan a bounded inventory window for OMOD pair (avoid huge bags)
	Int count = GardenOfEden.GetInventoryItemCount(PlayerRef)
	If count <= 0
		Return False
	EndIf
	If count > 80
		count = 80
	EndIf
	Int i = 0
	While i < count
		If InventorySlotIsPickmansBlade(i)
			Return True
		EndIf
		i += 1
	EndWhile
	Return False
EndFunction

; Legendary uniques: GetEquippedWeapon name is often "Combat Knife".
Bool Function FormLooksLikePickmansBlade(Form f, ObjectReference akRef)
	If IsPickmansBladeForm(f)
		Return True
	EndIf
	If akRef
		If NameLooksLikePickmansBlade(akRef.GetDisplayName())
			Return True
		EndIf
		If NameLooksLikePickmansBlade(akRef.GetName())
			Return True
		EndIf
		; F4SE OMOD scan on the instance ref
		If FormIsCombatKnife(f) && RefHasPickmansMods(akRef)
			Return True
		EndIf
	EndIf
	If FormIsCombatKnife(f) && FindEquippedPickmansBladeIndex() >= 0
		Return True
	EndIf
	Return False
EndFunction

Bool Function RefHasPickmansMods(ObjectReference akRef)
	If !akRef || !OmodBleed || !OmodStealthBlade
		Return False
	EndIf
	ObjectMod[] mods = akRef.GetAllMods()
	If !mods || mods.Length == 0
		Return False
	EndIf
	Bool hasBleed = False
	Bool hasStealth = False
	Int i = 0
	While i < mods.Length
		ObjectMod m = mods[i]
		If m == OmodBleed
			hasBleed = True
		ElseIf m == OmodStealthBlade
			hasStealth = True
		EndIf
		i += 1
	EndWhile
	Return hasBleed && hasStealth
EndFunction

Bool Function IsPickmansBladeForm(Form f)
	If !f
		Return False
	EndIf
	If PickmansBlade && (f == PickmansBlade || f.GetFormID() == PickmansBlade.GetFormID())
		Return True
	EndIf
	If NameLooksLikePickmansBlade(f.GetName())
		Return True
	EndIf
	Return False
EndFunction

Bool Function HasTemplateBlade()
	If !PlayerRef || !PickmansBlade
		Return False
	EndIf
	Return PlayerRef.GetItemCount(PickmansBlade) > 0
EndFunction

Function MarkOwnedBlade(String reason)
	OwnedPickmansBlade = True
	If !SeenBlade
		SeenBlade = True
		Debug.Trace("PickmansWhisper: acquired Pickman's Blade (" + reason + ")")
	EndIf
	If !BondStarted
		StartBond(reason)
	EndIf
EndFunction

Function RefreshBladeOwnershipFromEquip()
	If IsBladeEquipped()
		MarkOwnedBlade("equip-scan")
	ElseIf HasTemplateBlade()
		MarkOwnedBlade("template-count")
	EndIf
EndFunction

String Function GetEquippedWeaponName()
	If !PlayerRef
		Return ""
	EndIf
	Weapon w = PlayerRef.GetEquippedWeapon(0)
	If !w
		Return ""
	EndIf
	Return w.GetName()
EndFunction

Bool Function PlayerHasBlade()
	If !PlayerRef
		Return False
	EndIf
	If OwnedPickmansBlade
		Return True
	EndIf
	If PlayerOwnsPickmansBladeInstance()
		OwnedPickmansBlade = True
		Return True
	EndIf
	If HasTemplateBlade()
		Return True
	EndIf
	If IsBladeEquipped()
		Return True
	EndIf
	Return False
EndFunction

Bool Function WeaponIsRanged(Weapon w)
	If !w
		Return False
	EndIf
	Ammo a = w.GetAmmo()
	Return a != None
EndFunction

; Only the active hand from GetEquippedWeapon(0) — do NOT scan GoE (guns in inv can look "equipped").
Bool Function ActiveWeaponIsRanged()
	If !PlayerRef
		Return False
	EndIf
	Return WeaponIsRanged(PlayerRef.GetEquippedWeapon(0))
EndFunction

; Recompute drawn state via GoE (authoritative for legendary instance name/mods).
Bool Function ResyncDrawnBladeState()
	If !PlayerRef
		BladeCurrentlyDrawn = False
		DrawnWeaponStateValid = False
		Return False
	EndIf
	ResolveVanillaForms()
	Weapon w = PlayerRef.GetEquippedWeapon(0)
	If WeaponIsRanged(w)
		BladeCurrentlyDrawn = False
		DrawnWeaponStateValid = True
		Return False
	EndIf
	Int idx = FindEquippedPickmansBladeIndex()
	If idx >= 0
		BladeCurrentlyDrawn = True
		DrawnWeaponStateValid = True
		OwnedPickmansBlade = True
		If w
			RuntimeBladeForm = w
		ElseIf CombatKnifeBase
			RuntimeBladeForm = CombatKnifeBase
		EndIf
		Return True
	EndIf
	BladeCurrentlyDrawn = False
	DrawnWeaponStateValid = True
	Return False
EndFunction

Bool Function IsBladeEquipped()
	; Drawn Pickman's only — GoE instance scan; never LVLI template / inventory count alone.
	If !PlayerRef
		Return False
	EndIf
	Weapon w = PlayerRef.GetEquippedWeapon(0)
	If WeaponIsRanged(w)
		BladeCurrentlyDrawn = False
		DrawnWeaponStateValid = True
		Return False
	EndIf
	; Always prefer live GoE scan (handles load + Combat Knife base name)
	Int idx = FindEquippedPickmansBladeIndex()
	If idx >= 0
		BladeCurrentlyDrawn = True
		DrawnWeaponStateValid = True
		OwnedPickmansBlade = True
		Return True
	EndIf
	BladeCurrentlyDrawn = False
	DrawnWeaponStateValid = True
	Return False
EndFunction

; Alias for kill checks — no sheath / empty-hand grace. Gun or fists = not ready.
Bool Function IsBladeKillWeaponReady()
	Return IsBladeEquipped()
EndFunction

; Voice / whisper gate — same drawn-blade check as kills; do not reimplement GoE scan.
; All toast + notice audio must call this (not inventory ownership alone).
Bool Function IsVoiceWeaponReady()
	Return IsBladeEquipped()
EndFunction

String Function GetDrawnWeaponDebugName()
	If !PlayerRef
		Return "(no player)"
	EndIf
	Int idx = FindEquippedPickmansBladeIndex()
	If idx >= 0
		Return "PICKMANS=" + GardenOfEden.GetNthItemName(PlayerRef, idx)
	EndIf
	String latch = "latch=?"
	If DrawnWeaponStateValid
		If BladeCurrentlyDrawn
			latch = "latch=BLADE"
		Else
			latch = "latch=no"
		EndIf
	EndIf
	Weapon w = PlayerRef.GetEquippedWeapon(0)
	If WeaponIsRanged(w)
		String rn = "(ranged)"
		If w
			rn = w.GetName()
			If rn == ""
				rn = "(ranged id=" + w.GetFormID() + ")"
			EndIf
		EndIf
		Return latch + " GUN=" + rn
	EndIf
	If !w
		Return latch + " (none/fists)"
	EndIf
	String n = w.GetName()
	If n == ""
		Return latch + " (unnamed id=" + w.GetFormID() + ")"
	EndIf
	Return latch + " " + n
EndFunction

; Debug kill/scan toasts — MCM "Kill debug toasts" (default OFF). Gameplay voice stays separate.
Function InvalidateDebugToastCache()
	DebugKillToastsCacheValid = False
EndFunction

Bool Function IsKillDebugToastsEnabled()
	If DebugKillToastsCacheValid
		Return DebugKillToastsCached
	EndIf
	Bool on = False
	If MCM.IsInstalled()
		on = MCM.GetModSettingBool(MOD_NAME, "bKillDebugToasts:Debug")
	EndIf
	DebugKillToastsCached = on
	DebugKillToastsCacheValid = True
	Return on
EndFunction

Function ToastDebug(String msg)
	Debug.Trace("PickmansWhisper: " + msg)
	If IsKillDebugToastsEnabled()
		Debug.Notification(msg)
	EndIf
EndFunction

; Blade status toast (load/scene) — debug only
Function ToastBladeDetectStatus(String context)
	Bool owned = OwnedPickmansBlade || HasTemplateBlade() || PlayerHasBlade()
	Bool equipped = IsBladeEquipped()
	String msg = "PW debug [" + DEBUG_BUILD + "] (" + context + "): blade "
	If equipped
		msg += "EQUIPPED"
	ElseIf owned
		msg += "owned, not equipped"
	Else
		msg += "NOT detected"
	EndIf
	ToastDebug(msg)
	; Blade toasts prove bond poll / load is alive — force-arm kill scan there
	StartKillScanLoop()
	AnnounceKillScanArmed()
EndFunction

Function StartBond(String reason)
	If BondStarted
		Return
	EndIf
	BondStarted = True
	Float now = Utility.GetCurrentGameTime()
	BondStartGameTime = now
	If LastKnifeActivityGameTime <= 0.0
		LastKnifeActivityGameTime = now
	EndIf
	LastHungerPollGameTime = now
	Debug.Trace("PickmansWhisper: bond started (" + reason + ")")
	If !IntroToastShown
		IntroToastShown = True
		String line = PickTrustLine()
		If line == ""
			line = "Something in the gallery leans closer... glad you came."
		EndIf
	ToastVoice(line)
	EndIf
	ArmRuntimeLoops()
	RefreshHungerPanel(False)
	If !RefreshDebugBusy
		RefreshDebugStatus()
	EndIf
EndFunction

; --- Trust voice ---------------------------------------------------------------

Function StartTrustVoice()
	CancelTimer(TIMER_TRUST)
	If !IsVoiceEnabled()
		Return
	EndIf
	StartTimer(TRUST_VOICE_SECONDS, TIMER_TRUST)
EndFunction

Function MaybeSpeakTrustLine()
	If !BondStarted || !IsVoiceEnabled()
		Return
	EndIf
	If Utility.IsInMenuMode()
		Return
	EndIf
	If !IsVoiceWeaponReady()
		Return
	EndIf
	Float now = Utility.GetCurrentRealTime()
	If (now - LastTrustToastRealTime) < TRUST_TOAST_COOLDOWN
		Return
	EndIf
	String line = PickTrustLine()
	If line != ""
		ToastVoice(line)
	EndIf
EndFunction

Function StartNoticeVoice()
	CancelTimer(TIMER_NOTICE)
	If !IsVoiceEnabled()
		Return
	EndIf
	StartTimer(NOTICE_VOICE_SECONDS, TIMER_NOTICE)
EndFunction

Bool Function IsNoticePollDebugEnabled()
	If MCM.IsInstalled()
		Return MCM.GetModSettingBool(MOD_NAME, "bNoticePollDebug:Debug")
	EndIf
	Return NoticePollDebugDefault
EndFunction

Function ShowNoticePollDialog(String body)
	If !IsNoticePollDebugEnabled()
		Return
	EndIf
	If Utility.IsInMenuMode()
		Return
	EndIf
	Float now = Utility.GetCurrentRealTime()
	If (now - LastNoticeDiagRealTime) < NOTICE_DIAG_MIN_GAP
		Return
	EndIf
	LastNoticeDiagRealTime = now
	DEBUG_BUILD = "C2-stable"
	Debug.Trace("PickmansWhisper: notice pipe | " + body)
	Debug.MessageBox(body)
EndFunction

Function WriteNearbyStatusToMcm()
	If !MCM.IsInstalled()
		Return
	EndIf
	If !LastNearbySummary
		MCM.SetModSettingString(MOD_NAME, "sNearby:Debug", "(awaiting poll)")
	Else
		MCM.SetModSettingString(MOD_NAME, "sNearby:Debug", LastNearbySummary)
	EndIf
EndFunction

Function WriteNoticeStatusToMcm()
	If !MCM.IsInstalled()
		Return
	EndIf
	If !LastNoticeStatus
		MCM.SetModSettingString(MOD_NAME, "sNotice:Debug", "(none yet)")
	Else
		MCM.SetModSettingString(MOD_NAME, "sNotice:Debug", LastNoticeStatus)
	EndIf
EndFunction

; Full YES/NO checklist — first failing check is the break point for this actor.
String Function FormatNoticeActorChecklist(Actor ak)
	If !ak || ak == PlayerRef
		Return "  (invalid actor)\n"
	EndIf
	String nm = GetActorDisplayName(ak)
	If !nm
		nm = "?"
	EndIf
	Int dist = 0
	If PlayerRef
		dist = PlayerRef.GetDistance(ak) as Int
	EndIf
	String out = "#" + nm + " d=" + dist + "\n"
	String fail = ""

	If ak.IsDead()
		out += "  dead=YES <<\n"
		If !fail
			fail = "dead"
		EndIf
	Else
		out += "  dead=no\n"
	EndIf
	If ak.IsDisabled()
		out += "  disabled=YES <<\n"
		If !fail
			fail = "disabled"
		EndIf
	Else
		out += "  disabled=no\n"
	EndIf
	If PlayerRef && PlayerRef.GetDistance(ak) > KILL_WATCH_RADIUS
		out += "  far=YES (>" + (KILL_WATCH_RADIUS as Int) + ") <<\n"
		If !fail
			fail = "too far"
		EndIf
	Else
		out += "  far=no\n"
	EndIf
	If IsNoticeOnCooldown(ak)
		out += "  npcCool=YES <<\n"
		If !fail
			fail = "npc cooldown"
		EndIf
	Else
		out += "  npcCool=no\n"
	EndIf
	If IsChildNpc(ak)
		If IsChildTargetAllowed()
			out += "  child=YES (allowed by TargetOverrides)\n"
		Else
			out += "  child=YES <<\n"
			If !fail
				fail = "child"
			EndIf
		EndIf
	Else
		out += "  child=no\n"
	EndIf
	If ak.IsPlayerTeammate()
		out += "  teammate=YES <<\n"
		If !fail
			fail = "teammate"
		EndIf
	Else
		out += "  teammate=no\n"
	EndIf

	Bool ess = IsStoryEssential(ak)
	Bool prot = False
	ActorBase base = ak.GetLeveledActorBase()
	If base
		prot = base.IsProtected()
	EndIf
	If ess
		out += "  essential=YES <<\n"
		If !fail
			fail = "essential"
		EndIf
	Else
		out += "  essential=no\n"
	EndIf
	If prot
		out += "  protected=YES (ok for notice)\n"
	Else
		out += "  protected=no\n"
	EndIf

	EnsureFilterKeywords()
	If KW_ActorTypeAnimal && ak.HasKeyword(KW_ActorTypeAnimal)
		out += "  animal=YES <<\n"
		If !fail
			fail = "animal"
		EndIf
	Else
		out += "  animal=no\n"
	EndIf
	If KW_ActorTypeCreature && ak.HasKeyword(KW_ActorTypeCreature)
		out += "  creature=YES <<\n"
		If !fail
			fail = "creature"
		EndIf
	Else
		out += "  creature=no\n"
	EndIf
	If KW_ActorTypeRobot && ak.HasKeyword(KW_ActorTypeRobot)
		If IsRobotTargetAllowed()
			out += "  robot=YES (allowed by TargetOverrides)\n"
		Else
			out += "  robot=YES <<\n"
			If !fail
				fail = "robot"
			EndIf
		EndIf
	Else
		out += "  robot=no\n"
	EndIf
	If KW_ActorTypeGhoul && ak.HasKeyword(KW_ActorTypeGhoul)
		out += "  ghoul=YES <<\n"
		If !fail
			fail = "ghoul"
		EndIf
	Else
		out += "  ghoul=no\n"
	EndIf
	If KW_ActorTypeSuperMutant && ak.HasKeyword(KW_ActorTypeSuperMutant)
		out += "  supermutant=YES <<\n"
		If !fail
			fail = "supermutant"
		EndIf
	Else
		out += "  supermutant=no\n"
	EndIf
	If KW_ActorTypeSynth && ak.HasKeyword(KW_ActorTypeSynth)
		out += "  synth=YES (allowed for notice)\n"
	Else
		out += "  synth=no\n"
	EndIf

	Int sex = -1
	If base
		sex = base.GetSex()
	EndIf
	If sex == 1
		out += "  female=YES sex=1\n"
	Else
		out += "  female=NO sex=" + sex + " <<\n"
		If !fail
			fail = "not female"
		EndIf
	EndIf

	If IsHumanNpc(ak)
		out += "  knifeHuman=YES\n"
	Else
		out += "  knifeHuman=NO (notice uses exclusions)\n"
	EndIf

	If !fail
		out += "  → PASS\n"
	Else
		out += "  → FAIL: " + fail + "\n"
	EndIf
	Return out
EndFunction

Function MaybeSpeakNoticeLine(String source)
	; Proven C3 path — keep boring. Detection lives in ExplainNoticeReject / PickNoticeTarget.
	; Do not add FindActors / approach timers here until ambient toasts are verified again.
	NoticePollCount += 1
	LastNoticePollSource = source
	LastNoticeBreakAt = ""
	DEBUG_BUILD = "C2-stable"

	If !PlayerRef
		PlayerRef = Game.GetPlayer()
	EndIf
	If !PlayerRef
		LastNoticeStatus = "skip: no player"
		WriteNoticeStatusToMcm()
		Return
	EndIf
	If !BondStarted
		LastNoticeStatus = "skip: not bonded"
		WriteNoticeStatusToMcm()
		Return
	EndIf
	If !IsVoiceEnabled()
		LastNoticeStatus = "skip: voice off"
		WriteNoticeStatusToMcm()
		Return
	EndIf
	If !IsVoiceWeaponReady()
		LastNoticeStatus = "skip: Pickman's Blade not drawn"
		WriteNoticeStatusToMcm()
		Return
	EndIf

	; Ambient hunger cadence: at most once per NOTICE_MIN_GAME_HOURS (game time).
	; Fixation has its own look-edge path and must not share this gate.
	Float gnow = Utility.GetCurrentGameTime()
	If LastNoticeToastGameTime > 0.0
		Float hoursSince = (gnow - LastNoticeToastGameTime) * 24.0
		If hoursSince < NOTICE_MIN_GAME_HOURS
			LastNoticeStatus = "skip: hunger hour cooldown"
			WriteNoticeStatusToMcm()
			Return
		EndIf
	EndIf

	Actor target = PickNoticeTarget()
	If !target
		WriteNoticeStatusToMcm()
		WriteNearbyStatusToMcm()
		Return
	EndIf

	String npcName = GetActorDisplayName(target)
	Int stage = GetNoticeStage()
	Int mode = GetVoiceDeliveryMode() ; 0 toast+audio / 1 audio only / 2 toast only

	; --- Audio only: roll audio bank, no toast text ---
	If mode == 1
		Int aIdx = PickNoticeAudioIndex(stage)
		If aIdx < 0
			LastNoticeStatus = "skip: audio-only stage " + (stage + 1) + " map empty/mismatch"
			WriteNoticeStatusToMcm()
			WriteNearbyStatusToMcm()
			Return
		EndIf
		PlayNoticeAudio(stage, aIdx)
		MarkNoticeCooldown(target)
		LastNoticeStatus = "ok: audio-only idx=" + aIdx
		WriteNoticeStatusToMcm()
		WriteNearbyStatusToMcm()
		Return
	EndIf

	String line = PickNoticeLine(npcName)
	If !line || GardenOfEden.StrLength(line) < 1
		; Files-only: skip without arming cooldown so a later load can speak.
		LastNoticeStatus = "skip: stage " + (stage + 1) + " (" + GetNoticeStageName(stage) + ") not loaded"
		WriteNoticeStatusToMcm()
		WriteNearbyStatusToMcm()
		Return
	EndIf

	; Toast FIRST — do not put MCM / MessageBox before this (abort = silent voice).
	ToastNoticeLine(line)
	MarkNoticeCooldown(target)
	; Toast + Audio: same index as PickNoticeLine (no second RandomInt).
	If mode == 0
		PlayNoticeAudio(stage, LastNoticePickIndex)
	EndIf
	If npcName
		LastNoticeStatus = "ok: " + npcName
	Else
		LastNoticeStatus = "ok: (unnamed)"
	EndIf
	WriteNoticeStatusToMcm()
	WriteNearbyStatusToMcm()
	OnNoticeSpoken(target, npcName, line)
EndFunction

; Slice C3 will grow fixation memory + escalation banks from successful notices.
Function OnNoticeSpoken(Actor akTarget, String npcName, String line)
	If !akTarget
		Return
	EndIf
	Debug.Trace("PickmansWhisper: C3 hook notice | " + npcName + " | " + line)
EndFunction

Function ToastNoticeLine(String line)
	If !line
		Return
	EndIf
	If !IsVoiceWeaponReady()
		Return
	EndIf
	LastNoticeToastRealTime = Utility.GetCurrentRealTime()
	LastNoticeToastGameTime = Utility.GetCurrentGameTime()
	ShowVoiceToast(line)
	Debug.Trace("PickmansWhisper: notice | " + line)
EndFunction

; FO4 top-left notifications often clip 1–3 leading glyphs (HUD slide / stacked toasts /
; FallUI). ASCII leading spaces are LTRIM'd by the UI, so pad with NBSP (U+00A0).
; Trace stays unpadded. System/error toasts do not use this.
String Function FormatVoiceToast(String line)
	If !line
		Return ""
	EndIf
	Return "  " + line
EndFunction

Function ShowVoiceToast(String line)
	If !line
		Return
	EndIf
	; Central toast sink — recognition / rename / trust / praise all land here.
	If !IsVoiceWeaponReady()
		Return
	EndIf
	Debug.Notification(FormatVoiceToast(line))
EndFunction

; Whisper / fixation / notice label for an actor.
; P3+P4 Potential Victims: override + SetDisplayName so {name} matches aim/HUD.
String Function GetActorDisplayName(Actor ak)
	If !ak
		Return ""
	EndIf
	String overrideName = GetVictimOverrideName(ak)
	If overrideName
		; Lazy re-apply after load (ExtraTextDisplayData can drop; FormID table persists).
		EnsureVictimDisplayName(ak)
		Return overrideName
	EndIf
	String disp = ak.GetDisplayName()
	If disp
		Return disp
	EndIf
	ActorBase base = ak.GetLeveledActorBase()
	If !base
		Return ""
	EndIf
	String n = base.GetName()
	If n == ""
		Return ""
	EndIf
	Return n
EndFunction

; --- C5 P3+P4 Potential Victims ------------------------------------------------

Function EnsureVictimLists()
	If !VictimIds || VictimIds.Length == 0
		VictimIds = new Int[32]
		VictimNames = new String[32]
		VictimSlotCount = 0
	EndIf
EndFunction

Int Function FindVictimSlot(Int formId)
	EnsureVictimLists()
	If formId == 0
		Return -1
	EndIf
	Int i = 0
	While i < VictimSlotCount
		If VictimIds[i] == formId
			Return i
		EndIf
		i += 1
	EndWhile
	Return -1
EndFunction

String Function GetVictimNameByFormId(Int formId)
	Int slot = FindVictimSlot(formId)
	If slot < 0
		Return ""
	EndIf
	Return VictimNames[slot]
EndFunction

; FormID → player-given Potential Victim name (save-persisted).
String Function GetVictimOverrideName(Actor ak)
	If !ak
		Return ""
	EndIf
	Return GetVictimNameByFormId(ak.GetFormID())
EndFunction

; Store FormID+name. Returns False if table full and formId is new.
Bool Function UpsertVictim(Int formId, String name)
	EnsureVictimLists()
	If formId == 0 || !name
		Return False
	EndIf
	Int slot = FindVictimSlot(formId)
	If slot >= 0
		VictimNames[slot] = name
		Return True
	EndIf
	If VictimSlotCount >= VICTIM_MAX
		Return False
	EndIf
	VictimIds[VictimSlotCount] = formId
	VictimNames[VictimSlotCount] = name
	VictimSlotCount += 1
	Return True
EndFunction

Function HoldVictimRef(Actor ak)
	If !ak || !VictimsHold
		Return
	EndIf
	If VictimsHold.Find(ak) < 0
		VictimsHold.AddRef(ak)
	EndIf
EndFunction

; Re-apply F4SE world name when stored override differs from current display.
Function EnsureVictimDisplayName(Actor ak)
	If !ak
		Return
	EndIf
	String n = GetVictimOverrideName(ak)
	If !n
		Return
	EndIf
	String cur = ak.GetDisplayName()
	If cur == n
		Return
	EndIf
	ak.SetDisplayName(n, True)
EndFunction

; Apply player-chosen name to a living actor (MCM / debug).
Bool Function ApplyVictimName(Actor ak, String name)
	If !ak || !name
		LastVictimStatus = "apply failed — no actor or name"
		WriteVictimsStatusToMcm()
		Return False
	EndIf
	String useName = TrimString(name)
	If !IsUsableWhisperName(useName)
		LastVictimStatus = "apply failed — name not usable (generic/junk?)"
		WriteVictimsStatusToMcm()
		Debug.Notification("Pickman's Whisper: name rejected — use a real name (not Settler/Resident)")
		Return False
	EndIf
	; Block workshop generics even if they pass glyph checks
	If NoticeNameForLine(useName) == ""
		LastVictimStatus = "apply failed — generic label blocked"
		WriteVictimsStatusToMcm()
		Debug.Notification("Pickman's Whisper: generic labels can't be victim names")
		Return False
	EndIf
	Int id = ak.GetFormID()
	If !UpsertVictim(id, useName)
		LastVictimStatus = "apply failed — victim table full (32)"
		WriteVictimsStatusToMcm()
		Debug.Notification("Pickman's Whisper: victim list full (32)")
		Return False
	EndIf
	Bool ok = ak.SetDisplayName(useName, True)
	HoldVictimRef(ak)
	If ok
		LastVictimStatus = useName + " ok id=0x" + GardenOfEden.GetHexFormID(ak)
	Else
		LastVictimStatus = useName + " stored; SetDisplayName returned false id=0x" + GardenOfEden.GetHexFormID(ak)
	EndIf
	WriteVictimsSummaryToMcm()
	WriteVictimsStatusToMcm()
	Debug.Trace("PickmansWhisper: victim named | " + LastVictimStatus)
	Return True
EndFunction

Function WriteVictimsStatusToMcm()
	If !MCM.IsInstalled()
		Return
	EndIf
	If !LastVictimStatus
		MCM.SetModSettingString(MOD_NAME, "sVictimStatus:Victims", "(none yet)")
	Else
		MCM.SetModSettingString(MOD_NAME, "sVictimStatus:Victims", LastVictimStatus)
	EndIf
EndFunction

Function WriteVictimsSummaryToMcm()
	EnsureVictimLists()
	String s = ""
	Int i = 0
	Int shown = 0
	While i < VictimSlotCount && shown < 8
		If VictimNames[i]
			If s != ""
				s += "; "
			EndIf
			s += VictimNames[i]
			shown += 1
		EndIf
		i += 1
	EndWhile
	If VictimSlotCount > 8
		s += " (+" + (VictimSlotCount - 8) + " more)"
	EndIf
	If s == ""
		s = "(no named victims yet)"
	EndIf
	LastVictimsSummary = s
	If MCM.IsInstalled()
		MCM.SetModSettingString(MOD_NAME, "sVictimsSummary:Victims", s)
	EndIf
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

; Remember world aim — GetCameraTargetReference is usually None while Pause/MCM is open.
Function NoteVictimsAimActor(Actor ak)
	If !ak || ak == PlayerRef
		Return
	EndIf
	If ak.IsDisabled()
		Return
	EndIf
	LastVictimsAimActor = ak
	LastVictimsAimId = ak.GetFormID()
EndFunction

; Live camera target if any; else last cached world aim (still loaded).
Actor Function ResolveVictimsAimActor()
	Actor live = GetLookAimActor()
	If live && live != PlayerRef
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

Function PushVictimsPanelStrings()
	If !PlayerRef
		PlayerRef = Game.GetPlayer()
	EndIf
	Actor aimed = ResolveVictimsAimActor()
	LastVictimsAimLine = "(look at an adult woman in-world, then Refresh)"
	If aimed
		String nm = GetActorDisplayName(aimed)
		If !nm
			nm = "unnamed"
		EndIf
		String src = "aim"
		Actor live = GetLookAimActor()
		If !live || live != aimed
			src = "last look"
		EndIf
		LastVictimsAimLine = nm + "  id=0x" + GardenOfEden.GetHexFormID(aimed) + " (" + src + ")"
		EnsureVictimDisplayName(aimed)
	EndIf
	WriteVictimsAimedToMcm()
	WriteVictimsSummaryToMcm()
	WriteVictimsStatusToMcm()
EndFunction

Function RefreshVictimsPanel(Bool refreshMenu = True)
	; Same order as RefreshDebugStatus: RefreshMenu reloads settings.ini and wipes
	; SetModSettingString — push live rows AFTER the menu refresh.
	PushVictimsPanelStrings()
	If refreshMenu && MCM.IsInstalled()
		MCM.RefreshMenu()
		WriteVictimsAimedToMcm()
		WriteVictimsSummaryToMcm()
		WriteVictimsStatusToMcm()
	EndIf
EndFunction

; MCM CallFunction entry (no args) — button "Refresh aimed / list".
Function MCMRefreshVictimsPanel()
	RefreshVictimsPanel(True)
	If LastVictimsAimLine && GardenOfEden.ReplaceStr(LastVictimsAimLine, "(look at", "") == LastVictimsAimLine
		Debug.Notification("Pickman's Whisper: aimed " + LastVictimsAimLine)
	Else
		Debug.Notification("Pickman's Whisper: no aim — look at her in-world, then Refresh")
	EndIf
EndFunction

; MCM Victims — apply sVictimName to live aim or last cached look.
Function MCMNameAimedVictim()
	If !PlayerRef
		PlayerRef = Game.GetPlayer()
	EndIf
	Actor aimed = ResolveVictimsAimActor()
	If !aimed || aimed == PlayerRef
		LastVictimStatus = "no aim target — look at her in-world, then Name aimed"
		PushVictimsPanelStrings()
		If MCM.IsInstalled()
			MCM.RefreshMenu()
			WriteVictimsAimedToMcm()
			WriteVictimsStatusToMcm()
		EndIf
		Debug.Notification("Pickman's Whisper: look at someone in-world, then Name aimed")
		Return
	EndIf
	String name = ""
	If MCM.IsInstalled()
		name = MCM.GetModSettingString(MOD_NAME, "sVictimName:Victims")
	EndIf
	If ApplyVictimName(aimed, name)
		String shown = TrimString(name)
		Debug.Notification("Pickman's Whisper: she is " + shown + " now")
	EndIf
	RefreshVictimsPanel(True)
EndFunction

Bool Function IsNoticeCandidate(Actor ak)
	; Prefer boolean empty-check — Caprica/runtime can be finicky with == ""
	String reason = ExplainNoticeReject(ak, False)
	Return !reason
EndFunction

; Fixation ignores hunger/NPC toast cooldown so a hunger whisper never suppresses "seen xN".
Bool Function IsFixationEligible(Actor ak)
	String reason = ExplainNoticeReject(ak, True)
	Return !reason
EndFunction

; --- C5 P1 look-fixation (additive; ambient MaybeSpeakNoticeLine untouched) ------

Function EnsureFixationLists()
	If !FixationIds || FixationIds.Length == 0
		FixationIds = new Int[32]
		FixationCounts = new Int[32]
		RecognitionToastCounts = new Int[32]
		FixationSlotCount = 0
	ElseIf !RecognitionToastCounts || RecognitionToastCounts.Length == 0
		; Mid-save upgrade from pre-prompt builds
		RecognitionToastCounts = new Int[32]
	EndIf
EndFunction

Function WriteFixationStatusToMcm()
	If !MCM.IsInstalled()
		Return
	EndIf
	If !LastFixationStatus
		MCM.SetModSettingString(MOD_NAME, "sFixation:Debug", "(none yet)")
	Else
		MCM.SetModSettingString(MOD_NAME, "sFixation:Debug", LastFixationStatus)
	EndIf
EndFunction

; Drop lowest count (tie → lowest index / oldest). Leaves one free slot.
Function EvictLowestFixation()
	EnsureFixationLists()
	If FixationSlotCount < 1
		Return
	EndIf
	Int best = 0
	Int bestCount = FixationCounts[0]
	Int i = 1
	While i < FixationSlotCount
		If FixationCounts[i] < bestCount
			best = i
			bestCount = FixationCounts[i]
		EndIf
		i += 1
	EndWhile
	Int j = best
	While j < FixationSlotCount - 1
		FixationIds[j] = FixationIds[j + 1]
		FixationCounts[j] = FixationCounts[j + 1]
		RecognitionToastCounts[j] = RecognitionToastCounts[j + 1]
		j += 1
	EndWhile
	FixationIds[FixationSlotCount - 1] = 0
	FixationCounts[FixationSlotCount - 1] = 0
	RecognitionToastCounts[FixationSlotCount - 1] = 0
	FixationSlotCount -= 1
EndFunction

; Returns new seen count for formId (1 on first insert).
Int Function IncrementFixation(Int formId)
	EnsureFixationLists()
	Int i = 0
	While i < FixationSlotCount
		If FixationIds[i] == formId
			FixationCounts[i] = FixationCounts[i] + 1
			Return FixationCounts[i]
		EndIf
		i += 1
	EndWhile
	If FixationSlotCount >= FIXATION_MAX
		EvictLowestFixation()
	EndIf
	If FixationSlotCount >= FIXATION_MAX
		Return 0
	EndIf
	FixationIds[FixationSlotCount] = formId
	FixationCounts[FixationSlotCount] = 1
	RecognitionToastCounts[FixationSlotCount] = 0
	FixationSlotCount += 1
	Return 1
EndFunction

; Bump how many RecognitionLines toasts this FormID has heard. 0 if unknown slot.
Int Function IncrementRecognitionToast(Int formId)
	EnsureFixationLists()
	Int i = 0
	While i < FixationSlotCount
		If FixationIds[i] == formId
			RecognitionToastCounts[i] = RecognitionToastCounts[i] + 1
			Return RecognitionToastCounts[i]
		EndIf
		i += 1
	EndWhile
	Return 0
EndFunction

; After N recognition toasts, if still unnamed, queue MCM Victims nudge (delayed).
; Never ShowVoiceToast here — a second Notification in the same tick replaces the
; RecognitionLines toast in the FO4 HUD.
; Prompt text: ModConfig.txt → renamePromptFemaleNPC (files-only).
Function MaybePromptNameHer(Actor ak, Int recognitionToasts)
	If !ak || recognitionToasts < RECOGNITION_NAME_PROMPT_AT
		Return
	EndIf
	If GetVictimOverrideName(ak)
		Return
	EndIf
	If !RenamePromptFemaleNPC
		LoadModConfig()
	EndIf
	If !RenamePromptFemaleNPC
		; Trace only — Notification here would also clobber the recognition toast.
		Debug.Trace("PickmansWhisper: ERROR rename prompt — " + ModConfigLoadStatus)
		Return
	EndIf
	PendingRenamePrompt = RenamePromptFemaleNPC
	CancelTimer(TIMER_RENAME_PROMPT)
	StartTimer(RENAME_PROMPT_DELAY, TIMER_RENAME_PROMPT)
	Debug.Trace("PickmansWhisper: name-her prompt queued | id=0x" + GardenOfEden.GetHexFormID(ak))
EndFunction

; Aim actor for fixation — real GoE APIs only (never Game.GetCurrentCrosshairRef).
Actor Function GetLookAimActor()
	ObjectReference cam = GardenOfEden3.GetCameraTargetReference()
	Actor ak = cam as Actor
	If ak
		Return ak
	EndIf
	ObjectReference pick = GardenOfEden2.GetLastActivateTargetRef()
	Return pick as Actor
EndFunction

; Aim edge → bump seen count → MCM status; voice by count (P2).
; Runs before hunger whisper on killscan so look-edge is not lost to Notification drop / cooldown.
Function TickLookFixation()
	If !BondStarted
		Return
	EndIf
	If !PlayerRef
		PlayerRef = Game.GetPlayer()
	EndIf
	If !PlayerRef
		Return
	EndIf

	Actor ak = GetLookAimActor()
	If !ak || ak == PlayerRef || !IsFixationEligible(ak)
		LastLookFixationId = 0
		Return
	EndIf

	; Cache for MCM Victims (camera target dies when Pause menu opens).
	NoteVictimsAimActor(ak)

	Int id = ak.GetFormID()
	If id == 0
		LastLookFixationId = 0
		Return
	EndIf
	If id == LastLookFixationId
		Return
	EndIf
	LastLookFixationId = id

	Int count = IncrementFixation(id)
	If count < 1
		LastFixationStatus = "skip: fixation table full"
		WriteFixationStatusToMcm()
		Return
	EndIf

	; Whisper-safe name (rejects □□ junk; P3 override via GetActorDisplayName).
	String displayName = NoticeNameForLine(GetActorDisplayName(ak))
	String label = displayName
	If !label
		label = "unnamed"
	EndIf
	; Count always in MCM; voice by look count (P2): 1 silent / 2 stage / 3+ recognition.
	LastFixationStatus = label + " seen x" + count + " (" + FixationSlotCount + "/" + FIXATION_MAX + ")"
	WriteFixationStatusToMcm()
	Debug.Trace("PickmansWhisper: fixation edge | " + LastFixationStatus)
	If count == 1
		; First look — track only (silent).
		Return
	EndIf
	If !IsVoiceWeaponReady()
		LastFixationStatus = label + " seen x" + count + " (no blade — silent)"
		WriteFixationStatusToMcm()
		Return
	EndIf
	If count == 2
		SpeakFixationStageWhisper(ak, displayName)
	Else
		SpeakRecognitionLine(ak, displayName)
	EndIf
EndFunction

; Empty string = passes. Otherwise a short reject reason for MCM / MessageBox.
; abIgnoreCooldown=True for fixation (hunger NPC cool must not suppress look-edge toasts).
String Function ExplainNoticeReject(Actor ak, Bool abIgnoreCooldown = False)
	If !ak || ak == PlayerRef
		Return "no actor"
	EndIf
	If ak.IsDead()
		Return "dead"
	EndIf
	If ak.IsDisabled()
		Return "disabled"
	EndIf
	If PlayerRef && PlayerRef.GetDistance(ak) > KILL_WATCH_RADIUS
		Return "too far"
	EndIf
	If !abIgnoreCooldown && IsNoticeOnCooldown(ak)
		Return "cooldown"
	EndIf
	If IsChildNpc(ak) && !IsChildTargetAllowed()
		Return "child"
	EndIf
	If ak.IsPlayerTeammate()
		Return "teammate"
	EndIf
	If IsStoryEssential(ak)
		Return "essential"
	EndIf
	; Exclusion-based — blocks Brahmin/animals; do not gate on hostility (settler false positives)
	String nonHuman = ExplainNonHumanForNotice(ak)
	If nonHuman
		Return nonHuman
	EndIf
	If !IsAdultFemale(ak)
		ActorBase base = ak.GetLeveledActorBase()
		Int sex = -1
		If base
			sex = base.GetSex()
		EndIf
		Return "not female (sex=" + sex + ")"
	EndIf
	Return ""
EndFunction

; For notice only: reject clear non-humans. Synths allowed (look human). No positive keyword required.
String Function ExplainNonHumanForNotice(Actor ak)
	If !ak
		Return "no actor"
	EndIf
	EnsureFilterKeywords()
	If KW_ActorTypeAnimal && ak.HasKeyword(KW_ActorTypeAnimal)
		Return "animal"
	EndIf
	If KW_ActorTypeCreature && ak.HasKeyword(KW_ActorTypeCreature)
		Return "creature"
	EndIf
	If KW_ActorTypeRobot && ak.HasKeyword(KW_ActorTypeRobot) && !IsRobotTargetAllowed()
		Return "robot"
	EndIf
	If KW_ActorTypeTurret && ak.HasKeyword(KW_ActorTypeTurret)
		Return "turret"
	EndIf
	If KW_ActorTypeGhoul && ak.HasKeyword(KW_ActorTypeGhoul)
		Return "ghoul"
	EndIf
	If KW_ActorTypeSuperMutant && ak.HasKeyword(KW_ActorTypeSuperMutant)
		Return "supermutant"
	EndIf
	Return ""
EndFunction

Actor Function PickNoticeTarget()
	LastNoticeDiag = ""
	If !PlayerRef
		LastNoticeStatus = "skip: no player"
		LastNoticeDiag = "no player"
		LastNearbySummary = "live=? (no player)"
		Return None
	EndIf

	Actor[] living = GardenOfEden.FindActors(None, None, -1, -1, PlayerRef, KILL_WATCH_RADIUS, 1, -1, -1, -1, -1, -1, None, None, "", 0, 1, 0)
	Int nLive = 0
	If living
		nLive = living.Length
	EndIf

	; Checklist: two closest only (MessageBox size). Pick: all living via PickBestNoticeFromList.
	Actor a0 = None
	Actor a1 = None
	Float d0 = 999999.0
	Float d1 = 999999.0
	Int i = 0
	Int n = nLive
	If n > 48
		n = 48
	EndIf
	While i < n
		Actor ak = living[i]
		i += 1
		If ak && ak != PlayerRef && !ak.IsDead()
			Float d = PlayerRef.GetDistance(ak)
			If d < d0
				d1 = d0
				a1 = a0
				d0 = d
				a0 = ak
			ElseIf d < d1
				d1 = d
				a1 = ak
			EndIf
		EndIf
	EndWhile

	String report = "GoE living=" + nLive + " r=" + (KILL_WATCH_RADIUS as Int) + "\n"
	If a0
		report += FormatNoticeActorChecklist(a0)
		If !IsNoticeCandidate(a0)
			String why0 = ExplainNoticeReject(a0)
			If why0
				LastNoticeBreakAt = why0
			EndIf
		EndIf
	EndIf
	If a1
		report += FormatNoticeActorChecklist(a1)
	EndIf
	If nLive == 0
		report += "(no living actors in radius)\n"
		If !LastNoticeBreakAt
			LastNoticeBreakAt = "GoE living=0"
		EndIf
	EndIf

	; Real pick — not limited to the two checklist actors (Brahmin/men closer used to block toast).
	Actor best = PickBestNoticeFromList(living)
	If best
		LastNoticeStatus = "pick live=" + nLive
		LastNoticeDiag = report + "PICK: " + GetActorDisplayName(best)
		LastNoticeBreakAt = "(none — pick ok)"
		CommitNearbyPickSummary(nLive, best)
		Return best
	EndIf

	; Fallback detecting (one-line only to save space)
	Actor[] detecting = GardenOfEden2.GetActorsDetecting(PlayerRef, False)
	Int nDet = 0
	If detecting
		nDet = detecting.Length
	EndIf
	report += "Detecting=" + nDet + " (no living PASS)\n"
	best = PickBestNoticeFromList(detecting)
	If best
		LastNoticeStatus = "pick detecting"
		LastNoticeDiag = report + FormatNoticeActorChecklist(best) + "PICK: detecting"
		LastNoticeBreakAt = "(none — pick ok)"
		CommitNearbyPickSummary(nLive, best)
		Return best
	EndIf

	LastNoticeStatus = "no notice pass live=" + nLive
	If !LastNoticeBreakAt || LastNoticeBreakAt == "(none — pick ok)"
		LastNoticeBreakAt = "no PASS actor"
	EndIf
	LastNoticeDiag = report + "PICK: none"
	CommitNearbyPickSummary(nLive, None)
	Return None
EndFunction

Function CommitNearbyPickSummary(Int nLive, Actor best)
	; Memory only during poll — MCM writes happen after ToastNoticeLine / on Refresh.
	String s = "live=" + nLive + " r=" + (KILL_WATCH_RADIUS as Int)
	If best
		String nm = GetActorDisplayName(best)
		If !nm
			nm = "?"
		EndIf
		s = s + " pick=" + nm
	Else
		s = s + " pick=none"
		If LastNoticeBreakAt
			s = s + " (" + LastNoticeBreakAt + ")"
		EndIf
	EndIf
	LastNearbySummary = s
EndFunction

Actor Function PickBestNoticeFromList(Actor[] alive)
	If !alive || alive.Length == 0
		Return None
	EndIf
	Actor best = None
	Float bestDist = 999999.0
	Int n = alive.Length
	If n > 48
		n = 48
	EndIf
	Int i = 0
	While i < n
		Actor ak = alive[i]
		If IsNoticeCandidate(ak)
			Float d = PlayerRef.GetDistance(ak)
			If d < bestDist
				bestDist = d
				best = ak
			EndIf
		EndIf
		i += 1
	EndWhile
	Return best
EndFunction

Function EnsureNoticeCoolLists()
	If !NoticeCoolIds || NoticeCoolIds.Length == 0
		NoticeCoolIds = new Int[16]
		NoticeCoolTimes = new Float[16]
		NoticeCoolCount = 0
	EndIf
EndFunction

Bool Function IsNoticeOnCooldown(Actor ak)
	If !ak
		Return True
	EndIf
	EnsureNoticeCoolLists()
	Int id = ak.GetFormID()
	Float now = Utility.GetCurrentRealTime()
	Int i = 0
	While i < NoticeCoolCount
		If NoticeCoolIds[i] == id
			If (now - NoticeCoolTimes[i]) < NOTICE_NPC_COOLDOWN
				Return True
			EndIf
			Return False
		EndIf
		i += 1
	EndWhile
	Return False
EndFunction

Function MarkNoticeCooldown(Actor ak)
	If !ak
		Return
	EndIf
	EnsureNoticeCoolLists()
	Int id = ak.GetFormID()
	Float now = Utility.GetCurrentRealTime()
	Int i = 0
	While i < NoticeCoolCount
		If NoticeCoolIds[i] == id
			NoticeCoolTimes[i] = now
			Return
		EndIf
		i += 1
	EndWhile
	If NoticeCoolCount >= NOTICE_COOL_MAX
		; Drop oldest slot 0
		Int j = 0
		While j < NOTICE_COOL_MAX - 1
			NoticeCoolIds[j] = NoticeCoolIds[j + 1]
			NoticeCoolTimes[j] = NoticeCoolTimes[j + 1]
			j += 1
		EndWhile
		NoticeCoolCount = NOTICE_COOL_MAX - 1
	EndIf
	NoticeCoolIds[NoticeCoolCount] = id
	NoticeCoolTimes[NoticeCoolCount] = now
	NoticeCoolCount += 1
EndFunction

Function ToastVoice(String line)
	If line == "" || !IsVoiceEnabled()
		Return
	EndIf
	If Utility.IsInMenuMode()
		Return
	EndIf
	If !IsVoiceWeaponReady()
		Return
	EndIf
	LastTrustToastRealTime = Utility.GetCurrentRealTime()
	ShowVoiceToast(line)
	Debug.Trace("PickmansWhisper: voice | " + line)
EndFunction

Function ToastHungerLine(String line)
	If line == "" || !IsVoiceEnabled()
		Return
	EndIf
	If Utility.IsInMenuMode()
		Return
	EndIf
	If !IsVoiceWeaponReady()
		Return
	EndIf
	Float now = Utility.GetCurrentRealTime()
	If (now - LastHungerToastRealTime) < HUNGER_TOAST_COOLDOWN
		Return
	EndIf
	LastHungerToastRealTime = now
	ShowVoiceToast(line)
	Debug.Trace("PickmansWhisper: hunger voice | " + line)
EndFunction

; --- Line banks ----------------------------------------------------------------

Function LoadLineBanks()
	LoadTrustLines()
	LoadHungerLines()
	LoadPraiseLines()
	LoadNoticeLines()
	LoadAudioBanks()
	LoadWhisperSndrIds()
	LoadRecognitionLines()
	LoadSleepRecognitionLines()
	LoadIntimacyNamedLines()
	LoadModConfig()
	LoadTargetOverrides()
EndFunction

; ModConfig.txt — key=value prompts / toggles. Files-only (no baked mirror).
; E4/E5: intimacy toast+audio live in necromantic/Intimacy_*_Named.txt / *_Audio.txt.
Function LoadModConfig()
	RenamePromptFemaleNPC = ""
	NamedKillToast = ""
	NamedKillAudio = ""
	String fileName = "ModConfig.txt"
	String path = NoticeConfigPath()
	ModConfigLoadStatus = "READ FAILED (GoE2 missing?)"
	; Trace-only on load — Notification steals/clobbers voice toasts.
	If !GardenOfEden2.DoesFileExist(fileName, path)
		ModConfigLoadStatus = "MISSING FILE (" + path + fileName + ")"
		Debug.Trace("PickmansWhisper: ERROR ModConfig.txt — " + ModConfigLoadStatus)
		Return
	EndIf
	String[] raw = GardenOfEden2.GetLinesFromFile(fileName, path)
	If !raw || raw.Length == 0
		ModConfigLoadStatus = "EMPTY/UNREADABLE"
		Debug.Trace("PickmansWhisper: ERROR ModConfig.txt — " + ModConfigLoadStatus)
		Return
	EndIf
	Int i = 0
	While i < raw.Length
		String line = TrimString(raw[i])
		i += 1
		If line == ""
			; skip
		ElseIf GardenOfEden.SubStr(line, 0, 1) == "#"
			; comment
		Else
			Int eq = -1
			Int li = 0
			Int ln = GardenOfEden.StrLength(line)
			While li < ln && eq < 0
				If GardenOfEden.SubStr(line, li, 1) == "="
					eq = li
				EndIf
				li += 1
			EndWhile
			If eq > 0
				String key = TrimString(GardenOfEden.SubStr(line, 0, eq))
				String val = TrimString(GardenOfEden.SubStr(line, eq + 1, -1))
				If key == "renamePromptFemaleNPC"
					RenamePromptFemaleNPC = val
				ElseIf key == "namedKillToast"
					NamedKillToast = val
				ElseIf key == "namedKillAudio"
					NamedKillAudio = val
				EndIf
			EndIf
		EndIf
	EndWhile
	String status = ""
	If RenamePromptFemaleNPC
		status += "rename "
	EndIf
	If NamedKillToast
		status += "namedKill "
	EndIf
	If status != ""
		ModConfigLoadStatus = TrimString(status) + "ok"
		Debug.Trace("PickmansWhisper: ModConfig ready | " + ModConfigLoadStatus)
	Else
		ModConfigLoadStatus = "no known keys"
		Debug.Trace("PickmansWhisper: ERROR ModConfig.txt — " + ModConfigLoadStatus)
	EndIf
EndFunction

; E4/E5 — named intimacy toast + audio maps (files-only under config/necromantic/).
Function LoadIntimacyNamedLines()
	IntimacyStartNamedLines = new String[64]
	IntimacyStartNamedCount = LoadStageBankAt("Intimacy_Start_Named.txt", IntimacyStartNamedLines, NecromanticConfigPath())
	IntimacyStartNamedStatus = LastStageLoadStatus
	If IntimacyStartNamedCount <= 0
		Debug.Trace("PickmansWhisper: ERROR Intimacy_Start_Named.txt — " + IntimacyStartNamedStatus)
	Else
		Debug.Trace("PickmansWhisper: intimacy start named lines ready (" + IntimacyStartNamedCount + ")")
	EndIf
	IntimacyEndNamedLines = new String[64]
	IntimacyEndNamedCount = LoadStageBankAt("Intimacy_End_Named.txt", IntimacyEndNamedLines, NecromanticConfigPath())
	IntimacyEndNamedStatus = LastStageLoadStatus
	If IntimacyEndNamedCount <= 0
		Debug.Trace("PickmansWhisper: ERROR Intimacy_End_Named.txt — " + IntimacyEndNamedStatus)
	Else
		Debug.Trace("PickmansWhisper: intimacy end named lines ready (" + IntimacyEndNamedCount + ")")
	EndIf
	IntimacyStartAudioLines = new String[64]
	IntimacyStartAudioCount = LoadStageBankAt("Intimacy_Start_Audio.txt", IntimacyStartAudioLines, NecromanticConfigPath())
	IntimacyStartAudioStatus = LastStageLoadStatus
	IntimacyEndAudioLines = new String[64]
	IntimacyEndAudioCount = LoadStageBankAt("Intimacy_End_Audio.txt", IntimacyEndAudioLines, NecromanticConfigPath())
	IntimacyEndAudioStatus = LastStageLoadStatus
	ReportIntimacyAudioCountMismatch(True, IntimacyStartNamedCount, IntimacyStartAudioCount)
	ReportIntimacyAudioCountMismatch(False, IntimacyEndNamedCount, IntimacyEndAudioCount)
	Debug.Trace("PickmansWhisper: intimacy audio start=" + IntimacyStartAudioCount + " end=" + IntimacyEndAudioCount)
EndFunction

Function ReportIntimacyAudioCountMismatch(Bool abStart, Int toastCount, Int audioCount)
	If audioCount <= 0
		Return
	EndIf
	If toastCount == audioCount
		Return
	EndIf
	String which = "End"
	If abStart
		which = "Start"
	EndIf
	String msg = "intimacy " + which + " toast/audio mismatch toast=" + toastCount + " audio=" + audioCount
	Debug.Notification("Pickman's Whisper: " + msg)
	Debug.Trace("PickmansWhisper: ERROR " + msg)
EndFunction

; Random toast index; -1 if unloaded. No-immediate-repeat on raw template.
Int Function PickIntimacyNamedIndex(Bool abStart)
	If abStart
		If IntimacyStartNamedCount <= 0 || !IntimacyStartNamedLines
			Return -1
		EndIf
		Int idx = Utility.RandomInt(0, IntimacyStartNamedCount - 1)
		String raw = IntimacyStartNamedLines[idx]
		Int tries = 0
		While tries < 8 && IntimacyStartNamedCount > 1 && raw == LastIntimacyStartLine
			idx = Utility.RandomInt(0, IntimacyStartNamedCount - 1)
			raw = IntimacyStartNamedLines[idx]
			tries += 1
		EndWhile
		LastIntimacyStartLine = raw
		LastIntimacyStartPickIndex = idx
		Return idx
	EndIf
	If IntimacyEndNamedCount <= 0 || !IntimacyEndNamedLines
		Return -1
	EndIf
	Int eIdx = Utility.RandomInt(0, IntimacyEndNamedCount - 1)
	String eRaw = IntimacyEndNamedLines[eIdx]
	Int eTries = 0
	While eTries < 8 && IntimacyEndNamedCount > 1 && eRaw == LastIntimacyEndLine
		eIdx = Utility.RandomInt(0, IntimacyEndNamedCount - 1)
		eRaw = IntimacyEndNamedLines[eIdx]
		eTries += 1
	EndWhile
	LastIntimacyEndLine = eRaw
	LastIntimacyEndPickIndex = eIdx
	Return eIdx
EndFunction

; Audio-only roll — index or -1.
Int Function PickIntimacyAudioIndex(Bool abStart)
	Int count = IntimacyEndAudioCount
	String[] bank = IntimacyEndAudioLines
	If abStart
		count = IntimacyStartAudioCount
		bank = IntimacyStartAudioLines
	EndIf
	If count <= 0 || !bank
		Debug.Notification("Pickman's Whisper: intimacy audio map empty")
		Debug.Trace("PickmansWhisper: ERROR PickIntimacyAudioIndex empty start=" + abStart)
		Return -1
	EndIf
	Int idx = Utility.RandomInt(0, count - 1)
	String fileName = bank[idx]
	Int tries = 0
	While tries < 8 && count > 1 && fileName == LastIntimacyAudioFile
		idx = Utility.RandomInt(0, count - 1)
		fileName = bank[idx]
		tries += 1
	EndWhile
	LastIntimacyAudioFile = fileName
	Return idx
EndFunction

Function PlayIntimacyAudioAt(Bool abStart, Int index)
	Int count = IntimacyEndAudioCount
	String[] bank = IntimacyEndAudioLines
	If abStart
		count = IntimacyStartAudioCount
		bank = IntimacyStartAudioLines
	EndIf
	If count <= 0 || !bank
		Debug.Notification("Pickman's Whisper: intimacy audio map empty")
		Return
	EndIf
	If index < 0 || index >= count
		Debug.Notification("Pickman's Whisper: intimacy audio index out of range " + index)
		Debug.Trace("PickmansWhisper: ERROR PlayIntimacyAudioAt idx=" + index + " count=" + count)
		Return
	EndIf
	String fileName = bank[index]
	If !fileName || GardenOfEden.StrLength(fileName) < 1
		Debug.Notification("Pickman's Whisper: empty intimacy audio filename at " + index)
		Return
	EndIf
	PlayWhisperXwmByFile(fileName)
EndFunction


; C5 P2 — awake recognition bank (files-only). Later bands can use GetRecognitionBank(band).
Function LoadRecognitionLines()
	RecognitionLines = new String[64]
	RecognitionLineCount = LoadStageBank("RecognitionLines.txt", RecognitionLines)
	RecognitionLoadStatus = LastStageLoadStatus
	If RecognitionLineCount <= 0
		Debug.Trace("PickmansWhisper: ERROR RecognitionLines.txt — " + RecognitionLoadStatus)
	Else
		Debug.Trace("PickmansWhisper: recognition lines ready (" + RecognitionLineCount + ")")
	EndIf
EndFunction

; C5 P5 — sleep recognition bank (files-only).
Function LoadSleepRecognitionLines()
	SleepRecognitionLines = new String[64]
	SleepRecognitionLineCount = LoadStageBank("SleepRecognitionLines.txt", SleepRecognitionLines)
	SleepRecognitionLoadStatus = LastStageLoadStatus
	If SleepRecognitionLineCount <= 0
		Debug.Trace("PickmansWhisper: ERROR SleepRecognitionLines.txt — " + SleepRecognitionLoadStatus)
	Else
		Debug.Trace("PickmansWhisper: sleep recognition lines ready (" + SleepRecognitionLineCount + ")")
	EndIf
EndFunction

; FO4 GetSleepState: 3 = sleeping, 4 = sleeping wants wake. Treat both as asleep.
Bool Function IsActorSleeping(Actor ak)
	If !ak
		Return False
	EndIf
	Int st = ak.GetSleepState()
	Return st >= 3
EndFunction

; encounterBand reserved for later multi-file mapping; P2 always returns the single bank.
String[] Function GetRecognitionBank(Int encounterBand)
	Return RecognitionLines
EndFunction

Int Function GetRecognitionBankCount(Int encounterBand)
	Return RecognitionLineCount
EndFunction

String Function PickRecognitionLine(String npcName)
	String[] bank = GetRecognitionBank(0)
	Int count = GetRecognitionBankCount(0)
	If count <= 0 || !bank
		LoadRecognitionLines()
		bank = GetRecognitionBank(0)
		count = GetRecognitionBankCount(0)
	EndIf
	If count <= 0 || !bank
		Return ""
	EndIf
	String useName = NoticeNameForLine(npcName)
	Bool wantNameless = (useName == "")
	String raw = bank[Utility.RandomInt(0, count - 1)]
	Int tries = 0
	While tries < 8 && count > 1 && (raw == LastRecognitionLine || (wantNameless && StrContains(raw, "{name}")))
		raw = bank[Utility.RandomInt(0, count - 1)]
		tries += 1
	EndWhile
	If !raw
		Return ""
	EndIf
	LastRecognitionLine = raw
	Return ApplyNamePlaceholder(raw, useName)
EndFunction

String Function PickSleepRecognitionLine(String npcName)
	If SleepRecognitionLineCount <= 0 || !SleepRecognitionLines
		LoadSleepRecognitionLines()
	EndIf
	If SleepRecognitionLineCount <= 0 || !SleepRecognitionLines
		Return ""
	EndIf
	String useName = NoticeNameForLine(npcName)
	Bool wantNameless = (useName == "")
	String raw = SleepRecognitionLines[Utility.RandomInt(0, SleepRecognitionLineCount - 1)]
	Int tries = 0
	While tries < 8 && SleepRecognitionLineCount > 1 && (raw == LastSleepRecognitionLine || (wantNameless && StrContains(raw, "{name}")))
		raw = SleepRecognitionLines[Utility.RandomInt(0, SleepRecognitionLineCount - 1)]
		tries += 1
	EndWhile
	If !raw
		Return ""
	EndIf
	LastSleepRecognitionLine = raw
	Return ApplyNamePlaceholder(raw, useName)
EndFunction

; 2nd look — speak current hunger-stage notice line (does not rewrite MaybeSpeakNoticeLine).
Function SpeakFixationStageWhisper(Actor ak, String npcName)
	String line = PickNoticeLine(npcName)
	If !line || GardenOfEden.StrLength(line) < 1
		LastFixationStatus = "seen x2 — stage line skipped (bank empty)"
		WriteFixationStatusToMcm()
		Return
	EndIf
	; ToastNoticeLine stamps game-hour gate so ambient won't double-toast soon after.
	ToastNoticeLine(line)
	If ak
		MarkNoticeCooldown(ak)
		OnNoticeSpoken(ak, npcName, line)
	EndIf
EndFunction

; 3rd+ look — awake RecognitionLines / sleep SleepRecognitionLines (no hunger hour stamp).
; After RECOGNITION_NAME_PROMPT_AT successful toasts on this NPC (still unnamed),
; queue ModConfig renamePromptFemaleNPC until named.
Function SpeakRecognitionLine(Actor ak, String npcName)
	Bool asleep = IsActorSleeping(ak)
	String line = ""
	If asleep
		line = PickSleepRecognitionLine(npcName)
	Else
		line = PickRecognitionLine(npcName)
	EndIf
	If !line || GardenOfEden.StrLength(line) < 1
		If asleep
			LastFixationStatus = "sleep recognition MISSING — " + SleepRecognitionLoadStatus
			WriteFixationStatusToMcm()
			Debug.Notification("Pickman's Whisper: SleepRecognitionLines.txt not loaded — see MCM / config")
			Debug.Trace("PickmansWhisper: ERROR sleep recognition speak failed — " + SleepRecognitionLoadStatus)
		Else
			LastFixationStatus = "recognition MISSING — " + RecognitionLoadStatus
			WriteFixationStatusToMcm()
			Debug.Notification("Pickman's Whisper: RecognitionLines.txt not loaded — see MCM / config")
			Debug.Trace("PickmansWhisper: ERROR recognition speak failed — " + RecognitionLoadStatus)
		EndIf
		Return
	EndIf
	ShowVoiceToast(line)
	If asleep
		Debug.Trace("PickmansWhisper: sleep recognition | " + line)
	Else
		Debug.Trace("PickmansWhisper: recognition | " + line)
	EndIf
	If !ak
		Return
	EndIf
	Int n = IncrementRecognitionToast(ak.GetFormID())
	MaybePromptNameHer(ak, n)
EndFunction

Function LoadTrustLines()
	; Builtin-only bank. Only the Notice whispers are file-editable (per-stage txt);
	; trust/hunger/praise ship no config .txt to avoid dead, unread files.
	UseBuiltinTrustFallback()
	Debug.Trace("PickmansWhisper: trust lines ready (" + TrustLineCount + ")")
EndFunction

Function LoadHungerLines()
	UseBuiltinHungerFallback()
	Debug.Trace("PickmansWhisper: hunger lines ready (" + HungerLineCount + ")")
EndFunction

Function LoadPraiseLines()
	UseBuiltinPraiseFallback()
	Debug.Trace("PickmansWhisper: praise lines ready (" + PraiseLineCount + ")")
EndFunction

; C3 — hunger-stage whispers, FILES-ONLY. Content lives solely in the editable
; config .txt files; there are no hardcoded builtin copies. Each stage's load
; result is recorded for the MCM Debug rows, and any failure raises a load-time
; error toast so a missing/unreadable file is never silently masked.
; Does NOT MessageBox itself — callers that want the Necromantic-style popup call
; ReportNoticeLoadStatus() (MCM Debug button only). Lazy retries from PickNoticeLine
; must not spam dialogs.
Function LoadNoticeLines()
	; Pre-arm every row with a pessimistic sentinel and PUSH it to MCM *before* any
	; GoE2 call. If a GoE2 native aborts the Papyrus stack, these rows survive and
	; show the abort point instead of silently reading "(not loaded)".
	NoticeCalmStatus = "load did not complete (GoE2 file read aborted?)"
	NoticeRestlessStatus = NoticeCalmStatus
	NoticeHungryStatus = NoticeCalmStatus
	NoticeStarvingStatus = NoticeCalmStatus
	NoticeDesperateStatus = NoticeCalmStatus
	WriteNoticeLoadStatusToMcm()

	NoticeLoadDiag = "NOTICE | path=" + NoticeConfigPath() + " | GoE rel=" + GardenOfEden.GetVersionRelease()

	NoticeCalmLines = new String[64]
	NoticeCalmCount = LoadStageBank("NoticeLines_Calm.txt", NoticeCalmLines)
	NoticeCalmStatus = LastStageLoadStatus
	NoticeLoadDiag += " || " + LastStageLoadDiag
	WriteNoticeLoadStatusToMcm()
	NoticeRestlessLines = new String[64]
	NoticeRestlessCount = LoadStageBank("NoticeLines_Restless.txt", NoticeRestlessLines)
	NoticeRestlessStatus = LastStageLoadStatus
	NoticeLoadDiag += " || " + LastStageLoadDiag
	WriteNoticeLoadStatusToMcm()
	NoticeHungryLines = new String[64]
	NoticeHungryCount = LoadStageBank("NoticeLines_Hungry.txt", NoticeHungryLines)
	NoticeHungryStatus = LastStageLoadStatus
	NoticeLoadDiag += " || " + LastStageLoadDiag
	WriteNoticeLoadStatusToMcm()
	NoticeStarvingLines = new String[64]
	NoticeStarvingCount = LoadStageBank("NoticeLines_Starving.txt", NoticeStarvingLines)
	NoticeStarvingStatus = LastStageLoadStatus
	NoticeLoadDiag += " || " + LastStageLoadDiag
	WriteNoticeLoadStatusToMcm()
	NoticeDesperateLines = new String[64]
	NoticeDesperateCount = LoadStageBank("NoticeLines_Desperate.txt", NoticeDesperateLines)
	NoticeDesperateStatus = LastStageLoadStatus
	NoticeLoadDiag += " || " + LastStageLoadDiag
	WriteNoticeLoadStatusToMcm()

	String failed = NoticeLoadFailureList()
	If failed != ""
		Debug.Notification("Pickman's Whisper: notice lines failed to load — " + failed + ". See MCM > Debug.")
	EndIf

	Debug.Trace("PickmansWhisper: notice stages calm=" + NoticeCalmCount + " restless=" + NoticeRestlessCount + " hungry=" + NoticeHungryCount + " starving=" + NoticeStarvingCount + " desperate=" + NoticeDesperateCount)
EndFunction

; D1 — load five *_Audio.txt maps (filenames only). Empty stages are valid (count 0)
; until clips are authored; mismatch vs notice count fails loud at load.
Function LoadAudioBanks()
	AudioCalmLines = new String[64]
	AudioCalmCount = LoadStageBank("Calm_Audio.txt", AudioCalmLines)
	AudioCalmStatus = LastStageLoadStatus
	AudioRestlessLines = new String[64]
	AudioRestlessCount = LoadStageBank("Restless_Audio.txt", AudioRestlessLines)
	AudioRestlessStatus = LastStageLoadStatus
	AudioHungryLines = new String[64]
	AudioHungryCount = LoadStageBank("Hungry_Audio.txt", AudioHungryLines)
	AudioHungryStatus = LastStageLoadStatus
	AudioStarvingLines = new String[64]
	AudioStarvingCount = LoadStageBank("Starving_Audio.txt", AudioStarvingLines)
	AudioStarvingStatus = LastStageLoadStatus
	AudioDesperateLines = new String[64]
	AudioDesperateCount = LoadStageBank("Desperate_Audio.txt", AudioDesperateLines)
	AudioDesperateStatus = LastStageLoadStatus

	ReportAudioNoticeCountMismatch(0, NoticeCalmCount, AudioCalmCount, "Calm")
	ReportAudioNoticeCountMismatch(1, NoticeRestlessCount, AudioRestlessCount, "Restless")
	ReportAudioNoticeCountMismatch(2, NoticeHungryCount, AudioHungryCount, "Hungry")
	ReportAudioNoticeCountMismatch(3, NoticeStarvingCount, AudioStarvingCount, "Starving")
	ReportAudioNoticeCountMismatch(4, NoticeDesperateCount, AudioDesperateCount, "Desperate")

	Debug.Trace("PickmansWhisper: audio maps calm=" + AudioCalmCount + " restless=" + AudioRestlessCount + " hungry=" + AudioHungryCount + " starving=" + AudioStarvingCount + " desperate=" + AudioDesperateCount)
EndFunction

Function ReportAudioNoticeCountMismatch(Int stage, Int noticeCount, Int audioCount, String stageName)
	; Empty audio map (0) while notices exist: OK for unfinished stages — PlayNoticeAudio fails loud if used.
	; Non-zero mismatch: author error — surface at load.
	If audioCount <= 0
		Return
	EndIf
	If noticeCount == audioCount
		Return
	EndIf
	String msg = "audio/notice count mismatch " + stageName + " notice=" + noticeCount + " audio=" + audioCount
	Debug.Notification("Pickman's Whisper: " + msg)
	Debug.Trace("PickmansWhisper: ERROR " + msg)
EndFunction

; Generated by esp build — maps EndIt.xwm=2055 (local FormID decimal).
Function LoadWhisperSndrIds()
	; Cap must fit Desperate + Necromantic Start/End maps (see WHISPER_SNDR_MAX).
	WhisperSndrFiles = new String[128]
	WhisperSndrFids = new Int[128]
	WhisperSndrCount = 0
	WhisperSndrIdsStatus = "READ FAILED (GoE2 missing?)"
	String fileName = "WhisperSndrIds.txt"
	String path = NoticeConfigPath()
	If !GardenOfEden2.DoesFileExist(fileName, path)
		WhisperSndrIdsStatus = "MISSING FILE"
		Debug.Notification("Pickman's Whisper: WhisperSndrIds.txt missing — rebuild ESP")
		Debug.Trace("PickmansWhisper: ERROR WhisperSndrIds.txt missing at " + path)
		Return
	EndIf
	String[] raw = GardenOfEden2.GetLinesFromFile(fileName, path)
	If !raw || raw.Length == 0
		WhisperSndrIdsStatus = "EMPTY/UNREADABLE"
		Debug.Notification("Pickman's Whisper: WhisperSndrIds.txt empty — rebuild ESP")
		Debug.Trace("PickmansWhisper: ERROR WhisperSndrIds.txt empty")
		Return
	EndIf
	Int i = 0
	While i < raw.Length && WhisperSndrCount < WHISPER_SNDR_MAX
		String line = TrimString(raw[i])
		i += 1
		If line == ""
			; skip
		ElseIf GardenOfEden.SubStr(line, 0, 1) == "#"
			; comment
		Else
			Int eq = -1
			Int li = 0
			Int ln = GardenOfEden.StrLength(line)
			While li < ln && eq < 0
				If GardenOfEden.SubStr(line, li, 1) == "="
					eq = li
				EndIf
				li += 1
			EndWhile
			If eq > 0
				String key = TrimString(GardenOfEden.SubStr(line, 0, eq))
				String val = TrimString(GardenOfEden.SubStr(line, eq + 1, -1))
				Int fid = ParsePositiveInt(val)
				If key != "" && fid > 0
					WhisperSndrFiles[WhisperSndrCount] = key
					WhisperSndrFids[WhisperSndrCount] = fid
					WhisperSndrCount += 1
				EndIf
			EndIf
		EndIf
	EndWhile
	If WhisperSndrCount <= 0
		WhisperSndrIdsStatus = "EMPTY (no usable rows)"
		Debug.Notification("Pickman's Whisper: WhisperSndrIds.txt has no rows")
		Debug.Trace("PickmansWhisper: ERROR WhisperSndrIds.txt parsed 0 rows")
		Return
	EndIf
	WhisperSndrIdsStatus = WhisperSndrCount + " SNDRs"
	Debug.Trace("PickmansWhisper: WhisperSndrIds loaded " + WhisperSndrCount)
EndFunction

Int Function ParsePositiveInt(String s)
	If !s
		Return -1
	EndIf
	Int n = 0
	Int i = 0
	Int len = GardenOfEden.StrLength(s)
	If len <= 0
		Return -1
	EndIf
	While i < len
		String c = GardenOfEden.SubStr(s, i, 1)
		Int d = -1
		If c == "0"
			d = 0
		ElseIf c == "1"
			d = 1
		ElseIf c == "2"
			d = 2
		ElseIf c == "3"
			d = 3
		ElseIf c == "4"
			d = 4
		ElseIf c == "5"
			d = 5
		ElseIf c == "6"
			d = 6
		ElseIf c == "7"
			d = 7
		ElseIf c == "8"
			d = 8
		ElseIf c == "9"
			d = 9
		EndIf
		If d < 0
			Return -1
		EndIf
		n = n * 10 + d
		i += 1
	EndWhile
	Return n
EndFunction

String[] Function GetAudioBankForStage(Int stage)
	If stage == 4
		Return AudioDesperateLines
	ElseIf stage == 3
		Return AudioStarvingLines
	ElseIf stage == 2
		Return AudioHungryLines
	ElseIf stage == 1
		Return AudioRestlessLines
	EndIf
	Return AudioCalmLines
EndFunction

Int Function GetAudioCountForStage(Int stage)
	If stage == 4
		Return AudioDesperateCount
	ElseIf stage == 3
		Return AudioStarvingCount
	ElseIf stage == 2
		Return AudioHungryCount
	ElseIf stage == 1
		Return AudioRestlessCount
	EndIf
	Return AudioCalmCount
EndFunction

Int Function FindWhisperSndrFid(String fileName)
	If !fileName || WhisperSndrCount <= 0
		Return 0
	EndIf
	Int i = 0
	While i < WhisperSndrCount
		If WhisperSndrFiles[i] == fileName
			Return WhisperSndrFids[i]
		EndIf
		i += 1
	EndWhile
	Return 0
EndFunction

; Audio-only roll — returns index or -1. No toast. Fail-loud via Notification if empty.
Int Function PickNoticeAudioIndex(Int stage)
	String[] bank = GetAudioBankForStage(stage)
	Int count = GetAudioCountForStage(stage)
	If count <= 0 || !bank
		Debug.Notification("Pickman's Whisper: audio-only — stage " + GetNoticeStageName(stage) + " map empty")
		Debug.Trace("PickmansWhisper: ERROR PickNoticeAudioIndex empty stage=" + stage)
		Return -1
	EndIf
	Int idx = Utility.RandomInt(0, count - 1)
	String fileName = bank[idx]
	Int tries = 0
	While tries < 8 && count > 1 && fileName == LastAudioFile
		idx = Utility.RandomInt(0, count - 1)
		fileName = bank[idx]
		tries += 1
	EndWhile
	LastAudioFile = fileName
	LastNoticePickIndex = idx
	LastNoticePickStage = stage
	Return idx
EndFunction

; Play SNDR for *_Audio.txt[index]. Fail loud on missing map/xwm/SNDR — never substitute.
Function PlayNoticeAudio(Int stage, Int index)
	; Same drawn-blade gate as toasts — silent skip (no error spam while gun is out).
	If !IsVoiceWeaponReady()
		Return
	EndIf
	If index < 0
		Debug.Notification("Pickman's Whisper: audio play skipped — bad index")
		Debug.Trace("PickmansWhisper: ERROR PlayNoticeAudio bad index stage=" + stage)
		Return
	EndIf
	String[] bank = GetAudioBankForStage(stage)
	Int count = GetAudioCountForStage(stage)
	If count <= 0 || !bank
		Debug.Notification("Pickman's Whisper: no audio map for " + GetNoticeStageName(stage))
		Debug.Trace("PickmansWhisper: ERROR PlayNoticeAudio empty map stage=" + stage)
		Return
	EndIf
	If index >= count
		Debug.Notification("Pickman's Whisper: audio index " + index + " out of range (" + count + ") " + GetNoticeStageName(stage))
		Debug.Trace("PickmansWhisper: ERROR PlayNoticeAudio OOB stage=" + stage + " idx=" + index + " count=" + count)
		Return
	EndIf
	String fileName = bank[index]
	If !fileName || GardenOfEden.StrLength(fileName) < 1
		Debug.Notification("Pickman's Whisper: empty audio filename at " + GetNoticeStageName(stage) + "[" + index + "]")
		Debug.Trace("PickmansWhisper: ERROR PlayNoticeAudio empty filename")
		Return
	EndIf
	PlayWhisperXwmByFile(fileName)
EndFunction

; Play one Whisper SNDR by map key (WhisperSndrIds). Top-level or relative
; under Sound\PickmansWhisper\ (e.g. Necromantic/Start/01-LooksPeaceful.xwm).
; Fail loud — never substitute.
Function PlayWhisperXwmByFile(String fileName)
	If !IsVoiceWeaponReady()
		Return
	EndIf
	If !fileName || GardenOfEden.StrLength(fileName) < 1
		Debug.Notification("Pickman's Whisper: empty audio filename")
		Debug.Trace("PickmansWhisper: ERROR PlayWhisperXwmByFile empty filename")
		Return
	EndIf
	String leaf = fileName
	String dirPath = ".\\Data\\Sound\\PickmansWhisper\\"
	Int len = GardenOfEden.StrLength(fileName)
	Int lastSep = -1
	Int si = 0
	While si < len
		String c = GardenOfEden.SubStr(fileName, si, 1)
		If c == "/" || c == "\\"
			lastSep = si
		EndIf
		si += 1
	EndWhile
	If lastSep >= 0
		String relDir = GardenOfEden.SubStr(fileName, 0, lastSep + 1)
		leaf = GardenOfEden.SubStr(fileName, lastSep + 1, -1)
		; GoE paths use backslashes; audio maps use forward slashes.
		String relBack = ""
		Int ri = 0
		Int rlen = GardenOfEden.StrLength(relDir)
		While ri < rlen
			String rc = GardenOfEden.SubStr(relDir, ri, 1)
			If rc == "/"
				relBack += "\\"
			Else
				relBack += rc
			EndIf
			ri += 1
		EndWhile
		dirPath = ".\\Data\\Sound\\PickmansWhisper\\" + relBack
	EndIf
	If !leaf || GardenOfEden.StrLength(leaf) < 1
		Debug.Notification("Pickman's Whisper: empty audio leaf for " + fileName)
		Return
	EndIf
	Bool xwmOk = GardenOfEden2.DoesFileExist(leaf, dirPath)
	If !xwmOk
		Debug.Notification("Pickman's Whisper: missing xwm " + fileName)
		Debug.Trace("PickmansWhisper: ERROR PlayWhisperXwmByFile xwm missing " + fileName + " path=" + dirPath)
		Return
	EndIf
	; WhisperSndrIds keys match the map line (forward-slash relative path).
	Int fid = FindWhisperSndrFid(fileName)
	If fid <= 0
		Debug.Notification("Pickman's Whisper: no SNDR id for " + fileName + " — rebuild ESP")
		Debug.Trace("PickmansWhisper: ERROR PlayWhisperXwmByFile no FormID for " + fileName)
		Return
	EndIf
	If !PlayerRef
		PlayerRef = Game.GetPlayer()
	EndIf
	If !PlayerRef
		Debug.Notification("Pickman's Whisper: audio play — no player")
		Return
	EndIf
	Sound snd = Game.GetFormFromFile(fid, "PickmansWhisper.esp") as Sound
	If !snd
		Debug.Notification("Pickman's Whisper: SNDR missing for " + fileName + " (fid=" + fid + ")")
		Debug.Trace("PickmansWhisper: ERROR PlayWhisperXwmByFile GetFormFromFile failed fid=" + fid + " file=" + fileName)
		Return
	EndIf
	Int inst = snd.Play(PlayerRef)
	If inst == 0
		Debug.Notification("Pickman's Whisper: Play failed for " + fileName + " (instance 0)")
		Debug.Trace("PickmansWhisper: ERROR PlayWhisperXwmByFile Play=0 file=" + fileName)
		Return
	EndIf
	LastAudioFile = fileName
	Debug.Trace("PickmansWhisper: PlayWhisperXwmByFile " + fileName + " inst=" + inst)
EndFunction

; One modal dialog with the full step-by-step load trace (screenshot-friendly).
; MCM Debug "Test notice file load" only — never call from OnQuestInit / load resume.
Function ReportNoticeLoadStatus()
	String msg = "PICKMANS WHISPER NOTICE LOAD || " + NoticeLoadDiag
	Debug.Trace("PickmansWhisper notice load: " + msg)
	Debug.MessageBox(msg)
EndFunction

; Space-joined list of stages whose file did not load (count <= 0), else "".
String Function NoticeLoadFailureList()
	String s = ""
	If NoticeCalmCount <= 0
		s += "calm "
	EndIf
	If NoticeRestlessCount <= 0
		s += "restless "
	EndIf
	If NoticeHungryCount <= 0
		s += "hungry "
	EndIf
	If NoticeStarvingCount <= 0
		s += "starving "
	EndIf
	If NoticeDesperateCount <= 0
		s += "desperate "
	EndIf
	Return TrimString(s)
EndFunction

; Push the five per-stage load results to their MCM Debug rows.
Function WriteNoticeLoadStatusToMcm()
	If !MCM.IsInstalled()
		Return
	EndIf
	MCM.SetModSettingString(MOD_NAME, "sNoticeCalm:Debug", NoticeCalmStatus)
	MCM.SetModSettingString(MOD_NAME, "sNoticeRestless:Debug", NoticeRestlessStatus)
	MCM.SetModSettingString(MOD_NAME, "sNoticeHungry:Debug", NoticeHungryStatus)
	MCM.SetModSettingString(MOD_NAME, "sNoticeStarving:Debug", NoticeStarvingStatus)
	MCM.SetModSettingString(MOD_NAME, "sNoticeDesperate:Debug", NoticeDesperateStatus)
EndFunction

; Game-root-relative config path, exactly mirroring Necromantic's proven
; WitnessInsults/Positions loader (".\Data\<Mod>\config\"). This is the form GoE
; documents (asFilePath relative to the Fallout 4 root, leading ".\", trailing "\").
; Returned from a function so it can never be "" on an old save (a stale script
; String var can deserialize empty, which would break the read).
String Function NoticeConfigPath()
	Return ".\\Data\\PickmansWhisper\\config\\"
EndFunction

; Necromantic intimacy banks (E4) — subdirectory under config/.
String Function NecromanticConfigPath()
	Return ".\\Data\\PickmansWhisper\\config\\necromantic\\"
EndFunction

; Load one config .txt into a pre-allocated String[64] bank; returns usable count.
Int Function LoadStageBank(String fileName, String[] bank)
	Return LoadStageBankAt(fileName, bank, NoticeConfigPath())
EndFunction

; Mirrors Necromantic LoadWitnessInsults / LoadPositionList: DoesFileExist ->
; GetLinesFromFile -> parse (# and blank lines skipped). Files-only (no builtin
; fallback). Sets LastStageLoadStatus (MCM) and LastStageLoadDiag (MessageBox trace).
Int Function LoadStageBankAt(String fileName, String[] bank, String path)
	String nl = " | "
	LastStageLoadDiag = fileName
	; Pessimistic default survives a GoE2 native abort (e.g. GoE not installed).
	LastStageLoadStatus = "READ FAILED (GoE2 missing?)"
	Bool exists = GardenOfEden2.DoesFileExist(fileName, path)
	LastStageLoadDiag += nl + "exists=" + exists
	If !exists
		LastStageLoadStatus = "MISSING FILE (" + path + fileName + ")"
		LastStageLoadDiag += nl + "RESULT: NOT FOUND"
		Return 0
	EndIf
	String[] raw = GardenOfEden2.GetLinesFromFile(fileName, path)
	Int rawLen = 0
	If raw
		rawLen = raw.Length
	EndIf
	LastStageLoadDiag += nl + "raw lines=" + rawLen
	If raw && rawLen > 0
		LastStageLoadDiag += nl + "line0='" + raw[0] + "' len=" + GardenOfEden.StrLength(raw[0])
	EndIf
	If !raw || raw.Length == 0
		LastStageLoadStatus = "READ FAILED / EMPTY (GoE2 returned nothing)"
		LastStageLoadDiag += nl + "RESULT: EMPTY/UNREADABLE"
		Return 0
	EndIf
	Int n = ParseRawIntoBank(raw, bank)
	LastStageLoadDiag += nl + "parsed=" + n
	If n <= 0
		LastStageLoadStatus = "EMPTY (no usable lines)"
		LastStageLoadDiag += nl + "RESULT: NO USABLE LINES"
	Else
		LastStageLoadStatus = n + " lines"
		LastStageLoadDiag += nl + "RESULT: OK (" + n + ")"
	EndIf
	Return n
EndFunction

; Copy trimmed, non-comment, non-blank lines into bank (max 64). Returns count.
; Comment check uses GoE SubStr — FO4 has no StringUtil (see no-fake-native-stubs).
Int Function ParseRawIntoBank(String[] raw, String[] bank)
	Int n = 0
	Int i = 0
	While i < raw.Length && n < 64
		String line = TrimString(raw[i])
		i += 1
		If line == ""
			; skip
		ElseIf GardenOfEden.SubStr(line, 0, 1) == "#"
			; comment
		Else
			bank[n] = line
			n += 1
		EndIf
	EndWhile
	Return n
EndFunction

; Trims leading/trailing whitespace (spaces, tabs, trailing CR that GetLinesFromFile
; can leave on CRLF files) and normalizes internal runs of whitespace to single
; spaces. FO4/F4SE has NO built-in StringUtil (Skyrim/SKSE only), so this goes
; through Garden of Eden: GetWordsInStringAsArray. See no-fake-native-stubs.
; Mirrors Necromantic TrimString exactly.
String Function TrimString(String s)
	If s == ""
		Return s
	EndIf
	String[] words = GardenOfEden2.GetWordsInStringAsArray(s)
	If !words || words.Length == 0
		Return ""
	EndIf
	String out = words[0]
	Int i = 1
	While i < words.Length
		out += " " + words[i]
		i += 1
	EndWhile
	Return out
EndFunction

Function UseBuiltinTrustFallback()
	TrustLines = new String[LINE_FILE_MAX]
	TrustLines[0] = "You hear me. Good. Stay a while."
	TrustLines[1] = "I like the way you hold still in these halls."
	TrustLines[2] = "We're getting along already... aren't we?"
	TrustLines[3] = "Keep the knife close. It likes you."
	TrustLines[4] = "No need to rush. I'm not going anywhere."
	TrustLines[5] = "The paint chips look like smiles up close."
	TrustLines[6] = "You came seeking a gift. You found a friend."
	TrustLines[7] = "Quiet steps. Careful hands. Perfect."
	TrustLineCount = 8
EndFunction

Function UseBuiltinHungerFallback()
	HungerLines = new String[LINE_FILE_MAX]
	HungerLines[0] = "A restless edge... the blade wants use."
	HungerLines[1] = "Hunger grows while the knife sleeps."
	HungerLines[2] = "You feel it — that neat, bright need."
	HungerLines[3] = "Feed me. Just once. You'll see."
	HungerLines[4] = "The itching behind your eyes is for someone soft and still."
	HungerLines[5] = "Unused steel turns mean. You know how to fix that."
	HungerLines[6] = "They won't understand. We will."
	HungerLineCount = 7
EndFunction

Function UseBuiltinPraiseFallback()
	PraiseLines = new String[LINE_FILE_MAX]
	PraiseLines[0] = "Yes... that was beautiful. Rest a moment."
	PraiseLines[1] = "Perfect. Clean. The blade is smiling."
	PraiseLines[2] = "You felt that, didn't you? So did I."
	PraiseLines[3] = "Again when you're ready. I'll wait."
	PraiseLines[4] = "Good. They hardly knew how to thank you."
	PraiseLines[5] = "Quiet work. Elegant. Keep going."
	PraiseLines[6] = "I knew you'd understand us."
	PraiseLines[7] = "Hunger sleeps. For a little while."
	PraiseLineCount = 8
EndFunction

String Function PickTrustLine()
	If TrustLineCount <= 0 || !TrustLines
		LoadTrustLines()
	EndIf
	If TrustLineCount <= 0
		Return "You hear me. Good."
	EndIf
	Return TrustLines[Utility.RandomInt(0, TrustLineCount - 1)]
EndFunction

String Function PickHungerLine()
	If HungerLineCount <= 0 || !HungerLines
		LoadHungerLines()
	EndIf
	If HungerLineCount <= 0
		Return "The blade is hungry."
	EndIf
	Return HungerLines[Utility.RandomInt(0, HungerLineCount - 1)]
EndFunction

String Function PickPraiseLine()
	If PraiseLineCount <= 0 || !PraiseLines
		LoadPraiseLines()
	EndIf
	If PraiseLineCount <= 0
		Return "Yes... that was beautiful. Rest a moment."
	EndIf
	Return PraiseLines[Utility.RandomInt(0, PraiseLineCount - 1)]
EndFunction

; Whisper stage from hunger %: 0 calm / 1 restless / 2 hungry / 3 starving / 4 desperate.
; Read-only off HungerLevel — speaking a line never advances the stage.
Int Function GetNoticeStage()
	; Debug override: MCM "Force notice stage" pins the stage to the dropdown value
	; so each stage can be tested without grinding hunger. Off = derive from hunger.
	If IsNoticeStageForced()
		Int forced = MCM.GetModSettingInt(MOD_NAME, "iNoticeStage:Debug")
		If forced < 0
			Return 0
		ElseIf forced > 4
			Return 4
		EndIf
		Return forced
	EndIf
	Float level = HungerLevel
	If level >= 90.0
		Return 4
	ElseIf level >= 70.0
		Return 3
	ElseIf level >= 50.0
		Return 2
	ElseIf level >= 25.0
		Return 1
	EndIf
	Return 0
EndFunction

Bool Function IsNoticeStageForced()
	If !MCM.IsInstalled()
		Return False
	EndIf
	Return MCM.GetModSettingBool(MOD_NAME, "bForceNoticeStage:Debug")
EndFunction

String Function GetNoticeStageName(Int stage)
	If stage == 4
		Return "desperate"
	ElseIf stage == 3
		Return "starving"
	ElseIf stage == 2
		Return "hungry"
	ElseIf stage == 1
		Return "restless"
	EndIf
	Return "calm"
EndFunction

String[] Function GetNoticeBankForStage(Int stage)
	If stage == 4
		Return NoticeDesperateLines
	ElseIf stage == 3
		Return NoticeStarvingLines
	ElseIf stage == 2
		Return NoticeHungryLines
	ElseIf stage == 1
		Return NoticeRestlessLines
	EndIf
	Return NoticeCalmLines
EndFunction

Int Function GetNoticeCountForStage(Int stage)
	If stage == 4
		Return NoticeDesperateCount
	ElseIf stage == 3
		Return NoticeStarvingCount
	ElseIf stage == 2
		Return NoticeHungryCount
	ElseIf stage == 1
		Return NoticeRestlessCount
	EndIf
	Return NoticeCalmCount
EndFunction

; Files-only: returns "" when the current stage's file did not load. Callers must
; treat "" as "skip this whisper" — there is no hardcoded fallback line.
; Sets LastNoticePickIndex / LastNoticePickStage for D1 same-index audio.
String Function PickNoticeLine(String npcName)
	Int stage = GetNoticeStage()
	String[] bank = GetNoticeBankForStage(stage)
	Int count = GetNoticeCountForStage(stage)
	If count <= 0 || !bank
		; One retry in case the poll beat the initial load; then give up (skip).
		LoadNoticeLines()
		bank = GetNoticeBankForStage(stage)
		count = GetNoticeCountForStage(stage)
	EndIf
	If count <= 0 || !bank
		LastNoticePickIndex = -1
		LastNoticePickStage = stage
		Return ""
	EndIf

	String useName = NoticeNameForLine(npcName)
	Bool wantNameless = (useName == "")

	Int idx = Utility.RandomInt(0, count - 1)
	String raw = bank[idx]
	; One bounded reroll loop covers two wants: no immediate repeat, and (for
	; unnamed targets like generic settlers) prefer lines without {name} so we
	; never toast an awkwardly stripped sentence.
	Int tries = 0
	While tries < 8 && count > 1 && (raw == LastNoticeLine || (wantNameless && StrContains(raw, "{name}")))
		idx = Utility.RandomInt(0, count - 1)
		raw = bank[idx]
		tries += 1
	EndWhile
	If !raw
		LastNoticePickIndex = -1
		LastNoticePickStage = stage
		Return ""
	EndIf
	LastNoticeLine = raw
	LastNoticePickIndex = idx
	LastNoticePickStage = stage

	; ApplyNamePlaceholder strips {name} safely when there's no usable name.
	Return ApplyNamePlaceholder(raw, useName)
EndFunction

; Workshop / leveled labels / glyph junk are useless in whispers — treat as unnamed.
; Real names (Piper) and P3 player-assigned labels (Anne-Marie, O'Malley) pass.
String Function NoticeNameForLine(String npcName)
	If !npcName
		Return ""
	EndIf
	; Engine sometimes returns 1–2 unprintable glyphs (toast shows solid squares).
	If !IsUsableWhisperName(npcName)
		Return ""
	EndIf
	; Papyrus string compare is case-insensitive
	If npcName == "Settler" || npcName == "Raider" || npcName == "Gunner" || npcName == "Tramp"
		Return ""
	EndIf
	If npcName == "Scavenger" || npcName == "Farmer" || npcName == "Wastelander" || npcName == "Survivor"
		Return ""
	EndIf
	; Workshop / SS2-style labels (e.g. "Resident") — never toast as a personal name.
	If npcName == "Resident" || npcName == "Citizen" || npcName == "Neighbor" || npcName == "Worker"
		Return ""
	EndIf
	If StrContains(npcName, "Settler") || StrContains(npcName, "Resident")
		Return ""
	EndIf
	Return npcName
EndFunction

; True if every character is a common name glyph and at least one letter is present.
; GoE-only (no StringUtil) — rejects □□ / control junk that FO4 still treats as non-empty.
Bool Function IsUsableWhisperName(String npcName)
	If !npcName
		Return False
	EndIf
	String s = TrimString(npcName)
	Int n = GardenOfEden.StrLength(s)
	If n < 2
		Return False
	EndIf
	; Letters + digits + common name punctuation (case-insensitive via ReplaceStr path).
	String allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 -'."
	String letters = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
	Bool hasLetter = False
	Int i = 0
	While i < n
		String c = GardenOfEden.SubStr(s, i, 1)
		If !c || !StrContains(allowed, c)
			Return False
		EndIf
		If StrContains(letters, c)
			hasLetter = True
		EndIf
		i += 1
	EndWhile
	Return hasLetter
EndFunction

; GoE string ops only — FO4 has no StringUtil (see no-fake-native-stubs).
String Function ApplyNamePlaceholder(String line, String npcName)
	If !line
		Return ""
	EndIf
	If !npcName
		Return StripNamePlaceholder(line)
	EndIf
	If !StrContains(line, "{name}")
		Return line
	EndIf
	Return GardenOfEden.ReplaceStr(line, "{name}", npcName)
EndFunction

; Remove {name} — do NOT substitute "them" (that became a one-word toast).
; Also drop separators that immediately followed the placeholder (". ", " - ", " — ").
; IMPORTANT: GoE StrFind is an occurrence COUNT, not a char index — never slice with it.
; ReplaceStr of "{name}"+separator first, then bare "{name}".
String Function StripNamePlaceholder(String line)
	If !line
		Return ""
	EndIf
	If !StrContains(line, "{name}")
		Return line
	EndIf
	String out = line
	; Longer forms first so ". " / " - " / " — " leave with the placeholder.
	out = GardenOfEden.ReplaceStr(out, "{name}. ", "")
	out = GardenOfEden.ReplaceStr(out, "{name} - ", "")
	out = GardenOfEden.ReplaceStr(out, "{name} — ", "")
	out = GardenOfEden.ReplaceStr(out, "{name}— ", "")
	out = GardenOfEden.ReplaceStr(out, "{name}.", "")
	out = GardenOfEden.ReplaceStr(out, "{name}", "")
	out = TrimString(out)
	out = StripLeadingNameSeparator(out)
	If !out || GardenOfEden.StrLength(out) < 8
		; Degenerate user line (e.g. just "{name}") — skip rather than fake one.
		Return ""
	EndIf
	Return out
EndFunction

; True if needle occurs in hay — ReplaceStr based (GoE StrFind is not a safe index).
Bool Function StrContains(String hay, String needle)
	If !hay || !needle
		Return False
	EndIf
	Return GardenOfEden.ReplaceStr(hay, needle, "") != hay
EndFunction

; Leading cleanup only — uses SubStr prefix checks, not StrFind==0.
String Function StripLeadingNameSeparator(String s)
	If !s
		Return ""
	EndIf
	If GardenOfEden.StrLength(s) >= 2 && GardenOfEden.SubStr(s, 0, 2) == ". "
		Return GardenOfEden.SubStr(s, 2)
	EndIf
	If GardenOfEden.StrLength(s) >= 3 && GardenOfEden.SubStr(s, 0, 3) == " - "
		Return GardenOfEden.SubStr(s, 3)
	EndIf
	If GardenOfEden.StrLength(s) >= 3 && GardenOfEden.SubStr(s, 0, 3) == " — "
		Return GardenOfEden.SubStr(s, 3)
	EndIf
	If GardenOfEden.StrLength(s) >= 2 && GardenOfEden.SubStr(s, 0, 2) == "— "
		Return GardenOfEden.SubStr(s, 2)
	EndIf
	If s == "."
		Return ""
	EndIf
	Return s
EndFunction

Function ToastPraiseLine(String line)
	If line == "" || !IsVoiceEnabled()
		Return
	EndIf
	If !IsVoiceWeaponReady()
		Return
	EndIf
	Float now = Utility.GetCurrentRealTime()
	If (now - LastPraiseToastRealTime) < PRAISE_TOAST_COOLDOWN
		Return
	EndIf
	LastPraiseToastRealTime = now
	; Praise may fire mid-combat; allow even if menus briefly steal focus
	ShowVoiceToast(line)
	Debug.Trace("PickmansWhisper: praise | " + line)
EndFunction

; --- Hunger --------------------------------------------------------------------

Function StartHungerPoll()
	EnsureHungerSpell()
	If LastHungerPollGameTime <= 0.0
		LastHungerPollGameTime = Utility.GetCurrentGameTime()
	EndIf
	CancelTimer(TIMER_HUNGER)
	StartTimer(HUNGER_POLL_SECONDS, TIMER_HUNGER)
	SyncHungerAddictionSpell()
	RefreshHungerPanel(False)
EndFunction

Function EnsureHungerSpell()
	If KnifeHungerSpell && KnifeHungerAgiEffect && KnifeHungerGlobal
		Return
	EndIf
	If !KnifeHungerSpell
		Form f = Game.GetFormFromFile(FID_HUNGER_SPEL, "PickmansWhisper.esp")
		KnifeHungerSpell = f as Spell
		If KnifeHungerSpell
			Debug.Trace("PickmansWhisper: Knife Hunger SPEL loaded")
		ElseIf !HungerSpellLoadWarned
			HungerSpellLoadWarned = True
			Debug.Trace("PickmansWhisper: ERROR Knife Hunger SPEL missing — rebuild ESP")
			Debug.Notification("Pickman's Whisper: Knife Hunger spell missing (update ESP)")
		EndIf
	EndIf
	If !KnifeHungerGlobal
		KnifeHungerGlobal = Game.GetFormFromFile(FID_HUNGER_GLOB, "PickmansWhisper.esp") as GlobalVariable
	EndIf
	If !KnifeHungerAgiEffect
		KnifeHungerAgiEffect = Game.GetFormFromFile(FID_HUNGER_MGEF_AGI, "PickmansWhisper.esp") as MagicEffect
	EndIf
	If !KnifeHungerChaEffect
		KnifeHungerChaEffect = Game.GetFormFromFile(FID_HUNGER_MGEF_CHA, "PickmansWhisper.esp") as MagicEffect
	EndIf
EndFunction

Bool Function IsHungerUnlocked()
	Return BondStarted
EndFunction

Bool Function IsHungerAddictionSpellEnabled()
	If MCM.IsInstalled()
		Return MCM.GetModSettingBool(MOD_NAME, "bAddictionSpell:Hunger")
	EndIf
	Return True
EndFunction

Bool Function IsVoiceEnabled()
	If MCM.IsInstalled()
		Return MCM.GetModSettingBool(MOD_NAME, "bVoiceToasts:Voice")
	EndIf
	Return True
EndFunction

; 0 = Toast + Audio (default), 1 = Audio only, 2 = Toast only.
Int Function GetVoiceDeliveryMode()
	If MCM.IsInstalled()
		Int v = MCM.GetModSettingInt(MOD_NAME, "iVoiceDelivery:Voice")
		If v < 0
			Return 0
		EndIf
		If v > 2
			Return 2
		EndIf
		Return v
	EndIf
	Return 0
EndFunction

Float Function GetHungerTimeGainPerHour()
	Float v = 5.0
	If MCM.IsInstalled()
		v = MCM.GetModSettingFloat(MOD_NAME, "fTimeGain:Hunger")
	EndIf
	If v < 0.0
		v = 0.0
	EndIf
	Return v
EndFunction

Float Function GetHungerAddictedThreshold()
	Float v = 70.0
	If MCM.IsInstalled()
		v = MCM.GetModSettingFloat(MOD_NAME, "fAddictedAt:Hunger")
	EndIf
	If v < 1.0
		v = 70.0
	EndIf
	Return v
EndFunction

Float Function GetHungerSatedHours()
	Float v = 2.0
	If MCM.IsInstalled()
		v = MCM.GetModSettingFloat(MOD_NAME, "fSatedHours:Hunger")
	EndIf
	If v < 0.5
		v = 0.5
	EndIf
	Return v
EndFunction

Bool Function IsHungerSated()
	Float now = Utility.GetCurrentGameTime()
	Return SatedUntilGameTime > 0.0 && now < SatedUntilGameTime
EndFunction

String Function GetHungerBandLabel(Float level)
	If level >= 90.0
		Return "desperate"
	ElseIf level >= 70.0
		Return "starving"
	ElseIf level >= 50.0
		Return "hungry"
	ElseIf level >= 25.0
		Return "restless"
	EndIf
	Return "calm"
EndFunction

Function RunHungerTick()
	If !IsHungerUnlocked()
		LastHungerPollGameTime = Utility.GetCurrentGameTime()
		HungerWasSated = False
		SyncHungerAddictionSpell()
		Return
	EndIf
	If Utility.IsInMenuMode()
		Return
	EndIf

	Float now = Utility.GetCurrentGameTime()
	If LastHungerPollGameTime <= 0.0
		LastHungerPollGameTime = now
	EndIf
	Float last = LastHungerPollGameTime

	Bool satedNow = IsHungerSated()
	If HungerWasSated && !satedNow
		ToastHungerLine("The quiet ends. The knife remembers.")
		ApplyHungerDelta(20.0, "withdrawal-onset")
	EndIf

	If !satedNow
		; Unused knife-time: blade owned (or bond active) without recent activity.
		; Slice A treats LastKnifeActivityGameTime as bond start until B updates it.
		Float gainStart = last
		If SatedUntilGameTime > gainStart
			If now > SatedUntilGameTime
				gainStart = SatedUntilGameTime
			Else
				gainStart = now
			EndIf
		EndIf
		Float hours = (now - gainStart) * 24.0
		If hours > 0.0
			ApplyHungerDelta(hours * GetHungerTimeGainPerHour(), "unused-knife-time")
		EndIf
	EndIf

	HungerWasSated = satedNow
	LastHungerPollGameTime = now
	SyncHungerAddictionSpell()
	RefreshHungerPanel(False)
	; Hunger timer is proven live — drive notice poll from here too
	MaybeSpeakNoticeLine("hunger")
EndFunction

Function ApplyHungerDelta(Float amount, String reason)
	If amount == 0.0
		Return
	EndIf
	Float before = HungerLevel
	HungerLevel = HungerLevel + amount
	If HungerLevel > 100.0
		HungerLevel = 100.0
	ElseIf HungerLevel < 0.0
		HungerLevel = 0.0
	EndIf
	Debug.Trace("PickmansWhisper: hunger " + before + " -> " + HungerLevel + " (" + reason + ")")
	MaybeToastHungerBand(before, HungerLevel)
	SyncHungerAddictionSpell()
EndFunction

Function MaybeToastHungerBand(Float before, Float after)
	Int band = 0
	If after >= 90.0
		band = 90
	ElseIf after >= 70.0
		band = 70
	ElseIf after >= 50.0
		band = 50
	ElseIf after >= 25.0
		band = 25
	EndIf
	If band > LastHungerBand
		LastHungerBand = band
		String line = PickHungerLine()
		If band == 25
			If line == ""
				line = "A restless edge... the blade wants use."
			EndIf
		ElseIf band == 50
			If line == ""
				line = "Hunger grows while the knife sleeps."
			EndIf
		ElseIf band == 70
			If line == ""
				line = "You feel it — that neat, bright need."
			EndIf
		ElseIf band == 90
			If line == ""
				line = "Feed me. Just once. You'll see."
			EndIf
		EndIf
		ToastHungerLine(line)
	ElseIf after < 25.0 && LastHungerBand > 0
		LastHungerBand = 0
	EndIf
EndFunction

; --- Knife kills (Slice B) -----------------------------------------------------
; GoE FindActors + IsDead() like Necromantic. Driven by bond poll (proven) + StartTimer(13).

String Function EnsureCombatKillHooks()
	If !PlayerRef
		PlayerRef = Game.GetPlayer()
	EndIf
	EnsureKillWatchList()
	EnsureAliveSeenList()
	StartKillScanLoop()
	String status = "scan BOND+T13 living=" + KillWatchCount
	ToastDebug("PW [" + DEBUG_BUILD + "]: " + status)
	Debug.Trace("PickmansWhisper: EnsureCombatKillHooks " + DEBUG_BUILD + " " + status)
	AnnounceKillScanArmed()
	Return status
EndFunction

Function AnnounceKillScanArmed()
	If KillScanArmAnnounced
		Return
	EndIf
	KillScanArmAnnounced = True
	; Toast only — never MessageBox on arm/load (modals are MCM Debug buttons only).
	ToastDebug("PW kill scan armed [" + DEBUG_BUILD + "]")
	Debug.Trace("PickmansWhisper: kill scan armed " + DEBUG_BUILD)
EndFunction

Function StartKillScanLoop()
	; Necromantic uses StartTimer for craving — same approach, id 13
	CancelTimer(TIMER_KILL_SCAN)
	StartTimer(KILL_SCAN_SECONDS, TIMER_KILL_SCAN)
EndFunction

Function RunKillScanTick()
	If !PlayerRef
		PlayerRef = Game.GetPlayer()
	EndIf
	If !PlayerRef
		Return
	EndIf

	AnnounceKillScanArmed()

	Actor ct = PlayerRef.GetCombatTarget()
	If ct && !ct.IsDead() && IsBladeEquipped()
		TrackLivingNear(ct)
	EndIf

	ScanLivingToDeadTransitions()

	KillScanTickCount += 1
	; Fixation first (every ~2s tick) — look-edge must not lose to hunger toast / NPC cool.
	TickLookFixation()
	; Hunger whisper: poll often; ToastNoticeLine gated to ~1 per game hour.
	If BondStarted
		MaybeSpeakNoticeLine("killscan")
	ElseIf (KillScanTickCount % 6) == 0
		; Still prove the timer fires before bond — status only
		MaybeSpeakNoticeLine("killscan-prebond")
	EndIf
	If KillScanTickCount == 1 || (KillScanTickCount % 3) == 0
		String bladeBit = "blade=NO"
		If IsBladeEquipped()
			bladeBit = "blade=YES"
		EndIf
		ToastDebug("PW scan [" + DEBUG_BUILD + "] #" + KillScanTickCount + " near=" + KillWatchCount + " goeA=" + LastGoeAliveCount + " goeD=" + LastGoeDeadCount + " det=" + LastDetectCount + " " + bladeBit + " notice=" + LastNoticeStatus)
	EndIf
EndFunction

Function ScanLivingToDeadTransitions()
	If !PlayerRef
		Return
	EndIf

	Bool bladeReady = IsBladeKillWeaponReady()

	; --- Living sources -------------------------------------------------------
	; GoE: lifeState 0=dead (Necromantic). 1=alive. selectiveProcessMode 0 = broad.
	Actor[] alive = GardenOfEden.FindActors(None, None, -1, -1, PlayerRef, KILL_WATCH_RADIUS, 1, -1, -1, -1, -1, -1, None, None, "", 0, 1, 0)
	LastGoeAliveCount = 0
	If alive
		LastGoeAliveCount = alive.Length
	EndIf

	; NPCs that currently detect the player (works in combat; may miss total stealth)
	Actor[] detecting = GardenOfEden2.GetActorsDetecting(PlayerRef, False)
	LastDetectCount = 0
	If detecting
		LastDetectCount = detecting.Length
	EndIf

	; --- Dead source (exact Necromantic craving / target filter, no sex filter) -
	Actor[] dead = GardenOfEden.FindActors(None, None, -1, -1, PlayerRef, KILL_CORPSE_RADIUS, 0, 1, -1, -1, -1, -1, None, None, "", 0, 1, 1)
	LastGoeDeadCount = 0
	If dead
		LastGoeDeadCount = dead.Length
	EndIf

	Int i = 0
	Int n = LastGoeAliveCount
	If n > 24
		n = 24
	EndIf
	; Stamp living links always; satiation still requires IsBladeEquipped at kill time.
	While i < n
		Actor ak = alive[i]
		If ak && ak != PlayerRef && !ak.IsDead() && !ak.IsDisabled()
			TrackLivingNear(ak)
		EndIf
		i += 1
	EndWhile

	i = 0
	n = LastDetectCount
	If n > 24
		n = 24
	EndIf
	While i < n
		Actor ak = detecting[i]
		If ak && ak != PlayerRef && !ak.IsDead() && !ak.IsDisabled()
			TrackLivingNear(ak)
		EndIf
		i += 1
	EndWhile

	; Tracked living → dead (only evaluate satiation if blade is the kill weapon)
	EnsureKillWatchList()
	i = 0
	While i < KillWatchCount
		Actor ak = KillWatchList[i]
		If !ak
			RemoveKillWatchAt(i)
		ElseIf ak.IsDead()
			ToastHumanKillDetected(ak, "live-dead")
			HandlePotentialKnifeKill(ak, PlayerRef)
			RemoveKillWatchAt(i)
		ElseIf !ak.Is3DLoaded() || PlayerRef.GetDistance(ak) > KILL_WATCH_RADIUS
			RemoveKillWatchAt(i)
		Else
			i += 1
		EndIf
	EndWhile

	; Necromantic-style corpse pass + "new corpse while blade equipped"
	i = 0
	n = LastGoeDeadCount
	If n > 16
		n = 16
	EndIf
	While i < n
		Actor ak = dead[i]
		If ak && ak != PlayerRef && ak.IsDead() && ak.Is3DLoaded() && !ak.IsDisabled()
			Int id = ak.GetFormID()
			If WasAliveSeen(ak) || IsInKillWatchList(ak) || (ak == PendingKillVictim)
				ToastHumanKillDetected(ak, "dead-scan")
				HandlePotentialKnifeKill(ak, PlayerRef)
				NoteBackgroundDead(id)
			ElseIf !IsBackgroundDead(id)
				If KillScanTickCount <= 2 || !bladeReady
					; Warm-up / other weapon: remember existing corpses so they don't false-sate
					NoteBackgroundDead(id)
				ElseIf WasFriendlySeen(ak)
					; New corpse of someone we already marked non-hostile while living
					NoteAliveSeen(ak)
					ToastHumanKillDetected(ak, "new-corpse")
					HandlePotentialKnifeKill(ak, PlayerRef)
					NoteBackgroundDead(id)
				Else
					NoteBackgroundDead(id)
				EndIf
			EndIf
		EndIf
		i += 1
	EndWhile
EndFunction

Function EnsureBackgroundDeadList()
	If !BackgroundDeadIds || BackgroundDeadIds.Length == 0
		BackgroundDeadIds = new Int[48]
		BackgroundDeadCount = 0
	EndIf
EndFunction

Bool Function IsBackgroundDead(Int id)
	If id == 0
		Return False
	EndIf
	EnsureBackgroundDeadList()
	Int i = 0
	While i < BackgroundDeadCount
		If BackgroundDeadIds[i] == id
			Return True
		EndIf
		i += 1
	EndWhile
	Return False
EndFunction

Function NoteBackgroundDead(Int id)
	If id == 0 || IsBackgroundDead(id)
		Return
	EndIf
	EnsureBackgroundDeadList()
	If BackgroundDeadCount >= BACKGROUND_DEAD_MAX
		Int j = 0
		While j < BACKGROUND_DEAD_MAX - 1
			BackgroundDeadIds[j] = BackgroundDeadIds[j + 1]
			j += 1
		EndWhile
		BackgroundDeadCount = BACKGROUND_DEAD_MAX - 1
	EndIf
	BackgroundDeadIds[BackgroundDeadCount] = id
	BackgroundDeadCount += 1
EndFunction

Function RemoveKillWatchAt(Int index)
	EnsureKillWatchList()
	If index < 0 || index >= KillWatchCount
		Return
	EndIf
	Actor gone = KillWatchList[index]
	If gone
		RemoveAliveSeenId(gone.GetFormID())
	EndIf
	Int j = index
	While j < KillWatchCount - 1
		KillWatchList[j] = KillWatchList[j + 1]
		j += 1
	EndWhile
	KillWatchList[KillWatchCount - 1] = None
	KillWatchCount -= 1
EndFunction

; Drop active watch when switching to a non-blade weapon. Keep AliveSeen / FriendlySeen.
Function ClearKillWatchForWeaponSwap()
	PendingKillVictim = None
	KillWatchCount = 0
	If KillWatchList
		Int i = 0
		While i < KillWatchList.Length
			KillWatchList[i] = None
			i += 1
		EndWhile
	EndIf
	BladeTaggedCount = 0
EndFunction

Function RemoveAliveSeenId(Int id)
	If id == 0 || !AliveSeenIds
		Return
	EndIf
	Int i = 0
	While i < AliveSeenCount
		If AliveSeenIds[i] == id
			Int j = i
			While j < AliveSeenCount - 1
				AliveSeenIds[j] = AliveSeenIds[j + 1]
				j += 1
			EndWhile
			AliveSeenCount -= 1
			Return
		EndIf
		i += 1
	EndWhile
EndFunction

Function TrackLivingNear(Actor ak)
	; Track loosely — validity (sex / hostility / essential) enforced at kill time.
	If !ak || ak == PlayerRef || ak.IsDead() || ak.IsDisabled()
		Return
	EndIf
	If IsChildNpc(ak) && !IsChildTargetAllowed()
		Return
	EndIf
	NoteAliveSeen(ak)
	; Stamp disposition while still living — before the player turns a settler hostile.
	If PlayerRef && ak.IsHostileToActor(PlayerRef)
		; Hostile when first/ongoing seen — do not mark friendly
	Else
		NoteFriendlySeen(ak)
	EndIf
	If IsInKillWatchList(ak)
		Return
	EndIf
	EnsureKillWatchList()
	If KillWatchCount >= KILL_WATCH_MAX
		RemoveKillWatchAt(0)
	EndIf
	KillWatchList[KillWatchCount] = ak
	KillWatchCount += 1
	Debug.Trace("PickmansWhisper: track living id=" + ak.GetFormID() + " n=" + KillWatchCount)
EndFunction

Function EnsureFriendlySeenList()
	If !FriendlySeenIds || FriendlySeenIds.Length == 0
		FriendlySeenIds = new Int[32]
		FriendlySeenCount = 0
	EndIf
EndFunction

Function NoteFriendlySeen(Actor ak)
	If !ak
		Return
	EndIf
	EnsureFriendlySeenList()
	Int id = ak.GetFormID()
	Int i = 0
	While i < FriendlySeenCount
		If FriendlySeenIds[i] == id
			Return
		EndIf
		i += 1
	EndWhile
	If FriendlySeenCount >= FRIENDLY_SEEN_MAX
		Int j = 0
		While j < FRIENDLY_SEEN_MAX - 1
			FriendlySeenIds[j] = FriendlySeenIds[j + 1]
			j += 1
		EndWhile
		FriendlySeenCount = FRIENDLY_SEEN_MAX - 1
	EndIf
	FriendlySeenIds[FriendlySeenCount] = id
	FriendlySeenCount += 1
EndFunction

Bool Function WasFriendlySeen(Actor ak)
	If !ak
		Return False
	EndIf
	EnsureFriendlySeenList()
	Int id = ak.GetFormID()
	Int i = 0
	While i < FriendlySeenCount
		If FriendlySeenIds[i] == id
			Return True
		EndIf
		i += 1
	EndWhile
	Return False
EndFunction

; Children: native IsChild() is incomplete in FO4 — also require ActorTypeChild keyword.
Bool Function IsChildNpc(Actor ak)
	If !ak
		Return False
	EndIf
	If ak.IsChild()
		Return True
	EndIf
	EnsureFilterKeywords()
	If KW_ActorTypeChild && ak.HasKeyword(KW_ActorTypeChild)
		Return True
	EndIf
	Return False
EndFunction

Bool Function IsChildTargetAllowed()
	Return AllowChildFemalesOverride
EndFunction

Bool Function IsRobotTargetAllowed()
	Return AllowRobotsOverride
EndFunction

; Opt-in TargetOverrides.txt — 1/true/yes/on enable a category for notice + fixation + knife kills.
Bool Function ParseOverrideTruthy(String v)
	If !v
		Return False
	EndIf
	If v == "1" || v == "true" || v == "yes" || v == "on"
		Return True
	EndIf
	Return False
EndFunction

Function LoadTargetOverrides()
	; OPTIONAL file — missing is fine. Fail closed (both flags False = blocked).
	; Copy TargetOverrides.example.txt → TargetOverrides.txt to opt in.
	AllowChildFemalesOverride = False
	AllowRobotsOverride = False
	String fileName = "TargetOverrides.txt"
	String path = NoticeConfigPath()
	If !GardenOfEden2.DoesFileExist(fileName, path)
		LastTargetOverridesStatus = "optional file absent (defaults: blocked)"
		Debug.Trace("PickmansWhisper: TargetOverrides.txt not present — using safe defaults (see TargetOverrides.example.txt)")
		Return
	EndIf
	String[] raw = GardenOfEden2.GetLinesFromFile(fileName, path)
	If !raw || raw.Length == 0
		LastTargetOverridesStatus = "EMPTY/UNREADABLE (defaults: blocked)"
		Debug.Trace("PickmansWhisper: TargetOverrides.txt present but empty/unreadable — using safe defaults")
		Return
	EndIf
	Int i = 0
	While i < raw.Length
		String line = TrimString(raw[i])
		i += 1
		If line == ""
			; skip
		ElseIf GardenOfEden.SubStr(line, 0, 1) == "#"
			; comment
		Else
			; Scan for '=' — GoE StrFind is a count, not an index (cannot SubStr with it).
			Int eq = -1
			Int li = 0
			Int ln = GardenOfEden.StrLength(line)
			While li < ln && eq < 0
				If GardenOfEden.SubStr(line, li, 1) == "="
					eq = li
				EndIf
				li += 1
			EndWhile
			If eq > 0
				String key = TrimString(GardenOfEden.SubStr(line, 0, eq))
				String val = TrimString(GardenOfEden.SubStr(line, eq + 1, -1))
				If key == "AllowChildFemales"
					AllowChildFemalesOverride = ParseOverrideTruthy(val)
				ElseIf key == "AllowRobots"
					AllowRobotsOverride = ParseOverrideTruthy(val)
				EndIf
			EndIf
		EndIf
	EndWhile
	LastTargetOverridesStatus = "childFemales=" + (AllowChildFemalesOverride as Int) + " robots=" + (AllowRobotsOverride as Int)
	Debug.Trace("PickmansWhisper: TargetOverrides loaded | " + LastTargetOverridesStatus)
EndFunction

Bool Function IsAdultFemale(Actor ak)
	If !ak
		Return False
	EndIf
	ActorBase base = ak.GetLeveledActorBase()
	If !base
		Return False
	EndIf
	; 0 = male, 1 = female (same as Necromantic)
	If base.GetSex() != 1
		Return False
	EndIf
	; Child females only when TargetOverrides AllowChildFemales=1
	If IsChildNpc(ak) && !IsChildTargetAllowed()
		Return False
	EndIf
	Return True
EndFunction

Function ArmCombatTarget(Actor ak)
	TrackLivingNear(ak)
	If ak && !ak.IsDead()
		PendingKillVictim = ak
	EndIf
EndFunction

Function EnsureKillWatchList()
	If !KillWatchList || KillWatchList.Length == 0
		KillWatchList = new Actor[12]
		KillWatchCount = 0
	EndIf
EndFunction

Function EnsureBladeTaggedList()
	If !BladeTaggedIds || BladeTaggedIds.Length == 0
		BladeTaggedIds = new Int[24]
		BladeTaggedCount = 0
	EndIf
EndFunction

Function EnsureAliveSeenList()
	If !AliveSeenIds || AliveSeenIds.Length == 0
		AliveSeenIds = new Int[32]
		AliveSeenCount = 0
	EndIf
EndFunction

Function ClearAliveSeen()
	AliveSeenCount = 0
EndFunction

Function NoteAliveSeen(Actor ak)
	If !ak || ak.IsDead()
		Return
	EndIf
	EnsureAliveSeenList()
	Int id = ak.GetFormID()
	Int i = 0
	While i < AliveSeenCount
		If AliveSeenIds[i] == id
			Return
		EndIf
		i += 1
	EndWhile
	If AliveSeenCount >= ALIVE_SEEN_MAX
		Int j = 0
		While j < ALIVE_SEEN_MAX - 1
			AliveSeenIds[j] = AliveSeenIds[j + 1]
			j += 1
		EndWhile
		AliveSeenCount = ALIVE_SEEN_MAX - 1
	EndIf
	AliveSeenIds[AliveSeenCount] = id
	AliveSeenCount += 1
EndFunction

Bool Function WasAliveSeen(Actor ak)
	If !ak
		Return False
	EndIf
	EnsureAliveSeenList()
	Int id = ak.GetFormID()
	Int i = 0
	While i < AliveSeenCount
		If AliveSeenIds[i] == id
			Return True
		EndIf
		i += 1
	EndWhile
	Return False
EndFunction

Bool Function IsInKillWatchList(Actor ak)
	If !ak
		Return False
	EndIf
	EnsureKillWatchList()
	Int i = 0
	While i < KillWatchCount
		If KillWatchList[i] == ak
			Return True
		EndIf
		i += 1
	EndWhile
	Return False
EndFunction

Bool Function WasBladeTagged(Actor ak)
	If !ak
		Return False
	EndIf
	EnsureBladeTaggedList()
	Int id = ak.GetFormID()
	Int i = 0
	While i < BladeTaggedCount
		If BladeTaggedIds[i] == id
			Return True
		EndIf
		i += 1
	EndWhile
	Return False
EndFunction

Function TagBladeVictim(Actor ak)
	If !ak
		Return
	EndIf
	EnsureBladeTaggedList()
	Int id = ak.GetFormID()
	If WasBladeTagged(ak)
		Return
	EndIf
	If BladeTaggedCount >= BLADE_TAGGED_MAX
		Int j = 0
		While j < BLADE_TAGGED_MAX - 1
			BladeTaggedIds[j] = BladeTaggedIds[j + 1]
			j += 1
		EndWhile
		BladeTaggedCount = BLADE_TAGGED_MAX - 1
	EndIf
	BladeTaggedIds[BladeTaggedCount] = id
	BladeTaggedCount += 1
	RegisterForRemoteEvent(ak, "OnDeath")
	NoteAliveSeen(ak)
	LastKillIgnoreReason = "blade hit → tagged id=" + id
	ToastDebug("PW debug: blade HIT tagged id=" + id)
	Debug.Trace("PickmansWhisper: blade-tagged victim id=" + id)
EndFunction

Function OnPlayerCombatBegan(String path)
	; Soft backup — living scan is primary; do not clear the living track list.
	CombatGraceUntilRealTime = Utility.GetCurrentRealTime() + 10.0
	If PlayerRef
		Actor ctNow = PlayerRef.GetCombatTarget()
		If ctNow && IsBladeEquipped()
			TrackLivingNear(ctNow)
		EndIf
	EndIf
	Debug.Trace("PickmansWhisper: combat began path=" + path)
EndFunction

Function OnPlayerCombatEnded(String path)
	PollWatchedForDeath()
	Debug.Trace("PickmansWhisper: combat ended path=" + path + " livingTrack=" + KillWatchCount)
EndFunction

Function ReArmHitEventsOnWatched()
	EnsureKillWatchList()
	Int i = 0
	While i < KillWatchCount
		Actor ak = KillWatchList[i]
		If ak && !ak.IsDead()
			RegisterForHitEvent(ak, PlayerRef)
		EndIf
		i += 1
	EndWhile
EndFunction

Function ScanNearbyLivingCandidates()
	If !PlayerRef
		Return
	EndIf
	Actor[] found = GardenOfEden.FindActors(None, None, -1, -1, PlayerRef, KILL_WATCH_RADIUS, -1, 1, -1, -1, -1, -1, None, None, "", 0, 1, 1)
	If !found || found.Length == 0
		Actor[] detect = GardenOfEden2.GetActorsDetecting(PlayerRef, False)
		If detect && detect.Length > 0
			found = detect
		Else
			Return
		EndIf
	EndIf
	Int n = found.Length
	If n > 16
		n = 16
	EndIf
	Int i = 0
	While i < n
		Actor ak = found[i]
		If ak && ak != PlayerRef && !ak.IsDead()
			NoteAliveSeen(ak)
			WatchKillCandidate(ak, False)
		EndIf
		i += 1
	EndWhile
EndFunction

Function ScanNearbyDeadForKnifeKills(String path)
	If !PlayerRef
		Return
	EndIf
	; aiLifeState=0 → dead (Necromantic ScanCravingCorpses / FindNearestDeadFemale)
	Actor[] found = GardenOfEden.FindActors(None, None, -1, -1, PlayerRef, KILL_WATCH_RADIUS, 0, 1, -1, -1, -1, -1, None, None, "", 0, 1, 1)
	If !found || found.Length == 0
		Return
	EndIf
	Int n = found.Length
	If n > 16
		n = 16
	EndIf
	Bool combatGrace = Utility.GetCurrentRealTime() <= CombatGraceUntilRealTime
	Int i = 0
	While i < n
		Actor ak = found[i]
		If ak && ak != PlayerRef && ak.IsDead() && ak.Is3DLoaded() && !ak.IsDisabled()
			; Prefer people we saw alive / hit / watched. combatGrace allows short-fight misses.
			If WasAliveSeen(ak) || WasBladeTagged(ak) || IsInKillWatchList(ak) || (ak == PendingKillVictim) || combatGrace
				ToastHumanKillDetected(ak, path)
				HandlePotentialKnifeKill(ak, PlayerRef)
			EndIf
		EndIf
		i += 1
	EndWhile
EndFunction

Function PollWatchedForDeath()
	EnsureKillWatchList()
	Int i = 0
	While i < KillWatchCount
		Actor ak = KillWatchList[i]
		If ak && ak.IsDead()
			ToastHumanKillDetected(ak, "watch-poll")
			HandlePotentialKnifeKill(ak, PlayerRef)
			RemoveKillWatchAt(i)
		Else
			i += 1
		EndIf
	EndWhile
EndFunction

Function WatchKillCandidate(Actor ak, Bool abRequireValidFilter = True)
	If !ak || ak == PlayerRef
		Return
	EndIf
	If ak.IsDead()
		Return
	EndIf
	If abRequireValidFilter && !IsValidKnifeKillVictim(ak, True)
		Return
	EndIf
	NoteAliveSeen(ak)
	RegisterForHitEvent(ak, PlayerRef)
	If IsInKillWatchList(ak)
		Return
	EndIf
	EnsureKillWatchList()
	RegisterForRemoteEvent(ak, "OnDeath")
	If KillWatchCount >= KILL_WATCH_MAX
		Int j = 0
		While j < KILL_WATCH_MAX - 1
			KillWatchList[j] = KillWatchList[j + 1]
			j += 1
		EndWhile
		KillWatchCount = KILL_WATCH_MAX - 1
	EndIf
	KillWatchList[KillWatchCount] = ak
	KillWatchCount += 1
	Debug.Trace("PickmansWhisper: watching + hit-armed id=" + ak.GetFormID() + " watched=" + KillWatchCount)
EndFunction

Function HandleBladeHit(ObjectReference akTarget, ObjectReference akAggressor, Form akSource)
	Actor victim = akTarget as Actor
	Actor agg = akAggressor as Actor
	If !victim || agg != PlayerRef
		If victim && IsBladeEquipped()
			RegisterForHitEvent(victim, PlayerRef)
		EndIf
		Return
	EndIf
	Bool fromBlade = IsPickmansBladeForm(akSource) && IsBladeEquipped()
	If fromBlade
		NoteAliveSeen(victim)
		If victim.IsDead()
			TagBladeVictim(victim)
			ToastHumanKillDetected(victim, "hit-dead")
			HandlePotentialKnifeKill(victim, PlayerRef)
		Else
			TagBladeVictim(victim)
			WatchKillCandidate(victim, False)
		EndIf
	Else
		LastKillIgnoreReason = "hit not with blade; drawn=" + GetDrawnWeaponDebugName()
	EndIf
	If victim && !victim.IsDead() && IsBladeEquipped()
		RegisterForHitEvent(victim, PlayerRef)
	EndIf
EndFunction

Function ToastHumanKillDetected(Actor victim, String path)
	If !victim
		Return
	EndIf
	Int id = victim.GetFormID()
	If id == LastDeathToastId
		Return
	EndIf
	LastDeathToastId = id
	Bool human = IsHumanNpc(victim)
	If human
		ToastDebug("PW debug [" + DEBUG_BUILD + "]: HUMAN kill (" + path + ") id=" + id)
	Else
		ToastDebug("PW debug [" + DEBUG_BUILD + "]: non-human death (" + path + ") id=" + id)
	EndIf
	Debug.Trace("PickmansWhisper: death toast path=" + path + " human=" + human + " id=" + id)
EndFunction

Function EnsureFilterKeywords()
	; FormIDs verified against Fallout4.esm KYWD records.
	If !KW_ActorTypeNPC
		KW_ActorTypeNPC = Game.GetFormFromFile(0x00013794, "Fallout4.esm") as Keyword
	EndIf
	If !KW_ActorTypeHuman
		; 0x2CB72 is ActorTypeHuman — was wrongly used as Robot before (B18 and earlier).
		KW_ActorTypeHuman = Game.GetFormFromFile(0x0002CB72, "Fallout4.esm") as Keyword
	EndIf
	If !KW_ActorTypeChild
		KW_ActorTypeChild = Game.GetFormFromFile(0x001157E8, "Fallout4.esm") as Keyword
	EndIf
	If !KW_ActorTypeGhoul
		KW_ActorTypeGhoul = Game.GetFormFromFile(0x000EAFB7, "Fallout4.esm") as Keyword
	EndIf
	If !KW_ActorTypeSuperMutant
		KW_ActorTypeSuperMutant = Game.GetFormFromFile(0x0006D7B6, "Fallout4.esm") as Keyword
	EndIf
	If !KW_ActorTypeSynth
		KW_ActorTypeSynth = Game.GetFormFromFile(0x0010C3CE, "Fallout4.esm") as Keyword
	EndIf
	If !KW_ActorTypeRobot
		KW_ActorTypeRobot = Game.GetFormFromFile(0x0002CB73, "Fallout4.esm") as Keyword
	EndIf
	If !KW_ActorTypeAnimal
		KW_ActorTypeAnimal = Game.GetFormFromFile(0x00013798, "Fallout4.esm") as Keyword
	EndIf
	If !KW_ActorTypeCreature
		KW_ActorTypeCreature = Game.GetFormFromFile(0x00013795, "Fallout4.esm") as Keyword
	EndIf
	If !KW_ActorTypeTurret
		KW_ActorTypeTurret = Game.GetFormFromFile(0x000B2BF3, "Fallout4.esm") as Keyword
	EndIf
EndFunction

Bool Function IsStoryEssential(Actor ak)
	If !ak
		Return True
	EndIf
	ActorBase base = ak.GetLeveledActorBase()
	If !base
		; Don't block knife kills if base is missing on a corpse
		Return False
	EndIf
	Return base.IsEssential()
EndFunction

Bool Function IsHumanNpc(Actor ak)
	If !ak
		Return False
	EndIf
	EnsureFilterKeywords()
	; Hard exclusions first
	If KW_ActorTypeGhoul && ak.HasKeyword(KW_ActorTypeGhoul)
		Return False
	EndIf
	If KW_ActorTypeSuperMutant && ak.HasKeyword(KW_ActorTypeSuperMutant)
		Return False
	EndIf
	If KW_ActorTypeSynth && ak.HasKeyword(KW_ActorTypeSynth)
		Return False
	EndIf
	If KW_ActorTypeRobot && ak.HasKeyword(KW_ActorTypeRobot)
		; Robots normally excluded; TargetOverrides AllowRobots=1 opts them in fully.
		If IsRobotTargetAllowed()
			Return True
		EndIf
		Return False
	EndIf
	If KW_ActorTypeAnimal && ak.HasKeyword(KW_ActorTypeAnimal)
		Return False
	EndIf
	If KW_ActorTypeCreature && ak.HasKeyword(KW_ActorTypeCreature)
		Return False
	EndIf
	If KW_ActorTypeTurret && ak.HasKeyword(KW_ActorTypeTurret)
		Return False
	EndIf
	; Positive: NPC or Human (settlers/raiders/etc.)
	If KW_ActorTypeNPC && ak.HasKeyword(KW_ActorTypeNPC)
		Return True
	EndIf
	If KW_ActorTypeHuman && ak.HasKeyword(KW_ActorTypeHuman)
		Return True
	EndIf
	; Soft accept if exclude keywords loaded but no positive match yet — still reject unknown animals
	Return False
EndFunction

Bool Function IsValidKnifeKillVictim(Actor ak, Bool abRequireAlive = True)
	If !ak || ak == PlayerRef
		LastKillIgnoreReason = "no actor"
		Return False
	EndIf
	If abRequireAlive && ak.IsDead()
		LastKillIgnoreReason = "already dead"
		Return False
	EndIf
	If IsChildNpc(ak) && !IsChildTargetAllowed()
		LastKillIgnoreReason = "child"
		Return False
	EndIf
	If ak.IsPlayerTeammate()
		LastKillIgnoreReason = "teammate"
		Return False
	EndIf
	If IsStoryEssential(ak)
		LastKillIgnoreReason = "essential (story NPC)"
		Return False
	EndIf
	If !IsHumanNpc(ak)
		LastKillIgnoreReason = "not human NPC"
		Return False
	EndIf
	If !IsAdultFemale(ak)
		LastKillIgnoreReason = "not adult female"
		Return False
	EndIf
	; Must have been seen non-hostile while alive (raiders fail; settlers you aggro still pass).
	If !WasFriendlySeen(ak)
		LastKillIgnoreReason = "hostile / not seen friendly"
		Return False
	EndIf
	Return True
EndFunction

Function HandlePotentialKnifeKill(Actor victim, Actor akKiller)
	If !victim
		Return
	EndIf
	Int vid = victim.GetFormID()
	If vid == LastHandledKillId
		Return
	EndIf
	If akKiller && akKiller != PlayerRef
		LastKillIgnoreReason = "killer was not player"
		ToastDebug("PW debug: kill ignored — not player killer")
		Debug.Trace("PickmansWhisper: kill ignored — killer not player")
		Return
	EndIf
	; Drawn weapon must be Pickman's Blade right now. No finish window, no hit-tag waiver.
	String drawn = GetDrawnWeaponDebugName()
	If !IsBladeEquipped()
		LastKillIgnoreReason = "not blade; drawn=" + drawn
		ToastDebug("PW debug: kill ignored — " + LastKillIgnoreReason)
		Return
	EndIf
	Bool tagged = WasBladeTagged(victim)
	Bool seenAlive = IsInKillWatchList(victim) || (victim == PendingKillVictim) || WasAliveSeen(victim)
	If !tagged && !seenAlive
		LastKillIgnoreReason = "blade out but victim not linked; drawn=" + drawn
		ToastDebug("PW debug: kill ignored — " + LastKillIgnoreReason)
		Debug.Trace("PickmansWhisper: kill ignored — no blade-link id=" + vid)
		Return
	EndIf
	Float now = Utility.GetCurrentRealTime()
	If (now - LastKnifeKillRealTime) < KNIFE_KILL_COOLDOWN
		LastKillIgnoreReason = "cooldown"
		Return
	EndIf
	If !IsValidKnifeKillVictim(victim, False)
		ToastDebug("PW debug: kill ignored — " + LastKillIgnoreReason)
		Debug.Trace("PickmansWhisper: kill ignored — " + LastKillIgnoreReason + " id=" + vid)
		Return
	EndIf
	LastKnifeKillRealTime = now
	LastHandledKillId = vid
	LastKillIgnoreReason = "ok satiated; drawn=" + drawn
	If !BondStarted
		StartBond("knife-kill")
	EndIf
	ProcessKnifeKill(victim)
EndFunction

Function ProcessKnifeKill(Actor victim)
	; Final gate — never praise/sate unless blade is still the drawn weapon
	If !IsBladeEquipped()
		LastKillIgnoreReason = "abort satiate; drawn=" + GetDrawnWeaponDebugName()
		ToastDebug("PW debug: " + LastKillIgnoreReason)
		Return
	EndIf
	KnifeKillCount += 1
	NoteKnifeActivity()
	; E1 named-victim kill voice — satiation path unchanged; voice branch only.
	If !MaybeSpeakNamedKillVoice(victim)
		String line = PickPraiseLine()
		ToastPraiseLine(line)
	EndIf
	SatiateHunger()
	RefreshHungerPanel(False)
	RefreshDebugStatus()
	Int vid = 0
	If victim
		vid = victim.GetFormID()
	EndIf
	Debug.Trace("PickmansWhisper: knife kill #" + KnifeKillCount + " victim=" + vid + " hunger=0 drawn=" + GetDrawnWeaponDebugName())
	Debug.Notification("Pickman's Whisper: hunger sated")
EndFunction

; True if named-kill ModConfig voice handled this kill (skip generic praise).
; Missing namedKillToast → False (fall back). Key set but xwm/SNDR missing → fail loud.
Bool Function MaybeSpeakNamedKillVoice(Actor victim)
	If !victim
		Return False
	EndIf
	String overrideName = GetVictimOverrideName(victim)
	If !overrideName
		Return False
	EndIf
	If !NamedKillToast
		Return False
	EndIf
	If !IsVoiceEnabled()
		Return True
	EndIf
	If !IsVoiceWeaponReady()
		Return True
	EndIf
	String line = ApplyNamePlaceholder(NamedKillToast, overrideName)
	If !line || GardenOfEden.StrLength(line) < 1
		Return False
	EndIf
	Float now = Utility.GetCurrentRealTime()
	If (now - LastPraiseToastRealTime) < PRAISE_TOAST_COOLDOWN
		Return True
	EndIf
	LastPraiseToastRealTime = now
	Int mode = GetVoiceDeliveryMode()
	If mode != 1
		ShowVoiceToast(line)
	EndIf
	If mode != 2
		If NamedKillAudio
			PlayWhisperXwmByFile(NamedKillAudio)
		ElseIf mode == 1
			; Audio-only with no audio key — still deliver toast so the kill is not silent.
			ShowVoiceToast(line)
			Debug.Trace("PickmansWhisper: namedKillAudio missing — toast fallback for audio-only mode")
		EndIf
	EndIf
	Debug.Trace("PickmansWhisper: named kill voice | " + line)
	Return True
EndFunction

; Call after a valid knife kill (or MCM debug). Clears meter + sated window.
Function SatiateHunger()
	Float now = Utility.GetCurrentGameTime()
	LastKnifeActivityGameTime = now
	LastHungerPollGameTime = now
	HungerLevel = 0.0
	LastHungerBand = 0
	SatedUntilGameTime = now + (GetHungerSatedHours() / 24.0)
	HungerWasSated = True
	BondIntensity = BondIntensity + 1.0
	SyncHungerAddictionSpell()
	RefreshHungerPanel(False)
	Debug.Trace("PickmansWhisper: hunger satiated until " + SatedUntilGameTime)
EndFunction

Function NoteKnifeActivity()
	LastKnifeActivityGameTime = Utility.GetCurrentGameTime()
	Debug.Trace("PickmansWhisper: knife activity noted")
EndFunction

String Function FormatSpecialSnapshot()
	If !PlayerRef
		Return "AGI=? CHA=?"
	EndIf
	ActorValue avAgi = Game.GetForm(0x000002C7) as ActorValue
	ActorValue avCha = Game.GetForm(0x000002C5) as ActorValue
	Float agi = -1.0
	Float cha = -1.0
	If avAgi
		agi = PlayerRef.GetValue(avAgi)
	EndIf
	If avCha
		cha = PlayerRef.GetValue(avCha)
	EndIf
	Return "AGI=" + (agi as Int) + " CHA=" + (cha as Int)
EndFunction

Function ApplyHungerStatPenalty()
	If !PlayerRef || HungerStatPenaltyApplied
		Return
	EndIf
	ActorValue avAgi = Game.GetForm(0x000002C7) as ActorValue
	ActorValue avCha = Game.GetForm(0x000002C5) as ActorValue
	If !avAgi
		avAgi = Game.GetFormFromFile(0x000002C7, "Fallout4.esm") as ActorValue
	EndIf
	If !avCha
		avCha = Game.GetFormFromFile(0x000002C5, "Fallout4.esm") as ActorValue
	EndIf
	If avAgi
		PlayerRef.ModValue(avAgi, -1.0)
	EndIf
	If avCha
		PlayerRef.ModValue(avCha, -1.0)
	EndIf
	HungerStatPenaltyApplied = True
	Debug.Trace("PickmansWhisper: SPECIAL -1 applied " + FormatSpecialSnapshot())
EndFunction

Function ClearHungerStatPenalty()
	If !PlayerRef || !HungerStatPenaltyApplied
		Return
	EndIf
	ActorValue avAgi = Game.GetForm(0x000002C7) as ActorValue
	ActorValue avCha = Game.GetForm(0x000002C5) as ActorValue
	If !avAgi
		avAgi = Game.GetFormFromFile(0x000002C7, "Fallout4.esm") as ActorValue
	EndIf
	If !avCha
		avCha = Game.GetFormFromFile(0x000002C5, "Fallout4.esm") as ActorValue
	EndIf
	If avAgi
		PlayerRef.ModValue(avAgi, 1.0)
	EndIf
	If avCha
		PlayerRef.ModValue(avCha, 1.0)
	EndIf
	HungerStatPenaltyApplied = False
	Debug.Trace("PickmansWhisper: SPECIAL +1 restored " + FormatSpecialSnapshot())
EndFunction

Bool Function ApplyHungerAddictionStandIn(Bool abAnnounce)
	If !PlayerRef
		Return False
	EndIf
	EnsureHungerSpell()
	If KnifeHungerSpell && PlayerRef.HasSpell(KnifeHungerSpell)
		PlayerRef.DispelSpell(KnifeHungerSpell)
		PlayerRef.RemoveSpell(KnifeHungerSpell)
	EndIf
	If KnifeHungerGlobal
		KnifeHungerGlobal.SetValue(0.0)
	EndIf
	If !HungerStatPenaltyApplied
		ApplyHungerStatPenalty()
	EndIf
	If HungerStatPenaltyApplied && abAnnounce
		Debug.Notification("Pickman's Whisper: knife hunger withdrawal AGI/CHA -1")
	EndIf
	Return HungerStatPenaltyApplied
EndFunction

Function ClearHungerAddictionStandIn()
	If !PlayerRef
		Return
	EndIf
	EnsureHungerSpell()
	If KnifeHungerSpell
		PlayerRef.DispelSpell(KnifeHungerSpell)
		If PlayerRef.HasSpell(KnifeHungerSpell)
			PlayerRef.RemoveSpell(KnifeHungerSpell)
		EndIf
	EndIf
	If KnifeHungerGlobal
		KnifeHungerGlobal.SetValue(0.0)
	EndIf
	ClearHungerStatPenalty()
EndFunction

Function SyncHungerAddictionSpell()
	EnsureHungerSpell()
	If !PlayerRef
		Return
	EndIf
	Bool want = IsHungerUnlocked() && IsHungerAddictionSpellEnabled() && HungerLevel >= GetHungerAddictedThreshold() && !IsHungerSated()
	If want
		If !HungerStatPenaltyApplied
			ApplyHungerAddictionStandIn(!HungerAddictionApplied)
		EndIf
		HungerAddictionApplied = HungerStatPenaltyApplied
	ElseIf HungerStatPenaltyApplied || HungerAddictionApplied
		ClearHungerAddictionStandIn()
		HungerAddictionApplied = False
		Debug.Trace("PickmansWhisper: hunger withdrawal cleared")
	EndIf
EndFunction

; --- MCM -----------------------------------------------------------------------

Function OnMCMMenuOpen(String modName)
	If modName != MOD_NAME
		Return
	EndIf
	; RefreshMenu FIRST (it reloads page state from settings.ini), THEN reload
	; notice files and push status — same order as Necromantic. Loading before
	; RefreshMenu was getting wiped back to settings.ini "(not loaded)".
	EnsurePlayerCombatQuest()
	ArmRuntimeLoops() ; recovery if load hooks missed; not the sole arm path
	RefreshHungerPanel(False)
	If MCM.IsInstalled()
		MCM.RefreshMenu()
	EndIf
	LoadNoticeLines()
	RefreshDebugStatus()
	RefreshVictimsPanel(False)
EndFunction

Function OnMCMSettingChange(String modName, String id)
	If modName != MOD_NAME
		Return
	EndIf
	If id == "bKillDebugToasts:Debug"
		InvalidateDebugToastCache()
	ElseIf id == "bAddictionSpell:Hunger" || id == "fAddictedAt:Hunger"
		SyncHungerAddictionSpell()
		RefreshHungerPanel(True)
	ElseIf id == "bVoiceToasts:Voice"
		ArmRuntimeLoops()
	EndIf
EndFunction

Function RefreshHungerPanel(Bool refreshMenu = True)
	If !MCM.IsInstalled()
		Return
	EndIf
	If !IsHungerUnlocked()
		MCM.SetModSettingString(MOD_NAME, "sHungerLevel:Hunger", "locked (visit gallery or take the blade)")
		MCM.SetModSettingString(MOD_NAME, "sHungerSated:Hunger", "—")
		MCM.SetModSettingString(MOD_NAME, "sBondState:Hunger", "not bonded")
	Else
		Int lvl = HungerLevel as Int
		String band = GetHungerBandLabel(HungerLevel)
		MCM.SetModSettingString(MOD_NAME, "sHungerLevel:Hunger", lvl + " / 100 (" + band + ")")
		If IsHungerSated()
			Float left = (SatedUntilGameTime - Utility.GetCurrentGameTime()) * 24.0
			If left < 0.0
				left = 0.0
			EndIf
			MCM.SetModSettingString(MOD_NAME, "sHungerSated:Hunger", "yes (" + (left as Int) + "h left)")
		Else
			MCM.SetModSettingString(MOD_NAME, "sHungerSated:Hunger", "no — kill with Pickman's Blade")
		EndIf
		MCM.SetModSettingString(MOD_NAME, "sBondState:Hunger", "bonded | intensity " + (BondIntensity as Int) + " | kills " + KnifeKillCount)
	EndIf
	If refreshMenu
		MCM.RefreshMenu()
	EndIf
EndFunction

Function ShowHungerInfo()
	RefreshHungerPanel(True)
	String msg = "Pickman's Whisper — Hunger\n\n"
	If !IsHungerUnlocked()
		msg += "Not bonded yet.\nEnter Pickman Gallery or obtain Pickman's Blade.\n"
		Debug.MessageBox(msg)
		Return
	EndIf
	msg += "Level: " + (HungerLevel as Int) + " / 100 (" + GetHungerBandLabel(HungerLevel) + ")\n"
	If IsHungerSated()
		Float left = (SatedUntilGameTime - Utility.GetCurrentGameTime()) * 24.0
		msg += "Sated: yes (" + (left as Int) + "h left)\n"
	Else
		msg += "Sated: no\n"
	EndIf
	msg += "Bond intensity: " + (BondIntensity as Int) + "\n"
	msg += "Knife kills (sating): " + KnifeKillCount + "\n"
	msg += "Addicted at: " + (GetHungerAddictedThreshold() as Int) + "\n"
	msg += "Withdrawal flag: " + HungerStatPenaltyApplied + "\n"
	msg += "SPECIAL now: " + FormatSpecialSnapshot() + "\n"
	msg += "\nRises with unused knife-time after bonding.\n"
	msg += "Killing a non-essential human with Pickman's Blade sates hunger."
	Debug.MessageBox(msg)
EndFunction

Function ForceHungerAddictedTest()
	If !IsHungerUnlocked()
		Debug.MessageBox("Pickman's Whisper — Test\n\nBond first (gallery or blade).")
		Return
	EndIf
	If !IsHungerAddictionSpellEnabled()
		Debug.MessageBox("Pickman's Whisper — Test\n\nKnife Hunger effect is OFF in MCM.")
		Return
	EndIf
	If HungerStatPenaltyApplied
		ClearHungerAddictionStandIn()
	EndIf
	SatedUntilGameTime = 0.0
	HungerWasSated = False
	HungerLevel = 80.0
	LastHungerBand = 70
	HungerAddictionApplied = False
	String before = FormatSpecialSnapshot()
	SyncHungerAddictionSpell()
	RefreshHungerPanel(True)
	String msg = "Hunger forced to 80.\nBefore: " + before + "\nAfter: " + FormatSpecialSnapshot() + "\n"
	msg += "Withdrawal flag: " + HungerStatPenaltyApplied
	Debug.MessageBox("Pickman's Whisper — Test\n\n" + msg)
EndFunction

Function DebugForceBond()
	StartBond("mcm-debug")
	RefreshDebugStatus()
	Debug.MessageBox("Pickman's Whisper\n\nBond forced. Hunger unlocked.")
EndFunction

; D0-POC — play golden EndIt SNDR (no notice/audio-map wiring yet).
; MessageBox reports form resolve, loose xwm presence, and Play instance id (0 = failed).
Function DebugPlayTestWhisper()
	String nl = "\n"
	String msg = "Pickman's Whisper — Play test whisper [" + DEBUG_BUILD + "]" + nl + nl
	If !PlayerRef
		PlayerRef = Game.GetPlayer()
	EndIf
	If !PlayerRef
		msg += "FAIL: PlayerRef missing"
		Debug.Trace("PickmansWhisper: ERROR DebugPlayTestWhisper — PlayerRef missing")
		Debug.Notification("Pickman's Whisper: Play test whisper — no player")
		Debug.MessageBox(msg)
		Return
	EndIf
	msg += "FID 0x00000807 / PW_Whisper_EndIt" + nl
	msg += "SNDR path: Sound\\PickmansWhisper\\EndIt.xwm" + nl
	; GoE path is FO4-root relative (same pattern as NoticeConfigPath).
	Bool xwmOk = GardenOfEden2.DoesFileExist("EndIt.xwm", ".\\Data\\Sound\\PickmansWhisper\\")
	msg += "loose xwm exists=" + xwmOk + nl
	If !xwmOk
		msg += "HINT: deploy Data\\Sound\\PickmansWhisper\\EndIt.xwm into MO2 mod" + nl
	EndIf
	Form f = Game.GetFormFromFile(FID_WHISPER_ENDIT, "PickmansWhisper.esp")
	msg += "GetFormFromFile ok=" + (f != None) + nl
	Sound snd = f as Sound
	msg += "cast Sound ok=" + (snd != None) + nl
	If !snd
		msg += nl + "FAIL: SNDR missing — update/rebuild ESP"
		Debug.Trace("PickmansWhisper: ERROR DebugPlayTestWhisper — GetFormFromFile 0x00000807 failed")
		Debug.Notification("Pickman's Whisper: PW_Whisper_EndIt SNDR missing (0x807)")
		Debug.MessageBox(msg)
		Return
	EndIf
	; Play returns instance id; 0 means the engine refused / failed to start.
	Int inst = snd.Play(PlayerRef)
	msg += "Sound.Play instanceId=" + inst + nl
	If inst == 0
		msg += nl + "FAIL: Play returned 0 (silent). Check xwm path, category mute, or 3D."
		Debug.Trace("PickmansWhisper: ERROR DebugPlayTestWhisper Play instance=0 xwmExists=" + xwmOk)
		Debug.Notification("Pickman's Whisper: EndIt Play failed (instance 0)")
	Else
		msg += nl + "OK: Play started (listen for clip)."
		Debug.Trace("PickmansWhisper: DebugPlayTestWhisper Play instance=" + inst + " xwmExists=" + xwmOk)
		Debug.Notification("Pickman's Whisper: EndIt Play instance=" + inst)
	EndIf
	Debug.MessageBox(msg)
EndFunction

; Regression helper — confirm GoE sees Pickman's drawn without needing a kill.
Function DebugVerifyBladeDetect()
	If !PlayerRef
		PlayerRef = Game.GetPlayer()
	EndIf
	ResolveVanillaForms()
	Weapon w = None
	String baseName = "(none)"
	If PlayerRef
		w = PlayerRef.GetEquippedWeapon(0)
		If w
			baseName = w.GetName()
		EndIf
	EndIf
	Int idx = FindEquippedPickmansBladeIndex()
	Bool drawn = IsBladeEquipped()
	Bool owns = PlayerOwnsPickmansBladeInstance() || OwnedPickmansBlade || HasTemplateBlade()
	String goeName = "(not found)"
	If idx >= 0
		goeName = GardenOfEden.GetNthItemName(PlayerRef, idx)
	EndIf
	String verdict = "FAIL — not drawn"
	If drawn
		verdict = "PASS — Pickman's Blade DRAWN"
	EndIf
	String msg = "Pickman's Whisper [" + DEBUG_BUILD + "]\n\n"
	msg += verdict + "\n\n"
	msg += "GetEquippedWeapon: " + baseName + "\n"
	msg += "GoE equipped name: " + goeName + "\n"
	msg += "GoE slot index: " + idx + "\n"
	msg += "Owns Pickman's instance: " + owns + "\n"
	msg += "CombatKnife form: " + (CombatKnifeBase != None) + "\n"
	msg += "OMOD bleed+stealth loaded: " + (OmodBleed != None && OmodStealthBlade != None) + "\n\n"
	msg += "Gun with blade in inv must FAIL.\nBlade drawn must PASS."
	RefreshDebugStatus()
	Debug.MessageBox(msg)
EndFunction

Function DebugSatiateHunger()
	If !IsHungerUnlocked()
		Debug.MessageBox("Pickman's Whisper\n\nBond first.")
		Return
	EndIf
	String line = PickPraiseLine()
	ToastPraiseLine(line)
	SatiateHunger()
	RefreshHungerPanel(True)
	Debug.MessageBox("Pickman's Whisper\n\nHunger satiated (debug — no kill required).\n" + line)
EndFunction

Function DebugReloadLines()
	LoadLineBanks()
	Debug.MessageBox("Pickman's Whisper — reloaded line banks\n\nTrust (builtin): " + TrustLineCount + "\nHunger (builtin): " + HungerLineCount + "\nPraise (builtin): " + PraiseLineCount + "\n\nNotice stages (files-only):\ncalm: " + NoticeCalmStatus + "\nrestless: " + NoticeRestlessStatus + "\nhungry: " + NoticeHungryStatus + "\nstarving: " + NoticeStarvingStatus + "\ndesperate: " + NoticeDesperateStatus)
EndFunction

; MCM Debug button — reload all five notice files NOW and show the full
; step-by-step load trace MessageBox (mirrors Necromantic ShowConfigLoadInfo).
Function DebugTestNoticeFiles()
	LoadNoticeLines()
	String failed = NoticeLoadFailureList()
	If failed != ""
		Debug.Notification("Pickman's Whisper: NO/partial notice load — " + failed)
	Else
		Debug.Notification("Pickman's Whisper: notice files OK at " + NoticeConfigPath())
	EndIf
	ReportNoticeLoadStatus()
EndFunction

Function DebugTestPraiseLine()
	String line = PickPraiseLine()
	ToastPraiseLine(line)
	If Utility.IsInMenuMode()
		Debug.MessageBox("Pickman's Whisper\n\n" + line)
	EndIf
EndFunction

Function DebugTestTrustLine()
	String line = PickTrustLine()
	ToastVoice(line)
	If Utility.IsInMenuMode()
		Debug.MessageBox("Pickman's Whisper\n\n" + line)
	EndIf
EndFunction

Function DebugTestNoticeLine()
	If !PlayerRef
		PlayerRef = Game.GetPlayer()
	EndIf
	If !BondStarted
		Debug.MessageBox("Pickman's Whisper — Notice\n\nBond first (gallery or blade).")
		Return
	EndIf
	If !IsVoiceEnabled()
		Debug.MessageBox("Pickman's Whisper — Notice\n\nEnable toast voice on the Voice page.")
		Return
	EndIf
	; Diagnostics: raw GoE counts before filters
	Actor[] fem = GardenOfEden.FindActors(None, None, -1, -1, PlayerRef, KILL_WATCH_RADIUS, 1, 1, -1, 1, -1, -1, None, None, "", 0, 1, 1)
	Actor[] anyA = GardenOfEden.FindActors(None, None, -1, -1, PlayerRef, KILL_WATCH_RADIUS, 1, -1, -1, -1, -1, -1, None, None, "", 0, 1, 0)
	Int nFem = 0
	Int nAny = 0
	If fem
		nFem = fem.Length
	EndIf
	If anyA
		nAny = anyA.Length
	EndIf
	Actor target = PickNoticeTarget()
	If !target
		Debug.MessageBox("Pickman's Whisper — Notice [" + DEBUG_BUILD + "]\n\nNo candidate.\nGoE female loaded: " + nFem + "\nGoE any living: " + nAny + "\nKillWatch: " + KillWatchCount + "\nRadius: " + (KILL_WATCH_RADIUS as Int) + "\nNeed adult female, not hostile, not essential.")
		Return
	EndIf
	String npcName = GetActorDisplayName(target)
	String who = npcName
	If who == ""
		who = "id=" + target.GetFormID()
	EndIf
	Int stage = GetNoticeStage()
	Int mode = GetVoiceDeliveryMode()
	If mode == 1
		Int aIdx = PickNoticeAudioIndex(stage)
		If aIdx < 0
			Debug.MessageBox("Pickman's Whisper — Notice [" + DEBUG_BUILD + "]\n\nTarget: " + who + "\n\nAudio-only: no map for stage " + (stage + 1) + " (" + GetNoticeStageName(stage) + ").")
			Return
		EndIf
		PlayNoticeAudio(stage, aIdx)
		MarkNoticeCooldown(target)
		Debug.MessageBox("Pickman's Whisper — Notice [" + DEBUG_BUILD + "]\n\nTarget: " + who + "\nMode: Audio only\nIndex: " + aIdx)
		Return
	EndIf
	String line = PickNoticeLine(npcName)
	If line == ""
		Debug.MessageBox("Pickman's Whisper — Notice [" + DEBUG_BUILD + "]\n\nTarget: " + who + "\n\nNo whisper: stage " + (stage + 1) + " (" + GetNoticeStageName(stage) + ") file not loaded.\ncalm: " + NoticeCalmStatus + "\nrestless: " + NoticeRestlessStatus + "\nhungry: " + NoticeHungryStatus + "\nstarving: " + NoticeStarvingStatus + "\ndesperate: " + NoticeDesperateStatus)
		Return
	EndIf
	MarkNoticeCooldown(target)
	ToastNoticeLine(line)
	If mode == 0
		PlayNoticeAudio(stage, LastNoticePickIndex)
	EndIf
	Debug.MessageBox("Pickman's Whisper — Notice [" + DEBUG_BUILD + "]\n\nTarget: " + who + "\nGoE female: " + nFem + " any: " + nAny + "\nMode: " + mode + " idx: " + LastNoticePickIndex + "\n\n" + line)
EndFunction

; Unfiltered proximity probe — prove GoE/Detecting see anyone before notice filters.
; Mirrors Necromantic witness distance idea (GetActorsDetecting) + kill-scan FindActors living.
Function DebugScanNearbyNpcs()
	DEBUG_BUILD = "C2-stable"
	If !PlayerRef
		PlayerRef = Game.GetPlayer()
	EndIf
	If !PlayerRef
		Debug.MessageBox("C2-polldbg\n\nNo player ref.")
		Return
	EndIf
	; Manual button = non-destructive PROBE. Also re-arms loops (same as load) so a
	; stuck timer is recoverable — but load/OnInit must arm without this button.
	ArmRuntimeLoops()
	; Clear cools, toast, then leave the passive path un-throttled: do not arm
	; any notice cooldown here. (Old button re-stamped the per-NPC cooldown.)
	NoticeCoolCount = 0
	LastNoticeToastRealTime = 0.0
	Actor target = PickNoticeTarget()
	String body = "Manual scan (button)\n\n" + LastNoticeDiag
	If target
		String nm = GetActorDisplayName(target)
		String line = PickNoticeLine(nm)
		If line == ""
			; Files-only: stage file didn't load — surface it, don't fake a line.
			LastNoticeStatus = "skip: stage " + (GetNoticeStage() + 1) + " (" + GetNoticeStageName(GetNoticeStage()) + ") not loaded"
			WriteNoticeStatusToMcm()
			WriteNearbyStatusToMcm()
			body += "\n\nNO LINE — stage " + (GetNoticeStage() + 1) + " (" + GetNoticeStageName(GetNoticeStage()) + ") file not loaded. See Debug rows."
		Else
			ToastNoticeLine(line)
			LastNoticeToastRealTime = 0.0 ; probe must not arm the global cooldown
			LastNoticeStatus = "ok: manual scan (probe)"
			WriteNoticeStatusToMcm()
			WriteNearbyStatusToMcm()
			body += "\n\nTOASTED: " + line
		EndIf
	Else
		WriteNearbyStatusToMcm()
		body += "\n\nNo toast target"
	EndIf
	Debug.MessageBox("PW [" + DEBUG_BUILD + "]\n\n" + body)
EndFunction

Function RefreshDebugStatus()
	; Status snapshot for MCM. Must NOT StartBond / nest CallFunction.
	; Reloads notice files so "Refresh status" actually re-reads the .txt banks
	; (previously it only re-displayed stale in-memory "(not loaded)" defaults).
	If RefreshDebugBusy
		Return
	EndIf
	RefreshDebugBusy = True

	If !PlayerRef
		PlayerRef = Game.GetPlayer()
	EndIf

	If !MCM.IsInstalled()
		RefreshDebugBusy = False
		ToastDebug("PW debug refresh: MCM missing")
		Return
	EndIf
	InvalidateDebugToastCache()

	; Load BEFORE writing MCM rows so the five file statuses are live.
	LoadNoticeLines()

	Bool allOk = True
	Int f4seRel = F4SE.GetVersionRelease()
	If f4seRel > 0
		MCM.SetModSettingString(MOD_NAME, "sF4SE:Debug", "OK (release " + f4seRel + ")")
	Else
		MCM.SetModSettingString(MOD_NAME, "sF4SE:Debug", "MISSING")
		allOk = False
	EndIf
	MCM.SetModSettingString(MOD_NAME, "sMCM:Debug", "OK")

	ResolveVanillaForms()
	; Do NOT call RefreshBladeOwnershipFromEquip here — it can StartBond and nest MCM calls
	; (closes MCM / soft-crashes CallFunction). Ownership is updated by equip events.
	If PickmansBlade
		MCM.SetModSettingString(MOD_NAME, "sBlade:Debug", "OK template loaded")
	Else
		MCM.SetModSettingString(MOD_NAME, "sBlade:Debug", "MISSING template")
		allOk = False
	EndIf
	String eqName = GetEquippedWeaponName()
	If eqName == ""
		eqName = "(none)"
	EndIf
	Weapon eqW = None
	If PlayerRef
		eqW = PlayerRef.GetEquippedWeapon(0)
	EndIf
	String eqId = "(no weap)"
	If eqW
		eqId = GardenOfEden.GetHexFormID(eqW)
	EndIf
	If PlayerHasBlade()
		String how = ""
		If OwnedPickmansBlade
			how = "owned(name)"
		EndIf
		If HasTemplateBlade()
			If how != ""
				how = how + "+"
			EndIf
			how = how + "template"
		EndIf
		If how == ""
			how = "yes"
		EndIf
		MCM.SetModSettingString(MOD_NAME, "sBladeInv:Debug", how)
	Else
		MCM.SetModSettingString(MOD_NAME, "sBladeInv:Debug", "not owned | eq=" + eqName)
	EndIf
	If IsBladeEquipped()
		Int idx = FindEquippedPickmansBladeIndex()
		String goeName = eqName
		If idx >= 0
			goeName = GardenOfEden.GetNthItemName(PlayerRef, idx)
		EndIf
		MCM.SetModSettingString(MOD_NAME, "sBladeEq:Debug", "DRAWN | " + goeName + " / base=" + eqName + " " + eqId)
	Else
		MCM.SetModSettingString(MOD_NAME, "sBladeEq:Debug", "not drawn | base=" + eqName + " " + eqId)
	EndIf
	If IsPlayerInGallery()
		MCM.SetModSettingString(MOD_NAME, "sCell:Debug", "Pickman Gallery")
	ElseIf PlayerRef && PlayerRef.GetParentCell()
		MCM.SetModSettingString(MOD_NAME, "sCell:Debug", "other cell")
	Else
		MCM.SetModSettingString(MOD_NAME, "sCell:Debug", "unknown")
	EndIf
	If BondStarted
		MCM.SetModSettingString(MOD_NAME, "sBond:Debug", "bonded | kills " + KnifeKillCount)
	Else
		MCM.SetModSettingString(MOD_NAME, "sBond:Debug", "not bonded")
	EndIf
	If LastKillIgnoreReason == ""
		MCM.SetModSettingString(MOD_NAME, "sLastKill:Debug", "(none yet)")
	Else
		MCM.SetModSettingString(MOD_NAME, "sLastKill:Debug", LastKillIgnoreReason)
	EndIf

	String aliasStatus = EnsureCombatKillHooks()
	MCM.SetModSettingString(MOD_NAME, "sWatch:Debug", "watch " + KillWatchCount + " | " + aliasStatus)

	Int noticeStage = GetNoticeStage()
	String stageSrc = "auto"
	If IsNoticeStageForced()
		stageSrc = "forced"
	Else
		; Reflect the live (hunger-derived) stage in the dropdown so it reads as a
		; status display when not forcing. When forcing, leave the user's choice.
		MCM.SetModSettingInt(MOD_NAME, "iNoticeStage:Debug", noticeStage)
	EndIf
	String stageInfo = "stage " + (noticeStage + 1) + "/5 " + GetNoticeStageName(noticeStage) + " (" + stageSrc + ", " + GetNoticeCountForStage(noticeStage) + " lines)"
	If LastNoticeStatus == ""
		MCM.SetModSettingString(MOD_NAME, "sNotice:Debug", "(none yet) | " + stageInfo)
	Else
		MCM.SetModSettingString(MOD_NAME, "sNotice:Debug", LastNoticeStatus + " | " + stageInfo)
	EndIf
	WriteFixationStatusToMcm()
	WriteNoticeLoadStatusToMcm()
	WriteNearbyStatusToMcm()

	EnsureHungerSpell()
	If KnifeHungerSpell
		MCM.SetModSettingString(MOD_NAME, "sHungerSpell:Debug", "OK")
	Else
		MCM.SetModSettingString(MOD_NAME, "sHungerSpell:Debug", "MISSING SPEL")
		allOk = False
	EndIf
	If allOk
		MCM.SetModSettingString(MOD_NAME, "sOverall:Debug", "OK [" + DEBUG_BUILD + "]")
	Else
		MCM.SetModSettingString(MOD_NAME, "sOverall:Debug", "Issues - see rows")
	EndIf

	; RefreshMenu can re-read settings.ini and wipe SetModSettingString values
	; (our shipped defaults were "(not loaded)"). Re-push the live load rows AFTER
	; the menu refresh so the Debug page shows the real result.
	MCM.RefreshMenu()
	WriteNoticeLoadStatusToMcm()
	WriteNearbyStatusToMcm()
	If LastNoticeStatus == ""
		MCM.SetModSettingString(MOD_NAME, "sNotice:Debug", "(none yet) | " + stageInfo)
	Else
		MCM.SetModSettingString(MOD_NAME, "sNotice:Debug", LastNoticeStatus + " | " + stageInfo)
	EndIf
	RefreshDebugBusy = False
	ToastDebug("PW debug refreshed [" + DEBUG_BUILD + "]")
	Debug.Trace("PickmansWhisper: RefreshDebugStatus done " + DEBUG_BUILD)
EndFunction
