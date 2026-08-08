Scriptname PickmansWhisperMainQuestScript extends Quest

; Pickman's Whisper — Slice A+B: gallery/blade bond, toast voice, knife hunger, kill satiation.
; Soft companion to Necromantic (no AAF, no compile coupling). Soft deps: F4SE, MCM.

Actor Property PlayerRef Auto ; Property so VoiceAlias can read (voice banks moved)
Form PickmansBlade ; LVLI CustomItem template 0x22595F — not the drawn WEAP
Weapon CombatKnifeBase ; WEAP Knife 0x913CA — what GetEquippedWeapon returns for Pickman's
ObjectMod OmodBleed ; mod_Legendary_Weapon_Bleed 0x1E7C20
ObjectMod OmodStealthBlade ; mod_melee_Knife_SerratedStealth 0x187A10
Cell PickmanGalleryCell
; Slice H P4 — Cannibal perk ranks (Fallout4.esm grants each rank as its own PERK record;
; ranked perks are additive, so check all three rather than assume rank order).
Perk CannibalPerk1
Perk CannibalPerk2
Perk CannibalPerk3
; Slice H P5 — RestoreHealthGeneric is the shared/generic heal MGEF the vanilla
; PerkCannibalHeal spell applies (verified against Fallout4.esm; also used by Stimpaks
; etc., so it is NOT cannibal-exclusive on its own — see MaybeRewardEatenRipeCorpse).
MagicEffect RestoreHealthGenericEffect
; P5 discovery only — MCM Debug "Sniff magic effects". See SyncMagicEffectSniffer.
Bool DebugSniffMagicEffects = False

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

; Human / safety filters (Fallout4.esm keywords) — Property so VoiceAlias checklist can read
Keyword Property KW_ActorTypeNPC Auto
Keyword Property KW_ActorTypeHuman Auto
Keyword Property KW_ActorTypeChild Auto ; 0x1157E8 — IsChild() alone misses many settlement kids
Keyword Property KW_ActorTypeGhoul Auto
Keyword Property KW_ActorTypeSuperMutant Auto
Keyword Property KW_ActorTypeSynth Auto
Keyword Property KW_ActorTypeRobot Auto
Keyword Property KW_ActorTypeAnimal Auto
Keyword Property KW_ActorTypeCreature Auto
Keyword Property KW_ActorTypeTurret Auto

; Blade-tagged victims — a confirmed player+blade hit registers OnDeath and adds here;
; cleared (with UnregisterForRemoteEvent) the moment their death is processed, or by the
; periodic reconcile sweep if they wander off / never die. This is the ONLY tracking list
; the kill-credit path needs — eligibility is decided live at OnDeath (IsBladeEquipped +
; killer==player + IsValidTarget), not by whether ambient scanning happened to notice them.
Actor[] BladeTagged
Int Property BladeTaggedCount = 0 Auto
Int BLADE_TAGGED_MAX = 24
; Hit-watching dedup — TrackLivingNear runs every nearby actor every KillerScan tick;
; without this, RegisterForHitEvent got called on the same actor over and over for as
; long as they stayed nearby. Add-only, no unregister needed (unlike BladeTagged's
; OnDeath registration, a lingering HitEvent registration is inert until WE attack them
; again) — FIFO eviction just means an evicted actor gets re-armed next time they're
; seen, a harmless repeat call, not a leak.
Actor[] HitArmed
Int HitArmedCount = 0
Int HIT_ARMED_MAX = 32
Float LastKnifeKillRealTime = 0.0
Float KNIFE_KILL_COOLDOWN = 1.5
Int LastDeathToastId = 0
Int LastHandledKillId = 0
Cell LastBladeToastCell
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
String Property DEBUG_BUILD = "C2-stable" Auto ; detection = C2-pipe filters; Settler uses nameless whisper only
; Notice poll diag state moved to VoiceAlias with notice banks.
Bool RefreshDebugBusy = False
Int Property KillScanTickCount = 0 Auto
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
; How many ModValue(-1) pairs this mod has applied (0 or 1). Survives loads; blocks re-apply.
Int Property HungerSpecialPenaltyDepth = 0 Auto
Spell KnifeHungerSpell
MagicEffect KnifeHungerAgiEffect
MagicEffect KnifeHungerChaEffect
GlobalVariable KnifeHungerGlobal
Bool HungerSpellLoadWarned
Float HUNGER_POLL_SECONDS = 12.0
Float BOND_POLL_SECONDS = 4.0
Float TRUST_VOICE_SECONDS = 180.0
Float NOTICE_VOICE_SECONDS = 45.0 ; C2 nearby-female comments (slow ambient backup)
Float KILL_SCAN_SECONDS = 2.0 ; KillerScan tick; hunger toasts gated separately by game-hour

; Legacy timer ids — CancelTimer only on load (stale saves). KillerScan is the sole StartTimer.
Int TIMER_HUNGER = 1
Int TIMER_BOND = 2
Int TIMER_TRUST = 3
Int TIMER_KILL = 4
Int TIMER_NOTICE = 5
Int TIMER_NOTICE_APPROACH = 6
Int TIMER_BOOT_ARM = 7
Int TIMER_KILL_SCAN = 13
Int TIMER_RENAME_PROMPT = 14
Int TIMER_DECAY_SYNC = 15
Int TIMER_DECAY_ADVANCE = 17
Float RENAME_PROMPT_DELAY = 2.5
String Property PendingRenamePrompt = "" Auto
Float Property PendingRenameAtReal = 0.0 Auto
Float NextBondRealTime = 0.0
Float NextHungerRealTime = 0.0
Float NextTrustRealTime = 0.0
Float NextNoticeRealTime = 0.0
Float BootArmDeadlineReal = 0.0
String MOD_VERSION = "1.3.0"
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
Int FID_PERK_CANNIBAL_1 = 0x0004B259 ; Cannibal01 (Hole in the Wall quest reward)
Int FID_PERK_CANNIBAL_2 = 0x001D1A62 ; Cannibal02
Int FID_PERK_CANNIBAL_3 = 0x001D1A63 ; Cannibal03
Int FID_MGEF_RESTORE_HEALTH_GENERIC = 0x00023735 ; RestoreHealthGeneric
; Local forms (PickmansWhisper.esp) — low word for GetFormFromFile
Int FID_HUNGER_SPEL = 0x00000801
Int FID_HUNGER_GLOB = 0x00000802
Int FID_HUNGER_MGEF_AGI = 0x00000803
Int FID_HUNGER_MGEF_CHA = 0x00000804
Int FID_PLAYER_COMBAT_QUEST = 0x00000805 ; alias OnPlayerLoadGame lives here
Int FID_SEVER_MSG = 0x00000806 ; PW_SeverLimbMenu — Slice F butcher menu
; D0-POC / D0.5 whisper SNDRs — EndIt is BASE+0; clones follow Desperate_Audio.txt order.
Message SeverLimbMenu

String Property MOD_NAME = "PickmansWhisper" Auto
Int Property LINE_FILE_MAX = 64 Auto

String[] TrustLines
Int TrustLineCount = 0
String[] HungerLines
Int HungerLineCount = 0
String[] PraiseLines
Int PraiseLineCount = 0
; ModConfig.txt fields + decayStage0..4 live on ModConfigAlias (PickmansWhisperModConfigScript).
; Slice H P4 — Cannibal nag cooldown across all ripe corpses (not ModConfig).
Float LastEatRipeCorpseToastGameTime = 0.0
Float EAT_RIPE_CORPSE_TOAST_MIN_GAME_HOURS = 1.0
; Mirrored from ModConfigAlias after load / EnsureDecayStagesLoaded (Victims/CorpseDecay read this).
String Property ModConfigLoadStatus = "" Auto
; Knife-kill decay registry (credited ProcessKnifeKill only). Cap + FIFO eviction.
Int DECAY_KILL_MAX = 32
Int[] DecayKillIds
Float[] DecayKillGameTime
Int[] DecayKillLastStage ; -1 = never applied
Int DecayKillSlotCount = 0

; Slice E2–E5 — soft Necromantic scene CustomEvents (FormID 0x800). No esp master.
; E4/E5: Named toast banks + parallel Intimacy_*_Audio.txt (same-index delivery).
Int FID_NECROMANTIC_MAIN = 0x00000800
NecromanticMainQuestScript NecroQuestRef
Bool NecroEventsRegistered = False
Bool NecroSceneActive = False

; Slice H — mirrored from CorpseDecayScript (ROF DeadOverlays / LooksMenu).
String Property LastCorpseDecayStatus = "" Auto
; Slice H P0.1 — mirrored from DecayWoundLabScript.
String Property LastWoundLabStatus = "" Auto

; C5 P3+P4 Potential Victims — FormID ↔ player name + GoE2.SetDisplayName (world).
; RefCollectionAlias is optional (fill in CK / later ESP); FormID table is save truth.
Int VICTIM_MAX = 32
Int[] VictimIds
String[] VictimNames
Int VictimSlotCount = 0
RefCollectionAlias Property VictimsHold Auto ; optional hold; AddRef when present
String Property LastVictimStatus = "" Auto ; MCM Victims — last apply / aimed status
String Property LastVictimsSummary = "" Auto ; MCM Victims — short list
; Aim cache + MCM Advance timer live on PickmansWhisperVictimsScript (own lock).


;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;;
;; Killer aura var start
;;
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

; TargetOverrides.txt — opt-in filter gates (default off = current safe blocks).
Bool AllowChildFemalesOverride = False
Bool AllowRobotsOverride = False
String Property LastTargetOverridesStatus = "" Auto ; MCM / trace — last load result

; Valid target (living only?) NPCs — unmapped; retiring TrackedNPCs RefCollectionAlias.
; RefCollectionAlias Property TrackedNPCs Auto Const
; CK/VMAD: bound to PickmansWhisperPlayerCombat ALST 0 (PickmansWhisperPlayerAliasScript).
PickmansWhisperPlayerAliasScript Property PlayerAlias Auto Const

ActorValue Property PW_HitWihPickmansBlade Auto Const
ActorValue Property PW_Credit_For_PickmansBlade_Kill Auto Const
ActorValue Property PW_TargetTrackerExpiration Auto Const

; CK/VMAD: bound to PickmansWhisperMain ALST ModConfigAlias / VoiceAlias.
; KillRewardAlias retired — unmapped from ESP.
; Alias script VMAD ofmt=2 object must be (unk=0, aliasId, quest) — see build_hunger_spell_esp.
; PickmansWhisperKillRewardScript Property KillRewardAlias Auto Const
PickmansWhisperModConfigScript Property ModConfigAlias Auto Const
PickmansWhisperVoiceAliasScript Property VoiceAlias Auto Const

; Fail-loud check after load (properties are Auto Const — filled by ESP, not assigned here).
Function EnsureFeatureAliases()
	If !ModConfigAlias
		Debug.Trace("PickmansWhisper: ERROR ModConfigAlias unbound — rebuild esp / new save if ALST changed")
	EndIf
	If !VoiceAlias
		Debug.Trace("PickmansWhisper: ERROR VoiceAlias unbound — rebuild esp / new save if ALST changed")
	EndIf
EndFunction

; Debounce HandleGameResume (alias + remote). Kept on Main — not voice-owned.
Float LastGameResumeRealTime = 0.0
; Toast cooldowns for trust/hunger/praise (notice cools live on VoiceAlias).
; Whisper SNDR FormIDs (also on VoiceAlias for PlayWhisperXwmByFile).
Int FID_WHISPER_ENDIT = 0x00000807
Int FID_WHISPER_BASE = 0x00000807

Int MAX_TRACKABLE_TARGETS = 10 Const

Int TARGET_TRACKER_EXPIRATION_SECONDS = 30 Const

Int TIMER_TRACKER_EXPIRE = 23   ; pick an id free on Main (avoid 1–7, 13–15, 17)
Float TRACKER_EXPIRE_POLL_SECONDS = 30.0
Bool TrackerExpireRunning = False


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

	EnsureFeatureAliases()
	EnsurePlayerCombatQuest()
	ArmRuntimeLoops()
	ScheduleBootArm()
EndEvent

Function ClearCollection(RefCollectionAlias akCollection)
    If akCollection
        Int i = akCollection.GetCount()
        While i > 0
            i -= 1
            ObjectReference kRef = akCollection.GetAt(i)
            If kRef
                akCollection.RemoveRef(kRef)
            EndIf
        EndWhile
    EndIf
EndFunction

Event OnQuestInit()
	DEBUG_BUILD = "1.3.0-KO"
	Debug.Trace("PickmansWhisper: === v1.3.0 Killer Orchestrator loaded ===")
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
	EnsureFeatureAliases()
	; Arm KillerScan on init/load — no MessageBox here (MCM Debug buttons only).
	EnsurePlayerCombatQuest()
	ArmRuntimeLoops()
	ScheduleBootArm()
	; EnsureCombatKillHooks()
	LoadLineBanks()
	RegisterNecromanticSceneEvents()
	RegisterKillerScanScripts()
	EnsureSeverLimbMenu()
	ResyncDrawnBladeState()
	RefreshBladeOwnershipFromEquip()
	RefreshDebugStatus()
	RefreshHungerPanel(False)
	Debug.Trace("PickmansWhisper: quest init " + DEBUG_BUILD + " v" + MOD_VERSION)
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
		EnsureFeatureAliases()
		EnsurePlayerCombatQuest()
		ArmRuntimeLoops()
		ScheduleBootArm()
		EnsureSeverLimbMenu()
		Return
	EndIf
	LastGameResumeRealTime = now

	; Save games persist script vars — force build id from this PEX every load
	DEBUG_BUILD = "C2-stable"
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
	EnsureFeatureAliases()
	; Arm FIRST — MCM Debug must never be required to start the notice/killscan loops.
	; No MessageBox on load (ReportNoticeLoadStatus is MCM "Test notice file load" only).
	EnsurePlayerCombatQuest()
	ArmRuntimeLoops()
	ScheduleBootArm()
	; EnsureCombatKillHooks()
	LoadLineBanks()
	RegisterNecromanticSceneEvents()
	RegisterKillerScanScripts()
	EnsureSeverLimbMenu()
	ResyncDrawnBladeState()
	RefreshBladeOwnershipFromEquip()
	ReconcileHungerSpecialPenaltyFlags()
	SyncHungerAddictionSpell()
	If VoiceAlias
		VoiceAlias.LastNoticeToastRealTime = 0.0
		VoiceAlias.LastNoticeDiagRealTime = 0.0
		VoiceAlias.LastTrustToastRealTime = 0.0
		VoiceAlias.LastHungerToastRealTime = 0.0
		VoiceAlias.LastPraiseToastRealTime = 0.0
		VoiceAlias.NoticeCoolCount = 0
	EndIf
	NecroSceneActive = False
	RefreshDebugStatus()
	RefreshHungerPanel(False)
	; Potential Victims summary only — GoE2.SetDisplayName re-applies lazily when she is seen.
	WriteVictimsSummaryToMcm()
	PickmansWhisperVictimsScript victims = Victims()
	If victims
		victims.EnsureMcmOpenRegistered()
	EndIf

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

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;;
;; Killer aura handling Start
;;
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

