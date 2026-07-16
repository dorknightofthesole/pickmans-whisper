Scriptname PickmansWhisperMainQuestScript extends Quest

; Pickman's Whisper — Slice A+B: gallery/blade bond, toast voice, knife hunger, kill satiation.
; Soft companion to Necromantic (no AAF, no compile coupling). Soft deps: F4SE, MCM.

Actor PlayerRef
Form PickmansBlade ; LVLI CustomItem template 0x22595F — not the drawn WEAP
Weapon CombatKnifeBase ; WEAP Knife 0x913CA — what GetEquippedWeapon returns for Pickman's
ObjectMod OmodBleed ; mod_Legendary_Weapon_Bleed 0x1E7C20
ObjectMod OmodStealthBlade ; mod_melee_Knife_SerratedStealth 0x187A10
Cell PickmanGalleryCell

; --- Bond (Auto = saved with the quest) ----------------------------------------
Bool Property BondStarted = False Auto
Float Property BondStartGameTime = 0.0 Auto
Bool Property IntroToastShown = False Auto
Bool Property SeenGallery = False Auto
Bool Property SeenBlade = False Auto
; True once we've seen a unique Pickman's Blade instance (name match). Template FormID
; 0x22595F is CustomItem_DoNotPlaceDirectly_* — inventory copies often have other FormIDs.
Bool Property OwnedPickmansBlade = False Auto
Float Property BondIntensity = 0.0 Auto ; bumped on valid knife kills
Float Property LastKnifeActivityGameTime = 0.0 Auto
Int Property KnifeKillCount = 0 Auto ; valid blade kills that satiated hunger
String BLADE_NAME_NEEDLE = "Pickman's Blade"
; Runtime lofted form: for Pickman's this is usually the Combat Knife WEAP base (GetEquippedWeapon
; never returns LVLI 0x22595F / the display name). Captured when akReference name matches.
; Auto so load with blade already drawn can resync against GetEquippedWeapon(0).
Form Property RuntimeBladeForm Auto
; NOT Auto — runtime only; MCM bKillDebugToasts:Debug is the source of truth (default off).
Bool DebugKillToastsCached = False
Bool DebugKillToastsCacheValid = False

; Human / safety filters (Fallout4.esm keywords)
Keyword KW_ActorTypeNPC
Keyword KW_ActorTypeHuman
Keyword KW_ActorTypeGhoul
Keyword KW_ActorTypeSuperMutant
Keyword KW_ActorTypeSynth
Keyword KW_ActorTypeRobot
Keyword KW_ActorTypeAnimal
Keyword KW_ActorTypeCreature
Keyword KW_ActorTypeTurret

; Kill watch — combat/crosshair victim died while blade out (primary); hit-tag is optional backup
Actor PendingKillVictim
Actor[] KillWatchList
Int KillWatchCount = 0
Int KILL_WATCH_MAX = 12
Int[] BladeTaggedIds
Int BladeTaggedCount = 0
Int BLADE_TAGGED_MAX = 24
Float LastKnifeKillRealTime = 0.0
Float CombatGraceUntilRealTime = 0.0
Float KNIFE_KILL_COOLDOWN = 1.5
Float KILL_WATCH_RADIUS = 800.0
Float KILL_CORPSE_RADIUS = 400.0 ; Necromantic-ish close corpse window
String Property LastKillIgnoreReason = "" Auto
Int LastDeathToastId = 0
Int LastHandledKillId = 0
Cell LastBladeToastCell
Int[] AliveSeenIds
Int AliveSeenCount = 0
Int ALIVE_SEEN_MAX = 32
; FormIDs first seen while NOT hostile to player — settlers you later attack still count.
; Hostiles (raiders) seen already angry never get this stamp → no satiation.
Int[] FriendlySeenIds
Int FriendlySeenCount = 0
Int FRIENDLY_SEEN_MAX = 32
Int[] BackgroundDeadIds
Int BackgroundDeadCount = 0
Int BACKGROUND_DEAD_MAX = 48
Int LastGoeAliveCount = 0
Int LastGoeDeadCount = 0
Int LastDetectCount = 0
String DEBUG_BUILD = "B27-goe" ; GoE equipped name/OMOD scan (Combat Knife base + bleed+stealth)
Bool RefreshDebugBusy = False
Int KillScanTickCount = 0
Bool KillScanArmAnnounced = False
; Drawn latch — refreshed by GoE scan + OnItemEquipped
Bool BladeCurrentlyDrawn = False
Bool DrawnWeaponStateValid = False

; --- Hunger / addiction stand-in ----------------------------------------------
Float Property HungerLevel = 0.0 Auto ; 0–100 once bonded
Float Property SatedUntilGameTime = 0.0 Auto
Float LastHungerPollGameTime = 0.0
Int LastHungerBand = 0 ; 0/25/50/70/90
Bool HungerWasSated
Bool Property HungerAddictionApplied = False Auto
Bool Property HungerStatPenaltyApplied = False Auto
Spell KnifeHungerSpell
MagicEffect KnifeHungerAgiEffect
MagicEffect KnifeHungerChaEffect
GlobalVariable KnifeHungerGlobal
Bool HungerSpellLoadWarned
Float HUNGER_POLL_SECONDS = 12.0
Float BOND_POLL_SECONDS = 4.0
Float TRUST_VOICE_SECONDS = 180.0
Float KILL_SCAN_SECONDS = 2.0 ; Necromantic-style StartTimer id 13

Int TIMER_HUNGER = 1
Int TIMER_BOND = 2
Int TIMER_TRUST = 3
Int TIMER_KILL = 4 ; legacy unused
Int TIMER_KILL_SCAN = 13 ; match Necromantic TIMER_CRAVING id class

; Vanilla anchors (Fallout4.esm)
Int FID_PICKMANS_BLADE = 0x0022595F ; LVLI CustomItem template only
Int FID_COMBAT_KNIFE = 0x000913CA ; WEAP Knife — equipped base for Pickman's
Int FID_OMOD_BLEED = 0x001E7C20 ; mod_Legendary_Weapon_Bleed (Wounding)
Int FID_OMOD_STEALTH = 0x00187A10 ; mod_melee_Knife_SerratedStealth
Int FID_PICKMAN_GALLERY = 0x000379C5

; Local forms (PickmansWhisper.esp) — low word for GetFormFromFile
Int FID_HUNGER_SPEL = 0x00000801
Int FID_HUNGER_GLOB = 0x00000802
Int FID_HUNGER_MGEF_AGI = 0x00000803
Int FID_HUNGER_MGEF_CHA = 0x00000804

String MOD_NAME = "PickmansWhisper"
Int LINE_FILE_MAX = 64

String[] TrustLines
Int TrustLineCount = 0
String[] HungerLines
Int HungerLineCount = 0
String[] PraiseLines
Int PraiseLineCount = 0
Float LastTrustToastRealTime = 0.0
Float LastHungerToastRealTime = 0.0
Float TRUST_TOAST_COOLDOWN = 8.0
Float HUNGER_TOAST_COOLDOWN = 6.0
Float PRAISE_TOAST_COOLDOWN = 2.0
Float LastPraiseToastRealTime = 0.0

Event OnInit()
	; Also fires once when the script attaches (pairs with OnQuestInit on fresh starts).
	PlayerRef = Game.GetPlayer()
	If PlayerRef
		RegisterForRemoteEvent(PlayerRef, "OnCombatStateChanged")
	EndIf
EndEvent

Event OnQuestInit()
	ToastDebug("PW OnQuestInit FIRED [" + DEBUG_BUILD + "]")
	PlayerRef = Game.GetPlayer()
	InvalidateDebugToastCache()
	ResolveVanillaForms()
	EnsureHungerSpell()
	RegisterForRemoteEvent(PlayerRef, "OnPlayerLoadGame")
	RegisterForRemoteEvent(PlayerRef, "OnItemEquipped")
	RegisterForRemoteEvent(PlayerRef, "OnItemUnequipped")
	RegisterForRemoteEvent(PlayerRef, "OnItemAdded")
	RegisterForRemoteEvent(PlayerRef, "OnItemRemoved")
	RegisterForRemoteEvent(PlayerRef, "OnCombatStateChanged")
	RegisterForExternalEvent("OnMCMMenuOpen|PickmansWhisper", "OnMCMMenuOpen")
	RegisterForExternalEvent("OnMCMSettingChange|PickmansWhisper", "OnMCMSettingChange")
	LoadLineBanks()
	ResyncDrawnBladeState()
	RefreshBladeOwnershipFromEquip()
	StartBondPoll()
	StartHungerPoll()
	StartTrustVoice()
	EnsureCombatKillHooks()
	RefreshDebugStatus()
	RefreshHungerPanel(False)
	Debug.Trace("PickmansWhisper: quest init " + DEBUG_BUILD)
	ToastDebug("Pickman's Whisper ready [" + DEBUG_BUILD + "]")
	ToastBladeDetectStatus("load")
EndEvent

Event Actor.OnPlayerLoadGame(Actor akSender)
	PlayerRef = Game.GetPlayer()
	InvalidateDebugToastCache()
	ResolveVanillaForms()
	EnsureHungerSpell()
	RegisterForRemoteEvent(PlayerRef, "OnItemEquipped")
	RegisterForRemoteEvent(PlayerRef, "OnItemUnequipped")
	RegisterForRemoteEvent(PlayerRef, "OnItemAdded")
	RegisterForRemoteEvent(PlayerRef, "OnItemRemoved")
	RegisterForRemoteEvent(PlayerRef, "OnCombatStateChanged")
	LoadLineBanks()
	ResyncDrawnBladeState()
	RefreshBladeOwnershipFromEquip()
	StartBondPoll()
	StartHungerPoll()
	StartTrustVoice()
	EnsureCombatKillHooks()
	SyncHungerAddictionSpell()
	RefreshDebugStatus()
	RefreshHungerPanel(False)
	Debug.Trace("PickmansWhisper: player load " + DEBUG_BUILD)
	ToastDebug("Pickman's Whisper load [" + DEBUG_BUILD + "]")
	ToastBladeDetectStatus("load")
EndEvent

Event Actor.OnItemEquipped(Actor akSender, Form akBaseObject, ObjectReference akReference)
	Weapon asW = akBaseObject as Weapon
	If !asW
		If FormLooksLikePickmansBlade(akBaseObject, akReference)
			RuntimeBladeForm = akBaseObject
			MarkOwnedBlade("equipped")
		EndIf
		Return
	EndIf
	DrawnWeaponStateValid = True
	Bool isPickmans = FormLooksLikePickmansBlade(akBaseObject, akReference)
	If !isPickmans && FormIsCombatKnife(akBaseObject)
		; akReference often None — GoE sees the real equipped instance name/mods
		isPickmans = (FindEquippedPickmansBladeIndex() >= 0)
	EndIf
	If isPickmans
		BladeCurrentlyDrawn = True
		RuntimeBladeForm = akBaseObject
		MarkOwnedBlade("equipped")
		Int idx = FindEquippedPickmansBladeIndex()
		String nm = "(goe)"
		If idx >= 0
			nm = GardenOfEden.GetNthItemName(PlayerRef, idx)
		EndIf
		ToastDebug("PW debug: blade DRAWN [" + DEBUG_BUILD + "] " + nm)
	Else
		BladeCurrentlyDrawn = False
		ClearKillWatchForWeaponSwap()
		ToastDebug("PW debug: other weapon DRAWN — " + akBaseObject.GetName())
	EndIf
