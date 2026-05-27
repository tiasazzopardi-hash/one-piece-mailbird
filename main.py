import discord
from discord.ext import commands
from discord import app_commands
import os
import asyncio
from datetime import datetime, timezone
import traceback
import re
import json

# =========================================================
# TOKEN
# =========================================================
TOKEN = os.getenv("DISCORD_TOKEN")

# =========================================================
# INTENTS
# =========================================================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# =========================================================
# FILES
# =========================================================
POSTER_FOLDER = "bounty_posters"
DEFAULT_LOST_POSTER = "bounty_posters/lost.png"

# =========================================================
# ADMINS
# =========================================================
AUTHORIZED_USERS = [
    "king_matti_123",
    "gamerguyy21",
    "meownugs1"
]

# =========================================================
# STORAGE
# =========================================================
titles = {}
abilities = {}
weapons = {}

# =========================================================
# DELIVERY
# =========================================================
delivery_channel_id = None
last_notified = {}

# =========================================================
# SERIES DATA
# =========================================================
series_status = {
    "One Piece (Sub) - Crunchyroll": {
        "episode": 1100,
        "released": True
    },

    "One Piece (Dub) - Anime Dub": {
        "episode": 1080,
        "released": True
    },

    "One Piece Remake (Sub) - Crunchyroll": {
        "episode": 0,
        "released": False
    },

    "One Piece Remake (Dub) - Anime Dub": {
        "episode": 0,
        "released": False
    },

    "One Piece LEGO - Netflix": {
        "released": False,
        "release_date": "September 29th"
    },

    "One Piece Live Action - Netflix": {
        "released": True
    }
}

# =========================================================
# SAVE DATA
# =========================================================
def save_data():

    os.makedirs(
        "data",
        exist_ok=True
    )

    data = {
        "titles": titles,
        "abilities": abilities,
        "weapons": weapons
    }

    with open(
        "data/pirate_data.json",
        "w"
    ) as f:

        json.dump(
            data,
            f,
            indent=4
        )

# =========================================================
# LOAD DATA
# =========================================================
def load_data():

    global titles
    global abilities
    global weapons

    os.makedirs(
        "data",
        exist_ok=True
    )

    path = "data/pirate_data.json"

    if not os.path.exists(path):

        with open(path, "w") as f:

            json.dump(
                {
                    "titles": {},
                    "abilities": {},
                    "weapons": {}
                },
                f,
                indent=4
            )

    with open(path, "r") as f:

        data = json.load(f)

        titles = data.get("titles", {})
        abilities = data.get("abilities", {})
        weapons = data.get("weapons", {})

# =========================================================
# NORMALIZE
# =========================================================
def normalize(text):

    text = text.lower().strip()

    text = text.replace(" ", "")

    text = re.sub(
        r'[^a-z0-9_-]',
        '',
        text
    )

    return text

# =========================================================
# FIND MEMBER
# =========================================================
def find_member(guild, query):

    query = normalize(query)

    for member in guild.members:

        if (
            normalize(member.name) == query
            or
            normalize(member.display_name) == query
        ):
            return member

    for member in guild.members:

        if (
            normalize(member.name).startswith(query)
            or
            normalize(member.display_name).startswith(query)
        ):
            return member

    for member in guild.members:

        if (
            query in normalize(member.name)
            or
            query in normalize(member.display_name)
        ):
            return member

    return None

# =========================================================
# POSTER
# =========================================================
def get_poster_path(username):

    base = normalize(username)

    for ext in [
        "png",
        "jpg",
        "jpeg",
        "webp"
    ]:

        path = os.path.join(
            POSTER_FOLDER,
            f"{base}.{ext}"
        )

        if os.path.exists(path):
            return path

    return None

# =========================================================
# TIME FORMAT
# =========================================================
def format_duration(delta):

    days = delta.days

    years = days // 365

    months = (days % 365) // 30

    remaining_days = days % 30

    return (
        f"{years}y "
        f"{months}m "
        f"{remaining_days}d"
    )

# =========================================================
# STATS FORMAT
# =========================================================
def format_stats(
    member,
    title="Unknown",
    ability="None",
    weapon="None"
):

    role = member.top_role.name

    now = datetime.now(
        timezone.utc
    )

    if member.joined_at:

        crew = format_duration(
            now - member.joined_at
        )

    else:

        crew = "Unknown Seas"

    pirate = format_duration(
        now - member.created_at
    )

    return f"""
🏴‍☠️ **Pirate:** {member.display_name}
🎖️ **Title:** {title}
🎭 **Role:** {role}
🌀 **Abilities:** {ability}
🗡️ **Weapons:** {weapon}
⚓ **Time in Crew:** {crew}
🌊 **Time as Pirate:** {pirate}
"""

# =========================================================
# SLEEP MODE
# =========================================================
SLEEP_MODE = False

