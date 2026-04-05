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

export function getRandomStimulus() {
  if (Math.random() < 0.55) {
    return `Random word: ${pick(FALLBACK_WORDS)}`;
  }
  return `Random fact: ${pick(FALLBACK_FACTS)}`;
}
