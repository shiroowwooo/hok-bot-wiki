import os
import re
import json
import shutil
from urllib.parse import quote

import discord
from discord.ext import commands
import aiohttp
from bs4 import BeautifulSoup


# ============================================================
# CONFIG
# ============================================================

TOKEN = os.getenv("TOKEN")

MEDIA_API = "https://media-library-api.vincentpatayan88.workers.dev"
ADMIN_DISCORD_ID = 820945208853266442

HEROES_FILE = "heroes.json"

TENCENT_HERO_LIST = (
    "https://pvp.qq.com/web201605/js/herolist.json"
)

FANDOM_API = (
    "https://honor-of-kings.fandom.com/api.php"
)



# ============================================================
# BOT
# ============================================================

intents = discord.Intents.default()

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)



@bot.tree.command(name="setpassword", description="Change the Media Library website password")
async def setpassword(interaction: discord.Interaction, password: str):
    if interaction.user.id != ADMIN_DISCORD_ID:
        await interaction.response.send_message("You are not authorized.", ephemeral=True)
        return

    if len(password) < 8 or len(password) > 200:
        await interaction.response.send_message("Password must be 8-200 characters.", ephemeral=True)
        return

    secret = os.getenv("MEDIA_ADMIN_SECRET")
    if not secret:
        await interaction.response.send_message("Admin secret is not configured.", ephemeral=True)
        return

    headers = {
        "X-Media-Admin-Secret": secret,
        "X-Discord-User-ID": str(interaction.user.id),
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{MEDIA_API}/api/admin/password",
                json={"password": password},
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as response:
                data = await response.json(content_type=None)

        if response.status == 200 and data.get("ok"):
            await interaction.response.send_message(
                "✅ Media Library password changed.",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                f"❌ Failed to change password: {data.get('error', 'Unknown error')}",
                ephemeral=True,
            )

    except Exception as e:
        await interaction.response.send_message(
            f"❌ Could not contact Media Library: {type(e).__name__}",
            ephemeral=True,
        )

# ============================================================
# LOAD HERO DATABASE
# ============================================================

def load_heroes():
    try:
        with open(
            HEROES_FILE,
            "r",
            encoding="utf-8"
        ) as file:
            data = json.load(file)

        return data.get("heroes", [])

    except Exception as error:
        print(f"Failed to load heroes.json: {error}")
        return []


heroes = load_heroes()


# ============================================================
# FIND HERO
# ============================================================

def find_hero(hero_name):
    if not hero_name:
        return None

    search = hero_name.strip().lower()

    # Exact Global name
    for hero in heroes:
        if hero.get("global", "").lower() == search:
            return hero

    # Exact Chinese name
    for hero in heroes:
        if hero.get("cn", "").lower() == search:
            return hero

    # Aliases
    for hero in heroes:

        aliases = hero.get("aliases", [])

        if isinstance(aliases, str):
            aliases = [aliases]

        for alias in aliases:
            if alias.lower() == search:
                return hero

    # Partial Global name
    for hero in heroes:
        global_name = hero.get(
            "global",
            ""
        ).lower()

        if search in global_name:
            return hero

    # Partial Chinese name
    for hero in heroes:
        cn_name = hero.get(
            "cn",
            ""
        ).lower()

        if search in cn_name:
            return hero

    return None


# ============================================================
# TENCENT SKIN UPDATE
# ============================================================

async def update_skins():

    print("Updating Tencent skins...")

    try:

        if not os.path.exists(HEROES_FILE):
            print("heroes.json not found.")
            return

        # Backup before updating
        shutil.copy2(
            HEROES_FILE,
            "heroes_backup.json"
        )

        headers = {
            "User-Agent": "Mozilla/5.0"
        }

        timeout = aiohttp.ClientTimeout(
            total=60
        )

        async with aiohttp.ClientSession(
            timeout=timeout,
            headers=headers
        ) as session:

            async with session.get(
                TENCENT_HERO_LIST
            ) as response:

                if response.status != 200:
                    print(
                        f"Tencent request failed: "
                        f"HTTP {response.status}"
                    )
                    return

                tencent_data = await response.json(
                    content_type=None
                )

        updated = 0

        # Build Chinese-name lookup
        tencent_by_cn = {}

        for item in tencent_data:

            cn_name = item.get(
                "cname",
                ""
            ).strip()

            if cn_name:
                tencent_by_cn[cn_name] = item

        for hero in heroes:

            cn_name = hero.get(
                "cn",
                ""
            ).strip()

            if not cn_name:
                continue

            tencent_hero = tencent_by_cn.get(
                cn_name
            )

            if not tencent_hero:
                print(
                    f"No Tencent match: {cn_name}"
                )
                continue

            hero_id = tencent_hero.get(
                "ename"
            )

            skin_name = tencent_hero.get(
                "skin_name",
                ""
            )

            if not hero_id:
                continue

            skin_names = [
                name.strip()
                for name in skin_name.split("|")
                if name.strip()
            ]

            skins = []

            for index, skin in enumerate(
                skin_names,
                start=1
            ):

                image_url = (
                    "https://game.gtimg.cn/images/"
                    f"yxzj/img201606/skin/"
                    f"hero-info/{hero_id}/"
                    f"{hero_id}-bigskin-{index}.jpg"
                )

                skins.append({
                    "cn": skin,
                    "image": image_url
                })

            if skins:

                hero["skins"] = skins

                updated += 1

                print(
                    f"Updated {cn_name}: "
                    f"{len(skins)} skins"
                )

        with open(
            HEROES_FILE,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                {
                    "heroes": heroes
                },
                file,
                ensure_ascii=False,
                indent=2
            )

        print(
            f"Tencent skin update complete. "
            f"{updated} heroes updated."
        )

    except Exception as error:

        print(
            f"Tencent skin update failed: {error}"
        )

        print(
            "Your previous heroes.json backup "
            "was preserved."
        )


# ============================================================
# FANDOM WIKI PAGE
# ============================================================

async def get_hero_page(hero_name):

    headers = {
        "User-Agent":
            "HOK-Wiki-Discord-Bot/1.0"
    }

    timeout = aiohttp.ClientTimeout(
        total=30
    )

    async with aiohttp.ClientSession(
        timeout=timeout,
        headers=headers
    ) as session:

        # ----------------------------------------------------
        # SEARCH WIKI
        # ----------------------------------------------------

        search_params = {
            "action": "query",
            "list": "search",
            "srsearch": hero_name,
            "format": "json",
            "srlimit": 5
        }

        try:

            async with session.get(
                FANDOM_API,
                params=search_params
            ) as response:

                if response.status != 200:
                    print(
                        f"Wiki search failed: "
                        f"HTTP {response.status}"
                    )
                    return None

                search_data = await response.json()

        except Exception as error:

            print(
                f"Wiki search error: {error}"
            )

            return None

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

        # ----------------------------------------------------
        # GET PAGE HTML
        # ----------------------------------------------------

        page_params = {
            "action": "parse",
            "page": page_title,
            "prop": "text",
            "format": "json"
        }

        try:

            async with session.get(
                FANDOM_API,
                params=page_params
            ) as response:

                if response.status != 200:
                    print(
                        f"Wiki page failed: "
                        f"HTTP {response.status}"
                    )
                    return None

                page_data = await response.json()

        except Exception as error:

            print(
                f"Wiki page error: {error}"
            )

            return None

        if "parse" not in page_data:

            print(
                "Wiki API did not return page content."
            )

            return None

        return (
            page_data["parse"]
            ["text"]["*"]
        )


# ============================================================
# CLEAN TEXT
# ============================================================

def clean_text(text):

    if not text:
        return ""

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
        "[ ]",
        ""
    )

    return text.strip()


