ScriptName GardenOfEden2 Native Hidden

ObjectReference Function GetLastActivateTargetRef() Native Global

Actor[] Function GetActorsDetecting(Actor akActor, Bool bMustHaveLOS = False) Native Global
Actor[] Function GetActorsDetectedBy(Actor akActor, Bool bMustHaveLOS = False) Native Global

Bool Function DoesFileExist(String asFileName, String asFilePath = "") Native Global
String Function GetLineFromFile(String asFileName, Int aiLine, String asFilePath = "") Native Global
String[] Function GetLinesFromFile(String asFileName, String asFilePath = "") Native Global
Int Function CountLinesOfFile(String asFileName, String asFilePath = "") Native Global
; Splits on whitespace (drops edge/control whitespace). Used for TrimString — FO4 has no StringUtil.
String[] Function GetWordsInStringAsArray(String asString) Native Global
; Real GoE2 native — same lookup SFT uses for Damage/Boxer FULL names (face lab).
HeadPart[] Function GetHeadPartsByFullName(String asFullName) Native Global

Int Function GetModelNodeCount(ObjectReference akReference) Native Global
String[] Function GetModelNodes(ObjectReference akReference) Native Global
String Function GetNthNodeName(ObjectReference akReference, Int aiNodeIndex) Native Global
Float[] Function GetNthNodePosition(ObjectReference akReference, Int aiNodeIndex) Native Global
Float[] Function GetNthNodeParentRelativePosition(ObjectReference akReference, Int aiNodeIndex) Native Global
Bool Function SetNthNodePosition(ObjectReference akReference, Int aiNodeIndex, Float[] afPosition) Native Global
Bool Function SetNthNodeParentRelativePosition(ObjectReference akReference, Int aiNodeIndex, Float[] afPosition) Native Global
Int Function GetClosestNodeToPosition(ObjectReference akReference, Float[] afPosition) Native Global
