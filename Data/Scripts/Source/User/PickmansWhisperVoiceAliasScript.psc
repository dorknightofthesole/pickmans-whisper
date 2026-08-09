Scriptname PickmansWhisperVoiceAliasScript extends ReferenceAlias
{Voice owner — Notice / Recognition / SleepRecognition / stage Audio / Intimacy.
Entry: HandleWhisperVoice(Actor).}

; One row in the look-fixation table (who / how many looks / recognition toasts heard).
Struct FixationEntry
	Int ActorId
	Int LookCount
	Int RecognitionToasts
	Float lastFixation
EndStruct

; --- moved state ---
; Notice poll dialogs — OFF by default. Enable on Debug page if needed.
Bool NoticePollDebugDefault = False
Int NoticePollCount = 0
String Property LastNoticeDiag = "" Auto
String LastNoticeBreakAt = "" ; short "where it broke" for dialog header
String Property LastNearbySummary = "" Auto ; MCM Debug "Nearby NPC scan" — updated by every PickNoticeTarget
Float Property LastNoticeDiagRealTime = 0.0 Auto
Float NOTICE_DIAG_MIN_GAP = 5.0 ; real seconds between poll MessageBoxes
Int TIMER_NOTICE = 5
Int TIMER_NOTICE_APPROACH = 6
Float NOTICE_VOICE_SECONDS = 45.0
Float NextNoticeRealTime = 0.0
Float RENAME_PROMPT_DELAY = 2.5

Int FID_WHISPER_ENDIT = 0x00000807
Int FID_WHISPER_BASE = 0x00000807

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
String Property NoticeCalmStatus = "" Auto
String Property NoticeRestlessStatus = "" Auto
String Property NoticeHungryStatus = "" Auto
String Property NoticeStarvingStatus = "" Auto
String Property NoticeDesperateStatus = "" Auto
String LastStageLoadStatus = ""
; Step-by-step load trace (path/exists/raw/parsed/RESULT), shown in one MessageBox
; via ReportNoticeLoadStatus — mirrors Necromantic PosLoadDiag / InsLoadDiag.
String NoticeLoadDiag = ""
String LastStageLoadDiag = ""
Float Property LastNoticeToastRealTime = 0.0 Auto
Float Property LastNoticeToastGameTime = 0.0 Auto ; hunger whisper cadence (game days)
Float NOTICE_TOAST_COOLDOWN = 6.0 ; legacy real-s gap (kept for probes); ambient uses NOTICE_MIN_GAME_HOURS
Float NOTICE_MIN_GAME_HOURS = 0.083333 ; ~5 game minutes between ambient hunger whispers
Float NOTICE_NPC_COOLDOWN = 12.0 ; per-NPC cool after a hunger toast (does NOT block fixation)
; Trust / hunger-band / praise toast cooldowns (Main façades read/write these — must be Property).
Float Property LastTrustToastRealTime = 0.0 Auto
Float Property LastHungerToastRealTime = 0.0 Auto
Float Property LastPraiseToastRealTime = 0.0 Auto
Float Property TRUST_TOAST_COOLDOWN = 60 Auto Const
Float Property HUNGER_TOAST_COOLDOWN = 6.0 Auto Const
Float Property PRAISE_TOAST_COOLDOWN = 2.0 Auto Const
Int[] NoticeCoolIds
Float[] NoticeCoolTimes
Int Property NoticeCoolCount = 0 Auto
Int NOTICE_COOL_MAX = 16
; C4 approach is parked — do not reintroduce FindActors/timers on the notice hot
; path until ambient killscan whispers are verified working again in-game.
String Property LastNoticeStatus = "" Auto ; MCM Debug — why notice did/didn't fire

; Look fixation: count how many times the player has looked at each NPC, then
; speak more as that count rises. Separate from ambient hunger whispers.
; Called from TargetScan (via Main.LookingAtTarget) once per scan when aimed at someone.
;
; Per-NPC memory (up to FIXATION_MAX): single FixationEntry[] table.
; Spacing: SkipFixation / FIXATION_TOAST_GAP between counted looks while holding aim.
;
; Voice by look count (mild → sharper):
;   1st look — silent (just remember her)
;   2nd look — recognition lines (sleep bank if she is asleep)
;   3rd+    — hunger-stage notice lines (C3 banks; stronger than recognition)
; Name-her prompt queues at look count >= RECOGNITION_NAME_PROMPT_AT (still unnamed).
Int FIXATION_MAX = 32
Int LOOK_COUNT_FIRST_SILENT = 1
Int LOOK_COUNT_SECOND_RECOGNITION = 2
FixationEntry[] Fixations
Int FixationSlotCount = 0
Int LastLookFixationId = 0 ; last aimed actorId; 0 after look-away
String Property LastFixationStatus = "" Auto ; MCM Debug
String[] RecognitionLines
Int RecognitionLineCount = 0
String LastRecognitionLine = "" ; no-immediate-repeat (raw template)
String RecognitionLoadStatus = ""
; C5 P5 — sleep recognition bank (2nd look while GetSleepState >= 3).
String[] SleepRecognitionLines
Int SleepRecognitionLineCount = 0
String LastSleepRecognitionLine = "" ; no-immediate-repeat (raw template)
String SleepRecognitionLoadStatus = ""
; After this many counted looks on one NPC (still unnamed), nudge toward MCM Victims.
Int RECOGNITION_NAME_PROMPT_AT = 3

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
; True while PlayWhisperXwmAndWait is latent on PlayAndWait — skip overlapping clips.
Bool WhisperAudioBusy = False

Float FIXATION_TOAST_GAP = 20.0 ; real seconds between fixation toasts for one NPC

PickmansWhisperMainQuestScript Function Main()
	Return GetOwningQuest() as PickmansWhisperMainQuestScript
EndFunction

; Living-scan radius — TargetScan is the only definition (no Main copy).
Float Function KillWatchRadius()
	PickmansWhisperTargetScanScript ts = Main().TargetScan()
	If !ts
		Debug.Trace("PickmansWhisper: ERROR KillWatchRadius — TargetScan missing")
		Return 0.0
	EndIf
	Return ts.KILL_WATCH_RADIUS
EndFunction

Event OnAliasInit()
	LoadVoiceBanks()
EndEvent

Function LoadVoiceBanks()
	LoadNoticeLines()
	LoadAudioBanks()
	LoadWhisperSndrIds()
	LoadRecognitionLines()
	LoadSleepRecognitionLines()
	LoadIntimacyNamedLines()
