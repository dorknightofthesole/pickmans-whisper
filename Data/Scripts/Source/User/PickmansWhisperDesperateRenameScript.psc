Scriptname PickmansWhisperDesperateRenameScript extends Quest
{Slice I — at desperate hunger, append ModConfig suffix to nearby NPC display names.}

String Property LastDesperateRenameStatus = "" Auto
Bool SuffixMissingToasted = False

PickmansWhisperMainQuestScript Function Main()
	Return (Self as Quest) as PickmansWhisperMainQuestScript
EndFunction

Function SetStatus(String reason)
	LastDesperateRenameStatus = reason
	Debug.Trace("PickmansWhisper: desperate rename | " + reason)
EndFunction

; Aim-driven (Main.LookingAtTarget → DesperateRename() façade → here).
Function DesperateRename(Actor akTarget)
	If !akTarget
		Debug.Trace("PickmansWhisper: DesperateRename skip | no actor")
		Return
	EndIf
	PickmansWhisperMainQuestScript m = Main()
	If !m
		SetStatus("ERROR: Main missing")
		Return
	EndIf
	If !m.VoiceAlias
		SetStatus("ERROR: VoiceAlias unbound")
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

	Bool desperate = (m.VoiceAlias.GetNoticeStage() == 4)
	If desperate
		ApplySuffixToActor(akTarget, suffix)
		SetStatus("applied stage=desperate aim='" + akTarget.GetDisplayName() + "' suffix='" + suffix + "'")
	Else
		StripSuffixFromActor(akTarget, suffix)
		SetStatus("stripped (not desperate) aim='" + akTarget.GetDisplayName() + "'")
	EndIf
EndFunction

; Toast / GetActorDisplayName — append while desperate if not already present.
String Function MaybeSuffixDisplayName(Actor ak, String baseName)
	Debug.Notification("PW Debug: MaybeSuffixDisplayName " + baseName)
	If !baseName
		Return ""
	EndIf
	PickmansWhisperMainQuestScript m = Main()
	If !m || !m.VoiceAlias || m.VoiceAlias.GetNoticeStage() != 4
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

; Hard gate + rename feature: living only.
Bool Function IsRenameEligible(Actor ak)
	PickmansWhisperMainQuestScript m = Main()
	If !m || !ak || ak.IsDead()
		Return False
	EndIf
	Return m.IsValidTarget(ak)
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
