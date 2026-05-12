import discord
from discord.ext import commands
from discord import app_commands
import os
import asyncio
from datetime import datetime, timezone
import traceback
import re

# ---------- TOKEN ----------
TOKEN = os.getenv("DISCORD_TOKEN")

# ---------- INTENTS ----------
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# ---------- FILES ----------
POSTER_FOLDER = "bounty_posters"
DEFAULT_LOST_POSTER = "bounty_posters/lost.png"

# ---------- AUTHORIZED USERS ----------
AUTHORIZED_USERS = [
    "king_matti_123",
    "gamerguyy21"
]

# ---------- STORAGE ----------
titles = {}
abilities = {}

# ---------- DELIVERY ----------
delivery_channel_id = None
last_notified = {}

# ---------- TRACKED SERIES ----------
series_status = {
    "One Piece (Sub) - Crunchyroll": {"episode": 1100, "released": True},
    "One Piece (Dub) - Anime Dub": {"episode": 1080, "released": True},
    "One Piece Remake (Sub) - Crunchyroll": {"episode": 0, "released": False},
    "One Piece Remake (Dub) - Anime Dub": {"episode": 0, "released": False},
    "One Piece LEGO - Netflix": {"released": False, "release_date": "September 29th"},
    "One Piece Live Action - Netflix": {"released": True}
}

# ---------- NORMALIZE ----------
def normalize(text):
    text = text.lower().strip()
    text = text.replace(" ", "")
    text = re.sub(r'[^a-z0-9_-]', '', text)
    return text

# ---------- MEMBER FINDER ----------
def find_member(guild, query):
    query = normalize(query)

    for m in guild.members:
        if normalize(m.name) == query or normalize(m.display_name) == query:
            return m

    for m in guild.members:
        if normalize(m.name).startswith(query) or normalize(m.display_name).startswith(query):
            return m

    for m in guild.members:
        if query in normalize(m.name) or query in normalize(m.display_name):
            return m

    return None

# ---------- POSTER ----------
def get_poster_path(username):
    base = normalize(username)
    for ext in ["png", "jpg", "jpeg", "webp"]:
        path = os.path.join(POSTER_FOLDER, f"{base}.{ext}")
        if os.path.exists(path):
            return path
    return None

# ---------- TIME ----------
def format_duration(delta):
    days = delta.days
    return f"{days//365}y {(days%365)//30}m {days%30}d"

# ---------- STATS ----------
def format_stats(member, title="Unknown", ability="None"):
    role = member.top_role.name
    now = datetime.now(timezone.utc)

    crew = "Unknown Seas"
    if member.joined_at:
        crew = format_duration(now - member.joined_at)

    pirate = format_duration(now - member.created_at)

    return f"""
🏴‍☠️ **Pirate: {member.display_name}**
🎖️ **Title:** {title}
🎭 **Role:** {role}
⚔️ **Ability:** {ability}
⚓ **Time in Crew:** {crew}
🌊 **Time as Pirate:** {pirate}
"""

# =========================================================
# STATS COMMAND
# =========================================================
@bot.command()
async def stats(ctx, *, username):
    member = find_member(ctx.guild, username)

    if not member:
        await ctx.send("❌ Pirate not found.")
        return

    poster = get_poster_path(member.name) or get_poster_path(member.display_name)

    await ctx.send(
        content=format_stats(
            member,
            titles.get(member.name, "Unknown"),
            abilities.get(member.name, "None")
        ),
        file=discord.File(poster) if poster else None
    )

@tree.command(name="stats", description="Check pirate stats")
async def slash_stats(interaction, username: str):
    member = find_member(interaction.guild, username)

    if not member:
        await interaction.response.send_message("❌ Pirate not found.", ephemeral=True)
        return

    poster = get_poster_path(member.name) or get_poster_path(member.display_name)

    await interaction.response.send_message(
        content=format_stats(
            member,
            titles.get(member.name, "Unknown"),
            abilities.get(member.name, "None")
        ),
        file=discord.File(poster) if poster else None
    )

# =========================================================
# POSTER COMMAND (RENAMED)
# =========================================================
@tree.command(name="poster", description="Update bounty poster")
async def poster(interaction, username: str, picture: discord.Attachment):

    if interaction.user.name.lower() not in AUTHORIZED_USERS:
        await interaction.response.send_message("❌ Not allowed.", ephemeral=True)
        return

    os.makedirs(POSTER_FOLDER, exist_ok=True)

    ext = picture.filename.split(".")[-1].lower()

    if ext not in ["png", "jpg", "jpeg", "webp"]:
        await interaction.response.send_message("❌ Invalid format.", ephemeral=True)
        return

    path = os.path.join(POSTER_FOLDER, f"{normalize(username)}.{ext}")
    await picture.save(path)

    await interaction.response.send_message("📦 Poster updated.")

# =========================================================
# TITLE COMMAND
# =========================================================
@tree.command(name="settitle", description="Set pirate title")
async def set_title(interaction, username: str, title: str):

    if interaction.user.name.lower() not in AUTHORIZED_USERS:
        await interaction.response.send_message("❌ Not allowed.", ephemeral=True)
        return

    member = find_member(interaction.guild, username)
    if not member:
        await interaction.response.send_message("❌ Not found.", ephemeral=True)
        return

    titles[member.name] = title

    await interaction.response.send_message(
        f"🎖️ Title set: {title}"
    )

# =========================================================
# ABILITY COMMAND
# =========================================================
@tree.command(name="setability", description="Set pirate ability")
async def set_ability(interaction, username: str, ability: str):

    if interaction.user.name.lower() not in AUTHORIZED_USERS:
        await interaction.response.send_message("❌ Not allowed.", ephemeral=True)
        return

    member = find_member(interaction.guild, username)
    if not member:
        await interaction.response.send_message("❌ Not found.", ephemeral=True)
        return

    abilities[member.name] = ability

    await interaction.response.send_message(
        f"⚔️ Ability set: {ability}"
    )

# =========================================================
# DELIVERY ROUTE
# =========================================================
@tree.command(name="setdeliveryroute", description="Set episode channel")
async def set_route(interaction, channel: discord.TextChannel):

    if interaction.user.name.lower() not in AUTHORIZED_USERS:
        await interaction.response.send_message("❌ Not allowed.", ephemeral=True)
        return

    global delivery_channel_id
    delivery_channel_id = channel.id

    await interaction.response.send_message(
        f"📡 Route set to {channel.mention}"
    )

# =========================================================
# READY
# =========================================================
@bot.event
async def on_ready():
    await tree.sync()
    print(f"Logged in as {bot.user}")

bot.run(TOKEN)