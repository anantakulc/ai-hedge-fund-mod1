"""Assemble the AHF-native panel + football-field JSON from the raw agent signals.

ONE signal, faithful to ai-hedge-fund and internally consistent:
  * Each analyst gives a signal + a confidence + (stated or imputed) fair value.
  * The 12m target = the CONFIDENCE-WEIGHTED consensus of those fair values. No made-up
    per-analyst "importance" weights (the real ai-hedge-fund has none); confidence is the weight.
  * The recommendation = that consensus vs the price (BUY >+10%, SELL <-10%, else HOLD).
There is NO separate "weighted vote with a 0.55 threshold" -- that was a second signal that could
contradict the call, so it is gone. The 6/5/2 signal distribution is descriptive color only.

Usage:  python _ahf/build_panel.py --ticker AVGO --dir output/AVGO
"""

import argparse
import json
import os
from datetime import datetime, timezone

# Display + lens only. No importance weights (ai-hedge-fund has none; confidence is the weight).
PERSONAS = {
    "warren_buffett":        {"lens": "bull",      "display": "Warren Buffett"},
    "charlie_munger":        {"lens": "bull",      "display": "Charlie Munger"},
    "peter_lynch":           {"lens": "bull",      "display": "Peter Lynch"},
    "phil_fisher":           {"lens": "bull",      "display": "Phil Fisher"},
    "cathie_wood":           {"lens": "bull",      "display": "Cathie Wood"},
    "bill_ackman":           {"lens": "bull",      "display": "Bill Ackman"},
    "mohnish_pabrai":        {"lens": "bull",      "display": "Mohnish Pabrai"},
    "stanley_druckenmiller": {"lens": "bull",      "display": "Stanley Druckenmiller"},
    "rakesh_jhunjhunwala":   {"lens": "bull",      "display": "Rakesh Jhunjhunwala"},
    "michael_burry":         {"lens": "bear",      "display": "Michael Burry"},
    "nassim_taleb":          {"lens": "bear",      "display": "Nassim Taleb"},
    "ben_graham":            {"lens": "bear",      "display": "Ben Graham"},
    "aswath_damodaran":      {"lens": "valuation", "display": "Aswath Damodaran"},
}
SPECIALISTS = ["fundamentals", "growth", "valuation", "technicals", "sentiment", "news_sentiment"]
SIGNAL_VALUE = {"bullish": 1.0, "neutral": 0.5, "bearish": 0.0}
IMPUTE_MAX_SWING = 0.20  # a full-conviction bull implies fair value ~20% over price; a bear ~20% under


