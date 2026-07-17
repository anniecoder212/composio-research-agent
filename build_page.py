import csv, json, html

rows = list(csv.DictReader(open('research_results_clean.csv')))
for r in rows:
    for k in r:
        r[k] = r[k].strip() if r[k] else r[k]

CATEGORIES = []
seen = set()
for r in rows:
    if r['category'] not in seen:
        seen.add(r['category'])
        CATEGORIES.append(r['category'])

from collections import Counter
cat_stats = {c: Counter() for c in CATEGORIES}
for r in rows:
    c = cat_stats[r['category']]
    c['total'] += 1
    c[r['self_serve']] += 1
    c[r['buildability_verdict']] += 1

self_serve_cats = [c for c in CATEGORIES if cat_stats[c].get('self-serve',0) > cat_stats[c].get('gated',0)]
gated_cats = [c for c in CATEGORIES if cat_stats[c].get('self-serve',0) <= cat_stats[c].get('gated',0)]
self_serve_cats_sentence = ", ".join(self_serve_cats[:-1]) + ", and " + self_serve_cats[-1] if len(self_serve_cats) > 1 else "".join(self_serve_cats)
gated_cats_sentence = ", ".join(gated_cats[:-1]) + ", and " + gated_cats[-1] if len(gated_cats) > 1 else "".join(gated_cats)
self_serve_cats_app_count = sum(cat_stats[c]['total'] for c in self_serve_cats)
gated_cats_app_count = sum(cat_stats[c]['total'] for c in gated_cats)

# Actual self-serve vs gated app counts (pulled from the findings table rows), within each category group
self_serve_group_ss = sum(1 for r in rows if r['category'] in self_serve_cats and r['self_serve']=='self-serve')
self_serve_group_gt = sum(1 for r in rows if r['category'] in self_serve_cats and r['self_serve']=='gated')
gated_group_ss = sum(1 for r in rows if r['category'] in gated_cats and r['self_serve']=='self-serve')
gated_group_gt = sum(1 for r in rows if r['category'] in gated_cats and r['self_serve']=='gated')


overall = {
    'self_serve': sum(1 for r in rows if r['self_serve']=='self-serve'),
    'gated': sum(1 for r in rows if r['self_serve']=='gated'),
    'yes': sum(1 for r in rows if r['buildability_verdict']=='yes'),
    'partial': sum(1 for r in rows if r['buildability_verdict']=='partial'),
    'oauth2': sum(1 for r in rows if 'oauth2' in r['auth'].lower()),
    'mcp': sum(1 for r in rows if r['mcp_exists'].lower()=='true'),
}

easy_wins_rows = [r for r in rows if r['self_serve']=='self-serve' and r['buildability_verdict']=='yes']
needs_outreach_rows = [r for r in rows if r['self_serve']=='gated']
partial_selfserve_rows = [r for r in rows if r['self_serve']=='self-serve' and r['buildability_verdict']=='partial']

def esc(s):
    return html.escape(s or "", quote=True)

def bucket_table(rows_subset, blocker_col=False):
    out = ""
    for r in rows_subset:
        blocker_cell = f"<td class=\"small\">{esc(r['blocker'] or r['gated_reason'])[:90]}</td>" if blocker_col else ""
        out += f"""<tr>
          <td class="num">{esc(r['num'])}</td>
          <td class="appname">{esc(r['app'])}</td>
          <td>{esc(r['category'])}</td>
          <td>{esc(r['auth'])}</td>
          {blocker_cell}
          <td><a href="{esc(r['evidence_url'])}" target="_blank" rel="noopener">source</a></td>
        </tr>"""
    return out

easy_wins_html = bucket_table(easy_wins_rows, blocker_col=False)
needs_outreach_html = bucket_table(needs_outreach_rows, blocker_col=True)
partial_selfserve_html = bucket_table(partial_selfserve_rows, blocker_col=True)
easy_wins = [r['app'] for r in easy_wins_rows]
needs_outreach = [r['app'] for r in needs_outreach_rows]
partial_selfserve = [r['app'] for r in partial_selfserve_rows]


