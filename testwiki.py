import asyncio
import aiohttp

async def main():
    url = "https://honor-of-kings.fandom.com/wiki/Lam"

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(url) as response:
            html = await response.text()

            position = html.find("Lam_%28Classic%29")

            print("Status:", response.status)
            print("Position:", position)

            if position != -1:
                print(html[position - 500:position + 1500])

asyncio.run(main())