Function RegisterTarget(Actor akTarget)
	If !akTarget
		Debug.Trace("PickmansWhisper: RegisterTarget skip — akTarget None")
		Return
	EndIf
	If !PlayerAlias
		Debug.Trace("PickmansWhisper Error: RegisterTarget — PlayerAlias unbound")
		Return
	EndIf
	If !PlayerRef
		PlayerRef = Game.GetPlayer()
	EndIf

	Bool IsTargetDead = akTarget.IsDead()

	; Hard gate + knife feature: must have been seen non-hostile while alive.
	If !IsValidTarget(akTarget) || !WasFriendlySeen(akTarget)
		; Debug.Notification("PW RegisterTarget: " + akTarget.GetDisplayName() + " is not a valid target. Their kind holds no interest.")
		Debug.Trace("PickmansWhisper: RegisterTarget reject | " + akTarget.GetDisplayName() + " id=" + akTarget.GetFormID())
		Return
	EndIf

	Bool isPickmansBladeEquipped = PlayerAlias.IsPickmansBladeEquipped

	If !IsTargetDead && isPickmansBladeEquipped
		; Register for the events on this specific NPC
		RegisterForRemoteEvent(akTarget, "OnDeath")
		RegisterForHitEvent(akTarget, PlayerRef)
		
		; TODO replace with a toast that indicates that the NPC is being watched
		Debug.Notification("You notice " + akTarget.GetDisplayName())

		; TODO call whisper Logic
		;     Initial encounter with living target
		;     [x] Slice C integration
		;     Slice I 
		If VoiceAlias
			VoiceAlias.HandleWhisperVoice(akTarget)
		Else
			Debug.Notification("PW Error: VoiceAlias is not initialized")
			Debug.Trace("PickmansWhisper: ERROR RegisterTarget live — VoiceAlias unbound")
		EndIf

	ElseIf IsTargetDead && isPickmansBladeEquipped
		Debug.Notification("PW RegisterTarget: Target " + akTarget.GetDisplayName() + " is dead. She belongs to the knife now.")
		; TODO handle dead use cases
		;     Slice H
		;     Slice F

	ElseIf !IsTargetDead && PlayerAlias.IsReadyToGiveBeating
		; Not dead and currently tracked — blade away nudge (ModConfig needsBeatingWhisper).
		If VoiceAlias
			VoiceAlias.MaybeSpeakNeedsBeatingWhisper(akTarget)
		Else
			Debug.Trace("PickmansWhisper: RegisterTarget skip | VoiceAlias unbound (needsBeating)")
		EndIf
		; TODO handle beating use case
		;     Slice K — victim beat-before-kill
		Return
	EndIf

	Debug.Trace("PW RegisterTarget: Registered events for " + akTarget.GetDisplayName())
EndFunction

Event OnHit(ObjectReference akTarget, ObjectReference akAggressor, Form akSource, Projectile akProjectile, Bool abPowerAttack, Bool abSneakAttack, Bool abBashAttack, Bool abHitBlocked, String asMaterialName)
	Actor targetActor = akTarget as Actor
	If !targetActor
		Return
	EndIf

	Bool isPickmansBladeEquipped = False
	If PlayerAlias
		isPickmansBladeEquipped = PlayerAlias.IsPickmansBladeEquipped
	EndIf
	If isPickmansBladeEquipped
		If VoiceAlias
			VoiceAlias.MaybeSpeakHitWhisper(targetActor)
		Else
			Debug.Trace("PickmansWhisper: OnHit skip | VoiceAlias unbound")
		EndIf
	EndIf
EndEvent

Event Actor.OnDeath(Actor akSender, Actor akKiller)
	Debug.Trace("PW Manager: OnDeath Event for " + akSender.GetDisplayName())
	RewardKill(akSender)
	If VoiceAlias
		VoiceAlias.RemoveFixation(akSender)
	EndIf
EndEvent

; OnDeath / KillRewardAlias settle — credit a blade-hit kill if not already stamped.
Function RewardKill(Actor akSender)
	If !akSender
		Debug.Trace("PickmansWhisper Error: RewardKill — null sender")
		Return
	EndIf

	UnregisterForRemoteEvent(akSender, "OnDeath")
	UnregisterForAllHitEvents(akSender)

	If !PlayerAlias || !PlayerAlias.IsPickmansBladeEquipped
		Debug.Trace("PickmansWhisper: RewardKill skip — blade not equipped formId=" + akSender.GetFormID())
		Return
	EndIf
	ProcessKnifeKill(akSender)
EndFunction

; TODO Refactor this mess; Took initial stab at cleanup 
Function StartBond(String reason)
	If BondStarted
		Return
	EndIf
	
	BondStarted = True
	Float now = Utility.GetCurrentGameTime()
	BondStartGameTime = now
	
	; Delete This
	; If LastKnifeActivityGameTime <= 0.0
	;	LastKnifeActivityGameTime = now
	; EndIf
	
	; Delete This
	; LastHungerPollGameTime = now
	
	Debug.Trace("PickmansWhisper: bond started (" + reason + ")")
	
	; Always-visible status toast — not gated by voice settings or the once-ever intro
	; line, so re-bonding on a not-yet-bonded save is obvious instead of requiring an
	; MCM Debug check every few seconds to see when it catches up.
	Debug.Notification("Pickman's Whisper: bond active")
	
	If !IntroToastShown
		IntroToastShown = True
		String line = ""
		If ModConfigAlias
			line = ModConfigAlias.BondIntroGreeting
		EndIf
		If !line || GardenOfEden.StrLength(line) < 1
			Debug.Trace("PickmansWhisper: ERROR bond intro — bondIntroGreeting missing/empty (ModConfig)")
		Else
			ToastVoice(line)
		EndIf
	EndIf

	; Delete This
	; ArmRuntimeLoops()

	; MCM Hunger Panel update showing bonded status
	RefreshHungerPanel(False)
	
	; TODO RefreshDebugBusy is sus
	; MCM Debug panel update
	If !RefreshDebugBusy
		RefreshDebugStatus()
	EndIf
EndFunction

Function WhisperAliveVictim(Actor akTarget)
	If VoiceAlias
		VoiceAlias.HandleWhisperVoice(akTarget)
	Else
		Debug.Notification("Pickman's Whisper: VoiceAlias unbound — rebuild esp")
		Debug.Trace("PickmansWhisper: ERROR VoiceAlias unbound on Main quest")
	EndIf
EndFunction

; --- MCM CallFunction entry points only (MCM targets MainQuestScript by name) ---
; Everything else: call VoiceAlias.<fn> directly at the use site.

Function DebugTestNoticeLine(Actor akTarget)
	If !VoiceAlias
		Debug.Notification("Pickman's Whisper: VoiceAlias unbound — rebuild esp")
		Debug.Trace("PickmansWhisper: ERROR DebugTestNoticeLine — VoiceAlias unbound")
		Return
	EndIf
	VoiceAlias.DebugTestNoticeLine(akTarget)
EndFunction

Function DebugTestNoticeFiles()
	If !VoiceAlias
		Debug.Notification("Pickman's Whisper: VoiceAlias unbound — rebuild esp")
		Debug.Trace("PickmansWhisper: ERROR DebugTestNoticeFiles — VoiceAlias unbound")
		Return
	EndIf
	VoiceAlias.DebugTestNoticeFiles()
EndFunction

Function DebugVoicePathDump()
	If !VoiceAlias
		Debug.Notification("Pickman's Whisper: VoiceAlias unbound — rebuild esp")
		Debug.Trace("PickmansWhisper: ERROR DebugVoicePathDump — VoiceAlias unbound")
		Return
	EndIf
	VoiceAlias.DebugVoicePathDump()
EndFunction

Function LookingAtTarget(Actor WhoIsThat)
	; Look-edge voice (1 silent / 2 stage / 3+ recognition) — every sample, not comment-cooldown.
	If VoiceAlias
		VoiceAlias.LookFixation(WhoIsThat)
	Else
		Debug.Trace("PickmansWhisper: ERROR TargetScan LookFixation — VoiceAlias unbound")
		Debug.Notification("PW Error: VoiceAlias unbound — rebuild esp")
	EndIf
	; Slice I — desperate display-name suffix on the aimed NPC (same Quest, sibling script).
	PickmansWhisperDesperateRenameScript rename = DesperateRename()
	If rename
		rename.DesperateRename(WhoIsThat)
	Else
		Debug.Trace("PickmansWhisper: ERROR TargetScan DesperateRename — script unbound (rebuild esp)")
		Debug.Notification("PW Error: DesperateRename unbound — rebuild esp")
	EndIf
EndFunction

;----------------------- Utility -----------------------

; Returns the distance from an actor to the player in meters
Float Function GetDistanceToPlayerInMeters(Actor akTarget)
    If !akTarget
        Return -1.0 ; Invalid target check
    EndIf
	If !PlayerRef
		PlayerRef = Game.GetPlayer()
	EndIf
    
    ; Calculate distance and convert to meters (70 units ≈ 1 meter)
    Return (akTarget.GetDistance(PlayerRef) / 70.0)
EndFunction

;----------------------- Clean Up -----------------------

; Unregister the target NPC if they are more than N meters away from the Player
function UnRegisterTarget(Actor akTarget)
	If !akTarget
		Return
	EndIf
	If !PlayerRef
		PlayerRef = Game.GetPlayer()
	EndIf

	UnregisterForRemoteEvent(akTarget, "OnDeath")
	UnregisterForHitEvent(akTarget, PlayerRef)

	Debug.Notification("PicknmansWhisper Debug: No longer tracking " + akTarget.GetDisplayName())
EndFunction

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;;
;; Killer aura handling Stop; Begin of sus code
;;
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;


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
		DiagNotify("Pickman's Whisper: butcher unavailable during Necromantic scene")
		Return
	EndIf
	If !IsBladeEquipped()
		DiagNotify("Pickman's Whisper: draw Pickman's Blade for the butcher menu")
		Return
	EndIf
	If !PlayerRef
		PlayerRef = Game.GetPlayer()
	EndIf
	Actor aimed = ResolveSeverCorpseAim(abIgnoreMenuMode)
	If !aimed
		DiagNotify("Pickman's Whisper: aim / face a corpse for the butcher menu")
		Return
	EndIf
	EnsureSeverLimbMenu()
	If !SeverLimbMenu
		DiagNotify("Pickman's Whisper: butcher menu missing — rebuild ESP")
		Debug.Trace("PickmansWhisper: ERROR TrySeverAimedCorpse no MSG 0x806")
		Return
	EndIf
	Int btn = SeverLimbMenu.Show()
	; 0 Head / 1 LArm / 2 RArm / 3 LLeg / 4 RLeg / 5 Cancel
	If btn < 0
		DiagNotify("Pickman's Whisper: butcher Show failed (btn=" + btn + ")")
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
	; LooksMenu body overlays glow at stump edges — strip PW decay skins after butcher.
	PickmansWhisperCorpseDecayScript decay = CorpseDecay()
	If decay
		decay.QueueStripBodyDecayAfterDismember(ak)
	EndIf
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
		DiagNotify("Pickman's Whisper\n\nDraw Pickman's Blade first.")
		Return
	EndIf
	Actor aimed = ResolveSeverCorpseAim(True)
	If !aimed
		DiagNotify("Pickman's Whisper\n\nAim / face a dead adult female (or look then open MCM), then retry.")
		Return
	EndIf
	SeverCorpseLimb(aimed, "Head1")
	DiagNotify("Pickman's Whisper\n\nSever head requested on aimed corpse.")
EndFunction

; Soft E2 — register Necromantic scene CustomEvents when plugin present.
PickmansWhisperKillerScanScript Function KillerScan()
	Return (Self as Quest) as PickmansWhisperKillerScanScript
EndFunction

PickmansWhisperVictimsScript Function Victims()
	; Caprica forbids Self-as-sibling; Quest intermediate is the FO4 co-script cast.
	Return (Self as Quest) as PickmansWhisperVictimsScript
EndFunction

; Verify KillerScan + VoiceScan attached (dispatch is direct from KillerScan, not CustomEvent).
Function RegisterKillerScanScripts()
	EnsureFeatureAliases()
	PickmansWhisperKillerScanScript scan = KillerScan()
	If !scan
		Debug.Notification("Pickman's Whisper: KillerScan script missing — rebuild PickmansWhisper.esp")
		Debug.Trace("PickmansWhisper: ERROR KillerScan script missing on Main quest")
		Return
	EndIf
	If !VoiceAlias
		Debug.Notification("Pickman's Whisper: VoiceAlias unbound — rebuild PickmansWhisper.esp")
		Debug.Trace("PickmansWhisper: ERROR VoiceAlias unbound on Main quest")
	EndIf
	PickmansWhisperVictimsScript victims = Victims()
	If !victims
		Debug.Notification("Pickman's Whisper: Victims script missing — rebuild PickmansWhisper.esp")
		Debug.Trace("PickmansWhisper: ERROR Victims script missing on Main quest")
	Else
		victims.EnsureMcmOpenRegistered()
	EndIf
EndFunction

Function StartKillerScanLoop()
	; PickmansWhisperKillerScanScript scan = KillerScan()
	; If !scan
	;	Debug.Trace("PickmansWhisper: ERROR StartKillerScanLoop — KillerScan missing")
	;	Return
	; EndIf
	; scan.StartKillerScanLoop()
EndFunction

Function NoteKillerScanCounts(Int tick, Int aliveCount, Int deadCount, Int detectCount)
	KillScanTickCount = tick
	LastGoeAliveCount = aliveCount
	LastGoeDeadCount = deadCount
	LastDetectCount = detectCount
EndFunction

; KillerScan CallFunctionNoWait — knife credit + Victims aim.
; Voice runs sync on VoiceScan before this is kicked (must not Wait / LooksMenu).
Function HandleKillerScanKnifeAimWarm()
	PickmansWhisperKillerScanScript scan = KillerScan()
	If !scan
		Debug.Trace("PickmansWhisper: ERROR HandleKillerScanKnifeAimWarm — KillerScan missing")
		Return
	EndIf
	ProcessKnifeCreditFromKillerScan(scan)
	OnKillerScanVictimsAim(scan)
	If KillScanTickCount == 1 || (KillScanTickCount % 3) == 0
		String bladeBit = "blade=NO"
		If IsBladeEquipped()
			bladeBit = "blade=YES"
		EndIf
		String noticeBit = ""
		If VoiceAlias
			noticeBit = VoiceAlias.LastNoticeStatus
		EndIf
		ToastDebug("PW scan [" + DEBUG_BUILD + "] #" + KillScanTickCount + " near=" + BladeTaggedCount + " goeA=" + LastGoeAliveCount + " goeD=" + LastGoeDeadCount + " det=" + LastDetectCount + " " + bladeBit + " notice=" + noticeBit)
	EndIf
EndFunction

Function OnKillerScanVictimsAim(PickmansWhisperKillerScanScript akSender)
	If !akSender
		Return
	EndIf
	Actor cam = akSender.CameraActor
	Actor facedDead = akSender.FacedDead
	If cam && cam != PlayerRef && !cam.IsDisabled()
		NoteVictimsAimActor(cam)
	EndIf
	If facedDead && facedDead != PlayerRef && !facedDead.IsDisabled()
		NoteVictimsAimActor(facedDead)
	EndIf
EndFunction

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
	If VoiceAlias
		VoiceAlias.MaybeSpeakNamedIntimacyEvent(corpse, True)
	EndIf
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
	If corpse && VoiceAlias
		VoiceAlias.MaybeSpeakNamedIntimacyEvent(corpse, False)
	EndIf
	NecroSceneActive = False
	Debug.Trace("PickmansWhisper: OnNecroSceneEnd completed=" + completed)
EndEvent

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

