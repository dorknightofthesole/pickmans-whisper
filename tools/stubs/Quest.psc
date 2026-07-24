Scriptname Quest extends Form

Event OnInit()
EndEvent

Event OnQuestInit()
EndEvent

Event OnTimer(Int aiTimerID)
EndEvent

; Real FO4 Quest natives — do not stub with dummy Return True/False bodies.
Bool Function Start() Native
Function Stop() Native
Bool Function IsRunning() Native
Bool Function IsStopping() Native

Alias Function GetAlias(Int aiAliasID) Native
; StartTimer / CancelTimer / RegisterForRemoteEvent / RegisterForExternalEvent /
; RegisterForKey live on ScriptObject — do not redeclare here (wrong signatures
; compile green and fail or shadow the real natives at runtime).
