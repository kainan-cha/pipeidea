"""Generate a large deterministic fuzz seed pack for calibration."""

import argparse
import json
import random
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = REPO_ROOT / "calibration" / "seed_packs" / "fuzz_1000_v1.jsonl"

BLOOM_PREFIXES = [
    "public",
    "portable",
    "ritual",
    "civic",
    "ambient",
    "seasonal",
    "communal",
    "emergency",
    "informal",
    "autonomous",
    "analog",
    "underground",
    "elastic",
    "shared",
    "mobile",
    "intergenerational",
    "nighttime",
    "slow",
    "silent",
    "temporary",
    "neighborhood",
    "circular",
    "living",
    "post-scarcity",
    "weather-aware",
    "migratory",
    "ceremonial",
    "feral",
    "adaptive",
    "zero-waste",
]

BLOOM_SUBJECTS = [
    "housing",
    "insurance",
    "funerals",
    "public transit",
    "waste heat",
    "batteries",
    "libraries",
    "street lighting",
    "sleep",
    "tax filing",
    "playgrounds",
    "retail",
    "gardening",
    "water storage",
    "citizenship",
    "parking",
    "meetings",
    "school lunches",
    "weddings",
    "archives",
    "maps",
    "restaurants",
    "ambulances",
    "museums",
    "borders",
    "dating",
    "warehouses",
    "neighborhood watch",
    "waste collection",
    "childcare",
    "ports",
    "elections",
    "tourism",
    "construction sites",
    "elder care",
    "music lessons",
    "energy grids",
    "pharmacies",
    "commuting",
    "sidewalks",
    "grocery stores",
    "public bathrooms",
    "meditation",
    "newsletters",
    "fisheries",
    "farms",
    "apartment lobbies",
    "supply chains",
    "airports",
    "courtrooms",
]

COLLISION_TERMS = [
    "fungal networks",
    "luxury skincare",
    "jazz improvisation",
    "tax policy",
    "archaeology",
    "cloud infrastructure",
    "beekeeping",
    "public housing",
    "funeral rites",
    "machine vision",
    "cathedral architecture",
    "waste management",
    "fermentation",
    "maritime law",
    "kite festivals",
    "power grids",
    "street basketball",
    "hospital triage",
    "subway maps",
    "oral history",
    "aquaculture",
    "insurance underwriting",
    "weather balloons",
    "night markets",
    "chess notation",
    "disaster relief",
    "ballet rehearsal",
    "cemeteries",
    "voting systems",
    "language preservation",
    "microscopy",
    "public parks",
    "drone logistics",
    "water rights",
    "calligraphy",
    "debt collection",
    "composting",
    "airport security",
    "mythology",
    "wedding planning",
    "sourdough starters",
    "civic budgeting",
    "glacier science",
    "radio astronomy",
    "streetwear",
    "mutual aid",
    "lighthouses",
    "urban forestry",
    "warehouse robotics",
    "perfume design",
    "aqueducts",
    "wildfire response",
    "ice cream trucks",
    "court stenography",
    "orchestral conducting",
    "wastewater treatment",
    "zoning law",
    "bird migration",
    "detective fiction",
    "soil remediation",
    "museum conservation",
    "boxing gyms",
    "telemedicine",
    "theme parks",
    "open-source software",
    "artisan bread",
    "cryptography",
    "farmer cooperatives",
    "public libraries",
    "shipping containers",
    "disability advocacy",
    "graffiti",
    "weather derivatives",
    "pilgrimage routes",
    "emergency dispatch",
    "botanical gardens",
    "hotel housekeeping",
    "wilderness navigation",
    "courtship rituals",
    "harbor cranes",
    "glassblowing",
    "bankruptcy law",
    "urban beekeeping",
    "opera staging",
    "recycling centers",
    "land trusts",
    "food trucks",
    "forensic accounting",
    "rainwater capture",
    "sports commentary",
    "neon signage",
    "rail maintenance",
    "public speaking",
    "child development",
    "memory palaces",
    "space debris",
    "postal systems",
    "cemetery records",
    "reef restoration",
    "textile mills",
    "public defenders",
    "farm irrigation",
    "kitchen choreography",
    "migrant remittances",
    "tree rings",
    "bike repair",
    "wedding photography",
    "small claims court",
    "hydroelectric dams",
    "flea markets",
    "school uniforms",
    "aquariums",
    "taxidermy",
    "translation services",
    "storm drains",
    "podcast editing",
    "artisan cheese",
    "urban legends",
    "waste heat recovery",
]

