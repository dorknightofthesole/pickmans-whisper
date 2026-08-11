Scriptname AAF:AAF_API extends Quest

Struct SceneSettings
	Float duration
	Bool skipWalk
	Bool preventFurniture
	Bool usePackages
	Bool isNPCControlled
	String position
	String meta
	String includeTags
	String excludeTags
	Int scanRadius
	Int furniturePreference
	ObjectReference locationObject
	Bool ignoreActorLocations
	String startEquipmentSet
	Bool megaScene
EndStruct

Struct PositionSettings
	String id
EndStruct

AAF:AAF_API:SceneSettings Function GetSceneSettings()
	SceneSettings s = new SceneSettings
	Return s
EndFunction

Function StartScene(Actor[] actors, SceneSettings settings)
EndFunction

Function StartSceneByPosition(Actor[] actors, String positionId)
EndFunction

Function StopScene()
EndFunction

Function StopSceneWithAbruptStop()
EndFunction

Function ApplyOverlaySet(Actor akActor, String overlaySetID)
EndFunction

Function RemoveOverlaySet(Actor akActor, String overlaySetID)
EndFunction

Int Function GetVersion()
	Return 0
EndFunction

Int Function GetAAFStatus()
	Return 0
EndFunction

String Function GetBuild()
	Return ""
EndFunction

; Real AAF CustomEvents (names must exist for RegisterForCustomEvent / CustomEventName).
CustomEvent OnAAFReady
CustomEvent OnSceneInit
CustomEvent OnSceneEnd
CustomEvent OnAnimationStart
CustomEvent OnAnimationStop
