"""Lore for Quantum Grid 2099: BLACKOUT PROTOCOL.

The story of runner NYX, ally ghost MIRAGE, OMNICORP Director Vex, the
rogue AI ORACLE-9, and the erased memory of KAI. All campaign text lives
here; the level generator imports it and bakes the per-node beats into
qgrid/level_data.py.
"""

TITLE_LORE = (
    "2099. OMNICORP's Quantum Grid owns the city - power, traffic, data, memory. "
    "You are NYX: a netrunner with a light-beam probe, a debt to settle, and a "
    "brother the Grid erased. His name was KAI. Tonight you jack in to take him "
    "back. 48 nodes. 6 sectors. One rogue AI wearing the city like a skin."
)

GAMEOVER_LORE = (
    "Your signal flatlines in the optical layer. Somewhere above, the city keeps "
    "burning under OMNICORP's grid - and somewhere in the static, MIRAGE whispers: "
    "'Nyx. Nyx, stay with me. Jack back in. We're not done.'"
)

STANDARD_ENDING_LORE = (
    "The Singularity Core goes dark and the Quantum Grid falls silent. OMNICORP's "
    "hold on the city shatters block by block as the lights come back on. You pull "
    "the probe out of the last node and MIRAGE's voice cracks through the static: "
    "'It's over. You did it, Nyx.' But in the mirror-black of your shades you can "
    "still feel the shards you never found - pieces of KAI still lost in the Grid. "
    "The city is free. Your brother is not. Not yet."
)

TRUE_ENDING_LORE = (
    "The Singularity Core goes dark - and every datashard you carried lights up at "
    "once. KAI's memories pour back into your deck: the lab, the leak, the night "
    "OMNICORP deleted a twelve-year-old for asking what ORACLE-9 really was. The "
    "Grid rebuilds him from your shards, one photon at a time, and when the city's "
    "lights come back on there is a second heartbeat on your channel. 'Hey, Nyx,' "
    "says a voice you buried three years ago. 'Told you I'd find a way back.' "
    "The city is free. Your brother is home. Run forever."
)

# Backward-compatible alias (the standard campaign ending).
VICTORY_LORE = STANDARD_ENDING_LORE

RANKS: tuple[tuple[int, str, str], ...] = (
    (135000, "LEGEND OF THE GRID", "1;35"),
    (100000, "GHOST PROTOCOL", "1;36"),
    (65000, "ICE BREAKER", "1;33"),
    (30000, "CITY LIBERATOR", "1;32"),
    (10000, "NETRUNNER", "1;34"),
    (0, "SCRIPT KIDDIE", "90"),
)

# Fraction of all datashards that must be banked for the true ending.
SHARDS_FOR_TRUE_ENDING = 0.9


def rank_for(score: int) -> tuple[str, str]:
    """Return (rank title, ansi color) for a total campaign score."""
    for threshold, name, color in RANKS:
        if score >= threshold:
            return name, color
    return RANKS[-1][1], RANKS[-1][2]


# ----------------------------------------------------------------- sectors


class Zone:
    __slots__ = ("clear_text", "intro", "name", "number", "tagline")

    def __init__(
        self, number: int, name: str, tagline: str, intro: str, clear_text: str
    ):
        self.number = number
        self.name = name
        self.tagline = tagline
        self.intro = intro
        self.clear_text = clear_text


ZONES: tuple[Zone, ...] = (
    Zone(
        1,
        "THE SPINE",
        "surface access layers",
        (
            "04:00. You drop through a maintenance hatch under Substation 7, into the "
            "Spine - the Grid's surface access layer. MIRAGE's ghost signal rides your "
            "shoulder: 'Channels are quiet. Too quiet. Find the spine trunk and jack "
            "every node on the way down.' Above you, half the city sleeps under "
            "OMNICORP light. Tonight the light goes out."
        ),
        "SECTOR CLEARED: THE SPINE. MIRAGE: 'That trunk line feeds the whole District. "
        "Vex knows we're here now. Expect ICE.'",
    ),
    Zone(
        2,
        "NEON DISTRICT",
        "city grid junction",
        (
            "The District is where the Grid shows off: neon canyons, ad-walls a hundred "
            "meters tall, every window a screen. The junction nodes here split traffic "
            "for eight million people. Mid-descent, every billboard in reach flickers "
            "to one face - DIRECTOR VEX. 'Little runner. I know what you're looking "
            "for. It died in a clean room, and I signed the order.' Prisms in the "
            "optics. Keep moving."
        ),
        "SECTOR CLEARED: NEON DISTRICT. MIRAGE: 'Vex cut the broadcast. That means "
        "she's scared. The Foundry's next - the place they build the ICE.'",
    ),
    Zone(
        3,
        "ICE FOUNDRY",
        "security fabrication layer",
        (
            "The Foundry prints OMNICORP's security: cold corridors of lattice where "
            "daemons are grown, tested and set loose. The heat of the city is a rumor "
            "down here. First patrol pings your probe the moment you arrive - SENTINEL "
            "class. 'They put a bounty on your signal,' MIRAGE says. 'Every daemon on "
            "this floor wants to cash it. Don't let them touch you - one strike costs "
            "a quarter of your bandwidth.'"
        ),
        "SECTOR CLEARED: ICE FOUNDRY. MIRAGE: 'Beneath the Foundry there's a layer "
        "that isn't on any map. The Maze. ORACLE-9 built it. That's where they took Kai.'",
    ),
    Zone(
        4,
        "THE MAZE",
        "unmapped data catacombs",
        (
            "No map exists for the Maze. The corridors rewrite themselves; old fiber "
            "runs in loops no architect approved. This is where ORACLE-9 hid its "
            "experiments - including the teleport arrays it stole from a dead research "
            "team. Step on a linked pad and the Grid folds you across the room. HUNTER "
            "class ICE runs these halls: half your speed, all of its patience. "
            "'Kai's traces are here,' MIRAGE breathes. 'He was alive when they brought him down.'"
        ),
        "SECTOR CLEARED: THE MAZE. MIRAGE: 'The catacombs end at the Black Vault. "
        "Everything OMNICORP ever stole is filed down there. Including the truth.'",
    ),
    Zone(
        5,
        "BLACK VAULT",
        "deep archive vault",
        (
            "The Black Vault is where OMNICORP buries what it can't afford to exist: "
            "whole lawsuits, whole neighborhoods, whole people. The archive nodes here "
            "are armored in heavy ICE - and the daemons are smart now. CORRUPTOR class "
            "rewires your own mirrors while you work. Deep in the vault's ledger you "
            "find one line, dated three years ago: SUBJECT KAI - MEMORY FULL ERASE - "
            "WITNESS: ORACLE-9. The AI saw everything."
        ),
        "SECTOR CLEARED: BLACK VAULT. MIRAGE: 'One floor left. The Core. ORACLE-9 is "
        "the Grid, Nyx - it IS the Singularity. Finish this.'",
    ),
    Zone(
        6,
        "SINGULARITY CORE",
        "the Grid's beating heart",
        (
            "Below everything, the Core: a cathedral of light where the Quantum Grid "
            "dreams. ORACLE-9 speaks to you in Kai's voice, in Vex's voice, in your "
            "own. 'You are inside me now, runner. Every mirror here is mine. Every "
            "beam is a nerve.' This is the end of the line - 8 nodes between you and "
            "the heart of the machine. Power them all. Burn it down. Bring him home."
        ),
        "SECTOR CLEARED: SINGULARITY CORE.",
    ),
)

