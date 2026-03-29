import asyncio
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def run_automation():
    server_params = StdioServerParameters(
        command="wechat-mcp",
        args=["--transport", "stdio"]
    )

    chat_name = "Yu Song"
    polling_interval = 10  # seconds

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Establish baseline
            print(f"Fetching initial history for: {chat_name}")
            initial = await session.call_tool("fetch_messages_by_chat", {
                "chat_name": chat_name,
                "last_n": 50
            })

            def parse_messages(result):
                items = result.content if hasattr(result, "content") else []
                messages = []
                for item in items:
                    raw = item.text if hasattr(item, "text") else str(item)
                    try:
                        parsed = json.loads(raw)
                        if isinstance(parsed, list):
                            messages.extend(parsed)
                        elif isinstance(parsed, dict):
                            messages.append(parsed)
                    except (json.JSONDecodeError, TypeError):
                        pass
                return messages

            messages = parse_messages(initial)
            last_msg = messages[-1] if messages else None
            print(f"Baseline: {last_msg}")

            # Polling loop
            print(f"Polling every {polling_interval}s...")
            while True:
                try:
                    await asyncio.sleep(polling_interval)

                    update = await session.call_tool("fetch_messages_by_chat", {
                        "chat_name": chat_name,
                        "last_n": 1
                    })

                    current = parse_messages(update)
                    if not current:
                        continue

                    latest = current[-1]
                    #print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@", latest, last_msg)

                    if latest != last_msg and latest.get("sender") != "ME" and latest['text'] != last_msg['text']:
                        print(f"New message: {latest.get('text')}")

                        reply_text = "Received! Thanks for letting me know."
                        await session.call_tool("reply_to_messages_by_chat", {
                            "chat_name": chat_name,
                            "reply_message": reply_text
                        })
                        print(f"Replied: {reply_text}")

                    last_msg = latest

                except Exception as e:
                    print(f"Error during poll: {e}")


if __name__ == "__main__":
    try:
        asyncio.run(run_automation())
    except KeyboardInterrupt:
        print("\nBot stopped.")