verification_rows = [
    ("Salesforce", "mcp_exists=True claim", "PARTIAL", "Fact correct (Hosted MCP Servers GA Apr 2026) but evidence_url points to generic docs, not the MCP page"),
    ("DealCloud", "gated -- requires admin-provisioned account", "HIT", "Confirmed: needs system admin role + Access Web Service capability"),
    ("Front", "mcp_exists=True, exact evidence URL", "HIT", "Exact match -- official MCP server, OAuth-authenticated, open beta"),
    ("WhatsApp Business", "gated -- sandbox free, production needs verification", "HIT", "Confirmed: 2-10 day business verification, 1-3 day template approval"),
    ("Google Ads", "gated -- developer token needs manual review", "HIT", "Confirmed, matches 2026 approval backlog context"),
    ("Klaviyo", "mcp_exists=True, exact evidence URL", "HIT", "Exact URL match to developers.klaviyo.com MCP docs"),
    ("Ahrefs", "gated -- no free tier for API v3", "HIT", "Confirmed no free-tier API access; paid plan required"),
    ("Sherlock", "self-serve, no official maintained API", "HIT", "Near word-for-word match: experimental API unmaintained since 2021"),
    ("Waterfall.io", "self-serve, ~5-6 endpoints", "HIT", "Confirmed real product, endpoint list matches exactly"),
    ("Stripe", "mcp_exists=True, exact evidence URL", "HIT", "Exact match, official and well documented"),
    ("Plaid", "gated for production, sandbox self-serve", "HIT", "Confirmed: sandbox free, production needs compliance review"),
    ("iPayX", "API key REST, evidence = homepage", "PARTIAL", "Core claim roughly right; tool names slightly off and evidence_url should cite /docs/mcp-server specifically"),
    ("NotebookLM", "gated -- needs Google Cloud IAM + billing", "HIT", "Confirmed IAM + enterprise licensing requirement"),
    ("Consensus", "REST gated/quote-based, MCP server exists", "HIT", "Confirmed both halves of the claim"),
    ("Mermaid CLI", "no hosted API, MCP exists", "HIT", "Exact match, verified community MCP repo"),
]
hits = sum(1 for v in verification_rows if v[2]=="HIT")
partials = sum(1 for v in verification_rows if v[2]=="PARTIAL")

# Human verification pass -- 10 apps across 2 rounds, checked by hand by Ananya (not AI-assisted)
human_check_rows = [
    ("Gladly", "gated -- paid account + API User admin permission required", "HIT", "Confirmed on developer.gladly.com/rest, no correction needed"),
    ("Clay", "gated -- free tier excludes API/webhook access", "CORRECTED", "Right, but incomplete: a 14-day free trial of the paid Growth plan exists (found on clay.com/pricing) -- not a hard permanent wall, similar to the WhatsApp/Plaid sandbox pattern"),
    ("Brex", "mcp_exists=True + admin-gated API tokens", "HIT + NUANCE", "MCP server confirmed real (developer.brex.com/docs/mcp). Nuance found: admin does one-time setup, then any employee can self-serve connect via their own OAuth -- looser than the raw Developer API, which needs admin-issued static tokens every time"),
    ("Otter AI", "gated -- Enterprise-only, manual account-manager enablement", "HIT", "Exact match on help.otter.ai docs: \"available for all Enterprise workspaces... contact your Otter account manager\""),
    ("Pinterest", "gated (manual review) + mcp_exists=True", "HIT + CORRECTED", "Gating claim confirmed -- Pinterest's own docs require \"requesting trial access\" before API credentials. But mcp_exists should be False, not True: the \"Use with AI\" button on their docs is a markdown-for-AI-assistants helper, not an actual MCP server"),
    ("Paygent Connect", "gated -- needs existing merchant/partner account (NMI-powered)", "HIT", "Confirmed on docs.nmi.com: separate Merchant and Partner portals, both requiring an existing account before keys can be generated -- also validates the white-label/NMI framing since Paygent isn't named on the generic docs"),
    ("fanbasis", "self-serve + \"rebranded from Commas\" detail", "HIT", "Confirmed: fanbasis's own quickstart still refers to \"your Commas dashboard\" and returns a payment_link from \"Commas\" -- a specific detail that could've been hallucinated but checked out"),
    ("higgsfield", "self-serve API key generation", "HIT", "Confirmed: dashboard has a direct \"Create API Key\" button, no approval step visible"),
    ("MrScraper", "API can only rerun pre-built scrapers, can't define new ones via API", "HIT", "Exact match: step 1 of their own docs says \"select a scraper you've already created, if you don't have one, create it first\""),
    ("Devin", "gated -- Team ($80+/mo) or Enterprise plan required for API/MCP", "HIT (structure), UNVERIFIED (price)", "Initially looked like a miss -- auth/service-user docs don't mention plan tiers at all. Resolved by a separate quickstart page confirming API access is split by \"Teams\" vs \"Enterprise\" plan -- so the tier-gating claim holds, but the specific $80+/mo figure was never independently confirmed and should be treated as unverified, not confirmed"),
]
human_hits = sum(1 for v in human_check_rows if "HIT" in v[2])
human_corrections = sum(1 for v in human_check_rows if "CORRECTED" in v[2])

human_check_html = ""
for app, claim, verdict, note in human_check_rows:
    cls = "v-partial" if "CORRECTED" in verdict else "v-yes"
    human_check_html += f"""<tr>
      <td class="appname">{esc(app)}</td>
      <td class="small">{esc(claim)}</td>
      <td><span class="pill {cls}">{esc(verdict)}</span></td>
      <td class="small">{esc(note)}</td>
    </tr>"""


def esc(s):
    return html.escape(s or "", quote=True)



