Scriptname PickmansWhisperBuffTrackerScript extends Quest
{Dedicated home for player buffs granted by Pickman's Whisper. First buff: Slice H P5's
END bonus for eating a ripe (max decay stage) corpse. Add future timed buffs here as
their own Apply/Tick function pairs, each with its own applied-delta + expiry fields —
kept scalar per-buff (not a generic array) since there is exactly one buff today.}

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

Function EnsureEnduranceAV()
	If !EnduranceAV
		EnduranceAV = Game.GetFormFromFile(FID_AV_ENDURANCE, "Fallout4.esm") as ActorValue
	EndIf
EndFunction

; Slice H P5 bonus — called from MainQuestScript.ApplyEatRipeCorpseBonus. Amount/cap/
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
	Debug.Trace("PickmansWhisper: eat-ripe-corpse END buff +" + addAmount + " (total " + EndBuffAppliedDelta + "/" + maxDelta + ") expires in " + hours + "h")
EndFunction

; Dispatched every KillerScan tick (CallFunctionNoWait) — cheap no-op unless a buff is
; both active and past its expiry. No StartTimer of its own (Killer Orchestrator).
Function TickEndBuffExpiry()
	If EndBuffAppliedDelta <= 0.0
		Return
	EndIf
	Float now = Utility.GetCurrentGameTime()
	If EndBuffExpiryGameTime > now
		Return
	EndIf
	Actor player = Game.GetPlayer()
	EnsureEnduranceAV()
	If player && EnduranceAV
		player.ModValue(EnduranceAV, -EndBuffAppliedDelta)
		Debug.Trace("PickmansWhisper: eat-ripe-corpse END buff expired — removed " + EndBuffAppliedDelta)
	Else
		Debug.Trace("PickmansWhisper: ERROR TickEndBuffExpiry — player/EnduranceAV missing, buff bookkeeping cleared without ModValue revert")
	EndIf
	EndBuffAppliedDelta = 0.0
	EndBuffExpiryGameTime = 0.0
EndFunction