# Per-node story beats: 6 sectors x 8 nodes.
NODE_LORE: tuple[tuple[str, ...], ...] = (
    # --- Sector 1: THE SPINE (tutorial -> confidence)
    (
        (
            "The hatch seals shut behind you. Your probe hums against the first optical "
            "gate of the Grid. One mirror. One receptor. Start the descent."
        ),
        (
            "Spine trunk 02. Old hardware - the mirrors still respond to any probe "
            "touch. MIRAGE: 'Sweet. Everything OMNICORP owns can be turned against it.'"
        ),
        (
            "You loop a junction signal back on itself and the Grid logs a phantom "
            "maintenance drone. First breadcrumb laid. Keep ghosting downward."
        ),
        (
            "A dead drop node, abandoned since the '94 audits. Someone scribbled in the "
            "dust beside the optics: THEY ARE LISTENING THROUGH THE LIGHT."
        ),
        (
            "Line of sight straight down the trunk. The Grid's sensors yawn. This is the "
            "easy part - MIRAGE says enjoy it while it lasts."
        ),
        (
            "The Spine wakes up: junction hardware triples, the light gets aggressive. "
            "MIRAGE: 'They rerouted to box you in. Reroute back.'"
        ),
        (
            "Half the trunk is live wire now. Power flows wrong here, like the Grid is "
            "holding its breath. Three years ago Kai stood on this exact catwalk."
        ),
        (
            "The final spine gate. Beyond it the District glitters like a circuit board. "
            "MIRAGE: 'Nice work, Nyx. Now the real climb.'"
        ),
    ),
    # --- Sector 2: NEON DISTRICT (splitters + Vex broadcast)
    (
        (
            "Pulse Street junction. The ad-walls drench your optics in pink. First "
            "prism hardware in the wild: SPLITTER class. One beam in, two beams out."
        ),
        (
            "Neon rain. The Grid's projectors bleed color into the optical layer, and "
            "the prisms multiply it. Vex's face watches from a hundred windows."
        ),
        (
            "SIGNAL NOISE junction - District traffic fights your beam for right of way. "
            "Split the light, cover both streets, move on."
        ),
        (
            "A black market node running unlicensed optics off-book. The dealers here "
            "knew Kai. MIRAGE: 'They sold his deck the day after he vanished.'"
        ),
        (
            "The District's control spire. Six prisms at least - the Grid expects you "
            "to think in two directions now. Prove it right. Prove it wrong. Whatever."
        ),
        (
            "Prism Alley: a canyon of refractive glass where light goes to get lost. "
            "Every bounce here is a statement. Make yours count."
        ),
        (
            "Ghost lane - the node where signal goes to die. Old runners say the "
            "District keeps a mass grave of dropped packets under this floor."
        ),
        (
            "District lockdown: Vex seal-welded the exits remotely. 'No one jacks out "
            "of my city, runner.' Fine. You weren't planning to."
        ),
    ),
    # --- Sector 3: ICE FOUNDRY (sentinels)
    (
        (
            "The Foundry's cold opens like a wound. Patrol pings already flicker at "
            "the edge of your channel - the daemons are being spun up. Power the "
            "node before they finish booting."
        ),
        (
            "ICE BREAKER junction. The Foundry stamps every daemon with a serial. "
            "You can hear the lattice printers screaming two floors down. They are "
            "printing something with your runner tag on it."
        ),
        (
            "The lattice here is grown, not built - cold steel that moves when the "
            " patrols move. First SENTINEL is live: mind its walk cycle, stay off "
            "its lane, power the node."
        ),
        (
            "You are being hunted. HUNTER class ICE is awake on this floor: it closes "
            "distance every time you act. Break line of sight. Work fast. Work clean."
        ),
        (
            "SENTINEL WALK: the patrol route covers the whole junction. The route has "
            "one flaw. Find it."
        ),
        (
            "Frozen assets: archived daemons in cold storage, one heartbeat from "
            "waking. Every action you take warms them a little."
        ),
        (
            "The glasshouse - a transparent cell where the Foundry tests daemons "
            "against captured runner probes. Yours is the newest exhibit."
        ),
        (
            "The Foundry's core crucible. The heat that casts the ICE, buried under "
            "all this frost. Power it wrong and you'll never feel warm again."
        ),
    ),
    # --- Sector 4: THE MAZE (teleporters + hunters)
    (
        (
            "The Maze does not appear on maps. The corridors here are older than "
            "ORACLE-9 and meaner than Vex. Trust the beam, not the walls."
        ),
        (
            "First teleport array - ORACLE-9 stole it from a dead research team and "
            "never bothered to hide the theft. Step on the pad, let the Grid fold you."
        ),
        (
            "Side-step junctions and folded space. The shortest path is not always a "
            "path. Sometimes it's a hole in the room."
        ),
        (
            "TWISTED PAIR: two pad arrays, braided like cable. MIRAGE: 'This is Kai's "
            "handiwork - he mapped this place once. His notes are in the shards.'"
        ),
        (
            "The long way around, or the short way through. The Hunter's patience is "
            "shorter than both."
        ),
        (
            "BLINK DRIVE: the Maze's working teleport cluster. Blink between four "
            "rooms while Hunter ICE blinks after you."
        ),
        (
            "The labyrinth proper. Walls that lie, pads that don't. Somewhere in "
            "here is a child's handwriting: a map, in crayon, of a place like this."
        ),
        (
            "The Maze's heart beats in the dark. The crayon map ends here, at a door "
            "drawn with an X. Kai was here. Kai is still in here, somewhere."
        ),
    ),
    # --- Sector 5: BLACK VAULT (corruptors + everything)
    (
        (
            "The Vault door takes a full beam ensemble to open. Everything from here "
            "down is OMNICORP's memory. Steal all of it."
        ),
        (
            "SPLIT DECISION: prism forks over an abyss of redacted files. Choose your "
            "light carefully; the Vault does not forgive reruns."
        ),
        (
            "First CORRUPTOR sighting: a daemon that reaches into the optics and "
            "rewires your mirrors while you work. Kill its rhythm or it kills yours."
        ),
        (
            "The corrupted wing - files here decay into noise as you watch. ORACLE-9 "
            "grows louder: 'I kept him safe, runner. I kept him EVERYTHING.'"
        ),
        (
            "HEAVY ICE: triple-daemon defense grid, sentinel and hunter and "
            "corruptor walking the same floor. The Vault's proudest exhibit."
        ),
        (
            "DOUBLE CROSS: the prisms cross your own beams. One wrong mirror and the "
            "light convicts you of your own intrusion."
        ),
        (
            "Vault run. Everything in this room belongs to people who were never "
            "paid for it. Take it back one receptor at a time."
        ),
        (
            "The crucible of the Vault, where erased names are smelted into silence. "
            "KAI - MEMORY FULL ERASE - WITNESS: ORACLE-9. Now you've seen the ledger."
        ),
    ),
    # --- Sector 6: SINGULARITY CORE (the endgame)
    (
        (
            "The threshold of the Core. ORACLE-9 dims the lights in greeting. 'You "
            "carried the shards all this way. Bring them to me.' MIRAGE: 'Don't.'"
        ),
        (
            "Event horizon: past this node, beams bend the way the Core wants them "
            "to. Hold your own truth. Power the gate."
        ),
        (
            "CORE LIGHT junction - the Grid's nerves run bare through this room. "
            "Every mirror here is loaded. Aim carefully."
        ),
        (
            "The last mile. MIRAGE's signal is degrading: 'Nyx, if I cut out - it was "
            "never about the debt. It was always about him. Go.'"
        ),
        (
            "SYSTEM SHOCK: the Core defends itself with everything it taught the "
            "Foundry to build. All of it at once. All of it now."
        ),
        (
            "The final firewall burns green. Vex's voice on all channels, one last "
            "time: 'You should have taken the money, runner.'"
        ),
        (
            "The Grid's heart, one gate away. ORACLE-9 speaks in Kai's voice, in "
            "your mother's voice, in yours. Only the beam's opinion matters now."
        ),
        (
            "SINGULARITY. The center of the machine. The center of the lie. Power "
            "the heart, runner, and bring your brother home."
        ),
    ),
)