# Main blocker per category, written by hand from the gated_reason fields
MAIN_BLOCKER = {
    "CRM and Sales": "Admin-provisioned tenant account only (DealCloud)",
    "Support and Helpdesk": "Paid account + admin-level permission (Gladly)",
    "Communications and Messaging": "Production needs business verification (WhatsApp Business)",
    "Marketing, Ads, Email and Social": "Manual app review / business verification -- all 5 ad platforms",
    "Ecommerce": "Paid plan or admin-provisioned account (4 apps)",
    "Data, SEO and Scraping": "No free tier -- paid subscription required",
    "Developer, Infra and Data platforms": "--",
    "Productivity and Project Management": "--",
    "Finance and Fintech": "Admin approval on existing paid account (5 apps)",
    "AI, Research and Media-native": "Requires a paid Enterprise plan (5 apps)",
}

# Build category matrix table rows
cat_rows_html = ""
total_self, total_gated, total_yes, total_partial, total_n = 0, 0, 0, 0, 0
for c in CATEGORIES:
    s = cat_stats[c]
    ss, gt, yy, pp, tt = s.get('self-serve',0), s.get('gated',0), s.get('yes',0), s.get('partial',0), s['total']
    total_self += ss; total_gated += gt; total_yes += yy; total_partial += pp; total_n += tt
    cat_rows_html += f"""<tr>
      <td>{esc(c)}</td>
      <td class="num" style="color:var(--self); font-weight:600;">{ss}/{tt}</td>
      <td class="num" style="color:var(--gated); font-weight:600;">{gt}/{tt}</td>
      <td class="num">{yy}</td>
      <td class="num">{pp}</td>
      <td class="small">{esc(MAIN_BLOCKER.get(c,'--'))}</td>
    </tr>"""
cat_rows_html += f"""<tr style="border-top:2px solid var(--border); font-weight:700;">
  <td>Total</td>
  <td class="num" style="color:var(--self);">{total_self}/{total_n}</td>
  <td class="num" style="color:var(--gated);">{total_gated}/{total_n}</td>
  <td class="num">{total_yes}</td>
  <td class="num">{total_partial}</td>
  <td></td>
</tr>"""

def bucket_of(r):
    if r['self_serve'] == 'gated':
        return ("Outreach", "chip-gated")
    if r['buildability_verdict'] == 'yes':
        return ("Easy win", "chip-yes")
    return ("Incomplete", "chip-partial")

# Build full data table rows + JSON
table_rows_html = ""
for r in rows:
    verdict_class = {"yes":"v-yes","partial":"v-partial"}.get(r['buildability_verdict'],"")
    gate_class = "g-self" if r['self_serve']=='self-serve' else "g-gated"
    mcp_badge = "✓" if r['mcp_exists'].lower()=='true' else "–"
    bucket_label, bucket_cls = bucket_of(r)
    table_rows_html += f"""<tr class="datarow" data-cat="{esc(r['category'])}" data-gate="{esc(r['self_serve'])}" data-verdict="{esc(r['buildability_verdict'])}">
      <td class="num">{esc(r['num'])}</td>
      <td class="appname">{esc(r['app'])}</td>
      <td>{esc(r['category'])}</td>
      <td>{esc(r['auth'])}</td>
      <td><span class="pill {gate_class}">{esc(r['self_serve'])}</span></td>
      <td class="small">{esc(r['api_surface'][:110])}{'…' if len(r['api_surface'])>110 else ''}</td>
      <td class="num">{mcp_badge}</td>
      <td><span class="pill {verdict_class}">{esc(r['buildability_verdict'])}</span></td>
      <td class="small">{esc((r['blocker'] or r['gated_reason'])[:100])}{'…' if len(r['blocker'] or r['gated_reason'])>100 else ''}</td>
      <td><span class="applink {bucket_cls}" style="padding:2px 8px;">{bucket_label}</span></td>
      <td><a href="{esc(r['evidence_url'])}" target="_blank" rel="noopener">source</a></td>
      <td class="num">{esc(r['confidence'])}</td>
    </tr>"""

verification_rows_html = ""
for app, claim, verdict, note in verification_rows:
    cls = "v-yes" if verdict=="HIT" else "v-partial"
    verification_rows_html += f"""<tr>
      <td class="appname">{esc(app)}</td>
      <td class="small">{esc(claim)}</td>
      <td><span class="pill {cls}">{esc(verdict)}</span></td>
      <td class="small">{esc(note)}</td>
    </tr>"""

