Scriptname PickmansWhisperPlayerAliasScript extends ReferenceAlias

; OnPlayerLoadGame here is the reliable FO4 load hook — forward into main so
; killscan/notice timers arm without opening MCM Debug.
;
; Slice F butcher key: RegisterForKey + OnKeyDown live HERE (player alias), not
; on the main Quest. Quest key registration is unreliable in FO4/F4SE.
; Slice G sleep: RegisterForPlayerSleep lives on BedGiftScript; this alias only
; re-arms it every load via GetBedGift().RegisterBedGiftSleep().

Int FID_MAIN_QUEST = 0x00000800
; F4SE RegisterForKey uses Windows VK codes (same as Necromantic N=78), not DX DIK.
; /? on US keyboards = VK_OEM_2 = 191 (DIK 53 was wrong and never fired).
Int KEY_BUTCHER = 191
; ] — VK_OEM_6 = 221. Toggles Force Trade / Enslave / Free activate choices (default off).
Int KEY_DIALOG_ACTIVATE = 221
; Slice W execute menu (Decapitate / Smash Head In on a LIVING victim) — \ on US keyboards
; = VK_OEM_5 = 220. Distinct from the / butcher key (corpse-only) and ] dialog toggle.
Int KEY_EXECUTE = 220
Bool ButcherKeyRegistered = False
Bool DialogActivateKeyRegistered = False
Bool ExecuteKeyRegistered = False
; Slice H P5 — magic-effect-apply detection lives here, not on the Quest. A Quest-level
; RegisterForMagicEffectApplyEvent(PlayerRef, ...) was tried first and confirmed dead
; live (an unfiltered sniff variant caught zero effects over two minutes of play, even
; though the registration call itself reported success) — this alias is filled with the
; player and already proves other per-player natives work here (RegisterForKey and
; OnCombatStateChanged firing locally with no registration at all), so detection
; moved to match.
Bool MagicEffectDetectRegistered = False
Bool MagicEffectSniffRegistered = False

Weapon Property CombatKnifeBase Auto Const
Keyword Property PickmanModKeyword Auto Const
Bool Property IsPickmansBladeEquipped = False Auto
; True when the player has no weapon equipped (unarmed) — Slice K beat-before-kill gate.
Bool Property IsReadyToGiveBeating = False Auto

Event OnAliasInit()
	EnsurePlayerFill()
	RegisterButcherKey()
	RegisterDialogActivateKey()
	RegisterExecuteKey()
	RegisterMagicEffectDetect()
	CheckIfBladeEquipped()
	PickmansWhisperBedGiftScript bed = GetBedGift()
	If bed
		bed.RegisterBedGiftSleep()
	Else
		Debug.Trace("PickmansWhisper: alias OnAliasInit — BedGift script not found")
	EndIf
	PickmansWhisperMainQuestScript main = GetMain()
	If main
		main.EnsurePlayerCombatQuest()
		main.ArmRuntimeLoops()
		main.ScheduleBootArm()
	Else
		Debug.Trace("PickmansWhisper: alias OnAliasInit — main quest script not found")
	EndIf
EndEvent

Event OnPlayerLoadGame()
	EnsurePlayerFill()
	RegisterButcherKey()
	RegisterDialogActivateKey()
	RegisterExecuteKey()
	RegisterMagicEffectDetect()
	CheckIfBladeEquipped()
	PickmansWhisperBedGiftScript bed = GetBedGift()
	If bed
		bed.RegisterBedGiftSleep()
	Else
		Debug.Trace("PickmansWhisper: alias OnPlayerLoadGame — BedGift script not found")
	EndIf
	PickmansWhisperMainQuestScript main = GetMain()
	If main
		main.HandlePlayerLoadFromAlias()
	Else
		Debug.Trace("PickmansWhisper: alias OnPlayerLoadGame — main quest script not found (timers not armed)")
	EndIf
EndEvent

; Slavery — warp enslaved NPC when the player changes cell/location (remote, like equip).
Event Actor.OnLocationChange(Actor akSender, Location akOldLoc, Location akNewLoc)
	PickmansWhisperSlaveryScript slavery = GetSlavery()
	If slavery
		slavery.WarpSlaveToPlayerIfNeeded()
	EndIf
EndEvent

Event Actor.OnItemEquipped(Actor akSender, Form akBaseObject, ObjectReference akReference)
    CheckAndHandleBladeReady(akSender, akBaseObject)
EndEvent

Event Actor.OnItemUnequipped(Actor akSender, Form akBaseObject, ObjectReference akReference)
	If IsPickmansBlade(akSender, akBaseObject) || IsPickmansBladeEquipped
		Debug.Trace("PW PlayerAlias: Unequipping Pickman's Blade")
		IsPickmansBladeEquipped = False
	EndIf
	; Re-evaluate unarmed / other weapon so IsReadyToGiveBeating stays accurate.
	CheckIfBladeEquipped()
