Scriptname PickmansWhisperTargetScanScript extends Quest
{MainQuest Auto Const — filled from Main QUST VMAD form bind.}

; --- Properties ---
Actor[] Property TrackedTargets Auto
PickmansWhisperMainQuestScript Property MainQuest Auto Const Mandatory

; Scan / eligibility range — single source (other scripts read these Properties).
Float Property KILL_WATCH_RADIUS = 500.0 Auto Const ; was 800.0
Float Property KILL_CORPSE_RADIUS = 400.0 Auto Const
Float FIVE_FEET_IN_UNITS = 106.65 Const

Actor PlayerRef
Int TimerID_Scan = 100 Const
Float ScanInterval = 8.0 Const ; Run every 8 seconds
; Prior tick's PlayerAlias.IsReadyToGiveBeating — True↔False edge re-kicks beat for
; already-tracked living (RegisterTarget only runs on first add). Seeded in Init.
Bool LastReadyToGiveBeating = False

; --- Initialization ---
Event OnInit()
    Init()
EndEvent

Event OnQuestInit()
    Init()
EndEvent

Event Actor.OnPlayerLoadGame(Actor akSender)
    Init()
EndEvent

Function Init()
    Debug.Trace("PW Debug: PickmansWhisperTargetScanScript Init")
    PlayerRef = Game.GetPlayer()
    If PlayerRef
        RegisterForRemoteEvent(PlayerRef, "OnPlayerLoadGame")
    EndIf
    TrackedTargets = new Actor[0]
    ; Seed so the first scan is not a false True/False edge.
    If MainQuest && MainQuest.PlayerAlias
        LastReadyToGiveBeating = MainQuest.PlayerAlias.IsReadyToGiveBeating
    EndIf
    StartTimer(ScanInterval, TimerID_Scan)
EndFunction

; --- Core Loop ---
Event OnTimer(Int aiTimerID)
    If aiTimerID == TimerID_Scan
        ScanAndCleanTargets()
        
        ; Keep the loop running as long as the quest is active
        StartTimer(ScanInterval, TimerID_Scan)
    EndIf
EndEvent

Function ScanAndCleanTargets()
    If !MainQuest
        Debug.Notification("PW Error: MainQuest is not wired up")
        Debug.Trace("PW Error: MainQuest is not wired up")
    EndIf

    ; 1. GARBAGE COLLECTION (Clean up existing list first)
    Int i = TrackedTargets.Length
    While i > 0
        i -= 1
        Actor currentTarget = TrackedTargets[i]
        
        ; Remove if dead, unloaded, or out of active range
        If !currentTarget || !currentTarget.Is3DLoaded() || (currentTarget.GetDistance(PlayerRef) > (KILL_WATCH_RADIUS + FIVE_FEET_IN_UNITS))
            ; TODO unregister with the MainQuest
            TrackedTargets.Remove(i)
            Debug.Trace("PW: Cleaned up target -> " + currentTarget.GetDisplayName())
            ; Debug.Notification("PW: Cleaned up target -> " + currentTarget.GetDisplayName())
            MainQuest.UnRegisterTarget(currentTarget)
        EndIf
    EndWhile

    ; 2. SCAN FOR NEW NEARBY TARGETS
    Actor[] AliveTargets = GetAliveTargets()
    ProcessTargets(AliveTargets, "alive")

    Actor[] DeadTargets = GetDeadTargets()
    ProcessTargets(DeadTargets, "dead")

    Actor WhoIsThat = GetLookingAt()
    If WhoIsThat
        Var[] aimArgs = new Var[1]
        aimArgs[0] = WhoIsThat
        ; Victims MCM aim cache (living or dead).
        MainQuest.CallFunctionNoWait("NoteVictimsAimActor", aimArgs)
        If !WhoIsThat.IsDead() && MainQuest.IsValidTarget(WhoIsThat)
            MainQuest.CallFunctionNoWait("LookingAtTarget", aimArgs)
        EndIf
    EndIf

    ; Cadence formerly on KillerScan — Main / Beat own the bodies.
    If MainQuest
        MainQuest.CallFunctionNoWait("RunBondPoll", None)
        MainQuest.CallFunctionNoWait("RunHungerTick", None)
        If MainQuest.VoiceAlias
            MainQuest.VoiceAlias.CallFunctionNoWait("MaybeSpeakTrustLine", None)
        EndIf
        MainQuest.CallFunctionNoWait("TickBeatEssentialReconcile", None)
    EndIf