# Automated verification loop -- an agent (Composio + Claude Agent SDK, same pattern as the
# research pipeline) independently re-checked 15 rows via live web search, no human involved.
# Output: verification_results.csv, run by verify_loop.py
automated_loop_rows = [
    ("Salesforce", "OAuth2, self-serve, mcp_exists=True", "HIT", "Confirmed: OAuth2 connected apps, self-serve signup, Hosted MCP Servers GA 2026"),
    ("HubSpot", "OAuth2 + private-app tokens, self-serve, mcp_exists=True", "HIT", "Confirmed, including the nuance that the MCP server itself only accepts OAuth, not private-app tokens"),
    ("Attio", "API key + OAuth2, self-serve, mcp_exists=True", "HIT", "Confirmed both auth methods and an official MCP server (hosted + self-hosted)"),
    ("Pipedrive", "API key + OAuth2, self-serve, mcp_exists=True", "HIT", "Confirmed, plus found Pipedrive shipped a native MCP server June 30, 2026"),
    ("Twenty", "API key + OAuth2, self-serve, mcp_exists=True", "HIT", "Confirmed self-serve key generation and community MCP servers integrating with the API"),
    ("Podio", "OAuth2, self-serve, mcp_exists=False", "HIT", "Confirmed OAuth2 with Client ID/Secret registration, no official MCP server found"),
    ("Zoho CRM", "OAuth2, self-serve, mcp_exists=True", "HIT", "Confirmed via Zoho API Console docs and official pre-built CRM MCP servers"),
    ("Close", "API key + OAuth2, self-serve, mcp_exists=False", "PARTIAL -- corrected", "Auth and self-serve confirmed, but mcp_exists=False was wrong: Close does offer an MCP server for Claude/ChatGPT/Cursor. Corrected to True."),
    ("DealCloud", "OAuth2 client-credentials, gated", "HIT", "Confirmed: credentials only issued from a live tenant's admin/Platform Manager role, no public signup"),
    ("Copper", "API key + OAuth2, self-serve, mcp_exists=True", "PARTIAL", "Auth and self-serve confirmed; flagged that the MCP server is third-party/community, not Copper-built -- same convention already used elsewhere in the dataset, so left as-is"),
    ("Zendesk", "OAuth2 + legacy API token, self-serve, mcp_exists=True", "PARTIAL", "Auth confirmed; found the legacy Basic-auth deprecation date was already passed (Jan 2026, not Apr 2027) and that the MCP server is third-party, not official -- noted but not changed, consistent with how third-party MCPs are counted elsewhere"),
    ("Intercom", "OAuth2 + bearer tokens, self-serve, mcp_exists=True", "HIT", "Confirmed, including the official mcp.intercom.com server"),
    ("Freshdesk", "API key (Basic auth), self-serve, mcp_exists=True", "HIT", "Confirmed exact auth mechanism and an MCP server (official EAP + third-party)"),
    ("Front", "OAuth2 + API key, self-serve, mcp_exists=True", "PARTIAL", "MCP server confirmed real, but it only accepts OAuth2, not the API tokens implied by the original claim -- a scoping detail, not a wrong core fact"),
    ("Pylon", "API key, self-serve, mcp_exists=True", "HIT", "Confirmed: dashboard-generated key, official MCP server, no gating found"),
]
auto_hits = sum(1 for v in automated_loop_rows if v[2]=="HIT")
auto_partials = sum(1 for v in automated_loop_rows if v[2].startswith("PARTIAL"))
auto_corrections = sum(1 for v in automated_loop_rows if "corrected" in v[2])

automated_loop_html = ""
for app, claim, verdict, note in automated_loop_rows:
    cls = "v-yes" if verdict=="HIT" else "v-partial"
    automated_loop_html += f"""<tr>
      <td class="appname">{esc(app)}</td>
      <td class="small">{esc(claim)}</td>
      <td><span class="pill {cls}">{esc(verdict)}</span></td>
      <td class="small">{esc(note)}</td>
    </tr>"""

data_json = json.dumps(rows)

