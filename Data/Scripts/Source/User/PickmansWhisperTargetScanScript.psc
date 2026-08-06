Scriptname PickmansWhisperTargetScanScript extends Quest
{MainQuest Auto Const — filled from Main QUST VMAD form bind.}

; --- Properties ---
Actor[] Property TrackedTargets Auto
PickmansWhisperMainQuestScript Property MainQuest Auto Const Mandatory

Float KILL_WATCH_RADIUS = 800.0 Const
Float KILL_CORPSE_RADIUS = 400.0 Const
Float FIVE_FEET_IN_UNITS = 106.65 Const

Actor PlayerRef
Int TimerID_Scan = 100 Const
Float ScanInterval = 8.0 Const ; Run every 8 seconds
Float LookCommentCooldownSeconds = 30.0 Const
Float LastLookCommentRealTime = 0.0

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
            Debug.Notification("PW: Cleaned up target -> " + currentTarget.GetDisplayName())
            MainQuest.UnRegisterTarget(currentTarget)
        EndIf
    EndWhile

    ; 2. SCAN FOR NEW NEARBY TARGETS
    ; Find all loaded actors near the player
    Actor[] AliveTargets = GetAliveTargets()
    ProcessTargets(AliveTargets, "alive")

    Actor[] DeadTargets = GetDeadTargets()
    ProcessTargets(DeadTargets, "dead")

    Actor WhoIsThat = GetLookingAt()
    If WhoIsThat && MainQuest.IsValidTarget(WhoIsThat)
        Float now = Utility.GetCurrentRealTime()
        If LastLookCommentRealTime <= 0.0 || (now - LastLookCommentRealTime) >= LookCommentCooldownSeconds
            LastLookCommentRealTime = now
            ; TODO do something with this in Main
            Debug.Notification("PW Debug: " + WhoIsThat.GetDisplayName() + ", they look interesting... ")
        EndIf
    EndIf
EndFunction

Function ProcessTargets(Actor[] akTargets, String debugContext)
    ; Debug.Notification("PW Debug: " + debugContext + " targets found: " + akTargets.Length)

    Int j = 0
    While j < akTargets.Length
        Actor potentialTarget = akTargets[j] as Actor

        If potentialTarget && MainQuest.IsValidTarget(potentialTarget)
            ; Only add if not already in our tracking array
            If TrackedTargets.Find(potentialTarget) < 0
                TrackedTargets.Add(potentialTarget)
                ; Fire-and-forget — do not block TargetScan on RegisterTarget work.
                Var[] regArgs = new Var[1]
                regArgs[0] = potentialTarget
                MainQuest.CallFunctionNoWait("RegisterTarget", regArgs)

                ; Debug.Notification("PW: Now tracking -> " + potentialTarget.GetDisplayName())
                Debug.Trace("PW: Now tracking -> " + potentialTarget.GetDisplayName())
            Else
                ; Debug.Notification("PW: Already tracking -> " + potentialTarget.GetDisplayName())
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
