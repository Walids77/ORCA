"""Acceptance check for the token/cost meter (roadmap item #20).

Makes ONE live LLM call through the adapter, then verifies the meter's split
(tokens in + tokens out) sums EXACTLY to the provider's own reported total for
that same call — proving no token category (e.g. hidden thinking tokens) was
missed. Re-run after any model swap (Bedrock/Claude later).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from orca.brain import llm


def main() -> int:
    llm.reset_meter()
    answer = llm.ask("What is 2+2? Reply with just the number.", purpose="meter-check")

    calls = llm.meter_calls()
    summary = llm.meter_summary()

    print(f"answer: {answer!r}")
    print(f"\nMETER recorded {summary['calls']} call(s):")
    for c in calls:
        print(f"  purpose={c.purpose!r}  model={c.model}")
        print(f"  tokens in  = {c.tokens_in}")
        print(f"  tokens out = {c.tokens_out} (answer + hidden thinking)")
        print(f"  provider's own reported total = {c.tokens_total_reported}")
        print(f"  cost at paid-tier list price  = ${c.cost_usd:.6f}")

    c = calls[0]
    arithmetic_ok = c.tokens_in + c.tokens_out == c.tokens_total_reported
    ok = summary["calls"] == 1 and c.tokens_in > 0 and c.tokens_out > 0 and arithmetic_ok

    print(f"\narithmetic check: {c.tokens_in} + {c.tokens_out} "
          f"{'==' if arithmetic_ok else '!='} {c.tokens_total_reported}")
    print(f"{'PASS' if ok else 'FAIL'}: meter matches the provider's own usage report.")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