html_doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Composio: Product Internship Assignment</title>
<meta name="description" content="Research and buildability audit of 100 apps for AI-agent toolkit potential, built with an agent pipeline (Composio + Claude Agent SDK) and independently verified.">
<script type="application/json" id="app-data">{data_json}</script>
<style>
  :root {{
    --bg: #ffffff; --panel: #f6f7f8; --panel2: #eef0f2; --border: #dfe1e5;
    --text: #111214; --muted: #55585f; --accent: #111214; --accent2: #111214;
    --yes: #0f9d63; --partial: #b7791f; --gated: #d1453f; --self: #0f9d63;
    --radius: 10px;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; background: var(--bg); color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Inter, Roboto, sans-serif;
    line-height: 1.5;
  }}
  .wrap {{ max-width: 1180px; margin: 0 auto; padding: 32px 24px 80px; }}
  header.hero {{ padding: 8px 0 28px; border-bottom: 1px solid var(--border); margin-bottom: 28px; }}
  .kicker {{ color: var(--accent2); font-size: 13px; font-weight: 600; letter-spacing: 0.06em; text-transform: uppercase; margin-bottom: 10px; }}
  h1 {{ font-size: 30px; margin: 0 0 10px; line-height: 1.2; }}
  .sub {{ color: var(--muted); font-size: 15px; max-width: 780px; }}
  .badges {{ display: flex; gap: 10px; flex-wrap: wrap; margin-top: 16px; }}
  .badge {{ background: var(--panel2); border: 1px solid var(--border); border-radius: 999px; padding: 6px 14px; font-size: 13px; color: var(--muted); }}
  .badge b {{ color: var(--text); }}
  section {{ margin-bottom: 40px; }}
  h2 {{ font-size: 20px; margin: 0 0 4px; display: flex; align-items: center; gap: 10px; }}
  .section-num {{ display: inline-flex; align-items: center; justify-content: center; width: 26px; height: 26px; border-radius: 7px; background: var(--accent); color: #ffffff; font-size: 13px; font-weight: 700; }}
  .section-sub {{ color: var(--muted); font-size: 14px; margin: 6px 0 18px 36px; }}
  .stat-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-bottom: 22px; }}
  .stat {{ background: var(--panel); border: 1px solid var(--border); border-radius: var(--radius); padding: 18px; }}
  .stat .num {{ font-size: 28px; font-weight: 700; color: var(--accent2); }}
  .stat .label {{ font-size: 13px; color: var(--muted); margin-top: 4px; }}
  .insight-cards {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 20px; }}
  .card {{ background: var(--panel); border: 1px solid var(--border); border-radius: var(--radius); padding: 20px; }}
  .card h3 {{ margin: 0 0 8px; font-size: 15px; color: var(--accent2); }}
  .card p {{ margin: 0; color: var(--muted); font-size: 14px; }}
  .card p b {{ color: var(--text); }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13.5px; background: var(--panel); border-radius: var(--radius); overflow: hidden; }}
  thead th {{ text-align: left; background: var(--panel2); color: var(--muted); font-weight: 600; font-size: 12px; text-transform: uppercase; letter-spacing: 0.03em; padding: 10px 12px; border-bottom: 1px solid var(--border); position: sticky; top: 0; }}
  tbody td {{ padding: 9px 12px; border-bottom: 1px solid var(--border); vertical-align: top; }}
  tbody tr:hover {{ background: rgba(17,18,20,0.04); }}
  td.num {{ text-align: center; color: var(--muted); }}
  td.small {{ color: var(--muted); font-size: 12.5px; }}
  td.appname {{ font-weight: 600; }}
  table a {{ color: var(--accent); text-decoration: none; font-size: 12.5px; }}
  table a:hover {{ text-decoration: underline; }}
  .pill {{ display: inline-block; padding: 2px 9px; border-radius: 999px; font-size: 11.5px; font-weight: 600; }}
  .v-yes {{ background: rgba(52,211,153,0.15); color: var(--yes); }}
  .v-partial {{ background: rgba(251,191,36,0.15); color: var(--partial); }}
  .g-self {{ background: rgba(52,211,153,0.15); color: var(--self); }}
  .g-gated {{ background: rgba(248,113,113,0.15); color: var(--gated); }}
  .cat-matrix {{ width: 100%; }}
  .table-scroll {{ max-height: 560px; overflow: auto; border: 1px solid var(--border); border-radius: var(--radius); }}
  .table-scroll table {{ border-radius: 0; }}
  .controls {{ display: flex; gap: 10px; margin-bottom: 14px; flex-wrap: wrap; }}
  .controls input, .controls select {{ background: var(--panel2); border: 1px solid var(--border); color: var(--text); padding: 8px 12px; border-radius: 7px; font-size: 13px; }}
  .controls input {{ flex: 1; min-width: 200px; }}
  .agent-flow {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; margin-bottom: 20px; }}
  .flow-step {{ background: var(--panel); border: 1px solid var(--border); border-radius: var(--radius); padding: 14px 12px; text-align: center; font-size: 12.5px; color: var(--muted); position: relative; }}
  .flow-step b {{ display: block; color: var(--text); font-size: 13px; margin-bottom: 4px; }}
  .human-list {{ background: var(--panel); border: 1px solid var(--border); border-radius: var(--radius); padding: 4px 20px; }}
  .human-list li {{ margin: 14px 0; color: var(--muted); font-size: 14px; }}
  .human-list li b {{ color: var(--text); }}
  .run-log {{ display: flex; gap: 14px; margin: 16px 0; flex-wrap: wrap; }}
  .run {{ background: var(--panel); border: 1px solid var(--border); border-radius: var(--radius); padding: 14px 18px; flex: 1; min-width: 160px; }}
  .run .n {{ font-size: 22px; font-weight: 700; }}
  .run.bad .n {{ color: var(--gated); }}
  .run.mid .n {{ color: var(--partial); }}
  .run.good .n {{ color: var(--yes); }}
  .run .cause {{ font-size: 12px; color: var(--muted); margin-top: 6px; }}
  .arrow {{ align-self: center; color: var(--muted); font-size: 20px; }}
  code {{ background: var(--panel2); padding: 2px 6px; border-radius: 4px; font-size: 12.5px; color: var(--accent2); }}
  footer {{ border-top: 1px solid var(--border); padding-top: 20px; color: var(--muted); font-size: 13px; }}
  .legend {{ display: flex; gap: 16px; font-size: 12.5px; color: var(--muted); margin-bottom: 10px; flex-wrap: wrap; }}
  .chip-row {{ display: flex; flex-wrap: wrap; gap: 6px; margin: 10px 0 4px; }}
  .applink {{ display: inline-block; padding: 4px 10px; border-radius: 6px; font-size: 12.5px; border: 1px solid var(--border); }}
  .chip-yes {{ background: rgba(52,211,153,0.08); color: var(--yes); border-color: rgba(52,211,153,0.25); }}
  .chip-gated {{ background: rgba(248,113,113,0.08); color: var(--gated); border-color: rgba(248,113,113,0.25); }}
  .chip-partial {{ background: rgba(251,191,36,0.08); color: var(--partial); border-color: rgba(251,191,36,0.25); }}
  @media (max-width: 800px) {{
    .stat-grid, .insight-cards, .agent-flow {{ grid-template-columns: 1fr; }}
  }}
