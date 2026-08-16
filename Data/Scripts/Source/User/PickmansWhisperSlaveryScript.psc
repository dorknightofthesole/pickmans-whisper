Scriptname PickmansWhisperSlaveryScript extends Quest
{Slavery — enslave a slave-gear NPC to follow/teleport with the player.
Not a vanilla companion (no CurrentCompanionFaction). Remains a killable Whisper victim.
SSOT for inventory "slave" name scan; Trade pacify + auto-enslave call into here.}

; CK/VMAD: bound to PW_SlaveryActivate PERK.
Perk Property SlaveryActivatePerk Auto Const

Int FID_AV_CHA = 0x000002C5
Int FID_SLAVERY_PERK = 0x0000087A
; Fallout4.esm CurrentCompanionFaction — never treat vanilla companions as ours.
Int FID_CURRENT_COMPANION_FACTION = 0x00023C01
; Cross-cell safety: MoveTo if farther than this (game units).
Float WARP_DISTANCE = 2048.0
; SetPlayerTeammate alone does NOT path-follow — poll + PathToReference / MoveTo.
Int TIMER_SLAVE_FOLLOW = 91
Float FOLLOW_POLL_SECONDS = 2.0
; Start walking/running toward player past this distance.
Float FOLLOW_PATH_DISTANCE = 256.0
; PathToReference walk/run blend (1.0 = full run).
Float FOLLOW_PATH_SPEED = 1.0

Actor Slave
Int SlaveFormID = 0
Bool SlaveDeathWatching = False
Bool SlaveFollowLoopArmed = False

PickmansWhisperMainQuestScript Function Main()
	Return (Self as Quest) as PickmansWhisperMainQuestScript
EndFunction

Event OnInit()
	; Blade-drawn sync runs from Main.SyncBladeDrawnDebugLatch; grant if unarmed/other.
	EnsureSlaveryPerk()
EndEvent

; Grant Enslave/Free activate choices only when Pickman's Blade is NOT drawn
; (extra activate choices open a multi-choice menu and block attack).
Function SyncSlaveryActivatePerk(Bool abAllowDialog)
	Actor player = Game.GetPlayer()
	If !player
		Debug.Trace("PickmansWhisper: ERROR SyncSlaveryActivatePerk — no player")
		Return
	EndIf
	Perk pk = SlaveryActivatePerk
	If !pk
		pk = Game.GetFormFromFile(FID_SLAVERY_PERK, "PickmansWhisper.esp") as Perk
	EndIf
	If !pk
		Debug.Trace("PickmansWhisper: ERROR SyncSlaveryActivatePerk — PERK local FormID " + FID_SLAVERY_PERK + " missing")
		Debug.Notification("PickmansWhisper: Slavery perk missing — rebuild ESP")
		Return
	EndIf
	If abAllowDialog
		If player.HasPerk(pk)
			Return
		EndIf
		player.AddPerk(pk, False)
		Debug.Trace("PickmansWhisper: slavery activate perk granted")
	Else
		If !player.HasPerk(pk)
			Return
		EndIf
		player.RemovePerk(pk)
		Debug.Trace("PickmansWhisper: slavery activate perk removed | blade drawn")
	EndIf
EndFunction

Function EnsureSlaveryPerk()
	; Honor Main toggle + blade gate (default OFF so beat/attack keep a clean activate).
	PickmansWhisperMainQuestScript m = Main()
	If m
		m.SyncDialogActivatePerks()
	Else
		SyncSlaveryActivatePerk(False)
	EndIf
EndFunction

; True if any inventory/worn item display name contains "slave" (case-insensitive). SSOT.
; Prefer GoE GetItemIndexesByName(partial) — worn collars often miss a raw GetNthItem
; walk after ContainerMenu equip (saw clear "no slave gear" while collar still worn).
Bool Function InventoryHasSlaveItem(Actor akTarget)
	If !akTarget
		Return False
	EndIf
	; Same partial-name pattern as blade detect (abExactMatch=False).
	Int[] byName = GardenOfEden.GetItemIndexesByName(akTarget, "slave", False, False)
	If byName && byName.Length > 0
		Int idx0 = byName[0]
		String found = GardenOfEden.GetNthItemName(akTarget, idx0)
		Debug.Trace("PickmansWhisper: slavery slave item | " + found + " idx=" + idx0 + " (byName)")
		Return True
	EndIf
	; Fallback: equipped slots only (worn collar after trade equip).
	Int[] eq = GardenOfEden.GetEquippedItemIndexes(akTarget)
	If eq && eq.Length > 0
		Int ei = 0
		While ei < eq.Length
			Int eidx = eq[ei]
			String eqName = GardenOfEden.GetNthItemName(akTarget, eidx)
			If eqName && GardenOfEden.StrFind(eqName, "slave", 0, False) > 0
				Debug.Trace("PickmansWhisper: slavery slave item | " + eqName + " idx=" + eidx + " (equipped)")
				Return True
			EndIf
			ei += 1
		EndWhile
	EndIf
	; Last resort: full inventory index walk.
	Int n = GardenOfEden.GetInventoryItemCount(akTarget)
	Int i = 0
	While i < n
		String itemName = GardenOfEden.GetNthItemName(akTarget, i)
		If itemName && GardenOfEden.StrFind(itemName, "slave", 0, False) > 0
			Debug.Trace("PickmansWhisper: slavery slave item | " + itemName + " idx=" + i + " (scan)")
			Return True
		EndIf
		i += 1
	EndWhile
	Debug.Trace("PickmansWhisper: slavery no slave gear | invCount=" + n + " id=" + akTarget.GetFormID())
	Return False