# =========================================================
# NUKE COMMAND
# =========================================================
@bot.command()
async def nuke(ctx):

    global SLEEP_MODE

    # DM only
    if not isinstance(
        ctx.channel,
        discord.DMChannel
    ):
        return

    # only you
    if (
        ctx.author.name.lower()
        !=
        "king_matti_123"
    ):
        return

    SLEEP_MODE = True

    await ctx.send(
        "☠️ Sleep mode activated."
    )

# =========================================================
# RESTORE COMMAND
# =========================================================
@bot.command()
async def restore(ctx):

    global SLEEP_MODE

    # DM only
    if not isinstance(
        ctx.channel,
        discord.DMChannel
    ):
        return

    # only you
    if (
        ctx.author.name.lower()
        !=
        "king_matti_123"
    ):
        return

    SLEEP_MODE = False

    await ctx.send(
        "📡 Systems restored."
    )

# =========================================================
# GLOBAL BOT BLOCK
# =========================================================
@bot.check
async def global_sleep_check(ctx):

    global SLEEP_MODE

    # allow restore
    if (
        ctx.command
        and
        ctx.command.name == "restore"
    ):
        return True

    # allow you
    if (
        ctx.author.name.lower()
        ==
        "king_matti_123"
    ):
        return True

    # block everything
    if SLEEP_MODE:

        try:
            await ctx.send(
                "❌ Pirate not found."
            )
        except:
            pass

        return False

    return True

# =========================================================
# SLASH COMMAND BLOCK
# =========================================================
@tree.interaction_check
async def slash_sleep_check(
    interaction: discord.Interaction
):

    global SLEEP_MODE

    # allow you
    if (
        interaction.user.name.lower()
        ==
        "king_matti_123"
    ):
        return True

    # block everything
    if SLEEP_MODE:

        try:
            await interaction.response.send_message(
                "❌ Pirate not found.",
                ephemeral=True
            )
        except:
            pass

        return False

    return True

# =========================================================
# PREFIX STATS
# =========================================================
@bot.command()
async def stats(ctx, *, username):

    member = find_member(
        ctx.guild,
        username
    )

    if not member:

        await ctx.send(
            "❌ Pirate not found."
        )

        return

    poster = (
        get_poster_path(member.name)
        or
        get_poster_path(member.display_name)
    )

    await ctx.send(
        content=format_stats(
            member,
            titles.get(member.name, "Unknown"),
            abilities.get(member.name, "None"),
            weapons.get(member.name, "None")
        ),
        file=(
            discord.File(poster)
            if poster
            else None
        )
    )

# =========================================================
# SLASH STATS
# =========================================================
@tree.command(
    name="stats",
    description="Check pirate stats"
)
async def slash_stats(
    interaction,
    username: str
):

    member = find_member(
        interaction.guild,
        username
    )

    if not member:

        await interaction.response.send_message(
            "❌ Pirate not found.",
            ephemeral=True
        )

        return

    poster = (
        get_poster_path(member.name)
        or
        get_poster_path(member.display_name)
    )

    await interaction.response.send_message(
        content=format_stats(
            member,
            titles.get(member.name, "Unknown"),
            abilities.get(member.name, "None"),
            weapons.get(member.name, "None")
        ),
        file=(
            discord.File(poster)
            if poster
            else None
        )
    )

# =========================================================
# POSTER
# =========================================================
@tree.command(
    name="poster",
    description="Update bounty poster"
)
async def poster(
    interaction,
    username: str,
    picture: discord.Attachment
):

    if (
        interaction.user.name.lower()
        not in AUTHORIZED_USERS
    ):

        await interaction.response.send_message(
            "❌ Not allowed.",
            ephemeral=True
        )

        return

    os.makedirs(
        POSTER_FOLDER,
        exist_ok=True
    )

    ext = (
        picture.filename
        .split(".")[-1]
        .lower()
    )

    if ext not in [
        "png",
        "jpg",
        "jpeg",
        "webp"
    ]:

        await interaction.response.send_message(
            "❌ Invalid format.",
            ephemeral=True
        )

        return

    path = os.path.join(
        POSTER_FOLDER,
        f"{normalize(username)}.{ext}"
    )

    await picture.save(path)

    await interaction.response.send_message(
        "📦 Poster updated."
    )

# =========================================================
# SET TITLE
# =========================================================
@tree.command(
    name="settitle",
    description="Set pirate title"
)
async def set_title(
    interaction,
    username: str,
    title: str
):

    if (
        interaction.user.name.lower()
        not in AUTHORIZED_USERS
    ):

        await interaction.response.send_message(
            "❌ Not allowed.",
            ephemeral=True
        )

        return

    member = find_member(
        interaction.guild,
        username
    )

    if not member:

        await interaction.response.send_message(
            "❌ Pirate not found.",
            ephemeral=True
        )

        return

    titles[member.name] = title

    save_data()

    await interaction.response.send_message(
        f"🎖️ Title set for "
        f"**{member.display_name}**"
    )

