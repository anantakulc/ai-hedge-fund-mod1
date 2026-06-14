"""Auto-detect + fix the trillions/billions units mismatch in a <T>_inputs.json.

Some from-scratch IDR tickers got FCFF/net-debt/EBITDA entered in IDR-trillions while shares are in
billions, so dcf_compute's implied_px comes out ~1000x too small (e.g. 5.82 instead of 5,820). This
runs the DCF, and if implied_px is wildly off vs current_price (factor >50x either way), multiplies the
absolute IDR fields (fcf_b, revenue_b, ebitda_b, net_debt_b, cross_check.fy_estimate, and the same
inside scenario key_changes.fcf_projections) by 1000 and re-verifies. Idempotent-ish: only fires when
off-scale, so running it on already-correct inputs is a no-op.

Usage:  python _ahf/fix_units.py --inputs output/<T>/<T>_inputs.json
"""
import argparse
import json
import os
import subprocess
import sys


def implied_px(inputs_path):
    tmp = inputs_path + ".chk.json"
    subprocess.run([sys.executable, "_schema/dcf_compute.py", "--inputs", inputs_path, "--output", tmp],
                   capture_output=True, text=True)
    try:
        v = json.load(open(tmp, encoding="utf-8"))
        px = (v.get("primary_method", {}) or {}).get("outputs", {}).get("implied_px")
    except Exception:
        px = None
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    return px


def scale_x1000(d):
    inp = d.get("primary_method", {}).get("inputs", {})
    for r in inp.get("fcf_projections", []) or []:
        for k in ("fcf_b", "revenue_b", "ebitda_b"):
            if isinstance(r.get(k), (int, float)):
                r[k] *= 1000
    if isinstance(d.get("net_debt_b"), (int, float)):
        d["net_debt_b"] *= 1000
    cc = (d.get("cross_check") or {}).get("inputs", {})
    if isinstance(cc.get("fy_estimate"), (int, float)):
        cc["fy_estimate"] *= 1000
    for s in d.get("scenarios", []) or []:
        fp = (s.get("key_changes") or {}).get("fcf_projections")
        if isinstance(fp, list):
            for r in fp:
                for k in ("fcf_b", "revenue_b", "ebitda_b"):
                    if isinstance(r.get(k), (int, float)):
                        r[k] *= 1000


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inputs", required=True)
    a = ap.parse_args()
    d = json.load(open(a.inputs, encoding="utf-8"))
    if (d.get("primary_method", {}) or {}).get("name") != "DCF":
        print("not DCF; skipping units check")
        return 0
    price = d.get("current_price")
    px = implied_px(a.inputs)
    if px and price and (px < price / 50 or px > price * 50):
        scale_x1000(d)
        json.dump(d, open(a.inputs, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
        px2 = implied_px(a.inputs)
        print(f"UNITS FIXED x1000: implied {px} -> {px2}  (price {price})")
    else:
        print(f"units OK: implied {px} vs price {price}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
