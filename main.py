import discord
from discord.ext import commands
from discord import app_commands
import os
from datetime import datetime, timezone
import re
import json
import random

# =========================================================
# CONFIG
# =========================================================
TOKEN = os.getenv("DISCORD_TOKEN")

POSTER_FOLDER = "bounty_posters"
DATA_FOLDER   = "data"
DATA_PATH     = "data/pirate_data.json"

OWNER            = "king_matti_123"
AUTHORIZED_USERS = {OWNER, "gamerguyy21", "meownugs1"}

SLEEP_MODE          = False
delivery_channel_id = None

# =========================================================
# INTENTS / BOT
# =========================================================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot  = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# =========================================================
# STORAGE
# =========================================================
titles:    dict[str, str] = {}
abilities: dict[str, str] = {}
weapons:   dict[str, str] = {}

# =========================================================
# SERIES DATA
# =========================================================
series_status = {
    "One Piece (Sub) - Crunchyroll":        {"episode": 1100, "released": True},
    "One Piece (Dub) - Anime Dub":          {"episode": 1080, "released": True},
    "One Piece Remake (Sub) - Crunchyroll": {"episode": 0,    "released": False},
    "One Piece Remake (Dub) - Anime Dub":   {"episode": 0,    "released": False},
    "One Piece LEGO - Netflix":             {"released": False, "release_date": "September 29th"},
    "One Piece Live Action - Netflix":      {"released": True},
}

# =========================================================
# RANDOMISED RESPONSES
# =========================================================
REPLIES = {
    "bounty_found": [
        "📜 Bounty poster retrieved from Marine HQ… bweh heh heh.",
        "🐌 *Den Den Mushi crackles* — pirate file incoming, Vice Captain.",
        "🏴‍☠️ Got 'em on record. Here's what the Marines know…",
        "📡 Signal locked. Transmitting pirate data now — bweh!",
        "🔍 Dossier pulled from the Grand Line archives. Don't lose it.",
    ],
    "ep_set": [
        "📡 Route updated. The Den Den Mushi knows the way — bweh!",
        "🐌 Delivery channel locked in. No snail gets left behind.",
        "⚓ New port registered. Episodes will dock there from now on.",
        "📻 Frequency tuned. Ready to transmit whenever the seas call.",
    ],
    "poster_updated": [
        "📦 New wanted poster pinned to the mast — bweh heh heh.",
        "🖼️ The Marines updated their files. This pirate looks dangerous.",
        "📌 Poster swapped. The bounty board has been refreshed.",
        "🐌 *crackle* Image received and stored in the Marine database.",
    ],
    "field_set": [
        "✅ The record has been updated. The Grand Line never forgets — bweh.",
        "📝 Logged. One more legend written into the pirate annals.",
        "🐌 *bweh* Entry confirmed. The Den Den Mushi never lies.",
        "⚓ Done. The seas will know of this change.",
    ],
    "field_reset": [
        "🧹 Wiped clean. Like they never sailed a day — bweh.",
        "📋 Entry cleared from the record books.",
        "🐌 *click* Gone. The Marines have no memory of it either.",
        "🌊 Reset. Those seas are quiet now.",
    ],
    "not_found": [
        "❌ No such pirate in our records. Sure they sailed these seas?",
        "🔭 Scanned every island — no match found — bweh.",
        "🐌 *static* …Name unknown to the Den Den Mushi network.",
        "🗺️ Checked the Grand Line charts. Nothing. Try another name.",
        "❓ The Marines have no bounty on that name. Double-check the spelling.",
    ],
    "not_allowed": [
        "🚫 You're not on the crew manifest. Back off — bweh.",
        "⚓ Nice try, rookie. Only officers can do that.",
        "🐌 *bweh bweh* Clearance denied. The Den Den Mushi won't budge.",
        "🔒 This log is above your rank, pirate.",
    ],
    "bad_format": [
        "❌ That file type won't sail on this ship. PNG, JPG, JPEG or WEBP only.",
        "🐌 *bweh?* The Den Den Mushi can't digest that format.",
        "🗺️ Wrong chart format. Stick to PNG, JPG, JPEG or WEBP.",
    ],
    "sleeping": [
        "🌊 The seas are quiet. The Den Den Mushi is resting…",
        "🐌 *…silence…* No signal at this time.",
        "⚓ The ship is anchored. Try again when the tide returns.",
        "📻 *static* …Transmission unavailable. Stand by.",
        "🌙 The Den Den Mushi has gone dark. Nothing to report.",
    ],
}

