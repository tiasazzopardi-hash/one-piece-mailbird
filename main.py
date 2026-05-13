import discord
from discord.ext import commands
from discord import app_commands
import os
import asyncio
from datetime import datetime, timezone
import traceback
import re

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

# =========================================================
# BOT
# =========================================================
bot = commands.Bot(
    command_prefix="!",
    intents=intents
)

tree = bot.tree

# =========================================================
# FILES
# =========================================================
POSTER_FOLDER = "bounty_posters"
DEFAULT_LOST_POSTER = "bounty_posters/lost.png"

# =========================================================
# AUTHORIZED USERS
# =========================================================
AUTHORIZED_USERS = [
    "king_matti_123",
    "gamerguyy21"
]

# =========================================================
# STORAGE
# =========================================================
titles = {}
ranks = {}
abilities = {}

# =========================================================
# DELIVERY
# =========================================================
delivery_channel_id = None
last_notified = {}

# =========================================================
# TRACKED SERIES
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

    # exact
    for member in guild.members:

        if (
            normalize(member.name) == query
            or
            normalize(member.display_name) == query
        ):
            return member

    # startswith
    for member in guild.members:

        if (
            normalize(member.name).startswith(query)
            or
            normalize(member.display_name).startswith(query)
        ):
            return member

    # partial
    for member in guild.members:

        if (
            query in normalize(member.name)
            or
            query in normalize(member.display_name)
        ):
            return member

    return None

# =========================================================
# POSTER PATH
# =========================================================
def get_poster_path(username):

    base = normalize(username)

    extensions = [
        "png",
        "jpg",
        "jpeg",
        "webp"
    ]

    for ext in extensions:

        path = os.path.join(
            POSTER_FOLDER,
            f"{base}.{ext}"
        )

        if os.path.exists(path):
            return path

    return None

# =========================================================
# FORMAT TIME
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
# FORMAT STATS
# =========================================================
def format_stats(
    member,
    title="Unknown",
    rank="Unranked",
    ability="None"
):

    role = member.top_role.name

    now = datetime.now(
        timezone.utc
    )

    # crew time
    if member.joined_at:

        crew_duration = format_duration(
            now - member.joined_at
        )

    else:

        crew_duration = "Unknown Seas"

    # discord age
    pirate_duration = format_duration(
        now - member.created_at
    )

    return f"""
🏴‍☠️ **Pirate:** {member.display_name}
🎖️ **Title:** {title}
🏆 **Rank:** {rank}
🎭 **Role:** {role}
⚔️ **Ability:** {ability}
⚓ **Time in Crew:** {crew_duration}
🌊 **Time as Pirate:** {pirate_duration}
"""

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
            titles.get(
                member.name,
                "Unknown"
            ),
            ranks.get(
                member.name,
                "Unranked"
            ),
            abilities.get(
                member.name,
                "None"
            )
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
            titles.get(
                member.name,
                "Unknown"
            ),
            ranks.get(
                member.name,
                "Unranked"
            ),
            abilities.get(
                member.name,
                "None"
            )
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

    await interaction.response.send_message(
        f"🧹 Title reset for "
        f"**{member.display_name}**"
    )

# =========================================================
# SET RANK
# =========================================================
@tree.command(
    name="setrank",
    description="Set pirate rank"
)
async def set_rank(
    interaction,
    username: str,
    rank: str
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

    ranks[member.name] = rank

    await interaction.response.send_message(
        f"🏆 Rank set for "
        f"**{member.display_name}**"
    )

# =========================================================
# RESET RANK
# =========================================================
@tree.command(
    name="resetrank",
    description="Reset pirate rank"
)
async def reset_rank(
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

    ranks[member.name] = "Unranked"

    await interaction.response.send_message(
        f"🧹 Rank reset for "
        f"**{member.display_name}**"
    )

# =========================================================
# SET ABILITY
# =========================================================
@tree.command(
    name="setability",
    description="Set pirate ability"
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

    await interaction.response.send_message(
        f"⚔️ Ability set for "
        f"**{member.display_name}**"
    )

# =========================================================
# RESET ABILITY
# =========================================================
@tree.command(
    name="resetability",
    description="Reset pirate ability"
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

    await interaction.response.send_message(
        f"🧹 Ability reset for "
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

    await tree.sync()

    print(
        f"Den Den Mushi connected as "
        f"{bot.user}"
    )

# =========================================================
# RUN
# =========================================================
bot.run(TOKEN)