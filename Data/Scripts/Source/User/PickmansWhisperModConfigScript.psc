Scriptname PickmansWhisperModConfigScript extends ReferenceAlias
{ModConfig.txt owner — load/parse on Main ALST ModConfigAlias (UniqueActor=Player).
Toast/float keys + decayStage0..4 live/pending arrays. Main keeps thin façades.}

; Loaded from ModConfig.txt — files-only, no baked mirror.
; Properties: Main (and other scripts) may read via ModConfigAlias.*; locals stay private.
String Property BondIntroGreeting = "" Auto
String Property HungerWithdrawalToast = "" Auto
String Property RenamePromptFemaleNPC = "" Auto
String Property BedGiftWakeToast = "" Auto
String Property DesperateNameSuffix = "" Auto
Float Property BedGiftCooldownDays = -1.0 Auto
Float Property BedGiftWoundAlpha = -1.0 Auto
String Property NamedKillToast = "" Auto
String Property NamedKillAudio = "" Auto
String Property EatRipeCorpseToast = "" Auto
String Property AteRipeCorpseToast = "" Auto
Float Property EatRipeCorpseEndBuffAmount = -1.0 Auto
Float Property EatRipeCorpseEndBuffMaxDelta = -1.0 Auto
Float Property EatRipeCorpseEndBuffHours = -1.0 Auto
String Property ModConfigLoadStatus = "" Auto
Bool ModConfigLoadBusy = False

Int Property DECAY_STAGE_COUNT = 5 Auto
String[] DecayStageNames
Float[] DecayStageTintR
Float[] DecayStageTintG
Float[] DecayStageTintB
Float[] DecayStageTintA
Float[] DecayStageStartHours
String[] DecayStageSkinsRaw
Bool[] DecayStageAllScars
Int DecayStagesLoadedCount = 0

String[] PendingDecayStageNames
Float[] PendingDecayStageTintR
Float[] PendingDecayStageTintG
Float[] PendingDecayStageTintB
Float[] PendingDecayStageTintA
Float[] PendingDecayStageStartHours
String[] PendingDecayStageSkinsRaw
Bool[] PendingDecayStageAllScars
Int PendingDecayStagesFilled = 0

Event OnAliasInit()
	LoadModConfig()
EndEvent

PickmansWhisperMainQuestScript Function Main()
	Return GetOwningQuest() as PickmansWhisperMainQuestScript
EndFunction

; Same path as Main.NoticeConfigPath — local so load works without Main round-trip.
String Function ConfigPath()
	Return ".\\Data\\PickmansWhisper\\config\\"
EndFunction

String Function ConfigFieldTrim(String s)
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

Int Function SplitByChar(String s, String sep, String[] out)
	If !out || !sep || GardenOfEden.StrLength(sep) != 1
		Return 0
	EndIf
	Int outMax = out.Length
	If outMax <= 0
		Return 0
	EndIf
	If !s
		Return 0
	EndIf
	Int n = 0
	Int start = 0
	Int len = GardenOfEden.StrLength(s)
	Int i = 0
	While i <= len && n < outMax
		Bool atEnd = (i == len)
		Bool isSep = False
		If !atEnd
			If GardenOfEden.SubStr(s, i, 1) == sep
				isSep = True
			EndIf
		EndIf
		If atEnd || isSep
			Int flen = i - start
			If flen < 0
				flen = 0
			EndIf
			out[n] = ConfigFieldTrim(GardenOfEden.SubStr(s, start, flen))
			n += 1
			start = i + 1
		EndIf
		i += 1
	EndWhile
	Return n
EndFunction

Bool Function IsModConfigLoadBusy()
	Return ModConfigLoadBusy
EndFunction

; Boot load is OnAliasInit only — no nested/retry LoadModConfig here.
Bool Function EnsureDecayStagesLoaded()
	Return DecayStagesReady()
EndFunction

