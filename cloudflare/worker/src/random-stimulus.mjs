const FALLBACK_WORDS = [
  "crystalline",
  "fermentation",
  "cartography",
  "mycelium",
  "resonance",
  "obsidian",
  "tidal",
  "origami",
  "phosphorescence",
  "migration",
  "archaeology",
  "synapse",
  "metamorphosis",
  "pendulum",
  "coral",
  "labyrinth",
  "combustion",
  "silk",
  "erosion",
  "constellation",
  "alchemy",
  "osmosis",
  "driftwood",
  "vortex",
  "patina",
  "tessellation",
  "murmuration",
  "bioluminescence",
  "stalactite",
  "aurora",
  "undertow",
  "pollination",
  "calcification",
  "whisper",
  "fracture",
  "petrification",
  "iridescence",
  "sedimentation",
  "echo",
  "membrane"
];

const FALLBACK_FACTS = [
  "Octopuses have three hearts and blue blood.",
  "Honey never spoils; edible honey has been found in 3000-year-old tombs.",
  "Tardigrades can survive in the vacuum of space.",
  "Slime molds can solve mazes and replicate efficient transit networks.",
  "The Great Wall of China was held together with sticky rice mortar.",
  "Crows can recognize human faces and hold grudges for years.",
  "Trees in a forest communicate through underground fungal networks.",
  "A group of flamingos is called a flamboyance.",
  "Sharks are older than trees.",
  "Venice was built on a foundation of petrified tree trunks."
];

function pick(values) {
  return values[Math.floor(Math.random() * values.length)];
}

const RELATIONSHIP_MARKERS = [
  "between", "versus", "relationship", "connection",
  "intersection", "compared", "contrast"
];

export function isSeedRich(seeds, mode) {
  if (mode === "collision") return true;
  const combined = seeds.join(" ");
  const words = combined.split(/\s+/).filter((w) => w.length > 2);
  if (words.length >= 5) return true;
  const lowered = combined.toLowerCase();
  if (RELATIONSHIP_MARKERS.some((m) => lowered.includes(m))) return true;
  if (combined.includes("?")) return true;
  if (["what", "how", "why", "when"].some((q) => lowered.startsWith(q))) return true;
  return false;
}

export function getRandomStimulus() {
  if (Math.random() < 0.55) {
    return `Random word: ${pick(FALLBACK_WORDS)}`;
  }
  return `Random fact: ${pick(FALLBACK_FACTS)}`;
}