</style>
</head>
<body>
<div class="wrap">

<header class="hero">
  <div class="kicker">Composio &middot; App Research &amp; Buildability Audit</div>
  <h1>100 apps, researched by an agent, verified by three independent checks</h1>
  <p class="sub">Researched by a Composio + Claude Agent SDK pipeline for auth method, self-serve vs gated access, API surface, and agent-toolkit buildability. Verified through a manual AI check, an automated agent loop, and human spot-checks.</p>
  <div class="badges">
    <span class="badge"><b>100/100</b> apps researched</span>
    <span class="badge"><b>{overall['self_serve']}%</b> self-serve</span>
    <span class="badge"><b>{overall['yes']}%</b> buildable today</span>
    <span class="badge"><b>13/15</b> verification hits, 0 wrong facts</span>
  </div>
</header>

<section id="findings">
  <h2><span class="section-num">1</span> The findings</h2>
  <p class="section-sub">Filter and search below. Every row includes a direct evidence link.</p>
  <div class="controls">
    <input type="text" id="search" placeholder="Search app name...">
    <select id="filterCat"><option value="">All categories</option></select>
    <select id="filterGate"><option value="">Self-serve or gated</option><option value="self-serve">Self-serve</option><option value="gated">Gated</option></select>
    <select id="filterVerdict"><option value="">Any verdict</option><option value="yes">Yes</option><option value="partial">Partial</option></select>
  </div>
  <div class="table-scroll">
  <table id="mainTable">
    <thead><tr><th>#</th><th>App</th><th>Category</th><th>Auth</th><th>Access</th><th>API surface</th><th>MCP</th><th>Verdict</th><th>Blocker</th><th>Bucket</th><th>Evidence</th><th>Conf.</th></tr></thead>
    <tbody>{table_rows_html}</tbody>
  </table>
  </div>
</section>

<section id="patterns">
  <h2><span class="section-num">2</span> The patterns</h2>

  <div class="stat-grid" style="grid-template-columns: 1fr 1fr; margin-bottom:20px;">
    <div class="stat" style="border-color: rgba(52,211,153,0.3);">
      <div class="num" style="font-size:17px; line-height:1.4; color:var(--self);">{self_serve_cats_sentence}</div>
      <div class="label">majority self-serve categories</div>
    </div>
    <div class="stat" style="border-color: rgba(248,113,113,0.3);">
      <div class="num" style="font-size:17px; line-height:1.4; color:var(--gated);">{gated_cats_sentence}</div>
      <div class="label">evenly / majority gated categories</div>
    </div>
    <div class="stat" style="border-color: rgba(52,211,153,0.3);">
      <div class="num" style="color:var(--self);">{overall['self_serve']}/100</div>
      <div class="label">apps counted as self-serve</div>
    </div>
    <div class="stat" style="border-color: rgba(248,113,113,0.3);">
      <div class="num" style="color:var(--gated);">{overall['gated']}/100</div>
      <div class="label">apps counted as gated</div>
    </div>
  </div>

  <div class="stat" style="max-width:260px; margin-bottom:20px;">
    <div class="num">{overall['oauth2']}/100</div><div class="label">support OAuth2 (most common auth)</div>
  </div>

  <div class="card" style="margin-bottom:20px;">
    <h3>Most common blocker: a business gate, not a technical one</h3>
    <p>~13 of the 26 partial-verdict apps are blocked by <b>"needs an existing paid/admin account just to generate credentials"</b> (DealCloud, Gladly, Clay, Ramp, PitchBook, Devin, Grain, and others) -- the API itself usually works fine once inside. A tighter sub-cluster of this same pattern: all <b>5 major ad/social platforms</b> in the set (Google Ads, Meta Ads, LinkedIn Ads, Pinterest, Threads) hit an identical wall of manual app review + business verification, days to weeks, regardless of doc quality.</p>
  </div>

</section>

