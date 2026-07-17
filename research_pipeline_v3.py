"""
research_pipeline_v3.py

Researches all 100 apps from the AI Product Ops Intern take-home assignment
using Composio's web-search toolkit + Claude Agent SDK, and writes structured
results to results/raw_results.jsonl (one JSON object per line) and
results/research_results.csv.

Safe to re-run: it skips apps that already SUCCEEDED, so failed apps get
retried automatically and you never lose completed work or pay for it twice.

v3 fix: stop listening to the message stream the instant we get our
ResultMessage, instead of continuing to await further messages. The SDK
sometimes raises a trailing "Claude Code returned an error result: success"
error right after a perfectly good result, as part of its process-cleanup
handling -- continuing to listen was throwing away good answers.
"""

import asyncio
import csv
import json
import os
import re

from dotenv import load_dotenv
from composio import Composio
from composio_claude_agent_sdk import ClaudeAgentSDKProvider
from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage

load_dotenv()

RESULTS_DIR = "results"
JSONL_PATH = os.path.join(RESULTS_DIR, "raw_results.jsonl")
CSV_PATH = os.path.join(RESULTS_DIR, "research_results.csv")

CONCURRENCY = 3

APPS = [
    (1, "Salesforce", "CRM and Sales", "salesforce.com"),
    (2, "HubSpot", "CRM and Sales", "hubspot.com"),
    (3, "Pipedrive", "CRM and Sales", "pipedrive.com"),
    (4, "Attio", "CRM and Sales", "attio.com"),
    (5, "Twenty", "CRM and Sales", "twenty.com (open-source CRM)"),
    (6, "Podio", "CRM and Sales", "podio.com"),
    (7, "Zoho CRM", "CRM and Sales", "zoho.com/crm"),
    (8, "Close", "CRM and Sales", "close.com"),
    (9, "Copper", "CRM and Sales", "copper.com"),
    (10, "DealCloud", "CRM and Sales", "api.docs.dealcloud.com"),
    (11, "Zendesk", "Support and Helpdesk", "zendesk.com"),
    (12, "Intercom", "Support and Helpdesk", "intercom.com"),
    (13, "Freshdesk", "Support and Helpdesk", "freshdesk.com"),
    (14, "Front", "Support and Helpdesk", "front.com"),
    (15, "Pylon", "Support and Helpdesk", "usepylon.com"),
    (16, "LiveAgent", "Support and Helpdesk", "liveagent.com"),
    (17, "Plain", "Support and Helpdesk", "plain.com"),
    (18, "Help Scout", "Support and Helpdesk", "helpscout.com"),
    (19, "Gorgias", "Support and Helpdesk", "gorgias.com"),
    (20, "Gladly", "Support and Helpdesk", "gladly.com"),
    (21, "Slack", "Communications and Messaging", "slack.com"),
    (22, "Twilio", "Communications and Messaging", "twilio.com"),
    (23, "Zoho Cliq", "Communications and Messaging", "zoho.com/cliq"),
    (24, "Lark (Larksuite)", "Communications and Messaging", "open.larksuite.com"),
    (25, "Pumble", "Communications and Messaging", "pumble.com"),
    (26, "Discord", "Communications and Messaging", "discord.com"),
    (27, "Telegram", "Communications and Messaging", "core.telegram.org"),
    (28, "WhatsApp Business", "Communications and Messaging", "developers.facebook.com/docs/whatsapp"),
    (29, "Aircall", "Communications and Messaging", "aircall.io"),
    (30, "Vonage", "Communications and Messaging", "developer.vonage.com"),
    (31, "Google Ads", "Marketing, Ads, Email and Social", "developers.google.com/google-ads"),
    (32, "Meta Ads", "Marketing, Ads, Email and Social", "developers.facebook.com/docs/marketing-apis"),
    (33, "LinkedIn Ads", "Marketing, Ads, Email and Social", "learn.microsoft.com/linkedin/marketing"),
    (34, "GoHighLevel", "Marketing, Ads, Email and Social", "highlevel.stoplight.io"),
    (35, "Mailchimp", "Marketing, Ads, Email and Social", "mailchimp.com/developer"),
    (36, "Klaviyo", "Marketing, Ads, Email and Social", "developers.klaviyo.com"),
    (37, "systeme.io", "Marketing, Ads, Email and Social", "systeme.io (funnel builder)"),
    (38, "Pinterest", "Marketing, Ads, Email and Social", "developers.pinterest.com"),
    (39, "Threads (Meta)", "Marketing, Ads, Email and Social", "developers.facebook.com/docs/threads"),
    (40, "SendGrid", "Marketing, Ads, Email and Social", "sendgrid.com"),
    (41, "Shopify", "Ecommerce", "shopify.dev"),
    (42, "WooCommerce", "Ecommerce", "woocommerce.com/document/woocommerce-rest-api"),
    (43, "BigCommerce", "Ecommerce", "developer.bigcommerce.com"),
    (44, "Salesforce Commerce Cloud", "Ecommerce", "developer.salesforce.com/docs/commerce"),
    (45, "Magento (Adobe Commerce)", "Ecommerce", "developer.adobe.com/commerce"),
    (46, "Squarespace", "Ecommerce", "developers.squarespace.com"),
    (47, "Ecwid", "Ecommerce", "api-docs.ecwid.com"),
    (48, "Gumroad", "Ecommerce", "gumroad.com/api"),
    (49, "Amazon Selling Partner", "Ecommerce", "developer-docs.amazon.com/sp-api"),
    (50, "fanbasis", "Ecommerce", "fanbasis.com"),
    (51, "DataForSEO", "Data, SEO and Scraping", "docs.dataforseo.com"),
    (52, "SE Ranking", "Data, SEO and Scraping", "seranking.com/api"),
    (53, "Ahrefs", "Data, SEO and Scraping", "ahrefs.com/api"),
    (54, "MrScraper", "Data, SEO and Scraping", "docs.mrscraper.com"),
    (55, "Apify", "Data, SEO and Scraping", "docs.apify.com"),
    (56, "Firecrawl", "Data, SEO and Scraping", "firecrawl.dev"),
    (57, "Bright Data", "Data, SEO and Scraping", "brightdata.com"),
    (58, "Sherlock", "Data, SEO and Scraping", "github.com/sherlock-project/sherlock"),
    (59, "Waterfall.io", "Data, SEO and Scraping", "waterfall.io (contact/company intel)"),
    (60, "Clay", "Data, SEO and Scraping", "clay.com"),
    (61, "GitHub", "Developer, Infra and Data platforms", "docs.github.com/rest"),
    (62, "Vercel", "Developer, Infra and Data platforms", "vercel.com/docs/rest-api"),
    (63, "Netlify", "Developer, Infra and Data platforms", "docs.netlify.com/api"),
    (64, "Cloudflare", "Developer, Infra and Data platforms", "developers.cloudflare.com/api"),
    (65, "Supabase", "Developer, Infra and Data platforms", "supabase.com/docs"),
    (66, "Neo4j", "Developer, Infra and Data platforms", "neo4j.com/docs/api"),
    (67, "Snowflake", "Developer, Infra and Data platforms", "docs.snowflake.com"),
    (68, "MongoDB Atlas", "Developer, Infra and Data platforms", "mongodb.com/docs/atlas/api"),
    (69, "Datadog", "Developer, Infra and Data platforms", "docs.datadoghq.com/api"),
    (70, "Sentry", "Developer, Infra and Data platforms", "docs.sentry.io/api"),
    (71, "Notion", "Productivity and Project Management", "developers.notion.com"),
    (72, "Airtable", "Productivity and Project Management", "airtable.com/developers"),
    (73, "Linear", "Productivity and Project Management", "developers.linear.app"),
    (74, "Jira", "Productivity and Project Management", "developer.atlassian.com"),
    (75, "Asana", "Productivity and Project Management", "developers.asana.com"),
    (76, "Monday.com", "Productivity and Project Management", "developer.monday.com"),
    (77, "ClickUp", "Productivity and Project Management", "clickup.com/api"),
    (78, "Coda", "Productivity and Project Management", "coda.io/developers"),
    (79, "Smartsheet", "Productivity and Project Management", "smartsheet.com/developers"),
    (80, "Harvest", "Productivity and Project Management", "help.getharvest.com/api-v2"),
    (81, "Stripe", "Finance and Fintech", "stripe.com/docs/api"),
    (82, "Plaid", "Finance and Fintech", "plaid.com/docs"),
    (83, "Binance", "Finance and Fintech", "binance-docs.github.io"),
    (84, "Paygent Connect", "Finance and Fintech", "paygent (NMI-powered)"),
    (85, "iPayX", "Finance and Fintech", "ipayx.ai/docs"),
    (86, "QuickBooks", "Finance and Fintech", "developer.intuit.com"),
    (87, "Xero", "Finance and Fintech", "developer.xero.com"),
    (88, "Brex", "Finance and Fintech", "developer.brex.com"),
    (89, "Ramp", "Finance and Fintech", "docs.ramp.com"),
    (90, "PitchBook", "Finance and Fintech", "pitchbook.com (research API)"),
    (91, "NotebookLM", "AI, Research and Media-native", "cloud.google.com/gemini (Enterprise API)"),
    (92, "Otter AI", "AI, Research and Media-native", "help.otter.ai (MCP server)"),
    (93, "Fathom", "AI, Research and Media-native", "fathom.video"),
    (94, "Consensus", "AI, Research and Media-native", "consensus.app (OAuth requested)"),
    (95, "Reducto", "AI, Research and Media-native", "reducto.ai (document parsing)"),
    (96, "Devin", "AI, Research and Media-native", "docs.devin.ai (MCP)"),
    (97, "higgsfield", "AI, Research and Media-native", "higgsfield.ai/cli (content suite)"),
    (98, "Mermaid CLI", "AI, Research and Media-native", "github.com/mermaid-js/mermaid-cli"),
    (99, "YouTube Transcript", "AI, Research and Media-native", "transcriptapi.com"),
    (100, "Grain", "AI, Research and Media-native", "grain.com (meeting notes)"),
]

