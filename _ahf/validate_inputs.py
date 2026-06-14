"""Deterministic honesty gate for <T>_inputs.json before the compute step.

Run after the portfolio_manager writes inputs, BEFORE dcf_compute. Exits non-zero (so the
orchestrator knows to recalibrate) if the DCF was fabricated or the weights don't sum to 1.

Usage:  python _ahf/validate_inputs.py --inputs output/<T>/<T>_inputs.json
"""
import argparse
import json
import sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inputs", required=True)
    args = ap.parse_args()
    try:
        d = json.load(open(args.inputs, encoding="utf-8"))
    except Exception as e:
        print(f"VALIDATE FAIL: cannot read inputs ({e})")
        return 1

    pm = d.get("primary_method", {}) or {}
    method = pm.get("name", "")
    problems = []

    if method == "DCF":
        inp = pm.get("inputs", {}) or {}
        if not (inp.get("wacc", {}) or {}).get("value"):
            problems.append("missing wacc.value")
        if not inp.get("fcf_projections"):
            problems.append("missing fcf_projections")
        elif len(inp["fcf_projections"]) < 7:
            problems.append(f"only {len(inp['fcf_projections'])}y horizon (Damodaran-style fade wants ~10y)")
        for s in d.get("scenarios", []):
            if "fcf_multiplier" in (s.get("key_changes", {}) or {}):
                problems.append(f"scenario '{s.get('label')}' uses fcf_multiplier -> FABRICATED DCF, forbidden")
    elif method == "DDM":
        pass  # bank path validated separately
    else:
        problems.append(f"unexpected method '{method}' (expected DCF or DDM)")

    tot = None
    if d.get("scenarios"):
        probs = sum((s.get("probability") or 0) for s in d.get("scenarios", []))
        cc = (d.get("blending_weights", {}) or {}).get("cross_check", 0) or 0
        tot = probs + cc
        if abs(tot - 1.0) > 0.02:
            problems.append(f"scenario probabilities + cross_check = {tot:.2f}, must sum to 1.0")

    if problems:
        print("VALIDATE FAIL:")
        for p in problems:
            print("  - " + p)
        return 1
    print(f"VALIDATE OK ({method}; {len(pm.get('inputs',{}).get('fcf_projections',[]))}y FCF; "
          f"weights sum {tot if tot is None else round(tot,2)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