EndFunction

; When IsReadyToGiveBeating flips vs LastReadyToGiveBeating, HandleBeatBeforeKill for
; this living actor and commit LastReady (edge is one-shot for the first living hit
; in the FindActors pass — later actors that scan already see the new LastReady).
Bool Function MaybeRekickBeatOnBeatingModeEdge(Actor akTarget)
    If !akTarget || akTarget.IsDead() || !MainQuest || !MainQuest.PlayerAlias
        Return False
    EndIf
    Bool ready = MainQuest.PlayerAlias.IsReadyToGiveBeating
    If ready == LastReadyToGiveBeating
        Return False
    EndIf
    LastReadyToGiveBeating = ready
    CheckForBeatDown(akTarget)
    Return True
EndFunction

Function CheckForBeatDown(Actor akTarget)
    PickmansWhisperBeatBeforeKillScript beat = MainQuest.BeatBeforeKill()
    If !beat
        Debug.Trace("PickmansWhisper: ERROR beating-mode edge — BeatBeforeKill missing")
        Return
    EndIf
    Debug.Trace("PW: beating-mode edge → " + akTarget.GetDisplayName())
    Var[] beatArgs = new Var[1]
    beatArgs[0] = akTarget
    beat.CallFunctionNoWait("HandleBeatBeforeKill", beatArgs)
EndFunction

Function ProcessTargets(Actor[] akTargets, String debugContext)
    ; Debug.Notification("PW Debug: " + debugContext + " targets found: " + akTargets.Length)

    Int j = 0
    While j < akTargets.Length
        Actor potentialTarget = akTargets[j] as Actor
        Bool beatDownChange = MaybeRekickBeatOnBeatingModeEdge(potentialTarget)

        If potentialTarget && MainQuest.IsValidTarget(potentialTarget)
            ; Only add if not already in our tracking array
            If TrackedTargets.Find(potentialTarget) < 0
                TrackedTargets.Add(potentialTarget)
                
                CheckForBeatDown(potentialTarget)
                
                ; Fire-and-forget — do not block TargetScan on RegisterTarget work.
                Var[] regArgs = new Var[1]
                regArgs[0] = potentialTarget
                MainQuest.CallFunctionNoWait("RegisterTarget", regArgs)

                ; Debug.Notification("PW: Now tracking -> " + potentialTarget.GetDisplayName())
                Debug.Trace("PW: Now tracking -> " + potentialTarget.GetDisplayName())
            
            ElseIf beatDownChange
                ; Already tracked + IsReadyToGiveBeating flipped — re-RegisterTarget so
                ; unarmed first-add can gain OnDeath/Hit when the blade is drawn.
                Var[] regArgs = new Var[1]
                regArgs[0] = potentialTarget
                MainQuest.CallFunctionNoWait("RegisterTarget", regArgs)
                
            Else
                ; Already tracked — re-kick Slice H decay for dead so stage can advance
                ; while she stays in range (RegisterTarget only runs on first add).
                If potentialTarget.IsDead()
                    PickmansWhisperCorpseDecayScript decay = (MainQuest as Quest) as PickmansWhisperCorpseDecayScript
                    If decay
                        Var[] decayArgs = new Var[1]
                        decayArgs[0] = potentialTarget
                        decay.CallFunctionNoWait("HandleCorpseDecay", decayArgs)
                    EndIf
                EndIf
                Debug.Trace("PW: Already tracking -> " + potentialTarget.GetDisplayName())
            EndIf
        EndIf
        j += 1
        
        ; Safety cap to prevent array overflow in dense areas
        If TrackedTargets.Length >= 20
            Return
        EndIf
    EndWhile
EndFunction

Actor[] Function GetAliveTargets()
    return GardenOfEden.FindActors(None, None, -1, -1, PlayerRef, KILL_WATCH_RADIUS, 1, -1, -1, -1, -1, -1, None, None, "", 0, 1, 0)
EndFunction

Actor[] Function GetDeadTargets()
    return GardenOfEden.FindActors(None, None, -1, -1, PlayerRef, KILL_CORPSE_RADIUS, 0, 1, -1, -1, -1, -1, None, None, "", 0, 1, 1)
EndFunction

Actor Function GetLookingAt()
    ObjectReference cam = GardenOfEden3.GetCameraTargetReference()
	Actor CameraActor = cam as Actor
	If CameraActor == PlayerRef
		CameraActor = None
	EndIf
    return CameraActor
EndFunction