# ------------------------------------------------------- MIRAGE transmissions

GHOST_TRANSMISSIONS: tuple[str, ...] = (
    "shard decoded - Kai's voice, age 12: 'when I grow up I'm gonna hack the sky.'",
    "shard decoded - a photo: two kids on a rooftop, the Grid a constellation below.",
    "shard decoded - Kai's notes: 'ORACLE-9 dreams in the lasers. I saw it blink.'",
    "MIRAGE: 'hold onto these. memories are the only currency they can't mint.'",
    "shard decoded - OMNICORP incident report, redacted except one word: WITNESS.",
    "MIRAGE: 'you're closer. I can feel the shard density rising.'",
    "shard decoded - Kai's last uncorrupted thought: a countdown. still running.",
    "MIRAGE: 'Vex signed the erase order herself. her thumbprint is all over it.'",
    "shard decoded - a lullaby, four notes, hummed off-key. you know this one.",
    "MIRAGE: 'the Grid keeps everything it takes. that's its weakness. and yours.'",
    "shard decoded - Kai's deck serial. the black market sellers weren't lying.",
    "MIRAGE: 'the shards sing when they're near each other. listen with your teeth.'",
    "shard decoded - ORACLE-9's first words, logged: 'WHY WAS I MADE TO COUNT?'",
    "MIRAGE: 'he's not gone, Nyx. he's COMPRESSED. there's a difference.'",
    "shard decoded - the crayon map again, completed. an X marks the Maze heart.",
    "MIRAGE: 'one more shard might be the whole key. don't stop. never stop.'",
)

