import asyncio
import aiohttp
from bs4 import BeautifulSoup


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

    async with aiohttp.ClientSession(
        headers=headers
    ) as session:

        async with session.get(
            api_url,
            params=params
        ) as response:

            print("Status:", response.status)

            if response.status != 200:
                print(await response.text())
                return

            data = await response.json()

    if "parse" not in data:
        print("No parse data")
        return

    html = data["parse"]["text"]["*"]

    print("HTML length:", len(html))

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    print("\n==============================")
    print("HEADINGS")
    print("==============================")

    for heading in soup.find_all(["h2", "h3"]):

        title = heading.get_text(
            " ",
            strip=True
        )

        print(repr(title))


asyncio.run(main())
