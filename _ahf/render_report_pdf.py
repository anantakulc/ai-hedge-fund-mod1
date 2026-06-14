"""Panel-first PDF report for ai-hedge-fund-mod1.

Order, by design: (1) recommendation + thesis, (2) THE PANEL -- the 13 analyst signals with
confidence + reasoning (faithful to the original ai-hedge-fund output), the confidence-weighted
consensus, and the valuation football field, then (3) the details -- bull/bear cases, valuation
math, key risks, business overview, peers.

Reads:  <dir>/<T>.json (+ <T>_panel.json, <T>_valuation.json if present)
Writes: <dir>/<T>.pdf
Usage:  python _ahf/render_report_pdf.py --ticker NVDA --dir output/NVDA
"""

import argparse
import json
import os

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether)
from reportlab.graphics.shapes import Drawing, Rect, Line, String, Circle

INK = colors.HexColor("#111827"); SUB = colors.HexColor("#6B7280"); LINE = colors.HexColor("#E5E7EB")
GREEN = colors.HexColor("#166534"); RED = colors.HexColor("#991B1B"); AMBER = colors.HexColor("#854D0E")
BLUE = colors.HexColor("#2563EB"); BG = colors.HexColor("#F9FAFB")
KIND_COLOR = {"dcf": "#2563EB", "relative": "#7C3AED", "owner_earnings": "#0D9488", "ev_ebitda": "#B45309",
              "residual_income": "#0891B2", "persona": "#6B7280", "graham": "#991B1B", "method": "#2563EB"}
SIG = {"bullish": ("#DCFCE7", "#166534"), "bearish": ("#FEE2E2", "#991B1B"), "neutral": ("#FEF3C7", "#854D0E"),
       "method": ("#EFF6FF", "#1D4ED8")}

S = {
    "h1": ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=18, textColor=INK, leading=21),
    "name": ParagraphStyle("name", fontName="Helvetica", fontSize=12, textColor=INK, leading=15),
    "meta": ParagraphStyle("meta", fontName="Helvetica", fontSize=8.5, textColor=SUB, leading=11),
    "h2": ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=12.5, textColor=INK, leading=15,
                         spaceBefore=10, spaceAfter=2),
    "h2sub": ParagraphStyle("h2sub", fontName="Helvetica", fontSize=8, textColor=SUB, leading=10, spaceAfter=4),
    "body": ParagraphStyle("body", fontName="Helvetica", fontSize=9.5, textColor=INK, leading=13),
    "small": ParagraphStyle("small", fontName="Helvetica", fontSize=8.5, textColor=colors.HexColor("#374151"), leading=11),
    "tiny": ParagraphStyle("tiny", fontName="Helvetica", fontSize=7.5, textColor=SUB, leading=9.5),
    "pname": ParagraphStyle("pname", fontName="Helvetica-Bold", fontSize=9.5, textColor=INK, leading=12),
    "foot": ParagraphStyle("foot", fontName="Helvetica", fontSize=7.5, textColor=SUB, leading=10, alignment=1),
}


def _load(p):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def money(cur, v):
    if not isinstance(v, (int, float)):
        return "n/a"
    return (f"IDR {v:,.0f}" if cur == "IDR" else (f"${v:,.2f}" if abs(v) < 100 else f"${v:,.0f}"))


def esc(t):
    return (str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")) if t is not None else ""


def hr():
    t = Table([[""]], colWidths=[170 * mm])
    t.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -1), 0.5, LINE)]))
    return t