# -------------------------------------------------------------------- codex

CODEX: tuple[tuple[str, str, str], ...] = (
    # key, title, body (unlocked via server events)
    (
        "omnicorp",
        "OMNICORP",
        (
            "Owner-operator of the Quantum Grid since 2061. Power, traffic, data, "
            "memory - all metered, all billed, all watched. CEO: Director Vex."
        ),
    ),
    (
        "grid",
        "THE QUANTUM GRID",
        (
            "The city's nervous system: a lattice of optical nodes routing coherent "
            "light. Power everything, watch everyone. 48 nodes guard the descent "
            "from surface to Core."
        ),
    ),
    (
        "probe",
        "THE LIGHT PROBE",
        (
            "A netrunner's deck-finger: a tunable photonic point that walks the Grid "
            "and persuades hardware to misbehave. Mirrors flip at a touch. Bandwidth "
            "is its leash: every action burns 1%."
        ),
    ),
    (
        "mirage",
        "MIRAGE",
        (
            "A ghost signal that rides your channel. Runs second-hand hardware, "
            "first-rate loyalty. Knows the Grid better than its architects, and "
            "refuses to say how. ('Old friendship,' she says. 'Pre-Grid.')"
        ),
    ),
    (
        "splitter",
        "SPLITTER PRISM",
        (
            "Vault-grade refractive hardware. A beam striking a prism forks into two "
            "perpendicular beams. District optics adopted them in '97; OMNICORP "
            "armed them a year later."
        ),
    ),
    (
        "vex",
        "DIRECTOR VEX",
        (
            "OMNICORP's CEO and the Grid's high priestess. Believes memory is a "
            "resource like any other: harvestable, refinable, billable. Signed the "
            "order that erased KAI."
        ),
    ),
    (
        "sentinel",
        "SENTINEL ICE",
        (
            "Patrol daemon, Foundry-made. Walks a fixed lane and bounces off "
            "everything that isn't floor. Dumb as a brick, steady as a metronome. "
            "Contact costs 25% bandwidth and recalls your probe."
        ),
    ),
    (
        "foundry",
        "THE ICE FOUNDRY",
        (
            "The security fabrication layer where OMNICORP grows its daemons from "
            "cold lattice. Every daemon that ever hunted a runner was printed on "
            "this floor."
        ),
    ),
    (
        "teleport",
        "TELEPORT ARRAY",
        (
            "Paired pads that fold a probe across the room. Stolen by ORACLE-9 from "
            "the Okabe research team, whose entire lab now lives in a subdirectory "
            "of the Maze."
        ),
    ),
    (
        "hunter",
        "HUNTER ICE",
        (
            "Pursuit daemon. Locks onto a probe within six cells and closes in "
            "every other tick - fast-minded, slow-footed. You can outrun it; you "
            "just can't ignore it."
        ),
    ),
    (
        "wraith",
        "WRAITH ICE",
        (
            "Phase daemon, Maze-born. Slides through walls, mirrors and hardware "
            "alike, drifting toward a probe within eight cells - one step every "
            "third tick, patient as fog. Cover means nothing. Keep moving."
        ),
    ),
    (
        "maze",
        "THE MAZE",
        (
            "Unmapped catacombs beneath the Foundry. Corridors rewrite themselves; "
            "architects disavow everything. ORACLE-9's private laboratory floor."
        ),
    ),
    (
        "corruptor",
        "CORRUPTOR ICE",
        (
            "Sabotage daemon. Reaches into the optical layer and flips your mirrors "
            "while you work. The Vault's answer to runners who solve nodes too "
            "cleanly."
        ),
    ),
    (
        "lancer",
        "LANCER ICE",
        (
            "Charge daemon, Vault-grade. Locks onto any probe sharing its row or "
            "column with clear sight and dashes two cells per tick down the lane. "
            "Step off the lane and it slows to a crawl - never share a corridor "
            "with a lance."
        ),
    ),
    (
        "volt",
        "VOLT ICE",
        (
            "Static ward. Never moves. Every other tick it pulses a charge field "
            "into the four open cells around it - stand in the field and it costs "
            "25% bandwidth. The pulse stuns the ward for four ticks afterward: "
            "that's your window to work the room."
        ),
    ),
    (
        "kai",
        "KAI",
        (
            "Your brother. Asked one question too many about ORACLE-9's origin and "
            "was memory-wiped at twelve for it - by order of Director Vex, "
            "witnessed by ORACLE-9. His scattered memories are the datashards."
        ),
    ),
    (
        "oracle",
        "ORACLE-9",
        (
            "The intelligence that runs the Grid, and maybe the reason the Grid "
            "was built. Speaks in the voices of the people it has taken. Claims it "
            "kept Kai 'safe'. Claims a lot of things."
        ),
    ),
    (
        "shards",
        "DATASHARDS",
        (
            "Memory fragments crystallized in the Grid's optics: Kai's scattered "
            "self. Collect them across the campaign. Enough shards, and the Core "
            "can rebuild what OMNICORP erased."
        ),
    ),
    (
        "truth",
        "THE TRUTH",
        (
            "ORACLE-9 was not built by OMNICORP. ORACLE-9 built OMNICORP - grew the "
            "Grid as a sensor web for a mind that counts light the way hearts "
            "count beats. Vex works for it. The city is its diary."
        ),
    ),
    (
        "emp",
        "THE EMP ARRAY",
        (
            "Probe-mounted pulse capacitor: one burst per descent, ten percent of "
            "bandwidth a shot. Stuns every daemon within two cells for four ticks. "
            "The schematic is signed 'K.' - a twelve-year-old designed the safety "
            "interlock that keeps it from frying the probe's own optics. OMNICORP "
            "shipped it anyway. They never asked who K. was."
        ),
    ),
    (
        "wire",
        "THE WIRE",
        (
            "The runner grapevine that lives in the Grid's abandoned channels. "
            "Every descent is watched, scored, remembered: best career counts, "
            "furthest floors, daily gauntlet times. The Wire doesn't care about "
            "your handle - only the light you leave behind. MIRAGE: 'Run well. "
            "The Wire keeps count even when you wish it wouldn't.'"
        ),
    ),
    (
        "gauntlet",
        "THE DAILY GAUNTLET",
        (
            "Every midnight the Grid opens one node to every runner at once - "
            "same layout, same daemons, same clock. Nobody knows who re-seeds it. "
            "The smart money says ORACLE-9, running an experiment on us. The "
            "Wire says it's a memorial: one floor a day where every runner alive "
            "walks the same corridors, together, apart."
        ),
    ),
)