EndFunction

Actor Function GetSlave()
	Return Slave
EndFunction

Bool Function IsOurSlave(Actor ak)
	If !ak || !Slave
		Return False
	EndIf
	If ak == Slave
		Return True
	EndIf
	If SlaveFormID != 0 && ak.GetFormID() == SlaveFormID
		Return True
	EndIf
	Return False
EndFunction

Bool Function IsVanillaCompanion(Actor ak)
	If !ak
		Return False
	EndIf
	Faction fac = Game.GetFormFromFile(FID_CURRENT_COMPANION_FACTION, "Fallout4.esm") as Faction
	If !fac
		fac = Game.GetForm(FID_CURRENT_COMPANION_FACTION) as Faction
	EndIf
	If !fac
		Debug.Trace("PickmansWhisper: ERROR slavery — CurrentCompanionFaction 0x23C01 missing")
		Return False
	EndIf
	Return ak.IsInFaction(fac)
EndFunction

Function StopSlaveFollowLoop()
	If SlaveFollowLoopArmed
		CancelTimer(TIMER_SLAVE_FOLLOW)
		SlaveFollowLoopArmed = False
	EndIf
EndFunction

Function StartSlaveFollowLoop()
	If !Slave || Slave.IsDead()
		Return
	EndIf
	If SlaveFollowLoopArmed
		CancelTimer(TIMER_SLAVE_FOLLOW)
	EndIf
	SlaveFollowLoopArmed = True
	StartTimer(FOLLOW_POLL_SECONDS, TIMER_SLAVE_FOLLOW)
	Debug.Trace("PickmansWhisper: slavery follow loop armed id=" + SlaveFormID)
EndFunction

; Walk/run toward player; MoveTo when unloaded or too far. Teammate flag alone never paths.
Function TickSlaveFollow()
	If !Slave
		Return
	EndIf
	If Slave.IsDead()
		ClearSlave("dead follow")
		Return
	EndIf
	Actor player = Game.GetPlayer()
	If !player
		Debug.Trace("PickmansWhisper: ERROR slavery follow — no player latch=" + SlaveFormID)
		Return
	EndIf
	; Keep teammate + calm each tick (AI packages can drop the flag).
	If !Slave.IsPlayerTeammate()
		Slave.SetPlayerTeammate(True, False, False)
	EndIf
	If !Slave.Is3DLoaded()
		Slave.MoveTo(player)
		Debug.Trace("PickmansWhisper: slavery follow MoveTo (unloaded) id=" + SlaveFormID)
		Return
	EndIf
	Float dist = player.GetDistance(Slave)
	If dist > WARP_DISTANCE
		Slave.MoveTo(player)
		Debug.Trace("PickmansWhisper: slavery follow MoveTo (far) dist=" + dist + " id=" + SlaveFormID)
		Return
	EndIf
	If dist <= FOLLOW_PATH_DISTANCE
		Return
	EndIf
	; Latent — OnTimer re-arms after path completes or fails.
	Bool ok = Slave.PathToReference(player, FOLLOW_PATH_SPEED)
	Debug.Trace("PickmansWhisper: slavery PathToReference ok=" + ok + " dist=" + dist + " id=" + SlaveFormID)
EndFunction

Event OnTimer(Int aiTimerID)
	If aiTimerID != TIMER_SLAVE_FOLLOW
		Return
	EndIf
	If !SlaveFollowLoopArmed
		Return
	EndIf
	TickSlaveFollow()
	If Slave && !Slave.IsDead() && SlaveFollowLoopArmed
		StartTimer(FOLLOW_POLL_SECONDS, TIMER_SLAVE_FOLLOW)
	EndIf
