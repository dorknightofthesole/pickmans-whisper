Scriptname PickmansWhisperBuffTrackerScript extends Quest
{Dedicated home for player buffs granted by Pickman's Whisper. First buff: Slice H P5's
END bonus for eating a ripe (max decay stage) corpse. Expiry is a self-contained
StartTimerGameTime on this script (not KillerScan-polled). InitBuffTracker from Main
on quest init / load re-arms or clears a save-persisted buff.}

PickmansWhisperMainQuestScript Function Main()
	Return (Self as Quest) as PickmansWhisperMainQuestScript
EndFunction

Int FID_AV_ENDURANCE = 0x000002C4 ; Fallout4.esm Endurance (verified; matches AGI 0x2C7 / CHA 0x2C5 pattern already used for Knife Hunger)
ActorValue EnduranceAV

; Net delta this buff currently has applied (0 = not active) and the game-time it expires.
; Single whole-buff timer, not per-application — eating again while the buff is still
; live refreshes the expiry to "now + hours" rather than stacking independent timers.
Float EndBuffAppliedDelta = 0.0
Float EndBuffExpiryGameTime = 0.0

; Game-time timer id (unique per-script; does not collide with real-time StartTimer ids).
Int TIMER_END_BUFF = 1 Const

Function EnsureEnduranceAV()
	If !EnduranceAV
		EnduranceAV = Game.GetFormFromFile(FID_AV_ENDURANCE, "Fallout4.esm") as ActorValue
	EndIf
EndFunction

; Called from Main RegisterBuffTracker on quest init / load (same pattern as
; RegisterBuffTracker). Re-arms StartTimerGameTime if a buff survived the save,
; or expires immediately if the deadline already passed while unloaded.
Function InitBuffTracker()
	EnsureEnduranceAV()
	ReconcileEndBuffTimer()
	Debug.Trace("PickmansWhisper: BuffTracker init | delta=" + EndBuffAppliedDelta + " expiryGT=" + EndBuffExpiryGameTime)
EndFunction

Function ReconcileEndBuffTimer()
	If EndBuffAppliedDelta <= 0.0
		CancelTimerGameTime(TIMER_END_BUFF)
		EndBuffExpiryGameTime = 0.0
		Return
	EndIf
	Float now = Utility.GetCurrentGameTime()
	If EndBuffExpiryGameTime <= now
		ExpireEndBuff("load-expired")
		Return
	EndIf
	Float remainingHours = (EndBuffExpiryGameTime - now) * 24.0
	; Engine rounds intervals below ~2 game-minutes up to 0.033h.
	If remainingHours < 0.033
		remainingHours = 0.033
	EndIf
	ArmEndBuffExpiryTimer(remainingHours)
EndFunction

; Slice H P5 bonus — called from CorpseDecay ApplyEatRipeCorpseBonus. Amount/cap/
; duration come from ModConfig (ateRipeCorpseEndBuffAmount/MaxDelta/Hours); missing or
; invalid config fails loud (no baked fallback), matching this project's ModConfig
; convention elsewhere (decay stages, bed gift cooldown).
Function ApplyEatRipeCorpseEndBuff()
	Actor player = Game.GetPlayer()
	If !player
		Debug.Trace("PickmansWhisper: ERROR ApplyEatRipeCorpseEndBuff — no player")
		Return
	EndIf
	PickmansWhisperMainQuestScript m = Main()
	If !m
		Debug.Trace("PickmansWhisper: ERROR ApplyEatRipeCorpseEndBuff — Main missing")
		Return
	EndIf
	If !m.ModConfigAlias
		Debug.Trace("PickmansWhisper: ERROR ApplyEatRipeCorpseEndBuff — ModConfigAlias unbound")
		Return
	EndIf
	Float amount = m.ModConfigAlias.GetEatRipeCorpseEndBuffAmount()
	Float maxDelta = m.ModConfigAlias.GetEatRipeCorpseEndBuffMaxDelta()
	Float hours = m.ModConfigAlias.GetEatRipeCorpseEndBuffHours()
	If amount <= 0.0 || maxDelta <= 0.0 || hours <= 0.0
		Debug.Trace("PickmansWhisper: ERROR ApplyEatRipeCorpseEndBuff — ModConfig ateRipeCorpseEndBuff Amount/MaxDelta/Hours missing or invalid (amount=" + amount + " max=" + maxDelta + " hours=" + hours + ")")
		Return
	EndIf
	EnsureEnduranceAV()
	If !EnduranceAV
		Debug.Trace("PickmansWhisper: ERROR ApplyEatRipeCorpseEndBuff — Endurance AV missing")
		Return
	EndIf
	Float now = Utility.GetCurrentGameTime()
	Float headroom = maxDelta - EndBuffAppliedDelta
	If headroom <= 0.0
		; Already at cap — no further ModValue, but eating again still refreshes the clock.
		EndBuffExpiryGameTime = now + (hours / 24.0)
		ArmEndBuffExpiryTimer(hours)
		Debug.Trace("PickmansWhisper: eat-ripe-corpse END buff at cap (" + EndBuffAppliedDelta + "/" + maxDelta + ") — refreshed expiry only")
		Return
	EndIf
	Float addAmount = amount
	If addAmount > headroom
		addAmount = headroom
	EndIf
	player.ModValue(EnduranceAV, addAmount)
	EndBuffAppliedDelta += addAmount
	EndBuffExpiryGameTime = now + (hours / 24.0)
	ArmEndBuffExpiryTimer(hours)
	Debug.Trace("PickmansWhisper: eat-ripe-corpse END buff +" + addAmount + " (total " + EndBuffAppliedDelta + "/" + maxDelta + ") expires in " + hours + "h")
EndFunction

; StartTimerGameTime afInterval is game-time hours (CK wiki). Restarting same id resets.
Function ArmEndBuffExpiryTimer(Float hours)
	If hours <= 0.0
		Debug.Trace("PickmansWhisper: ERROR ArmEndBuffExpiryTimer — hours <= 0")
		Return
	EndIf
	CancelTimerGameTime(TIMER_END_BUFF)
	StartTimerGameTime(hours, TIMER_END_BUFF)
	Debug.Trace("PickmansWhisper: END buff timer armed for " + hours + "h game-time")
EndFunction

Event OnTimerGameTime(Int aiTimerID)
	If aiTimerID != TIMER_END_BUFF
		Debug.Trace("PickmansWhisper: BuffTracker OnTimerGameTime ignore id=" + aiTimerID)
		Return
	EndIf
	ExpireEndBuff("timer")
EndEvent

Function ExpireEndBuff(String reason)
	If EndBuffAppliedDelta <= 0.0
		EndBuffExpiryGameTime = 0.0
		CancelTimerGameTime(TIMER_END_BUFF)
		Return
	EndIf
	Actor player = Game.GetPlayer()
	EnsureEnduranceAV()
	If player && EnduranceAV
		player.ModValue(EnduranceAV, -EndBuffAppliedDelta)
		Debug.Trace("PickmansWhisper: eat-ripe-corpse END buff expired (" + reason + ") — removed " + EndBuffAppliedDelta)
	Else
		Debug.Trace("PickmansWhisper: ERROR ExpireEndBuff — player/EnduranceAV missing, buff bookkeeping cleared without ModValue revert (" + reason + ")")
	EndIf
	EndBuffAppliedDelta = 0.0
	EndBuffExpiryGameTime = 0.0
	CancelTimerGameTime(TIMER_END_BUFF)
EndFunction
