# QUANTUM GRID 2099 — BLACKOUT PROTOCOL

A cyberpunk laser-reflection puzzle game played entirely over SSH — now with
live ICE daemons, splitter prisms, teleport arrays, datashards, persistent
saves, a 16-entry codex and two endings.

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

## The Campaign

| Sector | Name | Nodes | Introduces |
| --- | --- | --- | --- |
| 01 | THE SPINE | 1–8 | Mirrors, receptors, bandwidth |
| 02 | NEON DISTRICT | 9–16 | Splitter prisms, Director Vex |
| 03 | ICE FOUNDRY | 17–24 | SENTINEL + HUNTER daemons |
| 04 | THE MAZE | 25–32 | Teleport pad arrays |
| 05 | BLACK VAULT | 33–40 | CORRUPTOR daemons, heavy ICE mixes |
| 06 | SINGULARITY CORE | 41–48 | Everything at once, the Grid's heart |

Every node is procedurally generated, BFS-verified solvable, and shows its
par (optimal action count) after extraction.

## Controls

| Key | Action |
| --- | --- |
| `W A S D` / arrow keys | Move the light-beam probe |
| `R` | Rotate an adjacent (or underfoot) mirror |
| `K` | Restart the current node (restores entry bandwidth) |
| `C` | Open the codex (from sector / node select) |
| `1`–`6` | Pick a sector |
| `1`–`8` | Pick a node within a sector |
| `ENTER` | Continue: next uncleared node |
| `Q` | Disconnect |

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
| `Ψ` | CORRUPTOR ICE | flips a nearby mirror, then backs off |
| `▓` | Wall | blocks beams, movement and daemons |
| `Ω` | Extraction node | step here with all receptors powered to win |

### Beam optics

Every action re-runs the ray tracer from each emitter. Mirrors bend the
beam 90 degrees, splitter prisms fork it into two perpendicular beams,
receptors are powered and let light pass. The player absorbs any beam it
stands in. Loop protection (including through prism forks) prevents
infinite traces. Beams pass through shards, pads and daemons — light
doesn't care about software.

### Bandwidth

Every move or rotation consumes **1%**. **ICE strikes cost 25%**. Hit 0%
and the session severs (game over — progress is saved). Bandwidth
refreshes to 100% after every node; `K` restores what you entered with.

### ICE combat

Daemons act on every successful player action (turn-based):

- **Contact costs 25% bandwidth.** The striking daemon is knocked back a
  cell and stunned 4 ticks; a stunned daemon is walkable (safe to pass).
- Walking **into** live ICE also triggers a strike — the daemon is shoved
  along your path. You can always push through a blocker, at a price.
- **Sentinels** never chase; learn their lane. **Hunters** are slower than
  you — outrun them, break line of sight. **Corruptors** flip a mirror and
  back off for a few ticks — race them, then restore your optics.
- The BFS solver intentionally ignores ICE: it verifies the laser puzzle.
  Beating a node *with* live daemons is the real game.

### Scoring & endings

Per node: `bandwidth×10 + shards×250 + efficiency bonus (par)`. Scores
bank into a persistent run total; final rank ranges from SCRIPT KIDDIE to
LEGEND OF THE GRID. Bank **90% of all datashards** across the campaign to
unlock the true ending — the one where KAI comes home.

### Codex

Press `C` on the sector or node screen. 16 entries decrypt as you
progress: faction lore, daemon dossiers, and the truth about ORACLE-9.

## Architecture

```
main.py            entry point (asyncio + signal handling)
qgrid/
  assets.py        unicode glyph theme, block-letter banner font, art motifs
  lore.py          sectors, node beats, codex, endings, MIRAGE transmissions
  level_data.py    GENERATED: 48 BFS-verified levels (do not hand-edit)
  levels.py        LevelDef/layout model, ASCII grid parser + border validation
  physics.py       ray-tracing engine (mirrors, splitter prisms, loop guard)
  enemies.py       ICE daemon AI (sentinel / hunter / corruptor, stun, knockback)
  solver.py        BFS solver over (player, mirror-state) space, teleport-aware
  game.py          game state, turns, ICE strikes, shards, teleports, scoring
  render.py        adaptive full-terminal ANSI frames + all screens
  save.py          per-username JSON persistence
  server.py        asyncssh server, session state machine, raw input handling
tests/             unit + solver + live-ICE bot + campaign verification tests
scripts/
  generate_levels.py   procedural generator (constructive + BFS-verified)
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
  shards reachable, hunter levels capped short) before acceptance.
- **Solver performance:** the BFS only evaluates the beam trace for states
  where the player stands on the extraction node.

## Testing

```bash
python -m pytest tests/ -q          # unit + solver + live-ICE bot + campaign
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