# ============================================================
# GET SECTION
# ============================================================

def get_section(
    soup,
    section_name
):

    headings = soup.find_all(
        ["h2", "h3"]
    )

    start = None

    for heading in headings:

        title = clean_text(
            heading.get_text(
                " ",
                strip=True
            )
        )

        if (
            title.lower()
            == section_name.lower()
        ):

            start = heading
            break

    if not start:
        return []

    content = []

    for element in start.find_all_next():

        # Stop at next major section
        if element.name == "h2":

            title = clean_text(
                element.get_text(
                    " ",
                    strip=True
                )
            )

            if (
                title.lower()
                != section_name.lower()
            ):
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

            if not text:
                continue

            if text.lower() in [
                "contents",
                "background",
                "lore",
                "skills",
                "skins",
                "strategies"
            ]:
                continue

            content.append(text)

    return content


# ============================================================
# LORE
# ============================================================

def get_lore(soup):

    # First try the actual Lore section
    section = get_section(
        soup,
        "Lore"
    )

    if section:
        return section

    # Fallback to GitHub bot's paragraph detection
    paragraphs = soup.find_all("p")

    content = []

    started = False

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

    for paragraph in paragraphs:

        text = clean_text(
            paragraph.get_text(
                " ",
                strip=True
            )
        )

        if not text:
            continue

        lower = text.lower()

        if (
            "hero in honor of kings"
            in lower
        ):
            continue

        if not started:

            if any(
                word in lower
                for word in story_words
            ):
                started = True

        if not started:
            continue

        content.append(text)

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

    return cleaned


