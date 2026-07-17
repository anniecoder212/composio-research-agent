"""
Automated verification loop.

Takes rows already in research_results_clean.csv and re-checks each claim
independently -- same Composio + Claude Agent SDK pattern as the research
pipeline, but the prompt asks the agent to VERIFY, not discover.

Run: python3 verify_loop.py
Output: verification_results.csv (resumable, same pattern as the research pipeline)
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

INPUT_CSV = "research_results_clean.csv"
OUTPUT_CSV = "verification_results.csv"
SAMPLE_SIZE = 15          # how many rows to re-check -- raise to len(rows) to check all 100
CONCURRENCY = 2
MAX_RETRIES = 2

FIELDNAMES = ["num", "app", "claim_checked", "verdict", "note"]

SYSTEM_PROMPT = """You are a fact-checker. You are given a claim someone already
made about a company's API/developer platform, plus the evidence URL they cited.
Use web search to independently verify the claim. Do not trust the original
claim -- check it yourself. Reply with ONLY a JSON object:
{"verdict": "HIT" | "PARTIAL" | "WRONG", "note": "one sentence, what you found"}
HIT = claim is accurate. PARTIAL = core fact right but a detail/citation is off.
WRONG = claim is factually incorrect."""

PROMPT_TEMPLATE = """App: {app}
Claim: auth={auth}, self_serve={self_serve}, mcp_exists={mcp_exists}, gated_reason={gated_reason}
Evidence URL originally cited: {evidence_url}

Verify this claim independently using web search. Reply with the JSON object only."""


def load_done_nums():
    done = set()
    if os.path.exists(OUTPUT_CSV):
        with open(OUTPUT_CSV) as f:
            for row in csv.DictReader(f):
                if row.get("verdict"):
                    done.add(row["num"])
    return done


def extract_json(text):
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("no JSON object found in response")
    return json.loads(match.group(0))


async def verify_one(composio, mcp_server, row, sem, writer, f):
    async with sem:
        prompt = PROMPT_TEMPLATE.format(**row)
        last_error = None
        for attempt in range(MAX_RETRIES + 1):
            try:
                final_text = None
                turn_errored = False
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
                        if message.is_error:
                            turn_errored = True
                        else:
                            final_text = message.result
                        break
                if turn_errored or not final_text:
                    raise RuntimeError("agent turn errored or returned nothing")
                parsed = extract_json(final_text)
                out = {
                    "num": row["num"],
                    "app": row["app"],
                    "claim_checked": f"auth={row['auth']}, self_serve={row['self_serve']}",
                    "verdict": parsed["verdict"],
                    "note": parsed["note"],
                }
                writer.writerow(out)
                f.flush()
                print(f"[ok] {row['app']}: {parsed['verdict']}")
                return
            except Exception as e:
                last_error = str(e)
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(2 * (attempt + 1))
        print(f"[fail] {row['app']}: {last_error}")


async def main():
    composio = Composio(api_key=os.environ["COMPOSIO_API_KEY"], provider=ClaudeAgentSDKProvider())
    tools = composio.tools.get(user_id="default", toolkits=["composio_search"])
    mcp_server = composio.provider.create_mcp_server(tools)

    with open(INPUT_CSV) as f:
        all_rows = list(csv.DictReader(f))

    sample = all_rows[:SAMPLE_SIZE]
    done = load_done_nums()
    todo = [r for r in sample if r["num"] not in done]
    print(f"{len(done)} already verified, {len(todo)} left")

    write_header = not os.path.exists(OUTPUT_CSV)
    with open(OUTPUT_CSV, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if write_header:
            writer.writeheader()
        sem = asyncio.Semaphore(CONCURRENCY)
        await asyncio.gather(*(verify_one(composio, mcp_server, row, sem, writer, f) for row in todo))

    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