EndEvent

Function CheckIfBladeEquipped()
	; 1. Get the physical Actor reference from the alias
	Actor PlayerRef = Self.GetActorReference()
	Weapon CurrentWeapon = PlayerRef.GetEquippedWeapon()
	CheckAndHandleBladeReady(PlayerRef, CurrentWeapon)
EndFunction

Function CheckAndHandleBladeReady(Actor PlayerRef, Form akBaseObject)
	If !PlayerRef
		Debug.Trace("PickmansWhisper: CheckAndHandleBladeReady skip | no player")
		Return
	EndIf

	If IsPickmansBlade(PlayerRef, akBaseObject)
		Debug.Trace("PW PlayerAlias: Pickman's Blade is Equipped")
		IsPickmansBladeEquipped = True
		IsReadyToGiveBeating = False

		PickmansWhisperMainQuestScript main = GetMain()
		If main
			main.StartBond("blade-equipped")
			main.SyncBladeDrawnDebugLatch()
		EndIf
	ElseIf !PlayerRef.GetEquippedWeapon()
		; Unarmed — no weapon in either hand.
		IsPickmansBladeEquipped = False
		IsReadyToGiveBeating = True
		Debug.Trace("PickmansWhisper: PlayerAlias unarmed — IsReadyToGiveBeating=True")
		PickmansWhisperMainQuestScript mainUnarmed = GetMain()
		If mainUnarmed
			mainUnarmed.SyncBladeDrawnDebugLatch()
		EndIf
	Else
		; Some other weapon equipped.
		IsPickmansBladeEquipped = False
		IsReadyToGiveBeating = False
		PickmansWhisperMainQuestScript mainOther = GetMain()
		If mainOther
			mainOther.SyncBladeDrawnDebugLatch()
		EndIf
	EndIf

	; Slice K5 — any weapon (blade or other) ends beat-before-kill temp essential.
	If !IsReadyToGiveBeating
		PickmansWhisperBeatBeforeKillScript beat = GetBeatBeforeKill()
		If beat
			beat.ClearAllEssentialOnWeaponEquip()
		EndIf
	EndIf
EndFunction

PickmansWhisperBeatBeforeKillScript Function GetBeatBeforeKill()
	Quest q = Game.GetFormFromFile(FID_MAIN_QUEST, "PickmansWhisper.esp") as Quest
	If !q
		Return None
	EndIf
	Return q as PickmansWhisperBeatBeforeKillScript
EndFunction

Bool Function IsPickmansBlade(Actor PlayerRef, Form akBaseObject)
	If akBaseObject == CombatKnifeBase
        ; Add a microscopic delay to let the visual mods initialize on the skeleton
        Utility.Wait(0.1) 
        
        ; WornHasKeyword checks the player's actively equipped gear for the injected keyword
        If PlayerRef.WornHasKeyword(PickmanModKeyword)
            Debug.Trace("Pickman's Blade Mod Detected!")
            return true
        EndIf
    EndIf

	return false
EndFunction

; Re-register every load, same pattern as RegisterButcherKey.
Function RegisterMagicEffectDetect()
	PickmansWhisperMainQuestScript main = GetMain()
	If !main
		Debug.Trace("PickmansWhisper: alias RegisterMagicEffectDetect — main quest script not found")
		Return
	EndIf
	MagicEffect effect = main.GetRestoreHealthGenericEffect()
	If !effect
		Debug.Trace("PickmansWhisper: ERROR alias RegisterMagicEffectDetect — RestoreHealthGenericEffect missing")
		Return
	EndIf
	If MagicEffectDetectRegistered
		UnregisterForMagicEffectApplyEvent(Self, None, effect, True)
	EndIf
	RegisterForMagicEffectApplyEvent(Self, None, effect, True)
	MagicEffectDetectRegistered = True
	Debug.Trace("PickmansWhisper: alias registered MagicEffectApply effect=" + effect)
EndFunction

; Called by MainQuestScript.SyncMagicEffectSniffer (MCM Debug switcher). Unfiltered catch-
; all — UnregisterForAllMagicEffectApplyEvents wipes the real registration too, so turning
; sniffing off must re-arm it.
Function SyncMagicEffectSniff(Bool abWant)
	If abWant == MagicEffectSniffRegistered
		Return
	EndIf
	MagicEffectSniffRegistered = abWant
	If abWant
		RegisterForMagicEffectApplyEvent(Self)
		Debug.Trace("PickmansWhisper: alias DEBUG magic-effect sniffer ON")
	Else
		UnregisterForAllMagicEffectApplyEvents(Self)
		RegisterMagicEffectDetect()
		Debug.Trace("PickmansWhisper: alias DEBUG magic-effect sniffer OFF")
	EndIf
EndFunction

