ScriptName GardenOfEden Native Hidden

Int Function GetVersionRelease() Native Global
Function ResetHavokPhysics(Actor akActor) Native Global
Function InitHavok(ObjectReference akReference) Native Global
Function ClampToGround(ObjectReference akReference) Native Global
String Function GetHexFormID(Form akForm) Native Global

Int[] Function GetEquippedItemIndexes(ObjectReference akReference) Native Global
Int Function GetNthItemIsEquipped(ObjectReference akReference, Int aiItemIndex) Native Global
Int Function GetNthItemBaseID(ObjectReference akReference, Int aiItemIndex) Native Global

Actor[] Function FindActors(Keyword[] akMustHaveKeywords, Keyword[] akExcludeKeywords, \
	int aiMustHaveKeywordsMode = 1, int aiExcludeKeywordsMode = 1, ObjectReference akOrigoRef = None, float afDistance = -1.0, \
	int aiLifeState = -1, int ai3DLoadedState = -1, int aiHostileState = -1, int aiSex = -1, int aiMinLevel = -1, int aiMaxLevel = -1, Actor akMyCombatTarget = None, \
	Keyword akMyCombatTargetMustHaveKeyword = None, String asName = "", int aiReturnMode = 0, int aiReturnOrderMode = 1, int aiSelectiveProcessMode = 0) native global