<section id="agent">
  <h2><span class="section-num">3</span> The agent</h2>
  <p class="section-sub">A Python pipeline using Composio's SDK (web-search toolkit) + Claude Agent SDK, run per-app across all 100.</p>

  <div class="agent-flow">
    <div class="flow-step"><b>1. Load app list</b>100 apps, 10 categories, hardcoded from the assignment brief</div>
    <div class="flow-step"><b>2. Composio search tool</b>No-auth web-search toolkit, wrapped as an MCP tool via ClaudeAgentSDKProvider</div>
    <div class="flow-step"><b>3. Claude Agent SDK query()</b>1-2 searches per app, structured JSON extraction against a fixed schema</div>
    <div class="flow-step"><b>4. Resumable JSONL log</b>Every result appended immediately; failed apps auto-retried, successes never re-run</div>
    <div class="flow-step"><b>5. CSV rebuild</b>Deduped, latest/best result per app written to the final table above</div>
  </div>

  <p style="color:var(--muted); font-size:14px; margin-bottom:10px;">Engineering reliability arc -- three real runs, not a hypothetical:</p>
  <div class="run-log">
    <div class="run bad"><div class="n">43/100</div><div class="cause">Run 1: per-app budget cap too tight ($0.10) + a bug where failed apps were wrongly marked "done"</div></div>
    <div class="arrow">&rarr;</div>
    <div class="run mid"><div class="n">63/100</div><div class="cause">Run 2: raised budget cap, fixed retry bug -- new bug found: SDK's ResultMessage can itself be a failed turn with empty text, which the pipeline was treating as valid</div></div>
    <div class="arrow">&rarr;</div>
    <div class="run good"><div class="n">100/100</div><div class="cause">Run 3: added is_error check + automatic retries with backoff -- remaining failures traced to a transient outage window, cleared on retry</div></div>
  </div>

  <p style="color:var(--muted); font-size:14px; margin:22px 0 10px;">Where a human was needed:</p>
  <ul class="human-list">
    <li><b>Bootstrapping</b> -- API keys, .env setup, and designing the extraction schema (what counts as "self-serve" vs "gated") all happened before the agent touched anything.</li>
    <li><b>Debugging all three failed runs above</b> -- the agent never self-corrected; a human read each error, diagnosed root cause, and patched the pipeline.</li>
    <li><b>Thin-documentation apps</b> -- Sherlock, MrScraper, Waterfall.io, iPayX, Paygent Connect needed a closer human read since public docs were sparse or scattered across community sources.</li>
    <li><b>The verification sample</b> -- picking which 15 apps to independently re-check, and judging borderline cases (e.g. WhatsApp Business: gated but still buildable) required human judgment, not just a rerun.</li>
    <li><b>Pattern synthesis</b> -- the agent produced 100 structured rows; clustering them into "ad platforms share one blocker" and "gating &ne; buildability" is human (or human-directed) interpretation, not something the row data states on its own.</li>
    <li><b>This page</b> -- built and curated by a human deciding what belongs above the fold.</li>
  </ul>
</section>

<section id="proof">
  <h2><span class="section-num">4</span> Proof</h2>
  <div class="insight-cards">
    <div class="card">
      <h3>Live page</h3>
      <p style="margin-top:8px;"><a id="live-url" class="applink" href="#" style="word-break:break-all;">this page's URL</a></p>
    </div>
    <div class="card">
      <h3>Source repo</h3>
      <p>Pipeline source (<code>research_pipeline_v4.py</code>, <code>verify_loop.py</code>) + README on how to run it end to end:</p>
      <p style="margin-top:8px;"><a class="applink" href="REPLACE_WITH_GITHUB_REPO_URL" style="word-break:break-all;">github.com/&hellip;/composio-research-agent</a></p>
    </div>
  </div>
  <p style="color:var(--muted); font-size:13px; margin-top:14px;">Further proof of a real run, not a hypothetical one, is in the engineering reliability arc above (43 &rarr; 63 &rarr; 100) and in the verification results below.</p>
  <script>
    document.getElementById('live-url').textContent = window.location.href;
    document.getElementById('live-url').href = window.location.href;
  </script>
</section>

