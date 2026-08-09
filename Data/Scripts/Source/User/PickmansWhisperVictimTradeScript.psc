Scriptname PickmansWhisperVictimTradeScript extends Quest
{Force-trade via Talk activate menu — calm hunger + ModConfig CHA gate + OpenInventory.
ShowBarterMenu is vendor-chest barter (empty on settlers); OpenInventory is companion-style transfer.
Strip once per NPC: empty Outfit + UnequipAll unlocks default gear; later Force Trades
skip strip so gear the player put on her stays equipped.}

; CK/VMAD: bound to PW_VictimTradeActivate PERK / PW_EmptyOutfit OTFT.
Perk Property TradeActivatePerk Auto Const
Outfit Property EmptyOutfit Auto Const

Float CALM_HUNGER_MAX = 25.0
Int FID_AV_CHA = 0x000002C5
Int FID_TRADE_PERK = 0x00000878
Int FID_EMPTY_OUTFIT = 0x00000879
Int STRIP_ONCE_MAX = 32

Actor PendingTradeStrip
Bool TradeMenuWatching = False
; FormIDs of actors we already cleared default outfit for (one-time strip).
Int[] TradeStripDoneIds
Int TradeStripDoneCount = 0

PickmansWhisperMainQuestScript Function Main()
	Return (Self as Quest) as PickmansWhisperMainQuestScript
EndFunction

Event OnInit()
	; Blade-drawn sync runs from Main.SyncBladeDrawnDebugLatch; grant if unarmed/other.
	EnsureTradePerk()
EndEvent

; Grant Force Trade activate choice only when Pickman's Blade is NOT drawn
; (extra activate choices open a multi-choice menu and block attack).
Function SyncTradeActivatePerk(Bool abAllowDialog)
	Actor player = Game.GetPlayer()
	If !player
		Debug.Trace("PickmansWhisper: ERROR SyncTradeActivatePerk — no player")
		Return
	EndIf
	Perk pk = TradeActivatePerk
	If !pk
		pk = Game.GetFormFromFile(FID_TRADE_PERK, "PickmansWhisper.esp") as Perk
	EndIf
	If !pk
		Debug.Trace("PickmansWhisper: ERROR SyncTradeActivatePerk — PERK local FormID " + FID_TRADE_PERK + " missing")
		Debug.Notification("PickmansWhisper: Trade perk missing — rebuild ESP")
		Return
	EndIf
	If abAllowDialog
		If player.HasPerk(pk)
			Return
		EndIf
		player.AddPerk(pk, False)
		Debug.Trace("PickmansWhisper: Trade activate perk granted")
	Else
		If !player.HasPerk(pk)
			Return
		EndIf
		player.RemovePerk(pk)
		Debug.Trace("PickmansWhisper: Trade activate perk removed | blade drawn")
	EndIf
EndFunction

Function EnsureTradePerk()
	PickmansWhisperMainQuestScript m = Main()
	Bool allow = True
	If m && m.IsBladeEquipped()
		allow = False
	EndIf
	SyncTradeActivatePerk(allow)
EndFunction

Outfit Function ResolveEmptyOutfit()
	If EmptyOutfit
		Return EmptyOutfit
	EndIf
	Return Game.GetFormFromFile(FID_EMPTY_OUTFIT, "PickmansWhisper.esp") as Outfit
EndFunction

Bool Function WasTradeStrippedOnce(Actor akTarget)
	If !akTarget || !TradeStripDoneIds || TradeStripDoneCount <= 0
		Return False
	EndIf
	Int id = akTarget.GetFormID()
	Int i = 0
	While i < TradeStripDoneCount
		If TradeStripDoneIds[i] == id
			Return True
		EndIf
		i += 1
	EndWhile
	Return False
EndFunction