# ============================================================
# STRATEGIES
# ============================================================

def get_strategies(soup):

    strategies = get_section(
        soup,
        "Strategies"
    )

    if strategies:
        return strategies

    return []


# ============================================================
# SKILLS
# ============================================================

async def get_skills(
    hero_name,
    html
):

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    skills = []

    skills_heading = None

    # Find Skills heading
    for heading in soup.find_all(
        ["h2", "h3"]
    ):

        title = clean_text(
            heading.get_text(
                " ",
                strip=True
            )
        )

        if (
            title.lower()
            == "skills"
        ):

            skills_heading = heading
            break

    if not skills_heading:

        print(
            "Skills heading not found"
        )

        return []

    current_skill = None

    for element in (
        skills_heading.find_all_next()
    ):

        # ----------------------------------------------------
        # STOP AT NEXT SECTION
        # ----------------------------------------------------

        if element.name == "h2":

            title = clean_text(
                element.get_text(
                    " ",
                    strip=True
                )
            ).lower()

            if title != "skills":
                break

        # ----------------------------------------------------
        # SKILL NAME
        # ----------------------------------------------------

        if element.name == "h3":

            name = clean_text(
                element.get_text(
                    " ",
                    strip=True
                )
            )

            if not name:
                continue

            if current_skill:

                skills.append(
                    current_skill
                )

            current_skill = {
                "name": name,
                "description": "",
                "image": None
            }

            continue

        # ----------------------------------------------------
        # SKILL IMAGE
        # ----------------------------------------------------

        if (
            element.name == "img"
            and current_skill
        ):

            src = (
                element.get("data-src")
                or element.get("src")
            )

            if not src:
                continue

            if src.startswith("//"):
                src = "https:" + src

            filename = (
                src.split("/")[-1]
                .split("?")[0]
            )

            name_without_ext = (
                filename.rsplit(
                    ".",
                    1
                )[0]
            )

            if name_without_ext.isdigit():

                if (
                    "/revision/latest/"
                    in src
                ):

                    src = (
                        src.split(
                            "/revision/latest/"
                        )[0]
                        + "/revision/latest"
                    )

                current_skill[
                    "image"
                ] = src

        # ----------------------------------------------------
        # SKILL DESCRIPTION
        # ----------------------------------------------------

        if (
            element.name == "p"
            and current_skill
        ):

            text = clean_text(
                element.get_text(
                    " ",
                    strip=True
                )
            )

            if text:

                current_skill[
                    "description"
                ] += " " + text

    # Save final skill
    if current_skill:
        skills.append(
            current_skill
        )

    for skill in skills:

        skill["description"] = clean_text(
            skill["description"]
        )

    print(
        f"Found {len(skills)} skills "
        f"for {hero_name}"
    )

    return skills