# =========================================================
# RESET TITLE
# =========================================================
@tree.command(
    name="resettitle",
    description="Reset pirate title"
)
async def reset_title(
    interaction,
    username: str
):

    if (
        interaction.user.name.lower()
        not in AUTHORIZED_USERS
    ):

        await interaction.response.send_message(
            "❌ Not allowed.",
            ephemeral=True
        )

        return

    member = find_member(
        interaction.guild,
        username
    )

    if not member:

        await interaction.response.send_message(
            "❌ Pirate not found.",
            ephemeral=True
        )

        return

    titles[member.name] = "Unknown"

    save_data()

    await interaction.response.send_message(
        f"🧹 Title reset for "
        f"**{member.display_name}**"
    )

# =========================================================
# SET ABILITIES
# =========================================================
@tree.command(
    name="setability",
    description="Set pirate abilities"
)
async def set_ability(
    interaction,
    username: str,
    ability: str
):

    if (
        interaction.user.name.lower()
        not in AUTHORIZED_USERS
    ):

        await interaction.response.send_message(
            "❌ Not allowed.",
            ephemeral=True
        )

        return

    member = find_member(
        interaction.guild,
        username
    )

    if not member:

        await interaction.response.send_message(
            "❌ Pirate not found.",
            ephemeral=True
        )

        return

    abilities[member.name] = ability

    save_data()

    await interaction.response.send_message(
        f"🌀 Abilities set for "
        f"**{member.display_name}**"
    )

# =========================================================
# RESET ABILITIES
# =========================================================
@tree.command(
    name="resetability",
    description="Reset pirate abilities"
)
async def reset_ability(
    interaction,
    username: str
):

    if (
        interaction.user.name.lower()
        not in AUTHORIZED_USERS
    ):

        await interaction.response.send_message(
            "❌ Not allowed.",
            ephemeral=True
        )

        return

    member = find_member(
        interaction.guild,
        username
    )

    if not member:

        await interaction.response.send_message(
            "❌ Pirate not found.",
            ephemeral=True
        )

        return

    abilities[member.name] = "None"

    save_data()

    await interaction.response.send_message(
        f"🧹 Abilities reset for "
        f"**{member.display_name}**"
    )

# =========================================================
# SET WEAPON
# =========================================================
@tree.command(
    name="setweapon",
    description="Set pirate weapon"
)
async def set_weapon(
    interaction,
    username: str,
    weapon: str
):

    if (
        interaction.user.name.lower()
        not in AUTHORIZED_USERS
    ):

        await interaction.response.send_message(
            "❌ Not allowed.",
            ephemeral=True
        )

        return

    member = find_member(
        interaction.guild,
        username
    )

    if not member:

        await interaction.response.send_message(
            "❌ Pirate not found.",
            ephemeral=True
        )

        return

    weapons[member.name] = weapon

    save_data()

    await interaction.response.send_message(
        f"🗡️ Weapon set for "
        f"**{member.display_name}**"
    )

# =========================================================
# RESET WEAPON
# =========================================================
@tree.command(
    name="resetweapon",
    description="Reset pirate weapon"
)
async def reset_weapon(
    interaction,
    username: str
):

    if (
        interaction.user.name.lower()
        not in AUTHORIZED_USERS
    ):

        await interaction.response.send_message(
            "❌ Not allowed.",
            ephemeral=True
        )

        return

    member = find_member(
        interaction.guild,
        username
    )

    if not member:

        await interaction.response.send_message(
            "❌ Pirate not found.",
            ephemeral=True
        )

        return

    weapons[member.name] = "None"

    save_data()

    await interaction.response.send_message(
        f"🧹 Weapon reset for "
        f"**{member.display_name}**"
    )

# =========================================================
# SET DELIVERY ROUTE
# =========================================================
@tree.command(
    name="setdeliveryroute",
    description="Set episode channel"
)
async def set_route(
    interaction,
    channel: discord.TextChannel
):

    if (
        interaction.user.name.lower()
        not in AUTHORIZED_USERS
    ):

        await interaction.response.send_message(
            "❌ Not allowed.",
            ephemeral=True
        )

        return

    global delivery_channel_id

    delivery_channel_id = channel.id

    await interaction.response.send_message(
        f"📡 Route set to "
        f"{channel.mention}"
    )

# =========================================================
# READY
# =========================================================
@bot.event
async def on_ready():

    load_data()

    await tree.sync()

    print(
        f"Den Den Mushi connected as "
        f"{bot.user}"
    )

# =========================================================
# RUN
# =========================================================
bot.run(TOKEN)