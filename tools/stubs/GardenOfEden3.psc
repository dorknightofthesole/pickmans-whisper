ScriptName GardenOfEden3 Native Hidden

Struct RayCastParams
	Float fRayLength
	Float fRayStartPosX
	Float fRayStartPosY
	Float fRayStartPosZ
	Float fRayAngleX
	Float fRayAngleY
	Float fRayAngleZ
	Bool bCastUpward
	Bool bCastDownward
	Int iCollisionObjectFilter
	String sCollisionLayers
	Float fRayOffsetX
	Float fRayOffsetY
	Float fRayOffsetZ
	Bool bQueryHitRef
EndStruct

Struct RayCastResult
	Bool bValid
	Bool bHasHit
	String sHitNode
	ObjectReference HitRef
	Float fHitPosX
	Float fHitPosY
	Float fHitPosZ
	Float fHitDistance
EndStruct

Bool Function DisableCollision(ObjectReference akReference, Bool abDisable = True) Native Global
ObjectReference Function GetCameraTargetReference() Native Global
Float[] Function Get3DPosition(ObjectReference akReference) Native Global
Float Function GetGroundDistanceFromLimb(Actor akActor, Int aiLimbIndex) Native Global
Float Function GetTerrainHeightAtReference(ObjectReference akReference) Native Global
ObjectReference Function FindClosestReferencesWithFormType(String[] asFormTypes, ObjectReference akOrigo, Float afAerialDistance) Native Global
RayCastResult Function RayCast(RayCastParams akParams) Native Global
Bool Function ApplyFanMotorEx(ObjectReference akReference, String asNodeName, Float aAxisX, Float aAxisY, Float aAxisZ, Float aForce, Bool abOn) Native Global
Bool Function FanMotorOnEx(ObjectReference akReference, String asNodeName, Bool abOn) Native Global
Bool Function ExecuteConsoleCommandSilent(String asCommand, ObjectReference akSelectRef = None) Native Global