EndEvent

Event Actor.OnItemUnequipped(Actor akSender, Form akBaseObject, ObjectReference akReference)
	; Drawn state cleared only when another weapon is equipped (FO4 unequip/re-equip flicker).
EndEvent

Event Actor.OnItemAdded(Actor akSender, Form akBaseItem, Int aiItemCount, ObjectReference akItemReference, ObjectReference akSourceContainer)
	If FormLooksLikePickmansBlade(akBaseItem, akItemReference)
		If akBaseItem as Weapon
			RuntimeBladeForm = akBaseItem
		EndIf
		MarkOwnedBlade("added")
	EndIf
EndEvent

Event Actor.OnItemRemoved(Actor akSender, Form akBaseItem, Int aiItemCount, ObjectReference akItemReference, ObjectReference akDestContainer)
	If FormLooksLikePickmansBlade(akBaseItem, akItemReference) || IsPickmansBladeForm(akBaseItem)
		If !IsBladeEquipped() && !HasTemplateBlade()
			OwnedPickmansBlade = False
			Debug.Trace("PickmansWhisper: blade ownership cleared (removed)")
		EndIf
	EndIf
EndEvent

Event OnTimer(Int aiTimerID)
	If aiTimerID == TIMER_BOND
		RunBondPoll()
		StartBondPoll()
	ElseIf aiTimerID == TIMER_HUNGER
		RunHungerTick()
		StartHungerPoll()
	ElseIf aiTimerID == TIMER_TRUST
		MaybeSpeakTrustLine()
		StartTrustVoice()
	ElseIf aiTimerID == TIMER_KILL || aiTimerID == TIMER_KILL_SCAN
		RunKillScanTick()
		StartKillScanLoop()
	EndIf
EndEvent

Event Actor.OnDeath(Actor akSender, Actor akKiller)
	ToastHumanKillDetected(akSender, "OnDeath")
	HandlePotentialKnifeKill(akSender, akKiller)
EndEvent

; Soft backup only — quiet settler kills often never raise combat state.
Event Actor.OnCombatStateChanged(Actor akSender, Actor akTarget, Int aeCombatState)
	If akSender != PlayerRef
		Return
	EndIf
	If aeCombatState == 1 && akTarget
		TrackLivingNear(akTarget)
	EndIf
EndEvent

Event OnHit(ObjectReference akTarget, ObjectReference akAggressor, Form akSource, Projectile akProjectile, Bool abPowerAttack, Bool abSneakAttack, Bool abBashAttack, Bool abHitBlocked, String asMaterialName)
	HandleBladeHit(akTarget, akAggressor, akSource)
EndEvent

Function ResolveVanillaForms()
	If !PickmansBlade
		PickmansBlade = Game.GetFormFromFile(FID_PICKMANS_BLADE, "Fallout4.esm")
		If PickmansBlade
			Debug.Trace("PickmansWhisper: blade LVLI template loaded")
		Else
			Debug.Trace("PickmansWhisper: ERROR Pickman's Blade LVLI missing")
		EndIf
	EndIf
	If !CombatKnifeBase
		CombatKnifeBase = Game.GetFormFromFile(FID_COMBAT_KNIFE, "Fallout4.esm") as Weapon
		If CombatKnifeBase
			Debug.Trace("PickmansWhisper: Combat Knife WEAP loaded")
		Else
			Debug.Trace("PickmansWhisper: ERROR Combat Knife WEAP 0x913CA missing")
		EndIf
	EndIf
	If !OmodBleed
		OmodBleed = Game.GetFormFromFile(FID_OMOD_BLEED, "Fallout4.esm") as ObjectMod
	EndIf
	If !OmodStealthBlade
		OmodStealthBlade = Game.GetFormFromFile(FID_OMOD_STEALTH, "Fallout4.esm") as ObjectMod
	EndIf
	If !PickmanGalleryCell
		PickmanGalleryCell = Game.GetFormFromFile(FID_PICKMAN_GALLERY, "Fallout4.esm") as Cell
		If PickmanGalleryCell
			Debug.Trace("PickmansWhisper: gallery cell loaded")
		Else
			Debug.Trace("PickmansWhisper: ERROR PickmanGallery01 missing")
		EndIf
	EndIf
EndFunction

; --- Bond / trigger ------------------------------------------------------------

Function StartBondPoll()
	CancelTimer(TIMER_BOND)
	StartTimer(BOND_POLL_SECONDS, TIMER_BOND)
EndFunction

Function RunBondPoll()
	If !PlayerRef
		PlayerRef = Game.GetPlayer()
	EndIf
	If !PlayerRef || Utility.IsInMenuMode()
		Return
	EndIf
	ResolveVanillaForms()

	; Bond poll survives save load — arm/run kill scan here (SingleUpdate does not).
	StartKillScanLoop()
	RunKillScanTick()

	Bool inGallery = IsPlayerInGallery()
	Bool hasBlade = PlayerHasBlade()
	Bool equipped = IsBladeEquipped()

	; Scene/cell change blade status toast (Caprica has no Location type for OnLocationChange)
	Cell curCell = PlayerRef.GetParentCell()
	If curCell && curCell != LastBladeToastCell
		LastBladeToastCell = curCell
		ToastBladeDetectStatus("scene")
	EndIf

	If inGallery && !SeenGallery
		SeenGallery = True
		Debug.Trace("PickmansWhisper: entered Pickman Gallery")
	EndIf
	If hasBlade && !SeenBlade
		SeenBlade = True
		Debug.Trace("PickmansWhisper: acquired Pickman's Blade")
	EndIf

	If !BondStarted && (inGallery || hasBlade || equipped)
		StartBond("trigger")
	EndIf
EndFunction

Bool Function IsPlayerInGallery()
	If !PlayerRef
		Return False
	EndIf
	Cell cur = PlayerRef.GetParentCell()
	If !cur
		Return False
	EndIf
	If PickmanGalleryCell && cur == PickmanGalleryCell
		Return True
	EndIf
	Int id = cur.GetFormID()
	Int low = id - (id / 0x01000000) * 0x01000000
	Return low == FID_PICKMAN_GALLERY
EndFunction

Bool Function NameLooksLikePickmansBlade(String n)
	If n == ""
		Return False
	EndIf
	Return StringUtil.Find(n, BLADE_NAME_NEEDLE) >= 0
EndFunction

Bool Function FormIsCombatKnife(Form f)
	If !f
		Return False
	EndIf
	If CombatKnifeBase && (f == CombatKnifeBase || f.GetFormID() == CombatKnifeBase.GetFormID())
		Return True
	EndIf
	; Fallback FormID if resolve failed
	Int id = f.GetFormID()
	Int low = id - (id / 0x01000000) * 0x01000000
	Return low == FID_COMBAT_KNIFE
EndFunction

; GoE inventory slot: Pickman's = display name OR (Knife base + bleed + stealth OMODs).
Bool Function InventorySlotIsPickmansBlade(Int aiItemIndex)
	If !PlayerRef || aiItemIndex < 0
		Return False
	EndIf
	String itemName = GardenOfEden.GetNthItemName(PlayerRef, aiItemIndex)
	If NameLooksLikePickmansBlade(itemName)
		Return True
	EndIf
	Int formId = GardenOfEden.GetNthItemFormID(PlayerRef, aiItemIndex)
	Int low = formId - (formId / 0x01000000) * 0x01000000
	If low != FID_COMBAT_KNIFE && !(CombatKnifeBase && formId == CombatKnifeBase.GetFormID())
		Return False
	EndIf
	; CustomItemMods_DN101PickmansBlade: bleed legendary + serrated stealth
	If OmodBleed && OmodStealthBlade
		If GardenOfEden.GetNthItemHasMod(PlayerRef, aiItemIndex, OmodBleed) > 0
			If GardenOfEden.GetNthItemHasMod(PlayerRef, aiItemIndex, OmodStealthBlade) > 0
				Return True
			EndIf
		EndIf
	EndIf
	; Legendary-only soft match on knife (weaker — any Wounding knife)
	ObjectMod leg = GardenOfEden.GetNthItemLegendaryMod(PlayerRef, aiItemIndex)
	If OmodBleed && leg && leg == OmodBleed && OmodStealthBlade
		If GardenOfEden.GetNthItemHasMod(PlayerRef, aiItemIndex, OmodStealthBlade) > 0
			Return True
		EndIf
	EndIf
	Return False
EndFunction

; Returns equipped inventory index of Pickman's Blade, or -1.
Int Function FindEquippedPickmansBladeIndex()
	If !PlayerRef
		Return -1
	EndIf
	ResolveVanillaForms()
	; Fast path: name lookup
	Int[] byName = GardenOfEden.GetItemIndexesByName(PlayerRef, BLADE_NAME_NEEDLE, False, False)
	If byName
		Int n = byName.Length
		Int i = 0
		While i < n
			Int idx = byName[i]
			If GardenOfEden.GetNthItemIsEquipped(PlayerRef, idx) > 0
				Return idx
			EndIf
			i += 1
		EndWhile
	EndIf
	; Equipped slots: Combat Knife + Pickman's OMOD pair
	Int[] eq = GardenOfEden.GetEquippedItemIndexes(PlayerRef)
	If !eq
		Return -1
	EndIf
	Int e = 0
	While e < eq.Length
		Int idx = eq[e]
		If GardenOfEden.GetNthItemIsEquipped(PlayerRef, idx) > 0
			If InventorySlotIsPickmansBlade(idx)
				Return idx
			EndIf
		EndIf
		e += 1
	EndWhile
	Return -1
EndFunction

Bool Function PlayerOwnsPickmansBladeInstance()
	If !PlayerRef
		Return False
	EndIf
	ResolveVanillaForms()
	Int[] byName = GardenOfEden.GetItemIndexesByName(PlayerRef, BLADE_NAME_NEEDLE, False, False)
	If byName && byName.Length > 0
		Return True
	EndIf
	; Scan a bounded inventory window for OMOD pair (avoid huge bags)
	Int count = GardenOfEden.GetInventoryItemCount(PlayerRef)
	If count <= 0
		Return False
	EndIf
	If count > 80
		count = 80
	EndIf
	Int i = 0
	While i < count
		If InventorySlotIsPickmansBlade(i)
			Return True
		EndIf
		i += 1
	EndWhile
	Return False
EndFunction

; Legendary uniques: GetEquippedWeapon name is often "Combat Knife".
Bool Function FormLooksLikePickmansBlade(Form f, ObjectReference akRef)
	If IsPickmansBladeForm(f)
		Return True
	EndIf
	If akRef
		If NameLooksLikePickmansBlade(akRef.GetDisplayName())
			Return True
		EndIf
		If NameLooksLikePickmansBlade(akRef.GetName())
			Return True
		EndIf
		; F4SE OMOD scan on the instance ref
		If FormIsCombatKnife(f) && RefHasPickmansMods(akRef)
			Return True
		EndIf
	EndIf
	If FormIsCombatKnife(f) && FindEquippedPickmansBladeIndex() >= 0
		Return True
	EndIf
	Return False
