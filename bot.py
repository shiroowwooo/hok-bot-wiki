import os
import discord
from discord.ext import commands
import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import quote, urlsplit, urlunsplit, unquote
import re

# ============================================================
# TOKEN
# ============================================================

# KEEP YOUR EXISTING TOKEN LINE HERE.
TOKEN = os.getenv("TOKEN")


# ============================================================
# BOT
# ============================================================

intents = discord.Intents.default()

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)


# ============================================================
# WIKI
# ============================================================

WIKI_URL = "https://honor-of-kings.fandom.com/wiki/"


async def get_hero_page(hero_name):

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    timeout = aiohttp.ClientTimeout(total=30)

    async with aiohttp.ClientSession(
        timeout=timeout,
        headers=headers
    ) as session:

        # Search the Fandom wiki
        search_url = (
            "https://honor-of-kings.fandom.com/"
            "api.php"
        )

        params = {
            "action": "query",
            "list": "search",
            "srsearch": hero_name,
            "format": "json",
            "srlimit": 10
        }

        async with session.get(
            search_url,
            params=params
        ) as response:

            if response.status != 200:
                print(
                    f"Search failed: HTTP {response.status}"
                )
                return None

            search_data = await response.json()

        results = search_data.get(
            "query",
            {}
        ).get(
            "search",
            []
        )

        if not results:
            print(
                f"No wiki results for {hero_name}"
            )
            return None

        # Find the closest page
        page_title = results[0]["title"]

        print(
            f"Wiki page found: {page_title}"
        )

        # Get the actual page
        page_url = (
            "https://honor-of-kings.fandom.com/wiki/"
            + quote(
                page_title.replace(" ", "_")
            )
        )

        async with session.get(
            page_url
        ) as response:

            if response.status != 200:
                print(
                    f"Page failed: HTTP {response.status}"
                )
                return None

            return await response.text()
async def get_hero_page(hero_name):

    # your get_hero_page code
    # ...
    return html
async def get_skin_images(hero_name):
    html = await get_hero_page(hero_name)

    if not html:
        return []

    import re
    from urllib.parse import unquote, quote

    images = []

    # Find actual Fandom gallery images
    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    # Only collect images from the Wiki gallery
    for link in soup.select("a.image.lightbox"):

        img = link.find("img")

        if not img:
            continue

        filename = (
            img.get("data-image-key")
            or img.get("data-image-name")
        )

        if not filename:
            continue

        filename = unquote(filename)

        # Ignore numbered skill images
        name_without_ext = filename.rsplit(".", 1)[0]

        if name_without_ext.isdigit():
            continue

        lower_name = filename.lower()

        # Ignore non-skin files
        if any(word in lower_name for word in [
            "skill",
            "ability",
            "spell",
            "talent",
            "starstone",
            "token",
            "icon",
            "portrait",
            "avatar"
        ]):
            continue

        src = (
            img.get("data-src")
            or img.get("data-original")
            or img.get("src")
        )

        if not src:
            continue

        # Ignore lazy-loading placeholder
        if src.startswith("data:image"):
            continue

        if src.startswith("//"):
            src = "https:" + src

        # Remove thumbnail size
        parts = urlsplit(src)
        clean_path = parts.path

        if "/revision/latest/" in clean_path:
            clean_path = clean_path.split(
                "/revision/latest/"
            )[0] + "/revision/latest"

        src = urlunsplit((
            parts.scheme,
            parts.netloc,
            clean_path,
            "",
            ""
        ))

        if src not in images:
            images.append(src)        # Build the Wiki file URL
        wiki_url = (
            "https://honor-of-kings.fandom.com/wiki/"
            + quote(hero_name.replace(" ", "_"))
            + "?file="
            + quote(filename)
        )

        # Find the actual static image URL associated with this filename
        escaped_filename = re.escape(filename)

        pattern = (
            r'https?://static\.wikia\.nocookie\.net/'
            r'honor-of-kings/images/[^"\'<> ]+'
            + escaped_filename
        )

        result = re.search(
            pattern,
            html,
            re.IGNORECASE
        )

        if result:
            src = result.group(0)

            # Remove thumbnail resizing
            if "/revision/latest/" in src:
                src = src.split(
                    "/revision/latest/"
                )[0] + "/revision/latest"

            if src not in images:
                images.append(src)

    print(
        f"Found {len(images)} skin images for {hero_name}"
    )

    return images