SYSTEM_PROMPT = """You are a research analyst investigating third-party software APIs and
developer platforms for an AI agent-tooling company. For each app you are given, use the
search tool (1-2 searches, prioritize official docs / developer portals, be efficient) to
answer the research questions. Always respond with ONLY a single valid JSON object matching
the exact schema given in the user prompt -- no markdown formatting, no code fences, no
extra prose before or after the JSON."""

PROMPT_TEMPLATE = """Research the app "{name}" ({hint}), category: "{category}".

Answer these questions:
1. description - one line: what the app does
2. auth - primary auth method(s) it uses for its API: OAuth2, API key, Basic, token, or other
3. self_serve - "self-serve" if a developer can get API credentials themselves for free or
   on a trial, or "gated" if it needs a paid plan, admin approval, or a partnership /
   contact-sales gate
4. gated_reason - one line explaining why it's gated, or "" if self-serve
5. api_surface - is there a documented public REST/GraphQL API? Roughly how broad is it
   (e.g. "narrow, ~10 endpoints" vs "extensive, full platform")? Does an MCP server already
   exist for it?
6. mcp_exists - true or false
7. buildability_verdict - "yes", "no", or "partial" -- could this be an agent toolkit today?
8. blocker - the main blocker if verdict is not "yes", or "" if none
9. evidence_url - the single best docs URL / article backing your answers
10. confidence - "high", "medium", or "low", based on how clear/complete the docs were

Respond with ONLY this JSON object (fill in every field, no placeholders):
{{"num": {num}, "app": "{name}", "category": "{category}", "description": "", "auth": "", "self_serve": "", "gated_reason": "", "api_surface": "", "mcp_exists": false, "buildability_verdict": "", "blocker": "", "evidence_url": "", "confidence": ""}}
"""