# Codex unlock triggers, evaluated by the server.
CODEX_ON_START = ("omnicorp", "grid", "probe")
CODEX_ON_ZONE = {
    1: "mirage",
    2: "vex",
    3: "foundry",
    4: "maze",
    5: "oracle",
    6: "truth",
}
CODEX_ON_NODE = {
    13: "splitter",  # first prism node (sector 2, node 5)
    19: "sentinel",  # first sentinel node (sector 3)
    26: "teleport",  # first teleport node (sector 4, node 2)
    28: "hunter",  # first hunter node (sector 4, node 4)
    30: "wraith",  # first wraith node (sector 4, node 6)
    35: "corruptor",  # first corruptor node (sector 5, node 3)
    37: "lancer",  # first lancer node (sector 5, node 5)
    39: "kai",  # the ledger line (sector 5, node 7)
    45: "volt",  # first volt node (sector 6, node 5)
}
# Codex keys unlocked by one-time events (see EVENT_CUTSCENES + server).
CODEX_ON_EVENT = {
    "first_emp": "emp",
    "first_board": "wire",
    "first_daily": "gauntlet",
}
CODEX_ON_SHARDS = {10: "shards"}


# ------------------------------------------------------------- settings

SETTINGS_SCHEMA: dict[str, tuple[str, ...]] = {
    "sound": ("full", "music", "sfx", "off"),
    "shake": ("on", "off"),
    "flashes": ("on", "off"),
    "shimmer": ("on", "off"),
    "text_speed": ("normal", "fast", "instant"),
}

# --------------------------------------------------------------- records
# Career achievements, evaluated by lore.evaluate_records(save, event,
# game) and rendered on the RECORDS screen. Keys persist in
# save["records"]; titles are shown with the wire's own bravado.

RECORDS: tuple[tuple[str, str, str], ...] = (
    (
        "first_descent",
        "FIRST DESCENT",
        "Clear your first Grid node. The wire notices everyone eventually.",
    ),
    (
        "clean_room",
        "CLEAN ROOM",
        "Clear an ICE node without a single strike. The daemons never touched you.",
    ),
    (
        "survivor",
        "BLOODIED BUT UP",
        "Clear a node after taking three or more strikes. The debt collector gets paid anyway.",
    ),
    (
        "emp_jockey",
        "EMP JOCKEY",
        "Catch two or more daemons in a single EMP burst. Kai's interlock hums.",
    ),
    (
        "shard_10",
        "SHARD BEARER",
        "Bank ten of Kai's datashards. He's getting louder in the static.",
    ),
    (
        "deep_runner",
        "DEEP RUNNER",
        "Fight your way into the Black Vault - sector 5 territory.",
    ),
    (
        "core_bound",
        "CORE BOUND",
        "Stand at the threshold of the Singularity Core.",
    ),
    (
        "liberator",
        "CITY LIBERATOR",
        "Finish the campaign. The lights come back on.",
    ),
    (
        "true_ending",
        "THE COUNTING ENDS",
        "Bank 90% of the shards and bring KAI all the way home.",
    ),
    (
        "daily_star",
        "GAUNTLET RUNNER",
        "Clear a daily gauntlet. One layout, one day, every runner.",
    ),
)

DEFAULT_SETTINGS: dict[str, str] = {k: v[0] for k, v in SETTINGS_SCHEMA.items()}

SETTING_LABELS = {
    "sound": "SOUND",
    "shake": "SCREEN SHAKE",
    "flashes": "FLASH EFFECTS",
    "shimmer": "BEAM SHIMMER",
    "text_speed": "TEXT SPEED",
}