def r(key: str) -> str:
    return random.choice(REPLIES[key])

# =========================================================
# PERSISTENCE
# =========================================================
def save_data() -> None:
    os.makedirs(DATA_FOLDER, exist_ok=True)
    with open(DATA_PATH, "w") as f:
        json.dump({"titles": titles, "abilities": abilities, "weapons": weapons}, f, indent=4)

def load_data() -> None:
    global titles, abilities, weapons
    os.makedirs(DATA_FOLDER, exist_ok=True)
    if not os.path.exists(DATA_PATH):
        save_data()
        return
    with open(DATA_PATH) as f:
        data = json.load(f)
    titles    = data.get("titles",    {})
    abilities = data.get("abilities", {})
    weapons   = data.get("weapons",   {})

# =========================================================
# HELPERS
# =========================================================
def normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9_-]", "", text.lower().strip().replace(" ", ""))

def find_member(guild: discord.Guild, query: str) -> discord.Member | None:
    q = normalize(query)
    for check in (
        lambda n: n == q,
        lambda n: n.startswith(q),
        lambda n: q in n,
    ):
        for m in guild.members:
            if check(normalize(m.name)) or check(normalize(m.display_name)):
                return m
    return None

def get_poster_path(username: str) -> str | None:
    base = normalize(username)
    for ext in ("png", "jpg", "jpeg", "webp"):
        path = os.path.join(POSTER_FOLDER, f"{base}.{ext}")
        if os.path.exists(path):
            return path
    return None

def format_duration(delta) -> str:
    days = delta.days
    y, rem = divmod(days, 365)
    m, d   = divmod(rem, 30)
    return f"{y}y {m}m {d}d"

def format_stats(member: discord.Member) -> str:
    now  = datetime.now(timezone.utc)
    crew = format_duration(now - member.joined_at) if member.joined_at else "Unknown Seas"
    return (
        f"🏴‍☠️ **Pirate:** {member.display_name}\n"
        f"🎖️ **Title:** {titles.get(member.name, 'Unknown')}\n"
        f"🎭 **Role:** {member.top_role.name}\n"
        f"🌀 **Abilities:** {abilities.get(member.name, 'None')}\n"
        f"🗡️ **Weapons:** {weapons.get(member.name, 'None')}\n"
        f"⚓ **Time in Crew:** {crew}\n"
        f"🌊 **Time as Pirate:** {format_duration(now - member.created_at)}\n"
    )

def poster_file(member: discord.Member) -> discord.File | None:
    path = get_poster_path(member.name) or get_poster_path(member.display_name)
    return discord.File(path) if path else None

def is_authorized(user: discord.User | discord.Member) -> bool:
    return user.name.lower() in AUTHORIZED_USERS

# =========================================================
# AUTOCOMPLETE — username
# Suggests all guild members filtered by what the user types
# =========================================================
async def username_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> list[app_commands.Choice[str]]:
    if not interaction.guild:
        return []
    q = current.lower()
    choices = []
    for m in interaction.guild.members:
        name = m.display_name
        if q in name.lower() or q in m.name.lower():
            choices.append(app_commands.Choice(name=name, value=m.name))
        if len(choices) >= 25:
            break
    return choices

# =========================================================
# AUTOCOMPLETE — field values (title / ability / weapon)
# Pre-fills whatever is currently stored for that pirate
# =========================================================
async def _field_autocomplete(
    interaction: discord.Interaction,
    current: str,
    store: dict,
    fallback: str,
) -> list[app_commands.Choice[str]]:
    username = interaction.namespace.username or ""
    member   = find_member(interaction.guild, username) if interaction.guild else None
    existing = store.get(member.name, fallback) if member else ""

    choices: list[app_commands.Choice[str]] = []

    # Always show the currently stored value first (so it acts as a pre-fill)
    if existing and existing != fallback:
        choices.append(app_commands.Choice(name=f"Current: {existing}", value=existing))

    # If the admin is typing something that differs, show it as an option too
    if current and current != existing:
        choices.append(app_commands.Choice(name=current, value=current))

    return choices[:25]

