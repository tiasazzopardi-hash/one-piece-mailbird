import discord
from discord.ext import commands
from discord import app_commands
import os
import asyncio
from datetime import datetime, timezone

TOKEN = ""

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

POSTER_FOLDER = "bounty_posters"
DEFAULT_LOST_POSTER = "bounty_posters/lost.png"
DELIVERY_CHANNEL_FILE = "delivery_channel.txt"

last_notified = {
    "sub": 0,
    "dub": 0
}

# ---------- NAME NORMALIZATION ----------
def normalize(text):
    return text.lower().replace(" ", "").strip()


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
    base = username.lower()
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


def format_stats(member: discord.Member):
    role = member.top_role.name
    now = datetime.now(timezone.utc)

    if member.joined_at:
        crew_time = now - member.joined_at
        crew_duration = format_duration(crew_time)
    else:
        crew_duration = "Unknown seas"

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
        await ctx.send("❌ **DEN DEN MUSHI ERROR**\nThat pirate is not part of this crew.")
        return

    poster_path = get_poster_path(member.name) or get_poster_path(member.display_name)

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
        await ctx.send(format_stats(member) + "\n⚠️ No bounty poster found.")


# ---------- SLASH COMMAND ----------
@tree.command(name="stats", description="Check a pirate's bounty")
@app_commands.describe(username="The pirate's username or nickname")
async def slash_stats(interaction: discord.Interaction, username: str):
    member = find_member(interaction.guild, username)

    if not member:
        await interaction.response.send_message(
            "❌ **DEN DEN MUSHI ERROR**\nThat pirate is not part of this crew.",
            ephemeral=True
        )
        return

    poster_path = get_poster_path(member.name) or get_poster_path(member.display_name)

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
            format_stats(member) + "\n⚠️ No bounty poster found."
        )


# ---------- SET DELIVERY ROUTE ----------
@tree.command(name="setdeliveryroute", description="Set the delivery channel for episode alerts")
async def set_delivery_route(interaction: discord.Interaction, channel: discord.TextChannel):
    with open(DELIVERY_CHANNEL_FILE, "w") as f:
        f.write(str(channel.id))

    await interaction.response.send_message(
        f"📦 **DELIVERY ROUTE SET!**\nDen Den Mushi will now report to {channel.mention}"
    )


# ---------- EPISODE CHECKER ----------
async def check_episodes():
    await bot.wait_until_ready()

    while not bot.is_closed():
        try:
            if not os.path.exists(DELIVERY_CHANNEL_FILE):
                await asyncio.sleep(300)
                continue

            with open(DELIVERY_CHANNEL_FILE, "r") as f:
                channel_id = int(f.read().strip())

            channel = bot.get_channel(channel_id)

            if not channel:
                await asyncio.sleep(300)
                continue

            # 🔥 Replace with real data later
            current_sub_ep = 1100
            current_dub_ep = 1080

            if current_sub_ep > last_notified["sub"]:
                last_notified["sub"] = current_sub_ep
                await channel.send(
                    f"📦 **DELIVERY FROM THE GRAND LINE!**\n"
                    f"Den Den Mushi reports a new arrival!\n"
                    f"🏴‍☠️ **One Piece (Sub) Episode {current_sub_ep} is now live!**"
                )

            if current_dub_ep > last_notified["dub"]:
                last_notified["dub"] = current_dub_ep
                await channel.send(
                    f"📦 **DELIVERY FROM THE GRAND LINE!**\n"
                    f"Den Den Mushi reports a voice shipment!\n"
                    f"🎙️ **One Piece (Dub) Episode {current_dub_ep} has arrived!**"
                )

        except Exception as e:
            print("Episode loop error:", e)

        await asyncio.sleep(600)


# ---------- READY ----------
@bot.event
async def on_ready():
    await tree.sync()
    bot.loop.create_task(check_episodes())
    print(f"Den Den Mushi connected as {bot.user}")


bot.run(TOKEN)