"""AHF-native Excel renderer: football field + per-method calc + agent-attributed assumptions.

Diverges deliberately from GER's _schema/render_excel.py (single-method DCF workbook).
GER's renderer is left untouched; this is AHF-only.

Tabs: Cover | Football Field (+chart) | DCF (Damodaran) | Owner Earnings | EV/EBITDA |
      Residual Income | Panel (13 personas + 6 specialists) | Assumptions

Usage:
    python _ahf/render_excel_ahf.py --ticker AVGO --dir output/AVGO
Reads:  <dir>/<T>.json, <dir>/<T>_valuation.json, <dir>/<T>_panel.json
Writes: <dir>/<T>.xlsx
"""

import argparse
import json
import os

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.chart import BarChart, Reference
from openpyxl.chart.shapes import GraphicalProperties
from openpyxl.utils import get_column_letter

ENGINE = "srqt2/ai-hedge-fund (translated)"

# palette
INK = "111827"; SUB = "6B7280"; LINE = "E5E7EB"; HEADBG = "F3F4F6"
GREEN = "166534"; RED = "991B1B"; BLUE = "2563EB"; AMBER = "B45309"
H1 = Font(name="Calibri", size=16, bold=True, color=INK)
H2 = Font(name="Calibri", size=12, bold=True, color=INK)
LBL = Font(name="Calibri", size=9, bold=True, color=SUB)
BODY = Font(name="Calibri", size=10, color=INK)
SMALL = Font(name="Calibri", size=9, color=SUB)
WHITE = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
thin = Side(style="thin", color=LINE)
BORDER = Border(left=thin, right=thin, top=thin, bottom=thin)
WRAP = Alignment(wrap_text=True, vertical="top")
RIGHT = Alignment(horizontal="right")


def _load(p):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _hdr(ws, row, cols, widths=None):
    for i, c in enumerate(cols, start=1):
        cell = ws.cell(row=row, column=i, value=c)
        cell.font = LBL
        cell.fill = PatternFill("solid", fgColor=HEADBG)
        cell.border = BORDER
    if widths:
        for i, w in enumerate(widths, start=1):
            ws.column_dimensions[get_column_letter(i)].width = w


def _money(cur, v):
    if v is None:
        return "n/a"
    if cur == "IDR":
        return f"IDR {v:,.0f}"
    return f"${v:,.2f}" if abs(v) < 100 else f"${v:,.0f}"


def cover(ws, narr, val, panel):
    cur = narr.get("currency", "USD")
    rec = narr.get("recommendation", {})
    cons = panel.get("consensus", {})
    ws.column_dimensions["A"].width = 26
    ws.column_dimensions["B"].width = 70
    rows = [
        (f"{narr.get('ticker','')} - {narr.get('name','')}", H1),
        (narr.get("sector", ""), SMALL),
        ("", BODY),
        ("Engine", ENGINE),
        ("Recommendation", f"{rec.get('action','')}  ({rec.get('tone','')})"),
        ("Current price", _money(cur, rec.get("current_price"))),
        ("12m target (DCF blend)", f"{_money(cur, rec.get('target_12m'))}  ({rec.get('upside_pct','')}%)"),
        ("Primary method", panel.get("method_choice", {}).get("primary", "DCF (FCFF, Damodaran)")),
        ("Method rationale", panel.get("method_choice", {}).get("rationale", "")),
        ("", BODY),
        ("Panel distribution", f"{cons.get('bullish',0)} constructive / {cons.get('neutral',0)} neutral / {cons.get('bearish',0)} cautious (of 13) - descriptive only"),
        ("Consensus fair value", f"{_money(cur, cons.get('consensus_target'))}  ({cons.get('consensus_upside_pct','')}% vs price)  ->  {rec.get('action','')}"),
        ("Top bull", f"{cons.get('top_bull_persona','')}: {cons.get('top_bull_reason','')}"),
        ("Top bear", f"{cons.get('top_bear_persona','')}: {cons.get('top_bear_reason','')}"),
        ("How the call was reached", cons.get("recommendation_derivation", "")),
        ("", BODY),
        ("Position limit (risk mgr)", f"{panel.get('risk_manager',{}).get('position_limit_pct','n/a')}%"),
        ("For research only", "Not financial advice. Valuation math is deterministic; assumptions are the panel's."),
    ]
    r = 1
    for item in rows:
        label, val2 = item
        if isinstance(val2, Font):
            c = ws.cell(row=r, column=1, value=label); c.font = val2
            ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=2)
        else:
            c1 = ws.cell(row=r, column=1, value=label); c1.font = LBL
            c2 = ws.cell(row=r, column=2, value=val2); c2.font = BODY; c2.alignment = WRAP
        r += 1