async def title_autocomplete(i: discord.Interaction, current: str):
    return await _field_autocomplete(i, current, titles, "Unknown")

async def ability_autocomplete(i: discord.Interaction, current: str):
    return await _field_autocomplete(i, current, abilities, "None")

async def weapon_autocomplete(i: discord.Interaction, current: str):
    return await _field_autocomplete(i, current, weapons, "None")

# =========================================================
# !nuke / !restore
# Must be registered BEFORE any global check so they are
# never blocked — they bypass everything via on_message.
# =========================================================
@bot.command()
async def nuke(ctx):
    global SLEEP_MODE
    # Only owner, only in DMs
    if not isinstance(ctx.channel, discord.DMChannel):
        return
    if ctx.author.name.lower() != OWNER:
        return
    if SLEEP_MODE:
        await ctx.send("☠️ Already in sleep mode.")
        return
    SLEEP_MODE = True
    await bot.change_presence(
        status=discord.Status.idle,
        activity=discord.Game(name="…")
    )
    await ctx.send(
        "☠️ **Sleep mode activated.**\n"
        "Everyone gets a quiet Den Den Mushi brush-off.\n"
        "DM me `!restore` to bring it back."
    )

@bot.command()
async def restore(ctx):
    global SLEEP_MODE
    if not isinstance(ctx.channel, discord.DMChannel):
        return
    if ctx.author.name.lower() != OWNER:
        return
    if not SLEEP_MODE:
        await ctx.send("📡 Already online.")
        return
    SLEEP_MODE = False
    await bot.change_presence(status=discord.Status.online, activity=None)
    await ctx.send("📡 **Systems restored.** The Den Den Mushi is back online — bweh!")

# =========================================================
# MESSAGE GATE
# Runs before any command processing.
# Owner DMs always go through (for nuke/restore).
# Everyone else is blocked silently during sleep.
# =========================================================
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    is_owner_dm = (
        isinstance(message.channel, discord.DMChannel)
        and message.author.name.lower() == OWNER
    )

    if is_owner_dm:
        # Owner DMs bypass everything — nuke/restore must always work
        await bot.process_commands(message)
        return

    if SLEEP_MODE:
        # Silently ignore — no response at all to non-commands,
        # sleeping reply handled by the bot.check below for actual commands
        return

    await bot.process_commands(message)

# =========================================================
# GLOBAL CHECK (prefix commands)
# Only reached if on_message already let it through,
# so SLEEP_MODE here only fires for owner (who gets a pass).
# =========================================================
@bot.check
async def prefix_sleep_check(ctx):
    # nuke / restore bypass the check entirely
    if ctx.command and ctx.command.name in ("nuke", "restore"):
        return True
    if ctx.author.name.lower() == OWNER:
        return True
    if SLEEP_MODE:
        await ctx.send(r("sleeping"))
        return False
    return True

# =========================================================
# GLOBAL CHECK (slash commands)
# =========================================================
@tree.interaction_check
async def slash_sleep_check(interaction: discord.Interaction):
    if interaction.user.name.lower() == OWNER:
        return True
    if SLEEP_MODE:
        await interaction.response.send_message(r("sleeping"), ephemeral=True)
        return False
    return True

# =========================================================
# GENERIC ADMIN SETTER / RESETTER
# =========================================================
async def _admin_set(
    interaction: discord.Interaction,
    username: str,
    value: str,
    store: dict,
    label: str,
    emoji: str,
):
    if not is_authorized(interaction.user):
        await interaction.response.send_message(r("not_allowed"), ephemeral=True)
        return
    member = find_member(interaction.guild, username)
    if not member:
        await interaction.response.send_message(r("not_found"), ephemeral=True)
        return
    store[member.name] = value
    save_data()
    await interaction.response.send_message(
        f"{emoji} {r('field_set')} — **{label}** updated for **{member.display_name}**."
    )

async def _admin_reset(
    interaction: discord.Interaction,
    username: str,
    store: dict,
    label: str,
    default: str,
):
    if not is_authorized(interaction.user):
        await interaction.response.send_message(r("not_allowed"), ephemeral=True)
        return
    member = find_member(interaction.guild, username)
    if not member:
        await interaction.response.send_message(r("not_found"), ephemeral=True)
        return
    store[member.name] = default
    save_data()
    await interaction.response.send_message(
        f"{r('field_reset')} — **{label}** cleared for **{member.display_name}**."
    )

