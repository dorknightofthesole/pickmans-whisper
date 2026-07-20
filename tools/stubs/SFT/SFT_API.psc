; Soft-dep stub for Scripted Face Tints (SFT.esp).
; Mirrors the public apply/remove surface used by Wound Lab.
; Do NOT invent members — keep in sync with the installed SFT:SFT_API.psc.
; Runtime implementation lives in the SFT mod; this stub is compile-only.
Scriptname SFT:SFT_API extends Quest

Bool Function ApplyHeadPart(String akCategory, String akTintName, Actor akActor = None)
	Return False
EndFunction

Bool Function ApplyHeadPartByFullName(String akTintName, Actor akActor = None)
	Return False
EndFunction

Bool Function ApplyHeadPartIfNone(String akCategory, String akTintName, Actor akActor = None)
	Return False
EndFunction

Bool Function RemoveHeadPart(String akTintName, Actor akActor = None)
	Return False
EndFunction

Bool Function RemoveHeadParts(String akCategory, Actor akActor = None)
	Return False
EndFunction

Function RemoveAllHeadParts(Actor akActor)
EndFunction

Bool Function HasHeadPart(String akTintName, Actor akActor = None)
	Return False
EndFunction
