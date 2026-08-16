Scriptname PickmansWhisperExecuteScript extends Quest
{Slice W — instant kill (Decapitate / Smash Head In) on a LIVING, eligible victim via a
new hotkey (\). Fully isolated from the existing corpse-sever feature (Slice F, / key,
PW_SeverLimbMenu, SeverCorpseLimb) — different hotkey, different MSG menu
(PW_ExecuteMenu), different Dismember call site; zero changes to any existing corpse-sever
code or behavior. Decapitate requires Pickman's Blade equipped (Main.IsBladeEquipped, same
gate as every other blade feature). Smash Head In requires one of a small curated set of
real, verified heavy blunt melee WEAP forms (BaseballBat/Sledgehammer/SuperSledge/
PipeWrench/PoolCue) — FO4 has no generic "blunt" keyword shared across these (confirmed by
scanning Fallout4.esm's own KWDA lists directly: each only carries its own weapon-specific
ma_* animation keyword plus the generic WeaponTypeMelee1H/2H handedness keyword, which is
also shared by bladed weapons like Shishkebab), so a curated FormID list is the only honest
option, not a keyword check. Both paths reuse Main.IsValidTarget(ak, False) (non-hostile
only) as the hard eligibility gate — the same essential/protected-NPC-safe check every
other feature in this mod relies on. Kill sequence: RegisterTarget (defensive — guarantees
OnDeath is hooked even if ambient TargetScan hasn't caught her yet) -> KillSilent(player)
(Protected-actor-safe pattern already used elsewhere in this mod — a killerless KillSilent
can leave Protected actors alive) -> Dismember("Head1", ...) for the visual. No new
kill-crediting code: the existing OnDeath -> RewardKill -> ProcessKnifeKill pipeline
(hunger satiation, decay stamp, named-kill voice) picks this up automatically like any
other blade kill — this script only owns the aim/menu/weapon-check/kill-visual side.}

; Heavy blunt melee WEAP forms — verified directly against Fallout4.esm (scanned every
; WEAP record's KWDA list; confirmed no shared "blunt" keyword exists), not guessed.
Int FID_WEAP_BASEBALLBAT = 0x0008E736 ; BaseballBat
Int FID_WEAP_SLEDGEHAMMER = 0x000E7AB9 ; Sledgehammer
Int FID_WEAP_SUPERSLEDGE = 0x000FF964 ; SuperSledge
Int FID_WEAP_PIPEWRENCH = 0x000D83BF ; PipeWrench
Int FID_WEAP_POOLCUE = 0x000FA3E8 ; PoolCue

Weapon WeapBaseballBat
Weapon WeapSledgehammer
Weapon WeapSuperSledge
Weapon WeapPipeWrench
Weapon WeapPoolCue

; PW_ExecuteMenu MESG — built in tools/build_hunger_spell_esp.py, same pattern as the
; existing PW_SeverLimbMenu. Resolved dynamically (not a VMAD property), matching how
; EnsureSeverLimbMenu resolves FID_SEVER_MSG.
Int FID_EXECUTE_MSG = 0x0100087B
Message ExecuteMenu

Float EXECUTE_RADIUS = 500.0 ; matches Main's BUTCHER_CORPSE_RADIUS — same aim-range feel

PickmansWhisperMainQuestScript Function Main()
	Return (Self as Quest) as PickmansWhisperMainQuestScript
EndFunction

PickmansWhisperVictimsScript Function Victims()
	Return (Self as Quest) as PickmansWhisperVictimsScript
EndFunction

PickmansWhisperCorpseDecayScript Function CorpseDecay()
	Return (Self as Quest) as PickmansWhisperCorpseDecayScript
EndFunction

Function ResolveWeaponForms()
	If !WeapBaseballBat
		WeapBaseballBat = Game.GetFormFromFile(FID_WEAP_BASEBALLBAT, "Fallout4.esm") as Weapon
	EndIf
	If !WeapSledgehammer
		WeapSledgehammer = Game.GetFormFromFile(FID_WEAP_SLEDGEHAMMER, "Fallout4.esm") as Weapon
	EndIf
	If !WeapSuperSledge
		WeapSuperSledge = Game.GetFormFromFile(FID_WEAP_SUPERSLEDGE, "Fallout4.esm") as Weapon
	EndIf
	If !WeapPipeWrench
		WeapPipeWrench = Game.GetFormFromFile(FID_WEAP_PIPEWRENCH, "Fallout4.esm") as Weapon
	EndIf
	If !WeapPoolCue
		WeapPoolCue = Game.GetFormFromFile(FID_WEAP_POOLCUE, "Fallout4.esm") as Weapon
	EndIf
EndFunction

Bool Function IsHeavyBluntMeleeEquipped()
	Actor player = Game.GetPlayer()
	If !player
		Return False
	EndIf
	ResolveWeaponForms()
	Weapon w = player.GetEquippedWeapon()
	If !w
		Return False
	EndIf
	If w == WeapBaseballBat || w == WeapSledgehammer || w == WeapSuperSledge || w == WeapPipeWrench || w == WeapPoolCue
		Return True
	EndIf
	Return False
EndFunction

Function EnsureExecuteMenu()
	If ExecuteMenu
		Return
	EndIf
	ExecuteMenu = Game.GetFormFromFile(FID_EXECUTE_MSG, "PickmansWhisper.esp") as Message
	If !ExecuteMenu
		Debug.Trace("PickmansWhisper: ERROR PW_ExecuteMenu 0x87B missing — rebuild ESP")
	EndIf
EndFunction

; Reuses VictimsScript's general-purpose living-actor aim resolver (camera + activate
; target + one-actor cache) rather than duplicating camera-resolution logic — that
; function is already shared, non-corpse-specific infrastructure, not something this
; feature owns. Only the range pre-filter here is Execute-specific.
Actor Function ResolveExecuteAim()
	Actor player = Game.GetPlayer()
	If !player
		Return None
	EndIf
	PickmansWhisperVictimsScript v = Victims()
	Actor aimed = None
	If v
		aimed = v.ResolveVictimsAimActor()
	EndIf
	If !aimed || aimed == player
		Return None
	EndIf
	If player.GetDistance(aimed) > EXECUTE_RADIUS
		Return None
	EndIf
	Return aimed
