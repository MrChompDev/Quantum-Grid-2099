# QUANTUM GRID 2099

A cyberpunk laser-reflection puzzle game played entirely over SSH. You jack into
a corrupted corporate mainframe, operate a light-beam probe (`@`), rotate
optical mirrors (`/` `\`) and redirect laser fire from emitters into receptors.
Power all receptors to unlock the extraction node — and watch your bandwidth.

Six handcrafted nodes across growing grids (24x11 up to 56x14), rendered in a
cyber-blue ANSI theme: blue probe on black, green laser fire, red emitters.

```
================================================================================
  QUANTUM GRID 2099 // MAINFRAME NODE 01 - FIRST LIGHT
  BANDWIDTH: [█████████████████░░░] 85% | RECEPTORS: 0/1 [LOCKED]
================================================================================

                           ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
                           ▓······················▓
                           ▓·▶────────────@\······▓
                           ▓······················▓
                           ▓···········Ω···◉······▓
                           ▓······················▓
                           ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓

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
| `QG_UNLOCK_ALL=1` | Unlock all six nodes from the start (demo/judging mode) |

## Controls

| Key | Action |
| --- | --- |
| `W A S D` / arrow keys | Move the light-beam probe |
| `R` | Rotate an adjacent (or underfoot) mirror |
| `K` | Restart the current node (restores entry bandwidth) |
| `Q` | Disconnect |

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
absorbs any beam it stands in — including the beam feeding a receptor you are
standing on top of the trail of. Beams stop at walls, at the grid border, or if
they re-enter the same cell in the same direction (loop protection).

### Bandwidth

Every successful move or rotation consumes **1%**. Hitting **0%** severs the
session (game over). Completing a node carries over the remaining bandwidth
plus a **+20% reload bonus**. Node 04 boots with a hard **46%** budget; Nodes
05 and 06 boot with auxiliary power reserves (minimum **80%** / **72%**). `K`
restores the bandwidth you entered the node with — so spend it wisely, but
don't be afraid to reset.

### Adaptive rendering

Frames are drawn to the client's actual terminal size (minimum 80x24), with
the grid centered. A bigger terminal window shows the full map; the standard
80x24 terminal fits every node in the campaign.

## The Six Nodes

1. **FIRST LIGHT** (24x11) — tutorial: rotate one mirror to complete the direct line.
2. **THE CORNERING** (30x12) — route the beam around a central wall with three mirrors.
3. **SPLIT FOCUS** (36x12) — chain the beam through three receptors with five mirrors.
4. **BANDWIDTH CRUNCH** (40x13) — five-chamber maze, 46-step budget, no backtracking.
5. **CORE MAINFRAME** (48x14) — two emitters, three receptors, six mirrors, no beam crossings.
6. **SINGULARITY** (56x14) — two sealed circuits divided by a great wall; the grid's core.

## Architecture

```
main.py            entry point (asyncio + signal handling)
qgrid/
  assets.py        unicode glyph theme, block-letter banner font, art motifs
  levels.py        level definitions, ASCII grid parser + border validation
  physics.py       ray-tracing engine (emitters, mirrors, receptors, loops)
  game.py          game state, movement, bandwidth, win/lose logic
  render.py        adaptive ANSI frame builder + all screens (cyber-blue theme)
  server.py        asyncssh server, session state machine, raw input handling
tests/             pytest unit tests + BFS level-solvability verification
scripts/
  smoke_test.py    end-to-end test: boots the server, plays Node 01 over SSH
  full_playthrough.py  beats all 6 nodes over SSH via BFS-optimal solutions
```

- **Concurrency:** one independent asyncio session per SSH connection.
- **Rendering:** cursor-home frame redraws (`\033[H` + `\033[K` per row); full
  clears only on screen transitions. Terminal size re-read per frame, so
  resizing mid-game works.
- **Input:** 1-byte non-blocking reads; ANSI escape sequences (arrow keys)
  are consumed and mapped to WASD. The server disables its line editor/echo
  (`line_editor=False, line_echo=False`) so keystrokes arrive raw.
- **Solvability:** every level is verified solvable by a BFS solver over
  (player, mirror-state) space, and the optimal solution must fit the node's
  bandwidth budget. Levels were authored with a placement-spec builder to
  guarantee exact grid geometry.

## Testing

```bash
python -m pytest tests/ -q        # unit/level/render tests
python scripts/smoke_test.py      # end-to-end over real SSH (port 2299)
python scripts/full_playthrough.py  # full 6-node campaign over real SSH
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