def football(ws, narr, panel):
    cur = narr.get("currency", "USD")
    ff = panel.get("football_field", [])
    price = panel.get("recommendation", {}).get("current_price")
    target = panel.get("recommendation", {}).get("target_12m")
    ws["A1"] = "Football field - implied value per share by agent / method"
    ws["A1"].font = H2
    ws["A2"] = ("Each row is an independent valuation lens from the panel. Bars span low-high; "
                "point methods show a single estimate. Compare to current price and the PM blended target.")
    ws["A2"].font = SMALL; ws["A2"].alignment = WRAP
    ws.merge_cells("A2:H2")

    hdr_row = 4
    _hdr(ws, hdr_row, ["Method / Agent", "Source", "Low", "Base", "High", "vs Price %", "Kind", "Note"],
         widths=[34, 20, 12, 12, 12, 12, 14, 50])
    r = hdr_row + 1
    # helper columns for the chart: offset (=low) and span (=high-low, min visible)
    span_min = (abs(price) * 0.012) if price else 1
    chart_start = r
    for e in ff:
        low, base, high = e.get("low"), e.get("base"), e.get("high")
        vs = ((base - price) / price * 100) if (price and base is not None) else None
        ws.cell(row=r, column=1, value=e.get("label")).font = BODY
        ws.cell(row=r, column=2, value=e.get("source")).font = SMALL
        ws.cell(row=r, column=3, value=low).font = BODY
        ws.cell(row=r, column=4, value=base).font = Font(size=10, bold=True, color=INK)
        ws.cell(row=r, column=5, value=high).font = BODY
        c6 = ws.cell(row=r, column=6, value=(round(vs, 1) if vs is not None else None))
        c6.font = Font(size=10, color=(GREEN if (vs or 0) >= 0 else RED)); c6.alignment = RIGHT
        ws.cell(row=r, column=7, value=e.get("kind")).font = SMALL
        ws.cell(row=r, column=8, value=e.get("note", "")).font = SMALL
        ws.cell(row=r, column=8).alignment = WRAP
        # chart helpers (cols J, K) — category label carries the number
        rng = f"${base:,.0f}" if low == high else f"${low:,.0f}-{high:,.0f}"
        ws.cell(row=r, column=10, value=f"{e.get('label')[:28]}  {rng}")
        ws.cell(row=r, column=11, value=low)
        ws.cell(row=r, column=12, value=max((high or low) - (low or 0), span_min))
        r += 1
    # reference rows: current price + PM target
    for label, v, col in [("Current price", price, AMBER), ("PM blended target", target, GREEN)]:
        if v is None:
            continue
        ws.cell(row=r, column=1, value=label).font = Font(size=10, bold=True, color=col)
        ws.cell(row=r, column=4, value=v).font = Font(size=10, bold=True, color=col)
        ws.cell(row=r, column=10, value=f">> {label}  ${v:,.0f}")
        ws.cell(row=r, column=11, value=max(v - span_min / 2, 0))
        ws.cell(row=r, column=12, value=span_min)
        r += 1
    chart_end = r - 1

    # Build the floating-bar chart
    if chart_end >= chart_start:
        chart = BarChart()
        chart.type = "bar"          # horizontal
        chart.grouping = "stacked"
        chart.overlap = 100
        chart.title = "Football field (implied value per share)"
        chart.height = max(8, (chart_end - chart_start + 1) * 0.9)
        chart.width = 24
        chart.legend = None
        off = Reference(ws, min_col=11, min_row=hdr_row, max_row=chart_end)  # header at hdr_row blank -> use titles
        span = Reference(ws, min_col=12, min_row=hdr_row, max_row=chart_end)
        cats = Reference(ws, min_col=10, min_row=chart_start, max_row=chart_end)
        # put titles in the helper header
        ws.cell(row=hdr_row, column=11, value="offset")
        ws.cell(row=hdr_row, column=12, value="span")
        chart.add_data(off, titles_from_data=True)
        chart.add_data(span, titles_from_data=True)
        chart.set_categories(cats)
        chart.series[0].graphicalProperties = GraphicalProperties(solidFill="FFFFFF")
        chart.series[0].graphicalProperties.line.noFill = True
        chart.series[1].graphicalProperties = GraphicalProperties(solidFill=BLUE)
        chart.x_axis.delete = False
        chart.y_axis.delete = False
        ws.add_chart(chart, f"A{chart_end + 3}")
    # hide helper cols
    for col in ("J", "K", "L"):
        ws.column_dimensions[col].hidden = True