EndFunction

Bool Function RefHasPickmansMods(ObjectReference akRef)
	If !akRef || !OmodBleed || !OmodStealthBlade
		Return False
	EndIf
	ObjectMod[] mods = akRef.GetAllMods()
	If !mods || mods.Length == 0
		Return False
	EndIf
	Bool hasBleed = False
	Bool hasStealth = False
	Int i = 0
	While i < mods.Length
		ObjectMod m = mods[i]
		If m == OmodBleed
			hasBleed = True
		ElseIf m == OmodStealthBlade
			hasStealth = True
		EndIf
		i += 1
	EndWhile
	Return hasBleed && hasStealth
EndFunction

Bool Function IsPickmansBladeForm(Form f)
	If !f
		Return False
	EndIf
	If PickmansBlade && (f == PickmansBlade || f.GetFormID() == PickmansBlade.GetFormID())
		Return True
	EndIf
	If NameLooksLikePickmansBlade(f.GetName())
		Return True
	EndIf
	Return False
EndFunction

Bool Function HasTemplateBlade()
	If !PlayerRef || !PickmansBlade
		Return False
	EndIf
	Return PlayerRef.GetItemCount(PickmansBlade) > 0
EndFunction

Function MarkOwnedBlade(String reason)
	OwnedPickmansBlade = True
	If !SeenBlade
		SeenBlade = True
		Debug.Trace("PickmansWhisper: acquired Pickman's Blade (" + reason + ")")
	EndIf
	If !BondStarted
		StartBond(reason)
	EndIf
EndFunction

Function RefreshBladeOwnershipFromEquip()
	If IsBladeEquipped()
		MarkOwnedBlade("equip-scan")
	ElseIf HasTemplateBlade()
		MarkOwnedBlade("template-count")
	EndIf
EndFunction

String Function GetEquippedWeaponName()
	If !PlayerRef
		Return ""
	EndIf
	Weapon w = PlayerRef.GetEquippedWeapon(0)
	If !w
		Return ""
	EndIf
	Return w.GetName()
EndFunction

Bool Function PlayerHasBlade()
	If !PlayerRef
		Return False
	EndIf
	If OwnedPickmansBlade
		Return True
	EndIf
	If PlayerOwnsPickmansBladeInstance()
		OwnedPickmansBlade = True
		Return True
	EndIf
	If HasTemplateBlade()
		Return True
	EndIf
	If IsBladeEquipped()
		Return True
	EndIf
	Return False
EndFunction

Bool Function WeaponIsRanged(Weapon w)
	If !w
		Return False
	EndIf
	Ammo a = w.GetAmmo()
	Return a != None
EndFunction

; Only the active hand from GetEquippedWeapon(0) — do NOT scan GoE (guns in inv can look "equipped").
Bool Function ActiveWeaponIsRanged()
	If !PlayerRef
		Return False
	EndIf
	Return WeaponIsRanged(PlayerRef.GetEquippedWeapon(0))
EndFunction

; Recompute drawn state via GoE (authoritative for legendary instance name/mods).
Bool Function ResyncDrawnBladeState()
	If !PlayerRef
		BladeCurrentlyDrawn = False
		DrawnWeaponStateValid = False
		Return False
	EndIf
	ResolveVanillaForms()
	Weapon w = PlayerRef.GetEquippedWeapon(0)
	If WeaponIsRanged(w)
		BladeCurrentlyDrawn = False
		DrawnWeaponStateValid = True
		Return False
	EndIf
	Int idx = FindEquippedPickmansBladeIndex()
	If idx >= 0
		BladeCurrentlyDrawn = True
		DrawnWeaponStateValid = True
		OwnedPickmansBlade = True
		If w
			RuntimeBladeForm = w
		ElseIf CombatKnifeBase
			RuntimeBladeForm = CombatKnifeBase
		EndIf
		Return True
	EndIf
	BladeCurrentlyDrawn = False
	DrawnWeaponStateValid = True
	Return False
EndFunction

Bool Function IsBladeEquipped()
	; Drawn Pickman's only — GoE instance scan; never LVLI template / inventory count alone.
	If !PlayerRef
		Return False
	EndIf
	Weapon w = PlayerRef.GetEquippedWeapon(0)
	If WeaponIsRanged(w)
		BladeCurrentlyDrawn = False
		DrawnWeaponStateValid = True
		Return False
	EndIf
	; Always prefer live GoE scan (handles load + Combat Knife base name)
	Int idx = FindEquippedPickmansBladeIndex()
	If idx >= 0
		BladeCurrentlyDrawn = True
		DrawnWeaponStateValid = True
		OwnedPickmansBlade = True
		Return True
	EndIf
	BladeCurrentlyDrawn = False
	DrawnWeaponStateValid = True
	Return False
EndFunction

; Alias for kill checks — no sheath / empty-hand grace. Gun or fists = not ready.
Bool Function IsBladeKillWeaponReady()
	Return IsBladeEquipped()
EndFunction

String Function GetDrawnWeaponDebugName()
	If !PlayerRef
		Return "(no player)"
	EndIf
	Int idx = FindEquippedPickmansBladeIndex()
	If idx >= 0
		Return "PICKMANS=" + GardenOfEden.GetNthItemName(PlayerRef, idx)
	EndIf
	String latch = "latch=?"
	If DrawnWeaponStateValid
		If BladeCurrentlyDrawn
			latch = "latch=BLADE"
		Else
			latch = "latch=no"
		EndIf
	EndIf
	Weapon w = PlayerRef.GetEquippedWeapon(0)
	If WeaponIsRanged(w)
		String rn = "(ranged)"
		If w
			rn = w.GetName()
			If rn == ""
				rn = "(ranged id=" + w.GetFormID() + ")"
			EndIf
		EndIf
		Return latch + " GUN=" + rn
	EndIf
	If !w
		Return latch + " (none/fists)"
	EndIf
	String n = w.GetName()
	If n == ""
		Return latch + " (unnamed id=" + w.GetFormID() + ")"
	EndIf
	Return latch + " " + n
EndFunction

; Debug kill/scan toasts — MCM "Kill debug toasts" (default OFF). Gameplay voice stays separate.
Function InvalidateDebugToastCache()
	DebugKillToastsCacheValid = False
EndFunction

Bool Function IsKillDebugToastsEnabled()
	If DebugKillToastsCacheValid
		Return DebugKillToastsCached
	EndIf
	Bool on = False
	If MCM.IsInstalled()
		on = MCM.GetModSettingBool(MOD_NAME, "bKillDebugToasts:Debug")
	EndIf
	DebugKillToastsCached = on
	DebugKillToastsCacheValid = True
	Return on
EndFunction

Function ToastDebug(String msg)
	Debug.Trace("PickmansWhisper: " + msg)
	If IsKillDebugToastsEnabled()
		Debug.Notification(msg)
	EndIf
EndFunction

; Blade status toast (load/scene) — debug only
Function ToastBladeDetectStatus(String context)
	Bool owned = OwnedPickmansBlade || HasTemplateBlade() || PlayerHasBlade()
	Bool equipped = IsBladeEquipped()
	String msg = "PW debug [" + DEBUG_BUILD + "] (" + context + "): blade "
	If equipped
		msg += "EQUIPPED"
	ElseIf owned
		msg += "owned, not equipped"
	Else
		msg += "NOT detected"
	EndIf
	ToastDebug(msg)
	; Blade toasts prove bond poll / load is alive — force-arm kill scan there
	StartKillScanLoop()
	AnnounceKillScanArmed()
EndFunction

Function StartBond(String reason)
	If BondStarted
		Return
	EndIf
	BondStarted = True
	Float now = Utility.GetCurrentGameTime()
	BondStartGameTime = now
	If LastKnifeActivityGameTime <= 0.0
		LastKnifeActivityGameTime = now
	EndIf
	LastHungerPollGameTime = now
	Debug.Trace("PickmansWhisper: bond started (" + reason + ")")
	If !IntroToastShown
		IntroToastShown = True
		String line = PickTrustLine()
		If line == ""
			line = "Something in the gallery leans closer... glad you came."
		EndIf
		ToastVoice(line)
	EndIf
	RefreshHungerPanel(False)
	If !RefreshDebugBusy
		RefreshDebugStatus()
	EndIf
EndFunction

; --- Trust voice ---------------------------------------------------------------

Function StartTrustVoice()
	CancelTimer(TIMER_TRUST)
	If !IsVoiceEnabled()
		Return
	EndIf
	StartTimer(TRUST_VOICE_SECONDS, TIMER_TRUST)
EndFunction

Function MaybeSpeakTrustLine()
	If !BondStarted || !IsVoiceEnabled()
		Return
	EndIf
	If Utility.IsInMenuMode()
		Return
	EndIf
	If !PlayerHasBlade() && !IsBladeEquipped() && !IsPlayerInGallery()
		Return
	EndIf
	Float now = Utility.GetCurrentRealTime()
	If (now - LastTrustToastRealTime) < TRUST_TOAST_COOLDOWN
		Return
	EndIf
	String line = PickTrustLine()
	If line != ""
		ToastVoice(line)
	EndIf
EndFunction

Function ToastVoice(String line)
	If line == "" || !IsVoiceEnabled()
		Return
	EndIf
	If Utility.IsInMenuMode()
		Return
	EndIf
	LastTrustToastRealTime = Utility.GetCurrentRealTime()
	Debug.Notification(line)
	Debug.Trace("PickmansWhisper: voice | " + line)
EndFunction

Function ToastHungerLine(String line)
	If line == "" || !IsVoiceEnabled()
		Return
	EndIf
	If Utility.IsInMenuMode()
		Return
	EndIf
	Float now = Utility.GetCurrentRealTime()
	If (now - LastHungerToastRealTime) < HUNGER_TOAST_COOLDOWN
		Return
	EndIf
	LastHungerToastRealTime = now
	Debug.Notification(line)
	Debug.Trace("PickmansWhisper: hunger voice | " + line)
EndFunction

; --- Line banks ----------------------------------------------------------------

Function LoadLineBanks()
	LoadTrustLines()
	LoadHungerLines()
	LoadPraiseLines()
EndFunction

Function LoadTrustLines()
	; Builtin banks (config .txt ships for editing; GoE disk reload later).
	UseBuiltinTrustFallback()
	Debug.Trace("PickmansWhisper: trust lines ready (" + TrustLineCount + ")")
EndFunction

Function LoadHungerLines()
	UseBuiltinHungerFallback()
	Debug.Trace("PickmansWhisper: hunger lines ready (" + HungerLineCount + ")")
EndFunction

Function LoadPraiseLines()
	UseBuiltinPraiseFallback()
	Debug.Trace("PickmansWhisper: praise lines ready (" + PraiseLineCount + ")")
EndFunction

