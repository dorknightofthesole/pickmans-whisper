Scriptname Sound extends Form Native

; Real FO4 Papyrus — plays a Sound Descriptor (SNDR), not a filesystem path.
Int Function Play(ObjectReference akSource) Native
; Latent — waits until the instance finishes (or fails).
Bool Function PlayAndWait(ObjectReference akSource) Native
; Stop a playback instance returned by Play.
Function StopInstance(Int aiPlaybackInstance) Native Global
Function SetInstanceVolume(Int aiPlaybackInstance, Float afVolume) Native Global