Function EnsureDecayStageArrays()
	If !DecayStageNames || DecayStageNames.Length != DECAY_STAGE_COUNT
		DecayStageNames = new String[5]
		DecayStageTintR = new Float[5]
		DecayStageTintG = new Float[5]
		DecayStageTintB = new Float[5]
		DecayStageTintA = new Float[5]
		DecayStageStartHours = new Float[5]
		DecayStageSkinsRaw = new String[5]
		DecayStageAllScars = new Bool[5]
	EndIf
EndFunction

Function EnsurePendingDecayStageArrays()
	If !PendingDecayStageNames || PendingDecayStageNames.Length != DECAY_STAGE_COUNT
		PendingDecayStageNames = new String[5]
		PendingDecayStageTintR = new Float[5]
		PendingDecayStageTintG = new Float[5]
		PendingDecayStageTintB = new Float[5]
		PendingDecayStageTintA = new Float[5]
		PendingDecayStageStartHours = new Float[5]
		PendingDecayStageSkinsRaw = new String[5]
		PendingDecayStageAllScars = new Bool[5]
	EndIf
EndFunction

Function ClearPendingDecayStages()
	EnsurePendingDecayStageArrays()
	PendingDecayStagesFilled = 0
	Int i = 0
	While i < DECAY_STAGE_COUNT
		PendingDecayStageNames[i] = ""
		PendingDecayStageTintR[i] = 0.0
		PendingDecayStageTintG[i] = 0.0
		PendingDecayStageTintB[i] = 0.0
		PendingDecayStageTintA[i] = 0.0
		PendingDecayStageStartHours[i] = -1.0
		PendingDecayStageSkinsRaw[i] = ""
		PendingDecayStageAllScars[i] = False
		i += 1
	EndWhile
EndFunction

; Commit pending → live only after a complete good parse (never wipe live mid-load).
Function CommitPendingDecayStages()
	EnsureDecayStageArrays()
	EnsurePendingDecayStageArrays()
	Int i = 0
	While i < DECAY_STAGE_COUNT
		DecayStageNames[i] = PendingDecayStageNames[i]
		DecayStageTintR[i] = PendingDecayStageTintR[i]
		DecayStageTintG[i] = PendingDecayStageTintG[i]
		DecayStageTintB[i] = PendingDecayStageTintB[i]
		DecayStageTintA[i] = PendingDecayStageTintA[i]
		DecayStageStartHours[i] = PendingDecayStageStartHours[i]
		DecayStageSkinsRaw[i] = PendingDecayStageSkinsRaw[i]
		DecayStageAllScars[i] = PendingDecayStageAllScars[i]
		i += 1
	EndWhile
	DecayStagesLoadedCount = DECAY_STAGE_COUNT
EndFunction

; Parse name;r;g;b;a;startHours;skins[+…];scars? into Pending* (not live).
; skins=none means no body overlays (default body; face still applies).
Bool Function ParseDecayStageValue(Int aiStage, String val)
	If aiStage < 0 || aiStage >= DECAY_STAGE_COUNT
		Return False
	EndIf
	If !val || val == ""
		Return False
	EndIf
	EnsurePendingDecayStageArrays()
	String[] fields = new String[9]
	Int n = SplitByChar(val, ";", fields)
	If n < 7
		Debug.Trace("PickmansWhisper: ERROR decayStage" + aiStage + " needs name;r;g;b;a;startHours;skins — got " + n + " fields")
		Return False
	EndIf
	String name = fields[0]
	String skins = fields[6]
	If !name || name == "" || !skins || skins == ""
		Debug.Trace("PickmansWhisper: ERROR decayStage" + aiStage + " empty name or skins (use none for no body)")
		Return False
	EndIf
	Float r = fields[1] as Float
	Float g = fields[2] as Float
	Float b = fields[3] as Float
	Float a = fields[4] as Float
	Float startH = fields[5] as Float
	If startH < 0.0
		Debug.Trace("PickmansWhisper: ERROR decayStage" + aiStage + " startHours must be >= 0")
		Return False
	EndIf
	Bool scars = False
	If n >= 8 && fields[7] == "scars"
		scars = True
	EndIf
	; none = intentional empty body bank (still a valid ModConfig field).
	If skins == "none"
		If scars
			Debug.Trace("PickmansWhisper: ERROR decayStage" + aiStage + " skins=none cannot use scars")
			Return False
		EndIf
	EndIf
	PendingDecayStageNames[aiStage] = name
	PendingDecayStageTintR[aiStage] = r
	PendingDecayStageTintG[aiStage] = g
	PendingDecayStageTintB[aiStage] = b
	PendingDecayStageTintA[aiStage] = a
	PendingDecayStageStartHours[aiStage] = startH
	PendingDecayStageSkinsRaw[aiStage] = skins
	PendingDecayStageAllScars[aiStage] = scars
	Return True