def dcf_tab(ws, narr, val):
    cur = narr.get("currency", "USD")
    pm = val.get("primary_method", {})
    inp = pm.get("inputs", {})
    out = pm.get("outputs", {})
    ws["A1"] = "DCF (FCFF) - Aswath Damodaran's inputs"; ws["A1"].font = H2
    ws["A2"] = pm.get("reasoning", ""); ws["A2"].font = SMALL; ws["A2"].alignment = WRAP
    ws.merge_cells("A2:H2")
    r = 4
    # WACC + terminal g with reasoning
    wacc = inp.get("wacc", {})
    comp = wacc.get("components", {})
    ws.cell(row=r, column=1, value="WACC").font = H2
    ws.cell(row=r, column=2, value=f"{wacc.get('value',0)*100:.2f}%").font = H2
    r += 1
    ws.cell(row=r, column=1, value="components").font = LBL
    ws.cell(row=r, column=2, value=", ".join(f"{k}={v}" for k, v in comp.items())).font = SMALL
    ws.cell(row=r, column=2).alignment = WRAP; ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=8)
    r += 1
    ws.cell(row=r, column=1, value="reasoning").font = LBL
    ws.cell(row=r, column=2, value=wacc.get("reasoning", "")).font = SMALL
    ws.cell(row=r, column=2).alignment = WRAP; ws.merge_cells(start_row=r, start_column=2, end_row=r+2, end_column=8)
    r += 4
    tg = inp.get("terminal_growth", {})
    ws.cell(row=r, column=1, value="Terminal growth").font = H2
    ws.cell(row=r, column=2, value=f"{tg.get('value',0)*100:.2f}%").font = H2
    r += 1
    ws.cell(row=r, column=1, value="reasoning").font = LBL
    ws.cell(row=r, column=2, value=tg.get("reasoning", "")).font = SMALL
    ws.cell(row=r, column=2).alignment = WRAP; ws.merge_cells(start_row=r, start_column=2, end_row=r+1, end_column=8)
    r += 3

    # FCFF build table
    fcff = out.get("fcff_build") or []
    if fcff:
        _hdr(ws, r, ["Year", "Revenue", "Growth", "EBIT mgn", "EBIT", "NOPAT", "D&A", "Capex", "dNWC", "FCFF"],
             widths=[10, 12, 10, 10, 10, 10, 10, 10, 10, 10])
        r += 1
        for y in fcff:
            ws.cell(row=r, column=1, value=y.get("year")).font = BODY
            ws.cell(row=r, column=2, value=y.get("revenue_b")).font = BODY
            ws.cell(row=r, column=3, value=(f"{y.get('ebit_margin')*100:.0f}%" if y.get("ebit_margin") else ""))
            ws.cell(row=r, column=4, value=(f"{y.get('ebit_margin')*100:.0f}%" if y.get("ebit_margin") else ""))
            ws.cell(row=r, column=5, value=y.get("ebit_b")).font = BODY
            ws.cell(row=r, column=6, value=y.get("nopat_b")).font = BODY
            ws.cell(row=r, column=7, value=y.get("da_b")).font = BODY
            ws.cell(row=r, column=8, value=y.get("capex_b")).font = BODY
            ws.cell(row=r, column=9, value=y.get("wc_change_b")).font = BODY
            ws.cell(row=r, column=10, value=y.get("fcf_b")).font = Font(size=10, bold=True)
            r += 1
        r += 1
    # bridge
    ws.cell(row=r, column=1, value="PV explicit FCF").font = LBL
    ws.cell(row=r, column=2, value=out.get("pv_explicit_fcf_b")).font = BODY; r += 1
    ws.cell(row=r, column=1, value="PV terminal value").font = LBL
    ws.cell(row=r, column=2, value=out.get("pv_terminal_b")).font = BODY; r += 1
    ws.cell(row=r, column=1, value="Implied EV").font = LBL
    ws.cell(row=r, column=2, value=out.get("implied_ev_b")).font = BODY; r += 1
    ws.cell(row=r, column=1, value="Less net debt").font = LBL
    ws.cell(row=r, column=2, value=val.get("net_debt_b")).font = BODY; r += 1
    ws.cell(row=r, column=1, value="Implied price / share").font = H2
    ws.cell(row=r, column=2, value=_money(cur, out.get("implied_px"))).font = H2


