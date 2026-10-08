# QUANTUM GRID 2099

A cyberpunk laser-reflection puzzle game played entirely over SSH. You jack into
OMNICORP's corrupted Quantum Grid, operate a light-beam probe (`@`), rotate
optical mirrors (`/` `\`) and redirect laser fire from emitters into receptors.
Power all receptors to unlock the extraction node — and watch your bandwidth.

**16 lore-driven nodes** across growing grids (24x11 up to 69x14), rendered in a
cyber-blue ANSI theme that fills your whole terminal: blue probe on black,
green laser fire, red emitters.

```
================================================================================
  QUANTUM GRID 2099 // MAINFRAME NODE 01 - FIRST LIGHT
  BANDWIDTH: [████████████████████] 100% | RECEPTORS: 0/1 [LOCKED]
================================================================================

                 ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
                 ▓·····························▓
                 ▓·▶────────────@\·············▓
                 ▓·····························▓
                 ▓············Ω···◉············▓
                 ▓·····························▓
                 ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓

  STATUS: Probe repositioned. Target node unpowered. Re-route beam line.
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
No authentication is required — anyone who connects gets a session.

### Command-line options

| Flag | Default | Description |
| --- | --- | --- |
| `--host` | `0.0.0.0` | Bind address |
| `--port` | `2222` | Listen port |
| `--host-key` | `ssh_host_key` | SSH host key path (generated if missing) |

### Environment

| Variable | Description |
| --- | --- |
| `QG_UNLOCK_ALL=1` | Unlock all sixteen nodes from the start (demo/judging mode) |

## Controls

| Key | Action |
| --- | --- |
| `W A S D` / arrow keys | Move the light-beam probe |
| `R` | Rotate an adjacent (or underfoot) mirror |
| `K` | Restart the current node (restores entry bandwidth) |
| `Q` | Disconnect |
| `1`-`16` / `ENTER` | Select a node (two-digit numbers buffered) |

## Mechanics

### Grid symbols

| Symbol | Entity | Color |
| --- | --- | --- |
| `@` | Player probe | bright blue on black |
| `▶` `◀` `▲` `▼` | Laser emitters | bright red |
| `◉` | Target receptor | yellow (bright yellow when powered) |
| `/` `\` | Optical mirrors | bright cyan |
| `─` `\|` | Propagated laser fire | bright green (`┼` where beams cross) |
| `▓` | Mainframe wall | blue (blocks beams and movement) |
| `Ω` | Extraction node | dim gray when locked, flashing white when active |
| `·` | Empty floor | dark gray on black |

### Beam optics

Every action re-runs the ray tracer from each emitter. Mirrors bend the beam
90 degrees:

- `/`: right→up, left→down, up→right, down→left
- `\`: right→down, left→up, up→left, down→right

Receptors are powered by the beam and let it pass through. The player probe
absorbs any beam it stands in — including the beam feeding a receptor further
down the trail. Beams stop at walls, at the grid border, or if they re-enter
the same cell in the same direction (loop protection).

### Bandwidth

Every successful move or rotation consumes **1%**. Hitting **0%** severs the
session (game over). **Bandwidth refreshes to 100% after every level** — each
node boots with a full charge. `K` restores the bandwidth you entered the node
with, so resets are always free.

### Full-terminal rendering

Frames are drawn to the client's actual terminal size (minimum 80x24) and
fill the whole window: full-width rules, the grid vertically centered between
the header and the status bar. Terminal size is re-read every frame, so
resizing mid-game re-flows instantly.

## Lore

2099. OMNICORP's Quantum Grid owns the city — power, traffic, data, everything.
You are a netrunner with a light-beam probe and a debt to settle. Every node
has its own story beat, shown when you jack in: from the tutorial hatch of
**FIRST LIGHT** through the firewall gauntlets of **OVERCLOCK** and **DEEP
GRID**, down to the grid's heart in **SINGULARITY**.

## The Sixteen Nodes

| # | Node | Grid | Mirrors | Receptors | Optimal |
| --- | --- | --- | --- | --- | --- |
| 01 | FIRST LIGHT | 24x11 | 1 | 1 | 14 |
| 02 | COLD BOOT | 27x11 | 1 | 1 | 30 |
| 03 | THE CORNERING | 30x11 | 2 | 1 | 28 |
| 04 | DEAD SECTOR | 33x11 | 2 | 1 | 18 |
| 05 | SPLIT FOCUS | 36x11 | 3 | 2 | 33 |
| 06 | GHOST PROTOCOL | 39x12 | 3 | 2 | 48 |
| 07 | NEON MAZE | 42x12 | 4 | 2 | 34 |
| 08 | BLACKOUT | 45x12 | 4 | 2 | 44 |
| 09 | FIREWALL | 48x12 | 5 | 3 | 45 |
| 10 | OVERCLOCK | 51x12 | 5 | 3 | 57 |
| 11 | DARK FIBER | 54x13 | 6 | 3 | 65 |
| 12 | ZERO DAY | 57x13 | 6 | 3 | 39 |
| 13 | TERMINAL VELOCITY | 60x13 | 7 | 4 | 88 |
| 14 | DEEP GRID | 63x13 | 8 | 4 | 86 |
| 15 | CORE MAINFRAME | 66x13 | 9 | 4 | 62 |
| 16 | SINGULARITY | 69x14 | 8 | 4 | 79 |

(Optimal = BFS-verified shortest action count.)

## Architecture

```
main.py            entry point (asyncio + signal handling)
qgrid/
  assets.py        unicode glyph theme, block-letter banner font, art motifs
  level_data.py    GENERATED: 16 BFS-verified levels + lore (do not hand-edit)
  levels.py        LevelDef/layout model, ASCII grid parser + border validation
  physics.py       ray-tracing engine (emitters, mirrors, receptors, loops)
  solver.py        BFS solver over (player, mirror-state) space
  game.py          game state, movement, bandwidth, win/lose logic
  render.py        adaptive full-terminal ANSI frames + all screens
  server.py        asyncssh server, session state machine, raw input handling
tests/             unit + solver-driven playthrough + level verification tests
scripts/
  generate_levels.py   procedural level generator (constructive + BFS-verified)
  smoke_test.py        end-to-end test: boots the server, plays Node 01 over SSH
  full_playthrough.py  beats all 16 nodes over SSH via BFS-optimal solutions
```

- **Concurrency:** one independent asyncio session per SSH connection.
- **Rendering:** cursor-home frame redraws (`\033[H` + `\033[K` per row); full
  clears only on screen transitions.
- **Input:** 1-byte non-blocking reads; ANSI escape sequences (arrow keys)
  are consumed and mapped to WASD. The server disables its line editor/echo
  (`line_editor=False, line_echo=False`) so keystrokes arrive raw.
- **Level generation (constructive):** a random beam path is built first —
  emitters, turn-point mirrors, receptors on the path — which guarantees
  solvability by construction. Walls, probe and extraction node are placed
  off-path; a difficulty-scaled subset of mirrors starts flipped. Every
  candidate is re-verified with the BFS solver (solvable, optimal within the
  tier's difficulty band, not already solved) before being accepted.
- **Solver performance:** the BFS only evaluates the beam trace for states
  where the player stands on the extraction node, keeping full-campaign
  verification under five seconds.

## Testing

```bash
python -m pytest tests/ -q        # unit + solver + level tests
python scripts/smoke_test.py      # end-to-end over real SSH (port 2299)
python scripts/full_playthrough.py  # full 16-node campaign over real SSH
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

Players then connect with `ssh -p 2222 <your-vps-ip>` — any username works.