; Local alias event — must match ScriptObject's declared OnMagicEffectApply signature
; EXACTLY (all 3 params; Caprica rejects a shortened override — confirmed by compile
; error: "doesn't match the signature in the parent class 'ScriptObject'"). Unlike
; OnCombatStateChanged, this event does not drop akTarget for local use.
Event OnMagicEffectApply(ObjectReference akTarget, ObjectReference akCaster, MagicEffect akEffect)
	Debug.Notification("OnMagicEffectApply")
	PickmansWhisperMainQuestScript main = GetMain()
	If main
		main.HandlePlayerMagicEffectApply(akEffect)
	EndIf
EndEvent

Function RegisterButcherKey()
	If ButcherKeyRegistered
		UnregisterForKey(KEY_BUTCHER)
	EndIf
	RegisterForKey(KEY_BUTCHER)
	ButcherKeyRegistered = True
	Debug.Trace("PickmansWhisper: alias registered butcher key " + KEY_BUTCHER)
EndFunction

Function RegisterDialogActivateKey()
	If DialogActivateKeyRegistered
		UnregisterForKey(KEY_DIALOG_ACTIVATE)
	EndIf
	RegisterForKey(KEY_DIALOG_ACTIVATE)
	DialogActivateKeyRegistered = True
	Debug.Trace("PickmansWhisper: alias registered dialog-activate toggle key " + KEY_DIALOG_ACTIVATE)
EndFunction

Function RegisterExecuteKey()
	If ExecuteKeyRegistered
		UnregisterForKey(KEY_EXECUTE)
	EndIf
	RegisterForKey(KEY_EXECUTE)
	ExecuteKeyRegistered = True
	Debug.Trace("PickmansWhisper: alias registered execute key " + KEY_EXECUTE)
EndFunction

Event OnKeyDown(Int keyCode)
	If keyCode == KEY_DIALOG_ACTIVATE
		PickmansWhisperMainQuestScript mainToggle = GetMain()
		If !mainToggle
			Debug.Trace("PickmansWhisper: Trade/Enslave toggle — main quest missing")
			Return
		EndIf
		mainToggle.ToggleDialogActivateChoices()
		Return
	EndIf
	If keyCode == KEY_EXECUTE
		PickmansWhisperMainQuestScript mainExecute = GetMain()
		If !mainExecute
			Debug.Notification("Pickman's Whisper: execute menu — main quest missing")
			Return
		EndIf
		mainExecute.TryExecuteAimedVictim()
		Return
	EndIf
	If keyCode != KEY_BUTCHER
		Return
	EndIf
	PickmansWhisperMainQuestScript main = GetMain()
	If !main
		Debug.Notification("Pickman's Whisper: butcher menu — main quest missing")
		Return
	EndIf
	main.TrySeverAimedCorpse()
EndEvent

Function EnsurePlayerFill()
	Actor p = Game.GetPlayer()
	If !p
		Return
	EndIf
	ObjectReference cur = GetReference()
	If cur != (p as ObjectReference)
		ForceRefTo(p)
	EndIf

	; Add the remote event registrations here
	RegisterForRemoteEvent(p, "OnItemEquipped")
	RegisterForRemoteEvent(p, "OnItemUnequipped")
	RegisterForRemoteEvent(p, "OnLocationChange")
EndFunction

PickmansWhisperMainQuestScript Function GetMain()
	Quest q = Game.GetFormFromFile(FID_MAIN_QUEST, "PickmansWhisper.esp") as Quest
	If !q
		Debug.Trace("PickmansWhisper: GetFormFromFile main quest 0x800 failed")
		Return None
	EndIf
	PickmansWhisperMainQuestScript main = q as PickmansWhisperMainQuestScript
	If !main
		Debug.Trace("PickmansWhisper: main quest cast to PickmansWhisperMainQuestScript failed")
	EndIf
	Return main
EndFunction

; BedGift is attached to PickmansWhisperMain (0x800), NOT this alias's owning quest
; (PlayerCombat 0x805). Always resolve Main via FormID — GetOwningQuest cast fails.
PickmansWhisperBedGiftScript Function GetBedGift()
	Quest q = Game.GetFormFromFile(FID_MAIN_QUEST, "PickmansWhisper.esp") as Quest
	If !q
		Debug.Trace("PickmansWhisper: GetBedGift — GetFormFromFile main quest 0x800 failed")
		Return None
	EndIf
	PickmansWhisperBedGiftScript bed = q as PickmansWhisperBedGiftScript
	If !bed
		Debug.Trace("PickmansWhisper: GetBedGift — BedGift script cast failed (is BedGift on Main VMAD?)")
	EndIf
	Return bed
EndFunction

PickmansWhisperSlaveryScript Function GetSlavery()
	Quest q = Game.GetFormFromFile(FID_MAIN_QUEST, "PickmansWhisper.esp") as Quest
	If !q
		Return None
	EndIf
	Return q as PickmansWhisperSlaveryScript
EndFunction