RANDOM_WORDS = [
    "mycelium",
    "labyrinth",
    "resonance",
    "sedimentation",
    "patina",
    "undertow",
    "constellation",
    "calcification",
    "pendulum",
    "iridescence",
    "driftwood",
    "whisper",
    "membrane",
    "migration",
    "coral",
    "fracture",
    "bioluminescence",
    "pollination",
    "synapse",
    "aurora",
]

RANDOM_FACTS = [
    "Honey never spoils.",
    "Sharks are older than trees.",
    "Slime molds can solve mazes.",
    "Octopuses have three hearts.",
    "Venice was built on petrified tree trunks.",
    "Crows can recognize human faces.",
    "The Great Wall used sticky rice mortar.",
    "Tardigrades can survive in space.",
    "Trees communicate through fungal networks.",
    "A group of flamingos is called a flamboyance.",
]


def random_stimulus(rng: random.Random) -> str:
    if rng.random() < 0.5:
        return f"Random word: {rng.choice(RANDOM_WORDS)}"
    return f"Random fact: {rng.choice(RANDOM_FACTS)}"


def generate_bloom_seed(rng: random.Random) -> str:
    pattern = rng.randrange(4)
    if pattern == 0:
        return f"{rng.choice(BLOOM_PREFIXES)} {rng.choice(BLOOM_SUBJECTS)}"
    if pattern == 1:
        return rng.choice(BLOOM_SUBJECTS)
    if pattern == 2:
        return f"{rng.choice(BLOOM_SUBJECTS)} for {rng.choice(BLOOM_SUBJECTS)}"
    return f"{rng.choice(BLOOM_PREFIXES)} {rng.choice(BLOOM_PREFIXES)} {rng.choice(BLOOM_SUBJECTS)}"


def unique_bloom_seed(rng: random.Random, seen: set[str]) -> str:
    while True:
        seed = generate_bloom_seed(rng)
        if seed not in seen:
            seen.add(seed)
            return seed


def unique_collision_pair(rng: random.Random, seen: set[tuple[str, str]]) -> tuple[str, str]:
    while True:
        first, second = rng.sample(COLLISION_TERMS, 2)
        pair = tuple(sorted((first, second)))
        if pair not in seen:
            seen.add(pair)
            return first, second


def build_cases(count: int, collision_ratio: float, seed: int) -> list[dict[str, object]]:
    rng = random.Random(seed)
    collision_count = round(count * collision_ratio)
    bloom_count = count - collision_count

    cases: list[dict[str, object]] = []
    seen_bloom: set[str] = set()
    seen_collision: set[tuple[str, str]] = set()

    for index in range(1, bloom_count + 1):
        topic = unique_bloom_seed(rng, seen_bloom)
        cases.append(
            {
                "id": f"fuzz_bloom_{index:04d}",
                "mode": "bloom",
                "seeds": [topic],
                "stimulus": random_stimulus(rng),
                "notes": "Auto-generated large-scale bloom fuzz case.",
                "metadata": {
                    "generator": "generate_fuzz_pack.py",
                    "suite": "fuzz",
                    "kind": "bloom",
                    "seed": seed,
                },
            }
        )

    for index in range(1, collision_count + 1):
        first, second = unique_collision_pair(rng, seen_collision)
        cases.append(
            {
                "id": f"fuzz_collision_{index:04d}",
                "mode": "collision",
                "seeds": [first, second],
                "stimulus": random_stimulus(rng),
                "notes": "Auto-generated large-scale collision fuzz case.",
                "metadata": {
                    "generator": "generate_fuzz_pack.py",
                    "suite": "fuzz",
                    "kind": "collision",
                    "seed": seed,
                },
            }
        )

    rng.shuffle(cases)
    return cases


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=1000, help="Number of cases to generate.")
    parser.add_argument(
        "--collision-ratio",
        type=float,
        default=0.35,
        help="Fraction of cases that should be collision mode.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=17,
        help="Deterministic RNG seed for reproducible pack generation.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Where to write the JSONL pack.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.count <= 0:
        raise SystemExit("--count must be positive.")
    if not 0.0 <= args.collision_ratio <= 1.0:
        raise SystemExit("--collision-ratio must be between 0 and 1.")

    cases = build_cases(args.count, args.collision_ratio, args.seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        for case in cases:
            handle.write(json.dumps(case, ensure_ascii=False) + "\n")

    print(f"Wrote {len(cases)} cases to {args.output}")


if __name__ == "__main__":
    main()