EndFunction

; Speak gates live inside MaybeSpeakNoticeLine (blade drawn, hunger hour, etc.).
Function HandleWhisperVoice(Actor akTarget)
	If !Main()
		Debug.Trace("PickmansWhisper: ERROR HandleWhisperVoice — Main script missing")
		Return
	EndIf
	String who = "?"
	If akTarget
		who = "id=0x" + GardenOfEden.GetHexFormID(akTarget)
	EndIf
	NoteVoiceDispatch("target=" + who)
	MaybeSpeakNoticeLine(akTarget)
EndFunction

; --- moved functions ---

; Heartbeat only — MCM Debug row + Trace. No script-side copy (RefreshMenu may wipe the row).
Function NoteVoiceDispatch(String detail)
	If !detail
		detail = "?"
	EndIf
	If MCM.IsInstalled()
		MCM.SetModSettingString(Main().MOD_NAME, "sVoiceDispatch:Debug", detail)
	EndIf
	Debug.Trace("PickmansWhisper: voice dispatch | " + detail)
EndFunction


; Named Potential Victim + iVoiceDelivery (0 toast+audio / 1 audio / 2 toast).
; abStart=True → Start banks; False → End banks. Same-index toast/audio like notice D1.
Function MaybeSpeakNamedIntimacyEvent(Actor partner, Bool abStart)
	If !partner
		Return
	EndIf
	String overrideName = Main().GetVictimOverrideName(partner)
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
	String line = Main().ApplyNamePlaceholder(toastTemplate, overrideName)
	If !line || GardenOfEden.StrLength(line) < 1
		Return
	EndIf
	ShowVoiceToast(line)
	If mode == 0
		PlayIntimacyAudioAt(abStart, tIdx)
	EndIf
	Debug.Trace("PickmansWhisper: named intimacy voice idx=" + tIdx + " start=" + abStart + " | " + line)
EndFunction