; Killer Orchestrator — cancel stale feature timers; arm sole KillerScan pulse.
Function ArmRuntimeLoops()
	CancelTimer(TIMER_HUNGER)
	CancelTimer(TIMER_BOND)
	CancelTimer(TIMER_TRUST)
	CancelTimer(TIMER_NOTICE)
	CancelTimer(TIMER_NOTICE_APPROACH)
	CancelTimer(TIMER_KILL)
	CancelTimer(TIMER_KILL_SCAN)
	CancelTimer(TIMER_DECAY_SYNC)
	CancelTimer(TIMER_BOOT_ARM)
	CancelTimer(TIMER_RENAME_PROMPT)
	CancelTimer(TIMER_DECAY_ADVANCE)
	NextBondRealTime = 0.0
	NextHungerRealTime = 0.0
	NextTrustRealTime = 0.0
	NextNoticeRealTime = 0.0
	RegisterKillerScanScripts()
	; StartKillerScanLoop()
	Debug.Trace("PickmansWhisper: ArmRuntimeLoops — KillerScan only v" + MOD_VERSION)
EndFunction

; Load retry without a second StartTimer — deadline checked on KillerScan cadence.
Function ScheduleBootArm()
	CancelTimer(TIMER_BOOT_ARM)
	BootArmDeadlineReal = Utility.GetCurrentRealTime() + BOOT_ARM_SECONDS
	Debug.Trace("PickmansWhisper: ScheduleBootArm deadline +" + BOOT_ARM_SECONDS + "s (Killer Orchestrator)")
EndFunction

; Ported from former Main timers — called via KillerScan NoWait each tick.
Function OnKillerScanCadence()
	;Float now = Utility.GetCurrentRealTime()
	;If BootArmDeadlineReal > 0.0 && now >= BootArmDeadlineReal
	;	BootArmDeadlineReal = 0.0
	;	EnsurePlayerCombatQuest()
	;	ArmRuntimeLoops()
	;	Debug.Trace("PickmansWhisper: boot-arm deadline fired v" + MOD_VERSION)
	;EndIf
	;If PendingRenameAtReal > 0.0 && now >= PendingRenameAtReal
	;	PendingRenameAtReal = 0.0
	;	If PendingRenamePrompt
	;		If VoiceAlias
	;			VoiceAlias.ShowVoiceToast(PendingRenamePrompt)
	;		EndIf
	;		Debug.Trace("PickmansWhisper: name-her prompt (deadline) | " + PendingRenamePrompt)
	;		PendingRenamePrompt = ""
	;	Else
	;		Debug.Trace("PickmansWhisper: rename deadline skip | empty prompt")
	;	EndIf
	;EndIf
	;If now >= NextBondRealTime
	;	NextBondRealTime = now + BOND_POLL_SECONDS
	;	RunBondPoll()
	;EndIf
	;If now >= NextHungerRealTime
	;	NextHungerRealTime = now + HUNGER_POLL_SECONDS
	;	RunHungerTick()
	;EndIf
	;If now >= NextTrustRealTime
	;	NextTrustRealTime = now + TRUST_VOICE_SECONDS
	;	MaybeSpeakTrustLine()
	;EndIf
	;If now >= NextNoticeRealTime
	;	NextNoticeRealTime = now + NOTICE_VOICE_SECONDS
	;	If VoiceAlias
	;		VoiceAlias.MaybeSpeakNoticeLine()
	;	EndIf
	;EndIf
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
	
	; Slice K5 — any weapon equip (Pickman's Blade included) ends the beat-before-kill
	; scuffle; her death is meant to come from the blade normally, not while essential.
	PickmansWhisperBeatBeforeKillScript beat = BeatBeforeKill()
	
	If beat
		beat.ClearAllEssentialOnWeaponEquip()
	EndIf
	
	Bool isPickmans = FormLooksLikePickmansBlade(akBaseObject, akReference)
	If !isPickmans && FormIsCombatKnife(akBaseObject)
		; akReference often None — GoE sees the real equipped instance name/mods
		isPickmans = (FindEquippedPickmansBladeIndex() >= 0)
	EndIf

	If isPickmans
		BladeCurrentlyDrawn = True
		RuntimeBladeForm = akBaseObject
		MarkOwnedBlade("equipped")
		
		; Add Cloak
	Else
		BladeCurrentlyDrawn = False
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

; Soft backup only — quiet settler kills often never raise combat state.
Event Actor.OnCombatStateChanged(Actor akSender, Actor akTarget, Int aeCombatState)
	If akSender != PlayerRef
		Return
	EndIf
	If aeCombatState == 1 && akTarget
		TrackLivingNear(akTarget)
		PickmansWhisperBeatBeforeKillScript beat = BeatBeforeKill()
		If beat
			beat.OnPlayerEnterCombatWith(akTarget)
		EndIf
	EndIf
	; No aeCombatState==0 handling here — Slice J's essential reversal is weapon-equip
	; only now (see PickmansWhisperBeatBeforeKillScript's top-of-file note: an "out of
	; combat" reversal raced with an essential actor's own protected-collapse moment and
	; actively broke the feature).
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
	If !CannibalPerk1
		CannibalPerk1 = Game.GetFormFromFile(FID_PERK_CANNIBAL_1, "Fallout4.esm") as Perk
	EndIf
	If !CannibalPerk2
		CannibalPerk2 = Game.GetFormFromFile(FID_PERK_CANNIBAL_2, "Fallout4.esm") as Perk
	EndIf
	If !CannibalPerk3
		CannibalPerk3 = Game.GetFormFromFile(FID_PERK_CANNIBAL_3, "Fallout4.esm") as Perk
	EndIf
	If !RestoreHealthGenericEffect
		RestoreHealthGenericEffect = Game.GetFormFromFile(FID_MGEF_RESTORE_HEALTH_GENERIC, "Fallout4.esm") as MagicEffect
	EndIf
EndFunction

; Any rank — Fallout4.esm grants each Cannibal rank as its own PERK record additively.
Bool Function PlayerHasCannibalPerk()
	If !PlayerRef
		Return False
	EndIf
	ResolveVanillaForms()
	If CannibalPerk1 && PlayerRef.HasPerk(CannibalPerk1)
		Return True
	EndIf
	If CannibalPerk2 && PlayerRef.HasPerk(CannibalPerk2)
		Return True
	EndIf
	If CannibalPerk3 && PlayerRef.HasPerk(CannibalPerk3)
		Return True
	EndIf
	Return False
EndFunction

; Slice H P5 — detect "player ate a corpse." No vanilla script anywhere registers an
; animation event for this (checked FO4's real Scripts/Source; the one precedent found,
; Bloodbug's feed event, is an arbitrary per-animation name like "FillingRed" with zero
; guessable convention) so an animation-event name cannot be verified without a live
; in-game discovery pass. Instead: the vanilla Cannibal fragment
; (PRKF_Cannibal_0004B259) always does `PerkCannibalHeal.Cast(player, player)`, and that
; spell's single effect is RestoreHealthGeneric (verified against Fallout4.esm,
; duration 5s) — the same generic heal MGEF Stimpaks etc. also use, so it is NOT
; cannibal-exclusive by itself. MaybeRewardEatenRipeCorpse compensates by additionally
; requiring the Cannibal perk (without it this MGEF cannot come from eating — the vanilla
; Eat choice would not exist) and a tracked, max-stage corpse within butcher range.
;
; Registration lives on PickmansWhisperPlayerAliasScript (ReferenceAlias filled with the
; player), NOT here — a Quest-level RegisterForMagicEffectApplyEvent(PlayerRef, ...) was
; tried first and never fired even once (confirmed live: an unfiltered sniff variant of
; it caught zero effects over two minutes of play, though registration itself reported
; success). The alias already proves the working pattern for other per-player natives
; (RegisterForKey/RegisterForPlayerSleep re-armed every load; OnCombatStateChanged fires
; locally with zero registration) so magic-effect detection moved there too. This getter
; is what the alias calls to resolve the filter effect.
MagicEffect Function GetRestoreHealthGenericEffect()
	ResolveVanillaForms()
	Return RestoreHealthGenericEffect
EndFunction

; MCM Debug switcher handler — delegates the actual (un)registration to the alias, since
; RegisterForMagicEffectApplyEvent(Self) there is what's proven to work; this script just
; tracks the flag for HandlePlayerMagicEffectApply's Trace-or-not decision.
Function SyncMagicEffectSniffer()
	Bool want = False
	If MCM.IsInstalled()
		want = MCM.GetModSettingBool(MOD_NAME, "bSniffMagicEffects:Debug")
	EndIf
	If !PlayerAlias
		Debug.Trace("PickmansWhisper: ERROR SyncMagicEffectSniffer — PlayerAlias property unbound")
		Debug.Notification("PW: PlayerAlias unbound")
		Return
	EndIf
	PlayerAlias.SyncMagicEffectSniff(want)
	DebugSniffMagicEffects = want
EndFunction

; Called by PickmansWhisperPlayerAliasScript.OnMagicEffectApply (local alias event).
Function HandlePlayerMagicEffectApply(MagicEffect akEffect)
	If DebugSniffMagicEffects
		Debug.Trace("PickmansWhisper: DEBUG MagicEffectApply effect=" + akEffect)
	EndIf
	If akEffect != RestoreHealthGenericEffect
		Return
	EndIf
	MaybeRewardEatenRipeCorpse()
EndFunction

; Trigger fires ~0.6s+ after the vanilla fragment's StartCannibal call (see its own Wait),
; so the player is still standing at/near her — no extra delay needed before resolving
; nearest corpse, unlike the fragment's own animation timing.
Function MaybeRewardEatenRipeCorpse()
	If !PlayerRef || !PlayerHasCannibalPerk()
		Debug.Trace("PickmansWhisper: eaten-ripe-corpse skip | no Cannibal perk (heal was not from eating)")
		Return
	EndIf
	PickmansWhisperKillerScanScript scan = KillerScan()
	If !scan
		Debug.Trace("PickmansWhisper: eaten-ripe-corpse skip | KillerScan missing")
		Return
	EndIf
	Actor[] dead = scan.ScanDead
	Int deadCount = scan.ScanDeadCount
	If !dead || deadCount <= 0
		Debug.Trace("PickmansWhisper: eaten-ripe-corpse skip | ScanDead empty")
		Return
	EndIf
	Int n = deadCount
	If n > 16
		n = 16
	EndIf
	Actor nearest = None
	Float nearestDist = BUTCHER_CORPSE_RADIUS + 1.0
	Int i = 0
	While i < n
		Actor ak = dead[i]
		If ak && ak != PlayerRef
			Float d = PlayerRef.GetDistance(ak)
			If d < nearestDist
				nearestDist = d
				nearest = ak
			EndIf
		EndIf
		i += 1
	EndWhile
	If !nearest
		Debug.Trace("PickmansWhisper: eaten-ripe-corpse skip | no corpse within " + BUTCHER_CORPSE_RADIUS)
		Return
	EndIf
	Int formId = nearest.GetFormID()
	If FindDecayKillSlot(formId) < 0
		Debug.Trace("PickmansWhisper: eaten-ripe-corpse skip | nearest corpse untracked formId=" + formId)
		Return
	EndIf
	If !ModConfigAlias || ResolveDecayStageForKill(formId) != (ModConfigAlias.DECAY_STAGE_COUNT - 1)
		Debug.Trace("PickmansWhisper: eaten-ripe-corpse skip | nearest corpse not max stage formId=" + formId)
		Return
	EndIf
	ToastAteRipeCorpse(nearest)
	ApplyEatRipeCorpseBonus(nearest)
EndFunction

Function ToastAteRipeCorpse(Actor akCorpse)
	If !akCorpse
		Return
	EndIf
	If !ModConfigAlias || !ModConfigAlias.AteRipeCorpseToast || GardenOfEden.StrLength(ModConfigAlias.AteRipeCorpseToast) < 1
		Debug.Trace("PickmansWhisper: eaten-ripe-corpse skip | no ateRipeCorpseToast (ModConfig not loaded / key empty)")
		Return
	EndIf
	String overrideName = GetVictimOverrideName(akCorpse)
	If !overrideName
		overrideName = "She"
	EndIf
	If !VoiceAlias
		Debug.Trace("PickmansWhisper: eaten-ripe-corpse skip | VoiceAlias unbound")
		Return
	EndIf
	String line = VoiceAlias.ApplyNamePlaceholder(ModConfigAlias.AteRipeCorpseToast, overrideName)
	If !line || GardenOfEden.StrLength(line) < 1
		Debug.Trace("PickmansWhisper: eaten-ripe-corpse skip | empty line after placeholder")
		Return
	EndIf
	Debug.Notification(line)
	Debug.Trace("PickmansWhisper: eaten-ripe-corpse toast | " + line + " formId=" + akCorpse.GetFormID())
EndFunction

; Bonus reward for eating a corpse at max decay stage — dedicated BuffTracker script
; (extensible for future buffs). akCorpse unused today but kept for future per-victim
; bonus variants (e.g. named victims granting something different).
Function ApplyEatRipeCorpseBonus(Actor akCorpse)
	PickmansWhisperBuffTrackerScript buffs = BuffTracker()
	If !buffs
		Debug.Trace("PickmansWhisper: ERROR ApplyEatRipeCorpseBonus — BuffTracker missing")
		Return
	EndIf
	buffs.ApplyEatRipeCorpseEndBuff()
EndFunction

; --- Bond / trigger ------------------------------------------------------------

Function StartBondPoll()
	; Killer Orchestrator — bond cadence via OnKillerScanCadence (no StartTimer).
	CancelTimer(TIMER_BOND)
	NextBondRealTime = 0.0
EndFunction

Function RunBondPoll()
	If !PlayerRef
		PlayerRef = Game.GetPlayer()
	EndIf
	If !PlayerRef || Utility.IsInMenuMode()
		Return
	EndIf
	ResolveVanillaForms()

	; Bond poll survives save load — re-arm world scan here (SingleUpdate does not).
	; StartKillerScanLoop()

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
	; GoE StrFind returns occurrence count (>0 == contains), not a char index.
	Return GardenOfEden.StrFind(n, BLADE_NAME_NEEDLE) > 0
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
	If !PlayerAlias
		Debug.Trace("PickmansWhisper Error: RegisterTarget — PlayerAlias unbound")
		Return
	EndIf

	return PlayerAlias.IsPickmansBladeEquipped
EndFunction

; Alias for kill checks — no sheath / empty-hand grace. Gun or fists = not ready.
Bool Function IsBladeKillWeaponReady()
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

; Former Debug.MessageBox — no pause; full text in Papyrus.0.log (filter PickmansWhisper).
Function DiagNotify(String msg)
	If msg == ""
		Return
	EndIf
	Debug.Trace("PickmansWhisper: DIAG " + msg)
	Debug.Notification(msg)
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
	; Blade toasts prove bond poll / load is alive — force-arm world scan there
	; StartKillerScanLoop()
	AnnounceKillScanArmed()
EndFunction

; --- Trust voice ---------------------------------------------------------------

Function StartTrustVoice()
	CancelTimer(TIMER_TRUST)
	NextTrustRealTime = 0.0
EndFunction

Function MaybeSpeakTrustLine()
	If !BondStarted || !VoiceAlias || !VoiceAlias.IsVoiceEnabled()
		Return
	EndIf
	If Utility.IsInMenuMode()
		Return
	EndIf
	If !VoiceAlias || !VoiceAlias.IsVoiceWeaponReady()
		Return
	EndIf
	Float now = Utility.GetCurrentRealTime()
	If (now - VoiceAlias.LastTrustToastRealTime) < VoiceAlias.TRUST_TOAST_COOLDOWN
		Return
	EndIf
	String line = PickTrustLine()
	If line != ""
		ToastVoice(line)
	EndIf
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

