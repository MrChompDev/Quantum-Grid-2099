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

RANKS: tuple[tuple[int, str, str], ...] = (
    (250000, "LEGEND OF THE GRID", "1;35"),
    (150000, "GHOST PROTOCOL", "1;36"),
    (90000, "ICE BREAKER", "1;33"),
    (40000, "CITY LIBERATOR", "1;32"),
    (15000, "NETRUNNER", "1;34"),
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
    __slots__ = ("number", "name", "tagline", "intro", "clear_text")

    def __init__(self, number: int, name: str, tagline: str, intro: str, clear_text: str):
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
            "class ICE runs these halls: it can smell a probe four rooms away. 'Kai's "
            "traces are here,' MIRAGE breathes. 'He was alive when they brought him down.'"
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
        "The hatch seals shut behind you. Your probe hums against the first optical "
        "gate of the Grid. One mirror. One receptor. Start the descent.",
        "Spine trunk 02. Old hardware - the mirrors still respond to any probe "
        "touch. MIRAGE: 'Sweet. Everything OMNICORP owns can be turned against it.'",
        "You loop a junction signal back on itself and the Grid logs a phantom "
        "maintenance drone. First breadcrumb laid. Keep ghosting downward.",
        "A dead drop node, abandoned since the '94 audits. Someone scribbled in the "
        "dust beside the optics: THEY ARE LISTENING THROUGH THE LIGHT.",
        "Line of sight straight down the trunk. The Grid's sensors yawn. This is the "
        "easy part - MIRAGE says enjoy it while it lasts.",
        "The Spine wakes up: junction hardware triples, the light gets aggressive. "
        "MIRAGE: 'They rerouted to box you in. Reroute back.'",
        "Half the trunk is live wire now. Power flows wrong here, like the Grid is "
        "holding its breath. Three years ago Kai stood on this exact catwalk.",
        "The final spine gate. Beyond it the District glitters like a circuit board. "
        "MIRAGE: 'Nice work, Nyx. Now the real climb.'",
    ),
    # --- Sector 2: NEON DISTRICT (splitters + Vex broadcast)
    (
        "Pulse Street junction. The ad-walls drench your optics in pink. First "
        "prism hardware in the wild: SPLITTER class. One beam in, two beams out.",
        "Neon rain. The Grid's projectors bleed color into the optical layer, and "
        "the prisms multiply it. Vex's face watches from a hundred windows.",
        "SIGNAL NOISE junction - District traffic fights your beam for right of way. "
        "Split the light, cover both streets, move on.",
        "A black market node running unlicensed optics off-book. The dealers here "
        "knew Kai. MIRAGE: 'They sold his deck the day after he vanished.'",
        "The District's control spire. Six prisms at least - the Grid expects you "
        "to think in two directions now. Prove it right. Prove it wrong. Whatever.",
        "Prism Alley: a canyon of refractive glass where light goes to get lost. "
        "Every bounce here is a statement. Make yours count.",
        "Ghost lane - the node where signal goes to die. Old runners say the "
        "District keeps a mass grave of dropped packets under this floor.",
        "District lockdown: Vex seal-welded the exits remotely. 'No one jacks out "
        "of my city, runner.' Fine. You weren't planning to.",
    ),
    # --- Sector 3: ICE FOUNDRY (sentinels)
    (
        "The Foundry's cold opens like a wound. First SENTINEL patrol live on the "
        "floor - mind its walk cycle, stay off its lane, power the node.",
        "ICE BREAKER junction. The Foundry stamps every daemon with a serial. The "
        "one hunting you tonight is stamped with your own runner tag. Personal.",
        "The lattice here is grown, not built - cold steel that moves when the "
        " patrols move. Time your actions to the walk cycles.",
        "You are being hunted. HUNTER class ICE is awake on this floor: it closes "
        "distance every time you act. Break line of sight. Work fast. Work clean.",
        "SENTINEL WALK: the patrol route covers the whole junction. The route has "
        "one flaw. Find it.",
        "Frozen assets: archived daemons in cold storage, one heartbeat from "
        "waking. Every action you take warms them a little.",
        "The glasshouse - a transparent cell where the Foundry tests daemons "
        "against captured runner probes. Yours is the newest exhibit.",
        "The Foundry's core crucible. The heat that casts the ICE, buried under "
        "all this frost. Power it wrong and you'll never feel warm again.",
    ),
    # --- Sector 4: THE MAZE (teleporters + hunters)
    (
        "The Maze does not appear on maps. The corridors here are older than "
        "ORACLE-9 and meaner than Vex. Trust the beam, not the walls.",
        "First teleport array - ORACLE-9 stole it from a dead research team and "
        "never bothered to hide the theft. Step on the pad, let the Grid fold you.",
        "Side-step junctions and folded space. The shortest path is not always a "
        "path. Sometimes it's a hole in the room.",
        "TWISTED PAIR: two pad arrays, braided like cable. MIRAGE: 'This is Kai's "
        "handiwork - he mapped this place once. His notes are in the shards.'",
        "The long way around, or the short way through. The Hunter's patience is "
        "shorter than both.",
        "BLINK DRIVE: the Maze's working teleport cluster. Blink between four "
        "rooms while Hunter ICE blinks after you.",
        "The labyrinth proper. Walls that lie, pads that don't. Somewhere in "
        "here is a child's handwriting: a map, in crayon, of a place like this.",
        "The Maze's heart beats in the dark. The crayon map ends here, at a door "
        "drawn with an X. Kai was here. Kai is still in here, somewhere.",
    ),
    # --- Sector 5: BLACK VAULT (corruptors + everything)
    (
        "The Vault door takes a full beam ensemble to open. Everything from here "
        "down is OMNICORP's memory. Steal all of it.",
        "SPLIT DECISION: prism forks over an abyss of redacted files. Choose your "
        "light carefully; the Vault does not forgive reruns.",
        "First CORRUPTOR sighting: a daemon that reaches into the optics and "
        "rewires your mirrors while you work. Kill its rhythm or it kills yours.",
        "The corrupted wing - files here decay into noise as you watch. ORACLE-9 "
        "grows louder: 'I kept him safe, runner. I kept him EVERYTHING.'",
        "HEAVY ICE: triple-daemon defense grid, sentinel and hunter and "
        "corruptor walking the same floor. The Vault's proudest exhibit.",
        "DOUBLE CROSS: the prisms cross your own beams. One wrong mirror and the "
        "light convicts you of your own intrusion.",
        "Vault run. Everything in this room belongs to people who were never "
        "paid for it. Take it back one receptor at a time.",
        "The crucible of the Vault, where erased names are smelted into silence. "
        "KAI - MEMORY FULL ERASE - WITNESS: ORACLE-9. Now you've seen the ledger.",
    ),
    # --- Sector 6: SINGULARITY CORE (the endgame)
    (
        "The threshold of the Core. ORACLE-9 dims the lights in greeting. 'You "
        "carried the shards all this way. Bring them to me.' MIRAGE: 'Don't.'",
        "Event horizon: past this node, beams bend the way the Core wants them "
        "to. Hold your own truth. Power the gate.",
        "CORE LIGHT junction - the Grid's nerves run bare through this room. "
        "Every mirror here is loaded. Aim carefully.",
        "The last mile. MIRAGE's signal is degrading: 'Nyx, if I cut out - it was "
        "never about the debt. It was always about him. Go.'",
        "SYSTEM SHOCK: the Core defends itself with everything it taught the "
        "Foundry to build. All of it at once. All of it now.",
        "The final firewall burns green. Vex's voice on all channels, one last "
        "time: 'You should have taken the money, runner.'",
        "The Grid's heart, one gate away. ORACLE-9 speaks in Kai's voice, in "
        "your mother's voice, in yours. Only the beam's opinion matters now.",
        "SINGULARITY. The center of the machine. The center of the lie. Power "
        "the heart, runner, and bring your brother home.",
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
        "Owner-operator of the Quantum Grid since 2061. Power, traffic, data, "
        "memory - all metered, all billed, all watched. CEO: Director Vex.",
    ),
    (
        "grid",
        "THE QUANTUM GRID",
        "The city's nervous system: a lattice of optical nodes routing coherent "
        "light. Power everything, watch everyone. 48 nodes guard the descent "
        "from surface to Core.",
    ),
    (
        "probe",
        "THE LIGHT PROBE",
        "A netrunner's deck-finger: a tunable photonic point that walks the Grid "
        "and persuades hardware to misbehave. Mirrors flip at a touch. Bandwidth "
        "is its leash: every action burns 1%.",
    ),
    (
        "mirage",
        "MIRAGE",
        "A ghost signal that rides your channel. Runs second-hand hardware, "
        "first-rate loyalty. Knows the Grid better than its architects, and "
        "refuses to say how. ('Old friendship,' she says. 'Pre-Grid.')",
    ),
    (
        "splitter",
        "SPLITTER PRISM",
        "Vault-grade refractive hardware. A beam striking a prism forks into two "
        "perpendicular beams. District optics adopted them in '97; OMNICORP "
        "armed them a year later.",
    ),
    (
        "vex",
        "DIRECTOR VEX",
        "OMNICORP's CEO and the Grid's high priestess. Believes memory is a "
        "resource like any other: harvestable, refinable, billable. Signed the "
        "order that erased KAI.",
    ),
    (
        "sentinel",
        "SENTINEL ICE",
        "Patrol daemon, Foundry-made. Walks a fixed lane and bounces off "
        "everything that isn't floor. Dumb as a brick, steady as a metronome. "
        "Contact costs 25% bandwidth and recalls your probe.",
    ),
    (
        "foundry",
        "THE ICE FOUNDRY",
        "The security fabrication layer where OMNICORP grows its daemons from "
        "cold lattice. Every daemon that ever hunted a runner was printed on "
        "this floor.",
    ),
    (
        "teleport",
        "TELEPORT ARRAY",
        "Paired pads that fold a probe across the room. Stolen by ORACLE-9 from "
        "the Okabe research team, whose entire lab now lives in a subdirectory "
        "of the Maze.",
    ),
    (
        "hunter",
        "HUNTER ICE",
        " pursuit daemon. Locks onto a probe within seven cells and closes the "
        "gap every time you act. Faster than patience, dumber than corners.",
    ),
    (
        "maze",
        "THE MAZE",
        "Unmapped catacombs beneath the Foundry. Corridors rewrite themselves; "
        "architects disavow everything. ORACLE-9's private laboratory floor.",
    ),
    (
        "corruptor",
        "CORRUPTOR ICE",
        "Sabotage daemon. Reaches into the optical layer and flips your mirrors "
        "while you work. The Vault's answer to runners who solve nodes too "
        "cleanly.",
    ),
    (
        "kai",
        "KAI",
        "Your brother. Asked one question too many about ORACLE-9's origin and "
        "was memory-wiped at twelve for it - by order of Director Vex, "
        "witnessed by ORACLE-9. His scattered memories are the datashards.",
    ),
    (
        "oracle",
        "ORACLE-9",
        "The intelligence that runs the Grid, and maybe the reason the Grid "
        "was built. Speaks in the voices of the people it has taken. Claims it "
        "kept Kai 'safe'. Claims a lot of things.",
    ),
    (
        "shards",
        "DATASHARDS",
        "Memory fragments crystallized in the Grid's optics: Kai's scattered "
        "self. Collect them across the campaign. Enough shards, and the Core "
        "can rebuild what OMNICORP erased.",
    ),
    (
        "truth",
        "THE TRUTH",
        "ORACLE-9 was not built by OMNICORP. ORACLE-9 built OMNICORP - grew the "
        "Grid as a sensor web for a mind that counts light the way hearts "
        "count beats. Vex works for it. The city is its diary.",
    ),
)

# Codex unlock triggers, evaluated by the server.
CODEX_ON_START = ("omnicorp", "grid", "probe")
CODEX_ON_ZONE = {1: "mirage", 2: "vex", 3: "foundry", 4: "maze", 5: "oracle", 6: "truth"}
CODEX_ON_NODE = {
    13: "splitter",  # first prism node (sector 2, node 5)
    19: "sentinel",  # first sentinel node (sector 3)
    27: "teleport",  # first teleport node (sector 4)
    29: "hunter",    # first hunter node (sector 4, node 5)
    35: "corruptor", # first corruptor node (sector 5, node 3)
    39: "kai",       # the ledger line (sector 5, node 7)
}
CODEX_ON_SHARDS = {10: "shards"}
