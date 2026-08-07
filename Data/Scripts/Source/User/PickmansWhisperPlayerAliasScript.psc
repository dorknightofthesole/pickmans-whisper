Scriptname PickmansWhisperPlayerAliasScript extends ReferenceAlias

; OnPlayerLoadGame here is the reliable FO4 load hook — forward into main so
; killscan/notice timers arm without opening MCM Debug.
;
; Slice F butcher key: RegisterForKey + OnKeyDown live HERE (player alias), not
; on the main Quest. Quest key registration is unreliable in FO4/F4SE.
; Slice G sleep: RegisterForPlayerSleep also lives HERE for the same reason.

Int FID_MAIN_QUEST = 0x00000800
; F4SE RegisterForKey uses Windows VK codes (same as Necromantic N=78), not DX DIK.
; /? on US keyboards = VK_OEM_2 = 191 (DIK 53 was wrong and never fired).
Int KEY_BUTCHER = 191
Bool ButcherKeyRegistered = False
Bool BedSleepRegistered = False
; Slice H P5 — magic-effect-apply detection lives here, not on the Quest. A Quest-level
; RegisterForMagicEffectApplyEvent(PlayerRef, ...) was tried first and confirmed dead
; live (an unfiltered sniff variant caught zero effects over two minutes of play, even
; though the registration call itself reported success) — this alias is filled with the
; player and already proves other per-player natives work here (RegisterForKey,
; RegisterForPlayerSleep, and OnCombatStateChanged firing locally with no registration
; at all), so detection moved to match.
Bool MagicEffectDetectRegistered = False
Bool MagicEffectSniffRegistered = False

Weapon Property CombatKnifeBase Auto Const
Keyword Property PickmanModKeyword Auto Const
Bool Property IsPickmansBladeEquipped = False Auto
; True when the player has no weapon equipped (unarmed) — Slice Q beat-before-kill gate.
Bool Property IsReadyToGiveBeating = False Auto

Event OnAliasInit()
	EnsurePlayerFill()
	RegisterButcherKey()
	RegisterBedGiftSleep()
	RegisterMagicEffectDetect()
	CheckIfBladeEquipped()
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
	RegisterBedGiftSleep()
	RegisterMagicEffectDetect()
	CheckIfBladeEquipped()
	PickmansWhisperMainQuestScript main = GetMain()
	If main
		main.HandlePlayerLoadFromAlias()
	Else
		Debug.Trace("PickmansWhisper: alias OnPlayerLoadGame — main quest script not found (timers not armed)")
	EndIf
EndEvent

Event Actor.OnItemEquipped(Actor akSender, Form akBaseObject, ObjectReference akReference)
    Debug.Notification("PW PlayerAlias: OnItemEquipped")
	CheckAndHandleBladeReady(akSender, akBaseObject)
EndEvent

Event Actor.OnItemUnequipped(Actor akSender, Form akBaseObject, ObjectReference akReference)
	Debug.Notification("PW PlayerAlias: OnItemUnequipped")

	If IsPickmansBlade(akSender, akBaseObject) || IsPickmansBladeEquipped
		Debug.Notification("PW PlayerAlias: Unequipping Pickman's Blade")
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
		Debug.Notification("PW PlayerAlias: Pickman's Blade is Equipped")
		IsPickmansBladeEquipped = True
		IsReadyToGiveBeating = False

		PickmansWhisperMainQuestScript main = GetMain()
		If main
			main.StartBond("blade-equipped")
		EndIf
	ElseIf !PlayerRef.GetEquippedWeapon()
		; Unarmed — no weapon in either hand.
		IsPickmansBladeEquipped = False
		IsReadyToGiveBeating = True
		Debug.Trace("PickmansWhisper: PlayerAlias unarmed — IsReadyToGiveBeating=True")
	Else
		; Some other weapon equipped.
		IsReadyToGiveBeating = False
	EndIf
EndFunction

Bool Function IsPickmansBlade(Actor PlayerRef, Form akBaseObject)
	If akBaseObject == CombatKnifeBase
        ; Add a microscopic delay to let the visual mods initialize on the skeleton
        Utility.Wait(0.1) 
        
        ; WornHasKeyword checks the player's actively equipped gear for the injected keyword
        If PlayerRef.WornHasKeyword(PickmanModKeyword)
            Debug.Notification("Pickman's Blade Mod Detected!")
            return true
        EndIf
    EndIf

	return false
EndFunction

; Re-register every load, same pattern as RegisterButcherKey/RegisterBedGiftSleep.
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

; Re-register every load — Quest-level sleep registration was missing most sleeps.
Function RegisterBedGiftSleep()
	If BedSleepRegistered
		UnregisterForPlayerSleep()
	EndIf
	RegisterForPlayerSleep()
	BedSleepRegistered = True
	Debug.Trace("PickmansWhisper: alias registered PlayerSleep (bed gift)")
EndFunction

Event OnPlayerSleepStart(Float afSleepStartTime, Float afDesiredSleepEndTime, ObjectReference akBed)
	PickmansWhisperMainQuestScript main = GetMain()
	If !main
		Debug.Trace("PickmansWhisper: alias sleep start — main missing")
		Return
	EndIf
	main.HandlePlayerSleepStart(afSleepStartTime, afDesiredSleepEndTime, akBed)
EndEvent

Event OnPlayerSleepStop(Bool abInterrupted, ObjectReference akBed)
	PickmansWhisperMainQuestScript main = GetMain()
	If !main
		Debug.Trace("PickmansWhisper: alias sleep stop — main missing")
		Return
	EndIf
	main.HandlePlayerSleepStop(abInterrupted, akBed)
EndEvent

Event OnKeyDown(Int keyCode)
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