; Voice / whisper gate — blade must be EQUIPPED (drawn), same requirement as kill
; satiation (IsBladeEquipped / IsBladeKillWeaponReady). Was ownership-only ("on the
; player, not necessarily drawn") — confirmed live that let ambient notice lines speak
; with the blade merely owned/sheathed; the blade is what "speaks" to the player, so it
; must be in hand, matching every other credited-action gate in the mod.
Bool Function IsVoiceWeaponReady()
	Return Main().IsBladeEquipped()
EndFunction


Function StartNoticeVoice()
	CancelTimer(TIMER_NOTICE)
	NextNoticeRealTime = 0.0
EndFunction


Bool Function IsNoticePollDebugEnabled()
	If MCM.IsInstalled()
		Return MCM.GetModSettingBool(Main().MOD_NAME, "bNoticePollDebug:Debug")
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
	Main().DEBUG_BUILD = "C2-stable"
	Debug.Trace("PickmansWhisper: notice pipe | " + body)
	Main().DiagNotify(body)
EndFunction


Function WriteNearbyStatusToMcm()
	If !MCM.IsInstalled()
		Return
	EndIf
	If !LastNearbySummary
		MCM.SetModSettingString(Main().MOD_NAME, "sNearby:Debug", "(awaiting poll)")
	Else
		MCM.SetModSettingString(Main().MOD_NAME, "sNearby:Debug", LastNearbySummary)
	EndIf
EndFunction

Function WriteNoticeStatusToMcm()
	If !MCM.IsInstalled()
		Return
	EndIf
	If !LastNoticeStatus
		MCM.SetModSettingString(Main().MOD_NAME, "sNotice:Debug", "(none yet)")
	Else
		MCM.SetModSettingString(Main().MOD_NAME, "sNotice:Debug", LastNoticeStatus)
	EndIf
EndFunction

Function MaybeSpeakNoticeLine(Actor akTarget)
	; Proven C3 path — keep boring. Detection lives in ExplainNoticeReject / PickNoticeTarget.
	; Do not add FindActors / approach timers here until ambient toasts are verified again.
	NoticePollCount += 1
	LastNoticeBreakAt = ""
	Main().DEBUG_BUILD = "C2-stable"

	If !Main().PlayerRef
		Main().PlayerRef = Game.GetPlayer()
	EndIf
	If !Main().PlayerRef
		LastNoticeStatus = "skip: no player"
		WriteNoticeStatusToMcm()
		Debug.Trace("PickmansWhisper: notice skip | " + LastNoticeStatus)
		Return
	EndIf
	If !IsVoiceEnabled()
		LastNoticeStatus = "skip: voice off"
		WriteNoticeStatusToMcm()
		Debug.Trace("PickmansWhisper: notice skip | " + LastNoticeStatus)
		Return
	EndIf
	If !IsVoiceWeaponReady()
		LastNoticeStatus = "skip: no Pickman's Blade"
		WriteNoticeStatusToMcm()
		Debug.Trace("PickmansWhisper: notice skip | " + LastNoticeStatus)
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
			Debug.Trace("PickmansWhisper: notice skip | " + LastNoticeStatus)
			Return
		EndIf
	EndIf

	If !akTarget
		; PickNoticeTarget already set LastNoticeStatus — force skip: prefix for MCM clarity.
		; GoE StrFind = occurrence count; <=0 means "skip:" not present.
		If !LastNoticeStatus || GardenOfEden.StrFind(LastNoticeStatus, "skip:") <= 0
			If LastNoticeBreakAt
				LastNoticeStatus = "skip: no target (" + LastNoticeBreakAt + ")"
			Else
				LastNoticeStatus = "skip: no eligible target"
			EndIf
		EndIf
		WriteNoticeStatusToMcm()
		WriteNearbyStatusToMcm()
		Debug.Trace("PickmansWhisper: notice skip | " + LastNoticeStatus)
		Return
	EndIf

	String npcName = GetActorDisplayName(akTarget)
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
		MarkNoticeCooldown(akTarget)
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
	MarkNoticeCooldown(akTarget)
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
	OnNoticeSpoken(akTarget, npcName, line)
EndFunction

; Called when the player is aimed at someone (Main.LookingAtTarget / TargetScan).
; First look counts immediately (silent). Further looks spaced by SkipFixation gap.
;
; After each counted look, speak based on how many times we have counted her:
;   1st — silent   2nd — recognition   3rd+ — hunger-stage
; Blade must be drawn to speak (not required for the silent first look).
; Name-her queues at look count >= RECOGNITION_NAME_PROMPT_AT.
Function LookFixation(Actor akTarget)
	If !Main().PlayerRef
		Main().PlayerRef = Game.GetPlayer()
	EndIf
	If !Main().PlayerRef
		LastFixationStatus = "skip: no player"
		WriteFixationStatusToMcm()
		Debug.Trace("PickmansWhisper: fixation skip | no player")
		Return
	EndIf

	; Not aimed at a valid target — clear aim id so the next look can count.
	; Eligibility matches notice filters but ignores hunger toast cooldown, so a
	; recent ambient whisper cannot block look-counting.
	If !akTarget || akTarget == Main().PlayerRef || !IsFixationEligible(akTarget)
		LastLookFixationId = 0
		Return
	EndIf

	Int actorId = akTarget.GetFormID()
	If actorId == 0
		Debug.Trace("PickmansWhisper: fixation skip | actorId=0")
		Return
	EndIf

	Int fixEntryId = GetOrCreateFixationEntry(actorId)
	If fixEntryId < 0
		LastFixationStatus = "skip: fixation table full"
		WriteFixationStatusToMcm()
		Debug.Trace("PickmansWhisper: fixation skip | table full")
		Debug.Notification("PickmansWhisper: fixation skip | table full")
		Return
	EndIf

	; per-NPC lastFixation time — skip until N seconds after last counted look
	Bool skip = SkipFixation(fixEntryId, actorId)
	If skip
		; Debug.Notification("PW Debug: Skipping fixation, its been less than " + FIXATION_TOAST_GAP + " since the last fixation whisper." )
		Debug.Trace("PW Debug: Skipping fixation, its been less than " + FIXATION_TOAST_GAP + " since the last fixation whisper." )
		Return
	EndIf

	FixationEntry bumped = IncrementFixation(fixEntryId, actorId)
	If !bumped
		LastFixationStatus = "skip: IncrementFixation failed"
		WriteFixationStatusToMcm()
		Debug.Trace("PickmansWhisper: fixation skip | IncrementFixation failed")
		Return
	EndIf
	Int count = bumped.LookCount
	LastLookFixationId = actorId

	; Name for toasts / MCM (rejects junk glyphs; Victims rename if set).
	String displayName = NoticeNameForLine(GetActorDisplayName(akTarget))
	String label = displayName
	If !label
		label = "unnamed"
	EndIf

	; Update MCM even when we stay silent.
	LastFixationStatus = label + " seen x" + count + " (" + FixationSlotCount + "/" + FIXATION_MAX + ")"
	WriteFixationStatusToMcm()
	Debug.Trace("PickmansWhisper: fixation edge | " + LastFixationStatus)

	; Name-her uses look count (not recognition-toast count) — queues for TickPendingRenameDeadline.
	If count >= RECOGNITION_NAME_PROMPT_AT
		MaybePromptNameHer(akTarget, count)
	EndIf

	If count == LOOK_COUNT_FIRST_SILENT
		; Remember her; no voice yet.
		Return
	EndIf

	If !IsVoiceWeaponReady()
		LastFixationStatus = label + " seen x" + count + " (no blade — silent)"
		WriteFixationStatusToMcm()
		Debug.Trace("PickmansWhisper: fixation skip | Blade not equipped")
		; Debug.Notification("PickmansWhisper: fixation skip | Blade not equipped")
		Return
	EndIf

	If count == LOOK_COUNT_SECOND_RECOGNITION
		; Second look — milder recognition (or sleep-recognition if she is asleep).
		SpeakRecognitionLine(akTarget, displayName)
	Else
		; Third look or later — hunger-stage notice (sharper).
		SpeakFixationStageWhisper(akTarget, displayName)
	EndIf

	Debug.Trace("PW Debug: Spoke Fixation Line")
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
		Debug.Trace("PickmansWhisper: ToastNoticeLine skip | empty line")
		Return
	EndIf
	If !IsVoiceWeaponReady()
		LastNoticeStatus = "skip: ToastNoticeLine — no Pickman's Blade"
		WriteNoticeStatusToMcm()
		Debug.Trace("PickmansWhisper: ToastNoticeLine skip | no Pickman's Blade")
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
		Debug.Trace("PickmansWhisper: ShowVoiceToast skip | empty line")
		Return
	EndIf
	; Central toast sink — recognition / rename / trust / praise all land here.
	If !IsVoiceWeaponReady()
		Debug.Trace("PickmansWhisper: ShowVoiceToast skip | no Pickman's Blade | " + line)
		Return
	EndIf
	Debug.Notification(FormatVoiceToast(line))
EndFunction


; Ambient trust lines (TrustLines.txt on Main). Hosted from TargetScan cadence.
Function MaybeSpeakTrustLine()
	PickmansWhisperMainQuestScript m = Main()
	If !m || !m.BondStarted
		Return
	EndIf
	If !IsVoiceEnabled()
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
	String line = m.PickTrustLine()
	If line == ""
		Return
	EndIf
	LastTrustToastRealTime = now
	ShowVoiceToast(line)
	Debug.Trace("PickmansWhisper: voice | " + line)
EndFunction


; Blade OnHit nudge — ModConfig hitWhisper toast for now; may grow into audio later.
Function MaybeSpeakHitWhisper(Actor akTarget)
	If !Main() || !Main().ModConfigAlias
		Debug.Trace("PickmansWhisper: MaybeSpeakHitWhisper skip | Main/ModConfig unbound")
		Return
	EndIf
	String line = Main().ModConfigAlias.HitWhisper
	If !line
		Debug.Trace("PickmansWhisper: MaybeSpeakHitWhisper skip | hitWhisper empty (ModConfig)")
		Return
	EndIf
	ShowVoiceToast(line)
EndFunction


; Living tracked NPC while blade unequipped — ModConfig needsBeatingWhisper.
; No ShowVoiceToast (that gates on blade drawn); plain FormatVoiceToast Notification.
; FormatLineWithActorName(..., False) keeps Settler/HUD label (not ambient nameless strip).
Function MaybeSpeakNeedsBeatingWhisper(Actor akTarget)
	If !akTarget
		Debug.Trace("PickmansWhisper: MaybeSpeakNeedsBeatingWhisper skip | no actor")
		Return
	EndIf
	If !Main() || !Main().ModConfigAlias
		Debug.Trace("PickmansWhisper: MaybeSpeakNeedsBeatingWhisper skip | Main/ModConfig unbound")
		Return
	EndIf
	String raw = Main().ModConfigAlias.NeedsBeatingWhisper
	If !raw
		Debug.Trace("PickmansWhisper: MaybeSpeakNeedsBeatingWhisper skip | needsBeatingWhisper empty (ModConfig)")
		Return
	EndIf
	String line = Main().FormatLineWithActorName(raw, akTarget, False)
	If !line
		Debug.Trace("PickmansWhisper: MaybeSpeakNeedsBeatingWhisper skip | line empty after {name}")
		Return
	EndIf
	Debug.Notification(FormatVoiceToast(line))
EndFunction


; Whisper / fixation / notice label for an actor.
; P3+P4 Potential Victims: override + GoE2.SetDisplayName so {name} matches aim/HUD.
String Function GetActorDisplayName(Actor ak)
	If !ak
		Return ""
	EndIf
	String label = ""
	String overrideName = Main().GetVictimOverrideName(ak)
	If overrideName
		; Lazy re-apply after load (ExtraTextDisplayData can drop; FormID table persists).
		Main().EnsureVictimDisplayName(ak)
		label = overrideName
	Else
		String disp = ak.GetDisplayName()
		If disp
			label = disp
		Else
			ActorBase base = ak.GetLeveledActorBase()
			If base
				label = base.GetName()
			EndIf
		EndIf
	EndIf
	If !label
		Return ""
	EndIf
	; Slice I — toast {name} matches desperate world suffix while stage 4.
	PickmansWhisperDesperateRenameScript dr = Main().DesperateRename()
	If dr
		Return dr.MaybeSuffixDisplayName(ak, label)
	EndIf
	Return label
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
; FO4: struct array slots and locals are None until `new FixationEntry`. Bare
; `FixationEntry entry` then `.ActorId = …` throws "Cannot access a variable of a
; None struct" and every look stays seen x1 while SlotCount climbs.

Function WriteFixationStatusToMcm()
	If !MCM.IsInstalled()
		Return
	EndIf
	If !LastFixationStatus
		MCM.SetModSettingString(Main().MOD_NAME, "sFixation:Debug", "(none yet)")
	Else
		MCM.SetModSettingString(Main().MOD_NAME, "sFixation:Debug", LastFixationStatus)
	EndIf
EndFunction


;-------------------------- Fixation Entry Util --------------------------;
Function EnsureFixationLists()
	If Fixations && Fixations.Length == FIXATION_MAX
		Return
	EndIf
	Fixations = new FixationEntry[32]
	Int i = 0
	While i < FIXATION_MAX
		Fixations[i] = new FixationEntry
		i += 1
	EndWhile
	FixationSlotCount = 0
EndFunction

FixationEntry Function GetFixationEntry(Int actorId)
	If actorId == 0
		Return None
	EndIf

	EnsureFixationLists()
	
	Int i = 0
	While i < FixationSlotCount
		FixationEntry e = Fixations[i]
		If e && e.ActorId == actorId
			Return e
		EndIf
		i += 1
	EndWhile
	
	Return None
EndFunction

Int Function GetOrCreateFixationEntry(Int actorId)
	If actorId == 0
		Return 0
	EndIf

	EnsureFixationLists()
	
	Int i = 0
	While i < FixationSlotCount
		FixationEntry e = Fixations[i]
		If e && e.ActorId == actorId
			Return i
		EndIf
		i += 1
	EndWhile
	
	If FixationSlotCount >= FIXATION_MAX
		EvictLowestFixation()
	EndIf
	If FixationSlotCount >= FIXATION_MAX
		Return -1
	EndIf
	
	; LookCount starts at 0 — IncrementFixation is the sole bump (avoids create+increment = 2).
	FixationEntry entry = new FixationEntry
	entry.ActorId = actorId
	entry.LookCount = 0
	entry.RecognitionToasts = 0
	entry.lastFixation = 0.0
	Fixations[FixationSlotCount] = entry
	
	Int CurFixationSlotCount = FixationSlotCount
	FixationSlotCount += 1

	Return CurFixationSlotCount
EndFunction

Bool Function UpdateFixationEntry(Int actorId, FixationEntry NewFixationEntry)
	If actorId == 0
		Return 0
	EndIf
	
	EnsureFixationLists()
	
	Int i = 0
	While i < FixationSlotCount
		FixationEntry e = Fixations[i]
		If e && e.ActorId == actorId
			Fixations[i] = NewFixationEntry
			Return True
		EndIf
		i += 1
	EndWhile
	
	Return False
EndFunction

; True = enough time since last fixation toast for this row (stamps lastFixation).
; False = still within FIXATION_TOAST_GAP, or bad index / actorId mismatch.
; Call site not wired yet — LookFixation will gate speak on this.
Bool Function SkipFixation(Int fixEntryId, Int actorId)
	EnsureFixationLists()
	If fixEntryId < 0 || fixEntryId >= FixationSlotCount
		Debug.Trace("PickmansWhisper: ERROR SkipFixation — bad index " + fixEntryId + " (slots=" + FixationSlotCount + ")")
		Return False
	EndIf
	FixationEntry e = Fixations[fixEntryId]
	If !e
		Debug.Trace("PickmansWhisper: ERROR SkipFixation — None struct at index " + fixEntryId)
		Return False
	EndIf
	If e.ActorId != actorId
		Debug.Trace("PickmansWhisper: ERROR SkipFixation — actorId mismatch index=" + fixEntryId + " entry=" + e.ActorId + " expected=" + actorId)
		Return False
	EndIf
	Float now = Utility.GetCurrentRealTime()
	; lastFixation == 0 → never toasted; always allow and stamp.
	; Negative gap = real-time clock reset after load — treat as allow (else Skip forever).
	Float gap = now - e.lastFixation
	If e.lastFixation > 0.0 && gap >= 0.0 && gap < FIXATION_TOAST_GAP
		Debug.Trace("PickmansWhisper: fixation skip | toast gap " + gap + "s < " + FIXATION_TOAST_GAP)
		Return True
	EndIf
	e.lastFixation = now
	Fixations[fixEntryId] = e
	Return False
EndFunction

; Bump LookCount at Fixations[fixEntryId]. actorId must match the row (sanity check).
; Returns the updated entry, or None on bad index / None slot / actorId mismatch.
FixationEntry Function IncrementFixation(Int fixEntryId, Int actorId)
	EnsureFixationLists()
	If fixEntryId < 0 || fixEntryId >= FixationSlotCount
		Debug.Trace("PickmansWhisper: ERROR IncrementFixation — bad index " + fixEntryId + " (slots=" + FixationSlotCount + ")")
		Return None
	EndIf
	FixationEntry e = Fixations[fixEntryId]
	If !e
		Debug.Trace("PickmansWhisper: ERROR IncrementFixation — None struct at index " + fixEntryId)
		Return None
	EndIf
	If e.ActorId != actorId
		Debug.Trace("PickmansWhisper: ERROR IncrementFixation — actorId mismatch index=" + fixEntryId + " entry=" + e.ActorId + " expected=" + actorId)
		Return None
	EndIf
	e.LookCount = e.LookCount + 1
	Fixations[fixEntryId] = e
	Return e
EndFunction

; Drop this actor from the look table (no-op if she is not tracked).
Function RemoveFixation(Actor ak)
	If !ak
		Return
	EndIf
	RemoveFixationByActorId(ak.GetFormID())
EndFunction

; Shared table splice — used by RemoveFixation and by eviction when GetForm fails.
Function RemoveFixationByActorId(Int actorId)
	If actorId == 0
		Return
	EndIf

	EnsureFixationLists()
	Int i = 0
	
	While i < FixationSlotCount
		FixationEntry cur = Fixations[i]
		If cur && cur.ActorId == actorId
			Int j = i
			While j < FixationSlotCount - 1
				Fixations[j] = Fixations[j + 1]
				j += 1
			EndWhile
			FixationEntry cleared = new FixationEntry
			Fixations[FixationSlotCount - 1] = cleared
			FixationSlotCount -= 1
			If LastLookFixationId == actorId
				LastLookFixationId = 0
			EndIf
			Return
		EndIf
		i += 1
	EndWhile
EndFunction

; Drop lowest look-count (tie → lowest index / oldest). Leaves one free slot.
Function EvictLowestFixation()
	EnsureFixationLists()
	If FixationSlotCount < 1
		Return
	EndIf
	Int best = 0
	FixationEntry bestEntry = Fixations[0]
	If !bestEntry
		Debug.Trace("PickmansWhisper: ERROR EvictLowestFixation — None struct at slot 0")
		Return
	EndIf
	Int bestCount = bestEntry.LookCount
	Int i = 1
	While i < FixationSlotCount
		FixationEntry e = Fixations[i]
		If e && e.LookCount < bestCount
			best = i
			bestCount = e.LookCount
		EndIf
		i += 1
	EndWhile
	FixationEntry victim = Fixations[best]
	If !victim
		Return
	EndIf
	Int actorId = victim.ActorId
	Actor ak = Game.GetForm(actorId) as Actor
	If ak
		RemoveFixation(ak)
	Else
		; Form not resolvable (unloaded) — still free the slot.
		RemoveFixationByActorId(actorId)
	EndIf
EndFunction

; Current look-count for actorId, or 0 if she is not in the table yet.
Int Function GetFixationLookCount(Int actorId)
	FixationEntry entry = GetFixationEntry(actorId)
	If entry && entry.ActorId == actorId
		Return entry.LookCount
	EndIf
	Return 0
EndFunction

;-------------------------- Fixation Entry Util End --------------------------;


; After N counted looks (LookFixation), if still unnamed, queue MCM Victims nudge (delayed).
; Never ShowVoiceToast here — a second Notification in the same tick replaces the
; recognition / stage toast in the FO4 HUD.
; Prompt text: ModConfig.txt → renamePromptFemaleNPC (files-only).
; aiLookCount is FixationEntry.LookCount from LookingAtTarget / LookFixation.
Function MaybePromptNameHer(Actor ak, Int aiLookCount)
	If !ak || aiLookCount < RECOGNITION_NAME_PROMPT_AT
		Return
	EndIf
	If Main().GetVictimOverrideName(ak)
		Return
	EndIf
	If !Main().ModConfigAlias || !Main().ModConfigAlias.RenamePromptFemaleNPC
		; Trace only — Notification here would also clobber the recognition toast.
		String st = ""
		If Main().ModConfigAlias
			st = Main().ModConfigAlias.ModConfigLoadStatus
		EndIf
		Debug.Trace("PickmansWhisper: ERROR rename prompt — " + st)
		Return
	EndIf
	Main().PendingRenamePrompt = Main().ModConfigAlias.RenamePromptFemaleNPC
	; LookingAtTarget → TickPendingRenameDeadline polls PendingRenameAtReal.
	Main().PendingRenameAtReal = Utility.GetCurrentRealTime() + RENAME_PROMPT_DELAY
	Debug.Trace("PickmansWhisper: name-her prompt queued (deadline) | id=0x" + GardenOfEden.GetHexFormID(ak) + " looks=" + aiLookCount)
EndFunction

; Empty string = passes. Otherwise a short reject reason for MCM / MessageBox.
; Notice feature checks first; hard gate is Main.IsValidTarget (Traces its own rejects).
; abIgnoreCooldown=True for fixation (hunger NPC cool must not suppress look-edge toasts).
String Function ExplainNoticeReject(Actor ak, Bool abIgnoreCooldown = False)
	If !ak || ak == Main().PlayerRef
		Return "no actor"
	EndIf
	If ak.IsDead()
		Return "dead"
	EndIf
	If Main().PlayerRef && Main().PlayerRef.GetDistance(ak) > KillWatchRadius()
		Return "too far"
	EndIf
	If !abIgnoreCooldown && IsNoticeOnCooldown(ak)
		Return "cooldown"
	EndIf
	If !Main().IsValidTarget(ak)
		Return "not a valid target"
	EndIf
	Return ""
EndFunction

Function CommitNearbyPickSummary(Int nLive, Actor best)
	; Memory only during poll — MCM writes happen after ToastNoticeLine / on Refresh.
	String s = "live=" + nLive + " r=" + (KillWatchRadius() as Int)
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
			Float d = Main().PlayerRef.GetDistance(ak)
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
	; Zero count before realloc so a concurrent pick never reads empty slots with a stale count.
	RecognitionLineCount = 0
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
	SleepRecognitionLineCount = 0
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
	Int attempt = 0
	While attempt < 20
		String raw = bank[Utility.RandomInt(0, count - 1)]
		Int tries = 0
		While tries < 8 && count > 1 && (!raw || raw == LastRecognitionLine || (wantNameless && Main().StrContains(raw, "{name}")))
			raw = bank[Utility.RandomInt(0, count - 1)]
			tries += 1
		EndWhile
		attempt += 1
		If !raw
			LoadRecognitionLines()
			bank = GetRecognitionBank(0)
			count = GetRecognitionBankCount(0)
			If count <= 0 || !bank
				Return ""
			EndIf
		Else
			String line = Main().ApplyNamePlaceholder(raw, useName)
			If line && GardenOfEden.StrLength(line) >= 1
				LastRecognitionLine = raw
				Return line
			EndIf
		EndIf
	EndWhile
	Return ""
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
	Int attempt = 0
	While attempt < 20
		String raw = SleepRecognitionLines[Utility.RandomInt(0, SleepRecognitionLineCount - 1)]
		Int tries = 0
		While tries < 8 && SleepRecognitionLineCount > 1 && (!raw || raw == LastSleepRecognitionLine || (wantNameless && Main().StrContains(raw, "{name}")))
			raw = SleepRecognitionLines[Utility.RandomInt(0, SleepRecognitionLineCount - 1)]
			tries += 1
		EndWhile
		attempt += 1
		If !raw
			; Empty slot with non-zero count = stale array; reload and retry.
			LoadSleepRecognitionLines()
			If SleepRecognitionLineCount <= 0 || !SleepRecognitionLines
				Return ""
			EndIf
		Else
			String line = Main().ApplyNamePlaceholder(raw, useName)
			If line && GardenOfEden.StrLength(line) >= 1
				LastSleepRecognitionLine = raw
				Return line
			EndIf
		EndIf
	EndWhile
	Return ""
EndFunction


; 3rd+ look — speak current hunger-stage notice line (does not rewrite MaybeSpeakNoticeLine).
; Honors Voice delivery (toast+audio / audio-only / toast-only) — Desperate_Audio etc.
Function SpeakFixationStageWhisper(Actor ak, String npcName)
	Int stage = GetNoticeStage()
	Int mode = GetVoiceDeliveryMode() ; 0 toast+audio / 1 audio only / 2 toast only

	If mode == 1
		Int aIdx = PickNoticeAudioIndex(stage)
		If aIdx < 0
			LastFixationStatus = "stage audio-only skipped (map empty)"
			WriteFixationStatusToMcm()
			Debug.Trace("PickmansWhisper: SpeakFixationStageWhisper skip | audio-only empty stage=" + stage)
			Return
		EndIf
		PlayNoticeAudio(stage, aIdx)
		If ak
			MarkNoticeCooldown(ak)
			OnNoticeSpoken(ak, npcName, "")
		EndIf
		Return
	EndIf

	String line = PickNoticeLine(npcName)
	If !line || GardenOfEden.StrLength(line) < 1
		LastFixationStatus = "seen x2 — stage line skipped (bank empty)"
		WriteFixationStatusToMcm()
		Debug.Notification("PW Debug: seen x2 — stage line skipped (bank empty)")
		Debug.Trace("PW Debug: seen x2 — stage line skipped (bank empty)")
		Return
	EndIf
	; ToastNoticeLine stamps game-hour gate so ambient won't double-toast soon after.
	ToastNoticeLine(line)
	; Same-index audio as MaybeSpeakNoticeLine (Desperate_Audio.txt when stage 4).
	If mode == 0
		PlayNoticeAudio(stage, LastNoticePickIndex)
	EndIf
	If ak
		MarkNoticeCooldown(ak)
		OnNoticeSpoken(ak, npcName, line)
	EndIf
EndFunction


; 2nd look — awake RecognitionLines / sleep SleepRecognitionLines (no hunger hour stamp).
; Name-her prompt is LookFixation look-count (RECOGNITION_NAME_PROMPT_AT), not here.
Function SpeakRecognitionLine(Actor ak, String npcName)
	Bool asleep = IsActorSleeping(ak)
	String line = ""
	If asleep
		line = PickSleepRecognitionLine(npcName)
	Else
		line = PickRecognitionLine(npcName)
	EndIf
	If !line || GardenOfEden.StrLength(line) < 1
		; "N lines" in load status means the file loaded — do not toast a false missing-file error.
		If asleep
			If SleepRecognitionLineCount <= 0
				LastFixationStatus = "sleep recognition MISSING — " + SleepRecognitionLoadStatus
				WriteFixationStatusToMcm()
				Debug.Notification("Pickman's Whisper: SleepRecognitionLines.txt not loaded — see MCM / config")
				Debug.Trace("PickmansWhisper: ERROR SleepRecognitionLines.txt — " + SleepRecognitionLoadStatus)
			Else
				LastFixationStatus = "sleep recognition pick empty — bank " + SleepRecognitionLoadStatus
				WriteFixationStatusToMcm()
				Debug.Trace("PickmansWhisper: ERROR sleep recognition pick empty — bank ok (" + SleepRecognitionLoadStatus + ")")
			EndIf
		Else
			If RecognitionLineCount <= 0
				LastFixationStatus = "recognition MISSING — " + RecognitionLoadStatus
				WriteFixationStatusToMcm()
				Debug.Notification("Pickman's Whisper: RecognitionLines.txt not loaded — see MCM / config")
				Debug.Trace("PickmansWhisper: ERROR RecognitionLines.txt — " + RecognitionLoadStatus)
			Else
				LastFixationStatus = "recognition pick empty — bank " + RecognitionLoadStatus
				WriteFixationStatusToMcm()
				Debug.Trace("PickmansWhisper: ERROR recognition pick empty — bank ok (" + RecognitionLoadStatus + ")")
			EndIf
		EndIf
		Return
	EndIf
	ShowVoiceToast(line)
	If asleep
		Debug.Trace("PickmansWhisper: sleep recognition | " + line)
	Else
		Debug.Trace("PickmansWhisper: recognition | " + line)
	EndIf
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


; Digits only; trailing junk (CRLF leftover \r, spaces) ignored after the first digit.
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
	Bool gotDigit = False
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
			If gotDigit
				Return n
			EndIf
			Return -1
		EndIf
		gotDigit = True
		n = n * 10 + d
		i += 1
	EndWhile
	If !gotDigit
		Return -1
	EndIf
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
; Fail loud — never substitute. Skips if a clip is already PlayAndWait-ing.
Function PlayWhisperXwmByFile(String fileName)
	If !IsVoiceWeaponReady()
		Return
	EndIf
	If !fileName || GardenOfEden.StrLength(fileName) < 1
		Debug.Notification("Pickman's Whisper: empty audio filename")
		Debug.Trace("PickmansWhisper: ERROR PlayWhisperXwmByFile empty filename")
		Return
	EndIf
	If WhisperAudioBusy
		Debug.Trace("PickmansWhisper: PlayWhisperXwmByFile skip | audio busy | " + fileName)
		Return
	EndIf
	; Claim before NoWait so a second caller on another stack sees busy.
	WhisperAudioBusy = True
	Var[] args = new Var[1]
	args[0] = fileName
	CallFunctionNoWait("PlayWhisperXwmAndWait", args)
EndFunction


; Latent worker — PlayAndWait until the clip ends, then clear WhisperAudioBusy.
; Do not call synchronously from toast/fixation stacks (would freeze the game).
Function PlayWhisperXwmAndWait(String fileName)
	If !fileName || GardenOfEden.StrLength(fileName) < 1
		WhisperAudioBusy = False
		Debug.Notification("Pickman's Whisper: empty audio filename")
		Debug.Trace("PickmansWhisper: ERROR PlayWhisperXwmAndWait empty filename")
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
		WhisperAudioBusy = False
		Debug.Notification("Pickman's Whisper: empty audio leaf for " + fileName)
		Return
	EndIf
	Bool xwmOk = GardenOfEden2.DoesFileExist(leaf, dirPath)
	If !xwmOk
		WhisperAudioBusy = False
		Debug.Notification("Pickman's Whisper: missing xwm " + fileName)
		Debug.Trace("PickmansWhisper: ERROR PlayWhisperXwmAndWait xwm missing " + fileName + " path=" + dirPath)
		Return
	EndIf
	; WhisperSndrIds keys match the map line (forward-slash relative path).
	Int fid = FindWhisperSndrFid(fileName)
	If fid <= 0
		WhisperAudioBusy = False
		Debug.Notification("Pickman's Whisper: no SNDR id for " + fileName + " — rebuild ESP")
		Debug.Trace("PickmansWhisper: ERROR PlayWhisperXwmAndWait no FormID for " + fileName)
		Return
	EndIf
	If !Main().PlayerRef
		Main().PlayerRef = Game.GetPlayer()
	EndIf
	If !Main().PlayerRef
		WhisperAudioBusy = False
		Debug.Notification("Pickman's Whisper: audio play — no player")
		Return
	EndIf
	Sound snd = Game.GetFormFromFile(fid, "PickmansWhisper.esp") as Sound
	If !snd
		WhisperAudioBusy = False
		Debug.Notification("Pickman's Whisper: SNDR missing for " + fileName + " (fid=" + fid + ")")
		Debug.Trace("PickmansWhisper: ERROR PlayWhisperXwmAndWait GetFormFromFile failed fid=" + fid + " file=" + fileName)
		Return
	EndIf
	; Latent — holds this stack until the instance finishes (or fails).
	Bool ok = snd.PlayAndWait(Main().PlayerRef)
	WhisperAudioBusy = False
	If !ok
		Debug.Notification("Pickman's Whisper: PlayAndWait failed for " + fileName)
		Debug.Trace("PickmansWhisper: ERROR PlayWhisperXwmAndWait PlayAndWait=false file=" + fileName)
		Return
	EndIf
	LastAudioFile = fileName
	Debug.Trace("PickmansWhisper: PlayWhisperXwmAndWait done " + fileName)
EndFunction


; One modal dialog with the full step-by-step load trace (screenshot-friendly).
; MCM Debug "Test notice file load" only — never call from OnQuestInit / load resume.
Function ReportNoticeLoadStatus()
	String msg = "PICKMANS WHISPER NOTICE LOAD || " + NoticeLoadDiag
	Debug.Trace("PickmansWhisper notice load: " + msg)
	Main().DiagNotify(msg)
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
	MCM.SetModSettingString(Main().MOD_NAME, "sNoticeCalm:Debug", NoticeCalmStatus)
	MCM.SetModSettingString(Main().MOD_NAME, "sNoticeRestless:Debug", NoticeRestlessStatus)
	MCM.SetModSettingString(Main().MOD_NAME, "sNoticeHungry:Debug", NoticeHungryStatus)
	MCM.SetModSettingString(Main().MOD_NAME, "sNoticeStarving:Debug", NoticeStarvingStatus)
	MCM.SetModSettingString(Main().MOD_NAME, "sNoticeDesperate:Debug", NoticeDesperateStatus)
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
; Exposed for feature scripts (BedGift) that load banks via Main.
String Function GetLastStageLoadStatus()
	Return LastStageLoadStatus
EndFunction


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


; Whisper stage from hunger %: 0 calm / 1 restless / 2 hungry / 3 starving / 4 desperate.
; Read-only off HungerLevel — speaking a line never advances the stage.
Int Function GetNoticeStage()
	; Debug override: MCM "Force notice stage" pins the stage to the dropdown value
	; so each stage can be tested without grinding hunger. Off = derive from hunger.
	If IsNoticeStageForced()
		Int forced = MCM.GetModSettingInt(Main().MOD_NAME, "iNoticeStage:Debug")
		If forced < 0
			Return 0
		ElseIf forced > 4
			Return 4
		EndIf
		Return forced
	EndIf
	Float level = Main().HungerLevel
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
	Return MCM.GetModSettingBool(Main().MOD_NAME, "bForceNoticeStage:Debug")
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
	While tries < 8 && count > 1 && (raw == LastNoticeLine || (wantNameless && Main().StrContains(raw, "{name}")))
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

	; Main.ApplyNamePlaceholder strips {name} safely when there's no usable name.
	Return Main().ApplyNamePlaceholder(raw, useName)
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
	; Placeholder label from fixation / display fallbacks — not a real name.
	If npcName == "Unnamed" || npcName == "unnamed"
		Return ""
	EndIf
	If Main().StrContains(npcName, "Settler") || Main().StrContains(npcName, "Resident")
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
		If !c || !Main().StrContains(allowed, c)
			Return False
		EndIf
		If Main().StrContains(letters, c)
			hasLetter = True
		EndIf
		i += 1
	EndWhile
	Return hasLetter
EndFunction


; GoE string ops only — FO4 has no StringUtil (see no-fake-native-stubs).
; Façade — Main.ApplyNamePlaceholder is SSOT (StripNamePlaceholder lives there too).
String Function ApplyNamePlaceholder(String line, String npcName)
	If !Main()
		Return ""
	EndIf
	Return Main().ApplyNamePlaceholder(line, npcName)
EndFunction


Bool Function IsVoiceEnabled()
	If MCM.IsInstalled()
		Return MCM.GetModSettingBool(Main().MOD_NAME, "bVoiceToasts:Voice")
	EndIf
	Return True
EndFunction


; 0 = Toast + Audio (default), 1 = Audio only, 2 = Toast only.
Int Function GetVoiceDeliveryMode()
	If MCM.IsInstalled()
		Int v = MCM.GetModSettingInt(Main().MOD_NAME, "iVoiceDelivery:Voice")
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

Function DebugTestNoticeLine(Actor akTarget)
	If !Main().PlayerRef
		Main().PlayerRef = Game.GetPlayer()
	EndIf
	If !Main().BondStarted
		Main().DiagNotify("Pickman's Whisper — Notice\n\nBond first (gallery or blade).")
		Return
	EndIf
	If !IsVoiceEnabled()
		Main().DiagNotify("Pickman's Whisper — Notice\n\nEnable toast voice on the Voice page.")
		Return
	EndIf
	; Diagnostics: raw GoE counts before filters
	Float watchR = KillWatchRadius()
	Actor[] fem = GardenOfEden.FindActors(None, None, -1, -1, Main().PlayerRef, watchR, 1, 1, -1, 1, -1, -1, None, None, "", 0, 1, 1)
	Actor[] anyA = GardenOfEden.FindActors(None, None, -1, -1, Main().PlayerRef, watchR, 1, -1, -1, -1, -1, -1, None, None, "", 0, 1, 0)
	Int nFem = 0
	Int nAny = 0
	If fem
		nFem = fem.Length
	EndIf
	If anyA
		nAny = anyA.Length
	EndIf

	If !akTarget
		Main().DiagNotify("Pickman's Whisper — Notice [" + Main().DEBUG_BUILD + "]\n\nNo candidate.\nGoE female loaded: " + nFem + "\nGoE any living: " + nAny + "\nRadius: " + (watchR as Int) + "\nNeed adult female, not hostile, not essential.")
		Return
	EndIf
	String npcName = GetActorDisplayName(akTarget)
	String who = npcName
	If who == ""
		who = "id=" + akTarget.GetFormID()
	EndIf
	Int stage = GetNoticeStage()
	Int mode = GetVoiceDeliveryMode()
	If mode == 1
		Int aIdx = PickNoticeAudioIndex(stage)
		If aIdx < 0
			Main().DiagNotify("Pickman's Whisper — Notice [" + Main().DEBUG_BUILD + "]\n\nTarget: " + who + "\n\nAudio-only: no map for stage " + (stage + 1) + " (" + GetNoticeStageName(stage) + ").")
			Return
		EndIf
		PlayNoticeAudio(stage, aIdx)
		MarkNoticeCooldown(akTarget)
		Main().DiagNotify("Pickman's Whisper — Notice [" + Main().DEBUG_BUILD + "]\n\nTarget: " + who + "\nMode: Audio only\nIndex: " + aIdx)
		Return
	EndIf
	String line = PickNoticeLine(npcName)
	If line == ""
		Main().DiagNotify("Pickman's Whisper — Notice [" + Main().DEBUG_BUILD + "]\n\nTarget: " + who + "\n\nNo whisper: stage " + (stage + 1) + " (" + GetNoticeStageName(stage) + ") file not loaded.\ncalm: " + NoticeCalmStatus + "\nrestless: " + NoticeRestlessStatus + "\nhungry: " + NoticeHungryStatus + "\nstarving: " + NoticeStarvingStatus + "\ndesperate: " + NoticeDesperateStatus)
		Return
	EndIf
	MarkNoticeCooldown(akTarget)
	ToastNoticeLine(line)
	If mode == 0
		PlayNoticeAudio(stage, LastNoticePickIndex)
	EndIf
	Main().DiagNotify("Pickman's Whisper — Notice [" + Main().DEBUG_BUILD + "]\n\nTarget: " + who + "\nGoE female: " + nFem + " any: " + nAny + "\nMode: " + mode + " idx: " + LastNoticePickIndex + "\n\n" + line)
EndFunction


; MCM Debug — DiagNotify with every gate that can silence whispers.
Function DebugVoicePathDump()
	If !Main().PlayerRef
		Main().PlayerRef = Game.GetPlayer()
	EndIf
	Bool voiceOn = IsVoiceEnabled()
	Bool blade = Main().IsBladeEquipped()
	Bool voiceReady = IsVoiceWeaponReady()
	Float hoursLeft = 0.0
	If LastNoticeToastGameTime > 0.0
		Float hoursSince = (Utility.GetCurrentGameTime() - LastNoticeToastGameTime) * 24.0
		hoursLeft = NOTICE_MIN_GAME_HOURS - hoursSince
		If hoursLeft < 0.0
			hoursLeft = 0.0
		EndIf
	EndIf
	String body = "Pickman's Whisper — VOICE PATH DUMP\n\n"
	body += "BondStarted=" + Main().BondStarted + "\n"
	body += "Voice enabled=" + voiceOn + "\n"
	body += "Blade drawn=" + blade + " voiceReady=" + voiceReady + "\n"
	body += "Drawn: " + Main().GetDrawnWeaponDebugName() + "\n"
	String dispatch = ""
	If MCM.IsInstalled()
		dispatch = MCM.GetModSettingString(Main().MOD_NAME, "sVoiceDispatch:Debug")
	EndIf
	If !dispatch
		dispatch = "(none yet — see Papyrus Trace)"
	EndIf
	body += "VoiceAlias=OK\n"
	body += "Dispatch: " + dispatch + "\n"
	body += "Notice: " + LastNoticeStatus + "\n"
	body += "Nearby: " + LastNearbySummary + "\n"
	body += "Fixation: " + LastFixationStatus + "\n"
	body += "Hunger cooldown left (game h): " + hoursLeft + "\n"
	body += "\nPapyrus log (if enabled):\nDocuments\\My Games\\Fallout4\\Logs\\Script\\Papyrus.0.log\nFilter: PickmansWhisper"
	Debug.Trace("PickmansWhisper: VoicePathDump | " + body)
	Main().DiagNotify(body)
EndFunction
