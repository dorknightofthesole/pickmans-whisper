Scriptname PickmansWhisperVoiceScanScript extends Quest
{KillerScan voice listener — live NPC whispers only (fixation / Recognition + Notice).
Called DIRECTLY from KillerScan (sync). Knife credit on Main; overlays on CorpseDecay.
No LooksMenu / Utility.Wait. Ignores dead targets in TargetSnapshot.}

PickmansWhisperMainQuestScript Function Main()
	Return (Self as Quest) as PickmansWhisperMainQuestScript
EndFunction

; Sync entry from KillerScan — must stay Wait-free. Living-only feature (ignore dead).
Function HandleKillerScanVoice(PickmansWhisperKillerScanScript akSender)
	If !akSender
		Debug.Trace("PickmansWhisper: VoiceScan skip | !akSender")
		Return
	EndIf
	PickmansWhisperMainQuestScript m = Main()
	If !m
		Debug.Trace("PickmansWhisper: ERROR VoiceScan — Main script missing")
		Return
	EndIf
	; Heartbeat every tick — if MCM sVoiceDispatch never moves, KillerScan never called us.
	String bondBit = "bond=0"
	If m.BondStarted
		bondBit = "bond=1"
	EndIf
	m.NoteVoiceDispatch("tick=" + akSender.ScanTick + " " + bondBit + " alive=" + akSender.ScanAliveCount)
	; Recognition (look edge) then ambient Notice.
	m.TickLookFixation()
	If m.BondStarted
		m.MaybeSpeakNoticeLine("killscan")
	ElseIf (akSender.ScanTick % 6) == 0
		m.MaybeSpeakNoticeLine("killscan-prebond")
	Else
		Debug.Trace("PickmansWhisper: VoiceScan skip | prebond throttle tick=" + akSender.ScanTick)
	EndIf
EndFunction
