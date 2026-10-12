# QUANTUM GRID 2099 — BLACKOUT PROTOCOL

A cyberpunk laser-reflection puzzle game played entirely over SSH — now with
live ICE daemons (six kinds, including wall-phasing wraiths, lane-charging
lancers and pulsing volt wards), splitter prisms, teleport arrays, datashards,
persistent saves, a 22-entry codex, typewriter cutscenes (prologue, sector
beats, first-encounter daemons, two endings), career records, a daily
gauntlet, an EMP burst, hint traces, a hall of fame, a settings
system, an 8-bit chiptune engine and a pixel-doubled playfield. Every one of the 48 nodes is
BFS-verified solvable AND beatable with live ICE by an adaptive bot
(`scripts/audit_levels.py`).

You are **NYX**: a netrunner with a light-beam probe and a brother the Grid
erased. Descend through **6 sectors and 48 nodes** of OMNICORP's Quantum
Grid, rotate mirrors, fork beams through prisms, fold space across teleport
pads, dodge the daemons hunting you — and piece KAI back together from the
datashards he left behind.

```
================================================================================
  QUANTUM GRID 2099 // NODE 20 [SECTOR 03] - THE HUNTER
  BW [██████████████░░░░░░] 70% | REC 1/2 [LOCKED] | ◆ 1/2 | 15400 PTS
================================================================================

                 ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
                 ▓·································▓
                 ▓·▶──────────@\·········✖·········▓
                 ▓·································▓
                 ▓··········Ω·····◉····»·····«····▓
                 ▓·············◇··········◆·······▓
                 ▓·································▓
                 ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓

  STATUS: ICE STRIKE! -25% bandwidth. Daemon stunned - move!
  CONTROLS: WASD (Move) | R (Rotate Mirror) | K (Restart) | Q (Disconnect)
================================================================================
```

## Quick Start

```bash
pip install -r requirements.txt
python main.py
# in another terminal:
ssh -p 2222 localhost
```

The server generates an Ed25519 host key on first boot (`ssh_host_key`).
No authentication is required — anyone who connects gets a session, and
your SSH username **is your save file**. Log in as the same user to resume.

### Command-line options

| Flag | Default | Description |
| --- | --- | --- |
| `--host` | `0.0.0.0` | Bind address |
| `--port` | `2222` | Listen port |
| `--host-key` | `ssh_host_key` | SSH host key path (generated if missing) |

### Environment

| Variable | Description |
| --- | --- |
| `QG_UNLOCK_ALL=1` | Unlock all 48 nodes from the start (demo/judging mode) |
| `QG_NO_ICE=1` | Disable ICE daemons (laser-puzzle verification runs) |
| `QG_SAVE_DIR=...` | Save directory (default: `./saves`) |
| `QG_AUDIO=off` | Initial sound mode: `full` / `music` / `sfx` / `off` |

## The Campaign

| Sector | Name | Nodes | Introduces |
| --- | --- | --- | --- |
| 01 | THE SPINE | 1–8 | Mirrors, receptors, bandwidth |
| 02 | NEON DISTRICT | 9–16 | Splitter prisms, Director Vex |
| 03 | ICE FOUNDRY | 17–24 | SENTINEL + HUNTER daemons |
| 04 | THE MAZE | 25–32 | Teleport pad arrays, WRAITH daemons |
| 05 | BLACK VAULT | 33–40 | CORRUPTOR + LANCER daemons, heavy ICE mixes |
| 06 | SINGULARITY CORE | 41–48 | VOLT wards, all six daemons at once |

Every node is procedurally generated, BFS-verified solvable, and shows its
par (optimal action count) after extraction.

## Controls

| Key | Action |
| --- | --- |
| `W A S D` / arrow keys | Move the light-beam probe |
| `R` | Rotate an adjacent (or underfoot) mirror |
| `E` | Fire the EMP burst (1 charge per node, 10% bandwidth) |
| `H` | Buy a hint: traces the next optimal step (5% bandwidth) |
| `K` | Restart the current node (restores entry bandwidth) |
| `M` | Cycle sound mode: full → music → SFX → off |
| `O` | Settings screen (from sector / node select) |
| `C` | Open the codex (from sector / node select) |
| `L` | Open the hall of fame (from sector / node select) |
| `R` | Open the RECORDS screen (from the save menu) |
| `D` | THE DAILY GAUNTLET (from sector select) |
| `1`–`6` | Pick a sector |
| `1`–`8` | Pick a node within a sector |
| `ENTER` | Continue: next uncleared node |
| `Q` | Disconnect |

