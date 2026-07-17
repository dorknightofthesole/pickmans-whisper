Scriptname Game Native

Actor Function GetPlayer() Global Native
Form Function GetForm(Int aiFormID) Global Native
Form Function GetFormFromFile(Int aiFormID, String asFilename) Global Native
Bool Function IsPluginInstalled(String asName) Global Native
; NOTE: Do NOT stub Game.GetCurrentCrosshairRef — that is Skyrim SKSE / optional
; extender API, not vanilla FO4 or base F4SE. A fake Native here compiles green and
; kills killscan at runtime when StartKillScanLoop runs after the call. Use GoE
; GardenOfEden3.GetCameraTargetReference / GetLastActivateTargetRef instead.
Function FadeOutGame(Bool abFadeOut, Bool abBlackFade, Float afFadeDuration, Float afSecondsBeforeFade, Bool abStayFaded = False) Global Native
Function DisablePlayerControls(Bool abMovement = True, Bool abFighting = True, Bool abCamSwitch = False, Bool abLooking = False, Bool abSneaking = False, Bool abMenu = True, Bool abActivate = True, Bool abJournalTabs = False, Bool abVATS = True, Bool abFavorites = True, Bool abRunning = True) Global Native
Function EnablePlayerControls(Bool abMovement = True, Bool abFighting = True, Bool abCamSwitch = True, Bool abLooking = True, Bool abSneaking = True, Bool abMenu = True, Bool abActivate = True, Bool abJournalTabs = True, Bool abVATS = True, Bool abFavorites = True, Bool abRunning = True) Global Native