def method_tab(ws, title, source, implied_px, cur, rows):
    ws["A1"] = title; ws["A1"].font = H2
    ws["A2"] = f"Source: {source}"; ws["A2"].font = SMALL
    ws.cell(row=4, column=1, value="Implied price / share").font = H2
    ws.cell(row=4, column=2, value=_money(cur, implied_px)).font = H2
    ws.column_dimensions["A"].width = 26; ws.column_dimensions["B"].width = 80
    r = 6
    for label, value in rows:
        ws.cell(row=r, column=1, value=label).font = LBL
        c = ws.cell(row=r, column=2, value=value); c.font = BODY; c.alignment = WRAP
        ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=8)
        r += 1


def panel_tab(ws, panel):
    ws["A1"] = "The panel - 13 personas + 6 specialists"; ws["A1"].font = H2
    cons = panel.get("consensus", {})
    ws["A2"] = (f"Weighted vote {cons.get('weighted_score','')} -> {cons.get('decision_from_vote','')}  |  "
                f"{cons.get('bullish',0)} bull / {cons.get('neutral',0)} neutral / {cons.get('bearish',0)} bear")
    ws["A2"].font = SMALL
    r = 4
    _hdr(ws, r, ["Persona", "Lens", "Signal", "Conf", "Reasoning"],
         widths=[22, 12, 10, 7, 99])
    r += 1
    for p in panel.get("personas", []):
        sig = p.get("signal", "")
        col = GREEN if sig == "bullish" else RED if sig == "bearish" else AMBER
        ws.cell(row=r, column=1, value=p.get("display")).font = BODY
        ws.cell(row=r, column=2, value=p.get("lens")).font = SMALL
        ws.cell(row=r, column=3, value=sig).font = Font(size=10, bold=True, color=col)
        ws.cell(row=r, column=4, value=p.get("confidence")).font = BODY
        c = ws.cell(row=r, column=5, value=(p.get("reasoning") or "")); c.font = SMALL; c.alignment = WRAP
        r += 1
    r += 2
    ws.cell(row=r, column=1, value="Computational specialists").font = H2; r += 1
    _hdr(ws, r, ["Specialist", "Signal", "Conf", "Summary"], widths=None)
    r += 1
    for s in panel.get("specialists", []):
        ws.cell(row=r, column=1, value=s.get("id")).font = BODY
        ws.cell(row=r, column=2, value=s.get("signal")).font = BODY
        ws.cell(row=r, column=3, value=s.get("confidence")).font = BODY
        c = ws.cell(row=r, column=6, value=(s.get("summary") or "")[:400]); c.font = SMALL; c.alignment = WRAP
        r += 1