## Sound & Visuals

### Hearing the soundtrack (companion client)

SSH is a text channel — the game cannot play audio on your machine by
itself. The companion client fixes that: run it instead of plain `ssh`
and it synthesizes the entire chiptune **locally as real 8-bit audio**
(square-wave synthesis, no dependencies):

```bash
python3 -m qgrid.audio_client -- ssh -p 2222 <host>
```

It bridges a PTY: your keystrokes and the game's rendering pass through
untouched, while the tone markers embedded in the stream are intercepted
and played through your actual speakers (`paplay` / `pw-play` / `aplay` /
`ffplay` / `mpv` on Linux, `afplay` on macOS, `[console]::beep` on
Windows—under WSL). Melodies, SFX, everything.

Running bare `ssh` instead? You still get the terminal-bell fallback
(beep rhythms). If you hear *nothing*: most terminals ship with the
audible bell muted — either use the companion client, or enable the
"audible bell" setting in your terminal. Servers can run with
`QG_BELL=off` to mute the bell when using the companion (avoids
double-beeps).

### Story & cutscenes

The campaign opens with a **prologue cutscene** (rain-soaked Sector 7, the debt, MIRAGE's call), each sector ends with a **dialogue cutscene** advancing the plot - NYX, MIRAGE, DIRECTOR VEX and ORACLE-9 trade words as you descend - and the finale plays one of **two ending cutscenes** before the victory screen. Pages type out character by character; any key reveals the page, ENTER advances, X skips the scene.

On top of those, **eight one-time milestone cutscenes** play the first time their moment happens: meeting each daemon class for the first time (sentinel, hunter, wraith, lancer, corruptor, volt - each with its dossier beat), your first ICE strike, your first EMP burst, and your first death. Seen scenes are remembered in your save and never replay; several unlock codex entries. Press `R` on the save menu to see your **RECORDS** screen: 10 career achievements (first descent, clean room, EMP jockey, gauntlet runner, the true ending...) inscribed as you earn them.

### Settings

Press `O` on the sector or node screen. Settings persist per-runner in your save and apply instantly:

| Setting | Values |
| --- | --- |
| SOUND | full / music / sfx / off (same as `M`) |
| SCREEN SHAKE | on / off (accessibility) |
| FLASH EFFECTS | on / off (accessibility) |
| BEAM SHIMMER | on / off |
| TEXT SPEED | normal / fast / instant (cutscenes) |

### 8-bit chiptune engine

SSH is a text channel, so the soundtrack is synthesized through the
terminal bell — pitch-programmed square-wave tones (`CSI 10;Hz` + BEL):

- **Music loops:** title theme, explore theme, and a **danger theme** that
  kicks in automatically when any live ICE closes in (a hunter in range, a
  wraith drifting near, a lancer with a lane on you, a volt at arm's length).
- **~12 SFX:** move/rotate blips, receptor power-ups, shard arpeggios,
  teleport zaps, ICE-strike hits, extraction fanfares, game-over dirge,
  campaign victory fanfare.
- **`M`** cycles full → music → sfx → off. `QG_AUDIO` sets the default.
- **Companion client = real melodies** (see above). The bell fallback
  plays pitch-programmed tones on PC-speaker terminals (Linux console)
  and bell rhythms elsewhere.
- The **equalizer strip** in the HUD animates with the music either way.

### Visual effects

- **2×2 pixel-doubling:** the grid auto-upscales to chunky 8-bit blocks
  whenever your terminal fits it (2×2 diagonal mirrors, doubled walls and
  daemons). On an 80x24 terminal the chrome shrinks to 5 lines so the grid
  fills the screen; on a large terminal the grid itself quadruples in area.
- **Beam shimmer:** laser trails pulse between single/double-line glyphs.
- **Flash bursts:** receptors flare when powered, shards sparkle, both
  teleport pads light up on a fold, the exit node flares when unlocked.
- **Screen shake + red alert rule** on ICE strikes, with a red rule tint
  while the shake is active.
- **Animated screens:** sweeping laser-lane on the title, blinking
  prompts, pulsing banners on victory.

## Mechanics

### Grid symbols

| Symbol | Entity | Behavior |
| --- | --- | --- |
| `@` | Player probe | absorbs beams it stands in |
| `▶◀▲▼` | Laser emitters | fire the beam |
| `◉` | Receptor | powered by any beam reaching it |
| `/` `\` | Mirrors | bend the beam 90°, rotatable with `R` |
| `◇` | Splitter prism | forks the beam into two perpendicular beams |
| `»«` | Teleport pad pair | step on one, fold to the other (free) |
| `◆` | Datashard | KAI's memory fragments: score + codex + endings |
| `✖` | SENTINEL ICE | patrols an axis, bounces off obstacles |
| `☠` | HUNTER ICE | chases within 6 cells, moves every other tick |
| `Ψ` | CORRUPTOR ICE | flips a nearby mirror, then backs off and shifts targets - no mirror stays pinned |
| `≈` | WRAITH ICE | phase ghost: drifts through walls toward you, one step every third tick |
| `†` | LANCER ICE | locks onto any probe in its row/column with clear sight and dashes 2 cells per tick |
| `¥` | VOLT ICE | static ward: pulses a charge field into its 4 adjacent cells every other tick |
| `▓` | Wall | blocks beams, movement and daemons (not wraiths) |
| `Ω` | Extraction node | step here with all receptors powered to win |

### Beam optics

Every action re-runs the ray tracer from each emitter. Mirrors bend the
beam 90 degrees, splitter prisms fork it into two perpendicular beams,
receptors are powered and let light pass. The player absorbs any beam it
stands in. Loop protection (including through prism forks) prevents
infinite traces. Beams pass through shards, pads and daemons — light
doesn't care about software.

### Bandwidth

You descend with a **200% bandwidth budget** per node (the run timer).
Every move or rotation consumes **1%**; **ICE strikes cost 25%**; an
**EMP burst costs 10%**. Hit 0% and the session severs (game over —
progress is saved). Bandwidth refreshes to 200% after every node; `K`
restores what you entered with. With node solutions averaging ~35
optimal actions, even the hardest node leaves 3x headroom for detours,
shard runs and daemon mistakes.

### The EMP burst

Press `E` once per node: the probe discharges a pulse that **stuns every
daemon within 2 cells for 4 ticks** — hunters mid-pounce, lancers
mid-dash, a volt mid-pulse. It costs 10% bandwidth. The HUD shows
`EMP READY` / `EMP SPENT`. Save it for the corridor you can't route
around — a stunned daemon is also a door.

### The hint trace

Stuck? `H` runs a solver trace from your current position: it flashes
the next optimal step (a destination cell, or the mirror that wants a
turn) and tells you the direction. A trace costs **5% bandwidth** and
does **not** advance the world — daemons hold still while you peek. No
affordable trace when you're below 6%; no refund if the tangle you're in
has no solution thread (it says so, and suggests `K`).

### THE DAILY GAUNTLET

Press `D` on the sector screen: **one shared node per calendar day**,
seeded from the date so every runner on the server faces the exact same
floor. Difficulty ramps through the week — Monday is a sector-3 warm-up,
Sunday is a six-daemon sector-6 finale. Scores post to a per-day hall of
fame (separate from the campaign board) with your daily best and rank;
attempts persist in your save. Gauntlets never touch your campaign
bandwidth carry, and the board resets at midnight. The day's layout is
generated once and cached under the save directory, so the whole server
shares it instantly.

### ICE combat

Daemons act on every successful player action (turn-based):

- **Contact costs 25% bandwidth.** The striking daemon is knocked back a
  cell and stunned 4 ticks; a stunned daemon is walkable (safe to pass).
  A pulsing volt is never knocked back - its stun *is* the window.
- Walking **into** live ICE also triggers a strike — the daemon is shoved
  along your path. You can always push through a blocker, at a price.
- **Sentinels** never chase; learn their lane. **Hunters** are slower than
  you — outrun them, break line of sight. **Corruptors** flip a mirror and
  back off for several ticks — race them, then restore your optics. A
  mirror you're touching (standing on or beside) is protected from
  corruption: hold your optics while you work. **Wraiths** ignore walls
  entirely — cover means nothing, keep moving and don't let one drift
  into your corridor. **Lancers** only dash when they can *see* you down
  a shared row or column — sidestep off the lane and they crawl. **Volts**
  never move; they own the four cells around them on a steady pulse —
  walk through on the off-beat, or bait a pulse and work while the ward
  recovers.
- The BFS solver intentionally ignores ICE: it verifies the laser puzzle.
  Beating a node *with* live daemons is the real game.

### Scoring & endings

Per node: `bandwidth×10 + shards×250 + efficiency bonus (par)`, plus a
**+400 FLAWLESS bonus** for clearing an ICE node without a single
strike. Scores bank into a persistent run total; final rank ranges from
SCRIPT KIDDIE to LEGEND OF THE GRID. Bank **90% of all datashards**
across the campaign to unlock the true ending — the one where KAI comes
home.

### Hall of fame

Every node you clear posts your best career score, furthest node and
shard count to the server-wide leaderboard — press `L` on the sector or
node screen to see the standings, your row highlighted, your rank shown
even when you're outside the top 10. The victory screen prints your
final hall-of-fame rank and the session death count (a flawless descent
is called out). THE DAILY GAUNTLET keeps its own per-day board. One
JSON file per board under the save directory; corrupt files degrade to
an empty board, never a crashed session.

The title screen shows how many runners are currently jacked in.

### Codex

Press `C` on the sector or node screen. 22 entries decrypt as you
progress: faction lore, dossiers for all six ICE kinds, the EMP array,
the Wire, the Daily Gauntlet - and the truth about ORACLE-9.

## Architecture

```
main.py            entry point (asyncio + signal handling)
qgrid/
  assets.py        unicode glyph theme, block-letter banner font, art motifs
  lore.py          sectors, node beats, codex, endings, MIRAGE transmissions
  level_data.py    GENERATED: 48 BFS-verified levels (do not hand-edit)
  levels.py        LevelDef/layout model, ASCII grid parser + border validation
  physics.py       ray-tracing engine (mirrors, splitter prisms, loop guard)
  enemies.py       ICE daemon AI (sentinel / hunter / corruptor / wraith /
                   lancer / volt, stun, knockback, pulse fields, threat map)
  solver.py        BFS solver over (player, mirror-state) space, teleport-aware,
                   optional danger-cell blocking for live-ICE planning
  game.py          game state, turns, ICE strikes, shards, teleports, scoring
  audio.py         8-bit chiptune engine (bell tones, songs, SFX, modes)
  audio_client.py  companion player: PTY bridge + local square-wave synth
  bot.py           adaptive live-ICE playthrough bot (danger-aware re-planning agent)
  render.py        adaptive full-terminal ANSI frames, 2x2 upscaling, VFX
  save.py          per-username JSON persistence
  leaderboard.py   server-wide hall of fame (campaign + per-day boards)
  daily.py         THE DAILY GAUNTLET (date-seeded shared node, cached)
  generator.py     constructive level generator core (BFS-verified)
  server.py        asyncssh server, session state machine, raw input handling
tests/             unit + solver + live-ICE bot + campaign verification tests
scripts/
  generate_levels.py   procedural generator CLI (constructive + BFS-verified)
  smoke_test.py        end-to-end: boots the server, plays Node 01 over SSH
  full_playthrough.py  beats all 48 nodes over SSH via BFS-optimal solutions
```

- **Concurrency:** one independent asyncio session per SSH connection.
- **Rendering:** cursor-home frame redraws (`\033[H` + `\033[K` per row);
  full clears only on screen transitions.
- **Input:** 1-byte non-blocking reads; ANSI escape sequences (arrow keys)
  are consumed and mapped to WASD.
- **Level generation (constructive):** beam paths are built first —
  emitters, turn-point mirrors and splitter prisms, receptors on the path —
  which guarantees solvability by construction. Walls, pads, shards, ICE
  spawns, probe and extraction node are placed off-path; a subset of
  mirrors starts flipped. Every candidate is re-verified with the BFS
  solver (solvable, optimal within the sector's band, not already solved,
  shards reachable, ICE-heavy levels capped short) before acceptance.
  Corruptors never spawn beside a mirror - they have to travel to reach
  one, which gives runners stability windows.
- **Solver performance:** the BFS only evaluates the beam trace for states
  where the player stands on the extraction node.

## Testing

```bash
python -m pytest tests/ -q          # unit + solver + all-48 live-ICE bot + campaign
python scripts/audit_levels.py      # full audit: solvable, pars, shards, ICE bot
python scripts/smoke_test.py        # end-to-end over real SSH (port 2299)
python scripts/full_playthrough.py  # full 48-node campaign over real SSH
python scripts/generate_levels.py   # regenerate level data (seed 2099)
```

## Deployment (VPS)

```bash
pip install -r requirements.txt
python main.py --host 0.0.0.0 --port 2222
```

systemd unit (`/etc/systemd/system/qgrid.service`):

```ini
[Unit]
Description=Quantum Grid 2099 SSH game server
After=network.target

[Service]
WorkingDirectory=/opt/qgrid
ExecStart=/usr/bin/python3 /opt/qgrid/main.py --host 0.0.0.0 --port 2222
Restart=always
User=qgrid

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable --now qgrid
```

Players then connect with `ssh -p 2222 <your-vps-ip>` — any username works,
and each username keeps its own save.

*The Grid keeps count even when you can't. Jack back in.*
