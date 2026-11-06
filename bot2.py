
import os
import threading
import time
from datetime import datetime, timezone

from dotenv import load_dotenv
import discord
from discord import app_commands
from discord.ext import tasks
from flask import Flask, jsonify
from flask_cors import CORS

# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

load_dotenv("/etc/secrets/.env")

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = os.getenv("GUILD_ID")

STATUS_CHANNEL_ID = 1563996333990215750

STARTED_AT = time.monotonic()

app = Flask(__name__)
CORS(app)

# --------------------------------------------------
# DISCORD CLIENT
# --------------------------------------------------

intents = discord.Intents.default()
intents.members = True
intents.presences = True
intents.guilds = True


class MyClient(discord.Client):
    def __init__(self, *, intents):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        if GUILD_ID:
            guild_obj = discord.Object(id=int(GUILD_ID))
            self.tree.copy_global_to(guild=guild_obj)
            await self.tree.sync(guild=guild_obj)
        else:
            await self.tree.sync()

        print("Slash commands synced successfully.")


client = MyClient(intents=intents)

# --------------------------------------------------
# GUILD DATA
# --------------------------------------------------

guild_data = {
    "total_members": 0,
    "online_members": 0,
    "bot_count": 0,
    "members": []
}

data_lock = threading.Lock()

# The single status message maintained by Kzz.
status_message = None


def get_guild():
    if GUILD_ID:
        return client.get_guild(int(GUILD_ID))

    return client.guilds[0] if client.guilds else None


def refresh_member_data(guild):
    members = list(guild.members)
    member_list = []

    online_count = sum(
        1 for member in members
        if not member.bot
        and member.status != discord.Status.offline
    )

    bot_count = sum(
        1 for member in members
        if member.bot
    )

    for member in members:
        member_list.append({
            "id": str(member.id),
            "username": member.name,
            "display_name": member.display_name,
            "avatar_url": str(member.display_avatar.url),
            "status": str(member.status),
            "bot": member.bot,
            "roles": [
                str(role.id)
                for role in member.roles
                if role != guild.default_role
            ]
        })

    with data_lock:
        guild_data["total_members"] = (
            guild.member_count or len(members)
        )
        guild_data["online_members"] = online_count
        guild_data["bot_count"] = bot_count
        guild_data["members"] = member_list


async def update_guild_data():
    guild = get_guild()

    if guild is None:
        print("ERROR: Could not find the configured Discord server.")
        return

    try:
        await guild.chunk(cache=True)
        refresh_member_data(guild)

        print(
            f"Loaded {len(guild_data['members'])} members "
            f"from {guild.name}"
        )

    except Exception as error:
        print(f"Failed to update members: {error}")
        await send_error(
            f"Failed to update member data: {error}"
        )


# --------------------------------------------------
# RUNTIME FORMATTER
# --------------------------------------------------

def get_runtime():
    seconds = int(time.monotonic() - STARTED_AT)

    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)

    return (
        f"{days}d {hours}h {minutes}m {seconds}s"
    )


# --------------------------------------------------
# STATUS EMBED
# --------------------------------------------------

async def get_status_channel():
    channel = client.get_channel(STATUS_CHANNEL_ID)

    if channel is None:
        try:
            channel = await client.fetch_channel(
                STATUS_CHANNEL_ID
            )
        except discord.HTTPException as error:
            print(f"Could not access status channel: {error}")

    return channel


def build_status_embed():
    embed = discord.Embed(
        title="🟢 Systems Functional",
        description="All systems online!",
        color=0x3BA55D,
        timestamp=datetime.now(timezone.utc)
    )

    embed.add_field(
        name="Runtime",
        value=f"`{get_runtime()}`",
        inline=True
    )

    embed.set_footer(
        text="Kzz's Lounge • Automated 15-minute health check"
    )

    return embed


