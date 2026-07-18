Scriptname RefCollectionAlias extends Alias Native

; FO4 native — hold multiple ObjectReferences on a quest alias.
Function AddRef(ObjectReference akNewRef) Native
Function RemoveRef(ObjectReference akRefToRemove) Native
Int Function Find(ObjectReference akFindRef) Native
ObjectReference Function GetAt(Int aiIndex) Native
Int Function GetCount() Native