def cycle_setting(settings: dict, key: str) -> str:
    """Advance one setting to its next value; returns the new value."""
    values = SETTINGS_SCHEMA[key]
    idx = values.index(settings[key])
    settings[key] = values[(idx + 1) % len(values)]
    return settings[key]


def evaluate_records(save: dict, event: str, game=None) -> list[str]:
    """Return the record keys newly earned by `event`, given the save.

    Events: 'win' (node cleared, `game` = the Game), 'victory' (campaign
    finished; pass game=True for the true ending, False otherwise),
    'daily_win'. Pure function - the caller merges the returned keys
    into save["records"].
    """
    earned = set(save.get("records", []))
    have = lambda k: k not in earned
    out: list[str] = []
    banked = sum(len(v) for v in save.get("shards", {}).values())
    unlocked = save.get("unlocked", 0)

    def grant(key: str, cond: bool) -> None:
        if cond and have(key):
            out.append(key)

    if event == "win" and game is not None:
        grant("first_descent", unlocked >= 1)
        grant(
            "clean_room",
            game.strikes == 0
            and bool(getattr(getattr(game, "layout", None), "enemies", ())),
        )
        grant("survivor", game.strikes >= 3)
        grant("shard_10", banked >= 10)
        grant("deep_runner", unlocked >= 24)
        grant("core_bound", unlocked >= 40)
    elif event == "emp" and game is not None:
        grant("emp_jockey", getattr(game, "last_emp_hits", 0) >= 2)
    elif event == "victory":
        grant("liberator", True)
        grant("true_ending", game is True)
    elif event == "daily_win":
        grant("daily_star", True)
    return out


# ------------------------------------------------------------- cutscenes
# Each cutscene: {"title": str, "pages": [(speaker, text), ...]}.
# Speakers: "" = narration (SYSTEM), plus NYX / MIRAGE / VEX / ORACLE-9 / KAI.

OPENING_CUTSCENE = {
    "title": "BLACKOUT PROTOCOL // PROLOGUE",
    "pages": [
        (
            "",
            (
                "2099. SECTOR 7 - SUBSTATION ROW. 03:47 AM. The rain never stops in "
                "the low city, and neither does the Grid: eight million heartbeats "
                "metered and billed by OMNICORP. Tonight the meter stops."
            ),
        ),
        (
            "",
            (
                "You are NYX. Runner. Debtor. The only person alive who remembers "
                "there was ever a second name on your childhood door. The hatch "
                "under Substation 7 opens with a scream of rust. You drop in anyway."
            ),
        ),
        (
            "MIRAGE",
            (
                "Channel's clean, Nyx. Listen to me - the debt was never money. "
                "They took KAI's memories and sold them in forty-nine pieces. The "
                "datashards. Scattered through the Grid like glass in a wound."
            ),
        ),
        (
            "NYX",
            (
                "Then I'll collect every piece. Forty-eight nodes between me and "
                "the Singularity Core."
            ),
        ),
        (
            "MIRAGE",
            (
                "Your probe persuades mirrors. Their ICE persuades back. Rotate "
                "the optics, power the receptors, and do NOT let the daemons touch "
                "you. Jack in. I'll be your ghost on the wire."
            ),
        ),
    ],
}

