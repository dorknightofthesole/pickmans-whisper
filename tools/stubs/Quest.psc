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

Function StartTimer(Float afInterval, Int aiTimerID = 0) Native
Function CancelTimer(Int aiTimerID = 0) Native
Alias Function GetAlias(Int aiAliasID) Native
; RegisterForCustomEvent / UnregisterForCustomEvent live on ScriptObject only —
; do not redeclare here (wrong Form + String signature shadows the real natives).
Function RegisterForRemoteEvent(Form akForm, String asEventName) Native
Function UnregisterForRemoteEvent(Form akForm, String asEventName) Native
Function RegisterForExternalEvent(String asEventName, String asCallback) Native
; RegisterForKey / UnregisterForKey live on ScriptObject — do not redeclare here
; (a Quest-only Native shadow can compile green and fail silently at runtime).