FIELDNAMES = [
    "num", "app", "category", "description", "auth", "self_serve",
    "gated_reason", "api_surface", "mcp_exists", "buildability_verdict",
    "blocker", "evidence_url", "confidence",
]


def load_done_nums():
    """Only apps that SUCCEEDED count as done -- failed apps get retried."""
    done = set()
    if os.path.exists(JSONL_PATH):
        with open(JSONL_PATH, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                    if row.get("_status") == "ok":
                        done.add(row["num"])
                except (json.JSONDecodeError, KeyError):
                    pass
    return done


def extract_json(text):
    text = text.strip()
    fence_match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1)
    else:
        brace_match = re.search(r"\{.*\}", text, re.DOTALL)
        if brace_match:
            text = brace_match.group(0)
    return json.loads(text)


async def research_one(mcp_server, app, lock):
    num, name, category, hint = app
    prompt = PROMPT_TEMPLATE.format(num=num, name=name, category=category, hint=hint)

    row = {f: "" for f in FIELDNAMES}
    row.update({"num": num, "app": name, "category": category})

    final_text = None
    try:
        async for message in query(
            prompt=prompt,
            options=ClaudeAgentOptions(
                system_prompt=SYSTEM_PROMPT,
                mcp_servers={"composio": mcp_server},
                permission_mode="bypassPermissions",
                model="claude-sonnet-5",
                max_turns=6,
                max_budget_usd=0.35,
            ),
        ):
            if isinstance(message, ResultMessage):
                final_text = message.result
                # Stop listening the moment we have our answer -- continuing
                # to await further messages is what triggered the spurious
                # trailing "error result: success" from the SDK's process
                # cleanup on some turns.
                break

        if final_text is None:
            raise RuntimeError("no ResultMessage received")

        parsed = extract_json(final_text)
        row.update(parsed)
        row["_status"] = "ok"

    except Exception as e:
        if final_text is not None:
            # We actually got a good answer before something (e.g. a trailing
            # SDK cleanup error) went wrong -- try to salvage it instead of
            # discarding a valid result.
            try:
                parsed = extract_json(final_text)
                row.update(parsed)
                row["_status"] = "ok"
            except Exception as parse_err:
                row["_status"] = "error"
                row["_error"] = f"had result but failed to parse: {parse_err}"
        else:
            row["_status"] = "error"
            row["_error"] = str(e)
            print(f"  [!] #{num} {name} FAILED: {e}")

    async with lock:
        with open(JSONL_PATH, "a") as f:
            f.write(json.dumps(row) + "\n")
        print(f"  [{'ok' if row.get('_status') == 'ok' else 'ERR'}] #{num} {name}")

    return row


