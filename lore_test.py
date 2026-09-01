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

            data = await response.json()

    html = data["parse"]["text"]["*"]

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    text = soup.get_text(
        "\n",
        strip=True
    )

    for word in [
        "Species",
        "Height",
        "Region",
        "Location",
        "Faction",
        "Background",
        "Skillset"
    ]:

        position = text.find(word)

        print("\n==========", word, "==========")

        if position != -1:
            print(
                text[position:position + 300]
            )
        else:
            print("NOT FOUND")


asyncio.run(main())
