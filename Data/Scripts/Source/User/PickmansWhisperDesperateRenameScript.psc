Scriptname PickmansWhisperDesperateRenameScript extends Quest
{Slice I — at desperate hunger, append ModConfig suffix to nearby NPC display names.}

String Property LastDesperateRenameStatus = "" Auto
Bool SuffixMissingToasted = False

PickmansWhisperMainQuestScript Function Main()
	Return (Self as Quest) as PickmansWhisperMainQuestScript
EndFunction

PickmansWhisperKillerScanScript Function KillerScan()
	Return (Self as Quest) as PickmansWhisperKillerScanScript
EndFunction

Function SetStatus(String reason)
	LastDesperateRenameStatus = reason
	Debug.Trace("PickmansWhisper: desperate rename | " + reason)
EndFunction

; Toast / GetActorDisplayName — append while desperate if not already present.
String Function MaybeSuffixDisplayName(Actor ak, String baseName)
	If !baseName
		Return ""
	EndIf
	PickmansWhisperMainQuestScript m = Main()
	If !m || m.GetNoticeStage() != 4
		Return baseName
	EndIf
	If !m.ModConfigAlias
		Return baseName
	EndIf
	String suffix = m.ModConfigAlias.GetDesperateNameSuffix()
	If !suffix
		Return baseName
	EndIf
	If NameHasSuffix(baseName, suffix)
		Return baseName
	EndIf
	Return baseName + suffix
EndFunction

Bool Function NameHasSuffix(String name, String suffix)
	If !name || !suffix
		Return False
	EndIf
	Int nLen = GardenOfEden.StrLength(name)
	Int sLen = GardenOfEden.StrLength(suffix)
	If sLen < 1 || nLen < sLen
		Return False
	EndIf
	Return GardenOfEden.SubStr(name, nLen - sLen, sLen) == suffix
EndFunction

String Function StripSuffix(String name, String suffix)
	If !NameHasSuffix(name, suffix)
		Return name
	EndIf
	Int nLen = GardenOfEden.StrLength(name)
	Int sLen = GardenOfEden.StrLength(suffix)
	If nLen <= sLen
		Return ""
	EndIf
	Return GardenOfEden.SubStr(name, 0, nLen - sLen)
EndFunction

; Core label without our suffix (victim override / display / base).
String Function ResolveBaseLabel(Actor ak, String suffix)
	If !ak
		Return ""
	EndIf
	PickmansWhisperMainQuestScript m = Main()
	If !m
		Return ""
	EndIf
	String overrideName = m.GetVictimOverrideName(ak)
	If overrideName
		Return StripSuffix(overrideName, suffix)
	EndIf
	String disp = ak.GetDisplayName()
	If disp
		Return StripSuffix(disp, suffix)
	EndIf
	ActorBase base = ak.GetLeveledActorBase()
	If !base
		Return ""
	EndIf
	Return StripSuffix(base.GetName(), suffix)
EndFunction

; Dedicated, stricter than the shared ambient notice filter: that filter allows
; synths through ("look human") and doesn't gate on hostility — fine for whispers,
; wrong for renaming.
; Codsworth (male robot companion) slipped through it once; this does not repeat
; that: explicit non-companion + non-hostile + strict human check (no synth
; carve-out) + adult female, on top of the usual essential/child safety nets.
Bool Function IsRenameEligible(Actor ak)
	PickmansWhisperMainQuestScript m = Main()
	If !m || !ak
		Return False
	EndIf
	Actor player = Game.GetPlayer()
	If ak == player || ak.IsDead() || ak.IsDisabled()
		Return False
	EndIf
	If ak.IsPlayerTeammate()
		Return False
	EndIf
	; Ambient whispers intentionally ignore hostility (settlers who aggro after being
	; seen friendly still need kill credit); renaming has no such reason to allow it.
	If player && ak.IsHostileToActor(player)
		Return False
	EndIf
	If m.IsStoryEssential(ak)
		Return False
	EndIf
	If m.IsChildNpc(ak) && !m.IsChildTargetAllowed()
		Return False
	EndIf
	; Strict human check — hard-excludes synths too, requires a positive
	; ActorTypeNPC/ActorTypeHuman keyword match rather than just "not excluded."
	If !m.IsHumanNpc(ak)
		Return False
	EndIf
	Return m.IsAdultFemale(ak)
EndFunction

Function ApplySuffixToActor(Actor ak, String suffix)
	If !ak || !suffix
		Return
	EndIf
	If !IsRenameEligible(ak)
		; Self-heal: if she somehow got suffixed while ineligible (edge case in the
		; shared notice filter — e.g. a keyword/sex mismatch), strip it back instead
		; of leaving a permanent mislabel until hunger drops out of desperate stage.
		StripSuffixFromActor(ak, suffix)
		Return
	EndIf
	String baseLabel = ResolveBaseLabel(ak, suffix)
	If !baseLabel
		Return
	EndIf
	String want = baseLabel + suffix
	String cur = ak.GetDisplayName()
	If cur == want
		Return
	EndIf
	Bool ok = GardenOfEden2.SetDisplayName(ak, want)
	If ak.GetDisplayName() != want
		Debug.Trace("PickmansWhisper: ERROR desperate rename SetDisplayName want='" + want + "' got='" + ak.GetDisplayName() + "' goe=" + ok)
	EndIf
EndFunction

Function StripSuffixFromActor(Actor ak, String suffix)
	If !ak || !suffix
		Return
	EndIf
	String cur = ak.GetDisplayName()
	If !NameHasSuffix(cur, suffix)
		Return
	EndIf
	String restored = StripSuffix(cur, suffix)
	If !restored
		Return
	EndIf
	GardenOfEden2.SetDisplayName(ak, restored)
EndFunction

; KillerScan NoWait — consume TargetSnapshot only (no FindActors).
Function SyncFromKillerScanSnapshot()
	PickmansWhisperMainQuestScript m = Main()
	If !m
		SetStatus("ERROR: Main missing")
		Return
	EndIf
	PickmansWhisperKillerScanScript ks = KillerScan()
	If !ks
		SetStatus("ERROR: KillerScan missing")
		Return
	EndIf
	If !m.ModConfigAlias
		SetStatus("ERROR: ModConfigAlias unbound")
		Return
	EndIf
	String suffix = m.ModConfigAlias.GetDesperateNameSuffix()
	If !suffix
		If !SuffixMissingToasted
			SuffixMissingToasted = True
			Debug.Trace("PickmansWhisper: desperateNameSuffix missing/empty — rename idle (edit ModConfig.txt)")
		EndIf
		SetStatus("idle: no desperateNameSuffix")
		Return
	EndIf
	SuffixMissingToasted = False
	Bool desperate = (m.GetNoticeStage() == 4)
	Actor[] alive = ks.ScanAlive
	Int n = ks.ScanAliveCount
	If !alive || n <= 0
		SetStatus("idle: no ScanAlive")
		Return
	EndIf
	Int i = 0
	Int touched = 0
	While i < n && i < alive.Length
		Actor ak = alive[i]
		i += 1
		If ak
			If desperate
				ApplySuffixToActor(ak, suffix)
				touched += 1
			Else
				StripSuffixFromActor(ak, suffix)
			EndIf
		EndIf
	EndWhile
	If desperate
		SetStatus("applied stage=desperate near=" + touched + " suffix='" + suffix + "'")
	Else
		SetStatus("stripped (not desperate) near=" + touched)
	EndIf
EndFunction