def get_lore(soup):

    # Get all text paragraphs from the page
    paragraphs = soup.find_all("p")

    content = []

    started = False

    for p in paragraphs:

        text = p.get_text(
            " ",
            strip=True
        )

        if not text:
            continue

        lower = text.lower()

        # Skip the short hero introduction
        if "hero in honor of kings" in lower:
            continue

        # Skip obvious navigation/description text
        if lower in [
            "contents",
            "background",
            "lore",
            "skills",
            "skins",
            "strategies"
        ]:
            continue

        # Detect the beginning of the actual story.
        #
        # The first real lore paragraph normally contains
        # words describing the hero's background/story.
        #
        # We use several possible indicators so this works
        # across different heroes.
        if not started:

            story_words = [
                "born",
                "grew up",
                "raised",
                "young",
                "childhood",
                "family",
                "clan",
                "village",
                "kingdom",
                "war",
                "life",
                "past",
                "story"
            ]

            if any(
                word in lower
                for word in story_words
            ):
                started = True

        if not started:
            continue

        content.append(text)

    # Remove anything that clearly belongs to Skills
    cleaned = []

    for text in content:

        lower = text.lower()

        if any(
            phrase in lower
            for phrase in [
                "basic attacks and skills deal",
                "cooldown",
                "physical damage",
                "movement speed",
                "magical damage",
                "physical attack",
                "bonus physical attack",
                "skill effect",
                "passive:",
                "active:"
            ]
        ):
            break

        cleaned.append(text)

    print(
        f"Found {len(cleaned)} lore paragraphs"
    )

    return cleaned
def get_strategies(soup):

    strategies_heading = None

    # Find the Strategies heading
    for heading in soup.find_all(["h2", "h3"]):

        headline = heading.find(
            class_="mw-headline"
        )

        if headline:
            title = headline.get_text(
                " ",
                strip=True
            )
        else:
            title = heading.get_text(
                " ",
                strip=True
            )

        if title.lower().strip() == "strategies":
            strategies_heading = heading
            break

    if not strategies_heading:
        print("Strategies heading not found")
        return []

    content = []

    for element in strategies_heading.find_all_next():

        if element.name == "h2":

            headline = element.find(
                class_="mw-headline"
            )

            if headline:

                title = headline.get_text(
                    " ",
                    strip=True
                ).lower()

                if title != "strategies":
                    break

        if element.name in ["p", "li"]:

            text = clean_text(
                element.get_text(
                    " ",
                    strip=True
                )
            )

            if not text:
                continue

            if text.lower() in [
                "strategies",
                "contents",
                "skins",
                "skills",
                "lore"
            ]:
                continue

            content.append(text)

    print(
        f"Found {len(content)} strategy lines"
    )

    return content
async def get_hero_data(hero_name):

    html = await get_hero_page(hero_name)

    if not html:
        return None

    soup = BeautifulSoup(
        html,
        "html.parser"
    )
    data = {

        "background": get_section(
            soup,
            "Background"
        ),

        "lore": get_lore(
            soup
        ),

        "skills": await get_skills(
            hero_name,
            html
        ),

        "skins": get_section(
            soup,
            "Skins"
        ),

        "skin_images": await get_skin_images(
            hero_name
        ),

        "strategies": get_strategies(
            soup
        )
    }

    return data
    data = {
        "background": get_section(
            soup,
            "Background"
        ),

        "lore": get_lore(
            soup
        ),

        "skills": await get_skills(
            hero_name,
            html
        ),
        "skins": get_section(
            soup,
            "Skins"
        ),

        "skin_images": await get_skin_images(
            hero_name
        ),

        "strategies": get_section(
            soup,
            "Strategies"
        )
    }

    return data

# ============================================================
# CLEAN WIKI TEXT
# ============================================================