Function MarkTradeStrippedOnce(Actor akTarget)
	If !akTarget
		Return
	EndIf
	If WasTradeStrippedOnce(akTarget)
		Return
	EndIf
	If !TradeStripDoneIds
		TradeStripDoneIds = new Int[STRIP_ONCE_MAX]
		TradeStripDoneCount = 0
	EndIf
	If TradeStripDoneCount >= STRIP_ONCE_MAX
		; Drop oldest so new victims can still unlock once.
		Int i = 0
		While i < STRIP_ONCE_MAX - 1
			TradeStripDoneIds[i] = TradeStripDoneIds[i + 1]
			i += 1
		EndWhile
		TradeStripDoneCount = STRIP_ONCE_MAX - 1
	EndIf
	TradeStripDoneIds[TradeStripDoneCount] = akTarget.GetFormID()
	TradeStripDoneCount += 1
EndFunction

; One-time: clear default outfit so worn gear is not locked, then unequip for lootable naked.
Function ForceStripForTrade(Actor akTarget)
	If !akTarget
		Return
	EndIf
	Outfit empty = ResolveEmptyOutfit()
	If empty
		akTarget.SetOutfit(empty)
	Else
		Debug.Trace("PickmansWhisper: ERROR trade strip — EmptyOutfit missing")
		Debug.Notification("PickmansWhisper: Trade strip outfit missing — rebuild ESP")
	EndIf
	akTarget.UnequipAll()
	MarkTradeStrippedOnce(akTarget)
	Debug.Trace("PickmansWhisper: trade one-time strip id=" + akTarget.GetFormID())
EndFunction

; Strip only the first Force Trade on this NPC; later opens keep player-equipped gear.
Function MaybeForceStripForTrade(Actor akTarget)
	If !akTarget
		Return
	EndIf
	If WasTradeStrippedOnce(akTarget)
		Debug.Trace("PickmansWhisper: trade skip strip | already cleared once id=" + akTarget.GetFormID())
		Return
	EndIf
	ForceStripForTrade(akTarget)
EndFunction

; Forward to Slavery SSOT (inventory name contains "slave").
Bool Function InventoryHasSlaveItem(Actor akTarget)
	PickmansWhisperSlaveryScript slavery = (Self as Quest) as PickmansWhisperSlaveryScript
	If !slavery
		Debug.Trace("PickmansWhisper: ERROR trade slave scan — SlaveryScript missing")
		Return False
	EndIf
	Return slavery.InventoryHasSlaveItem(akTarget)
EndFunction

; Best-effort pacify after Force Trade leaves a "slave" item on her.
Function MaybePacifyIfSlaveGear(Actor akTarget)
	If !akTarget || akTarget.IsDead()
		Return
	EndIf
	If !InventoryHasSlaveItem(akTarget)
		Return
	EndIf
	Actor player = Game.GetPlayer()
	If !player
		Return
	EndIf
	akTarget.StopCombat()
	akTarget.StopCombatAlarm()
	akTarget.SetAttackActorOnSight(False)
	akTarget.SetRelationshipRank(player, 1)
	akTarget.EvaluatePackage()
	Debug.Trace("PickmansWhisper: trade pacify | slave gear on id=" + akTarget.GetFormID())
	Debug.Notification("PickmansWhisper: She yields — slave gear")
EndFunction

; Best-effort — auto-enslave / free via Slavery after Trade close; must not skip pacify.
Function MaybeSyncSlaveryAfterTrade(Actor akTarget)
	PickmansWhisperSlaveryScript slavery = (Self as Quest) as PickmansWhisperSlaveryScript
	If !slavery
		Debug.Trace("PickmansWhisper: ERROR trade slavery sync — SlaveryScript missing")
		Debug.Notification("PickmansWhisper: Slavery script missing — rebuild ESP")
		Return
	EndIf
	slavery.SyncSlaveryFromSlaveGear(akTarget)
EndFunction