; Re-apply world name when stored override differs from current display.
; GoE2.SetDisplayName — NOT Actor.SetDisplayName (SKSE-shaped; missing at FO4 runtime).
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
	GardenOfEden2.SetDisplayName(ak, n)
EndFunction

; Apply player-chosen name to a living OR dead actor (MCM / debug) — naming a corpse
; is a supported workflow (MCM: "aim a corpse, then open MCM" for the decay-stage row
; on this same page), so this must not require her to still be alive.
Bool Function ApplyVictimName(Actor ak, String name)
	If !ak || !name
		LastVictimStatus = "apply failed — no actor or name"
		WriteVictimsStatusToMcm()
		Return False
	EndIf
	If !IsValidTarget(ak)
		; Hard-gate Trace already fired inside IsValidTarget.
		Return False
	EndIf
	If !VoiceAlias
		LastVictimStatus = "apply failed — VoiceAlias unbound"
		WriteVictimsStatusToMcm()
		Debug.Notification("Pickman's Whisper: VoiceAlias unbound — rebuild esp")
		Return False
	EndIf
	String useName = VoiceAlias.TrimString(name)
	If !VoiceAlias.IsUsableWhisperName(useName)
		LastVictimStatus = "apply failed — name not usable (generic/junk?)"
		WriteVictimsStatusToMcm()
		Debug.Notification("Pickman's Whisper: name rejected — use a real name (not Settler/Resident)")
		Return False
	EndIf
	; Block workshop generics even if they pass glyph checks
	If VoiceAlias.NoticeNameForLine(useName) == ""
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
	; GoE returns true on no native error — verify aim/HUD name with GetDisplayName.
	Bool goeOk = GardenOfEden2.SetDisplayName(ak, useName)
	HoldVictimRef(ak)
	String shown = ak.GetDisplayName()
	If shown == useName
		LastVictimStatus = useName + " ok id=0x" + GardenOfEden.GetHexFormID(ak)
	Else
		LastVictimStatus = useName + " stored; world name still '" + shown + "' goe=" + goeOk + " id=0x" + GardenOfEden.GetHexFormID(ak)
		Debug.Trace("PickmansWhisper: ERROR GoE2.SetDisplayName verify failed want='" + useName + "' got='" + shown + "' goeOk=" + goeOk)
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

; How many slots share this exact name (FormID table — same label on different NPCs).
Int Function CountVictimNameOccurrences(String name)
	If !name
		Return 0
	EndIf
	EnsureVictimLists()
	Int c = 0
	Int i = 0
	While i < VictimSlotCount
		If VictimNames[i] == name
			c += 1
		EndIf
		i += 1
	EndWhile
	Return c
EndFunction

; True if an earlier slot already listed this name (for unique summary rows).
Bool Function VictimNameAlreadyListed(String name, Int beforeIndex)
	If !name || beforeIndex <= 0
		Return False
	EndIf
	Int j = 0
	While j < beforeIndex
		If VictimNames[j] == name
			Return True
		EndIf
		j += 1
	EndWhile
	Return False
EndFunction

; MCM list: unique names; "Leslie x2" when two different FormIDs share a label.
Function WriteVictimsSummaryToMcm()
	EnsureVictimLists()
	String s = ""
	Int i = 0
	Int shown = 0
	While i < VictimSlotCount && shown < 8
		If VictimNames[i] && !VictimNameAlreadyListed(VictimNames[i], i)
			If s != ""
				s += "; "
			EndIf
			Int copies = CountVictimNameOccurrences(VictimNames[i])
			If copies > 1
				s += VictimNames[i] + " x" + copies
			Else
				s += VictimNames[i]
			EndIf
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

; --- Victims MCM façades (logic on PickmansWhisperVictimsScript) ---------------

Int Function GetDecayKillSlotCount()
	EnsureDecayKillLists()
	Return DecayKillSlotCount
EndFunction

; Aimed-row fallback when Victims cache is empty (no FindActors).
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

; Decay row without re-entering Victims.Resolve (avoids lock deadlock from Push).
; abSyncStepper=False during Set/Reset so Pick stage is not clobbered mid-button race.
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

; Keep Victims "Pick stage" stepper aligned with the aimed / last-kill clock.
; Prefer resolved clock stage (what KillerScan / ForceDecay want) over LastStage-1, so a queued
; apply does not snap the stepper backward before overlays land.
Function SyncVictimDecayStageStepper(Int formId)
	If !MCM.IsInstalled() || formId == 0
		Return
	EndIf
	If FindDecayKillSlot(formId) < 0
		Return
	EndIf
	If !DecayStagesReady()
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

Function WriteVictimsAimedToMcm()
	PickmansWhisperVictimsScript v = Victims()
	If v
		v.WriteVictimsAimedToMcm()
	EndIf
EndFunction

Function NoteVictimsAimActor(Actor ak)
	PickmansWhisperVictimsScript v = Victims()
	If v
		v.NoteVictimsAimActor(ak)
	EndIf
EndFunction

Actor Function ResolveVictimsAimActor()
	PickmansWhisperVictimsScript v = Victims()
	If v
		Return v.ResolveVictimsAimActor()
	EndIf
	Return None
EndFunction

Function PushVictimsPanelStrings()
	PickmansWhisperVictimsScript v = Victims()
	If v
		v.PushVictimsPanelStrings()
	EndIf
EndFunction

Function RefreshVictimsPanel(Bool refreshMenu = True)
	PickmansWhisperVictimsScript v = Victims()
	If v
		v.RefreshVictimsPanel(refreshMenu)
	EndIf
EndFunction

; Debug — prove MCM CallFunction reaches MainQuestScript (multi-script quest needs scriptName).
Function MCMQuestPing()
	Int cacheId = 0
	String victimsBit = "VictimsScript=MISSING"
	PickmansWhisperVictimsScript v = Victims()
	If v
		cacheId = v.LastVictimsAimId
		victimsBit = "VictimsScript=OK"
	EndIf
	Debug.Notification("PW QUEST PING — CallFunction hit MainQuestScript")
	Debug.Trace("PickmansWhisper: MCMQuestPing OK")
	DiagNotify("Pickman's Whisper — QUEST PING\n\nCallFunction reached PickmansWhisperMainQuestScript.\nBond=" + BondStarted + " killsTracked=" + DecayKillSlotCount + " cacheId=" + cacheId + "\n" + victimsBit)
EndFunction

; Façade — MCM CallFunction targets VictimsScript (own lock). Kept for old configs.
Function MCMRefreshVictimsPanel()
	PickmansWhisperVictimsScript v = Victims()
	If v
		v.MCMRefreshVictimsPanel()
	Else
		Debug.Notification("PW Victims — VictimsScript missing; rebuild ESP")
		Debug.Trace("PickmansWhisper: ERROR MCMRefreshVictimsPanel — VictimsScript missing")
		DiagNotify("Pickman's Whisper — Victims\n\nVictimsScript missing on Main quest.\nRebuild / reinstall PickmansWhisper.esp")
	EndIf
EndFunction

; Backdate kill clock by ModConfig startHours so ResolveDecayStageForKill == aiStage.
; killTime = now - (startHours / 24). Stage 0 => now (0 hours).
Bool Function ForceDecayKillClockToStage(Int formId, Int aiStage)
	If !ModConfigAlias || formId == 0 || aiStage < 0 || aiStage >= ModConfigAlias.DECAY_STAGE_COUNT
		Return False
	EndIf
	If !DecayStagesReady()
		Return False
	EndIf
	Int slot = FindDecayKillSlot(formId)
	If slot < 0
		Return False
	EndIf
	Float needH = GetDecayStageStartHours(aiStage)
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

; Façades — bodies on PickmansWhisperVictimsScript.
Bool Function QueueAimedDecayStage(Int targetStage)
	PickmansWhisperVictimsScript v = Victims()
	If v
		Return v.QueueAimedDecayStage(targetStage)
	EndIf
	LastVictimStatus = "set decay: VictimsScript missing"
	Return False
EndFunction

Bool Function QueueAimedDecayAdvance()
	PickmansWhisperVictimsScript v = Victims()
	If v
		Return v.QueueAimedDecayAdvance()
	EndIf
	LastVictimStatus = "advance decay: VictimsScript missing"
	Return False
EndFunction

Function RunPendingDecayAdvance()
	PickmansWhisperVictimsScript v = Victims()
	If v
		v.RunPendingDecayAdvance()
	EndIf
EndFunction

Bool Function AdvanceAimedDecayStage()
	PickmansWhisperVictimsScript v = Victims()
	If v
		Return v.AdvanceAimedDecayStage()
	EndIf
	Return False
EndFunction

Function MCMApplyAimedDecayStage()
	PickmansWhisperVictimsScript v = Victims()
	If v
		v.MCMApplyAimedDecayStage()
	Else
		Debug.Notification("PW Victims — VictimsScript missing; rebuild ESP")
		Debug.Trace("PickmansWhisper: ERROR MCMApplyAimedDecayStage — VictimsScript missing")
		DiagNotify("Pickman's Whisper — Set decay stage\n\nVictimsScript missing on Main quest.\nRebuild / reinstall PickmansWhisper.esp")
	EndIf
EndFunction

Function MCMResetAimedDecayKillClock()
	PickmansWhisperVictimsScript v = Victims()
	If v
		v.MCMResetAimedDecayKillClock()
	Else
		Debug.Notification("PW Victims — VictimsScript missing; rebuild ESP")
		Debug.Trace("PickmansWhisper: ERROR MCMResetAimedDecayKillClock — VictimsScript missing")
		DiagNotify("Pickman's Whisper — Reset decay stage\n\nVictimsScript missing on Main quest.\nRebuild / reinstall PickmansWhisper.esp")
	EndIf
EndFunction

Function MCMAdvanceAimedDecayStage()
	PickmansWhisperVictimsScript v = Victims()
	If v
		v.MCMAdvanceAimedDecayStage()
	Else
		Debug.Notification("PW Victims — VictimsScript missing; rebuild ESP")
		Debug.Trace("PickmansWhisper: ERROR MCMAdvanceAimedDecayStage — VictimsScript missing")
		DiagNotify("Pickman's Whisper — Advance decay\n\nVictimsScript missing on Main quest.\nRebuild / reinstall PickmansWhisper.esp")
	EndIf
EndFunction

Function MCMNameAimedVictim()
	PickmansWhisperVictimsScript v = Victims()
	If v
		v.MCMNameAimedVictim()
	Else
		Debug.Notification("PW Victims — VictimsScript missing; rebuild ESP")
		Debug.Trace("PickmansWhisper: ERROR MCMNameAimedVictim — VictimsScript missing")
		DiagNotify("Pickman's Whisper — Apply name\n\nVictimsScript missing on Main quest.\nRebuild / reinstall PickmansWhisper.esp")
	EndIf
EndFunction

; True if she is in the Potential Victims FormID table (Named victims).
Bool Function IsTrackedVictim(Actor ak)
	If !ak
		Return False
	EndIf
	Int formId = ak.GetFormID()
	If formId == 0
		Return False
	EndIf
	Return FindVictimSlot(formId) >= 0
EndFunction

; Named/tracked victim with no decay clock → stamp Freshly Deceased.
; abApplyOverlays=False from KillerScan overlay NoWait / MCM; True only for explicit apply paths.
Bool Function EnsureDecayForTrackedVictim(Actor ak, Bool abApplyOverlays = True)
	If !ak || ak == PlayerRef || !ak.IsDead()
		Return False
	EndIf
	If IsNonGameplayCorpse(ak)
		Return False
	EndIf
	Int formId = ak.GetFormID()
	If formId == 0 || FindVictimSlot(formId) < 0
		Return False
	EndIf
	If FindDecayKillSlot(formId) >= 0
		Return False
	EndIf
	StampDecayKill(ak)
	; Never LooksMenu-apply from MCM / hot killscan — stalls voice + menu.
	If !abApplyOverlays || Utility.IsInMenuMode()
		Debug.Trace("PickmansWhisper: decay clock stamped (tracked victim, overlays deferred) id=0x" + GardenOfEden.GetHexFormID(ak))
		Return True
	EndIf
	PickmansWhisperCorpseDecayScript decay = CorpseDecay()
	If !decay
		Debug.Notification("Pickman's Whisper: CorpseDecay missing — Freshly Deceased clock stamped, overlays NOT applied")
		Debug.Trace("PickmansWhisper: ERROR EnsureDecayForTrackedVictim — CorpseDecay script missing id=0x" + GardenOfEden.GetHexFormID(ak))
		Return True
	EndIf
	decay.SyncDecayForKnifeCorpse(ak)
	If GetDecayKillLastStage(formId) < 0
		Debug.Notification("Pickman's Whisper: Freshly Deceased overlays failed — " + LastCorpseDecayStatus)
		Debug.Trace("PickmansWhisper: ERROR EnsureDecayForTrackedVictim overlays pending id=0x" + GardenOfEden.GetHexFormID(ak) + " | " + LastCorpseDecayStatus)
	Else
		Debug.Trace("PickmansWhisper: decay clock + stage overlays started (tracked victim) id=0x" + GardenOfEden.GetHexFormID(ak) + " applied=" + GetDecayKillLastStage(formId))
	EndIf
	Return True
EndFunction

; Decay row from knife-kill registry FormID (no Actor required).
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
	If !DecayStagesReady()
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
	String stageName = GetDecayStageName(stage)
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

; Aimed / last-look body stage from knife-kill registry.
String Function FormatDecayStageStatusForActor(Actor ak)
	If !ak
		Return "(face a corpse, then open MCM)"
	EndIf
	If ak == PlayerRef
		Return "(player)"
	EndIf
	String label = ""
	If VoiceAlias
		label = VoiceAlias.GetActorDisplayName(ak)
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
	WriteDecayStageStatusToMcmForActor(ResolveVictimsAimActor())
EndFunction

; Slice J1 — checkbox-style status row for the aimed NPC's beat-mode essential state.
; ☑/☐ so it reads at a glance, matching the "Toggle essential" button right below it.
Function WriteBeatEssentialStatusToMcm(Actor aimed)
	If !MCM.IsInstalled()
		Return
	EndIf
	If !aimed || aimed == PlayerRef
		MCM.SetModSettingString(MOD_NAME, "sBeatEssential:Victims", "☐ (no aim — Load targeted victim)")
		Return
	EndIf
	PickmansWhisperBeatBeforeKillScript beat = BeatBeforeKill()
	If !beat
		MCM.SetModSettingString(MOD_NAME, "sBeatEssential:Victims", "☐ (BeatBeforeKill script missing)")
		Return
	EndIf
	If beat.IsTrackedEssential(aimed)
		MCM.SetModSettingString(MOD_NAME, "sBeatEssential:Victims", "☑ essential (beat mode) — toggle to clear")
	Else
		MCM.SetModSettingString(MOD_NAME, "sBeatEssential:Victims", "☐ not essential — toggle to set")
	EndIf
EndFunction

; VictimsScript CallFunctionNoWait after aimed push — decay/summary/status without stalling MCM.
Function WriteVictimsMcmAuxRows()
	PickmansWhisperVictimsScript v = Victims()
	Actor aimed = None
	If v
		aimed = v.ResolveVictimsAimActor()
		If aimed
			EnsureVictimDisplayName(aimed)
		Else
			; Keep Aimed row honest if Main has a knife-kill fallback.
			String noAim = FormatNoAimVictimsAimLine()
			If noAim && MCM.IsInstalled()
				MCM.SetModSettingString(MOD_NAME, "sVictimAimed:Victims", noAim)
			EndIf
		EndIf
	EndIf
	WriteDecayStageStatusToMcmForActor(aimed)
	WriteBeatEssentialStatusToMcm(aimed)
	WriteVictimsSummaryToMcm()
	WriteVictimsStatusToMcm()
