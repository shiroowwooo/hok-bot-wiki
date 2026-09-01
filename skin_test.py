import asyncio
import aiohttp

async def main():

    api_url = "https://honor-of-kings.fandom.com/api.php"

    headers = {
        "User-Agent": "HOK-Wiki-Discord-Bot/1.0"
    }

    params = {
        "action": "parse",
        "page": "Lam",
        "prop": "text",
        "format": "json"
    }

    timeout = aiohttp.ClientTimeout(total=30)

    async with aiohttp.ClientSession(
        timeout=timeout,
        headers=headers
    ) as session:

        async with session.get(
            api_url,
            params=params
        ) as response:

            print("Status:", response.status)

            data = await response.json()

    html = data["parse"]["text"]["*"]

    position = html.find("Lam_%28Classic%29")

    print("Classic position:", position)

    if position != -1:
        print(html[position - 500:position + 1500])

asyncio.run(main())