EndEvent

Function ClearSlave(String asReason)
	StopSlaveFollowLoop()
	Actor prev = Slave
	If SlaveDeathWatching && prev
		UnregisterForRemoteEvent(prev, "OnDeath")
		SlaveDeathWatching = False
	EndIf
	If prev
		prev.SetPlayerTeammate(False, False, False)
		prev.EvaluatePackage()
		Debug.Trace("PickmansWhisper: slavery cleared id=" + prev.GetFormID() + " reason=" + asReason)
	EndIf
	Slave = None
	SlaveFormID = 0
EndFunction

Function PacifyForSlavery(Actor akTarget)
	If !akTarget
		Return
	EndIf
	Actor player = Game.GetPlayer()
	If !player
		Return
	EndIf
	akTarget.StopCombat()
	akTarget.StopCombatAlarm()
	akTarget.SetAttackActorOnSight(False)
	; Ally so sandbox AI is less likely to ignore the player.
	akTarget.SetRelationshipRank(player, 2)
	akTarget.EvaluatePackage()
EndFunction

; Latch + teammate + follow loop. Does not SetEssential — beat-before-kill owns that.
Function StartSlavery(Actor akTarget)
	If !akTarget || akTarget.IsDead()
		Return
	EndIf
	If IsVanillaCompanion(akTarget)
		Debug.Trace("PickmansWhisper: slavery skip start | vanilla companion id=" + akTarget.GetFormID())
		; Debug.Notification("PickmansWhisper: Slavery — that is a real companion")
		Return
	EndIf
	If Slave && Slave != akTarget
		ClearSlave("replaced")
	EndIf
	If IsOurSlave(akTarget)
		; Refresh pacify/follow; always toast so activate/"Enslave" never looks dead.
		PacifyForSlavery(akTarget)
		If !akTarget.IsPlayerTeammate()
			akTarget.SetPlayerTeammate(True, False, False)
		EndIf
		StartSlaveFollowLoop()
		Debug.Trace("PickmansWhisper: slavery already active id=" + akTarget.GetFormID())
		Debug.Notification("PickmansWhisper: Already enslaved — she follows")
		Return
	EndIf
	Slave = akTarget
	SlaveFormID = akTarget.GetFormID()
	PacifyForSlavery(akTarget)
	; No favor menu, no teammate XP — not a Followers companion.
	akTarget.SetPlayerTeammate(True, False, False)
	akTarget.EvaluatePackage(True)
	If !SlaveDeathWatching
		RegisterForRemoteEvent(akTarget, "OnDeath")
		SlaveDeathWatching = True
	EndIf
	StartSlaveFollowLoop()
	Debug.Trace("PickmansWhisper: slavery started id=" + SlaveFormID)
	Debug.Notification("PickmansWhisper: She follows — enslaved")
EndFunction

; Trade close / gear sync — enslave if slave gear present; free if ours and gear gone.
Function SyncSlaveryFromSlaveGear(Actor akTarget)
	If !akTarget || akTarget.IsDead()
		If IsOurSlave(akTarget)
			ClearSlave("dead")
		EndIf
		Return
	EndIf
	If InventoryHasSlaveItem(akTarget)
		StartSlavery(akTarget)
		Return
	EndIf
	; invCount==0 after ContainerMenu/equip is often a GoE lag — do NOT free on that.
	Int n = GardenOfEden.GetInventoryItemCount(akTarget)
	If n <= 0
		Debug.Trace("PickmansWhisper: slavery sync skip free | invCount=0 (unreliable) id=" + akTarget.GetFormID())
		Return
	EndIf
	If IsOurSlave(akTarget)
		ClearSlave("no slave gear")
		Debug.Notification("PickmansWhisper: Slavery — collar gone; freed")
	EndIf
EndFunction

