import asyncio
import os
from dotenv import load_dotenv
from composio import Composio
from composio_claude_agent_sdk import ClaudeAgentSDKProvider
from claude_agent_sdk import query, ClaudeAgentOptions

load_dotenv()

async def main():
    composio = Composio(
        api_key=os.getenv("COMPOSIO_API_KEY"),
        provider=ClaudeAgentSDKProvider(),
    )

    # composio_search is a no-auth toolkit -- no OAuth setup needed to test with
    tools = composio.tools.get(
        user_id=os.getenv("USER_ID", "default"),
        toolkits=["composio_search"],
    )

    mcp_server = composio.provider.create_mcp_server(tools)

    print("Testing setup -- asking the agent to search the web...\n")

    async for message in query(
        prompt="Search the web for: what authentication method does the Stripe API use? Answer in one sentence and give the source URL.",
        options=ClaudeAgentOptions(
            mcp_servers={"composio": mcp_server},
            permission_mode="bypassPermissions",
        ),
    ):
        print(message)

if __name__ == "__main__":
    asyncio.run(main())