Function UseBuiltinTrustFallback()
	TrustLines = new String[LINE_FILE_MAX]
	TrustLines[0] = "You hear me. Good. Stay a while."
	TrustLines[1] = "I like the way you hold still in these halls."
	TrustLines[2] = "We're getting along already... aren't we?"
	TrustLines[3] = "Keep the knife close. It likes you."
	TrustLines[4] = "No need to rush. I'm not going anywhere."
	TrustLines[5] = "The paint chips look like smiles up close."
	TrustLines[6] = "You came seeking a gift. You found a friend."
	TrustLines[7] = "Quiet steps. Careful hands. Perfect."
	TrustLineCount = 8
EndFunction

Function UseBuiltinHungerFallback()
	HungerLines = new String[LINE_FILE_MAX]
	HungerLines[0] = "A restless edge... the blade wants use."
	HungerLines[1] = "Hunger grows while the knife sleeps."
	HungerLines[2] = "You feel it — that neat, bright need."
	HungerLines[3] = "Feed me. Just once. You'll see."
	HungerLines[4] = "The itching behind your eyes is for someone soft and still."
	HungerLines[5] = "Unused steel turns mean. You know how to fix that."
	HungerLines[6] = "They won't understand. We will."
	HungerLineCount = 7
EndFunction

Function UseBuiltinPraiseFallback()
	PraiseLines = new String[LINE_FILE_MAX]
	PraiseLines[0] = "Yes... that was beautiful. Rest a moment."
	PraiseLines[1] = "Perfect. Clean. The blade is smiling."
	PraiseLines[2] = "You felt that, didn't you? So did I."
	PraiseLines[3] = "Again when you're ready. I'll wait."
	PraiseLines[4] = "Good. They hardly knew how to thank you."
	PraiseLines[5] = "Quiet work. Elegant. Keep going."
	PraiseLines[6] = "I knew you'd understand us."
	PraiseLines[7] = "Hunger sleeps. For a little while."
	PraiseLineCount = 8
EndFunction

String Function PickTrustLine()
	If TrustLineCount <= 0 || !TrustLines
		LoadTrustLines()
	EndIf
	If TrustLineCount <= 0
		Return "You hear me. Good."
	EndIf
	Return TrustLines[Utility.RandomInt(0, TrustLineCount - 1)]
EndFunction

String Function PickHungerLine()
	If HungerLineCount <= 0 || !HungerLines
		LoadHungerLines()
	EndIf
	If HungerLineCount <= 0
		Return "The blade is hungry."
	EndIf
	Return HungerLines[Utility.RandomInt(0, HungerLineCount - 1)]
EndFunction

String Function PickPraiseLine()
	If PraiseLineCount <= 0 || !PraiseLines
		LoadPraiseLines()
	EndIf
	If PraiseLineCount <= 0
		Return "Yes... that was beautiful. Rest a moment."
	EndIf
	Return PraiseLines[Utility.RandomInt(0, PraiseLineCount - 1)]
EndFunction

Function ToastPraiseLine(String line)
	If line == "" || !IsVoiceEnabled()
		Return
	EndIf
	Float now = Utility.GetCurrentRealTime()
	If (now - LastPraiseToastRealTime) < PRAISE_TOAST_COOLDOWN
		Return
	EndIf
	LastPraiseToastRealTime = now
	; Praise may fire mid-combat; allow even if menus briefly steal focus
	Debug.Notification(line)
	Debug.Trace("PickmansWhisper: praise | " + line)
EndFunction

; --- Hunger --------------------------------------------------------------------

Function StartHungerPoll()
	EnsureHungerSpell()
	If LastHungerPollGameTime <= 0.0
		LastHungerPollGameTime = Utility.GetCurrentGameTime()
	EndIf
	CancelTimer(TIMER_HUNGER)
	StartTimer(HUNGER_POLL_SECONDS, TIMER_HUNGER)
	SyncHungerAddictionSpell()
	RefreshHungerPanel(False)
EndFunction

Function EnsureHungerSpell()
	If KnifeHungerSpell && KnifeHungerAgiEffect && KnifeHungerGlobal
		Return
	EndIf
	If !KnifeHungerSpell
		Form f = Game.GetFormFromFile(FID_HUNGER_SPEL, "PickmansWhisper.esp")
		KnifeHungerSpell = f as Spell
		If KnifeHungerSpell
			Debug.Trace("PickmansWhisper: Knife Hunger SPEL loaded")
		ElseIf !HungerSpellLoadWarned
			HungerSpellLoadWarned = True
			Debug.Trace("PickmansWhisper: ERROR Knife Hunger SPEL missing — rebuild ESP")
			Debug.Notification("Pickman's Whisper: Knife Hunger spell missing (update ESP)")
		EndIf
	EndIf
	If !KnifeHungerGlobal
		KnifeHungerGlobal = Game.GetFormFromFile(FID_HUNGER_GLOB, "PickmansWhisper.esp") as GlobalVariable
	EndIf
	If !KnifeHungerAgiEffect
		KnifeHungerAgiEffect = Game.GetFormFromFile(FID_HUNGER_MGEF_AGI, "PickmansWhisper.esp") as MagicEffect
	EndIf
	If !KnifeHungerChaEffect
		KnifeHungerChaEffect = Game.GetFormFromFile(FID_HUNGER_MGEF_CHA, "PickmansWhisper.esp") as MagicEffect
	EndIf
EndFunction

Bool Function IsHungerUnlocked()
	Return BondStarted
EndFunction

Bool Function IsHungerAddictionSpellEnabled()
	If MCM.IsInstalled()
		Return MCM.GetModSettingBool(MOD_NAME, "bAddictionSpell:Hunger")
	EndIf
	Return True
EndFunction

Bool Function IsVoiceEnabled()
	If MCM.IsInstalled()
		Return MCM.GetModSettingBool(MOD_NAME, "bVoiceToasts:Voice")
	EndIf
	Return True
EndFunction

Float Function GetHungerTimeGainPerHour()
	Float v = 5.0
	If MCM.IsInstalled()
		v = MCM.GetModSettingFloat(MOD_NAME, "fTimeGain:Hunger")
	EndIf
	If v < 0.0
		v = 0.0
	EndIf
	Return v
EndFunction

Float Function GetHungerAddictedThreshold()
	Float v = 70.0
	If MCM.IsInstalled()
		v = MCM.GetModSettingFloat(MOD_NAME, "fAddictedAt:Hunger")
	EndIf
	If v < 1.0
		v = 70.0
	EndIf
	Return v
EndFunction

Float Function GetHungerSatedHours()
	Float v = 2.0
	If MCM.IsInstalled()
		v = MCM.GetModSettingFloat(MOD_NAME, "fSatedHours:Hunger")
	EndIf
	If v < 0.5
		v = 0.5
	EndIf
	Return v
EndFunction

Bool Function IsHungerSated()
	Float now = Utility.GetCurrentGameTime()
	Return SatedUntilGameTime > 0.0 && now < SatedUntilGameTime
EndFunction

String Function GetHungerBandLabel(Float level)
	If level >= 90.0
		Return "desperate"
	ElseIf level >= 70.0
		Return "starving"
	ElseIf level >= 50.0
		Return "hungry"
	ElseIf level >= 25.0
		Return "restless"
	EndIf
	Return "calm"
EndFunction

Function RunHungerTick()
	If !IsHungerUnlocked()
		LastHungerPollGameTime = Utility.GetCurrentGameTime()
		HungerWasSated = False
		SyncHungerAddictionSpell()
		Return
	EndIf
	If Utility.IsInMenuMode()
		Return
	EndIf

	Float now = Utility.GetCurrentGameTime()
	If LastHungerPollGameTime <= 0.0
		LastHungerPollGameTime = now
	EndIf
	Float last = LastHungerPollGameTime

	Bool satedNow = IsHungerSated()
	If HungerWasSated && !satedNow
		ToastHungerLine("The quiet ends. The knife remembers.")
		ApplyHungerDelta(20.0, "withdrawal-onset")
	EndIf

	If !satedNow
		; Unused knife-time: blade owned (or bond active) without recent activity.
		; Slice A treats LastKnifeActivityGameTime as bond start until B updates it.
		Float gainStart = last
		If SatedUntilGameTime > gainStart
			If now > SatedUntilGameTime
				gainStart = SatedUntilGameTime
			Else
				gainStart = now
			EndIf
		EndIf
		Float hours = (now - gainStart) * 24.0
		If hours > 0.0
			ApplyHungerDelta(hours * GetHungerTimeGainPerHour(), "unused-knife-time")
		EndIf
	EndIf

	HungerWasSated = satedNow
	LastHungerPollGameTime = now
	SyncHungerAddictionSpell()
	RefreshHungerPanel(False)
EndFunction

Function ApplyHungerDelta(Float amount, String reason)
	If amount == 0.0
		Return
	EndIf
	Float before = HungerLevel
	HungerLevel = HungerLevel + amount
	If HungerLevel > 100.0
		HungerLevel = 100.0
	ElseIf HungerLevel < 0.0
		HungerLevel = 0.0
	EndIf
	Debug.Trace("PickmansWhisper: hunger " + before + " -> " + HungerLevel + " (" + reason + ")")
	MaybeToastHungerBand(before, HungerLevel)
	SyncHungerAddictionSpell()
EndFunction

Function MaybeToastHungerBand(Float before, Float after)
	Int band = 0
	If after >= 90.0
		band = 90
	ElseIf after >= 70.0
		band = 70
	ElseIf after >= 50.0
		band = 50
	ElseIf after >= 25.0
		band = 25
	EndIf
	If band > LastHungerBand
		LastHungerBand = band
		String line = PickHungerLine()
		If band == 25
			If line == ""
				line = "A restless edge... the blade wants use."
			EndIf
		ElseIf band == 50
			If line == ""
				line = "Hunger grows while the knife sleeps."
			EndIf
		ElseIf band == 70
			If line == ""
				line = "You feel it — that neat, bright need."
			EndIf
		ElseIf band == 90
			If line == ""
				line = "Feed me. Just once. You'll see."
			EndIf
		EndIf
		ToastHungerLine(line)
	ElseIf after < 25.0 && LastHungerBand > 0
		LastHungerBand = 0
	EndIf
EndFunction

; --- Knife kills (Slice B) -----------------------------------------------------
; GoE FindActors + IsDead() like Necromantic. Driven by bond poll (proven) + StartTimer(13).

String Function EnsureCombatKillHooks()
	If !PlayerRef
		PlayerRef = Game.GetPlayer()
	EndIf
	EnsureKillWatchList()
	EnsureAliveSeenList()
	StartKillScanLoop()
	String status = "scan BOND+T13 living=" + KillWatchCount
	ToastDebug("PW [" + DEBUG_BUILD + "]: " + status)
	Debug.Trace("PickmansWhisper: EnsureCombatKillHooks " + DEBUG_BUILD + " " + status)
	AnnounceKillScanArmed()
	Return status
EndFunction

Function AnnounceKillScanArmed()
	If KillScanArmAnnounced
		Return
	EndIf
	KillScanArmAnnounced = True
	If IsKillDebugToastsEnabled()
		Debug.MessageBox("Pickman's Whisper [" + DEBUG_BUILD + "]\n\nKill scan armed.\nHeartbeat: PW scan #N near=…")
	EndIf
	Debug.Trace("PickmansWhisper: kill scan armed " + DEBUG_BUILD)
