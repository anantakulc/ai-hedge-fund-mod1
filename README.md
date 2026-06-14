# ai-hedge-fund-mod1

An AI **investor panel** you run locally with [Claude Code](https://claude.ai/code). Thirteen
famous-investor personas — Buffett, Munger, Lynch, Fisher, Wood, Ackman, Pabrai, Druckenmiller,
Jhunjhunwala, Burry, Taleb, Graham, and Damodaran — plus six computational specialists analyze any
stock. A risk manager and a portfolio manager synthesize their views into a recommendation, and you
get a **panel-first PDF report** and an **Excel valuation workbook**.

Translated from [virattt/ai-hedge-fund](https://github.com/virattt/ai-hedge-fund) into Claude Code
subagents. It runs entirely on your machine — **no API keys**, free data via `yfinance`, nothing to deploy.

## What you get (per ticker, in `output/<TICKER>/`)

- **`<T>.pdf`** — leads with the **recommendation + thesis**, then **the panel**: every analyst's
  signal (bullish / neutral / bearish), confidence, and reasoning; the confidence-weighted consensus;
  and a valuation **"football field"** (each method/analyst's implied value per share). Business,
  valuation math, and risk detail come after.
- **`<T>.xlsx`** — the football field as a chart, per-method valuation tabs (DCF, owner earnings,
  EV/EBITDA, residual income), the full 13-analyst panel, and agent-attributed assumptions.

See **`examples/NVDA/`** for a complete worked example.

## Quick start

1. Install **Claude Code** (CLI, desktop app, or web at `claude.ai/code`) and clone this repo:
   ```bash
   git clone https://github.com/srqt2/ai-hedge-fund-mod1.git
   cd ai-hedge-fund-mod1
   pip install -r requirements.txt
   ```
2. Open the folder in Claude Code and just type a ticker:
   - US: `NVDA`, `AVGO`, or `research ASML`
   - Indonesia (IDX): `BBCA.JK`, `ASII.JK`, `research Chandra Asri` (TPIA.JK)
3. Claude reads `CLAUDE.md`, dispatches the `alpha` agent (the panel), and writes the PDF + Excel to
   `output/<TICKER>/`. A full run is ~13–20 minutes (the panel reasons through 19 analysts).

No keys required. If your Claude install has a finance-skills plugin it will use it; otherwise the
agents fetch prices and financials with the `yfinance` package you installed above.

## How it works

```
ticker ─▶ alpha
           ├─ 13 persona analysts  (each: signal + confidence + reasoning, independent)
           ├─ 6 specialists        (fundamentals, growth, valuation, technicals, sentiment, news)
           ├─ risk_manager         (structural concerns, key risks, position cap)
           └─ portfolio_manager    (synthesizes; the only agent that sees all signals)
                 │
                 ├─ dcf_compute.py / ddm_compute.py   (deterministic valuation math)
                 ├─ build_panel.py                    (confidence-weighted consensus + football field)
                 └─ render_report_pdf.py + render_excel_ahf.py
```

## Faithful to the original

Each persona emits an independent `{signal, confidence, reasoning}` and only the portfolio manager
combines them — the same contract as `virattt/ai-hedge-fund`. The headline recommendation and 12-month
target are the **confidence-weighted consensus** of the analysts' fair values (not a raw vote), and the
valuation is kept honest: real CAPM betas, no fabricated cash-flow multipliers (a validator enforces it).

## Notes

- **Method:** DCF for non-banks, DDM for banks. The engine never invents math — Python computes it from
  the LLM's stated, agent-attributed assumptions, so the same inputs always reproduce the same numbers.
- **Data:** `yfinance` (delayed / approximate). Anything that could not be fetched is listed in each
  report's `data_gaps`.
- **No deploy step.** This is a local research tool; the deliverable is the PDF + Excel.

## Disclaimer

For research and education only. **Not financial advice.** The personas are stylized approximations of
public investors, not those individuals. Do your own diligence.

## Credits

Personas and the analyst/PM framework are adapted from **[virattt/ai-hedge-fund](https://github.com/virattt/ai-hedge-fund)** (MIT).
This fork swaps the Python LLM-API harness for Claude Code subagents and adds a panel-first PDF, a
football-field Excel, and a confidence-weighted consensus layer. MIT licensed.
