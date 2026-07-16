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
ObjectReference Function PlaceAtMe(Form akFormToPlace, Int aiCount = 1, Bool abForcePersist = False, Bool abInitiallyDisabled = False, Bool abDeleteWhenAble = True) Native
Function ApplyHavokImpulse(Float afX, Float afY, Float afZ, Float afMagnitude) Native
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
Int Function GetItemCount(Form akItem) Native