async def main():
    os.makedirs(RESULTS_DIR, exist_ok=True)

    composio = Composio(
        api_key=os.getenv("COMPOSIO_API_KEY"),
        provider=ClaudeAgentSDKProvider(),
    )
    tools = composio.tools.get(
        user_id=os.getenv("USER_ID", "default"),
        toolkits=["composio_search"],
    )
    mcp_server = composio.provider.create_mcp_server(tools)

    done_nums = load_done_nums()
    todo = [a for a in APPS if a[0] not in done_nums]

    print(f"{len(done_nums)} apps already done, {len(todo)} left to research.\n")

    semaphore = asyncio.Semaphore(CONCURRENCY)
    lock = asyncio.Lock()

    async def bound_research(app):
        async with semaphore:
            return await research_one(mcp_server, app, lock)

    await asyncio.gather(*(bound_research(app) for app in todo))

    all_rows = {}
    with open(JSONL_PATH, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            existing = all_rows.get(r["num"])
            if existing is None or r.get("_status") == "ok":
                all_rows[r["num"]] = r

    with open(CSV_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES + ["_status", "_error"])
        writer.writeheader()
        for num in sorted(all_rows):
            row = all_rows[num]
            writer.writerow({k: row.get(k, "") for k in FIELDNAMES + ["_status", "_error"]})

    ok_count = sum(1 for r in all_rows.values() if r.get("_status") == "ok")
    print(f"\nDone. {ok_count}/{len(all_rows)} apps researched successfully.")
    print(f"Raw results: {JSONL_PATH}")
    print(f"CSV: {CSV_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