def clean_text(text):

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    text = text.replace(
        "[edit]",
        ""
    )

    text = text.replace(
        "[]",
        ""
    )

    return text.strip()


# ============================================================
# FIND SECTION
# ============================================================

def get_hero_details(soup):

    details = {}

    # Find the text containing the hero information
    text = soup.get_text(
        "\n",
        strip=True
    )

    fields = [
        "Species",
        "Height",
        "Region",
        "Location",
        "Faction",
        "Background",
        "Skillset"
    ]

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    for i, line in enumerate(lines):

        if line in fields and i + 1 < len(lines):

            value = lines[i + 1]

            # Don't accidentally use another field as the value
            if value not in fields:
                details[line] = value

    return details
def get_section(soup, section_name):

    # Find headings such as:
    # Background
    # Lore
    # Skills
    # Skins
    # Strategies

    headings = soup.find_all(
        ["h2", "h3"]
    )

    start = None

    for heading in headings:

        title = clean_text(
            heading.get_text(" ", strip=True)
        )

        title = title.replace(
            "[edit]",
            ""
        )

        if title.lower() == section_name.lower():

            start = heading
            break

    if not start:
        return None

    content = []

    for element in start.find_all_next():

        if element == start:
            continue

        if element.name in ["h2", "h3"]:

            heading_text = clean_text(
                element.get_text(
                    " ",
                    strip=True
                )
            )

            if heading_text.lower() != section_name.lower():

                # Stop at next major section.
                if element.name == "h2":
                    break

        if element.name in [
            "p",
            "li"
        ]:

            text = clean_text(
                element.get_text(
                    " ",
                    strip=True
                )
            )

            if text:
                content.append(text)

    if not content:
        return None

    return content


# ============================================================
# GET HERO DATA
# ============================================================

async def get_hero_page(hero_name):

    headers = {
        "User-Agent": "HOK-Wiki-Discord-Bot/1.0"
    }

    api_url = (
        "https://honor-of-kings.fandom.com/api.php"
    )

    timeout = aiohttp.ClientTimeout(total=30)

    async with aiohttp.ClientSession(
        timeout=timeout,
        headers=headers
    ) as session:

        # Search for the hero
        search_params = {
            "action": "query",
            "list": "search",
            "srsearch": hero_name,
            "format": "json",
            "srlimit": 5
        }

        async with session.get(
            api_url,
            params=search_params
        ) as response:

            if response.status != 200:
                print(
                    f"Search failed: HTTP {response.status}"
                )
                return None

            search_data = await response.json()

        results = (
            search_data
            .get("query", {})
            .get("search", [])
        )

        if not results:
            print(
                f"No wiki results for {hero_name}"
            )
            return None

        page_title = results[0]["title"]

        print(
            f"Wiki page found: {page_title}"
        )

        # Get the actual wiki HTML through the API
        page_params = {
            "action": "parse",
            "page": page_title,
            "prop": "text",
            "format": "json"
        }

        async with session.get(
            api_url,
            params=page_params
        ) as response:

            if response.status != 200:
                print(
                    f"API page failed: HTTP {response.status}"
                )
                return None

            page_data = await response.json()

        if "parse" not in page_data:
            print(
                "Wiki API did not return page content."
            )
            return None

        html = (
            page_data["parse"]["text"]["*"]
        )

        return html


# ============================================================
# EMBED TEXT HELPER
# ============================================================

def make_pages(
    title,
    lines,
    max_chars=3800
):

    if not lines:
        return [
            "No information was found on the wiki."
        ]

    pages = []
    current = ""

    for line in lines:

        # Remove excessive wiki text
        line = clean_text(line)

        if not line:
            continue

        # Add bullet
        line = "• " + line

        if len(current) + len(line) + 1 > max_chars:

            if current:
                pages.append(
                    current
                )

            current = line

        else:

            if current:
                current += "\n\n"

            current += line

    if current:
        pages.append(
            current
        )

    return pages


# ============================================================
# INFORMATION VIEW
# ============================================================