def assumptions_tab(ws, val):
    ws["A1"] = "Assumptions - agent-attributed"; ws["A1"].font = H2
    ws["A2"] = "Every input and the agent whose reasoning set it. This is the A/B vs GER."; ws["A2"].font = SMALL
    r = 4
    _hdr(ws, r, ["Input", "Value", "Reasoning (agent-attributed)"], widths=[26, 14, 100])
    r += 1
    inp = val.get("primary_method", {}).get("inputs", {})
    wacc = inp.get("wacc", {})
    items = [("WACC", f"{wacc.get('value',0)*100:.2f}%", wacc.get("reasoning", "")),
             ("Terminal growth", f"{inp.get('terminal_growth',{}).get('value',0)*100:.2f}%",
              inp.get("terminal_growth", {}).get("reasoning", ""))]
    for y in inp.get("fcf_projections", []):
        items.append((f"FY{y.get('year')} FCF", f"{y.get('fcf_b')}B", y.get("rationale", "")))
    for label, value, reason in items:
        ws.cell(row=r, column=1, value=label).font = LBL
        ws.cell(row=r, column=2, value=value).font = BODY
        c = ws.cell(row=r, column=3, value=reason); c.font = SMALL; c.alignment = WRAP
        r += 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ticker", required=True)
    ap.add_argument("--dir", required=True)
    args = ap.parse_args()
    T, d = args.ticker, args.dir
    narr = _load(os.path.join(d, f"{T}.json"))
    val = _load(os.path.join(d, f"{T}_valuation.json"))
    panel = _load(os.path.join(d, f"{T}_panel.json"))
    cur = narr.get("currency", "USD")

    wb = Workbook()
    cover(wb.active, narr, val, panel); wb.active.title = "Cover"
    football(wb.create_sheet("Football Field"), narr, panel)
    dcf_tab(wb.create_sheet("DCF (Damodaran)"), narr, val)

    # per-method tabs from specialist detail (carried in panel.specialists)
    spec_detail = {}
    for s in panel.get("specialists", []):
        if s.get("id") == "valuation" and isinstance(s.get("detail"), dict):
            spec_detail = s["detail"]
    oe = spec_detail.get("owner_earnings_analysis", {})
    method_tab(wb.create_sheet("Owner Earnings"), "Owner Earnings", "valuation specialist",
               oe.get("implied_value_per_share"), cur,
               [("Gap vs price", f"{oe.get('gap_pct','')}%"), ("Detail", oe.get("details", ""))])
    ev = spec_detail.get("ev_ebitda_analysis", {})
    method_tab(wb.create_sheet("EV-EBITDA"), "EV / EBITDA (relative)", "valuation specialist",
               ev.get("implied_value_per_share"), cur,
               [("Historical median x", ev.get("historical_median_multiple", "")),
                ("Peer median x", ev.get("peer_median_multiple", "")),
                ("Gap vs price", f"{ev.get('gap_pct','')}%")])
    ri = spec_detail.get("residual_income_analysis", {})
    method_tab(wb.create_sheet("Residual Income"), "Residual Income", "valuation specialist",
               ri.get("implied_value_per_share"), cur,
               [("Book value / share", ri.get("book_value_per_share", "")),
                ("Cost of equity", f"{ri.get('cost_of_equity_pct','')}%"),
                ("Gap vs price", f"{ri.get('gap_pct','')}%")])

    panel_tab(wb.create_sheet("Panel"), panel)
    assumptions_tab(wb.create_sheet("Assumptions"), val)

    out = os.path.join(d, f"{T}.xlsx")
    wb.save(out)
    print(f"[OK] wrote {out}  ({len(wb.sheetnames)} tabs: {', '.join(wb.sheetnames)})")


if __name__ == "__main__":
    main()
