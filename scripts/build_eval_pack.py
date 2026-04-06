"""Build a mixed evaluation pack from multiple seed pack families."""

import argparse
import json
import random
from pathlib import Path

from pipeidea.realist.runner import resolve_seed_pack


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument(
        "--source",
        action="append",
        nargs=2,
        metavar=("PACK", "COUNT"),
        required=True,
        help="Pack ref and number of cases to sample from it.",
    )
    args = parser.parse_args()

    rng = random.Random(args.seed)
    selected: list[dict] = []

    for pack_ref, count_text in args.source:
        _, _, cases = resolve_seed_pack(pack_ref)
        count = int(count_text)
        if count > len(cases):
            raise SystemExit(f"Requested {count} cases from {pack_ref}, but only {len(cases)} exist.")
        sampled = rng.sample(cases, count)
        selected.extend(
            {
                "id": case.id,
                "mode": case.mode,
                "seeds": case.seeds,
                "stimulus": case.stimulus,
                "notes": case.notes,
                "web_stimuli": case.web_stimuli,
                "garden_echoes": case.garden_echoes,
                "metadata": case.metadata,
            }
            for case in sampled
        )

    Path(args.output).write_text(
        "\n".join(json.dumps(item, ensure_ascii=False) for item in selected) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