def _load(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _num(x):
    return float(x) if isinstance(x, (int, float)) else None


def _conf01(c):
    """Normalize confidence to 0-1, accepting either 0-1 fractions or 0-100 integers
    (different panel runs have emitted both scales)."""
    if isinstance(c, (int, float)):
        return c if 0 < c <= 1 else c / 100.0
    return 0.5


def extract_persona_anchors(persona_id, key_metrics):
    pts = []
    if not isinstance(key_metrics, dict):
        return pts
    for k, v in key_metrics.items():
        kl = k.lower()
        if any(s in kl for s in ("pct", "momentum", "margin", "ratio", "yield")):
            continue
        if any(s in kl for s in ("value_per_share", "intrinsic", "graham_number", "downside_target",
                                 "fair_value", "price_target")):
            val = _num(v)
            if val is not None and val > 0:
                pts.append({"key": k, "kind": "graham" if "graham" in kl else "persona",
                            "value": round(val, 2), "metric": k.replace("_", " ").replace("per share", "").strip()})
    return pts


def persona_fair_value(p, price):
    """One analyst's implied fair value: stated number if it's a sane price target, else imputed from signal."""
    signal = (p.get("signal") or "neutral").lower()
    conf01 = _conf01(p.get("confidence"))
    km = p.get("key_metrics") or {}
    explicit = None
    if isinstance(km, dict):
        for k, v in km.items():
            kl = k.lower()
            if any(s in kl for s in ("pct", "ratio", "margin", "yield", "momentum")):
                continue
            if any(s in kl for s in ("intrinsic", "fair_value", "value_per_share", "price_target", "downside_target")):
                val = _num(v)
                if val is not None and val > 0:
                    explicit = val
                    break
    # Use a stated anchor if it's a plausible fair value (0.25x-4x price). This keeps a
    # legitimately-bearish DCF (~40% below price) while still dropping absurd deep-value
    # screens like a Graham Number that sits at a tiny fraction of price.
    if explicit is not None and price and 0.25 * price <= explicit <= 4.0 * price:
        return round(explicit, 2), "stated"
    if not price:
        return (round(explicit, 2), "stated") if explicit else (None, None)
    direction = (SIGNAL_VALUE.get(signal, 0.5) - 0.5) * 2  # +1 bull / 0 neutral / -1 bear
    fv = price * (1 + direction * IMPUTE_MAX_SWING * conf01)
    return round(fv, 2), "imputed"


METHOD_WEIGHT = 0.6  # weight per concrete valuation method (vs personas weighted by confidence)


def compute_consensus(personas_out, spec_val, valuation, price):
    """Confidence-weighted consensus fair value.

    Two kinds of voter:
      * the 13 personas (signal-aware sentiment; stated fair value where given, else imputed vs price,
        capped at +/-20% so a single analyst can't run away), weighted by confidence;
      * the CONCRETE valuation methods (the specialist's DCF / owner-earnings / EV-EBITDA /
        residual-income + the peer-multiple cross-check), which carry the TRUE magnitude and so let a
        genuinely over- or under-valued name register (e.g. a peak-cycle stock the methods value at a
        fraction of price). Method values are clamped to 0.1x-5x price so one wild method can't dominate.
    """
    rows, num, den = [], 0.0, 0.0
    for p in personas_out:
        fv, basis = persona_fair_value(p, price)
        if fv is None:
            continue
        cw = _conf01(p.get("confidence"))      # confidence IS the weight (handles 0-1 or 0-100)
        num += cw * fv
        den += cw
        rows.append({"source": p["id"], "display": p["display"], "signal": p["signal"],
                     "confidence": p.get("confidence"), "fair_value": fv, "basis": basis,
                     "confidence_weight": round(cw, 3)})

    def _clamp(v):
        return max(0.1 * price, min(5.0 * price, v)) if price else v

    methods = []
    if valuation:
        cc = (valuation.get("cross_check") or {}).get("outputs", {}).get("implied_px")
        if cc is not None:
            methods.append(("Relative (peer multiple)", cc))
        pm_out = (valuation.get("primary_method", {}) or {}).get("outputs", {}) or {}
        m_name = (valuation.get("primary_method", {}) or {}).get("name", "DCF")
        # DCF exposes outputs.implied_px; DDM (banks) exposes blended_implied_value / top-level blended_target.
        base_val = pm_out.get("implied_px") or pm_out.get("blended_implied_value") or valuation.get("blended_target")
        if base_val is not None:
            methods.append((f"{m_name} (base)" if m_name != "DCF" else "FCFF DCF (base)", base_val))
    if spec_val:
        r = spec_val.get("reasoning", {}) if isinstance(spec_val.get("reasoning"), dict) else {}
        for key, label in [("dcf_analysis", "Specialist DCF"), ("owner_earnings_analysis", "Owner Earnings"),
                           ("ev_ebitda_analysis", "EV/EBITDA"), ("residual_income_analysis", "Residual Income")]:
            v = _num((r.get(key) or {}).get("implied_value_per_share"))
            if v is not None and v > 0:
                methods.append((label, v))
    for label, v in methods:
        vc = _clamp(v)
        num += METHOD_WEIGHT * vc
        den += METHOD_WEIGHT
        note = "valuation method" + (f" (clamped from {v:.0f})" if abs(vc - v) > 1 else "")
        rows.append({"source": "valuation_method", "display": label, "signal": "method",
                     "confidence": int(METHOD_WEIGHT * 100), "fair_value": round(vc, 2),
                     "basis": note, "confidence_weight": METHOD_WEIGHT})

    consensus = round(num / den, 2) if den else None
    rows.sort(key=lambda x: x["fair_value"])
    return consensus, rows


def build_football_field(valuation, spec_val, persona_signals, current_price):
    ff = []
    if valuation:
        base_px = (valuation.get("primary_method", {}) or {}).get("outputs", {}).get("implied_px")
        scen = {s.get("label", "").lower(): s.get("implied_px") for s in valuation.get("scenarios", [])}
        lows = [p for p in [scen.get("bear"), base_px, scen.get("bull")] if p is not None]
        if base_px is not None:
            ff.append({"label": "FCFF DCF (Damodaran)", "source": "aswath_damodaran", "kind": "dcf",
                       "low": min(lows) if lows else base_px, "base": base_px,
                       "high": max(lows) if lows else base_px,
                       "note": "One analyst's rigorous DCF. The headline target is the panel consensus, not this bar."})
        cc = valuation.get("cross_check") or {}
        cc_px = (cc.get("outputs") or {}).get("implied_px")
        if cc_px is not None:
            ff.append({"label": cc.get("name", "Peer multiple (relative)"), "source": "relative",
                       "kind": "relative", "low": cc_px, "base": cc_px, "high": cc_px})
    if spec_val:
        r = spec_val.get("reasoning", {}) if isinstance(spec_val.get("reasoning"), dict) else {}
        for key, label, kind in [("owner_earnings_analysis", "Owner Earnings", "owner_earnings"),
                                  ("ev_ebitda_analysis", "EV/EBITDA (trailing)", "ev_ebitda"),
                                  ("residual_income_analysis", "Residual Income", "residual_income")]:
            v = (r.get(key) or {}).get("implied_value_per_share")
            if v is not None:
                ff.append({"label": label, "source": "valuation_specialist", "kind": kind,
                           "low": v, "base": v, "high": v})
    for pid, sig in persona_signals.items():
        if pid == "aswath_damodaran":
            continue
        for a in extract_persona_anchors(pid, sig.get("key_metrics")):
            disp = PERSONAS.get(pid, {}).get("display", pid)
            ff.append({"label": f"{disp} - {a['metric']}", "source": pid, "kind": a["kind"],
                       "low": a["value"], "base": a["value"], "high": a["value"]})
    ff.sort(key=lambda e: e["base"])
    return ff


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ticker", required=True)
    ap.add_argument("--dir", required=True)
    args = ap.parse_args()
    T, d = args.ticker, args.dir
    sigdir = os.path.join(d, "_signals")

    narrative = _load(os.path.join(d, f"{T}.json")) or {}
    valuation = _load(os.path.join(d, f"{T}_valuation.json")) or {}

    persona_signals = {pid: _load(os.path.join(sigdir, f"{pid}.json")) for pid in PERSONAS}
    persona_signals = {k: v for k, v in persona_signals.items() if v}
    spec_signals = {sp: _load(os.path.join(sigdir, f"_{sp}.json")) for sp in SPECIALISTS}
    spec_signals = {k: v for k, v in spec_signals.items() if v}
    risk = _load(os.path.join(sigdir, "_risk.json")) or {}
    spec_val = spec_signals.get("valuation")

    counts = {"bullish": 0, "neutral": 0, "bearish": 0}
    personas_out = []
    for pid, meta in PERSONAS.items():
        sig = persona_signals.get(pid, {})
        signal = (sig.get("signal") or "neutral").lower()
        if signal not in SIGNAL_VALUE:
            signal = "neutral"
        counts[signal] += 1
        personas_out.append({"id": pid, "display": meta["display"], "lens": meta["lens"],
                             "signal": signal, "confidence": sig.get("confidence"),
                             "reasoning": sig.get("reasoning", ""), "key_metrics": sig.get("key_metrics", {}),
                             "data_gaps": sig.get("data_gaps", [])})

    specialists_out = []
    for sp in SPECIALISTS:
        s = spec_signals.get(sp)
        if not s:
            continue
        reasoning = s.get("reasoning")
        summary = reasoning if isinstance(reasoning, str) else (reasoning.get("summary") if isinstance(reasoning, dict) else "")
        specialists_out.append({"id": sp, "signal": s.get("signal"), "confidence": s.get("confidence"),
                                "score": s.get("score"), "summary": summary or "",
                                "detail": reasoning if isinstance(reasoning, dict) else None})

    current_price = (narrative.get("recommendation", {}) or {}).get("current_price") or valuation.get("current_price")

    # THE one signal: confidence-weighted consensus fair value -> action
    consensus_target, consensus_rows = compute_consensus(personas_out, spec_val, valuation, current_price)
    if consensus_target is not None and current_price:
        consensus_upside = round((consensus_target - current_price) / current_price * 100, 1)
        consensus_action = "BUY" if consensus_upside > 10 else "SELL" if consensus_upside < -10 else "HOLD"
    else:
        consensus_upside = None
        consensus_action = (narrative.get("recommendation", {}) or {}).get("action", "HOLD")
    consensus_tone = {"BUY": "positive", "SELL": "negative"}.get(consensus_action, "neutral")

    _cur = "IDR " if narrative.get("currency") == "IDR" else "$"
    def _px(v):
        return f"{_cur}{v:,.0f}" if isinstance(v, (int, float)) else "n/a"
    _dcf_px = (valuation.get("primary_method", {}) or {}).get("outputs", {}).get("implied_px")
    if consensus_rows and consensus_target is not None and current_price:
        _hi = list(reversed(consensus_rows[-2:]))
        _lo = consensus_rows[:2]
        _bulls = ", ".join(f"{r['display'].split(' (')[0]} {_px(r['fair_value'])}" for r in _hi)
        _bears = ", ".join(f"{r['display'].split(' (')[0]} {_px(r['fair_value'])}" for r in _lo)
        _rel = "above" if consensus_upside > 2 else "below" if consensus_upside < -2 else "right at"
        rationale_text = (f"Confidence-weighted analyst consensus fair value {_px(consensus_target)} "
                          f"({consensus_upside:+.1f}% vs {_px(current_price)}); {consensus_action}. The constructive lens "
                          f"({_bulls}) sits above today's price, the valuation-cautious lens ({_bears}) below; the "
                          f"confidence-weighted center lands {_rel} the market price.")
        derivation_text = (f"{counts['bullish']} constructive / {counts['neutral']} neutral / {counts['bearish']} cautious. "
                           f"The 12m target is the confidence-weighted consensus of every analyst's fair value, not a vote "
                           f"and not any single model ({_px(consensus_target)}); it sits {_rel} the {_px(current_price)} price, "
                           f"so the call is {consensus_action}. The strict harsh-WACC FCFF DCF ({_px(_dcf_px)}) is one bar on "
                           f"the field and is carried as the headline valuation risk.")
    else:
        rationale_text = (narrative.get("recommendation", {}) or {}).get("rationale", "")
        derivation_text = (narrative.get("ahf_panel", {}) or {}).get("recommendation_derivation", "")

    football = build_football_field(valuation, spec_val, persona_signals, current_price)
    methods = [{"name": e["label"], "source": e["source"], "kind": e["kind"], "implied_px": e["base"],
                "range": [e["low"], e["high"]] if e["low"] != e["high"] else None}
               for e in football if e["kind"] in ("dcf", "relative", "owner_earnings", "ev_ebitda", "residual_income")]

    ahf_panel = narrative.get("ahf_panel", {}) or {}
    dcf_blended = valuation.get("blended_target")
    panel = {
        "schema_version": "ahf-1.2",
        "ticker": T, "name": narrative.get("name", T), "currency": narrative.get("currency", "USD"),
        "as_of_date": narrative.get("date"), "engine": "srqt2/ai-hedge-fund (translated)",
        "recommendation": {"action": consensus_action, "target_12m": consensus_target,
                           "upside_pct": consensus_upside, "current_price": current_price,
                           "basis": "confidence-weighted analyst consensus fair value",
                           "dcf_blended_reference": dcf_blended},
        "consensus": {
            "bullish": counts["bullish"], "neutral": counts["neutral"], "bearish": counts["bearish"],
            "consensus_target": consensus_target, "consensus_upside_pct": consensus_upside,
            "method": "Confidence-weighted mean of each analyst's fair value (stated where given, else imputed "
                      "from signal vs price, max +/-20% at full conviction). No fixed per-analyst weights; "
                      "confidence is the weight. No vote threshold.",
            "top_bull_persona": (ahf_panel.get("consensus", {}) or {}).get("top_bull_persona"),
            "top_bull_reason": (ahf_panel.get("consensus", {}) or {}).get("top_bull_reason"),
            "top_bear_persona": (ahf_panel.get("consensus", {}) or {}).get("top_bear_persona"),
            "top_bear_reason": (ahf_panel.get("consensus", {}) or {}).get("top_bear_reason"),
            "recommendation_derivation": derivation_text,
        },
        "consensus_breakdown": consensus_rows,
        "method_choice": ahf_panel.get("method_choice", {}),
        "football_field": football, "valuation_methods": methods,
        "personas": personas_out, "specialists": specialists_out,
        "risk_manager": {"structural_concerns": risk.get("structural_concerns", []),
                         "key_risks": risk.get("key_risks", []),
                         "position_limit_pct": risk.get("position_limit_pct")},
        "pm_synthesis": {"thesis": narrative.get("thesis", []), "rationale": rationale_text,
                         "bear_paragraph": narrative.get("bear_paragraph", "")},
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    with open(os.path.join(d, f"{T}_panel.json"), "w", encoding="utf-8") as f:
        json.dump(panel, f, indent=2, ensure_ascii=False)

    if narrative:
        rec = narrative.setdefault("recommendation", {})
        if consensus_target is not None:
            rec["action"] = consensus_action
            rec["target_12m"] = consensus_target
            rec["upside_pct"] = consensus_upside
            rec["tone"] = consensus_tone
            rec["rationale"] = rationale_text
        scen_rows = []
        inp = (valuation.get("primary_method", {}) or {}).get("inputs", {})
        bw = (inp.get("wacc", {}) or {}).get("value")
        bg = (inp.get("terminal_growth", {}) or {}).get("value")
        for s in valuation.get("scenarios", []):
            kc = s.get("key_changes", {}) or {}
            w = kc.get("wacc", bw)
            g = kc.get("terminal_g", kc.get("terminal_growth", bg))
            scen_rows.append({"scenario": s.get("label"),
                              "wacc": f"{w*100:.1f}%" if isinstance(w, (int, float)) else str(w),
                              "terminal_g": f"{g*100:.1f}%" if isinstance(g, (int, float)) else str(g),
                              "fcf_path": s.get("reasoning", "")[:120], "implied_px": s.get("implied_px")})
        if scen_rows:
            narrative["dcf_scenarios"] = scen_rows
        ap_block = narrative.setdefault("ahf_panel", {})
        ap_block.pop("weighted_score", None)  # remove the old contradictory vote score
        ap_block["recommendation_derivation"] = derivation_text
        ap_block["consensus_target"] = consensus_target
        ap_block["consensus_upside_pct"] = consensus_upside
        ap_block["consensus_method"] = panel["consensus"]["method"]
        ap_block["consensus"] = {**ap_block.get("consensus", {}), "bullish": counts["bullish"],
                                 "neutral": counts["neutral"], "bearish": counts["bearish"]}
        ap_block["football_field"] = football
        ap_block["dcf_blended_reference"] = dcf_blended
        with open(os.path.join(d, f"{T}.json"), "w", encoding="utf-8") as f:
            json.dump(narrative, f, indent=2, ensure_ascii=False)

    print(f"[OK] {T}: {counts['bullish']}b/{counts['neutral']}n/{counts['bearish']}r  "
          f"CONSENSUS ${consensus_target} ({consensus_upside}%) -> {consensus_action}   (DCF ref ${dcf_blended})")
    for r in consensus_rows:
        print(f"       {r['display']:30s} {r['signal']:8s} ${r['fair_value']:>8.1f}  {r['basis']:18s} conf={r['confidence']}")


if __name__ == "__main__":
    main()
