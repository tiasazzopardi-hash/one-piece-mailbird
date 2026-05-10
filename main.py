import discord
from discord.ext import commands
from discord import app_commands
from discord.app_commands import checks
import os
import asyncio
from datetime import datetime, timezone
import traceback
import re

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

POSTER_FOLDER = "bounty_posters"
DEFAULT_LOST_POSTER = "bounty_posters/lost.png"

delivery_channel_id = None

# ---------- TRACKED SERIES ----------
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

last_notified = {}


# ---------- NAME NORMALIZATION ----------
def normalize(text):
    text = text.lower().strip()

    # remove spaces
    text = text.replace(" ", "")

    # remove weird filename-breaking characters
    text = re.sub(r'[^a-z0-9_-]', '', text)

    return text

# ---------- SMART MEMBER FINDER ----------
def find_member(guild, query: str):
    query = normalize(query)

    for member in guild.members:
        if normalize(member.name) == query or normalize(member.display_name) == query:
            return member

    for member in guild.members:
        if normalize(member.name).startswith(query) or normalize(member.display_name).startswith(query):
            return member

    for member in guild.members:
        if query in normalize(member.name) or query in normalize(member.display_name):
            return member

    return None


# ---------- POSTER FUNCTION ----------
def get_poster_path(username):
    base = normalize(username)
    extensions = ["png", "jpg", "jpeg", "webp"]

    for ext in extensions:
        path = os.path.join(POSTER_FOLDER, f"{base}.{ext}")

        if os.path.exists(path):
            return path

    return None


# ---------- TIME FORMAT ----------
def format_duration(delta):
    days = delta.days
    years = days // 365
    months = (days % 365) // 30

    return f"{years}y {months}m {days % 30}d"


# ---------- STATS FORMAT ----------
def format_stats(member: discord.Member):
    role = member.top_role.name
    now = datetime.now(timezone.utc)

    if member.joined_at:
        crew_time = now - member.joined_at
        crew_duration = format_duration(crew_time)
    else:
        crew_duration = "Unknown Seas"

    account_time = now - member.created_at
    pirate_duration = format_duration(account_time)

    return f"""📜 **DEN DEN MUSHI REPORT** 📜

🏴‍☠️ **Pirate:** {member.display_name}
🎭 **Role:** {role}
⚓ **Time in Crew:** {crew_duration}
🌊 **Time as Pirate:** {pirate_duration}
"""


# ---------- PREFIX COMMAND ----------
@bot.command()
async def stats(ctx, *, username: str):
    member = find_member(ctx.guild, username)

    if not member:
        await ctx.send(
            "❌ **DEN DEN MUSHI ERROR**\n"
            "That pirate is not part of this crew."
        )
        return

    poster_path = (
        get_poster_path(member.name)
        or get_poster_path(member.display_name)
    )

    if poster_path:
        await ctx.send(
            content=format_stats(member),
            file=discord.File(poster_path)
        )

    elif os.path.exists(DEFAULT_LOST_POSTER):
        await ctx.send(
            content=format_stats(member) + "\n⚠️ Poster lost at sea...",
            file=discord.File(DEFAULT_LOST_POSTER)
        )

    else:
        await ctx.send(
            format_stats(member) +
            "\n⚠️ No bounty poster found."
        )


# ---------- SLASH STATS ----------
@tree.command(name="stats", description="Check a pirate's bounty")
@app_commands.describe(
    username="The pirate's username or nickname"
)
async def slash_stats(
    interaction: discord.Interaction,
    username: str
):
    member = find_member(interaction.guild, username)

    if not member:
        await interaction.response.send_message(
            "❌ **DEN DEN MUSHI ERROR**\n"
            "That pirate is not part of this crew.",
            ephemeral=True
        )
        return

    poster_path = (
        get_poster_path(member.name)
        or get_poster_path(member.display_name)
    )

    if poster_path:
        await interaction.response.send_message(
            content=format_stats(member),
            file=discord.File(poster_path)
        )

    elif os.path.exists(DEFAULT_LOST_POSTER):
        await interaction.response.send_message(
            content=format_stats(member) + "\n⚠️ Poster lost at sea...",
            file=discord.File(DEFAULT_LOST_POSTER)
        )

    else:
        await interaction.response.send_message(
            format_stats(member) +
            "\n⚠️ No bounty poster found."
        )