EndFunction

Function StartKillScanLoop()
	; Necromantic uses StartTimer for craving — same approach, id 13
	CancelTimer(TIMER_KILL_SCAN)
	StartTimer(KILL_SCAN_SECONDS, TIMER_KILL_SCAN)
EndFunction

Function RunKillScanTick()
	If !PlayerRef
		PlayerRef = Game.GetPlayer()
	EndIf
	If !PlayerRef
		Return
	EndIf

	AnnounceKillScanArmed()

	Actor ct = PlayerRef.GetCombatTarget()
	If ct && !ct.IsDead() && IsBladeEquipped()
		TrackLivingNear(ct)
	EndIf

	ScanLivingToDeadTransitions()

	KillScanTickCount += 1
	If KillScanTickCount == 1 || (KillScanTickCount % 3) == 0
		String bladeBit = "blade=NO"
		If IsBladeEquipped()
			bladeBit = "blade=YES"
		EndIf
		ToastDebug("PW scan [" + DEBUG_BUILD + "] #" + KillScanTickCount + " near=" + KillWatchCount + " goeA=" + LastGoeAliveCount + " goeD=" + LastGoeDeadCount + " det=" + LastDetectCount + " " + bladeBit)
	EndIf
EndFunction

Function ScanLivingToDeadTransitions()
	If !PlayerRef
		Return
	EndIf

	Bool bladeReady = IsBladeKillWeaponReady()

	; --- Living sources -------------------------------------------------------
	; GoE: lifeState 0=dead (Necromantic). 1=alive. selectiveProcessMode 0 = broad.
	Actor[] alive = GardenOfEden.FindActors(None, None, -1, -1, PlayerRef, KILL_WATCH_RADIUS, 1, -1, -1, -1, -1, -1, None, None, "", 0, 1, 0)
	LastGoeAliveCount = 0
	If alive
		LastGoeAliveCount = alive.Length
	EndIf

	; NPCs that currently detect the player (works in combat; may miss total stealth)
	Actor[] detecting = GardenOfEden2.GetActorsDetecting(PlayerRef, False)
	LastDetectCount = 0
	If detecting
		LastDetectCount = detecting.Length
	EndIf

	; --- Dead source (exact Necromantic craving / target filter, no sex filter) -
	Actor[] dead = GardenOfEden.FindActors(None, None, -1, -1, PlayerRef, KILL_CORPSE_RADIUS, 0, 1, -1, -1, -1, -1, None, None, "", 0, 1, 1)
	LastGoeDeadCount = 0
	If dead
		LastGoeDeadCount = dead.Length
	EndIf

	Int i = 0
	Int n = LastGoeAliveCount
	If n > 24
		n = 24
	EndIf
	; Stamp living links always; satiation still requires IsBladeEquipped at kill time.
	While i < n
		Actor ak = alive[i]
		If ak && ak != PlayerRef && !ak.IsDead() && !ak.IsDisabled()
			TrackLivingNear(ak)
		EndIf
		i += 1
	EndWhile

	i = 0
	n = LastDetectCount
	If n > 24
		n = 24
	EndIf
	While i < n
		Actor ak = detecting[i]
		If ak && ak != PlayerRef && !ak.IsDead() && !ak.IsDisabled()
			TrackLivingNear(ak)
		EndIf
		i += 1
	EndWhile

	; Tracked living → dead (only evaluate satiation if blade is the kill weapon)
	EnsureKillWatchList()
	i = 0
	While i < KillWatchCount
		Actor ak = KillWatchList[i]
		If !ak
			RemoveKillWatchAt(i)
		ElseIf ak.IsDead()
			ToastHumanKillDetected(ak, "live-dead")
			HandlePotentialKnifeKill(ak, PlayerRef)
			RemoveKillWatchAt(i)
		ElseIf !ak.Is3DLoaded() || PlayerRef.GetDistance(ak) > KILL_WATCH_RADIUS
			RemoveKillWatchAt(i)
		Else
			i += 1
		EndIf
	EndWhile

	; Necromantic-style corpse pass + "new corpse while blade equipped"
	i = 0
	n = LastGoeDeadCount
	If n > 16
		n = 16
	EndIf
	While i < n
		Actor ak = dead[i]
		If ak && ak != PlayerRef && ak.IsDead() && ak.Is3DLoaded() && !ak.IsDisabled()
			Int id = ak.GetFormID()
			If WasAliveSeen(ak) || IsInKillWatchList(ak) || (ak == PendingKillVictim)
				ToastHumanKillDetected(ak, "dead-scan")
				HandlePotentialKnifeKill(ak, PlayerRef)
				NoteBackgroundDead(id)
			ElseIf !IsBackgroundDead(id)
				If KillScanTickCount <= 2 || !bladeReady
					; Warm-up / other weapon: remember existing corpses so they don't false-sate
					NoteBackgroundDead(id)
				ElseIf WasFriendlySeen(ak)
					; New corpse of someone we already marked non-hostile while living
					NoteAliveSeen(ak)
					ToastHumanKillDetected(ak, "new-corpse")
					HandlePotentialKnifeKill(ak, PlayerRef)
					NoteBackgroundDead(id)
				Else
					NoteBackgroundDead(id)
				EndIf
			EndIf
		EndIf
		i += 1
	EndWhile
EndFunction

Function EnsureBackgroundDeadList()
	If !BackgroundDeadIds || BackgroundDeadIds.Length == 0
		BackgroundDeadIds = new Int[48]
		BackgroundDeadCount = 0
	EndIf
EndFunction

Bool Function IsBackgroundDead(Int id)
	If id == 0
		Return False
	EndIf
	EnsureBackgroundDeadList()
	Int i = 0
	While i < BackgroundDeadCount
		If BackgroundDeadIds[i] == id
			Return True
		EndIf
		i += 1
	EndWhile
	Return False
EndFunction

Function NoteBackgroundDead(Int id)
	If id == 0 || IsBackgroundDead(id)
		Return
	EndIf
	EnsureBackgroundDeadList()
	If BackgroundDeadCount >= BACKGROUND_DEAD_MAX
		Int j = 0
		While j < BACKGROUND_DEAD_MAX - 1
			BackgroundDeadIds[j] = BackgroundDeadIds[j + 1]
			j += 1
		EndWhile
		BackgroundDeadCount = BACKGROUND_DEAD_MAX - 1
	EndIf
	BackgroundDeadIds[BackgroundDeadCount] = id
	BackgroundDeadCount += 1
EndFunction

Function RemoveKillWatchAt(Int index)
	EnsureKillWatchList()
	If index < 0 || index >= KillWatchCount
		Return
	EndIf
	Actor gone = KillWatchList[index]
	If gone
		RemoveAliveSeenId(gone.GetFormID())
	EndIf
	Int j = index
	While j < KillWatchCount - 1
		KillWatchList[j] = KillWatchList[j + 1]
		j += 1
	EndWhile
	KillWatchList[KillWatchCount - 1] = None
	KillWatchCount -= 1
EndFunction

; Drop active watch when switching to a non-blade weapon. Keep AliveSeen / FriendlySeen.
Function ClearKillWatchForWeaponSwap()
	PendingKillVictim = None
	KillWatchCount = 0
	If KillWatchList
		Int i = 0
		While i < KillWatchList.Length
			KillWatchList[i] = None
			i += 1
		EndWhile
	EndIf
	BladeTaggedCount = 0
EndFunction

Function RemoveAliveSeenId(Int id)
	If id == 0 || !AliveSeenIds
		Return
	EndIf
	Int i = 0
	While i < AliveSeenCount
		If AliveSeenIds[i] == id
			Int j = i
			While j < AliveSeenCount - 1
				AliveSeenIds[j] = AliveSeenIds[j + 1]
				j += 1
			EndWhile
			AliveSeenCount -= 1
			Return
		EndIf
		i += 1
	EndWhile
EndFunction

Function TrackLivingNear(Actor ak)
	; Track loosely — validity (sex / hostility / essential) enforced at kill time.
	If !ak || ak == PlayerRef || ak.IsDead() || ak.IsDisabled()
		Return
	EndIf
	If ak.IsChild()
		Return
	EndIf
	NoteAliveSeen(ak)
	; Stamp disposition while still living — before the player turns a settler hostile.
	If PlayerRef && ak.IsHostileToActor(PlayerRef)
		; Hostile when first/ongoing seen — do not mark friendly
	Else
		NoteFriendlySeen(ak)
	EndIf
	If IsInKillWatchList(ak)
		Return
	EndIf
	EnsureKillWatchList()
	If KillWatchCount >= KILL_WATCH_MAX
		RemoveKillWatchAt(0)
	EndIf
	KillWatchList[KillWatchCount] = ak
	KillWatchCount += 1
	Debug.Trace("PickmansWhisper: track living id=" + ak.GetFormID() + " n=" + KillWatchCount)
EndFunction

Function EnsureFriendlySeenList()
	If !FriendlySeenIds || FriendlySeenIds.Length == 0
		FriendlySeenIds = new Int[32]
		FriendlySeenCount = 0
	EndIf
EndFunction

Function NoteFriendlySeen(Actor ak)
	If !ak
		Return
	EndIf
	EnsureFriendlySeenList()
	Int id = ak.GetFormID()
	Int i = 0
	While i < FriendlySeenCount
		If FriendlySeenIds[i] == id
			Return
		EndIf
		i += 1
	EndWhile
	If FriendlySeenCount >= FRIENDLY_SEEN_MAX
		Int j = 0
		While j < FRIENDLY_SEEN_MAX - 1
			FriendlySeenIds[j] = FriendlySeenIds[j + 1]
			j += 1
		EndWhile
		FriendlySeenCount = FRIENDLY_SEEN_MAX - 1
	EndIf
	FriendlySeenIds[FriendlySeenCount] = id
	FriendlySeenCount += 1
EndFunction

Bool Function WasFriendlySeen(Actor ak)
	If !ak
		Return False
	EndIf
	EnsureFriendlySeenList()
	Int id = ak.GetFormID()
	Int i = 0
	While i < FriendlySeenCount
		If FriendlySeenIds[i] == id
			Return True
		EndIf
		i += 1
	EndWhile
	Return False
EndFunction

Bool Function IsAdultFemale(Actor ak)
	If !ak
		Return False
	EndIf
	If ak.IsChild()
		Return False
	EndIf
	ActorBase base = ak.GetLeveledActorBase()
	If !base
		Return False
	EndIf
	; 0 = male, 1 = female (same as Necromantic)
	Return base.GetSex() == 1
EndFunction

Function ArmCombatTarget(Actor ak)
	TrackLivingNear(ak)
	If ak && !ak.IsDead()
		PendingKillVictim = ak
	EndIf
EndFunction

Function EnsureKillWatchList()
	If !KillWatchList || KillWatchList.Length == 0
		KillWatchList = new Actor[12]
		KillWatchCount = 0
	EndIf
EndFunction

Function EnsureBladeTaggedList()
	If !BladeTaggedIds || BladeTaggedIds.Length == 0
		BladeTaggedIds = new Int[24]
		BladeTaggedCount = 0
	EndIf
EndFunction