EndFunction

Bool Function IsExecuteEligible(Actor ak)
	If !ak || ak.IsDead()
		Return False
	EndIf
	PickmansWhisperMainQuestScript m = Main()
	If !m
		Return False
	EndIf
	Return m.IsValidTarget(ak, False)
EndFunction

; Hotkey entry point (\ — see PlayerAliasScript.RegisterExecuteKey / KEY_EXECUTE). Mirrors
; TrySeverAimedCorpse's shape but targets a LIVING eligible victim instead of a corpse.
Function TryExecuteAimedVictim()
	PickmansWhisperMainQuestScript m = Main()
	If !m
		Debug.Notification("Pickman's Whisper: execute menu — main quest missing")
		Return
	EndIf
	If m.IsNecroSceneActive()
		m.DiagNotify("Pickman's Whisper: execute unavailable during Necromantic scene")
		Return
	EndIf
	If !m.IsBladeEquipped() && !IsHeavyBluntMeleeEquipped()
		m.DiagNotify("Pickman's Whisper: draw Pickman's Blade or a heavy blunt weapon for the execute menu")
		Return
	EndIf
	Actor aimed = ResolveExecuteAim()
	If !aimed || !IsExecuteEligible(aimed)
		m.DiagNotify("Pickman's Whisper: aim / face an eligible living target for the execute menu")
		Return
	EndIf
	EnsureExecuteMenu()
	If !ExecuteMenu
		m.DiagNotify("Pickman's Whisper: execute menu missing — rebuild ESP")
		Return
	EndIf
	Int btn = ExecuteMenu.Show()
	; 0 Sever Head / 1 Smash Head In / 2 Cancel
	If btn < 0
		m.DiagNotify("Pickman's Whisper: execute menu Show failed (btn=" + btn + ")")
		Debug.Trace("PickmansWhisper: ERROR ExecuteMenu.Show returned " + btn)
		Return
	EndIf
	If btn == 0
		TryDecapitate(aimed)
	ElseIf btn == 1
		TrySmashHeadIn(aimed)
	EndIf
EndFunction

Function TryDecapitate(Actor ak)
	PickmansWhisperMainQuestScript m = Main()
	If !m
		Return
	EndIf
	If !m.IsBladeEquipped()
		m.DiagNotify("Pickman's Whisper: decapitate requires Pickman's Blade equipped")
		Debug.Trace("PickmansWhisper: execute skip | decapitate — blade not equipped")
		Return
	EndIf
	If !IsExecuteEligible(ak)
		m.DiagNotify("Pickman's Whisper: execute — target no longer eligible")
		Debug.Trace("PickmansWhisper: execute skip | decapitate — target no longer eligible")
		Return
	EndIf
	ExecuteKill(ak, False)
EndFunction

Function TrySmashHeadIn(Actor ak)
	PickmansWhisperMainQuestScript m = Main()
	If !m
		Return
	EndIf
	If !IsHeavyBluntMeleeEquipped()
		m.DiagNotify("Pickman's Whisper: smash head in requires a heavy blunt weapon (baseball bat, sledgehammer, super sledge, pipe wrench, pool cue)")
		Debug.Trace("PickmansWhisper: execute skip | smash — no heavy blunt melee equipped")
		Return
	EndIf
	If !IsExecuteEligible(ak)
		m.DiagNotify("Pickman's Whisper: execute — target no longer eligible")
		Debug.Trace("PickmansWhisper: execute skip | smash — target no longer eligible")
		Return
	EndIf
	ExecuteKill(ak, True)
EndFunction

; The actual kill. See class doc comment for the full sequencing rationale.
Function ExecuteKill(Actor ak, Bool abSmash)
	If !ak
		Return
	EndIf
	PickmansWhisperMainQuestScript m = Main()
	If !m
		Return
	EndIf
	Actor player = Game.GetPlayer()
	If !player
		Return
	EndIf
	m.RegisterTarget(ak)
	ak.KillSilent(player)
	If !ak.Is3DLoaded()
		Debug.Trace("PickmansWhisper: execute — corpse 3D not loaded post-kill, skipping dismember visual id=0x" + GardenOfEden.GetHexFormID(ak))
		Return
	EndIf
	ak.Dismember("Head1", False, True, abSmash)
	PickmansWhisperCorpseDecayScript decay = CorpseDecay()
	If decay
		decay.QueueStripBodyDecayAfterDismember(ak)
	EndIf
	If abSmash
		Debug.Notification("Pickman's Whisper: head smashed in")
		Debug.Trace("PickmansWhisper: execute smash id=0x" + GardenOfEden.GetHexFormID(ak))
	Else
		Debug.Notification("Pickman's Whisper: decapitated")
		Debug.Trace("PickmansWhisper: execute decapitate id=0x" + GardenOfEden.GetHexFormID(ak))
	EndIf
EndFunction