def football_drawing(panel, cur):
    bars = panel.get("football_field", [])
    price = (panel.get("recommendation", {}) or {}).get("current_price")
    target = (panel.get("recommendation", {}) or {}).get("target_12m")
    if not bars:
        return Spacer(1, 1)
    vals = [b["low"] for b in bars] + [b["high"] for b in bars]
    if isinstance(price, (int, float)):
        vals.append(price)
    if isinstance(target, (int, float)):
        vals.append(target)
    vmin, vmax = min(vals), max(vals)
    pad = (vmax - vmin) * 0.08 or 1
    dmin, dmax = vmin - pad, vmax + pad
    W, labelW, rowH, top, bot = 470, 150, 15, 26, 24
    plotW = W - labelW - 14
    H = top + len(bars) * rowH + bot
    d = Drawing(W, H)

    def x(v):
        return labelW + (v - dmin) / (dmax - dmin) * plotW

    for i in range(5):
        tv = dmin + (dmax - dmin) * i / 4
        xx = x(tv)
        d.add(Line(xx, bot, xx, H - top + 4, strokeColor=colors.HexColor("#F0F0F0"), strokeWidth=0.5))
        d.add(String(xx, bot - 9, money(cur, round(tv)), fontSize=6, fillColor=SUB, textAnchor="middle"))
    for v, col, lab in [(price, "#B45309", "Price"), (target, "#166534", "Target")]:
        if isinstance(v, (int, float)):
            d.add(Line(x(v), bot, x(v), H - 6, strokeColor=colors.HexColor(col), strokeWidth=1, strokeDashArray=[3, 2]))
            d.add(String(x(v), H - 5, f"{lab} {money(cur, v)}", fontSize=6.5, fillColor=colors.HexColor(col), textAnchor="middle"))
    for i, b in enumerate(bars):
        y = H - top - i * rowH - rowH / 2 + 3
        col = colors.HexColor(KIND_COLOR.get(b.get("kind"), "#6B7280"))
        lab = b.get("label", "")[:30]
        d.add(String(labelW - 6, y - 2, lab, fontSize=6.8, fillColor=colors.HexColor("#374151"), textAnchor="end"))
        if b["high"] > b["low"]:
            d.add(Rect(x(b["low"]), y - 4, max(x(b["high"]) - x(b["low"]), 1), 8, rx=2, ry=2,
                       fillColor=col, strokeColor=None, fillOpacity=0.30))
            d.add(Line(x(b["base"]), y - 6, x(b["base"]), y + 6, strokeColor=col, strokeWidth=2))
            d.add(String(x(b["high"]) + 4, y - 2, f"{money(cur, b['low'])}-{money(cur, b['high'])}", fontSize=6, fillColor=INK))
        else:
            d.add(Circle(x(b["base"]), y, 3.2, fillColor=col, strokeColor=None))
            d.add(String(x(b["base"]) + 6, y - 2, money(cur, b["base"]), fontSize=6.2, fillColor=INK))
    return d


