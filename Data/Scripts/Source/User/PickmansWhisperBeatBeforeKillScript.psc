Scriptname PickmansWhisperBeatBeforeKillScript extends Quest
{Slice K — victim beat-before-kill (temp essential; was roadmap Q / earlier J).
K1: manual MCM Victims toggle (dialog-free — MCM's own status row is its feedback).
K2–K5: Apply / clear via HandleBeatBeforeKill(Actor) using wired PlayerAlias blade/unarmed flags.
Weapon-equip clear-all also from PlayerAlias (any weapon) + KillerScan TickEssentialReconcile safety net.

REMOVED — "out of combat -> clear essential" (both the direct OnCombatStateChanged(0)
handler and the reconcile poll's !IsInCombat() check): confirmed via live log evidence
this actively broke the feature. Weapon-equip is the only reversal now.}

; CK/VMAD: bound to PickmansWhisperPlayerCombat ALST 0 (same as Main.PlayerAlias).
PickmansWhisperPlayerAliasScript Property PlayerAlias Auto Const

PickmansWhisperMainQuestScript Function Main()
	Return (Self as Quest) as PickmansWhisperMainQuestScript
EndFunction

; Actors WE set essential=True on via this system (J1's manual toggle or J2's auto
; trigger — same list either way). Never touch essential state for anyone not in this
; list — an NPC essential for any other reason was never eligible to be added here
; (IsValidTarget already excludes anyone currently essential), so this list existing is
; proof enough that toggling her back off is safe. Actor refs (not FormIDs) so the
; weapon-equip / reconcile sweeps can act on them directly without re-resolving.
Actor[] EssentialActors
Int EssentialCount = 0
Int ESSENTIAL_MAX = 16

Function EnsureEssentialList()
	If !EssentialActors || EssentialActors.Length != ESSENTIAL_MAX
		EssentialActors = new Actor[16]
		EssentialCount = 0
	EndIf
EndFunction

Int Function FindEssentialSlot(Actor ak)
	If !ak
		Return -1
	EndIf
	EnsureEssentialList()
	Int i = 0
	While i < EssentialCount
		If EssentialActors[i] == ak
			Return i
		EndIf
		i += 1
	EndWhile
	Return -1
EndFunction

; Swap-with-last removal — order doesn't matter for this list.
Function RemoveEssentialAt(Int slot)
	EnsureEssentialList()
	If slot < 0 || slot >= EssentialCount
		Return
	EndIf
	Int last = EssentialCount - 1
	EssentialActors[slot] = EssentialActors[last]
	EssentialActors[last] = None
	EssentialCount = last
EndFunction

Bool Function IsTrackedEssential(Actor ak)
	Return FindEssentialSlot(ak) >= 0
EndFunction

; Debug/UX visibility for the AUTOMATIC (J2/J5) path ONLY — deliberately NOT called from
; the shared Add/RemoveEssentialTracked helpers, so J1's MCM manual toggle stays silent
; (it already has its own feedback: the MCM status row + sBeatEssential checkbox). Callers
; that want this dialog call it explicitly themselves: HandleBeatBeforeKill (apply) and
; ClearAllEssentialOnWeaponEquip (the only reversal left — see the top-of-file note).
Function ToastEssentialChange(Actor ak, Bool abNowEssential)
	If !ak
		Return
	EndIf
	PickmansWhisperMainQuestScript m = Main()
	String label = "her"
	If m && m.VoiceAlias
		String resolved = m.VoiceAlias.GetActorDisplayName(ak)
		If resolved
			label = resolved
		EndIf
	EndIf
	String stateWord = "ESSENTIAL (can't die)"
	If !abNowEssential
		stateWord = "NOT essential (can die again)"
	EndIf
	; Ground-truth check — confirms SetEssential actually took, not just that we asked.
	String verify = ""
	If ak.IsEssential() != abNowEssential
		verify = "\n\nWARNING: SetEssential did not take — IsEssential() reports " + ak.IsEssential()
	EndIf
	Debug.Trace("PickmansWhisper: beat-before-kill essential=" + abNowEssential + " id=0x" + GardenOfEden.GetHexFormID(ak) + " name=" + label)
	; Debug.MessageBox("Pickman's Whisper\n\n" + label + " is now " + stateWord + verify)
EndFunction

; Shared apply — caller must already have verified eligibility + list capacity. No UI
; feedback here on purpose (see ToastEssentialChange) — callers decide what to show.
Function AddEssentialTracked(Actor ak)
	EnsureEssentialList()
	EssentialActors[EssentialCount] = ak
	EssentialCount += 1
	ak.SetEssential(True)
EndFunction

; Shared clear — safe regardless of caller; only ever removes actors WE tracked. No UI
; feedback here on purpose (see ToastEssentialChange) — callers decide what to show.
Function RemoveEssentialTracked(Actor ak)
	Int slot = FindEssentialSlot(ak)
	If slot < 0
		Return
	EndIf
	RemoveEssentialAt(slot)
	ak.SetEssential(False)
EndFunction

; J1 — MCM Victims manual toggle for the aimed NPC. The eligibility gate (IsValidTarget,
; same as knife-kill crediting) only applies when turning essential ON. Turning it back
; OFF only requires that WE set it in the first place (tracked in EssentialActors).
Bool Function ToggleEssentialForAimed(Actor ak)
	PickmansWhisperMainQuestScript m = Main()
	If !m
		Debug.Trace("PickmansWhisper: ERROR ToggleEssentialForAimed — Main missing")
		Return False
	EndIf
	If !ak
		m.LastVictimStatus = "toggle essential failed — no aimed actor"
		Return False
	EndIf
	If FindEssentialSlot(ak) >= 0
		RemoveEssentialTracked(ak)
		m.LastVictimStatus = "essential OFF id=0x" + GardenOfEden.GetHexFormID(ak)
		Debug.Trace("PickmansWhisper: " + m.LastVictimStatus)
		Return True
	EndIf
	; Feature: living; hard gate (incl. living hostility) Traces its own rejects.
	If ak.IsDead() || !m.IsValidTarget(ak)
		m.LastVictimStatus = "toggle essential failed — not a valid target"
		Debug.Trace("PickmansWhisper: " + m.LastVictimStatus + " id=" + ak.GetFormID())
		Return False
	EndIf
	EnsureEssentialList()
	If EssentialCount >= ESSENTIAL_MAX
		m.LastVictimStatus = "toggle essential failed — tracking list full (" + ESSENTIAL_MAX + ")"
		Debug.Trace("PickmansWhisper: " + m.LastVictimStatus)
		Return False
	EndIf
	AddEssentialTracked(ak)
	m.LastVictimStatus = "essential ON id=0x" + GardenOfEden.GetHexFormID(ak)
	Debug.Trace("PickmansWhisper: " + m.LastVictimStatus)
	Return True
EndFunction

; Single gameplay entry — akTarget is the NPC. Uses wired PlayerAlias for blade/unarmed:
;   blade equipped → clear essential on her if WE tracked her
;   unarmed (IsReadyToGiveBeating) → apply temp essential (K2) when eligible
Function HandleBeatBeforeKill(Actor akTarget)
	If !akTarget
		Return
	EndIf
	If !PlayerAlias
		Debug.Trace("PickmansWhisper: ERROR HandleBeatBeforeKill — PlayerAlias unbound")
		Return
	EndIf
	PickmansWhisperMainQuestScript m = Main()
	If !m
		Debug.Trace("PickmansWhisper: ERROR HandleBeatBeforeKill — Main missing")
		Return
	EndIf

	If PlayerAlias.IsPickmansBladeEquipped
		If FindEssentialSlot(akTarget) >= 0
			RemoveEssentialTracked(akTarget)
			ToastEssentialChange(akTarget, False)
			Debug.Trace("PickmansWhisper: beat-before-kill essential OFF (blade equipped) id=0x" + GardenOfEden.GetHexFormID(akTarget))
		EndIf
		Return
	EndIf

	If !PlayerAlias.IsReadyToGiveBeating
		Return
	EndIf
	If FindEssentialSlot(akTarget) >= 0
		Return ; already tracked (e.g. via J1) — nothing to do
	EndIf
	If !m.PlayerHasBlade()
		Debug.Trace("PickmansWhisper: beat-before-kill skip | player does not own Pickman's Blade")
		Return
	EndIf
	If akTarget.IsDead() || !m.IsValidTarget(akTarget)
		Debug.Trace("PickmansWhisper: beat-before-kill skip | not a valid target id=" + akTarget.GetFormID())
		Return
	EndIf
	EnsureEssentialList()
	If EssentialCount >= ESSENTIAL_MAX
		Debug.Trace("PickmansWhisper: ERROR beat-before-kill — tracking list full (" + ESSENTIAL_MAX + ")")
		Return
	EndIf
	AddEssentialTracked(akTarget)
	Debug.Trace("PickmansWhisper: beat-before-kill essential ON (auto, unarmed) id=0x" + GardenOfEden.GetHexFormID(akTarget))
	ToastEssentialChange(akTarget, True)
EndFunction

; Compat wrapper — combat enter / older call sites.
Function OnPlayerEnterCombatWith(Actor target)
	HandleBeatBeforeKill(target)
EndFunction

; J5 reversal — player equipped ANY weapon. Called from PlayerAlias after blade/unarmed
; flags update. Clears every currently-tracked actor.
Function ClearAllEssentialOnWeaponEquip()
	EnsureEssentialList()
	Int i = EssentialCount - 1
	While i >= 0
		Actor ak = EssentialActors[i]
		If ak
			Debug.Trace("PickmansWhisper: beat-before-kill essential OFF (weapon equipped) id=0x" + GardenOfEden.GetHexFormID(ak))
			RemoveEssentialTracked(ak)
			ToastEssentialChange(ak, False)
		Else
			RemoveEssentialAt(i)
		EndIf
		i -= 1
	EndWhile
EndFunction

; Ambient safety net — KillerScan every tick. Cheap no-op unless list non-empty AND armed.
Function TickEssentialReconcile()
	If EssentialCount <= 0
		Return
	EndIf
	If PlayerAlias
		If PlayerAlias.IsReadyToGiveBeating
			Return
		EndIf
		Debug.Trace("PickmansWhisper: beat-before-kill reconcile — player armed (alias), clearing all")
		ClearAllEssentialOnWeaponEquip()
		Return
	EndIf
	Actor player = Game.GetPlayer()
	If !player
		Return
	EndIf
	If player.GetEquippedWeapon(0)
		Debug.Trace("PickmansWhisper: beat-before-kill reconcile — player armed, clearing all")
		ClearAllEssentialOnWeaponEquip()
	EndIf
EndFunction