Function EnsureAliveSeenList()
	If !AliveSeenIds || AliveSeenIds.Length == 0
		AliveSeenIds = new Int[32]
		AliveSeenCount = 0
	EndIf
EndFunction

Function ClearAliveSeen()
	AliveSeenCount = 0
EndFunction

Function NoteAliveSeen(Actor ak)
	If !ak || ak.IsDead()
		Return
	EndIf
	EnsureAliveSeenList()
	Int id = ak.GetFormID()
	Int i = 0
	While i < AliveSeenCount
		If AliveSeenIds[i] == id
			Return
		EndIf
		i += 1
	EndWhile
	If AliveSeenCount >= ALIVE_SEEN_MAX
		Int j = 0
		While j < ALIVE_SEEN_MAX - 1
			AliveSeenIds[j] = AliveSeenIds[j + 1]
			j += 1
		EndWhile
		AliveSeenCount = ALIVE_SEEN_MAX - 1
	EndIf
	AliveSeenIds[AliveSeenCount] = id
	AliveSeenCount += 1
EndFunction

Bool Function WasAliveSeen(Actor ak)
	If !ak
		Return False
	EndIf
	EnsureAliveSeenList()
	Int id = ak.GetFormID()
	Int i = 0
	While i < AliveSeenCount
		If AliveSeenIds[i] == id
			Return True
		EndIf
		i += 1
	EndWhile
	Return False
EndFunction

Bool Function IsInKillWatchList(Actor ak)
	If !ak
		Return False
	EndIf
	EnsureKillWatchList()
	Int i = 0
	While i < KillWatchCount
		If KillWatchList[i] == ak
			Return True
		EndIf
		i += 1
	EndWhile
	Return False
EndFunction

Bool Function WasBladeTagged(Actor ak)
	If !ak
		Return False
	EndIf
	EnsureBladeTaggedList()
	Int id = ak.GetFormID()
	Int i = 0
	While i < BladeTaggedCount
		If BladeTaggedIds[i] == id
			Return True
		EndIf
		i += 1
	EndWhile
	Return False
EndFunction

Function TagBladeVictim(Actor ak)
	If !ak
		Return
	EndIf
	EnsureBladeTaggedList()
	Int id = ak.GetFormID()
	If WasBladeTagged(ak)
		Return
	EndIf
	If BladeTaggedCount >= BLADE_TAGGED_MAX
		Int j = 0
		While j < BLADE_TAGGED_MAX - 1
			BladeTaggedIds[j] = BladeTaggedIds[j + 1]
			j += 1
		EndWhile
		BladeTaggedCount = BLADE_TAGGED_MAX - 1
	EndIf
	BladeTaggedIds[BladeTaggedCount] = id
	BladeTaggedCount += 1
	RegisterForRemoteEvent(ak, "OnDeath")
	NoteAliveSeen(ak)
	LastKillIgnoreReason = "blade hit → tagged id=" + id
	ToastDebug("PW debug: blade HIT tagged id=" + id)
	Debug.Trace("PickmansWhisper: blade-tagged victim id=" + id)
EndFunction

Function OnPlayerCombatBegan(String path)
	; Soft backup — living scan is primary; do not clear the living track list.
	CombatGraceUntilRealTime = Utility.GetCurrentRealTime() + 10.0
	If PlayerRef
		Actor ctNow = PlayerRef.GetCombatTarget()
		If ctNow && IsBladeEquipped()
			TrackLivingNear(ctNow)
		EndIf
	EndIf
	Debug.Trace("PickmansWhisper: combat began path=" + path)
EndFunction

Function OnPlayerCombatEnded(String path)
	PollWatchedForDeath()
	Debug.Trace("PickmansWhisper: combat ended path=" + path + " livingTrack=" + KillWatchCount)
EndFunction

Function ReArmHitEventsOnWatched()
	EnsureKillWatchList()
	Int i = 0
	While i < KillWatchCount
		Actor ak = KillWatchList[i]
		If ak && !ak.IsDead()
			RegisterForHitEvent(ak, PlayerRef)
		EndIf
		i += 1
	EndWhile
EndFunction

Function ScanNearbyLivingCandidates()
	If !PlayerRef
		Return
	EndIf
	Actor[] found = GardenOfEden.FindActors(None, None, -1, -1, PlayerRef, KILL_WATCH_RADIUS, -1, 1, -1, -1, -1, -1, None, None, "", 0, 1, 1)
	If !found || found.Length == 0
		Actor[] detect = GardenOfEden2.GetActorsDetecting(PlayerRef, False)
		If detect && detect.Length > 0
			found = detect
		Else
			Return
		EndIf
	EndIf
	Int n = found.Length
	If n > 16
		n = 16
	EndIf
	Int i = 0
	While i < n
		Actor ak = found[i]
		If ak && ak != PlayerRef && !ak.IsDead()
			NoteAliveSeen(ak)
			WatchKillCandidate(ak, False)
		EndIf
		i += 1
	EndWhile
EndFunction

Function ScanNearbyDeadForKnifeKills(String path)
	If !PlayerRef
		Return
	EndIf
	; aiLifeState=0 → dead (Necromantic ScanCravingCorpses / FindNearestDeadFemale)
	Actor[] found = GardenOfEden.FindActors(None, None, -1, -1, PlayerRef, KILL_WATCH_RADIUS, 0, 1, -1, -1, -1, -1, None, None, "", 0, 1, 1)
	If !found || found.Length == 0
		Return
	EndIf
	Int n = found.Length
	If n > 16
		n = 16
	EndIf
	Bool combatGrace = Utility.GetCurrentRealTime() <= CombatGraceUntilRealTime
	Int i = 0
	While i < n
		Actor ak = found[i]
		If ak && ak != PlayerRef && ak.IsDead() && ak.Is3DLoaded() && !ak.IsDisabled()
			; Prefer people we saw alive / hit / watched. combatGrace allows short-fight misses.
			If WasAliveSeen(ak) || WasBladeTagged(ak) || IsInKillWatchList(ak) || (ak == PendingKillVictim) || combatGrace
				ToastHumanKillDetected(ak, path)
				HandlePotentialKnifeKill(ak, PlayerRef)
			EndIf
		EndIf
		i += 1
	EndWhile
EndFunction

Function PollWatchedForDeath()
	EnsureKillWatchList()
	Int i = 0
	While i < KillWatchCount
		Actor ak = KillWatchList[i]
		If ak && ak.IsDead()
			ToastHumanKillDetected(ak, "watch-poll")
			HandlePotentialKnifeKill(ak, PlayerRef)
			RemoveKillWatchAt(i)
		Else
			i += 1
		EndIf
	EndWhile
EndFunction

Function WatchKillCandidate(Actor ak, Bool abRequireValidFilter = True)
	If !ak || ak == PlayerRef
		Return
	EndIf
	If ak.IsDead()
		Return
	EndIf
	If abRequireValidFilter && !IsValidKnifeKillVictim(ak, True)
		Return
	EndIf
	NoteAliveSeen(ak)
	RegisterForHitEvent(ak, PlayerRef)
	If IsInKillWatchList(ak)
		Return
	EndIf
	EnsureKillWatchList()
	RegisterForRemoteEvent(ak, "OnDeath")
	If KillWatchCount >= KILL_WATCH_MAX
		Int j = 0
		While j < KILL_WATCH_MAX - 1
			KillWatchList[j] = KillWatchList[j + 1]
			j += 1
		EndWhile
		KillWatchCount = KILL_WATCH_MAX - 1
	EndIf
	KillWatchList[KillWatchCount] = ak
	KillWatchCount += 1
	Debug.Trace("PickmansWhisper: watching + hit-armed id=" + ak.GetFormID() + " watched=" + KillWatchCount)
EndFunction

Function HandleBladeHit(ObjectReference akTarget, ObjectReference akAggressor, Form akSource)
	Actor victim = akTarget as Actor
	Actor agg = akAggressor as Actor
	If !victim || agg != PlayerRef
		If victim && IsBladeEquipped()
			RegisterForHitEvent(victim, PlayerRef)
		EndIf
		Return
	EndIf
	Bool fromBlade = IsPickmansBladeForm(akSource) && IsBladeEquipped()
	If fromBlade
		NoteAliveSeen(victim)
		If victim.IsDead()
			TagBladeVictim(victim)
			ToastHumanKillDetected(victim, "hit-dead")
			HandlePotentialKnifeKill(victim, PlayerRef)
		Else
			TagBladeVictim(victim)
			WatchKillCandidate(victim, False)
		EndIf
	Else
		LastKillIgnoreReason = "hit not with blade; drawn=" + GetDrawnWeaponDebugName()
	EndIf
	If victim && !victim.IsDead() && IsBladeEquipped()
		RegisterForHitEvent(victim, PlayerRef)
	EndIf
EndFunction

Function ToastHumanKillDetected(Actor victim, String path)
	If !victim
		Return
	EndIf
	Int id = victim.GetFormID()
	If id == LastDeathToastId
		Return
	EndIf
	LastDeathToastId = id
	Bool human = IsHumanNpc(victim)
	If human
		ToastDebug("PW debug [" + DEBUG_BUILD + "]: HUMAN kill (" + path + ") id=" + id)
	Else
		ToastDebug("PW debug [" + DEBUG_BUILD + "]: non-human death (" + path + ") id=" + id)
	EndIf
	Debug.Trace("PickmansWhisper: death toast path=" + path + " human=" + human + " id=" + id)
EndFunction

Function EnsureFilterKeywords()
	; FormIDs verified against Fallout4.esm KYWD records.
	If !KW_ActorTypeNPC
		KW_ActorTypeNPC = Game.GetFormFromFile(0x00013794, "Fallout4.esm") as Keyword
	EndIf
	If !KW_ActorTypeHuman
		; 0x2CB72 is ActorTypeHuman — was wrongly used as Robot before (B18 and earlier).
		KW_ActorTypeHuman = Game.GetFormFromFile(0x0002CB72, "Fallout4.esm") as Keyword
	EndIf
	If !KW_ActorTypeGhoul
		KW_ActorTypeGhoul = Game.GetFormFromFile(0x000EAFB7, "Fallout4.esm") as Keyword
	EndIf
	If !KW_ActorTypeSuperMutant
		KW_ActorTypeSuperMutant = Game.GetFormFromFile(0x0006D7B6, "Fallout4.esm") as Keyword
	EndIf
	If !KW_ActorTypeSynth
		KW_ActorTypeSynth = Game.GetFormFromFile(0x0010C3CE, "Fallout4.esm") as Keyword
	EndIf
	If !KW_ActorTypeRobot
		KW_ActorTypeRobot = Game.GetFormFromFile(0x0002CB73, "Fallout4.esm") as Keyword
	EndIf
	If !KW_ActorTypeAnimal
		KW_ActorTypeAnimal = Game.GetFormFromFile(0x00013798, "Fallout4.esm") as Keyword
	EndIf
	If !KW_ActorTypeCreature
		KW_ActorTypeCreature = Game.GetFormFromFile(0x00013795, "Fallout4.esm") as Keyword
	EndIf
	If !KW_ActorTypeTurret
		KW_ActorTypeTurret = Game.GetFormFromFile(0x000B2BF3, "Fallout4.esm") as Keyword
	EndIf