async def update_status_message():
    global status_message

    channel = await get_status_channel()

    if channel is None:
        print("WARNING: Status channel unavailable.")
        return

    embed = build_status_embed()

    try:
        if status_message is None:
            status_message = await channel.send(embed=embed)
            print("Status embed sent successfully.")

        else:
            await status_message.edit(embed=embed)
            print("Status embed updated.")

    except discord.NotFound:
        # Previous status message was deleted.
        status_message = await channel.send(embed=embed)
        print("Previous status message missing. Created a new one.")

    except discord.HTTPException as error:
        print(f"Failed to update status embed: {error}")


@tasks.loop(minutes=15)
async def system_status_loop():
    await update_status_message()


@system_status_loop.before_loop
async def before_status_loop():
    await client.wait_until_ready()


# --------------------------------------------------
# WARNING AND ERROR REPORTING
# --------------------------------------------------

async def send_warning(message_text):
    channel = await get_status_channel()

    if channel:
        embed = discord.Embed(
            title="⚠️ System Warning",
            description=message_text,
            color=0xFAA61A
        )

        await channel.send(embed=embed)


async def send_error(error_text):
    channel = await get_status_channel()

    if channel:
        embed = discord.Embed(
            title="❌ System Error",
            description=error_text,
            color=0xED4245
        )

        await channel.send(embed=embed)


# --------------------------------------------------
# /STATS COMMAND
# --------------------------------------------------

@client.tree.command(
    name="stats",
    description="Check system status and server statistics."
)
async def stats(interaction: discord.Interaction):

    with data_lock:
        total = guild_data["total_members"]
        online = guild_data["online_members"]
        bots = guild_data["bot_count"]

    embed = discord.Embed(
        title="📊 Kzz's Lounge Stats",
        description="System is fully functional and awake! 🦋",
        color=0xFF1A40
    )

    embed.add_field(
        name="👥 Total Members",
        value=f"`{total}`",
        inline=True
    )

    embed.add_field(
        name="🟢 Online Humans",
        value=f"`{online}`",
        inline=True
    )

    embed.add_field(
        name="🤖 Bots",
        value=f"`{bots}`",
        inline=True
    )

    embed.set_footer(
        text="Requested via /stats"
    )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=False
    )


# --------------------------------------------------
# DISCORD EVENTS
# --------------------------------------------------

@client.event
async def on_ready():
    print(f"Logged in as {client.user}")

    await update_guild_data()

    # Send the startup embed or refresh the existing one
    # if Discord reconnects.
    await update_status_message()

    if not system_status_loop.is_running():
        system_status_loop.start()


@client.event
async def on_member_join(member):
    guild = get_guild()

    if guild and member.guild.id == guild.id:
        refresh_member_data(guild)


@client.event
async def on_member_remove(member):
    guild = get_guild()

    if guild and member.guild.id == guild.id:
        refresh_member_data(guild)


@client.event
async def on_member_update(before, after):
    guild = get_guild()

    if guild and after.guild.id == guild.id:
        refresh_member_data(guild)


@client.event
async def on_presence_update(before, after):
    guild = get_guild()

    if guild and after.guild.id == guild.id:
        refresh_member_data(guild)


# --------------------------------------------------
# FLASK API
# --------------------------------------------------

@app.route("/")
def home():
    return "Kzz's Lounge is active!"


@app.route("/api/guild-data")
def get_guild_data():
    with data_lock:
        return jsonify({
            "total_members": guild_data["total_members"],
            "online_members": guild_data["online_members"],
            "bot_count": guild_data["bot_count"],
            "members": guild_data["members"]
        })


# --------------------------------------------------
# STARTUP
# --------------------------------------------------

def run_discord():
    if not TOKEN:
        raise RuntimeError("DISCORD_TOKEN is missing.")

    client.run(TOKEN)


if __name__ == "__main__":
    discord_thread = threading.Thread(
        target=run_discord,
        daemon=True
    )

    discord_thread.start()

    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        use_reloader=False
    )
