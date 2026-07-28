Scriptname ActiveMagicEffect extends ScriptObject Native Hidden

; Event received when this effect is first started (OnInit may not have been run yet!)
Event OnEffectStart(Actor akTarget, Actor akCaster)
EndEvent

; Event received when this effect is finished (effect may already be deleted, calling
; functions on this effect will fail)
Event OnEffectFinish(Actor akTarget, Actor akCaster)
EndEvent