EndFunction

Bool Function IsStoryEssential(Actor ak)
	If !ak
		Return True
	EndIf
	ActorBase base = ak.GetLeveledActorBase()
	If !base
		; Don't block knife kills if base is missing on a corpse
		Return False
	EndIf
	Return base.IsEssential()
EndFunction

Bool Function IsHumanNpc(Actor ak)
	If !ak
		Return False
	EndIf
	EnsureFilterKeywords()
	; Hard exclusions first
	If KW_ActorTypeGhoul && ak.HasKeyword(KW_ActorTypeGhoul)
		Return False
	EndIf
	If KW_ActorTypeSuperMutant && ak.HasKeyword(KW_ActorTypeSuperMutant)
		Return False
	EndIf
	If KW_ActorTypeSynth && ak.HasKeyword(KW_ActorTypeSynth)
		Return False
	EndIf
	If KW_ActorTypeRobot && ak.HasKeyword(KW_ActorTypeRobot)
		Return False
	EndIf
	If KW_ActorTypeAnimal && ak.HasKeyword(KW_ActorTypeAnimal)
		Return False
	EndIf
	If KW_ActorTypeCreature && ak.HasKeyword(KW_ActorTypeCreature)
		Return False
	EndIf
	If KW_ActorTypeTurret && ak.HasKeyword(KW_ActorTypeTurret)
		Return False
	EndIf
	; Positive: NPC or Human (settlers/raiders/etc.)
	If KW_ActorTypeNPC && ak.HasKeyword(KW_ActorTypeNPC)
		Return True
	EndIf
	If KW_ActorTypeHuman && ak.HasKeyword(KW_ActorTypeHuman)
		Return True
	EndIf
	; Soft accept if exclude keywords loaded but no positive match yet — still reject unknown animals
	Return False
EndFunction

Bool Function IsValidKnifeKillVictim(Actor ak, Bool abRequireAlive = True)
	If !ak || ak == PlayerRef
		LastKillIgnoreReason = "no actor"
		Return False
	EndIf
	If abRequireAlive && ak.IsDead()
		LastKillIgnoreReason = "already dead"
		Return False
	EndIf
	If ak.IsChild()
		LastKillIgnoreReason = "child"
		Return False
	EndIf
	If ak.IsPlayerTeammate()
		LastKillIgnoreReason = "teammate"
		Return False
	EndIf
	If IsStoryEssential(ak)
		LastKillIgnoreReason = "essential (story NPC)"
		Return False
	EndIf
	If !IsHumanNpc(ak)
		LastKillIgnoreReason = "not human NPC"
		Return False
	EndIf
	If !IsAdultFemale(ak)
		LastKillIgnoreReason = "not adult female"
		Return False
	EndIf
	; Must have been seen non-hostile while alive (raiders fail; settlers you aggro still pass).
	If !WasFriendlySeen(ak)
		LastKillIgnoreReason = "hostile / not seen friendly"
		Return False
	EndIf
	Return True
EndFunction

Function HandlePotentialKnifeKill(Actor victim, Actor akKiller)
	If !victim
		Return
	EndIf
	Int vid = victim.GetFormID()
	If vid == LastHandledKillId
		Return
	EndIf
	If akKiller && akKiller != PlayerRef
		LastKillIgnoreReason = "killer was not player"
		ToastDebug("PW debug: kill ignored — not player killer")
		Debug.Trace("PickmansWhisper: kill ignored — killer not player")
		Return
	EndIf
	; Drawn weapon must be Pickman's Blade right now. No finish window, no hit-tag waiver.
	String drawn = GetDrawnWeaponDebugName()
	If !IsBladeEquipped()
		LastKillIgnoreReason = "not blade; drawn=" + drawn
		ToastDebug("PW debug: kill ignored — " + LastKillIgnoreReason)
		Return
	EndIf
	Bool tagged = WasBladeTagged(victim)
	Bool seenAlive = IsInKillWatchList(victim) || (victim == PendingKillVictim) || WasAliveSeen(victim)
	If !tagged && !seenAlive
		LastKillIgnoreReason = "blade out but victim not linked; drawn=" + drawn
		ToastDebug("PW debug: kill ignored — " + LastKillIgnoreReason)
		Debug.Trace("PickmansWhisper: kill ignored — no blade-link id=" + vid)
		Return
	EndIf
	Float now = Utility.GetCurrentRealTime()
	If (now - LastKnifeKillRealTime) < KNIFE_KILL_COOLDOWN
		LastKillIgnoreReason = "cooldown"
		Return
	EndIf
	If !IsValidKnifeKillVictim(victim, False)
		ToastDebug("PW debug: kill ignored — " + LastKillIgnoreReason)
		Debug.Trace("PickmansWhisper: kill ignored — " + LastKillIgnoreReason + " id=" + vid)
		Return
	EndIf
	LastKnifeKillRealTime = now
	LastHandledKillId = vid
	LastKillIgnoreReason = "ok satiated; drawn=" + drawn
	If !BondStarted
		StartBond("knife-kill")
	EndIf
	ProcessKnifeKill(victim)
EndFunction

Function ProcessKnifeKill(Actor victim)
	; Final gate — never praise/sate unless blade is still the drawn weapon
	If !IsBladeEquipped()
		LastKillIgnoreReason = "abort satiate; drawn=" + GetDrawnWeaponDebugName()
		ToastDebug("PW debug: " + LastKillIgnoreReason)
		Return
	EndIf
	KnifeKillCount += 1
	NoteKnifeActivity()
	String line = PickPraiseLine()
	ToastPraiseLine(line)
	SatiateHunger()
	RefreshHungerPanel(False)
	RefreshDebugStatus()
	Int vid = 0
	If victim
		vid = victim.GetFormID()
	EndIf
	Debug.Trace("PickmansWhisper: knife kill #" + KnifeKillCount + " victim=" + vid + " hunger=0 drawn=" + GetDrawnWeaponDebugName())
	Debug.Notification("Pickman's Whisper: hunger sated")
EndFunction

; Call after a valid knife kill (or MCM debug). Clears meter + sated window.
Function SatiateHunger()
	Float now = Utility.GetCurrentGameTime()
	LastKnifeActivityGameTime = now
	LastHungerPollGameTime = now
	HungerLevel = 0.0
	LastHungerBand = 0
	SatedUntilGameTime = now + (GetHungerSatedHours() / 24.0)
	HungerWasSated = True
	BondIntensity = BondIntensity + 1.0
	SyncHungerAddictionSpell()
	RefreshHungerPanel(False)
	Debug.Trace("PickmansWhisper: hunger satiated until " + SatedUntilGameTime)
EndFunction

Function NoteKnifeActivity()
	LastKnifeActivityGameTime = Utility.GetCurrentGameTime()
	Debug.Trace("PickmansWhisper: knife activity noted")
EndFunction

String Function FormatSpecialSnapshot()
	If !PlayerRef
		Return "AGI=? CHA=?"
	EndIf
	ActorValue avAgi = Game.GetForm(0x000002C7) as ActorValue
	ActorValue avCha = Game.GetForm(0x000002C5) as ActorValue
	Float agi = -1.0
	Float cha = -1.0
	If avAgi
		agi = PlayerRef.GetValue(avAgi)
	EndIf
	If avCha
		cha = PlayerRef.GetValue(avCha)
	EndIf
	Return "AGI=" + (agi as Int) + " CHA=" + (cha as Int)
EndFunction

Function ApplyHungerStatPenalty()
	If !PlayerRef || HungerStatPenaltyApplied
		Return
	EndIf
	ActorValue avAgi = Game.GetForm(0x000002C7) as ActorValue
	ActorValue avCha = Game.GetForm(0x000002C5) as ActorValue
	If !avAgi
		avAgi = Game.GetFormFromFile(0x000002C7, "Fallout4.esm") as ActorValue
	EndIf
	If !avCha
		avCha = Game.GetFormFromFile(0x000002C5, "Fallout4.esm") as ActorValue
	EndIf
	If avAgi
		PlayerRef.ModValue(avAgi, -1.0)
	EndIf
	If avCha
		PlayerRef.ModValue(avCha, -1.0)
	EndIf
	HungerStatPenaltyApplied = True
	Debug.Trace("PickmansWhisper: SPECIAL -1 applied " + FormatSpecialSnapshot())
EndFunction

Function ClearHungerStatPenalty()
	If !PlayerRef || !HungerStatPenaltyApplied
		Return
	EndIf
	ActorValue avAgi = Game.GetForm(0x000002C7) as ActorValue
	ActorValue avCha = Game.GetForm(0x000002C5) as ActorValue
	If !avAgi
		avAgi = Game.GetFormFromFile(0x000002C7, "Fallout4.esm") as ActorValue
	EndIf
	If !avCha
		avCha = Game.GetFormFromFile(0x000002C5, "Fallout4.esm") as ActorValue
	EndIf
	If avAgi
		PlayerRef.ModValue(avAgi, 1.0)
	EndIf
	If avCha
		PlayerRef.ModValue(avCha, 1.0)
	EndIf
	HungerStatPenaltyApplied = False
	Debug.Trace("PickmansWhisper: SPECIAL +1 restored " + FormatSpecialSnapshot())
EndFunction

Bool Function ApplyHungerAddictionStandIn(Bool abAnnounce)
	If !PlayerRef
		Return False
	EndIf
	EnsureHungerSpell()
	If KnifeHungerSpell && PlayerRef.HasSpell(KnifeHungerSpell)
		PlayerRef.DispelSpell(KnifeHungerSpell)
		PlayerRef.RemoveSpell(KnifeHungerSpell)
	EndIf
	If KnifeHungerGlobal
		KnifeHungerGlobal.SetValue(0.0)
	EndIf
	If !HungerStatPenaltyApplied
		ApplyHungerStatPenalty()
	EndIf
	If HungerStatPenaltyApplied && abAnnounce
		Debug.Notification("Pickman's Whisper: knife hunger withdrawal AGI/CHA -1")
	EndIf
	Return HungerStatPenaltyApplied
EndFunction

Function ClearHungerAddictionStandIn()
	If !PlayerRef
		Return
	EndIf
	EnsureHungerSpell()
	If KnifeHungerSpell
		PlayerRef.DispelSpell(KnifeHungerSpell)
		If PlayerRef.HasSpell(KnifeHungerSpell)
			PlayerRef.RemoveSpell(KnifeHungerSpell)
		EndIf
	EndIf
	If KnifeHungerGlobal
		KnifeHungerGlobal.SetValue(0.0)
	EndIf
	ClearHungerStatPenalty()
EndFunction

Function SyncHungerAddictionSpell()
	EnsureHungerSpell()
	If !PlayerRef
		Return
	EndIf
	Bool want = IsHungerUnlocked() && IsHungerAddictionSpellEnabled() && HungerLevel >= GetHungerAddictedThreshold() && !IsHungerSated()
	If want
		If !HungerStatPenaltyApplied
			ApplyHungerAddictionStandIn(!HungerAddictionApplied)
		EndIf
		HungerAddictionApplied = HungerStatPenaltyApplied
	ElseIf HungerStatPenaltyApplied || HungerAddictionApplied
		ClearHungerAddictionStandIn()
		HungerAddictionApplied = False
		Debug.Trace("PickmansWhisper: hunger withdrawal cleared")
	EndIf