# =========================================================
# STATS
# =========================================================
@bot.command()
async def stats(ctx, *, username):
    member = find_member(ctx.guild, username)
    if not member:
        await ctx.send(r("not_found"))
        return
    await ctx.send(
        content=f"{r('bounty_found')}\n\n{format_stats(member)}",
        file=poster_file(member)
    )

@tree.command(name="stats", description="Check pirate stats")
@app_commands.autocomplete(username=username_autocomplete)
async def slash_stats(interaction: discord.Interaction, username: str):
    member = find_member(interaction.guild, username)
    if not member:
        await interaction.response.send_message(r("not_found"), ephemeral=True)
        return
    await interaction.response.send_message(
        content=f"{r('bounty_found')}\n\n{format_stats(member)}",
        file=poster_file(member)
    )

# =========================================================
# POSTER
# =========================================================
@tree.command(name="poster", description="Update bounty poster")
@app_commands.autocomplete(username=username_autocomplete)
async def slash_poster(
    interaction: discord.Interaction,
    username: str,
    picture: discord.Attachment,
):
    if not is_authorized(interaction.user):
        await interaction.response.send_message(r("not_allowed"), ephemeral=True)
        return
    ext = picture.filename.rsplit(".", 1)[-1].lower()
    if ext not in ("png", "jpg", "jpeg", "webp"):
        await interaction.response.send_message(r("bad_format"), ephemeral=True)
        return
    os.makedirs(POSTER_FOLDER, exist_ok=True)
    await picture.save(os.path.join(POSTER_FOLDER, f"{normalize(username)}.{ext}"))
    await interaction.response.send_message(r("poster_updated"))

# =========================================================
# TITLE
# =========================================================
@tree.command(name="settitle", description="Set pirate title")
@app_commands.autocomplete(username=username_autocomplete, title=title_autocomplete)
async def set_title(interaction: discord.Interaction, username: str, title: str):
    await _admin_set(interaction, username, title, titles, "Title", "🎖️")

@tree.command(name="resettitle", description="Reset pirate title")
@app_commands.autocomplete(username=username_autocomplete)
async def reset_title(interaction: discord.Interaction, username: str):
    await _admin_reset(interaction, username, titles, "Title", "Unknown")

# =========================================================
# ABILITY
# =========================================================
@tree.command(name="setability", description="Set pirate abilities")
@app_commands.autocomplete(username=username_autocomplete, ability=ability_autocomplete)
async def set_ability(interaction: discord.Interaction, username: str, ability: str):
    await _admin_set(interaction, username, ability, abilities, "Abilities", "🌀")

@tree.command(name="resetability", description="Reset pirate abilities")
@app_commands.autocomplete(username=username_autocomplete)
async def reset_ability(interaction: discord.Interaction, username: str):
    await _admin_reset(interaction, username, abilities, "Abilities", "None")

# =========================================================
# WEAPON
# =========================================================
@tree.command(name="setweapon", description="Set pirate weapon")
@app_commands.autocomplete(username=username_autocomplete, weapon=weapon_autocomplete)
async def set_weapon(interaction: discord.Interaction, username: str, weapon: str):
    await _admin_set(interaction, username, weapon, weapons, "Weapon", "🗡️")

@tree.command(name="resetweapon", description="Reset pirate weapon")
@app_commands.autocomplete(username=username_autocomplete)
async def reset_weapon(interaction: discord.Interaction, username: str):
    await _admin_reset(interaction, username, weapons, "Weapon", "None")

# =========================================================
# DELIVERY ROUTE
# =========================================================
@tree.command(name="setdeliveryroute", description="Set episode delivery channel")
async def set_route(interaction: discord.Interaction, channel: discord.TextChannel):
    if not is_authorized(interaction.user):
        await interaction.response.send_message(r("not_allowed"), ephemeral=True)
        return
    global delivery_channel_id
    delivery_channel_id = channel.id
    await interaction.response.send_message(
        f"{r('ep_set')} — Now routing to {channel.mention}"
    )

# =========================================================
# READY
# =========================================================
@bot.event
async def on_ready():
    load_data()
    await tree.sync()
    print(f"Den Den Mushi connected as {bot.user} — bweh!")

# =========================================================
# RUN
# =========================================================
bot.run(TOKEN)