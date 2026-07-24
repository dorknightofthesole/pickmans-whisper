Scriptname ObjectReference extends Form Native

Float Function GetPositionX() Native
Float Function GetPositionY() Native
Float Function GetPositionZ() Native
Float Function GetAngleX() Native
Float Function GetAngleY() Native
Float Function GetAngleZ() Native
Function SetPosition(Float x, Float y, Float z) Native
Function SetAngle(Float x, Float y, Float z) Native
Float Function GetDistance(ObjectReference akOther) Native
Cell Function GetParentCell() Native
; F4SE — inventory/world display name (legendary uniques); Form.GetName() is often the base WEAP name.
; World rename is NOT a member here (Skyrim SKSE shape). Use GardenOfEden2.SetDisplayName(ref, name).
String Function GetDisplayName() Native
; F4SE — attached ObjectMods (legendary + weapon mods on this instance)
ObjectMod[] Function GetAllMods() Native
ObjectReference Function PlaceAtMe(Form akFormToPlace, Int aiCount = 1, Bool abForcePersist = False, Bool abInitiallyDisabled = False, Bool abDeleteWhenAble = True) Native
; FO4 native — enable/disable any world ref (STAT clutter, actors, etc.).
Function Disable(Bool abFadeOut = False) Native
Function Enable(Bool abFadeIn = False) Native
Bool Function IsDisabled() Native
Bool Function Is3DLoaded() Native
Bool Function HasKeyword(Keyword akKeyword) Native
Float Function GetValue(ActorValue akAV) Native
Function SetValue(ActorValue akAV, Float afValue) Native
Function ModValue(ActorValue akAV, Float afAmount) Native
Float Function GetHeadingAngle(ObjectReference akOther) Native
Function Delete() Native
Function ApplyHavokImpulse(Float afX, Float afY, Float afZ, Float afMagnitude) Native
; FO4 native — blood/debris decals via ImpactDataSet (pick from node along direction).
Bool Function PlayImpactEffect(ImpactDataSet akImpactEffect, String asNodeName = "", Float afPickDirX = 0.0, Float afPickDirY = 0.0, Float afPickDirZ = -1.0, Float afPickLength = 512.0, Bool abApplyNodeRotation = False, Bool abUseNodeLocalRotation = False) Native
Function ForceAddRagdollToWorld() Native
Function ForceRemoveRagdollFromWorld() Native
Function PushActorAway(Actor akActorToPush, Float aiKnockbackForce) Native
Function MoveTo(ObjectReference akTarget, Float afXOffset = 0.0, Float afYOffset = 0.0, Float afZOffset = 0.0, Bool abMatchRotation = True) Native
Function SetMotionType(Int aeMotionType, Bool abAllowActivate = True) Native
Int Property Motion_Fixed = 0 AutoReadOnly
Int Property Motion_Dynamic = 1 AutoReadOnly
Int Property Motion_Keyframed = 2 AutoReadOnly
Function TranslateTo(Float afX, Float afY, Float afZ, Float afXAngle, Float afYAngle, Float afZAngle, Float afSpeed, Float afMaxRotationSpeed = 0.0) Native
Function StopTranslation() Native
Function AddItem(Form akItem, Int aiCount = 1, Bool abSilent = False) Native
Function RemoveItem(Form akItem, Int aiCount = 1, Bool abSilent = False, ObjectReference akOtherContainer = None) Native
; FO4 native — strip inventory (weapons/armor/junk). akTransferTo None = destroy.
Function RemoveAllItems(ObjectReference akTransferTo = None, Bool abKeepOwnership = False) Native
Int Function GetItemCount(Form akItem) Native
