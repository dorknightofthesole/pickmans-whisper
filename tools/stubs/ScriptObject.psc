Scriptname ScriptObject Native

Function RegisterForKey(Int keyCode) Native
Function UnregisterForKey(Int keyCode) Native
Function RegisterForControl(String control) Native
Function UnregisterForControl(String control) Native
Function RegisterForRemoteEvent(Form akForm, String asEventName) Native
Function UnregisterForRemoteEvent(Form akForm, String asEventName) Native
; Real FO4 — second arg is CustomEventName (compiler type for a declared CustomEvent).
Function RegisterForCustomEvent(ScriptObject akSender, CustomEventName asEventName) Native
Function UnregisterForCustomEvent(ScriptObject akSender, CustomEventName asEventName) Native
Function SendCustomEvent(CustomEventName asEvent, Var[] akArgs = None) Native
Function RegisterForExternalEvent(String asEventName, String asCallbackName) Native
Function UnregisterForExternalEvent(String asEventName) Native

; FO4 hit events — registration is consumed after one matching hit; must re-register.
Function RegisterForHitEvent(ScriptObject akTarget, ScriptObject akAggressorFilter = None, Form akSourceFilter = None, Form akProjectileFilter = None, Int aiPowerFilter = -1, Int aiSneakFilter = -1, Int aiBashFilter = -1, Int aiBlockFilter = -1, Bool abMatch = True) Native
Function UnregisterForHitEvent(ScriptObject akTarget, ScriptObject akAggressorFilter = None, Form akSourceFilter = None, Form akProjectileFilter = None, Int aiPowerFilter = -1, Int aiSneakFilter = -1, Int aiBashFilter = -1, Int aiBlockFilter = -1, Bool abMatch = True) Native
Function UnregisterForAllHitEvents(ScriptObject akTarget = None) Native

; FO4 timers: StartTimer / CancelTimer / OnTimer (on Quest/ScriptObject in engine).
; Do NOT stub Skyrim RegisterForUpdate* — removed in FO4; fake Natives compile green
; and fail at runtime. See .cursor/rules/no-fake-native-stubs.mdc.

Event OnKeyDown(Int keyCode)
EndEvent

Event OnKeyUp(Int keyCode, Float holdTime)
EndEvent

Event OnControlDown(String control)
EndEvent

Event OnControlUp(String control, Float time)
EndEvent

Event OnHit(ObjectReference akTarget, ObjectReference akAggressor, Form akSource, Projectile akProjectile, Bool abPowerAttack, Bool abSneakAttack, Bool abBashAttack, Bool abHitBlocked, String asMaterialName)
EndEvent
