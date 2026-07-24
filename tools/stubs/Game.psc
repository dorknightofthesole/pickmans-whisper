Scriptname Game Native

Actor Function GetPlayer() Global Native
Form Function GetForm(Int aiFormID) Global Native
Form Function GetFormFromFile(Int aiFormID, String asFilename) Global Native
Bool Function IsPluginInstalled(String asName) Global Native
; NOTE: Do NOT stub Game.GetCurrentCrosshairRef — that is Skyrim SKSE / optional
; extender API, not vanilla FO4 or base F4SE. A fake Native here compiles green and
; kills killscan at runtime when StartKillScanLoop runs after the call. Use GoE
; GardenOfEden3.GetCameraTargetReference / GetLastActivateTargetRef instead.
;
; NOTE: Do NOT stub EnablePlayerControls / DisablePlayerControls — those are Skyrim.
; FO4 uses InputEnableLayer / Is*ControlsEnabled queries instead.
; Arg order matches FO4 Game.psc (secs-before-fade, then fade duration).
Function FadeOutGame(Bool abFadingOut, Bool abBlackFade, Float afSecsBeforeFade, Float afFadeDuration, Bool abStayFaded = False) Global Native