EndFunction

Bool Function DecayStagesReady()
	Return DecayStagesLoadedCount == DECAY_STAGE_COUNT
EndFunction

; True if startHours[0..4] are nondecreasing (required for threshold resolve).
Bool Function DecayStageHoursOrdered()
	If !DecayStagesReady()
		Return False
	EndIf
	Int i = 1
	While i < DECAY_STAGE_COUNT
		If DecayStageStartHours[i] < DecayStageStartHours[i - 1]
			Return False
		EndIf
		i += 1
	EndWhile
	Return True
EndFunction

Bool Function PendingDecayStageHoursOrdered()
	EnsurePendingDecayStageArrays()
	Int i = 1
	While i < DECAY_STAGE_COUNT
		If PendingDecayStageStartHours[i] < PendingDecayStageStartHours[i - 1]
			Return False
		EndIf
		i += 1
	EndWhile
	Return True
EndFunction

String Function GetDecayStageName(Int aiStage)
	If !DecayStagesReady() || aiStage < 0 || aiStage >= DECAY_STAGE_COUNT
		Return ""
	EndIf
	Return DecayStageNames[aiStage]
EndFunction

Float Function GetDecayStageTintR(Int aiStage)
	If !DecayStagesReady() || aiStage < 0 || aiStage >= DECAY_STAGE_COUNT
		Return 0.0
	EndIf
	Return DecayStageTintR[aiStage]
EndFunction

Float Function GetDecayStageTintG(Int aiStage)
	If !DecayStagesReady() || aiStage < 0 || aiStage >= DECAY_STAGE_COUNT
		Return 0.0
	EndIf
	Return DecayStageTintG[aiStage]
EndFunction

Float Function GetDecayStageTintB(Int aiStage)
	If !DecayStagesReady() || aiStage < 0 || aiStage >= DECAY_STAGE_COUNT
		Return 0.0
	EndIf
	Return DecayStageTintB[aiStage]
EndFunction

Float Function GetDecayStageTintA(Int aiStage)
	If !DecayStagesReady() || aiStage < 0 || aiStage >= DECAY_STAGE_COUNT
		Return 0.0
	EndIf
	Return DecayStageTintA[aiStage]
EndFunction

Float Function GetDecayStageStartHours(Int aiStage)
	If !DecayStagesReady() || aiStage < 0 || aiStage >= DECAY_STAGE_COUNT
		Return -1.0
	EndIf
	Return DecayStageStartHours[aiStage]
EndFunction

Bool Function GetDecayStageAllScars(Int aiStage)
	If !DecayStagesReady() || aiStage < 0 || aiStage >= DECAY_STAGE_COUNT
		Return False
	EndIf
	Return DecayStageAllScars[aiStage]
EndFunction

; Highest stage with startHours <= elapsedHours. -1 if stages not ready.
Int Function ResolveDecayStageFromElapsedHours(Float afElapsedHours)
	If !DecayStagesReady()
		Return -1
	EndIf
	Float elapsed = afElapsedHours
	If elapsed < 0.0
		elapsed = 0.0
	EndIf
	Int stage = 0
	Int i = 0
	While i < DECAY_STAGE_COUNT
		If elapsed >= DecayStageStartHours[i]
			stage = i
		EndIf
		i += 1
	EndWhile
	Return stage
EndFunction