class SkinSlideshow(discord.ui.View):

    def __init__(self, hero_name, skins):
        super().__init__(timeout=300)

        self.hero_name = hero_name
        self.skins = skins
        self.current_skin = 0

    def create_embed(self):

        skin_url = self.skins[self.current_skin]

        embed = discord.Embed(
            title=f"{self.hero_name} — Skins",
            description=(
                f"Skin {self.current_skin + 1} "
                f"of {len(self.skins)}"
            )
        )

        embed.set_image(url=skin_url)

        embed.set_footer(
            text="Honor of Kings Wiki • Skin Slideshow"
        )

        return embed

    @discord.ui.button(
        label="◀ Previous",
        style=discord.ButtonStyle.secondary
    )
    async def previous(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        self.current_skin -= 1

        if self.current_skin < 0:
            self.current_skin = len(self.skins) - 1

        await interaction.response.edit_message(
            embed=self.create_embed(),
            view=self
        )

    @discord.ui.button(
        label="▶ Next",
        style=discord.ButtonStyle.primary
    )
    async def next(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        self.current_skin += 1

        if self.current_skin >= len(self.skins):
            self.current_skin = 0

        await interaction.response.edit_message(
            embed=self.create_embed(),
            view=self
        )
async def get_skills(hero_name, html):

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    skills = []

    # Find the EXACT "Skills [ ]" heading
    skills_heading = None

    for heading in soup.find_all(["h2", "h3"]):

        title = clean_text(
            heading.get_text(" ", strip=True)
        )

        title = title.replace("[edit]", "")
        title = title.replace("[ ]", "")
        title = title.strip()

        if title.lower() == "skills":
            skills_heading = heading
            break

    if not skills_heading:
        print("Skills heading not found")
        return []

    current_skill = None

    for element in skills_heading.find_all_next():

        # ------------------------------------------------
        # Stop when Skills section ends
        # ------------------------------------------------

        if element.name == "h2":

            title = clean_text(
                element.get_text(" ", strip=True)
            )

            title = title.replace("[edit]", "")
            title = title.replace("[ ]", "")
            title = title.strip().lower()

            if title in [
                "skins",
                "partner and counter",
                "strategies"
            ]:
                break

        # ------------------------------------------------
        # Skill name
        # ------------------------------------------------

        if element.name == "h3":

            name = clean_text(
                element.get_text(" ", strip=True)
            )

            if not name:
                continue

            # Save previous skill
            if current_skill:
                skills.append(current_skill)

            current_skill = {
                "name": name,
                "description": "",
                "image": None
            }

            continue

        # ------------------------------------------------
        # Skill image
        # ------------------------------------------------

        if element.name == "img" and current_skill:

            src = (
                element.get("data-src")
                or element.get("src")
            )

            if not src:
                continue

            filename = src.split("/")[-1]
            filename = filename.split("?")[0]

            name_without_ext = filename.rsplit(
                ".",
                1
            )[0]

            # Skill images are numbered
            if name_without_ext.isdigit():

                if "/revision/latest/" in src:

                    src = src.split(
                        "/revision/latest/"
                    )[0] + "/revision/latest"

                current_skill["image"] = src

        # ------------------------------------------------
        # Skill description
        # ------------------------------------------------

        if element.name == "p" and current_skill:

            text = clean_text(
                element.get_text(
                    " ",
                    strip=True
                )
            )

            if text:
                current_skill["description"] += (
                    " " + text
                )

    # Save last skill
    if current_skill:
        skills.append(current_skill)

    # Clean descriptions
    for skill in skills:

        skill["description"] = clean_text(
            skill["description"]
        )

    print(
        f"Found {len(skills)} skills for {hero_name}"
    )

    for skill in skills:

        print(
            skill["name"],
            "|",
            skill["image"]
        )

    return skills
class LoreView(discord.ui.View):

    def __init__(self, hero_name, pages):

        super().__init__(
            timeout=300
        )

        self.hero_name = hero_name
        self.pages = pages
        self.page = 0

    def create_embed(self):

        embed = discord.Embed(
            title=f"{self.hero_name} — Lore",
            description=self.pages[self.page]
        )

        embed.set_footer(
            text=(
                f"Honor of Kings Wiki • "
                f"Page {self.page + 1}/{len(self.pages)}"
            )
        )

        return embed

    @discord.ui.button(
        label="◀ Previous",
        style=discord.ButtonStyle.secondary
    )
    async def previous(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        self.page -= 1

        if self.page < 0:
            self.page = len(self.pages) - 1

        await interaction.response.edit_message(
            embed=self.create_embed(),
            view=self
        )

    @discord.ui.button(
        label="▶ Next",
        style=discord.ButtonStyle.primary
    )
    async def next(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        self.page += 1

        if self.page >= len(self.pages):
            self.page = 0

        await interaction.response.edit_message(
            embed=self.create_embed(),
            view=self
        )

class SkillView(discord.ui.View):

    def __init__(self, hero_name, skills):

        super().__init__(
            timeout=300
        )

        self.hero_name = hero_name
        self.skills = skills
        self.current_skill = 0

    def create_embed(self):

        skill = self.skills[
            self.current_skill
        ]

        embed = discord.Embed(
            title=(
                f"{self.hero_name} — "
                f"{skill['name']}"
            ),
            description=(
                skill["description"]
                or "No description found."
            )
        )

        if skill.get("image"):
            embed.set_image(
                url=skill["image"]
            )

        embed.set_footer(
            text=(
                f"Honor of Kings Wiki • "
                f"Skill "
                f"{self.current_skill + 1}/"
                f"{len(self.skills)}"
            )
        )

        return embed

    @discord.ui.button(
        label="◀ Previous",
        style=discord.ButtonStyle.secondary
    )
    async def previous(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        self.current_skill -= 1

        if self.current_skill < 0:
            self.current_skill = (
                len(self.skills) - 1
            )

        await interaction.response.edit_message(
            embed=self.create_embed(),
            view=self
        )

    @discord.ui.button(
        label="▶ Next",
        style=discord.ButtonStyle.primary
    )
    async def next(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        self.current_skill += 1

        if self.current_skill >= len(self.skills):
            self.current_skill = 0

        await interaction.response.edit_message(
            embed=self.create_embed(),
            view=self
        )
class HeroInfoView(discord.ui.View):

    def __init__(
        self,
        hero_name,
        data
    ):

        super().__init__(
            timeout=300
        )

        self.hero_name = hero_name
        self.data = data

        self.page = 0
        self.pages = []

    async def show_section(
        self,
        interaction,
        section_name,
        title
    ):

        lines = self.data.get(
            section_name
        )

        self.pages = make_pages(
            title,
            lines
        )

        self.page = 0

        embed = discord.Embed(
            title=f"{self.hero_name} — {title}",
            description=self.pages[0]
        )

        embed.set_footer(
            text=(
                f"Honor of Kings Wiki • "
                f"Page 1/{len(self.pages)}"
            )
        )

        await interaction.response.edit_message(
            embed=embed,
            view=self
        )

    # --------------------------------------------------------
    # BACKGROUND
    # --------------------------------------------------------

    @discord.ui.button(
        label="✨ Skins",
        style=discord.ButtonStyle.primary,
        row=1
    )
    async def skins(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        skin_images = self.data.get(
            "skin_images",
            []
        )

        if not skin_images:
            await interaction.response.send_message(
                f"❌ No skin images found for "
                f"**{self.hero_name}**.",
                ephemeral=True
            )
            return

        slideshow = SkinSlideshow(
            self.hero_name,
            skin_images
        )

        await interaction.response.edit_message(
            embed=slideshow.create_embed(),
            view=slideshow
        )

    # --------------------------------------------------------
    # LORE
    # --------------------------------------------------------

    @discord.ui.button(
        label="📜 Lore",
        style=discord.ButtonStyle.secondary,
        row=0
    )
    async def lore(
        self,
        interaction,
        button
    ):

        lines = self.data.get(
            "lore",
            []
        )

        pages = make_pages(
            "Lore",
            lines
        )

        if not pages:
            await interaction.response.send_message(
                "❌ No Lore information found.",
                ephemeral=True
            )
            return

        view = LoreView(
            self.hero_name,
            pages
        )

        await interaction.response.edit_message(
            embed=view.create_embed(),
            view=view
        )
    # --------------------------------------------------------
    # SKILLS
    # --------------------------------------------------------

    @discord.ui.button(
        label="⚔️ Skills",
        style=discord.ButtonStyle.primary,
        row=0
    )
    async def skills(
        self,
        interaction,
        button
    ):

        skills = self.data.get(
            "skills",
            []
        )

        if not skills:
            await interaction.response.send_message(
                f"❌ No skill information found for "
                f"**{self.hero_name}**.",
                ephemeral=True
            )
            return

        view = SkillView(
            self.hero_name,
            skills
        )

        await interaction.response.edit_message(
            embed=view.create_embed(),
            view=view
        )

    # --------------------------------------------------------
    # STRATEGIES
    # --------------------------------------------------------

    @discord.ui.button(
        label="🏆 Strategies",
        style=discord.ButtonStyle.secondary,
        row=1
    )
    async def strategies(
        self,
        interaction,
        button
    ):

        await self.show_section(
            interaction,
            "strategies",
            "Strategies"
        )


# ============================================================
# BACK BUTTON
# ============================================================

class BackView(discord.ui.View):

    def __init__(
        self,
        hero_name,
        data
    ):

        super().__init__(
            timeout=300
        )

        self.hero_name = hero_name
        self.data = data

    @discord.ui.button(
        label="◀ Back to Hero",
        style=discord.ButtonStyle.secondary
    )
    async def back(
        self,
        interaction,
        button
    ):

        embed = discord.Embed(
            title=f"⚔️ {self.hero_name}",
            description="Select a category below."
        )

        embed.add_field(
            name="📖 Background",
            value="Hero background",
            inline=True
        )

        embed.add_field(
            name="📜 Lore",
            value="Hero lore",
            inline=True
        )

        embed.add_field(
            name="⚔️ Skills",
            value="Hero skills",
            inline=True
        )

        embed.add_field(
            name="✨ Skins",
            value="Hero skins",
            inline=True
        )

        embed.add_field(
            name="🏆 Strategies",
            value="Gameplay strategies",
            inline=True
        )

        await interaction.response.edit_message(
            embed=embed,
            view=HeroInfoView(
                self.hero_name,
                self.data
            )
        )


# ============================================================
# /HERO
# ============================================================

@bot.tree.command(
    name="hero",
    description="View information about a Honor of Kings hero"
)
async def hero(
    interaction: discord.Interaction,
    hero_name: str
):
    await interaction.response.defer()

    print(f"Searching wiki for: {hero_name}")

    data = await get_hero_data(hero_name)

    if not data:
        await interaction.followup.send(
            f"❌ I couldn't find information for **{hero_name}**."
        )
        return

    embed = discord.Embed(
        title=f"⚔️ {hero_name}",
        description="Choose a category below."
    )

    embed.add_field(
        name="📖 Background",
        value="Hero background",
        inline=True
    )

    embed.add_field(
        name="📜 Lore",
        value="Hero lore",
        inline=True
    )

    embed.add_field(
        name="⚔️ Skills",
        value="Hero abilities",
        inline=True
    )

    embed.add_field(
        name="✨ Skins",
        value="Hero skins",
        inline=True
    )

    embed.add_field(
        name="🏆 Strategies",
        value="Gameplay strategies",
        inline=True
    )

    view = HeroInfoView(
        hero_name,
        data
    )

    await interaction.followup.send(
        embed=embed,
        view=view
    )


# ============================================================
# READY + SYNC
# ============================================================

@bot.event
async def on_ready():

    try:

        synced = await bot.tree.sync()

        print(
            f"Logged in as {bot.user}"
        )

        print(
            f"Synced {len(synced)} slash command(s)."
        )

        print(
            "Bot is ready!"
        )

    except Exception as error:

        print(
            f"Command sync error: {error}"
        )


# ============================================================
# RUN
# ============================================================

bot.run(TOKEN)