EndFunction

; Victims MCM cache helper — body on VictimsScript.
Function TickVictimsAimCache()
	PickmansWhisperVictimsScript v = Victims()
	If v
		v.TickVictimsAimCache()
	EndIf
EndFunction

; From an already-fetched dead scan — nearest corpse in the facing cone (no extra FindActors).
Function NoteFacedDeadForVictimsAim(Actor[] dead, Int count)
	If !PlayerRef || !dead || count <= 0
		Return
	EndIf
	PickmansWhisperTargetScanScript ts = TargetScan()
	If !ts
		Debug.Trace("PickmansWhisper: ERROR NoteFacedDeadForVictimsAim — TargetScan missing")
		Return
	EndIf
	Float corpseR = ts.KILL_CORPSE_RADIUS
	Actor best = None
	Float bestDist = corpseR + 1.0
	Int i = 0
	Int n = count
	If n > 16
		n = 16
	EndIf
	While i < n
		Actor ak = dead[i]
		If ak && ak != PlayerRef && ak.IsDead() && ak.Is3DLoaded() && !ak.IsDisabled()
			If Math.abs(PlayerRef.GetHeadingAngle(ak)) <= BUTCHER_FACING_DEG
				Float d = PlayerRef.GetDistance(ak)
				If d <= corpseR && d < bestDist
					bestDist = d
					best = ak
				EndIf
			EndIf
		EndIf
		i += 1
	EndWhile
	If best
		NoteVictimsAimActor(best)
	EndIf
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

Function ToastVoice(String line)
	If line == "" || !VoiceAlias || !VoiceAlias.IsVoiceEnabled()
		Return
	EndIf
	If Utility.IsInMenuMode()
		Return
	EndIf
	If !VoiceAlias || !VoiceAlias.IsVoiceWeaponReady()
		Return
	EndIf
	VoiceAlias.LastTrustToastRealTime = Utility.GetCurrentRealTime()
	VoiceAlias.ShowVoiceToast(line)
	Debug.Trace("PickmansWhisper: voice | " + line)
EndFunction

Function ToastHungerLine(String line)
	If line == "" || !VoiceAlias || !VoiceAlias.IsVoiceEnabled()
		Return
	EndIf
	If Utility.IsInMenuMode()
		Return
	EndIf
	If !VoiceAlias || !VoiceAlias.IsVoiceWeaponReady()
		Return
	EndIf
	Float now = Utility.GetCurrentRealTime()
	If (now - VoiceAlias.LastHungerToastRealTime) < VoiceAlias.HUNGER_TOAST_COOLDOWN
		Return
	EndIf
	VoiceAlias.LastHungerToastRealTime = now
	VoiceAlias.ShowVoiceToast(line)
	Debug.Trace("PickmansWhisper: hunger voice | " + line)
EndFunction

; --- Line banks ----------------------------------------------------------------


; --- ModConfigAlias façades (bodies on PickmansWhisperModConfigScript) ----------

Bool Function IsModConfigLoadBusy()
	If !ModConfigAlias
		Return False
	EndIf
	Return ModConfigAlias.IsModConfigLoadBusy()
EndFunction

Bool Function EnsureDecayStagesLoaded()
	If !ModConfigAlias
		Debug.Trace("PickmansWhisper Error: EnsureDecayStagesLoaded — ModConfigAlias unbound")
		Return False
	EndIf
	Bool ok = ModConfigAlias.EnsureDecayStagesLoaded()
	ModConfigLoadStatus = ModConfigAlias.ModConfigLoadStatus
	Return ok
EndFunction

Bool Function DecayStagesReady()
	If !ModConfigAlias
		Return False
	EndIf
	ModConfigLoadStatus = ModConfigAlias.ModConfigLoadStatus
	Return ModConfigAlias.DecayStagesReady()
EndFunction

Bool Function DecayStageHoursOrdered()
	If !ModConfigAlias
		Return False
	EndIf
	Return ModConfigAlias.DecayStageHoursOrdered()
EndFunction

String Function GetDecayStageName(Int aiStage)
	If !ModConfigAlias
		Return ""
	EndIf
	Return ModConfigAlias.GetDecayStageName(aiStage)
EndFunction

Float Function GetDecayStageTintR(Int aiStage)
	If !ModConfigAlias
		Return 0.0
	EndIf
	Return ModConfigAlias.GetDecayStageTintR(aiStage)
EndFunction

Float Function GetDecayStageTintG(Int aiStage)
	If !ModConfigAlias
		Return 0.0
	EndIf
	Return ModConfigAlias.GetDecayStageTintG(aiStage)
EndFunction

Float Function GetDecayStageTintB(Int aiStage)
	If !ModConfigAlias
		Return 0.0
	EndIf
	Return ModConfigAlias.GetDecayStageTintB(aiStage)
EndFunction

Float Function GetDecayStageTintA(Int aiStage)
	If !ModConfigAlias
		Return 0.0
	EndIf
	Return ModConfigAlias.GetDecayStageTintA(aiStage)
EndFunction

Float Function GetDecayStageStartHours(Int aiStage)
	If !ModConfigAlias
		Return -1.0
	EndIf
	Return ModConfigAlias.GetDecayStageStartHours(aiStage)
EndFunction

Bool Function GetDecayStageAllScars(Int aiStage)
	If !ModConfigAlias
		Return False
	EndIf
	Return ModConfigAlias.GetDecayStageAllScars(aiStage)
EndFunction

Int Function ResolveDecayStageFromElapsedHours(Float afElapsedHours)
	If !ModConfigAlias
		Return -1
	EndIf
	Return ModConfigAlias.ResolveDecayStageFromElapsedHours(afElapsedHours)
EndFunction

Int Function FillDecayStageSkins(Int aiStage, String[] outTemplates)
	If !ModConfigAlias
		Return 0
	EndIf
	Return ModConfigAlias.FillDecayStageSkins(aiStage, outTemplates)
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

; Credited knife kill only — upsert FormID + kill game-time; lastStage = -1 (needs apply).
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

; Stage for a stamped kill from kill game-time. -1 if unknown / stages not ready.
Int Function ResolveDecayStageForKill(Int formId)
	If !DecayStagesReady()
		Return -1
	EndIf
	Float killTime = GetDecayKillGameTime(formId)
	If killTime < 0.0
		Return -1
	EndIf
	Float elapsedHours = (Utility.GetCurrentGameTime() - killTime) * 24.0
	Return ResolveDecayStageFromElapsedHours(elapsedHours)
EndFunction

PickmansWhisperDesperateRenameScript Function DesperateRename()
	Return (Self as Quest) as PickmansWhisperDesperateRenameScript
EndFunction

; --- Slice G — bed gift callbacks (shared Main APIs only; orchestration on BedGift)

; BedGift status → shared debug toast path (status string owned by BedGiftScript).
Function OnBedGiftStatus(String reason)
	ToastDebug("PW bed: " + reason)
EndFunction

; --- Slice H — corpse decay overlays (façade) ----------------------------------

PickmansWhisperCorpseDecayScript Function CorpseDecay()
	Return (Self as Quest) as PickmansWhisperCorpseDecayScript
EndFunction

PickmansWhisperTargetScanScript Function TargetScan()
	Return (Self as Quest) as PickmansWhisperTargetScanScript
EndFunction

; --- Slice H P5 — player buffs (façade) -----------------------------------------

PickmansWhisperBuffTrackerScript Function BuffTracker()
	Return (Self as Quest) as PickmansWhisperBuffTrackerScript
EndFunction

PickmansWhisperBeatBeforeKillScript Function BeatBeforeKill()
	Return (Self as Quest) as PickmansWhisperBeatBeforeKillScript
EndFunction

; --- Slice H P0.1 — decay wound lab (façade) ------------------------------------

PickmansWhisperDecayWoundLabScript Function DecayWoundLab()
	Return (Self as Quest) as PickmansWhisperDecayWoundLabScript
EndFunction

Function DebugSpawnWoundLabCorpse()
	PickmansWhisperDecayWoundLabScript lab = DecayWoundLab()
	If lab
		lab.DebugSpawnWoundLabCorpse()
	Else
		DiagNotify("Pickman's Whisper\n\nDecayWoundLab script missing on Main quest.\nReinstall / rebuild PickmansWhisper.esp")
	EndIf
EndFunction

Function DebugClearWoundLabCorpse()
	PickmansWhisperDecayWoundLabScript lab = DecayWoundLab()
	If lab
		lab.DebugClearWoundLabCorpse()
	Else
		DiagNotify("Pickman's Whisper\n\nDecayWoundLab script missing on Main quest.")
	EndIf
EndFunction

Function DebugApplyWoundLabOverlays()
	PickmansWhisperDecayWoundLabScript lab = DecayWoundLab()
	If lab
		lab.DebugApplyWoundLabOverlays()
	Else
		DiagNotify("Pickman's Whisper\n\nDecayWoundLab script missing on Main quest.")
	EndIf
EndFunction

Function DebugApplyAllWoundLabOverlays()
	PickmansWhisperDecayWoundLabScript lab = DecayWoundLab()
	If lab
		lab.DebugApplyAllWoundLabOverlays()
	Else
		DiagNotify("Pickman's Whisper\n\nDecayWoundLab script missing on Main quest.")
	EndIf
EndFunction

Function DebugApplySkinLabOverlays()
	PickmansWhisperDecayWoundLabScript lab = DecayWoundLab()
	If lab
		lab.DebugApplySkinLabOverlays()
	Else
		DiagNotify("Pickman's Whisper\n\nDecayWoundLab script missing on Main quest.")
	EndIf
EndFunction

Function DebugApplyAllSkinLabOverlays()
	PickmansWhisperDecayWoundLabScript lab = DecayWoundLab()
	If lab
		lab.DebugApplyAllSkinLabOverlays()
	Else
		DiagNotify("Pickman's Whisper\n\nDecayWoundLab script missing on Main quest.")
	EndIf
EndFunction

Function DebugApplyAllScarLabOverlays()
	PickmansWhisperDecayWoundLabScript lab = DecayWoundLab()
	If lab
		lab.DebugApplyAllScarLabOverlays()
	Else
		DiagNotify("Pickman's Whisper\n\nDecayWoundLab script missing on Main quest.")
	EndIf
EndFunction

Function DebugApplyDecayStageLab()
	PickmansWhisperDecayWoundLabScript lab = DecayWoundLab()
	If lab
		lab.DebugApplyDecayStageLab()
	Else
		DiagNotify("Pickman's Whisper\n\nDecayWoundLab script missing on Main quest.")
	EndIf
EndFunction

Function DebugApplyFaceLabOverlays()
	PickmansWhisperDecayWoundLabScript lab = DecayWoundLab()
	If lab
		lab.DebugApplyFaceLabOverlays()
	Else
		DiagNotify("Pickman's Whisper\n\nDecayWoundLab script missing on Main quest.")
	EndIf
EndFunction

Function DebugApplyAllFaceLabOverlays()
	PickmansWhisperDecayWoundLabScript lab = DecayWoundLab()
	If lab
		lab.DebugApplyAllFaceLabOverlays()
	Else
		DiagNotify("Pickman's Whisper\n\nDecayWoundLab script missing on Main quest.")
	EndIf
EndFunction

String Function PickTrustLine()
	If TrustLineCount <= 0 || !TrustLines
		LoadTrustLines()
	EndIf
	If TrustLineCount <= 0
		Debug.Trace("PickmansWhisper: ERROR PickTrustLine — TrustLines bank empty")
		Return ""
	EndIf
	Return TrustLines[Utility.RandomInt(0, TrustLineCount - 1)]
EndFunction

String Function PickHungerLine()
	If HungerLineCount <= 0 || !HungerLines
		LoadHungerLines()
	EndIf
	If HungerLineCount <= 0
		Debug.Trace("PickmansWhisper: ERROR PickHungerLine — HungerLines bank empty")
		Return ""
	EndIf
	Return HungerLines[Utility.RandomInt(0, HungerLineCount - 1)]
EndFunction

String Function PickPraiseLine()
	If PraiseLineCount <= 0 || !PraiseLines
		LoadPraiseLines()
	EndIf
	If PraiseLineCount <= 0
		Debug.Trace("PickmansWhisper: ERROR PickPraiseLine — PraiseLines bank empty")
		Return ""
	EndIf
	Return PraiseLines[Utility.RandomInt(0, PraiseLineCount - 1)]
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
	If VoiceAlias
		out = VoiceAlias.TrimString(out)
	EndIf
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
	If line == "" || !VoiceAlias || !VoiceAlias.IsVoiceEnabled()
		Return
	EndIf
	If !VoiceAlias || !VoiceAlias.IsVoiceWeaponReady()
		Return
	EndIf
	Float now = Utility.GetCurrentRealTime()
	If (now - VoiceAlias.LastPraiseToastRealTime) < VoiceAlias.PRAISE_TOAST_COOLDOWN
		Return
	EndIf
	VoiceAlias.LastPraiseToastRealTime = now
	; Praise may fire mid-combat; allow even if menus briefly steal focus
	VoiceAlias.ShowVoiceToast(line)
	Debug.Trace("PickmansWhisper: praise | " + line)
EndFunction

; Trust / Hunger / Praise banks — files-only via VoiceAlias.LoadStageBank (no builtins).
Function LoadTrustLines()
	TrustLines = new String[LINE_FILE_MAX]
	TrustLineCount = 0
	If !VoiceAlias
		Debug.Trace("PickmansWhisper: ERROR LoadTrustLines — VoiceAlias unbound")
		Debug.Notification("Pickman's Whisper: VoiceAlias unbound — rebuild esp")
		Return
	EndIf
	TrustLineCount = VoiceAlias.LoadStageBank("TrustLines.txt", TrustLines)
	If TrustLineCount <= 0
		Debug.Trace("PickmansWhisper: ERROR TrustLines.txt — " + VoiceAlias.GetLastStageLoadStatus())
	Else
		Debug.Trace("PickmansWhisper: trust lines ready (" + TrustLineCount + ")")
	EndIf
EndFunction

Function LoadHungerLines()
	HungerLines = new String[LINE_FILE_MAX]
	HungerLineCount = 0
	If !VoiceAlias
		Debug.Trace("PickmansWhisper: ERROR LoadHungerLines — VoiceAlias unbound")
		Debug.Notification("Pickman's Whisper: VoiceAlias unbound — rebuild esp")
		Return
	EndIf
	HungerLineCount = VoiceAlias.LoadStageBank("HungerLines.txt", HungerLines)
	If HungerLineCount <= 0
		Debug.Trace("PickmansWhisper: ERROR HungerLines.txt — " + VoiceAlias.GetLastStageLoadStatus())
	Else
		Debug.Trace("PickmansWhisper: hunger lines ready (" + HungerLineCount + ")")
	EndIf
EndFunction

Function LoadPraiseLines()
	PraiseLines = new String[LINE_FILE_MAX]
	PraiseLineCount = 0
	If !VoiceAlias
		Debug.Trace("PickmansWhisper: ERROR LoadPraiseLines — VoiceAlias unbound")
		Debug.Notification("Pickman's Whisper: VoiceAlias unbound — rebuild esp")
		Return
	EndIf
	PraiseLineCount = VoiceAlias.LoadStageBank("PraiseLines.txt", PraiseLines)
	If PraiseLineCount <= 0
		Debug.Trace("PickmansWhisper: ERROR PraiseLines.txt — " + VoiceAlias.GetLastStageLoadStatus())
	Else
		Debug.Trace("PickmansWhisper: praise lines ready (" + PraiseLineCount + ")")
	EndIf