; Called from perk OnEntryRun via Main façade. akTarget is the activate subject.
Function TryForceVictimTradeFromActivate(Actor akTarget)
	EnsureTradePerk()
	If !akTarget
		Debug.Trace("PickmansWhisper: trade skip | no activate target")
		Debug.Notification("PickmansWhisper: Trade — no target")
		Return
	EndIf
	If akTarget.IsDead()
		Debug.Trace("PickmansWhisper: trade skip | target dead id=" + akTarget.GetFormID())
		Debug.Notification("PickmansWhisper: Trade — target is dead")
		Return
	EndIf
	PickmansWhisperMainQuestScript m = Main()
	If !m
		Debug.Trace("PickmansWhisper: ERROR trade — Main missing")
		Debug.Notification("PickmansWhisper: Trade — Main missing")
		Return
	EndIf
	If m.IsBladeEquipped()
		Debug.Trace("PickmansWhisper: trade skip | blade drawn")
		Debug.Notification("PickmansWhisper: Trade — sheath the blade first")
		Return
	EndIf
	; Force Trade may open on hostiles (e.g. after aggro); whisper/scan keep default reject.
	If !m.IsValidTarget(akTarget, True)
		Debug.Trace("PickmansWhisper: trade skip | not valid target id=" + akTarget.GetFormID())
		Debug.Notification("PickmansWhisper: Trade — not an eligible target")
		Return
	EndIf
	If m.HungerLevel >= CALM_HUNGER_MAX
		Debug.Trace("PickmansWhisper: trade skip | hunger not calm level=" + m.HungerLevel)
		Debug.Notification("PickmansWhisper: Trade — knife is not calm")
		Return
	EndIf
	Int minCha = 0
	If m.ModConfigAlias
		minCha = m.ModConfigAlias.GetVictimTradeMinCha()
	EndIf
	If minCha <= 0
		Debug.Trace("PickmansWhisper: ERROR trade — victimTradeMinCha missing/invalid")
		Debug.Notification("PickmansWhisper: Trade — ModConfig victimTradeMinCha missing")
		Return
	EndIf
	Actor player = Game.GetPlayer()
	If !player
		Debug.Trace("PickmansWhisper: ERROR trade — no player")
		Return
	EndIf
	ActorValue avCha = Game.GetForm(FID_AV_CHA) as ActorValue
	If !avCha
		avCha = Game.GetFormFromFile(FID_AV_CHA, "Fallout4.esm") as ActorValue
	EndIf
	If !avCha
		Debug.Trace("PickmansWhisper: ERROR trade — Charisma AV 0x2C5 missing")
		Debug.Notification("PickmansWhisper: Trade — Charisma AV missing")
		Return
	EndIf
	Float cha = player.GetValue(avCha)
	If cha < (minCha as Float)
		Debug.Trace("PickmansWhisper: trade skip | CHA " + cha + " < min " + minCha)
		Debug.Notification("PickmansWhisper: Trade — Charisma too low (" + (cha as Int) + " < " + minCha + ")")
		Return
	EndIf

	PendingTradeStrip = akTarget
	MaybeForceStripForTrade(akTarget)
	If !TradeMenuWatching
		RegisterForMenuOpenCloseEvent("ContainerMenu")
		TradeMenuWatching = True
	EndIf
	; Force-open actor container (same idea as console openactorcontainer 1).
	akTarget.OpenInventory(True)
	Debug.Trace("PickmansWhisper: trade opened inventory id=" + akTarget.GetFormID() + " cha=" + cha)
EndFunction

Event OnMenuOpenCloseEvent(String asMenuName, Bool abOpening)
	If asMenuName != "ContainerMenu"
		Return
	EndIf
	If abOpening
		Return
	EndIf
	If TradeMenuWatching
		UnRegisterForMenuOpenCloseEvent("ContainerMenu")
		TradeMenuWatching = False
	EndIf
	Actor ak = PendingTradeStrip
	PendingTradeStrip = None
	If !ak
		Return
	EndIf
	; Do NOT strip on close — keeps gear the player put on her.
	Debug.Trace("PickmansWhisper: trade ContainerMenu closed id=" + ak.GetFormID())
	; Inventory indexes can lag a beat after ContainerMenu equip — settle, then pacify/sync.
	Utility.Wait(0.2)
	MaybePacifyIfSlaveGear(ak)
	MaybeSyncSlaveryAfterTrade(ak)
EndEvent