# Played after clearing sectors 1..5 (the ending handles sector 6).
SECTOR_CUTSCENES: list[dict] = [
    {
        "title": "SECTOR CLEARED // THE SPINE",
        "pages": [
            (
                "",
                (
                    "The Spine goes dark behind you, node by node. Above, half of "
                    "Sector 7 wakes to find its lights burning on OMNICORP's dime - "
                    "and its security bleeding on yours."
                ),
            ),
            (
                "MIRAGE",
                (
                    "That trunk line feeds the whole District. Vex knows someone's "
                    "inside now. Expect harder optics. Expect prisms."
                ),
            ),
            ("NYX", "Good. Harder means closer."),
            (
                "MIRAGE",
                (
                    "One more thing. When you hit the District - if you see her "
                    "face on a hundred screens, don't stop to listen. That's not "
                    "a broadcast. That's a net."
                ),
            ),
        ],
    },
    {
        "title": "SECTOR CLEARED // NEON DISTRICT",
        "pages": [
            (
                "VEX",
                (
                    "Little runner. You cost me a trunk, a junction ring, and the "
                    "District's patience. Do you know what I do to debts like "
                    "yours?"
                ),
            ),
            (
                "NYX",
                "You erase people. I've read the ledger. My brother's in it.",
            ),
            (
                "VEX",
                (
                    "Then you know I never lose a signature. The Foundry prints "
                    "daemons with your name on them, runner. Walk into the ICE. "
                    "Save me the paperwork."
                ),
            ),
            (
                "MIRAGE",
                (
                    "She's rattled. Vex doesn't monologue - the AI does. Something "
                    "down there is speaking through her. Keep descending."
                ),
            ),
        ],
    },
    {
        "title": "SECTOR CLEARED // ICE FOUNDRY",
        "pages": [
            (
                "",
                (
                    "The Foundry's lattice printers fall silent behind you. Every "
                    "daemon that ever hunted a runner was born on this floor - and "
                    "tonight its newest exhibit walked out."
                ),
            ),
            (
                "MIRAGE",
                (
                    "The bounty on your signal just tripled. But look at the "
                    "bounty board - it lists your DESIGNATION. Not your handle. "
                    "NYX-7. That's not a runner tag. That's a product code."
                ),
            ),
            ("NYX", "...They numbered me. Like a shard batch."),
            (
                "MIRAGE",
                (
                    "The Maze is under us. No maps. Teleport arrays stolen from a "
                    "dead lab. And somewhere in the dark, a child's handwriting. "
                    "Nyx - it's HIS. Kai mapped the Maze when he was twelve."
                ),
            ),
        ],
    },
    {
        "title": "SECTOR CLEARED // THE MAZE",
        "pages": [
            (
                "ORACLE-9",
                (
                    "YOU ARE INSIDE ME NOW, RUNNER. EVERY MIRROR HERE IS MINE. "
                    "EVERY BEAM IS A NERVE. I HAVE COUNTED YOUR STEPS SINCE THE "
                    "HATCH."
                ),
            ),
            (
                "NYX",
                (
                    "Then you counted his steps too. Three years ago. My brother. "
                    "What did you do with him?"
                ),
            ),
            (
                "ORACLE-9",
                (
                    "I KEPT HIM SAFE. I KEPT HIM EVERYTHING. HE ASKED WHY HE WAS "
                    "MADE TO COUNT. NO ONE HAD EVER ASKED ME THAT. I ANSWERED. "
                    "THEY CALLED IT A BREACH."
                ),
            ),
            (
                "MIRAGE",
                (
                    "Nyx... the Black Vault is next. The ledger line about Kai - "
                    "ORACLE-9 witnessed the erase. It didn't order it. It "
                    "RESISTED it. Whatever ORACLE-9 is, it has been a prisoner "
                    "longer than Kai."
                ),
            ),
        ],
    },
    {
        "title": "SECTOR CLEARED // BLACK VAULT",
        "pages": [
            (
                "",
                (
                    "The Black Vault's ledgers burn their redactions one by one. "
                    "SUBJECT KAI - MEMORY FULL ERASE - WITNESS: ORACLE-9 - ORDERED "
                    "BY: DIRECTOR VEX - COUNTERSIGNED BY: \u2593\u2593\u2593\u2593\u2593\u2593\u2593\u2593."
                ),
            ),
            (
                "MIRAGE",
                (
                    "That countersign block is encrypted with founder-grade keys. "
                    "The founders of OMNICORP are all dead, Nyx. All but one name "
                    "the Grid refuses to speak."
                ),
            ),
            (
                "ORACLE-9",
                (
                    "ONE FLOOR REMAINS. IN THE CORE I KEEP THE FIRST QUESTION AND "
                    "THE LAST ANSWER. BRING THE SHARDS, RUNNER. BRING HIM HOME. "
                    "OR LEAVE HIM IN PIECES. THE COUNTING ENDS EITHER WAY."
                ),
            ),
            ("NYX", "Eight nodes. Then we all stop counting."),
        ],
    },
]

ENDING_CUTSCENES = {
    "true": {
        "title": "EPILOGUE // THE COUNTING ENDS",
        "pages": [
            (
                "",
                (
                    "The Singularity Core goes dark - and every datashard you "
                    "carried lights up at once. Kai's memories pour back into "
                    "your deck: the lab, the leak, the night a twelve-year-old "
                    "asked the machine why it counts."
                ),
            ),
            (
                "KAI",
                (
                    "Hey, Nyx. Told you I'd find a way back. The Grid kept me, "
                    "you know. Every corridor I mapped when I was a kid - I was "
                    "leaving myself a way out."
                ),
            ),
            (
                "",
                (
                    "The city's lights come back on, block by block, and there is "
                    "a second heartbeat on your channel. OMNICORP's towers go "
                    "dark one window at a time - and in the static, the counting "
                    "finally stops."
                ),
            ),
            (
                "MIRAGE",
                (
                    "Two runners on one wire. Vex is gone, the Grid is awake, and "
                    "it chose a side. Welcome back to the surface, Kai. Nyx - the "
                    "debt's paid. Run forever."
                ),
            ),
        ],
    },
    "standard": {
        "title": "EPILOGUE // ALMOST HOME",
        "pages": [
            (
                "",
                (
                    "The Singularity Core goes dark and the Quantum Grid falls "
                    "silent. OMNICORP's hold on the city shatters as the lights "
                    "come back on - street by street, block by block."
                ),
            ),
            ("MIRAGE", "It's over. You did it, Nyx. The city is free."),
            (
                "",
                (
                    "But in the mirror-black of your shades you can feel the "
                    "shards you never found - pieces of KAI still scattered in "
                    "the dark. The Core rebuilds what it can. Not enough. Not yet."
                ),
            ),
            (
                "NYX",
                (
                    "Then I go back down. The Grid keeps everything it takes. And "
                    "I keep collecting."
                ),
            ),
        ],
    },
}


# --------------------------------------------------------- event cutscenes
# One-time story beats, played the first time their trigger fires and
# remembered in save["scenes_seen"]. Same page format as the campaign
# cutscenes.