EndFunction

; --- MCM -----------------------------------------------------------------------

Function OnMCMMenuOpen(String modName)
	If modName != MOD_NAME
		Return
	EndIf
	RefreshHungerPanel(False)
	RefreshDebugStatus()
	If MCM.IsInstalled()
		MCM.RefreshMenu()
	EndIf
EndFunction

Function OnMCMSettingChange(String modName, String id)
	If modName != MOD_NAME
		Return
	EndIf
	If id == "bKillDebugToasts:Debug"
		InvalidateDebugToastCache()
	ElseIf id == "bAddictionSpell:Hunger" || id == "fAddictedAt:Hunger"
		SyncHungerAddictionSpell()
		RefreshHungerPanel(True)
	ElseIf id == "bVoiceToasts:Voice"
		StartTrustVoice()
	EndIf
EndFunction

Function RefreshHungerPanel(Bool refreshMenu = True)
	If !MCM.IsInstalled()
		Return
	EndIf
	If !IsHungerUnlocked()
		MCM.SetModSettingString(MOD_NAME, "sHungerLevel:Hunger", "locked (visit gallery or take the blade)")
		MCM.SetModSettingString(MOD_NAME, "sHungerSated:Hunger", "—")
		MCM.SetModSettingString(MOD_NAME, "sBondState:Hunger", "not bonded")
	Else
		Int lvl = HungerLevel as Int
		String band = GetHungerBandLabel(HungerLevel)
		MCM.SetModSettingString(MOD_NAME, "sHungerLevel:Hunger", lvl + " / 100 (" + band + ")")
		If IsHungerSated()
			Float left = (SatedUntilGameTime - Utility.GetCurrentGameTime()) * 24.0
			If left < 0.0
				left = 0.0
			EndIf
			MCM.SetModSettingString(MOD_NAME, "sHungerSated:Hunger", "yes (" + (left as Int) + "h left)")
		Else
			MCM.SetModSettingString(MOD_NAME, "sHungerSated:Hunger", "no — kill with Pickman's Blade")
		EndIf
		MCM.SetModSettingString(MOD_NAME, "sBondState:Hunger", "bonded | intensity " + (BondIntensity as Int) + " | kills " + KnifeKillCount)
	EndIf
	If refreshMenu
		MCM.RefreshMenu()
	EndIf
EndFunction

Function ShowHungerInfo()
	RefreshHungerPanel(True)
	String msg = "Pickman's Whisper — Hunger\n\n"
	If !IsHungerUnlocked()
		msg += "Not bonded yet.\nEnter Pickman Gallery or obtain Pickman's Blade.\n"
		Debug.MessageBox(msg)
		Return
	EndIf
	msg += "Level: " + (HungerLevel as Int) + " / 100 (" + GetHungerBandLabel(HungerLevel) + ")\n"
	If IsHungerSated()
		Float left = (SatedUntilGameTime - Utility.GetCurrentGameTime()) * 24.0
		msg += "Sated: yes (" + (left as Int) + "h left)\n"
	Else
		msg += "Sated: no\n"
	EndIf
	msg += "Bond intensity: " + (BondIntensity as Int) + "\n"
	msg += "Knife kills (sating): " + KnifeKillCount + "\n"
	msg += "Addicted at: " + (GetHungerAddictedThreshold() as Int) + "\n"
	msg += "Withdrawal flag: " + HungerStatPenaltyApplied + "\n"
	msg += "SPECIAL now: " + FormatSpecialSnapshot() + "\n"
	msg += "\nRises with unused knife-time after bonding.\n"
	msg += "Killing a non-essential human with Pickman's Blade sates hunger."
	Debug.MessageBox(msg)
EndFunction

Function ForceHungerAddictedTest()
	If !IsHungerUnlocked()
		Debug.MessageBox("Pickman's Whisper — Test\n\nBond first (gallery or blade).")
		Return
	EndIf
	If !IsHungerAddictionSpellEnabled()
		Debug.MessageBox("Pickman's Whisper — Test\n\nKnife Hunger effect is OFF in MCM.")
		Return
	EndIf
	If HungerStatPenaltyApplied
		ClearHungerAddictionStandIn()
	EndIf
	SatedUntilGameTime = 0.0
	HungerWasSated = False
	HungerLevel = 80.0
	LastHungerBand = 70
	HungerAddictionApplied = False
	String before = FormatSpecialSnapshot()
	SyncHungerAddictionSpell()
	RefreshHungerPanel(True)
	String msg = "Hunger forced to 80.\nBefore: " + before + "\nAfter: " + FormatSpecialSnapshot() + "\n"
	msg += "Withdrawal flag: " + HungerStatPenaltyApplied
	Debug.MessageBox("Pickman's Whisper — Test\n\n" + msg)
EndFunction

Function DebugForceBond()
	StartBond("mcm-debug")
	RefreshDebugStatus()
	Debug.MessageBox("Pickman's Whisper\n\nBond forced. Hunger unlocked.")
EndFunction

Function DebugSatiateHunger()
	If !IsHungerUnlocked()
		Debug.MessageBox("Pickman's Whisper\n\nBond first.")
		Return
	EndIf
	String line = PickPraiseLine()
	ToastPraiseLine(line)
	SatiateHunger()
	RefreshHungerPanel(True)
	Debug.MessageBox("Pickman's Whisper\n\nHunger satiated (debug — no kill required).\n" + line)
EndFunction

Function DebugReloadLines()
	LoadLineBanks()
	Debug.MessageBox("Pickman's Whisper\n\nReloaded line banks.\nTrust: " + TrustLineCount + "\nHunger: " + HungerLineCount + "\nPraise: " + PraiseLineCount)
EndFunction

Function DebugTestPraiseLine()
	String line = PickPraiseLine()
	ToastPraiseLine(line)
	If Utility.IsInMenuMode()
		Debug.MessageBox("Pickman's Whisper\n\n" + line)
	EndIf
EndFunction

Function DebugTestTrustLine()
	String line = PickTrustLine()
	ToastVoice(line)
	If Utility.IsInMenuMode()
		Debug.MessageBox("Pickman's Whisper\n\n" + line)
	EndIf
EndFunction

Function RefreshDebugStatus()
	; Side-effect-free read of status for MCM. Must NOT StartBond / nest CallFunction.
	If RefreshDebugBusy
		Return
	EndIf
	RefreshDebugBusy = True

	If !PlayerRef
		PlayerRef = Game.GetPlayer()
	EndIf

	If !MCM.IsInstalled()
		RefreshDebugBusy = False
		ToastDebug("PW debug refresh: MCM missing")
		Return
	EndIf
	InvalidateDebugToastCache()

	Bool allOk = True
	Int f4seRel = F4SE.GetVersionRelease()
	If f4seRel > 0
		MCM.SetModSettingString(MOD_NAME, "sF4SE:Debug", "OK (release " + f4seRel + ")")
	Else
		MCM.SetModSettingString(MOD_NAME, "sF4SE:Debug", "MISSING")
		allOk = False
	EndIf
	MCM.SetModSettingString(MOD_NAME, "sMCM:Debug", "OK")

	ResolveVanillaForms()
	; Do NOT call RefreshBladeOwnershipFromEquip here — it can StartBond and nest MCM calls
	; (closes MCM / soft-crashes CallFunction). Ownership is updated by equip events.
	If PickmansBlade
		MCM.SetModSettingString(MOD_NAME, "sBlade:Debug", "OK template loaded")
	Else
		MCM.SetModSettingString(MOD_NAME, "sBlade:Debug", "MISSING template")
		allOk = False
	EndIf
	String eqName = GetEquippedWeaponName()
	If eqName == ""
		eqName = "(none)"
	EndIf
	Weapon eqW = None
	If PlayerRef
		eqW = PlayerRef.GetEquippedWeapon(0)
	EndIf
	String eqId = "(no weap)"
	If eqW
		eqId = GardenOfEden.GetHexFormID(eqW)
	EndIf
	If PlayerHasBlade()
		String how = ""
		If OwnedPickmansBlade
			how = "owned(name)"
		EndIf
		If HasTemplateBlade()
			If how != ""
				how = how + "+"
			EndIf
			how = how + "template"
		EndIf
		If how == ""
			how = "yes"
		EndIf
		MCM.SetModSettingString(MOD_NAME, "sBladeInv:Debug", how)
	Else
		MCM.SetModSettingString(MOD_NAME, "sBladeInv:Debug", "not owned | eq=" + eqName)
	EndIf
	If IsBladeEquipped()
		Int idx = FindEquippedPickmansBladeIndex()
		String goeName = eqName
		If idx >= 0
			goeName = GardenOfEden.GetNthItemName(PlayerRef, idx)
		EndIf
		MCM.SetModSettingString(MOD_NAME, "sBladeEq:Debug", "DRAWN | " + goeName + " / base=" + eqName + " " + eqId)
	Else
		MCM.SetModSettingString(MOD_NAME, "sBladeEq:Debug", "not drawn | base=" + eqName + " " + eqId)
	EndIf
	If IsPlayerInGallery()
		MCM.SetModSettingString(MOD_NAME, "sCell:Debug", "Pickman Gallery")
	ElseIf PlayerRef && PlayerRef.GetParentCell()
		MCM.SetModSettingString(MOD_NAME, "sCell:Debug", "other cell")
	Else
		MCM.SetModSettingString(MOD_NAME, "sCell:Debug", "unknown")
	EndIf
	If BondStarted
		MCM.SetModSettingString(MOD_NAME, "sBond:Debug", "bonded | kills " + KnifeKillCount)
	Else
		MCM.SetModSettingString(MOD_NAME, "sBond:Debug", "not bonded")
	EndIf
	If LastKillIgnoreReason == ""
		MCM.SetModSettingString(MOD_NAME, "sLastKill:Debug", "(none yet)")
	Else
		MCM.SetModSettingString(MOD_NAME, "sLastKill:Debug", LastKillIgnoreReason)
	EndIf

	String aliasStatus = EnsureCombatKillHooks()
	MCM.SetModSettingString(MOD_NAME, "sWatch:Debug", "watch " + KillWatchCount + " | " + aliasStatus)

	EnsureHungerSpell()
	If KnifeHungerSpell
		MCM.SetModSettingString(MOD_NAME, "sHungerSpell:Debug", "OK")
	Else
		MCM.SetModSettingString(MOD_NAME, "sHungerSpell:Debug", "MISSING SPEL")
		allOk = False
	EndIf
	If allOk
		MCM.SetModSettingString(MOD_NAME, "sOverall:Debug", "OK [" + DEBUG_BUILD + "]")
	Else
		MCM.SetModSettingString(MOD_NAME, "sOverall:Debug", "Issues - see rows")
	EndIf

	MCM.RefreshMenu()
	RefreshDebugBusy = False
	ToastDebug("PW debug refreshed [" + DEBUG_BUILD + "]")
	Debug.Trace("PickmansWhisper: RefreshDebugStatus done " + DEBUG_BUILD)
EndFunction