# ---------- UPDATE POSTER ----------
@tree.command(
    name="update",
    description="Update a pirate's bounty poster"
)
@checks.has_permissions(administrator=True)
@app_commands.describe(
    username="Pirate username",
    picture="The new bounty poster image"
)
async def update_poster(
    interaction: discord.Interaction,
    username: str,
    picture: discord.Attachment
):
    try:
        os.makedirs(POSTER_FOLDER, exist_ok=True)

        extension = picture.filename.split(".")[-1].lower()

        if extension not in ["png", "jpg", "jpeg", "webp"]:
            await interaction.response.send_message(
                "❌ Invalid image format.\n"
                "Use PNG, JPG, JPEG, or WEBP.",
                ephemeral=True
            )
            return

        filename = f"{normalize(username)}.{extension}"
        save_path = os.path.join(POSTER_FOLDER, filename)

        await picture.save(save_path)

        await interaction.response.send_message(
            f"📦 **POSTER UPDATED!**\n"
            f"New bounty poster saved for **{username}**."
        )

    except Exception as e:
        await interaction.response.send_message(
            f"❌ Failed to update poster.\n```{e}```",
            ephemeral=True
        )


# ---------- SET DELIVERY ROUTE ----------
@tree.command(
    name="setdeliveryroute",
    description="Set the episode notification channel"
)
async def set_delivery_route(
    interaction: discord.Interaction,
    channel: discord.TextChannel
):
    global delivery_channel_id

    delivery_channel_id = channel.id

    await interaction.response.send_message(
        f"📦 **DELIVERY ROUTE SET!**\n"
        f"Den Den Mushi will now report to {channel.mention}"
    )


# ---------- SERIES STATUS ----------
@tree.command(
    name="seriesstatus",
    description="View tracked One Piece projects"
)
async def series_status_command(interaction: discord.Interaction):

    message = "📡 **GRAND LINE BROADCAST** 📡\n\n"

    for name, info in series_status.items():

        if info.get("released"):

            if "episode" in info:
                message += (
                    f"✅ **{name}**\n"
                    f"Latest Episode: {info['episode']}\n\n"
                )

            else:
                message += (
                    f"✅ **{name}**\n"
                    f"Currently Released\n\n"
                )

        else:

            if "release_date" in info:
                message += (
                    f"⏳ **{name}**\n"
                    f"Release Date: {info['release_date']}\n\n"
                )

            else:
                message += (
                    f"🚧 **{name}**\n"
                    f"Not released yet.\n\n"
                )

    await interaction.response.send_message(message)


# ---------- EPISODE CHECKER ----------
async def check_episodes():
    await bot.wait_until_ready()

    while not bot.is_closed():

        try:

            if not delivery_channel_id:
                await asyncio.sleep(300)
                continue

            channel = bot.get_channel(delivery_channel_id)

            if not channel:
                await asyncio.sleep(300)
                continue

            for series_name, info in series_status.items():

                if not info.get("released"):
                    continue

                if "episode" not in info:
                    continue

                current_episode = info["episode"]

                previous_episode = last_notified.get(series_name, 0)

                if current_episode > previous_episode:

                    last_notified[series_name] = current_episode

                    await channel.send(
                        f"📦 **DELIVERY FROM THE GRAND LINE!**\n\n"
                        f"📺 **{series_name}**\n"
                        f"Episode **{current_episode}** has arrived!\n\n"
                        f"🏴‍☠️ Prepare the Den Den Mushi!"
                    )

        except Exception:
            print(traceback.format_exc())

        await asyncio.sleep(600)


# ---------- READY ----------
@bot.event
async def on_ready():
    await tree.sync()

    bot.loop.create_task(check_episodes())

    print(f"Den Den Mushi connected as {bot.user}")


# ---------- RUN ----------
bot.run(TOKEN)