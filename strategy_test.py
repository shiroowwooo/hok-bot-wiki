import asyncio
import aiohttp
from bs4 import BeautifulSoup


async def main():

    api_url = "https://honor-of-kings.fandom.com/api.php"

    params = {
        "action": "parse",
        "page": "Lam",
        "prop": "text",
        "format": "json"
    }

    headers = {
        "User-Agent": "HOK-Wiki-Discord-Bot/1.0"
    }

    async with aiohttp.ClientSession(
        headers=headers
    ) as session:

        async with session.get(
            api_url,
            params=params
        ) as response:

            print("Status:", response.status)

            data = await response.json()

    html = data["parse"]["text"]["*"]

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    print("\n==============================")
    print("ALL STRATEGY HEADINGS")
    print("==============================")

    for h in soup.find_all(["h2", "h3"]):

        title = h.get_text(
            " ",
            strip=True
        )

        if "strateg" in title.lower():

            print(
                "TAG:",
                h.name,
                "|",
                repr(title)
            )

            print(
                "HTML:",
                str(h)[:1000]
            )


asyncio.run(main())
