Scriptname PickmansWhisperBeatBeforeKillScript extends Quest
{Slice J — victim beat-before-kill (temp essential).
J1: manual MCM Victims toggle (dialog-free — MCM's own status row is its feedback).
J2-J5: automatic trigger when the player enters combat unarmed against an eligible NPC;
cleared ONLY on weapon-equip (see the removed "out of combat" reversal note below).
Dispatched from KillerScanScript as an ambient reconciliation safety net (weapon-state
only) alongside the direct native-event triggers (OnCombatStateChanged / OnItemEquipped
on MainQuestScript).

REMOVED — "out of combat -> clear essential" (both the direct OnCombatStateChanged(0)
handler and the reconcile poll's !IsInCombat() check): confirmed via live log evidence
this actively broke the feature. The reconcile poll fired within ~3 seconds of an MCM
J1 toggle and stripped essential from an NPC who was never even in combat yet, because
"not currently fighting" was treated as "safe to clear" — which is also true the instant
an essential actor "survives" lethal damage and collapses into the protected knockdown
state, since combat state can flip to not-in-combat AS PART of that same moment. That
race meant our own cleanup code could undo the protection at exactly the moment it was
supposed to matter. Weapon-equip is the only reversal now: a deliberate, player-initiated
action that can't fire mid-combat-resolution the way a combat-state transition can.}

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
; that want this dialog call it explicitly themselves: OnPlayerEnterCombatWith (apply) and
; ClearAllEssentialOnWeaponEquip (the only reversal left — see the top-of-file note).
; Debug.MessageBox (pauses, requires an OK click) rather than a toast: a Debug.Notification
; here was confirmed firing correctly in the log but easy to lose amid everything else
; toasting during combat. NOTE: MessageBox pauses like any menu, so this WILL freeze the
; fight the instant the auto trigger flips her essential mid-combat — a deliberate
; tradeoff for debugging visibility right now, not the long-term answer (this codebase
; otherwise reserves MessageBox for MCM Debug buttons only, never ambient gameplay
; events, for exactly this reason).
Function ToastEssentialChange(Actor ak, Bool abNowEssential)
	If !ak
		Return
	EndIf
	PickmansWhisperMainQuestScript m = Main()
	String label = "her"
	If m
		String resolved = m.GetActorDisplayName(ak)
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
	Debug.MessageBox("Pickman's Whisper\n\n" + label + " is now " + stateWord + verify)
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
	If !m.IsValidTarget(ak, True)
		m.LastVictimStatus = "toggle essential failed — not a valid target (" + m.LastKillIgnoreReason + ")"
		Debug.Trace("PickmansWhisper: " + m.LastVictimStatus)
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

; J2 — auto trigger. Called from MainQuestScript's Actor.OnCombatStateChanged handler
; when the PLAYER enters combat (aeCombatState==1) with `target`. Fists only (no weapon
; equipped — that IS the beat-before-kill fantasy), blade owned (hard requirement — no
; point starting this if there's no knife to finish her with later), same eligibility as
; a valid knife-kill target (human, adult female, not essential/child/teammate, seen
; non-hostile, alive).
Function OnPlayerEnterCombatWith(Actor target)
	PickmansWhisperMainQuestScript m = Main()
	If !m || !target
		Return
	EndIf
	If FindEssentialSlot(target) >= 0
		Return ; already tracked (e.g. via J1) — nothing to do
	EndIf
	Actor player = Game.GetPlayer()
	If !player
		Return
	EndIf
	If player.GetEquippedWeapon(0)
		Debug.Trace("PickmansWhisper: beat-before-kill skip | player has a weapon equipped")
		Return
	EndIf
	If !m.PlayerHasBlade()
		Debug.Trace("PickmansWhisper: beat-before-kill skip | player does not own Pickman's Blade")
		Return
	EndIf
	If !m.IsValidTarget(target, True)
		Debug.Trace("PickmansWhisper: beat-before-kill skip | not a valid target (" + m.LastKillIgnoreReason + ") id=" + target.GetFormID())
		Return
	EndIf
	EnsureEssentialList()
	If EssentialCount >= ESSENTIAL_MAX
		Debug.Trace("PickmansWhisper: ERROR beat-before-kill — tracking list full (" + ESSENTIAL_MAX + ")")
		Return
	EndIf
	AddEssentialTracked(target)
	Debug.Trace("PickmansWhisper: beat-before-kill essential ON (auto, unarmed combat) id=0x" + GardenOfEden.GetHexFormID(target))
	ToastEssentialChange(target, True)
EndFunction

; J5 reversal — player equipped ANY weapon. Called from MainQuestScript's
; Actor.OnItemEquipped handler. Clears every currently-tracked actor (not scoped to one
; scuffle partner) — matches "if the player arms a weapon" without qualification. This is
; now the ONLY reversal trigger — see the top-of-file note on why "out of combat" was
; removed.
Function ClearAllEssentialOnWeaponEquip()
	EnsureEssentialList()
	; Iterate from the end and remove via the shared helper — safe because RemoveEssentialAt
	; always swaps the current LAST element into the removed slot, which never disturbs any
	; index at or before the one we're currently on.
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

; Ambient safety net — dispatched from KillerScanScript every tick (Killer Orchestrator;
; no StartTimer here). Cheap no-op unless the list is non-empty AND the player is armed.
; Catches only "player re-armed but OnItemEquipped somehow didn't fire cleanly" — does
; NOT re-check combat state (see the top-of-file note on why that was actively dangerous).
Function TickEssentialReconcile()
	If EssentialCount <= 0
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
