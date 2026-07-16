Scriptname Quest extends Form

Event OnInit()
EndEvent

Event OnQuestInit()
EndEvent

Event OnTimer(Int aiTimerID)
EndEvent

Bool Function Start()
	Return True
EndFunction

Function Stop()
EndFunction

Bool Function IsRunning()
	Return True
EndFunction

Bool Function IsStopping()
	Return False
EndFunction

Function StartTimer(Float afInterval, Int aiTimerID = 0) Native
Function CancelTimer(Int aiTimerID = 0) Native
Alias Function GetAlias(Int aiAliasID) Native
Function RegisterForCustomEvent(Form akSender, String asEventName) Native
Function UnregisterForCustomEvent(Form akSender, String asEventName) Native
Function RegisterForRemoteEvent(Form akForm, String asEventName) Native
Function UnregisterForRemoteEvent(Form akForm, String asEventName) Native
Function RegisterForExternalEvent(String asEventName, String asCallback) Native
Function RegisterForKey(Int keyCode) Native
Function UnregisterForKey(Int keyCode) Native