EndFunction

Function LoadLineBanks()
	If ModConfigAlias
		ModConfigAlias.LoadModConfig()
	Else
		Debug.Trace("PickmansWhisper: ERROR LoadLineBanks — ModConfigAlias unbound")
		Debug.Notification("Pickman's Whisper: ModConfigAlias unbound — rebuild esp")
	EndIf
	If VoiceAlias
		VoiceAlias.LoadVoiceBanks()
	Else
		Debug.Trace("PickmansWhisper: ERROR LoadLineBanks — VoiceAlias unbound")
		Debug.Notification("Pickman's Whisper: VoiceAlias unbound — rebuild esp")
	EndIf
	LoadTrustLines()
	LoadHungerLines()
	LoadPraiseLines()
	LoadTargetOverrides()
EndFunction

; --- Hunger --------------------------------------------------------------------

Function StartHungerPoll()
	EnsureHungerSpell()
	If LastHungerPollGameTime <= 0.0
		LastHungerPollGameTime = Utility.GetCurrentGameTime()
	EndIf
	CancelTimer(TIMER_HUNGER)
	NextHungerRealTime = 0.0
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
	;If !IsHungerUnlocked()
	;	LastHungerPollGameTime = Utility.GetCurrentGameTime()
	;	HungerWasSated = False
	;	SyncHungerAddictionSpell()
	;	Return
	;EndIf
	;If Utility.IsInMenuMode()
	;	Return
	;EndIf

	;Float now = Utility.GetCurrentGameTime()
	;If LastHungerPollGameTime <= 0.0
	;	LastHungerPollGameTime = now
	;EndIf
	;Float last = LastHungerPollGameTime

	;Bool satedNow = IsHungerSated()
	;If HungerWasSated && !satedNow
	;	If ModConfigAlias && ModConfigAlias.HungerWithdrawalToast != ""
	;		ToastHungerLine(ModConfigAlias.HungerWithdrawalToast)
	;	Else
	;		Debug.Trace("PickmansWhisper: ERROR hunger withdrawal toast skipped — hungerWithdrawalToast missing/empty")
	;	EndIf
	;	ApplyHungerDelta(20.0, "withdrawal-onset")
	;EndIf

	;If !satedNow
	;	; Unused knife-time: blade owned (or bond active) without recent activity.
	;	; Slice A treats LastKnifeActivityGameTime as bond start until B updates it.
	;	Float gainStart = last
	;	If SatedUntilGameTime > gainStart
	;		If now > SatedUntilGameTime
	;			gainStart = SatedUntilGameTime
	;		Else
	;			gainStart = now
	;		EndIf
	;	EndIf
	;	Float hours = (now - gainStart) * 24.0
	;	If hours > 0.0
	;		ApplyHungerDelta(hours * GetHungerTimeGainPerHour(), "unused-knife-time")
	;	EndIf
	;EndIf

	;HungerWasSated = satedNow
	;LastHungerPollGameTime = now
	;SyncHungerAddictionSpell()
	;RefreshHungerPanel(False)
	; Hunger timer is proven live — drive notice poll from here too
	;If VoiceAlias
	;	VoiceAlias.MaybeSpeakNoticeLine()
	;EndIf
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
		If line != ""
			ToastHungerLine(line)
		Else
			Debug.Trace("PickmansWhisper: ERROR MaybeToastHungerBand — HungerLines empty (band=" + band + ")")
		EndIf
	ElseIf after < 25.0 && LastHungerBand > 0
		LastHungerBand = 0
	EndIf
EndFunction

; --- Knife kills (Slice B) -----------------------------------------------------
; GoE FindActors + IsDead() like Necromantic. Driven by bond poll (proven) + KillerScan timer.

String Function EnsureCombatKillHooks()
	If !PlayerRef
		PlayerRef = Game.GetPlayer()
	EndIf
	; StartKillerScanLoop()
	String status = "scan WORLD+T16 tagged=" + BladeTaggedCount
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
	ToastDebug("PW world scan armed [" + DEBUG_BUILD + "]")
	Debug.Trace("PickmansWhisper: world scan armed " + DEBUG_BUILD)
EndFunction

; Legacy name — redirects to KillerScan bus.
Function StartKillScanLoop()
	CancelTimer(TIMER_KILL_SCAN)
	CancelTimer(TIMER_DECAY_SYNC)
	; StartKillerScanLoop()
EndFunction

; Knife credit from KillerScan snapshot — no FindActors, no LooksMenu.
Function ProcessKnifeCreditFromKillerScan(PickmansWhisperKillerScanScript scan)
	If !scan
		Return
	EndIf
	If !PlayerRef
		PlayerRef = Game.GetPlayer()
	EndIf
	If !PlayerRef
		Return
	EndIf

	Actor ct = scan.CombatTarget
	TrackLivingNear(ct)

	Actor[] alive = scan.ScanAlive
	Actor[] detecting = scan.ScanDetecting
	Int aliveCount = scan.ScanAliveCount
	Int detectCount = scan.ScanDetectCount

	Int i = 0
	Int n = aliveCount
	If n > 24
		n = 24
	EndIf
	While i < n
		Actor ak = None
		If alive
			ak = alive[i]
		EndIf
		TrackLivingNear(ak)
		i += 1
	EndWhile

	i = 0
	n = detectCount
	If n > 24
		n = 24
	EndIf
	While i < n
		Actor ak = None
		If detecting
			ak = detecting[i]
		EndIf
		TrackLivingNear(ak)
		i += 1
	EndWhile

	; Kill detection itself is event-driven now (HandleBladeHit registers OnDeath on a
	; confirmed hit; HandleNPCDeath credits + cleans up). This sweep only evicts blade-tagged
	; actors who were hit but never died and wandered off, so their registration doesn't leak.
	ReconcileBladeTagged()
EndFunction

; Overlay sync moved to CorpseDecay (OnKillerScan → CallFunctionNoWait). Kept for MCM/debug callers.
Function SyncNearbyKnifeDecayOverlays()
	PickmansWhisperCorpseDecayScript decay = CorpseDecay()
	If decay
		decay.SyncOverlaysFromKillerScanSnapshot()
	Else
		Debug.Trace("PickmansWhisper: ERROR SyncNearbyKnifeDecayOverlays — CorpseDecay missing")
	EndIf
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

Function TrackLivingNear(Actor ak)
	; Ambient sighting for WasFriendlySeen (knife feature hostility-history), AND
	; the ONLY place that proactively arms hit detection. RegisterForHitEvent is otherwise
	; only ever called reactively, inside HandleBladeHit, to re-arm AFTER a hit already
	; landed — nothing else registers a fresh, never-hit actor, so without this call here
	; Actor.OnHit can never fire for a target's first strike (confirmed live: a whole
	; session produced zero "blade-tagged" traces — HandleBladeHit never ran at all for
	; any kill, because nothing had armed hit-watching on the victim beforehand). This is
	; exactly the ambient sweep that already runs for every nearby actor every KillerScan
	; tick, so it is the natural place to close that gap. Not gated on IsBladeEquipped
	; here — HandleBladeHit and HandleNPCDeath both independently re-check blade state
	; live, so gating here would only be an unverified micro-optimization, not a
	; correctness requirement; HitArmed dedup is what actually keeps this cheap.
	If !ak || ak == PlayerRef || ak.IsDead() || ak.IsDisabled()
		Return
	EndIf

	; Bed hallucination / wound lab PlaceAtMe bodies must never enter kill-watch.
	If IsNonGameplayCorpse(ak)
		Return
	EndIf

	; Hard gate — stamp friendly / arm hits only for mod-eligible NPCs.
	If !IsValidTarget(ak)
		Return
	EndIf

	; Stamp disposition while still living — before the player turns a settler hostile.
	If PlayerRef && ak.IsHostileToActor(PlayerRef)
		; Hostile when first/ongoing seen — do not mark friendly
	Else
		NoteFriendlySeen(ak)
	EndIf

	If !WasHitArmed(ak)
		Debug.Trace("Pickman's Whisper: RegisterForHitEvent")
		RegisterForHitEvent(ak, PlayerRef)
		MarkHitArmed(ak)
	EndIf
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
	If !VoiceAlias
		LastTargetOverridesStatus = "ERROR: VoiceAlias unbound (cannot resolve config path)"
		Debug.Trace("PickmansWhisper: ERROR LoadTargetOverrides — VoiceAlias unbound")
		Return
	EndIf
	String path = VoiceAlias.NoticeConfigPath()
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
		String line = raw[i]
		If VoiceAlias
			line = VoiceAlias.TrimString(raw[i])
		EndIf
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
				String key = GardenOfEden.SubStr(line, 0, eq)
				String val = GardenOfEden.SubStr(line, eq + 1, -1)
				If VoiceAlias
					key = VoiceAlias.TrimString(key)
					val = VoiceAlias.TrimString(val)
				EndIf
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

Function EnsureBladeTaggedList()
	If !BladeTagged || BladeTagged.Length == 0
		BladeTagged = new Actor[24]
		BladeTaggedCount = 0
	EndIf
EndFunction

Bool Function WasBladeTagged(Actor ak)
	If !ak
		Return False
	EndIf
	EnsureBladeTaggedList()
	Int i = 0
	While i < BladeTaggedCount
		If BladeTagged[i] == ak
			Return True
		EndIf
		i += 1
	EndWhile
	Return False
EndFunction

; Add-only — caller has already decided to register OnDeath; this just remembers we did,
; so a repeat hit on the same actor doesn't re-register. Actor refs (not FormIDs) so the
; reconcile sweep (ReconcileBladeTagged) can check distance/dead state directly.
Function MarkBladeTagged(Actor ak)
	If !ak || WasBladeTagged(ak)
		Return
	EndIf
	EnsureBladeTaggedList()
	If BladeTaggedCount >= BLADE_TAGGED_MAX
		Int j = 0
		While j < BLADE_TAGGED_MAX - 1
			BladeTagged[j] = BladeTagged[j + 1]
			j += 1
		EndWhile
		BladeTaggedCount = BLADE_TAGGED_MAX - 1
	EndIf
	BladeTagged[BladeTaggedCount] = ak
	BladeTaggedCount += 1
	Debug.Trace("PickmansWhisper: blade-tagged victim id=" + ak.GetFormID())
EndFunction

; Sole cleanup point — pairs the tag-list removal with the actual engine unregister, so
; OnDeath registrations never outlive our own bookkeeping (confirmed live: the old
; the old tagging code called RegisterForRemoteEvent liberally but never once
; called UnregisterForRemoteEvent anywhere in this file — every tagged actor stayed
; registered for the rest of the session, dead, fled, or otherwise). Called from
; HandleNPCDeath (the normal path — death was just processed) and ReconcileBladeTagged
; (the safety-valve path — tagged but never died, wandered off).
Function ForgetBladeTagged(Actor ak)
	If !ak
		Return
	EndIf
	UnregisterForRemoteEvent(ak, "OnDeath")
	Int i = 0
	While i < BladeTaggedCount
		If BladeTagged[i] == ak
			Int j = i
			While j < BladeTaggedCount - 1
				BladeTagged[j] = BladeTagged[j + 1]
				j += 1
			EndWhile
			BladeTagged[BladeTaggedCount - 1] = None
			BladeTaggedCount -= 1
			Return
		EndIf
		i += 1
	EndWhile
EndFunction