def build(narr, panel, val, out_path):
    cur = narr.get("currency", "USD")
    rec = narr.get("recommendation", {}) or {}
    cons = panel.get("consensus", {}) or {}
    story = []

    # 1. HEADER + RECOMMENDATION
    story.append(Paragraph(f"{esc(narr.get('ticker',''))} &nbsp; {esc(narr.get('name',''))}", S["h1"]))
    story.append(Paragraph(f"{esc(narr.get('listings',''))} &middot; {esc(narr.get('sector',''))} &middot; "
                           f"Updated {esc(narr.get('date',''))} &middot; Engine: ai-hedge-fund-mod1", S["meta"]))
    story.append(Spacer(1, 7))
    action = rec.get("action", ""); up = rec.get("upside_pct")
    upst = f"{'+' if isinstance(up,(int,float)) and up>=0 else ''}{up}%" if up is not None else ""
    banner = [[Paragraph("<b>RECOMMENDATION</b><br/>" + esc(action), S["small"]),
               Paragraph("<b>CURRENT</b><br/>" + money(cur, rec.get("current_price")), S["small"]),
               Paragraph("<b>12M TARGET (consensus)</b><br/>" + money(cur, rec.get("target_12m")) + f" &nbsp;({upst})", S["small"]),
               Paragraph("<b>METHOD</b><br/>" + esc((panel.get("recommendation", {}) or {}).get("method") or
                         (panel.get("method_choice", {}) or {}).get("primary", "DCF")), S["small"])]]
    bt = Table(banner, colWidths=[42 * mm, 38 * mm, 52 * mm, 38 * mm])
    bt.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), BG), ("BOX", (0, 0), (-1, -1), 0.5, LINE),
                            ("INNERGRID", (0, 0), (-1, -1), 0.5, LINE), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                            ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                            ("LEFTPADDING", (0, 0), (-1, -1), 7)]))
    story.append(bt)

    # THESIS
    story.append(Paragraph("Thesis", S["h2"]))
    story.append(Paragraph("The whole bet in three bullets", S["h2sub"]))
    for t in narr.get("thesis", []):
        story.append(Paragraph("&bull; " + esc(t), S["body"]))
        story.append(Spacer(1, 2))

    # 2. THE PANEL (first)
    story.append(Spacer(1, 6))
    story.append(Paragraph("The panel", S["h2"]))
    story.append(Paragraph(esc(cons.get("method", "13 investor personas + 6 specialists; confidence-weighted consensus")), S["h2sub"]))
    b, n, r = cons.get("bullish", 0), cons.get("neutral", 0), cons.get("bearish", 0)
    summ = [[Paragraph(f"<b>{b}</b> bullish &nbsp; <b>{n}</b> neutral &nbsp; <b>{r}</b> bearish (of 13)", S["small"]),
             Paragraph("Consensus fair value <b>" + money(cur, cons.get("consensus_target") or rec.get("target_12m")) +
                       f"</b> ({upst})", S["small"])]]
    st = Table(summ, colWidths=[85 * mm, 85 * mm])
    st.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), BG), ("BOX", (0, 0), (-1, -1), 0.5, LINE),
                            ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                            ("LEFTPADDING", (0, 0), (-1, -1), 7)]))
    story.append(st)
    if cons.get("recommendation_derivation"):
        story.append(Spacer(1, 3))
        story.append(Paragraph(esc(cons["recommendation_derivation"]), S["small"]))

    # Football field
    story.append(Paragraph("Football field &mdash; implied value per share by analyst / method", S["h2"]))
    story.append(Paragraph("Dashed lines: current price (amber), consensus target (green)", S["h2sub"]))
    story.append(football_drawing(panel, cur))

    # Analyst signals, grouped (faithful to ai-hedge-fund: signal + confidence + reasoning)
    story.append(Paragraph("Analyst signals", S["h2"]))
    story.append(Paragraph("Each persona ran in its own lens; the synthesizer combined them last", S["h2sub"]))
    personas = panel.get("personas", [])
    order = {"bullish": 0, "neutral": 1, "bearish": 2}
    for grp in ("bullish", "neutral", "bearish"):
        members = [p for p in personas if (p.get("signal") or "neutral") == grp]
        if not members:
            continue
        story.append(Paragraph(grp.capitalize() + f" ({len(members)})", ParagraphStyle(
            "g", parent=S["small"], fontName="Helvetica-Bold", textColor=SIG[grp][1], spaceBefore=4)))
        for p in members:
            bg, fg = SIG.get(p.get("signal"), SIG["neutral"])
            conf = p.get("confidence")
            head = (f"<b>{esc(p.get('display'))}</b> &nbsp;<font color='#9CA3AF'>{esc(p.get('lens'))}</font> &nbsp;"
                    f"<font color='{fg}'><b>{esc((p.get('signal') or '').upper())}</b></font>"
                    + (f" <font color='#9CA3AF'>(conf {conf})</font>" if conf is not None else ""))
            blk = [Paragraph(head, S["small"]), Paragraph(esc(p.get("reasoning", "")), S["tiny"])]
            story.append(KeepTogether(blk))
            story.append(Spacer(1, 3))

    # Specialists
    specs = panel.get("specialists", [])
    if specs:
        story.append(Paragraph("Computational specialists", S["h2"]))
        for sp in specs:
            sg = (sp.get("signal") or "neutral")
            fg = SIG.get(sg, SIG["neutral"])[1]
            story.append(Paragraph(f"<b>{esc(sp.get('id'))}</b> <font color='{fg}'>{esc(sg)}</font>"
                                   + (f" (conf {sp.get('confidence')})" if sp.get('confidence') is not None else "")
                                   + " &nbsp;" + esc((sp.get("summary") or "")[:240]), S["tiny"]))
            story.append(Spacer(1, 1))

    # Risk manager
    rm = panel.get("risk_manager", {}) or {}
    if rm.get("structural_concerns") or rm.get("key_risks"):
        story.append(Paragraph("Risk manager", S["h2"]))
        pl = rm.get("position_limit_pct")
        if pl is not None:
            story.append(Paragraph(f"Position limit: <b>{pl}%</b>", S["small"]))
        for s in (rm.get("structural_concerns") or [])[:6]:
            story.append(Paragraph("&bull; " + esc(s), S["tiny"]))

    # 3. DETAILS
    story.append(Spacer(1, 6))
    story.append(hr())
    story.append(Paragraph("Bull catalysts", S["h2"]))
    for c in narr.get("bull_catalysts", []):
        story.append(Paragraph(f"<b>{c.get('id','')}. {esc(c.get('title',''))}</b> &nbsp;" + esc(c.get("body", "")), S["small"]))
        story.append(Spacer(1, 2))
    story.append(Paragraph("Bear thesis-breakers", S["h2"]))
    for c in narr.get("bear_breakers", []):
        story.append(Paragraph(f"<b>{c.get('id','')}. {esc(c.get('title',''))}</b> &nbsp;" + esc(c.get("body", "")), S["small"]))
        story.append(Spacer(1, 2))
    if narr.get("bear_paragraph"):
        story.append(Paragraph("Bear case in one paragraph", ParagraphStyle("bp", parent=S["small"], fontName="Helvetica-Bold", textColor=RED, spaceBefore=3)))
        story.append(Paragraph(esc(narr["bear_paragraph"]), S["small"]))

    # Valuation methods + scenarios
    vm = panel.get("valuation_methods", [])
    if vm:
        story.append(Paragraph("Valuation methods", S["h2"]))
        data = [["Method", "Source", "Implied / share"]]
        for m in vm:
            rng = m.get("range")
            px = f"{money(cur, rng[0])} - {money(cur, rng[1])}" if rng else money(cur, m.get("implied_px"))
            data.append([esc(m.get("name")), esc(m.get("source")), px])
        t = Table(data, colWidths=[70 * mm, 55 * mm, 45 * mm])
        t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F3F4F6")),
                               ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 8),
                               ("LINEBELOW", (0, 0), (-1, -1), 0.4, LINE), ("ALIGN", (2, 0), (2, -1), "RIGHT"),
                               ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
        story.append(t)
    scen = narr.get("dcf_scenarios", [])
    if scen:
        story.append(Paragraph("Scenarios", S["h2"]))
        data = [["Scenario", "WACC", "Terminal g", "Implied px"]]
        for s in scen:
            data.append([esc(s.get("scenario")), esc(s.get("wacc")), esc(s.get("terminal_g")), money(cur, s.get("implied_px"))])
        t = Table(data, colWidths=[40 * mm, 30 * mm, 35 * mm, 40 * mm])
        t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F3F4F6")),
                               ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 8),
                               ("LINEBELOW", (0, 0), (-1, -1), 0.4, LINE), ("ALIGN", (3, 0), (3, -1), "RIGHT"),
                               ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
        story.append(t)
    # Key assumptions (agent-attributed)
    inp = (val.get("primary_method", {}) or {}).get("inputs", {}) or {}
    wacc = inp.get("wacc", {}) or {}
    if wacc.get("reasoning") or inp.get("terminal_growth"):
        story.append(Paragraph("Key assumptions (agent-attributed)", S["h2"]))
        if wacc.get("value") is not None:
            story.append(Paragraph(f"<b>WACC {wacc['value']*100:.2f}%</b> &nbsp;" + esc(wacc.get("reasoning", "")), S["tiny"]))
        tg = inp.get("terminal_growth", {}) or {}
        if tg.get("value") is not None:
            story.append(Paragraph(f"<b>Terminal g {tg['value']*100:.2f}%</b> &nbsp;" + esc(tg.get("reasoning", "")), S["tiny"]))

    # Key risks
    kr = narr.get("key_risks", [])
    if kr:
        story.append(Paragraph("Key structural risks", S["h2"]))
        for r0 in kr:
            story.append(Paragraph(f"<b>[{esc(r0.get('category',''))}] {esc(r0.get('title',''))}</b> &nbsp;" + esc(r0.get("description", "")), S["tiny"]))
            story.append(Spacer(1, 1))

    # Business overview
    bo = narr.get("business_overview")
    if isinstance(bo, dict) and bo.get("summary"):
        story.append(Paragraph("Business overview", S["h2"]))
        story.append(Paragraph(esc(bo.get("summary")), S["small"]))

    # Data gaps
    dg = narr.get("data_gaps", [])
    if dg:
        story.append(Paragraph("Data gaps", S["h2"]))
        for g in dg:
            story.append(Paragraph("&bull; " + esc(g), S["tiny"]))

    story.append(Spacer(1, 10))
    story.append(Paragraph("Engine: ai-hedge-fund-mod1 (13-persona panel + 6 specialists, translated from "
                           "virattt/ai-hedge-fund). Analysts ran independently; the portfolio manager synthesized last. "
                           "For research only. Not financial advice.", S["foot"]))

    SimpleDocTemplate(out_path, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm,
                      topMargin=15 * mm, bottomMargin=14 * mm,
                      title=f"{narr.get('ticker','')} - ai-hedge-fund-mod1").build(story)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ticker", required=True)
    ap.add_argument("--dir", required=True)
    ap.add_argument("--output")
    a = ap.parse_args()
    T, d = a.ticker, a.dir
    narr = _load(os.path.join(d, f"{T}.json"))
    panel = _load(os.path.join(d, f"{T}_panel.json"))
    val = _load(os.path.join(d, f"{T}_valuation.json"))
    out = a.output or os.path.join(d, f"{T}.pdf")
    build(narr, panel, val, out)
    print(f"[OK] wrote {out}")


if __name__ == "__main__":
    main()