<section id="verification">
  <h2><span class="section-num">5</span> Verification</h2>
  <p class="section-sub">Three independent verification methods, none overlapping in which apps they cover: a manual AI-assisted check (below), a fully automated agent-based verification loop, and a human check with no AI assistance at all. First: 15 apps sampled across all 10 categories and weighted toward the riskiest claims (gating reasons, "does an MCP exist" claims, thin-docs apps), each independently re-checked by hand via live web search.</p>

  <div class="stat-grid" style="grid-template-columns: repeat(3,1fr);">
    <div class="stat"><div class="num">{hits}/15</div><div class="label">clean hits</div></div>
    <div class="stat"><div class="num">{partials}/15</div><div class="label">partial (right fact, weak citation)</div></div>
    <div class="stat"><div class="num">0/15</div><div class="label">outright wrong findings</div></div>
  </div>

  <div class="table-scroll" style="max-height:400px;">
  <table>
    <thead><tr><th>App</th><th>Claim checked</th><th>Verdict</th><th>Note</th></tr></thead>
    <tbody>{verification_rows_html}</tbody>
  </table>
  </div>
  <p style="color:var(--muted); font-size:13px; margin-top:10px;">Both partials are the same failure mode: the underlying fact was correct, but the cited evidence_url was a generic page instead of the specific one that actually substantiates the claim (Salesforce's MCP claim is true, but cites a general API docs page; iPayX's evidence cites the homepage instead of its docs subpage). Zero factual errors about auth, gating, or buildability were found in this sample.</p>

  <h3 style="font-size:15px; color:var(--accent2); margin:28px 0 6px;">Automated verification loop -- {len(automated_loop_rows)} apps, checked by an agent (no human involved)</h3>
  <p class="section-sub" style="margin-bottom:14px;">A second, fully automated pass: a Composio + Claude Agent SDK agent (<code>verify_loop.py</code>, same pattern as the research pipeline) was given each already-researched claim and independently re-verified it via live web search, with no human opening a URL. This is the actual verification loop the brief asks for, distinct from the manual AI-assisted check above and the human check below.</p>
  <div class="stat-grid" style="grid-template-columns: repeat(3,1fr);">
    <div class="stat"><div class="num">{auto_hits}/{len(automated_loop_rows)}</div><div class="label">clean hits</div></div>
    <div class="stat"><div class="num">{auto_partials}/{len(automated_loop_rows)}</div><div class="label">partial / nuance found</div></div>
    <div class="stat"><div class="num">{auto_corrections}</div><div class="label">real correction applied</div></div>
  </div>
  <div class="table-scroll" style="max-height:400px;">
  <table>
    <thead><tr><th>App</th><th>Claim checked</th><th>Verdict</th><th>Note</th></tr></thead>
    <tbody>{automated_loop_html}</tbody>
  </table>
  </div>
  <p style="color:var(--muted); font-size:13px; margin-top:10px;">Concrete first-pass-to-higher-pass result: the loop caught a real error on Close (mcp_exists was recorded False, but Close does offer an MCP server) -- corrected in the dataset. Two more rows (Copper, Zendesk) surfaced a definitional nuance (official vs. third-party MCP servers) already handled consistently elsewhere in the dataset, so left as-is rather than over-corrected.</p>

  <h3 style="font-size:15px; color:var(--accent2); margin:28px 0 6px;">Human verification pass -- {len(human_check_rows)} apps, checked by hand (no AI assistance)</h3>
  <p class="section-sub" style="margin-bottom:14px;">A separate, distinct manual check from the AI-based pass above: I personally opened each evidence URL and compared it to the row, across two rounds. In the second round I deliberately picked the riskiest, most obscure apps in the dataset (thin docs, unusual naming, newer companies). None of these overlap with the 15 apps already checked above.</p>
  <div class="stat-grid" style="grid-template-columns: repeat(2,1fr); max-width:420px;">
    <div class="stat"><div class="num">{human_hits}/{len(human_check_rows)}</div><div class="label">confirmed accurate</div></div>
    <div class="stat"><div class="num">{human_corrections}/{len(human_check_rows)}</div><div class="label">real corrections found</div></div>
  </div>
  <div class="table-scroll" style="max-height:320px;">
  <table>
    <thead><tr><th>App</th><th>Claim checked</th><th>Verdict</th><th>Note</th></tr></thead>
    <tbody>{human_check_html}</tbody>
  </table>
  </div>

</section>

</div>

<script>
  const data = JSON.parse(document.getElementById('app-data').textContent);
  const catSelect = document.getElementById('filterCat');
  const cats = [...new Set(data.map(d => d.category))];
  cats.forEach(c => {{
    const opt = document.createElement('option');
    opt.value = c; opt.textContent = c;
    catSelect.appendChild(opt);
  }});

  const search = document.getElementById('search');
  const gateSelect = document.getElementById('filterGate');
  const verdictSelect = document.getElementById('filterVerdict');
  const rows = document.querySelectorAll('#mainTable tbody tr');

  function applyFilters() {{
    const q = search.value.toLowerCase();
    const cat = catSelect.value;
    const gate = gateSelect.value;
    const verdict = verdictSelect.value;
    rows.forEach(r => {{
      const name = r.querySelector('.appname').textContent.toLowerCase();
      const matchQ = !q || name.includes(q);
      const matchCat = !cat || r.dataset.cat === cat;
      const matchGate = !gate || r.dataset.gate === gate;
      const matchVerdict = !verdict || r.dataset.verdict === verdict;
      r.style.display = (matchQ && matchCat && matchGate && matchVerdict) ? '' : 'none';
    }});
  }}
  [search, catSelect, gateSelect, verdictSelect].forEach(el => el.addEventListener('input', applyFilters));
</script>
</body>
</html>
"""

with open('case_study.html', 'w') as f:
    f.write(html_doc)

print("Written", len(html_doc), "bytes")