# ============================================================
# HERO DATA
# ============================================================

async def get_hero_data(
    hero_name
):

    html = await get_hero_page(
        hero_name
    )

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

        "strategies": get_strategies(
            soup
        )
    }

    return data


# ============================================================
# MAKE DISCORD PAGES
# ============================================================

def make_pages(
    title,
    lines,
    max_chars=3800
):

    if not lines:

        return [
            "No information was found "
            "on the wiki."
        ]

    pages = []

    current = ""

    for line in lines:

        line = clean_text(
            line
        )

        if not line:
            continue

        line = "• " + line

        if (
            len(current)
            + len(line)
            + 1
            > max_chars
        ):

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
# TENCENT SKIN SLIDESHOW
# ============================================================

class SkinView(discord.ui.View):

    def __init__(
        self,
        hero,
        timeout=300
    ):

        super().__init__(
            timeout=timeout
        )

        self.hero = hero

        self.skins = hero.get(
            "skins",
            []
        )

        self.current_skin = 0

    def create_embed(self):

        if not self.skins:

            return discord.Embed(
                title=(
                    f"{self.hero.get('global', 'Hero')} "
                    f"— Skins"
                ),
                description="No skins found."
            )

        skin = self.skins[
            self.current_skin
        ]

        hero_name = self.hero.get(
            "global",
            self.hero.get(
                "cn",
                "Hero"
            )
        )

        skin_name = skin.get(
            "cn",
            f"Skin {self.current_skin + 1}"
        )

        image_url = skin.get(
            "image"
        )

        embed = discord.Embed(
            title=(
                f"✨ {hero_name} — {skin_name}"
            ),
            description=(
                f"Skin "
                f"{self.current_skin + 1}"
                f"/{len(self.skins)}"
            )
        )

        if image_url:
            embed.set_image(
                url=image_url
            )

        embed.set_footer(
            text=(
                "Honor of Kings • "
                "Tencent Skin Slideshow"
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

        if not self.skins:
            await interaction.response.defer()
            return

        self.current_skin -= 1

        if self.current_skin < 0:

            self.current_skin = (
                len(self.skins) - 1
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

        if not self.skins:
            await interaction.response.defer()
            return

        self.current_skin += 1

        if (
            self.current_skin
            >= len(self.skins)
        ):

            self.current_skin = 0

        await interaction.response.edit_message(
            embed=self.create_embed(),
            view=self
        )


# ============================================================
# LORE VIEW
# ============================================================

class LoreView(discord.ui.View):

    def __init__(
        self,
        hero_name,
        pages
    ):

        super().__init__(
            timeout=300
        )

        self.hero_name = hero_name
        self.pages = pages
        self.page = 0

    def create_embed(self):

        embed = discord.Embed(
            title=(
                f"{self.hero_name} — Lore"
            ),
            description=self.pages[
                self.page
            ]
        )

        embed.set_footer(
            text=(
                f"Honor of Kings Wiki • "
                f"Page {self.page + 1}/"
                f"{len(self.pages)}"
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

            self.page = (
                len(self.pages) - 1
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

        self.page += 1

        if (
            self.page
            >= len(self.pages)
        ):

            self.page = 0

        await interaction.response.edit_message(
            embed=self.create_embed(),
            view=self
        )


# ============================================================
# SKILL VIEW
# ============================================================

class SkillView(discord.ui.View):

    def __init__(
        self,
        hero_name,
        skills
    ):

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
                skill.get(
                    "description",
                    ""
                )
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

        if (
            self.current_skill
            >= len(self.skills)
        ):

            self.current_skill = 0

        await interaction.response.edit_message(
            embed=self.create_embed(),
            view=self
        )


# ============================================================
# HERO INFO VIEW
# ============================================================

class HeroInfoView(
    discord.ui.View
):

    def __init__(
        self,
        hero_name,
        data,
        hero
    ):

        super().__init__(
            timeout=300
        )

        self.hero_name = hero_name
        self.data = data
        self.hero = hero

    async def show_section(
        self,
        interaction,
        section_name,
        title
    ):

        lines = self.data.get(
            section_name,
            []
        )

        pages = make_pages(
            title,
            lines
        )

        embed = discord.Embed(
            title=(
                f"{self.hero_name} — "
                f"{title}"
            ),
            description=pages[0]
        )

        embed.set_footer(
            text=(
                f"Honor of Kings Wiki • "
                f"Page 1/{len(pages)}"
            )
        )

        # If multiple pages, use a page view
        if len(pages) > 1:

            view = SectionView(
                self.hero_name,
                title,
                pages
            )

            await interaction.response.edit_message(
                embed=view.create_embed(),
                view=view
            )

        else:

            await interaction.response.edit_message(
                embed=embed,
                view=self
            )

    # --------------------------------------------------------
    # BACKGROUND
    # --------------------------------------------------------

    @discord.ui.button(
        label="📖 Background",
        style=discord.ButtonStyle.secondary,
        row=0
    )
    async def background(
        self,
        interaction,
        button
    ):

        await self.show_section(
            interaction,
            "background",
            "Background"
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
                f"❌ No skill information found "
                f"for **{self.hero_name}**.",
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
    # SKINS
    # --------------------------------------------------------

    @discord.ui.button(
        label="✨ Skins",
        style=discord.ButtonStyle.primary,
        row=1
    )
    async def skins(
        self,
        interaction,
        button
    ):

        skins = self.hero.get(
            "skins",
            []
        )

        if not skins:

            await interaction.response.send_message(
                f"❌ No Tencent skins found "
                f"for **{self.hero_name}**.",
                ephemeral=True
            )

            return

        view = SkinView(
            self.hero
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
# SECTION PAGE VIEW
# ============================================================

class SectionView(
    discord.ui.View
):

    def __init__(
        self,
        hero_name,
        title,
        pages
    ):

        super().__init__(
            timeout=300
        )

        self.hero_name = hero_name
        self.title = title
        self.pages = pages
        self.page = 0

    def create_embed(self):

        embed = discord.Embed(
            title=(
                f"{self.hero_name} — "
                f"{self.title}"
            ),
            description=self.pages[
                self.page
            ]
        )

        embed.set_footer(
            text=(
                f"Honor of Kings Wiki • "
                f"Page {self.page + 1}/"
                f"{len(self.pages)}"
            )
        )

        return embed

    @discord.ui.button(
        label="◀ Previous",
        style=discord.ButtonStyle.secondary
    )
    async def previous(
        self,
        interaction,
        button
    ):

        self.page -= 1

        if self.page < 0:
            self.page = (
                len(self.pages) - 1
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
        interaction,
        button
    ):

        self.page += 1

        if (
            self.page
            >= len(self.pages)
        ):

            self.page = 0

        await interaction.response.edit_message(
            embed=self.create_embed(),
            view=self
        )


# ============================================================
# BACK TO HERO
# ============================================================

class BackView(
    discord.ui.View
):

    def __init__(
        self,
        hero_name,
        data,
        hero
    ):

        super().__init__(
            timeout=300
        )

        self.hero_name = hero_name
        self.data = data
        self.hero = hero

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
            title=(
                f"⚔️ {self.hero_name}"
            ),
            description=(
                "Select a category below."
            )
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
            value="Tencent skins",
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
                self.data,
                self.hero
            )
        )


# ============================================================
# /HERO
# ============================================================

@bot.tree.command(
    name="hero",
    description=(
        "View information about a "
        "Honor of Kings hero"
    )
)
async def hero(
    interaction: discord.Interaction,
    hero_name: str
):

    await interaction.response.defer()

    print(
        f"Searching hero: {hero_name}"
    )

    # Find hero in local database
    hero = find_hero(
        hero_name
    )

    if not hero:

        await interaction.followup.send(
            f"❌ I couldn't find "
            f"**{hero_name}** in the hero database."
        )

        return

    display_name = hero.get(
        "global",
        hero.get(
            "cn",
            hero_name
        )
    )

    # Get wiki information
    data = await get_hero_data(
        display_name
    )

    if not data:

        await interaction.followup.send(
            f"❌ I found **{display_name}** "
            f"in the database, but couldn't "
            f"load the wiki information."
        )

        return

    embed = discord.Embed(
        title=f"⚔️ {display_name}",
        description=(
            f"**{hero.get('cn', '')}**\n\n"
            "Choose a category below."
        )
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
        value="Tencent skins",
        inline=True
    )

    embed.add_field(
        name="🏆 Strategies",
        value="Gameplay strategies",
        inline=True
    )

    view = HeroInfoView(
        display_name,
        data,
        hero
    )

    await interaction.followup.send(
        embed=embed,
        view=view
    )


# ============================================================
# /SKINS
# ============================================================

@bot.tree.command(
    name="skins",
    description="View a hero's Tencent skins"
)
async def skins(
    interaction: discord.Interaction,
    hero_name: str
):

    hero = find_hero(
        hero_name
    )

    if not hero:

        await interaction.response.send_message(
            f"❌ Hero **{hero_name}** "
            f"was not found."
        )

        return

    skin_list = hero.get(
        "skins",
        []
    )

    if not skin_list:

        await interaction.response.send_message(
            f"❌ No skins found for "
            f"**{hero.get('global', hero_name)}**."
        )

        return

    view = SkinView(
        hero
    )

    await interaction.response.send_message(
        embed=view.create_embed(),
        view=view
    )


# ============================================================
# /HEROES
# ============================================================

@bot.tree.command(
    name="heroes",
    description="List all Honor of Kings heroes"
)
async def heroes_command(
    interaction: discord.Interaction
):

    if not heroes:

        await interaction.response.send_message(
            "❌ heroes.json is empty."
        )

        return

    names = []

    for hero in heroes:

        global_name = hero.get(
            "global"
        )

        cn_name = hero.get(
            "cn"
        )

        if global_name and cn_name:

            names.append(
                f"• **{global_name}** — {cn_name}"
            )

        elif global_name:

            names.append(
                f"• **{global_name}**"
            )

    # Discord message limit
    chunks = []
    current = ""

    for name in names:

        if (
            len(current)
            + len(name)
            + 1
            > 3800
        ):

            chunks.append(
                current
            )

            current = name

        else:

            if current:
                current += "\n"

            current += name

    if current:
        chunks.append(
            current
        )

    embed = discord.Embed(
        title="⚔️ Honor of Kings Heroes",
        description=chunks[0]
    )

    embed.set_footer(
        text=(
            f"{len(heroes)} heroes "
            "in database"
        )
    )

    await interaction.response.send_message(
        embed=embed
    )

    # Send additional pages if needed
    for chunk in chunks[1:]:

        await interaction.followup.send(
            chunk
        )


# ============================================================
# READY
# ============================================================

@bot.event
async def on_ready():

    print(
        f"Logged in as {bot.user}"
    )

    # Update Tencent skins
    await update_skins()

    # Reload after update
    global heroes
    heroes = load_heroes()

    try:

        synced = await bot.tree.sync()

        print(
            f"Synced {len(synced)} "
            "slash command(s)."
        )

    except Exception as error:

        print(
            f"Command sync error: {error}"
        )

    print(
        "Bot is ready!"
    )


# ============================================================
# RUN
# ============================================================

if not TOKEN:

    print(
        "ERROR: TOKEN environment variable "
        "is not set."
    )

else:

    bot.run(TOKEN)
