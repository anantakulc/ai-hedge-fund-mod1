# Indium Phosphide (InP) export-control chokepoint — AI data centre overlay

> Light Value-Chain-Alpha overlay for the AHF panel. Source: Reuters, "China's control over
> indium phosphide exports threatens AI data centre rollout," Laurie Chen & Liam Mo, 2026-06-11
> (full text supplied by user). Use as **shared market context** every panelist is aware of.
> NOT a signal file — personas may read this; it does not violate signal-independence.

## The event (facts from the article)

- **InP = indium phosphide**, a III-V compound substrate. Core material for **photonics**: high-speed
  optical chips / lasers / transceivers (800G/1.6T datacom optics, coherent optics). Article: **"no
  substitute"** — data centres are moving from copper (electrical) to optical (photonic) interconnect.
- **China has throttled InP export licences since February 2025.** China = **70% of global indium
  output** (2024, USGS). Beijing is extending its rare-earth "materials chokepoint" playbook upstream:
  condition the *substrate/compound*, not the finished module, to pace the whole optical ecosystem.
- **Substrate supply is concentrated:** Sumitomo Electric (5802.T) ~40%, **AXT (AXTI) ~35%** → together
  ~80%; JX Advanced Metals (5016.T) ~10%. **AXT makes most of its InP substrate IN CHINA** → directly
  caught by the licence regime (first export permits only arrived June 2024; large backlog).
- **Price:** a 6-inch InP wafer is **+250% to ~$5,000** since the restrictions began.
- **Demand is white-hot:** Lumentum (LITE) **sold out through 2028** despite quadrupling output.
- **Substitution is slow:** new InP plants take **2-3 years**. Coherent is **doubling its Texas InP
  wafer capacity in 2026 and plans to more than double again by end-2027**. Non-China sourcing =
  Sumitomo / JX, but Sumitomo consumes most of its output internally → global market stays undersupplied.
- **Money is already moving:** **Nvidia invested $2B each into Coherent (COHR) and Lumentum (LITE) in
  March**; Marvell bought Celestial AI (photonics). Qualification cycles are long → incumbents sticky.
- Analyst framing: SemiAnalysis (K. Wang) — "InP is one of several supply-chain bottlenecks
  collectively gating AI data-centre buildouts." Albright Stonebridge (P. Triolo) — "materials
  chokepoint toolkit."

## Chain map (mine → substrate → device → system → power)

indium metal (China 70%) → **InP substrate** (Sumitomo / AXT-in-China / JX) → **InP lasers & EMLs /
photonic ICs** (Coherent, Lumentum, VPEC, LandMark) → **optical transceivers / co-packaged optics /
optical DSP** (Coherent, Lumentum; AVGO optical DSP+CPO) → **AI networking hardware** (Celestica builds
800G/1.6T switches) → **AI clusters / hyperscalers** (NVDA systems; AVGO/MRVL custom silicon) →
**data-centre power & grid** (Vistra, GE Vernova).

The chokepoint bites hardest at the **substrate** node and ripples downstream: device makers with
**captive substrate + non-China supply win share/pricing**; system & compute names face a **gating
risk** to optical scale-out; power names see only a **deferred, second-order** effect.

## Per-ticker exposure (this panel's 15 names)

| Ticker | Node | Exposure | Direction | One-line rationale |
|---|---|---|---|---|
| **COHR** | InP laser/transceiver + **captive Texas InP fab** | **HIGH** | **Mixed → net Tailwind** | Most InP-levered name in the panel. Headwind: warned of InP shortage (May), AXT-supplied, wafer +250%. Tailwind: NVDA's $2B, demand sold-out, **doubling own Texas InP capacity 2026 / again by 2027**, sticky qualification cycles → share + pricing power for whoever owns supply. Execution risk on the ramp. |
| **NVDA** | AI systems; optical interconnect / silicon photonics | **MED** | Headwind (mitigated) | InP is a *gating* bottleneck for optical scale-out (CPO switches), but NVDA is **proactively de-risking** ($2B each into COHR+LITE). Demand >> supply; substitutable over time. Risk factor, not thesis-breaker. |
| **AVGO** | Optical DSP / PAM4 / co-packaged optics; switch silicon | **MED** | Headwind (minor) | Mostly CMOS not InP, but CPO + optics-attach exposure. If optical modules are supply-gated, networking attach/ramp paces at the margin. |
| **CLS** | Builds 800G/1.6T AI networking hardware (consumes optical modules) | **MED** | Headwind (passed through) | Optical-module tightness can disrupt build schedules/mix; largely passed to customers but a real near-term supply-chain risk to AI hardware revenue cadence. |
| **CBRS** | RESOLVE in-panel | **TBD** | TBD | alpha: classify from the actual business. If optical/photonics/networking → HIGH/Mixed; if not → LOW. Do not assume. |
| **TSM** | Silicon foundry; silicon photonics (COUPE) integrates III-V lasers | **LOW-MED** | Headwind (indirect) | Direct InP exposure low (silicon, not III-V), but indirect if the optics bottleneck slows AI wafer-demand growth; COUPE silicon-photonics roadmap touches III-V lasers. |
| **MU** | HBM / DRAM (silicon) | **LOW** | Headwind (indirect) | No direct InP. Only via a hypothetical AI-buildout slowdown denting HBM demand — currently supply-constrained, demand robust. |
| **VST** | Power producer levered to data-centre load | **LOW** | Headwind (deferred) | If InP gates DC rollout, marginal hit to the power-demand-growth narrative; immaterial near-term, structural demand intact. |
| **GEV** | Grid / power equipment for data centres | **LOW** | Headwind (deferred) | Same as VST — second-order, deferred, immaterial near-term. |
| **NOW** | Enterprise SaaS | **NONE** | Neutral | No supply-chain exposure; only third-order AI-capex-sentiment beta. |
| **BBCA / BBRI / BMRI / BBNI** | Indonesian banks | **NONE** | Neutral | Zero direct exposure; negligible EM-flow sentiment third-order. |
| **ANTM** | Indonesian miner (Ni / Au / bauxite) | **LOW** | Mixed / thematic Tailwind | Not an indium producer (indium is a Zn/Sn by-product), so no direct InP link. But the "China weaponises critical-mineral exports" theme raises the strategic value of non-China mineral suppliers → thematic sentiment tailwind only. |

## How the panel should use this (instruction for alpha / PM)

- Inject the relevant **one-line rationale** into every persona's dispatch as shared context. Personas
  still reach their own conclusions independently.
- **risk_manager**: add the InP chokepoint to `structural_concerns` / `key_risks` where exposure is
  MED+ (COHR, NVDA, AVGO, CLS, CBRS-if-optical). Severity scales with the table.
- **portfolio_manager**: where exposure is HIGH/MED, this belongs in `bear_breakers` (supply/cost gating)
  AND, for COHR specifically, in `bull_catalysts` (captive InP + NVDA backing + pricing power). For
  LOW/NONE names, mention only if a persona raised it; do not manufacture relevance.
- **data_gap to carry:** exact licence scope / quota figures and any post-2026-06-11 developments were
  not machine-fetched (source paywalled to the fetch tool; event post-dates model training). Magnitudes
  above are analyst-inferred from the supplied article text + known optical supply-chain structure.