; Expand skins[+skin…] into outTemplates; returns count.
Int Function FillDecayStageSkins(Int aiStage, String[] outTemplates)
	If !outTemplates || !DecayStagesReady() || aiStage < 0 || aiStage >= DECAY_STAGE_COUNT
		Return 0
	EndIf
	String raw = DecayStageSkinsRaw[aiStage]
	If !raw || raw == "" || raw == "none"
		Return 0
	EndIf
	Return SplitByChar(raw, "+", outTemplates)
EndFunction

; ModConfig.txt — key=value prompts / toggles. Files-only (no baked mirror).
; E4/E5: intimacy toast+audio live in necromantic/Intimacy_*_Named.txt / *_Audio.txt.
; Decay stages: parse into Pending* then Commit — never Clear live mid-load (Sync race).
Function LoadModConfig()
	If ModConfigLoadBusy
		Debug.Trace("PickmansWhisper: LoadModConfig skipped — already in progress")
		Return
	EndIf
	ModConfigLoadBusy = True
	; Parse into locals, commit to the live fields only after a full successful read —
	; same "Pending then Commit" principle as decay stages below. Clearing the live
	; fields up front (old behavior) left a window where a concurrently-dispatched
	; reader (e.g. DesperateRenameScript.SyncFromKillerScanSnapshot, KillerScan-fired
	; mid-reload) would read "" instead of the real value. Confirmed live: frequent
	; reload triggers (loading screens re-run HandleGameResume -> LoadLineBanks ->
	; LoadModConfig) raced ambient reads often enough to flicker desperateNameSuffix
	; empty for seconds at a time.
	String nextBondIntroGreeting = ""
	String nextHungerWithdrawalToast = ""
	String nextRenamePromptFemaleNPC = ""
	String nextBedGiftWakeToast = ""
	Float nextBedGiftCooldownDays = -1.0
	Float nextBedGiftWoundAlpha = -1.0
	String nextDesperateNameSuffix = ""
	String nextNamedKillToast = ""
	String nextNamedKillAudio = ""
	String nextEatRipeCorpseToast = ""
	String nextAteRipeCorpseToast = ""
	Float nextEatRipeCorpseEndBuffAmount = -1.0
	Float nextEatRipeCorpseEndBuffMaxDelta = -1.0
	Float nextEatRipeCorpseEndBuffHours = -1.0
	ClearPendingDecayStages()
	String fileName = "ModConfig.txt"
	String path = ConfigPath()
	; Do NOT touch ModConfigLoadStatus / live fields on a failed read — leave whatever
	; the last successful load produced in place rather than blanking it out.
	If !GardenOfEden2.DoesFileExist(fileName, path)
		Debug.Trace("PickmansWhisper: ERROR ModConfig.txt — MISSING FILE (" + path + fileName + ")")
		ModConfigLoadBusy = False
		Return
	EndIf
	String[] raw = GardenOfEden2.GetLinesFromFile(fileName, path)
	If !raw || raw.Length == 0
		Debug.Trace("PickmansWhisper: ERROR ModConfig.txt — EMPTY/UNREADABLE")
		ModConfigLoadBusy = False
		Return
	EndIf
	Int i = 0
	While i < raw.Length
		; Space-only trim — GetWords/TrimString mangles decayStage semicolon values.
		String line = ConfigFieldTrim(raw[i])
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
				String key = ConfigFieldTrim(GardenOfEden.SubStr(line, 0, eq))
				String val = ConfigFieldTrim(GardenOfEden.SubStr(line, eq + 1, -1))
				If key == "bondIntroGreeting"
					nextBondIntroGreeting = val
				ElseIf key == "hungerWithdrawalToast"
					nextHungerWithdrawalToast = val
				ElseIf key == "renamePromptFemaleNPC"
					nextRenamePromptFemaleNPC = val
				ElseIf key == "bedGiftWakeToast"
					nextBedGiftWakeToast = val
				ElseIf key == "desperateNameSuffix"
					; Keep leading/trailing spaces — " Dumb Bitch" is intentional.
					nextDesperateNameSuffix = GardenOfEden.SubStr(line, eq + 1, -1)
				ElseIf key == "bedGiftCooldownDays"
					If val && GardenOfEden.StrLength(val) > 0
						Float days = val as Float
						If days > 0.0
							nextBedGiftCooldownDays = days
						EndIf
					EndIf
				ElseIf key == "bedGiftWoundAlpha"
					If val && GardenOfEden.StrLength(val) > 0
						Float a = val as Float
						If a >= 0.0 && a <= 1.0
							nextBedGiftWoundAlpha = a
						EndIf
					EndIf
				ElseIf key == "namedKillToast"
					nextNamedKillToast = val
				ElseIf key == "namedKillAudio"
					nextNamedKillAudio = val
				ElseIf key == "eatRipeCorpseToast"
					nextEatRipeCorpseToast = val
				ElseIf key == "ateRipeCorpseToast"
					nextAteRipeCorpseToast = val
				ElseIf key == "ateRipeCorpseEndBuffAmount"
					If val && GardenOfEden.StrLength(val) > 0
						Float endAmt = val as Float
						If endAmt > 0.0
							nextEatRipeCorpseEndBuffAmount = endAmt
						EndIf
					EndIf
				ElseIf key == "ateRipeCorpseEndBuffMaxDelta"
					If val && GardenOfEden.StrLength(val) > 0
						Float endMax = val as Float
						If endMax > 0.0
							nextEatRipeCorpseEndBuffMaxDelta = endMax
						EndIf
					EndIf
				ElseIf key == "ateRipeCorpseEndBuffHours"
					If val && GardenOfEden.StrLength(val) > 0
						Float endHours = val as Float
						If endHours > 0.0
							nextEatRipeCorpseEndBuffHours = endHours
						EndIf
					EndIf
				ElseIf key == "decayStage0"
					ParseDecayStageValue(0, val)
				ElseIf key == "decayStage1"
					ParseDecayStageValue(1, val)
				ElseIf key == "decayStage2"
					ParseDecayStageValue(2, val)
				ElseIf key == "decayStage3"
					ParseDecayStageValue(3, val)
				ElseIf key == "decayStage4"
					ParseDecayStageValue(4, val)
				EndIf
			EndIf
		EndIf
	EndWhile
	; Commit all-or-nothing, now that the full file read succeeded — no reader can
	; observe a half-cleared state.
	BondIntroGreeting = nextBondIntroGreeting
	HungerWithdrawalToast = nextHungerWithdrawalToast
	RenamePromptFemaleNPC = nextRenamePromptFemaleNPC
	BedGiftWakeToast = nextBedGiftWakeToast
	BedGiftCooldownDays = nextBedGiftCooldownDays
	BedGiftWoundAlpha = nextBedGiftWoundAlpha
	DesperateNameSuffix = nextDesperateNameSuffix
	NamedKillToast = nextNamedKillToast
	NamedKillAudio = nextNamedKillAudio
	EatRipeCorpseToast = nextEatRipeCorpseToast
	AteRipeCorpseToast = nextAteRipeCorpseToast
	EatRipeCorpseEndBuffAmount = nextEatRipeCorpseEndBuffAmount
	EatRipeCorpseEndBuffMaxDelta = nextEatRipeCorpseEndBuffMaxDelta
	EatRipeCorpseEndBuffHours = nextEatRipeCorpseEndBuffHours
	If !BondIntroGreeting
		Debug.Trace("PickmansWhisper: ERROR ModConfig.txt — bondIntroGreeting missing/empty")
	EndIf
	If !HungerWithdrawalToast
		Debug.Trace("PickmansWhisper: ERROR ModConfig.txt — hungerWithdrawalToast missing/empty")
	EndIf
	If BedGiftCooldownDays <= 0.0
		Debug.Trace("PickmansWhisper: ERROR ModConfig.txt — bedGiftCooldownDays missing or <=0")
	EndIf
	If BedGiftWoundAlpha < 0.0
		Debug.Trace("PickmansWhisper: ERROR ModConfig.txt — bedGiftWoundAlpha missing or out of 0..1")
	EndIf
	Int filled = 0
	Int si = 0
	While si < DECAY_STAGE_COUNT
		If PendingDecayStageNames[si] != "" && PendingDecayStageSkinsRaw[si] != "" && PendingDecayStageStartHours[si] >= 0.0
			filled += 1
		EndIf
		si += 1
	EndWhile
	PendingDecayStagesFilled = filled
	Bool stagesOk = False
	If filled == DECAY_STAGE_COUNT
		If PendingDecayStageHoursOrdered()
			CommitPendingDecayStages()
			stagesOk = True
			; Face banks only when stages actually committed (not mid-flight wipe).
			PickmansWhisperCorpseDecayScript decay = GetOwningQuest() as PickmansWhisperCorpseDecayScript
			If decay
				decay.InvalidateDecayFaceArmorBanks()
				; Eager NoWait preload was tried here and reverted — it added a constantly
				; re-competing background call (never once completed in testing) that
				; correlated with much worse despawn delays (5-10s baseline -> 80-130s+).
				; Face mask reliability is a dropped stretch goal; spawn/despawn reliability
				; is not. Stay fully lazy — only load when an actual decay apply needs it.
			EndIf
		Else
			Debug.Trace("PickmansWhisper: ERROR ModConfig.txt — decayStage startHours must be nondecreasing 0..4 (live stages kept)")
		EndIf
	Else
		Debug.Trace("PickmansWhisper: ERROR ModConfig.txt — decayStage0..4 incomplete (" + filled + "/" + DECAY_STAGE_COUNT + ") — live stages kept")
	EndIf
	String status = ""
	If BondIntroGreeting
		status += "bondIntro "
	EndIf
	If HungerWithdrawalToast
		status += "hungerWithdraw "
	EndIf
	If RenamePromptFemaleNPC
		status += "rename "
	EndIf
	If BedGiftWakeToast
		status += "bedGift "
	EndIf
	If BedGiftCooldownDays > 0.0
		status += "bedCooldown "
	EndIf
	If BedGiftWoundAlpha >= 0.0
		status += "bedWoundA "
	EndIf
	If NamedKillToast
		status += "namedKill "
	EndIf
	If stagesOk
		status += "decayStages "
	EndIf
	If status != ""
		ModConfigLoadStatus = ConfigFieldTrim(status) + "ok"
		Debug.Trace("PickmansWhisper: ModConfig ready | " + ModConfigLoadStatus)
	Else
		ModConfigLoadStatus = "no known keys"
		Debug.Trace("PickmansWhisper: ERROR ModConfig.txt — " + ModConfigLoadStatus)
	EndIf
	ModConfigLoadBusy = False
EndFunction

; Exposed for BedGiftScript wake toast (ModConfig bedGiftWakeToast).
String Function GetBedGiftWakeToast()
	Return BedGiftWakeToast
EndFunction

; Slice I — ModConfig desperateNameSuffix (may include leading space). Empty = idle.
String Function GetDesperateNameSuffix()
	Return DesperateNameSuffix
EndFunction

; Exposed for BedGiftScript cooldown (ModConfig bedGiftCooldownDays). <=0 = missing/invalid.
Float Function GetBedGiftCooldownDays()
	Return BedGiftCooldownDays
EndFunction

; Exposed for CorpseDecay bed wounds (ModConfig bedGiftWoundAlpha). <0 = missing/invalid.
Float Function GetBedGiftWoundAlpha()
	Return BedGiftWoundAlpha
EndFunction

Float Function GetEatRipeCorpseEndBuffAmount()
	Return EatRipeCorpseEndBuffAmount
EndFunction

Float Function GetEatRipeCorpseEndBuffMaxDelta()
	Return EatRipeCorpseEndBuffMaxDelta
EndFunction

Float Function GetEatRipeCorpseEndBuffHours()
	Return EatRipeCorpseEndBuffHours
EndFunction

