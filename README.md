# Composio Research Agent

An agent pipeline that researched 100 apps across 10 categories (CRM/Sales, Support, Communications, Marketing/Ads, Ecommerce, Data/SEO/Scraping, Developer/Infra, Productivity, Finance/Fintech, AI/Research) for AI-agent-toolkit buildability: auth method, self-serve vs. gated access, API surface, and whether an MCP server exists. Results were independently checked through three separate verification methods, then rendered into a single-page case study.

- **Live case study:** `LIVE_URL_HERE`
- **This repo:** `https://github.com/anniecoder212/composio-research-agent`

## Quickstart

Prerequisites: Python 3.10+, a Composio API key, an Anthropic API key.

```bash
git clone https://github.com/anniecoder212/composio-research-agent.git
cd composio-research-agent
pip install composio composio-claude-agent-sdk claude-agent-sdk python-dotenv
```

Create a `.env` file in the repo root (never commit this — it's already in `.gitignore`):

```
COMPOSIO_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here
```

Get a Composio key at composio.dev, an Anthropic key at console.anthropic.com.

## Running it

**1. Research all 100 apps:**
```bash
python3 research_pipeline_v4.py
```
Resumable — safe to stop and rerun; already-completed apps are skipped and only failures retry. Writes `results/research_results.csv` and `results/raw_results.jsonl` (append-only log, one line per app as it completes).

**2. Verify a sample automatically:**
```bash
python3 verify_loop.py
```
Same agent pattern as step 1, but pointed at the *existing* results instead of discovering new ones — it independently re-checks each claim via live web search and reports HIT / PARTIAL / WRONG. Writes `verification_results.csv`.

**3. Rebuild the case study page (optional — `index.html` is already committed):**
```bash
python3 build_page.py
```
Reads `research_results_clean.csv`, regenerates `index.html` as a single self-contained file (data, styles, and interactive table filtering all inline, no external dependencies).

## Files

| File | What it is |
|---|---|
| `research_pipeline_v4.py` | The research agent — final, working version. Composio SDK (`composio_search`, no-auth web search) + Claude Agent SDK, run per app. |
| `research_pipeline_v3.py` | An earlier version, kept for the reliability story below. |
| `verify_loop.py` | Automated verification loop — re-checks existing claims rather than discovering new ones. |
| `test_setup.py` | Minimal script to confirm API keys and SDK wiring work before running the full pipeline. |
| `research_results_clean.csv` | Final 100-row dataset — the source of truth. Columns: `num, app, category, description, auth, self_serve, gated_reason, api_surface, mcp_exists, buildability_verdict, blocker, evidence_url, confidence`. |
| `results/research_results.csv`, `results/raw_results.jsonl` | Raw pipeline output, before cleanup/corrections. |
| `verification_results.csv` | Output of the automated verification loop. |
| `build_page.py` | Generates `index.html` from `research_results_clean.csv`. The only thing that should write `index.html`. |
| `index.html` | The single-page case study: findings, patterns, the agent, proof, and verification. |

## Engineering reliability arc

Three real runs, not a hypothetical: **43/100 -> 63/100 -> 100/100** successful completions, driven by real bugs found and fixed along the way — a per-app budget cap that was too tight, a bug where failed apps were wrongly marked "done" (which would have silently blocked retries), and an unchecked `is_error` flag on the Claude Agent SDK's `ResultMessage` that let empty failed results through as if they were valid. Full writeup is on the case study page.

## Verification

Three independent, non-overlapping methods:
1. A manual AI-assisted web-search check (15 apps)
2. A fully automated agent-based verification loop — `verify_loop.py` (15 apps)
3. A human spot-check, no AI assistance (10 apps, across two rounds)

Results, including the real corrections each pass found, are on the case study page.

## Notes for anyone (or any agent) picking this up

`research_results_clean.csv` is the single source of truth for all 100 rows — edit it directly if you find and confirm a correction, don't hand-edit `index.html`. Re-running `research_pipeline_v4.py` or `verify_loop.py` is safe and idempotent; both skip rows already marked done and only retry failures.
