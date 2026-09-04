# Changelog — Pickman's Whisper

Slice status and planned work live in [docs/ROADMAP.md](docs/ROADMAP.md); this file is the per-release summary.

---

## 1.4.0 — Butcher props

48 commits since 1.3.0. The headline is **Cut Off Tits**, but this release is also where Execute, Slavery, Force Trade, and the Corpse Decay pipeline all landed.

### Cut Off Tits (Slice F)

The butcher menu (`/` with the blade drawn, aimed at a dead adult woman) gains a **Cut Off Tits** entry. Unlike the limb options it is not an `Actor.Dismember` call — FO4 has no breast gore bone — so it works in two halves: the corpse is swapped onto a slot-33 mutilated-body ARMO, and a lootable, weighted **Cut Off Tits** MISC is dropped beside her.

- The dropped prop has **working Havok**: it falls, settles on the floor, can be shoved around, and can be looted.
- Getting there meant fixing three defects in the Blender-exported Havok packfile, none of which are visible in Blender or NifSkope. Diagnosed by byte-diffing against vanilla `GoreSuperMutantArmL.nif`:
  - `hknpBodyCinfo.m_motionId` was left on its `0x7FFFFFFF` default, which is Havok's definition of a **static** body — it collided and looted but could never fall or be pushed. This was the actual bug.
  - `hknpMotionCinfo` was allocated at `0x40` bytes where the engine reads `0x70`, so the orientation quaternion was read off the end of the array as **NaN**.
  - `m_inverseInertiaLocal` was being written as direct `I`. Havok stores `1/I` there, so the prop had roughly 2400x too much rotational inertia.
- Spawn order matters and is now fixed: `PlaceAtMe` **initially disabled** → `MoveTo` → `Enable` → wait for 3D → `InitHavok`. Moving a MISC that already has 3D keyframes it in Havok and it hangs in the air regardless of how correct the NIF is.
- Corpse decay no longer **replaces** the mutilated body. Decay strips the corpse before applying overlays, which was also removing the slot-33 ARMO; it is now restored after the strip so decay layers on top of the severed body instead of reverting it.
- Cut cap renders correctly on a dropped MISC: vanilla `Materials\Gore\GoreHumanLeg.BGSM`, shader forced to Default, `FACEGEN_RGB_TINT` cleared, `DOUBLE_SIDED` set. A facegen-tinted skin shader on a MISC draws as nothing.
- New build guide: [docs/Severed_Part_Guide.md](docs/Severed_Part_Guide.md) — the whole Blender → materials → Havok → ESP → spawn → verify pipeline, with a symptom-to-cause troubleshooting table.

### Execute (Slice W)

Instant kill on a **living** victim via a new `\` hotkey — **Decapitate** or **Smash Head In**. Previously beheading was corpse-only.

### Slavery (Slice T)

- **Enslave** — follow plus cross-cell warp. Deliberately **not** a vanilla companion: she stays a Whisper victim you can still kill.
- Pacify a beaten victim with a **slave collar**, and force collar plus bindings onto her.
- Any inventory item whose name contains `slave` (case-insensitive) pacifies her on trade close and auto-enslaves.
- Gated on a living eligible target, knife calm, and player Charisma ≥ `slaveryMinCha`.

### Force Trade (Slice S)

Activate-choice inventory access (`OpenInventory`) on eligible living victims. First trade strips outfit-locked gear once; later trades keep whatever you dressed her in. Gated on knife calm and `victimTradeMinCha`. The `]` key toggles the Force Trade / Enslave / Take Her activate choices, off by default so beat and attack keep a clean activate, and they stay hidden while the blade is drawn.

### Take Her (Slice U)

Once she is already enslaved, this choice replaces the old direct "Free" with a two-actor AAF scene, with randomized position selection. Requires AAF. Direct freeing without a scene moved to an MCM button on the Victims page. This is the mod's one narrow sexual exception, as described in the README.

### Corpse decay (Slice H)

- Tracked knife-kill bodies stage through LooksMenu overlays over in-game days.
- MCM Set/Reset moves the kill clock immediately; ambient sync applies stage changes to all tracked corpses.
- FaceGen-preserving **slot-54 face decals** so corpses keep their real face identity — no slot-32 full-head swap.
- At max decay stage, a toast urges the player to eat her before she is too ripe; eating a stage-4 corpse grants an END buff. Cannibal-perk gated. Detection hangs off the vanilla `PerkCannibalHeal` effect landing on the player, since FO4 exposes no animation event for the Cannibal eat action.
- Facial bruises now apply after a beat-down.

### Bed corpse hallucination (Slice G)

Occasional hallucinated corpse near the bed on sleep, with look-away despawn. Rebuilt around **sleep-start only**, which made it substantially more reliable.

### Architecture — Killer Orchestrator (Slice J)

The multi-timer arming model is gone. `PickmansWhisperKillerScanScript` is now the mod's **single** recurring timer and the sole `FindActors` producer: it builds one target snapshot per tick and fans out to Voice (sync) plus knife, cadence, Victims, CorpseDecay, and BedGift (NoWait). Delays that used to own their own timers now use realtime deadlines checked on that cadence. `WorldScan` and the old KillerScan state tracking were removed rather than left as a second path.

### Removed

- The Glowing One–cloned **proximity cloak** SPEL/MGEF chain (`0x870`–`0x873`) and `PickmansWhisperProximityEffect`. Built during this cycle, then retired; a contract test now keeps it from coming back.

### Tooling

- `tools/compare_prop_havok.py` — side-by-side Havok diff of our prop against any vanilla reference NIF.
- Prop Havok verifiers fail the build on a short motion array, a static motion id, or direct-`I`-where-`1/I`-belongs, so a Blender re-export cannot silently regress the physics.
- `tools/test_version_sync.py` — `fomod/info.xml` is the version source of truth; the Papyrus and MCM copies are checked against it and any stray version literal in Main fails the gate.
- Deploy now copies file by file, because `Copy-Item -Recurse -Force` was not reliably overwriting an existing NIF at the destination — which made several correct fixes look like they did nothing in-game. The gate also hash-compares the deployed prop NIF against source.

### Verification state

**Cut Off Tits is confirmed working in-game.** Several other slices in this release are implemented and passing contracts but not yet confirmed in a play session — Execute (W), Slavery (T), Take Her (U), the Killer Orchestrator retirement (J1), and parts of Corpse Decay (H). See [docs/ROADMAP.md](docs/ROADMAP.md) for the current per-slice status.

---

## Earlier releases

Pre-1.4.0 history was not tracked in a changelog. For what shipped when, see the slice table in [docs/ROADMAP.md](docs/ROADMAP.md):

- **1.3.0** — Killer Orchestrator refactor: single main-loop timer replacing the per-feature timers.
- **0.2.0** — full asset payload build.
- **0.1.0** — Slice A: bond on house/knife, toast-only voice, hunger meter, MCM.
