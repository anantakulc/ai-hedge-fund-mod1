# ai-hedge-fund-mod1 — run the investor panel locally with Claude Code

A panel of **13 famous-investor personas + 6 computational specialists** debates any stock; a risk
manager and a portfolio manager synthesize; you get a **panel-first PDF report + a football-field Excel**
in `output/<TICKER>/`. Translated from [virattt/ai-hedge-fund](https://github.com/virattt/ai-hedge-fund)
into Claude Code subagents. Runs locally, no API keys (data via `yfinance`), no deploy.

## STOP — there is only one workflow

When the user types a ticker (e.g. `NVDA`), a company name, or "research X" / "do X", **dispatch the
`alpha` subagent.** It runs the whole cycle and produces the deliverable. Do not improvise another path.

## What `alpha` does (full spec in `.claude/agents/alpha.md`)

1. **Verify price** via `yfinance` (use the exchange suffix for non-US names, e.g. `BBCA.JK`, `ASII.JK`).
2. **Run the panel** — 13 personas + 6 specialists, each independent, then `risk_manager`, then
   `portfolio_manager`. If your Claude exposes a subagent-dispatch tool, fan them out in parallel;
   otherwise **emulate them sequentially** (reason in each persona's lens and write its
   `_signals/<name>.json` before the next, without reading the others). Never stop to ask about this.
3. **Compute valuation:** `python _schema/dcf_compute.py` (non-banks) or `python _schema/ddm_compute.py`
   (banks). LLM picks honest inputs; Python does the math.
4. **`python _ahf/build_panel.py`** — confidence-weighted consensus + the valuation football field.
5. **`python _schema/voice_clean.py`** — strip em-dashes / AI tells.
6. **`python _ahf/render_report_pdf.py` + `python _ahf/render_excel_ahf.py`** — the PDF + Excel.

## Output (in `output/<TICKER>/`)

- **`<T>.pdf`** — panel-first report: recommendation + thesis, then **THE PANEL** (13 analyst signals
  with confidence + reasoning, the consensus, the football field), then valuation / risks / business.
- **`<T>.xlsx`** — football-field workbook (Cover, Football Field + chart, per-method tabs, Panel, Assumptions).
- **`<T>.json` / `<T>_panel.json` / `<T>_valuation.json` / `<T>_inputs.json`** — the underlying data.

## Principles (faithful to ai-hedge-fund)

- Each analyst emits `{signal: bullish|bearish|neutral, confidence, reasoning}` **independently**; the
  portfolio manager is the only agent that reads all signals together.
- The **headline recommendation + 12m target is the confidence-weighted consensus** of the analysts'
  fair values (`build_panel.py`), NOT a raw vote threshold.
- **Honest valuation:** real CAPM beta (plus a country risk premium for non-US names), no fabricated
  `fcf_multiplier`; scenarios move via WACC / terminal-g / FCF-path. `_ahf/validate_inputs.py` enforces
  it; `_ahf/fix_units.py` auto-corrects a trillions/billions mismatch.
- **No web.** Prices + financials come from `yfinance` (the finance-skills plugin if your Claude has it,
  otherwise plain `python -c "import yfinance ..."`). Flag anything you could not fetch in `data_gaps`.

## Setup

```bash
pip install -r requirements.txt        # yfinance, openpyxl, reportlab, pandas
```
Then open this folder in Claude Code (CLI, desktop, or claude.ai/code) and type a ticker. See `README.md`.

## Layout

| Path | What |
|---|---|
| `.claude/agents/` | 22 agents: `alpha` + 13 personas + 6 specialists + `risk_manager` + `portfolio_manager` |
| `_schema/` | `dcf_compute.py`, `ddm_compute.py`, `sotp_compute.py`, `voice_clean.py` + `SPEC_v2.md` / `VALUATION_SCHEMA.md` / `VOICE.md` |
| `_ahf/` | `build_panel.py`, `render_report_pdf.py`, `render_excel_ahf.py`, `validate_inputs.py`, `fix_units.py` |
| `personas.yaml` | persona lenses + one-liners |
| `examples/NVDA/` | a complete worked example (PDF, Excel, all signals + JSON) |
| `output/` | your generated reports land here |