; Safety-valve sweep — the primary cleanup path is HandleNPCDeath (fires the moment a
; tagged victim's death is processed). This only catches actors who were hit and tagged
; but never died (fled, player broke off, etc.) — evicts + unregisters them once they're
; out of range so the registration doesn't linger for the rest of the session.
Function ReconcileBladeTagged()
	If BladeTaggedCount <= 0 || !PlayerRef
		Return
	EndIf
	PickmansWhisperTargetScanScript ts = TargetScan()
	If !ts
		Debug.Trace("PickmansWhisper: ERROR ReconcileBladeTagged — TargetScan missing")
		Return
	EndIf
	Float watchR = ts.KILL_WATCH_RADIUS
	Int i = BladeTaggedCount - 1
	While i >= 0
		Actor ak = BladeTagged[i]
		If !ak || ak.IsDead() || !ak.Is3DLoaded() || PlayerRef.GetDistance(ak) > watchR
			ForgetBladeTagged(ak)
		EndIf
		i -= 1
	EndWhile
EndFunction

Function EnsureHitArmedList()
	If !HitArmed || HitArmed.Length == 0
		HitArmed = new Actor[32]
		HitArmedCount = 0
	EndIf
EndFunction

Bool Function WasHitArmed(Actor ak)
	If !ak
		Return False
	EndIf
	EnsureHitArmedList()
	Int i = 0
	While i < HitArmedCount
		If HitArmed[i] == ak
			Return True
		EndIf
		i += 1
	EndWhile
	Return False
EndFunction

Function MarkHitArmed(Actor ak)
	If !ak || WasHitArmed(ak)
		Return
	EndIf
	EnsureHitArmedList()
	If HitArmedCount >= HIT_ARMED_MAX
		Int j = 0
		While j < HIT_ARMED_MAX - 1
			HitArmed[j] = HitArmed[j + 1]
			j += 1
		EndWhile
		HitArmedCount = HIT_ARMED_MAX - 1
	EndIf
	HitArmed[HitArmedCount] = ak
	HitArmedCount += 1
EndFunction

Function HandleBladeHit(ObjectReference akTarget, ObjectReference akAggressor, Form akSource)
	Actor victim = akTarget as Actor
	Actor agg = akAggressor as Actor
	
	Debug.Trace("Pickman's Whisper: HandleBladeHit 0")

	If !victim || agg != PlayerRef
		If victim && IsBladeEquipped()
			RegisterForHitEvent(victim, PlayerRef)
		EndIf
		Return
	EndIf
	If !IsPickmansBladeForm(akSource) || !IsBladeEquipped()
		Debug.Trace("PickmansWhisper: HandleBladeHit reject | hit not with blade; drawn=" + GetDrawnWeaponDebugName())
		If !victim.IsDead()
			RegisterForHitEvent(victim, PlayerRef)
		EndIf
		Return
	EndIf

	Debug.Trace("Pickman's Whisper: HandleBladeHit 1")

	; Stamp disposition while we can — same rule as TrackLivingNear (raiders already hostile
	; at hit-time still fail the knife WasFriendlySeen feature check; a stealth kill on someone
	; who never got the chance to react correctly passes).
	If !PlayerRef || !victim.IsHostileToActor(PlayerRef)
		NoteFriendlySeen(victim)
	EndIf
	If victim.IsDead()
		Debug.Trace("Pickman's Whisper: HandleBladeHit 2")

		HandleNPCDeath(victim, PlayerRef, "hit-dead")
		Return
	EndIf
	If !WasBladeTagged(victim)
		Debug.Trace("Pickman's Whisper: HandleBladeHit 3")

		RegisterForRemoteEvent(victim, "OnDeath")
		MarkBladeTagged(victim)
	EndIf
	RegisterForHitEvent(victim, PlayerRef)
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

; Hard eligibility — "this NPC can never be a Pickman's Whisper target."
; Feature paths compose their own checks (IsDead, WasFriendlySeen, distance, cooldown).
; Bool only; every reject Traces. No Autovar reason side-channel.
Bool Function IsValidTarget(Actor ak)
	If !ak || ak == PlayerRef
		Debug.Trace("PickmansWhisper: target reject | no actor")
		Debug.Notification("PickmansWhisper: target reject | no actor")
		Return False
	EndIf
	Int id = ak.GetFormID()
	If ak.IsDisabled()
		Debug.Trace("PickmansWhisper: target reject | disabled id=" + id)
		Debug.Notification("PickmansWhisper: target reject | disabled id=" + id)
		Return False
	EndIf
	If IsChildNpc(ak) && !IsChildTargetAllowed()
		Debug.Trace("PickmansWhisper: target reject | child id=" + id)
		Debug.Notification("PickmansWhisper: target reject | child id=" + id)
		Return False
	EndIf
	If ak.IsPlayerTeammate()
		Debug.Trace("PickmansWhisper: target reject | teammate id=" + id)
		Debug.Notification("PickmansWhisper: target reject | teammate id=" + id)
		Return False
	EndIf
	If IsStoryEssential(ak)
		Debug.Trace("PickmansWhisper: target reject | essential (story NPC) id=" + id)
		Debug.Notification("PickmansWhisper: target reject | essential (story NPC) id=" + id)
		Return False
	EndIf
	If !IsHumanNpc(ak)
		Debug.Trace("PickmansWhisper: target reject | not human NPC id=" + id)
		Debug.Notification("PickmansWhisper: target reject | not human NPC id=" + id)
		Return False
	EndIf
	If !IsAdultFemale(ak)
		Debug.Trace("PickmansWhisper: target reject | not adult female id=" + id)
		Debug.Notification("PickmansWhisper: target reject | not adult female id=" + id)
		Return False
	EndIf
	Return True
EndFunction

; Slice G / H — KillSilent(player) on PlaceAtMe bodies must never satiate hunger.
; Set during KillBedCorpse / KillLabCorpse (BedCorpse/LabCorpse assigned after kill).
Bool KnifeKillCreditSuppressed = False

Function SetKnifeKillCreditSuppressed(Bool abSuppressed)
	KnifeKillCreditSuppressed = abSuppressed
EndFunction

; True for bed-hallucination / wound-lab actors (after they are assigned).
; Multi-feature gate — queries each feature script; no BedGift façade on Main.
Bool Function IsNonGameplayCorpse(Actor ak)
	If !ak
		Return False
	EndIf
	PickmansWhisperBedGiftScript bed = (Self as Quest) as PickmansWhisperBedGiftScript
	If bed && bed.IsBedGiftCorpse(ak)
		Return True
	EndIf
	PickmansWhisperDecayWoundLabScript lab = DecayWoundLab()
	If lab && lab.IsWoundLabCorpse(ak)
		Return True
	EndIf
	Return False
EndFunction

; Sole credit-and-cleanup entry point for a confirmed NPC death — called either directly
; from HandleBladeHit (the blade hit landed on an already-dead actor) or from the real
; Actor.OnDeath event (the common case: death happens after the hit that tagged them).
; Cleanup (ForgetBladeTagged) runs unconditionally up front, before any credit decision —
; once we're evaluating this death we're done tracking the actor regardless of outcome.
; Shared rejection path for HandleNPCDeath's gate — collapses the "set reason, maybe
; toast, always trace" pattern each gate repeated. abToastDebug=False for reasons that
; are routine/expected (non-gameplay corpse, cooldown) rather than something worth a
; debug toast every time.
Function RejectKill(String reason, Bool abToastDebug = True)
	If abToastDebug
		ToastDebug("PW debug: kill ignored — " + reason)
	EndIf
	Debug.Trace("PickmansWhisper: kill ignored — " + reason)
EndFunction

; DELETE THIS
; Sole credit-and-cleanup entry point for a confirmed NPC death — called either directly
; from HandleBladeHit (the blade hit landed on an already-dead actor) or from the real
; Actor.OnDeath event (the common case: death happens after the hit that tagged them).
; Cleanup (ForgetBladeTagged) runs unconditionally up front, before any credit decision —
; once we're evaluating this death we're done tracking the actor regardless of outcome.
Function HandleNPCDeath(Actor victim, Actor akKiller, String path)
	Debug.Trace("Pickman's Whisper: HandleNPCDeath")
	Debug.Notification("Pickman's Whisper: HandleNPCDeath")
	If !victim
		Return
	EndIf
	Int vid = victim.GetFormID()
	ToastHumanKillDetected(victim, path)
	ForgetBladeTagged(victim)
	If vid == LastHandledKillId
		Return
	EndIf
	; Bed gift / wound lab KillSilent(player) must not clear hunger (docs: no satiation).
	If KnifeKillCreditSuppressed || IsNonGameplayCorpse(victim)
		RejectKill("non-gameplay corpse (bed/lab)", False)
		NoteBackgroundDead(vid)
		Return
	EndIf
	If akKiller && akKiller != PlayerRef
		RejectKill("killer was not player")
		Return
	EndIf
	; Drawn weapon must be Pickman's Blade right now. No finish window, no hit-tag waiver.
	String drawn = GetDrawnWeaponDebugName()
	If !IsBladeEquipped()
		RejectKill("not blade; drawn=" + drawn)
		Return
	EndIf
	If !IsValidTarget(victim)
		RejectKill("not a valid target")
		Return
	EndIf
	; Knife feature: must have been seen non-hostile while alive (raiders fail; settlers you aggro still pass).
	If !WasFriendlySeen(victim)
		RejectKill("hostile / not seen friendly")
		Return
	EndIf
	Float now = Utility.GetCurrentRealTime()
	If (now - LastKnifeKillRealTime) < KNIFE_KILL_COOLDOWN
		RejectKill("cooldown", False)
		Return
	EndIf
	LastKnifeKillRealTime = now
	LastHandledKillId = vid
	Debug.Trace("PickmansWhisper: kill ok satiated; drawn=" + drawn + " id=" + vid)
	If !BondStarted
		StartBond("knife-kill")
	EndIf
	ProcessKnifeKill(victim)
EndFunction

Function ProcessKnifeKill(Actor victim)
	; Final gate — never praise/sate unless blade is still the drawn weapon
	If !IsBladeEquipped()
		String abortReason = "abort satiate; drawn=" + GetDrawnWeaponDebugName()
		ToastDebug("PW debug: " + abortReason)
		Debug.Trace("PickmansWhisper: " + abortReason)
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
	; Slice H P2 — stamp kill clock only. LooksMenu sync is TIMER_DECAY_SYNC
	; (Utility.Wait inside ApplyTinted* must never run on this call stack).
	If victim
		StampDecayKill(victim)
		; MCM Victims / decay row — camera often misses the body right after the kill.
		NoteVictimsAimActor(victim)
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
	If !ModConfigAlias || !ModConfigAlias.NamedKillToast
		Return False
	EndIf
	If !VoiceAlias || !VoiceAlias.IsVoiceEnabled()
		Return True
	EndIf
	If !VoiceAlias || !VoiceAlias.IsVoiceWeaponReady()
		Return True
	EndIf
	String line = VoiceAlias.ApplyNamePlaceholder(ModConfigAlias.NamedKillToast, overrideName)
	If !line || GardenOfEden.StrLength(line) < 1
		Return False
	EndIf
	Float now = Utility.GetCurrentRealTime()
	If (now - VoiceAlias.LastPraiseToastRealTime) < VoiceAlias.PRAISE_TOAST_COOLDOWN
		Return True
	EndIf
	VoiceAlias.LastPraiseToastRealTime = now
	Int mode = VoiceAlias.GetVoiceDeliveryMode()
	If mode != 1
		VoiceAlias.ShowVoiceToast(line)
	EndIf
	If mode != 2
		If ModConfigAlias.NamedKillAudio
			VoiceAlias.PlayWhisperXwmByFile(ModConfigAlias.NamedKillAudio)
		ElseIf mode == 1
			; Audio-only with no audio key — still deliver toast so the kill is not silent.
			VoiceAlias.ShowVoiceToast(line)
			Debug.Trace("PickmansWhisper: namedKillAudio missing — toast fallback for audio-only mode")
		EndIf
	EndIf
	Debug.Trace("PickmansWhisper: named kill voice | " + line)
	Return True
EndFunction

; Slice H P4 — Cannibal-perk nag at Black Putrefaction (max decay stage). Called from
; CorpseDecay's ambient KillerScan sweep for every tracked corpse currently AT that stage
; (not just on transition), so this owns its own once-per-game-hour throttle rather than
; relying on SyncDecayForKnifeCorpse's stage-changed gate. One shared cooldown across all
; ripe corpses — several corpses hitting the cap at once should not stack toasts.
Function MaybeToastEatRipeCorpse(Actor akCorpse)
	If !akCorpse
		Return
	EndIf
	If !ModConfigAlias || !ModConfigAlias.EatRipeCorpseToast || GardenOfEden.StrLength(ModConfigAlias.EatRipeCorpseToast) < 1
		Debug.Trace("PickmansWhisper: eat-ripe-corpse skip | no eatRipeCorpseToast (ModConfig not loaded / key empty)")
		Return
	EndIf
	If !PlayerHasCannibalPerk()
		Debug.Trace("PickmansWhisper: eat-ripe-corpse skip | player lacks Cannibal perk")
		Return
	EndIf
	Float now = Utility.GetCurrentGameTime()
	If (now - LastEatRipeCorpseToastGameTime) < (EAT_RIPE_CORPSE_TOAST_MIN_GAME_HOURS / 24.0)
		Debug.Trace("PickmansWhisper: eat-ripe-corpse skip | cooldown formId=" + akCorpse.GetFormID())
		Return
	EndIf
	String overrideName = GetVictimOverrideName(akCorpse)
	If !overrideName
		overrideName = "her"
	EndIf
	If !VoiceAlias
		Debug.Trace("PickmansWhisper: eat-ripe-corpse skip | VoiceAlias unbound")
		Return
	EndIf
	String line = VoiceAlias.ApplyNamePlaceholder(ModConfigAlias.EatRipeCorpseToast, overrideName)
	If !line || GardenOfEden.StrLength(line) < 1
		Debug.Trace("PickmansWhisper: eat-ripe-corpse skip | empty line after placeholder")
		Return
	EndIf
	LastEatRipeCorpseToastGameTime = now
	Debug.Notification(line)
	Debug.Trace("PickmansWhisper: eat-ripe-corpse toast | " + line)
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

; Net ModValue/temp delta vs base. Negative = reduced vs GetBaseValue.
Float Function GetSpecialModDelta(ActorValue av)
	If !PlayerRef || !av
		Return 0.0
	EndIf
	Return PlayerRef.GetValue(av) - PlayerRef.GetBaseValue(av)
EndFunction

; Hard floor: never ModValue(-1) when AGI or CHA is already -2 (or worse) vs base.
Bool Function IsSpecialModAtMinusTwoFloor(ActorValue av)
	Return GetSpecialModDelta(av) <= -2.0
EndFunction

; Align flags with depth after load / script updates so Sync never ModValue twice.
Function ReconcileHungerSpecialPenaltyFlags()
	If HungerSpecialPenaltyDepth < 0
		HungerSpecialPenaltyDepth = 0
	EndIf
	If HungerSpecialPenaltyDepth > 1
		; Cap bookkeeping at 1 going forward; extras need RepairHungerSpecialStacks.
		Debug.Trace("PickmansWhisper: hunger SPECIAL depth was " + HungerSpecialPenaltyDepth + " — capping bookkeeping at 1")
		HungerSpecialPenaltyDepth = 1
	EndIf
	If HungerSpecialPenaltyDepth > 0
		HungerStatPenaltyApplied = True
	ElseIf HungerStatPenaltyApplied
		; Pre-depth saves: flag said applied — assume exactly one live ModValue pair.
		HungerSpecialPenaltyDepth = 1
		Debug.Trace("PickmansWhisper: hunger SPECIAL depth reconciled from flag → 1")
	EndIf
EndFunction

Function ApplyHungerStatPenalty()
	If !PlayerRef
		Return
	EndIf
	ReconcileHungerSpecialPenaltyFlags()
	; Idempotent — never ModValue again while depth already accounts for a live penalty.
	If HungerStatPenaltyApplied || HungerSpecialPenaltyDepth > 0 || HungerAddictionApplied
		HungerStatPenaltyApplied = True
		If HungerSpecialPenaltyDepth < 1
			HungerSpecialPenaltyDepth = 1
		EndIf
		Debug.Trace("PickmansWhisper: SPECIAL -1 skipped (already applied depth=" + HungerSpecialPenaltyDepth + ") " + FormatSpecialSnapshot())
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
	; Floor: if either SPECIAL is already -2 (or worse) vs base, do not decrement further.
	If (avAgi && IsSpecialModAtMinusTwoFloor(avAgi)) || (avCha && IsSpecialModAtMinusTwoFloor(avCha))
		HungerStatPenaltyApplied = True
		If HungerSpecialPenaltyDepth < 1
			HungerSpecialPenaltyDepth = 1
		EndIf
		Debug.Trace("PickmansWhisper: SPECIAL -1 skipped (mod already <= -2 vs base) " + FormatSpecialSnapshot() + " agiDelta=" + GetSpecialModDelta(avAgi) + " chaDelta=" + GetSpecialModDelta(avCha))
		Return
	EndIf
	If avAgi
		PlayerRef.ModValue(avAgi, -1.0)
	EndIf
	If avCha
		PlayerRef.ModValue(avCha, -1.0)
	EndIf
	HungerSpecialPenaltyDepth = 1
	HungerStatPenaltyApplied = True
	Debug.Trace("PickmansWhisper: SPECIAL -1 applied " + FormatSpecialSnapshot())
EndFunction

Function ClearHungerStatPenalty()
	If !PlayerRef
		Return
	EndIf
	ReconcileHungerSpecialPenaltyFlags()
	Int n = HungerSpecialPenaltyDepth
	If n < 1 && !HungerStatPenaltyApplied && !HungerAddictionApplied
		Return
	EndIf
	If n < 1
		n = 1
	EndIf
	ActorValue avAgi = Game.GetForm(0x000002C7) as ActorValue
	ActorValue avCha = Game.GetForm(0x000002C5) as ActorValue
	If !avAgi
		avAgi = Game.GetFormFromFile(0x000002C7, "Fallout4.esm") as ActorValue
	EndIf
	If !avCha
		avCha = Game.GetFormFromFile(0x000002C5, "Fallout4.esm") as ActorValue
	EndIf
	Int i = 0
	While i < n
		If avAgi
			PlayerRef.ModValue(avAgi, 1.0)
		EndIf
		If avCha
			PlayerRef.ModValue(avCha, 1.0)
		EndIf
		i += 1
	EndWhile
	HungerSpecialPenaltyDepth = 0
	HungerStatPenaltyApplied = False
	Debug.Trace("PickmansWhisper: SPECIAL +" + n + " restored " + FormatSpecialSnapshot())
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
	If !HungerStatPenaltyApplied && HungerSpecialPenaltyDepth <= 0
		ApplyHungerStatPenalty()
	Else
		ReconcileHungerSpecialPenaltyFlags()
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
	ReconcileHungerSpecialPenaltyFlags()
	Bool want = IsHungerUnlocked() && IsHungerAddictionSpellEnabled() && HungerLevel >= GetHungerAddictedThreshold() && !IsHungerSated()
	If want
		If !HungerStatPenaltyApplied && HungerSpecialPenaltyDepth <= 0
			ApplyHungerAddictionStandIn(!HungerAddictionApplied)
		EndIf
		HungerAddictionApplied = HungerStatPenaltyApplied || HungerSpecialPenaltyDepth > 0
		HungerStatPenaltyApplied = HungerAddictionApplied
	ElseIf HungerStatPenaltyApplied || HungerAddictionApplied || HungerSpecialPenaltyDepth > 0
		ClearHungerAddictionStandIn()
		HungerAddictionApplied = False
		Debug.Trace("PickmansWhisper: hunger withdrawal cleared")
	EndIf
EndFunction

; MCM — each click undoes one rogue AGI/CHA pair. Keeps a single legitimate penalty if still addicted.
Function RepairHungerSpecialStacks()
	; Immediate toast — proves MCM CallFunction reached the body (prior jam starved this).
	Debug.Notification("PW: SPECIAL repair running…")
	Debug.Trace("PickmansWhisper: SPECIAL repair enter")
	If !PlayerRef
		PlayerRef = Game.GetPlayer()
	EndIf
	If !PlayerRef
		DiagNotify("Pickman's Whisper\n\nNo player.")
		Return
	EndIf
	String before = FormatSpecialSnapshot()
	ActorValue avAgi = Game.GetForm(0x000002C7) as ActorValue
	ActorValue avCha = Game.GetForm(0x000002C5) as ActorValue
	If !avAgi
		avAgi = Game.GetFormFromFile(0x000002C7, "Fallout4.esm") as ActorValue
	EndIf
	If !avCha
		avCha = Game.GetFormFromFile(0x000002C5, "Fallout4.esm") as ActorValue
	EndIf
	If !avAgi || !avCha
		DiagNotify("Pickman's Whisper — Repair\n\nERROR: AGI/CHA ActorValue resolve failed.")
		Debug.Trace("PickmansWhisper: ERROR SPECIAL repair — AV missing agi=" + (avAgi as Bool) + " cha=" + (avCha as Bool))
		Return
	EndIf
	Float agiBefore = PlayerRef.GetValue(avAgi)
	Float chaBefore = PlayerRef.GetValue(avCha)
	PlayerRef.ModValue(avAgi, 1.0)
	PlayerRef.ModValue(avCha, 1.0)
	Float agiAfter = PlayerRef.GetValue(avAgi)
	Float chaAfter = PlayerRef.GetValue(avCha)
	; Do not Sync-apply here — that would ModValue(-1) again and undo the repair.
	Bool want = IsHungerUnlocked() && IsHungerAddictionSpellEnabled() && HungerLevel >= GetHungerAddictedThreshold() && !IsHungerSated()
	If want
		HungerSpecialPenaltyDepth = 1
		HungerStatPenaltyApplied = True
		HungerAddictionApplied = True
	Else
		HungerSpecialPenaltyDepth = 0
		HungerStatPenaltyApplied = False
		HungerAddictionApplied = False
	EndIf
	String msg = "Restored one AGI/CHA pair.\nBefore: " + before + "\nAfter: " + FormatSpecialSnapshot()
	msg += "\nRaw: AGI " + (agiBefore as Int) + "->" + (agiAfter as Int) + " CHA " + (chaBefore as Int) + "->" + (chaAfter as Int)
	msg += "\nDepth bookkeeping: " + HungerSpecialPenaltyDepth
	msg += "\nClick again if still short from an older stack."
	If want
		msg += "\n(Still addicted — one -1 kept in bookkeeping, not re-applied.)"
	EndIf
	If agiAfter <= agiBefore && chaAfter <= chaBefore
		msg += "\nWARNING: GetValue did not rise — SPECIAL may be locked by another mod."
	EndIf
	Debug.Trace("PickmansWhisper: SPECIAL repair click " + before + " -> " + FormatSpecialSnapshot() + " depth=" + HungerSpecialPenaltyDepth + " agi " + agiBefore + "->" + agiAfter + " cha " + chaBefore + "->" + chaAfter)
	DiagNotify("Pickman's Whisper — Repair\n\n" + msg)
EndFunction

; --- MCM -----------------------------------------------------------------------

Function OnMCMMenuOpen(String modName)
	If modName != MOD_NAME
		Return
	EndIf
	Debug.Notification("PW: MCM open — Main quest alive")
	Debug.Trace("PickmansWhisper: OnMCMMenuOpen")
	; RefreshMenu FIRST (it reloads page state from settings.ini), THEN reload
	; notice files and push status — same order as Necromantic. Loading before
	; RefreshMenu was getting wiped back to settings.ini "(not loaded)".
	EnsurePlayerCombatQuest()
	ArmRuntimeLoops() ; recovery if load hooks missed; not the sole arm path
	RefreshHungerPanel(False)
	If MCM.IsInstalled()
		MCM.RefreshMenu()
	EndIf
	If VoiceAlias
		VoiceAlias.LoadNoticeLines()
	EndIf
	RefreshDebugStatus()
	; After Debug's RefreshMenu wipe — push Victims (incl. decay) from aim cache.
	RefreshVictimsPanel(False)
EndFunction

Function OnMCMSettingChange(String modName, String id)
	If modName != MOD_NAME
		Return
	EndIf
	If id == "bKillDebugToasts:Debug"
		InvalidateDebugToastCache()
	ElseIf id == "bSniffMagicEffects:Debug"
		SyncMagicEffectSniffer()
	ElseIf id == "bAddictionSpell:Hunger" || id == "fAddictedAt:Hunger"
		SyncHungerAddictionSpell()
		RefreshHungerPanel(True)
	ElseIf id == "bVoiceToasts:Voice"
		ArmRuntimeLoops()
	ElseIf id == "iWoundLabTintPreset:WoundLab"
		PickmansWhisperDecayWoundLabScript lab = DecayWoundLab()
		If lab
			lab.ApplyWoundLabTintPreset()
		EndIf
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
		DiagNotify(msg)
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
	DiagNotify(msg)
EndFunction

Function ForceHungerAddictedTest()
	If !IsHungerUnlocked()
		DiagNotify("Pickman's Whisper — Test\n\nBond first (gallery or blade).")
		Return
	EndIf
	If !IsHungerAddictionSpellEnabled()
		DiagNotify("Pickman's Whisper — Test\n\nKnife Hunger effect is OFF in MCM.")
		Return
	EndIf
	ReconcileHungerSpecialPenaltyFlags()
	If HungerStatPenaltyApplied || HungerSpecialPenaltyDepth > 0 || HungerAddictionApplied
		ClearHungerAddictionStandIn()
	EndIf
	SatedUntilGameTime = 0.0
	HungerWasSated = False
	HungerLevel = 80.0
	LastHungerBand = 70
	HungerAddictionApplied = False
	HungerStatPenaltyApplied = False
	HungerSpecialPenaltyDepth = 0
	String before = FormatSpecialSnapshot()
	SyncHungerAddictionSpell()
	RefreshHungerPanel(True)
	String msg = "Hunger forced to 80.\nBefore: " + before + "\nAfter: " + FormatSpecialSnapshot() + "\n"
	msg += "Withdrawal flag: " + HungerStatPenaltyApplied + " depth=" + HungerSpecialPenaltyDepth
	DiagNotify("Pickman's Whisper — Test\n\n" + msg)
EndFunction

Function DebugForceBond()
	StartBond("mcm-debug")
	RefreshDebugStatus()
	DiagNotify("Pickman's Whisper\n\nBond forced. Hunger unlocked.")
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
		DiagNotify(msg)
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
		DiagNotify(msg)
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
	DiagNotify(msg)
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
	DiagNotify(msg)
EndFunction

Function DebugSatiateHunger()
	If !IsHungerUnlocked()
		DiagNotify("Pickman's Whisper\n\nBond first.")
		Return
	EndIf
	String line = PickPraiseLine()
	ToastPraiseLine(line)
	SatiateHunger()
	RefreshHungerPanel(True)
	DiagNotify("Pickman's Whisper\n\nHunger satiated (debug — no kill required).\n" + line)
EndFunction

; Debug: BondStarted only ever goes True->never-False in normal play, so there was
; no way to retest bond-activation behavior (e.g. the "bond active" toast) without
; hunting for a genuinely pre-bond save. This lets the next RunBondPoll (~4s, since
; the blade is presumably already equipped) re-trigger StartBond on demand.
Function DebugResetBond()
	If !BondStarted
		DiagNotify("Pickman's Whisper\n\nAlready unbonded — StartBond hasn't fired yet.")
		Return
	EndIf
	BondStarted = False
	IntroToastShown = False
	BondStartGameTime = 0.0
	Debug.Trace("PickmansWhisper: DEBUG bond reset — awaiting next RunBondPoll")
	DiagNotify("Pickman's Whisper\n\nBond reset (debug). Next bond poll (~4s, if blade is equipped/owned) re-triggers StartBond and the bond toast.")
EndFunction

Function DebugReloadLines()
	If !VoiceAlias
		Debug.Trace("PickmansWhisper: ERROR DebugReloadLines — VoiceAlias unbound")
		DiagNotify("Pickman's Whisper\n\nVoiceAlias unbound — rebuild / reinstall PickmansWhisper.esp")
		Return
	EndIf
	LoadLineBanks()
	String calm = VoiceAlias.NoticeCalmStatus
	String restless = VoiceAlias.NoticeRestlessStatus
	String hungry = VoiceAlias.NoticeHungryStatus
	String starving = VoiceAlias.NoticeStarvingStatus
	String desperate = VoiceAlias.NoticeDesperateStatus
	DiagNotify("Pickman's Whisper — reloaded line banks\n\nTrust (files): " + TrustLineCount + "\nHunger (files): " + HungerLineCount + "\nPraise (files): " + PraiseLineCount + "\n\nNotice stages (files-only):\ncalm: " + calm + "\nrestless: " + restless + "\nhungry: " + hungry + "\nstarving: " + starving + "\ndesperate: " + desperate)
EndFunction

Function DebugTestPraiseLine()
	String line = PickPraiseLine()
	ToastPraiseLine(line)
	If Utility.IsInMenuMode()
		DiagNotify("Pickman's Whisper\n\n" + line)
	EndIf
EndFunction

Function DebugTestTrustLine()
	String line = PickTrustLine()
	ToastVoice(line)
	If Utility.IsInMenuMode()
		DiagNotify("Pickman's Whisper\n\n" + line)
	EndIf
EndFunction

; Unfiltered proximity probe — prove GoE/Detecting see anyone before notice filters.
; Mirrors Necromantic witness distance idea (GetActorsDetecting) + kill-scan FindActors living.
Function DebugScanNearbyNpcs()
	DEBUG_BUILD = "C2-stable"
	If !PlayerRef
		PlayerRef = Game.GetPlayer()
	EndIf
	If !PlayerRef
		DiagNotify("C2-polldbg\n\nNo player ref.")
		Return
	EndIf
	; Manual button = non-destructive PROBE. Also re-arms loops (same as load) so a
	; stuck timer is recoverable — but load/OnInit must arm without this button.
	ArmRuntimeLoops()
	; Clear cools, toast, then leave the passive path un-throttled: do not arm
	; any notice cooldown here. (Old button re-stamped the per-NPC cooldown.)
	String noticeDiag = ""
	If !VoiceAlias
		DiagNotify("C2-polldbg\n\nVoiceAlias unbound — rebuild esp.")
		Return
	EndIf
	VoiceAlias.NoticeCoolCount = 0
	VoiceAlias.LastNoticeToastRealTime = 0.0
	noticeDiag = VoiceAlias.LastNoticeDiag
	
	;Actor target = VoiceAlias.PickNoticeTarget()
	Actor target

	String body = "Manual scan (button)\n\n" + noticeDiag
	If target
		String nm = VoiceAlias.GetActorDisplayName(target)
		String line = VoiceAlias.PickNoticeLine(nm)
		If line == ""
			; Files-only: stage file didn't load — surface it, don't fake a line.
			VoiceAlias.LastNoticeStatus = "skip: stage " + (VoiceAlias.GetNoticeStage() + 1) + " (" + VoiceAlias.GetNoticeStageName(VoiceAlias.GetNoticeStage()) + ") not loaded"
			VoiceAlias.WriteNoticeStatusToMcm()
			VoiceAlias.WriteNearbyStatusToMcm()
			body += "\n\nNO LINE — stage " + (VoiceAlias.GetNoticeStage() + 1) + " (" + VoiceAlias.GetNoticeStageName(VoiceAlias.GetNoticeStage()) + ") file not loaded. See Debug rows."
		Else
			VoiceAlias.ToastNoticeLine(line)
			VoiceAlias.LastNoticeToastRealTime = 0.0 ; probe must not arm the global cooldown
			VoiceAlias.LastNoticeStatus = "ok: manual scan (probe)"
			VoiceAlias.WriteNoticeStatusToMcm()
			VoiceAlias.WriteNearbyStatusToMcm()
			body += "\n\nTOASTED: " + line
		EndIf
	Else
		VoiceAlias.WriteNearbyStatusToMcm()
		body += "\n\nNo toast target"
	EndIf
	DiagNotify("PW [" + DEBUG_BUILD + "]\n\n" + body)
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
	If !VoiceAlias
		RefreshDebugBusy = False
		ToastDebug("PW debug refresh: VoiceAlias unbound")
		Debug.Trace("PickmansWhisper: ERROR RefreshDebugStatus — VoiceAlias unbound")
		Return
	EndIf
	VoiceAlias.LoadNoticeLines()

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

	String aliasStatus = EnsureCombatKillHooks()
	MCM.SetModSettingString(MOD_NAME, "sWatch:Debug", "tagged " + BladeTaggedCount + " | " + aliasStatus)

	Int noticeStage = VoiceAlias.GetNoticeStage()
	String stageSrc = "auto"
	If VoiceAlias.IsNoticeStageForced()
		stageSrc = "forced"
	Else
		; Reflect the live (hunger-derived) stage in the dropdown so it reads as a
		; status display when not forcing. When forcing, leave the user's choice.
		MCM.SetModSettingInt(MOD_NAME, "iNoticeStage:Debug", noticeStage)
	EndIf
	String stageInfo = "stage " + (noticeStage + 1) + "/5 " + VoiceAlias.GetNoticeStageName(noticeStage) + " (" + stageSrc + ", " + VoiceAlias.GetNoticeCountForStage(noticeStage) + " lines)"
	String noticeStatus = ""
	If VoiceAlias
		noticeStatus = VoiceAlias.LastNoticeStatus
	EndIf
	If noticeStatus == ""
		MCM.SetModSettingString(MOD_NAME, "sNotice:Debug", "(none yet) | " + stageInfo)
	Else
		MCM.SetModSettingString(MOD_NAME, "sNotice:Debug", noticeStatus + " | " + stageInfo)
	EndIf
	VoiceAlias.WriteFixationStatusToMcm()
	VoiceAlias.WriteNoticeLoadStatusToMcm()
	VoiceAlias.WriteNearbyStatusToMcm()

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
	VoiceAlias.WriteNoticeLoadStatusToMcm()
	VoiceAlias.WriteNearbyStatusToMcm()
	VoiceAlias.WriteFixationStatusToMcm()
	; Victims page strings live outside Debug — RefreshMenu wipes them to settings.ini.
	TickVictimsAimCache()
	PushVictimsPanelStrings()
	If noticeStatus == ""
		MCM.SetModSettingString(MOD_NAME, "sNotice:Debug", "(none yet) | " + stageInfo)
	Else
		MCM.SetModSettingString(MOD_NAME, "sNotice:Debug", noticeStatus + " | " + stageInfo)
	EndIf
	RefreshDebugBusy = False
	ToastDebug("PW debug refreshed [" + DEBUG_BUILD + "]")
	Debug.Trace("PickmansWhisper: RefreshDebugStatus done " + DEBUG_BUILD)
EndFunction