Function TryEnslaveFromActivate(Actor akTarget)
	EnsureSlaveryPerk()
	If !akTarget
		Debug.Trace("PickmansWhisper: slavery skip | no activate target")
		Debug.Notification("PickmansWhisper: Slavery — no target")
		Return
	EndIf
	If akTarget.IsDead()
		Debug.Trace("PickmansWhisper: slavery skip | target dead id=" + akTarget.GetFormID())
		Debug.Notification("PickmansWhisper: Slavery — target is dead")
		Return
	EndIf
	If IsVanillaCompanion(akTarget)
		Debug.Trace("PickmansWhisper: slavery skip | vanilla companion id=" + akTarget.GetFormID())
		Debug.Notification("PickmansWhisper: Slavery — that is a real companion")
		Return
	EndIf
	PickmansWhisperMainQuestScript m = Main()
	If !m
		Debug.Trace("PickmansWhisper: ERROR slavery — Main missing")
		Debug.Notification("PickmansWhisper: Slavery — Main missing")
		Return
	EndIf
	If m.IsBladeEquipped()
		Debug.Trace("PickmansWhisper: slavery skip | blade drawn")
		Debug.Notification("PickmansWhisper: Slavery — sheath the blade first")
		Return
	EndIf
	If !m.IsValidTarget(akTarget, True)
		Debug.Trace("PickmansWhisper: slavery skip | not valid target id=" + akTarget.GetFormID())
		Debug.Notification("PickmansWhisper: Slavery — not an eligible target")
		Return
	EndIf
	Int minCha = 0
	If m.ModConfigAlias
		minCha = m.ModConfigAlias.GetSlaveryMinCha()
	EndIf
	If minCha <= 0
		Debug.Trace("PickmansWhisper: ERROR slavery — slaveryMinCha missing/invalid")
		Debug.Notification("PickmansWhisper: Slavery — ModConfig slaveryMinCha missing")
		Return
	EndIf
	Actor player = Game.GetPlayer()
	If !player
		Debug.Trace("PickmansWhisper: ERROR slavery — no player")
		Return
	EndIf
	ActorValue avCha = Game.GetForm(FID_AV_CHA) as ActorValue
	If !avCha
		avCha = Game.GetFormFromFile(FID_AV_CHA, "Fallout4.esm") as ActorValue
	EndIf
	If !avCha
		Debug.Trace("PickmansWhisper: ERROR slavery — Charisma AV 0x2C5 missing")
		Debug.Notification("PickmansWhisper: Slavery — Charisma AV missing")
		Return
	EndIf
	Float cha = player.GetValue(avCha)
	If cha < (minCha as Float)
		Debug.Trace("PickmansWhisper: slavery skip | CHA " + cha + " < min " + minCha)
		Debug.Notification("PickmansWhisper: Slavery — Charisma too low (" + (cha as Int) + " < " + minCha + ")")
		Return
	EndIf
	If !InventoryHasSlaveItem(akTarget)
		Debug.Trace("PickmansWhisper: slavery skip | no slave gear id=" + akTarget.GetFormID())
		Debug.Notification("PickmansWhisper: Slavery — needs slave gear")
		Return
	EndIf
	StartSlavery(akTarget)
EndFunction

Function TryFreeSlaveFromActivate(Actor akTarget)
	EnsureSlaveryPerk()
	If !akTarget
		Debug.Trace("PickmansWhisper: slavery free skip | no target")
		Debug.Notification("PickmansWhisper: Slavery — no target")
		Return
	EndIf
	PickmansWhisperMainQuestScript mFree = Main()
	If mFree && mFree.IsBladeEquipped()
		Debug.Trace("PickmansWhisper: slavery free skip | blade drawn")
		Debug.Notification("PickmansWhisper: Slavery — sheath the blade first")
		Return
	EndIf
	If !IsOurSlave(akTarget)
		Debug.Trace("PickmansWhisper: slavery free skip | not our slave id=" + akTarget.GetFormID())
		Debug.Notification("PickmansWhisper: Slavery — she is not yours")
		Return
	EndIf
	ClearSlave("free activate")
	Debug.Notification("PickmansWhisper: Slavery — freed")
EndFunction

; PlayerAlias OnLocationChange — keep enslaved NPC with the player across cells.
Function WarpSlaveToPlayerIfNeeded()
	If !Slave
		Return
	EndIf
	If Slave.IsDead()
		ClearSlave("dead warp")
		Return
	EndIf
	Actor player = Game.GetPlayer()
	If !player
		Debug.Trace("PickmansWhisper: ERROR slavery warp — no player (latch id=" + SlaveFormID + ")")
		Debug.Notification("PickmansWhisper: Slavery warp failed — no player")
		Return
	EndIf
	Bool needWarp = False
	If !Slave.Is3DLoaded()
		needWarp = True
	ElseIf player.GetDistance(Slave) > WARP_DISTANCE
		needWarp = True
	EndIf
	If !needWarp
		Return
	EndIf
	Slave.MoveTo(player)
	Debug.Trace("PickmansWhisper: slavery warp MoveTo player id=" + SlaveFormID)
EndFunction

Event Actor.OnDeath(Actor akSender, Actor akKiller)
	If IsOurSlave(akSender)
		ClearSlave("death")
	EndIf
EndEvent