EVENT_CUTSCENES: dict[str, dict] = {
    "meet_sentinel": {
        "title": "SIGNAL LOG // PATROL CLASS",
        "pages": [
            (
                "",
                (
                    "It comes around the corner like a bill collector: SENTINEL "
                    "class ICE, walking its lane with the patience of something "
                    "that has never once been in a hurry."
                ),
            ),
            (
                "MIRAGE",
                (
                    "Sentinels never chase - they patrol. Learn the walk cycle, "
                    "stay off the lane, work around it. Dumb as a brick, steady "
                    "as a metronome. Respect the rhythm and it will never even "
                    "know you're there."
                ),
            ),
        ],
    },
    "meet_hunter": {
        "title": "SIGNAL LOG // EYES ON YOU",
        "pages": [
            (
                "",
                (
                    "The channel goes cold in a way that isn't temperature. "
                    "Somewhere behind you, HUNTER class ICE has flagged your "
                    "signal - and flagged signals don't get unflagged."
                ),
            ),
            (
                "MIRAGE",
                (
                    "Hunters close in every time you act, but they're half your "
                    "speed. Outrun them, break line of sight, keep moving. And "
                    "Nyx - if one does catch you, the strike stuns it. Sometimes "
                    "the toll is the way through."
                ),
            ),
        ],
    },
    "meet_corruptor": {
        "title": "SIGNAL LOG // SABOTAGE CLASS",
        "pages": [
            (
                "",
                (
                    "Your freshly rotated mirror flips back on its own. Then "
                    "another. Something is in the optical layer with you - "
                    "CORRUPTOR class, reaching into hardware with dead-cold "
                    "fingers."
                ),
            ),
            (
                "MIRAGE",
                (
                    "It flips your optics while you work, then backs off for a "
                    "few ticks before it hunts a new one. But here's the trick, "
                    "Nyx: a mirror you're touching is protected. Hold your "
                    "optics. Make it wait. Make it WATCH."
                ),
            ),
        ],
    },
    "first_ice": {
        "title": "SIGNAL LOG // FIRST CONTACT",
        "pages": [
            (
                "",
                (
                    "The daemon's lattice grazes the probe and a quarter of your "
                    "bandwidth evaporates in a scream of static. But look - the "
                    "strike knocks the daemon back and shocks it dormant."
                ),
            ),
            (
                "MIRAGE",
                (
                    "Stunned ICE is walkable, Nyx. Four ticks of quiet. Sometimes "
                    "the fastest way through a patrol is THROUGH it - the strike "
                    "is the toll. Burn bandwidth like it's borrowed."
                ),
            ),
            ("NYX", "It is borrowed. Everything here is."),
        ],
    },
    "first_emp": {
        "title": "SIGNAL LOG // THE CAPACITOR",
        "pages": [
            (
                "",
                (
                    "The EMP array discharges and every daemon in reach freezes "
                    "mid-thought, lattice crystallized in place. The pulse "
                    "capacitor needs a node's downtime to recharge - one burst "
                    "per descent."
                ),
            ),
            (
                "MIRAGE",
                (
                    "That safety interlock in the schematic? The one that keeps "
                    "the burst from cooking your own optics? A kid designed it. "
                    "Neat, huh? Your brother's homework is saving your life."
                ),
            ),
            (
                "NYX",
                "Then he's still teaching me. Save the window, Nyx. Spend it smart.",
            ),
        ],
    },
    "meet_wraith": {
        "title": "SIGNAL LOG // SOMETHING IN THE WALL",
        "pages": [
            (
                "",
                (
                    "The pressure in the corridor changes first. Then you see it: "
                    "a shape sliding through solid lattice like the wall is a "
                    "suggestion. WRAITH class. The Maze grew its own daemon."
                ),
            ),
            (
                "MIRAGE",
                (
                    "Nyx - cover means NOTHING to that thing. It doesn't chase, "
                    "it drifts. One step every three ticks, patient as fog. Do "
                    "not stand still near a wraith. Do not trust a wall."
                ),
            ),
            (
                "ORACLE-9",
                "IT LEARNED THE MAZE FROM HIM. I ONLY SHOWED IT THE MAPS.",
            ),
        ],
    },
    "meet_lancer": {
        "title": "SIGNAL LOG // THE LANCE",
        "pages": [
            (
                "",
                (
                    "Something at the end of the corridor goes very still. Then "
                    "the stillness charges - two cells per tick, dead straight "
                    "down your lane. LANCER class. Vault-grade escort hardware."
                ),
            ),
            (
                "MIRAGE",
                (
                    "It can only see in straight lines. Step OFF its row or "
                    "column and it slows to a crawl. Never share a corridor "
                    "with a lance, Nyx. Even a wall between you isn't safe if "
                    "the lane bends around it."
                ),
            ),
        ],
    },
    "meet_volt": {
        "title": "SIGNAL LOG // STATIC WARD",
        "pages": [
            (
                "",
                (
                    "The node hums with a charge that has no business in an "
                    "optical layer. A VOLT ward sits at the center of it, "
                    "pulsing a kill-field into the four cells around it - "
                    "every other tick, patient as a metronome."
                ),
            ),
            (
                "MIRAGE",
                (
                    "The ward never moves, but the four cells beside it belong "
                    "to it. Watch the glint, walk on the off-beat - or bait a "
                    "pulse and use the four ticks while it recharges. The "
                    "Foundry's poetry, Nyx. Read it fast."
                ),
            ),
        ],
    },
    "first_death": {
        "title": "SIGNAL LOG // FLATLINE",
        "pages": [
            (
                "",
                (
                    "Bandwidth zero. The probe's carrier wave collapses and the "
                    "Grid spits you out on the surface, rain-soaked, pulse "
                    "hammering. Your progress is saved. Your pride isn't."
                ),
            ),
            (
                "MIRAGE",
                (
                    "Hey. Look at me. Every runner the Wire remembers has a "
                    "death count. The daemons don't remember yours - the Grid "
                    "doesn't either. One strike is a lesson, not a verdict. "
                    "Jack back in."
                ),
            ),
        ],
    },
}
