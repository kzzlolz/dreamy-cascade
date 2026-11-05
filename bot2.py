import os
import threading
from dotenv import load_dotenv
import discord
from discord import app_commands
from discord.ext import tasks
from flask import Flask, jsonify
from flask_cors import CORS

load_dotenv("/etc/secrets/.env")

app = Flask(__name__)
CORS(app)

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = os.getenv("GUILD_ID")

# Dedicated Channel ID for system status, warnings, and errors
STATUS_CHANNEL_ID = 1563996333990215750

intents = discord.Intents.default()
intents.members = True
intents.presences = True
intents.guilds = True

class MyClient(discord.Client):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        # Sync slash commands with Discord
        if GUILD_ID:
            guild_obj = discord.Object(id=int(GUILD_ID))
            self.tree.copy_global_to(guild=guild_obj)
            await self.tree.sync(guild=guild_obj)
        else:
            await self.tree.sync()
        print("Slash commands synced successfully.")

client = MyClient(intents=intents)

guild_data = {
    "total_members": 0,
    "online_members": 0,
    "members": []
}

data_lock = threading.Lock()


def get_guild():
    if GUILD_ID:
        return client.get_guild(int(GUILD_ID))
    return client.guilds[0] if client.guilds else None


def refresh_member_data(guild):
    members = list(guild.members)
    member_list = []

    online_count = sum(
        1 for member in members
        if not member.bot and member.status != discord.Status.offline
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
        guild_data["total_members"] = guild.member_count or len(members)
        guild_data["online_members"] = online_count
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
            f"Loaded {len(guild_data['members'])} total members "
            f"from {guild.name}"
        )
    except Exception as error:
        print(f"Failed to update members: {error}")
        await send_error(f"Failed to update member chunk: {error}")


# --- Periodic Status Loop (Every 15 Minutes) ---
@tasks.loop(minutes=15)
async def system_status_loop():
    channel = client.get_channel(STATUS_CHANNEL_ID)
    if not channel:
        try:
            channel = await client.fetch_channel(STATUS_CHANNEL_ID)
        except Exception:
            pass

    if channel:
        with data_lock:
            total = guild_data["total_members"]
            online = guild_data["online_members"]

        embed = discord.Embed(
            title="🟢 System Functional",
            description="System is operational and running smoothly!",
            color=0x3ba55d
        )
        embed.add_field(name="Total Members", value=str(total), inline=True)
        embed.add_field(name="Online Members", value=str(online), inline=True)
        embed.set_footer(text="Automated 15-minute health check")
        await channel.send(embed=embed)

@system_status_loop.before_loop
async def before_status_loop():
    await client.wait_until_ready()


# --- Helper Functions for Warnings and Errors ---
async def send_warning(message_text):
    channel = client.get_channel(STATUS_CHANNEL_ID)
    if channel:
        embed = discord.Embed(
            title="⚠️ System Warning",
            description=message_text,
            color=0xfaa61a
        )
        await channel.send(embed=embed)


async def send_error(error_text):
    channel = client.get_channel(STATUS_CHANNEL_ID)
    if channel:
        embed = discord.Embed(
            title="❌ System Error",
            description=error_text,
            color=0xed4245
        )
        await channel.send(embed=embed)


# --- Slash Command: /stats ---
@client.tree.command(name="stats", description="Check the system status and server statistics.")
async def stats(interaction: discord.Interaction):
    with data_lock:
        total = guild_data["total_members"]
        online = guild_data["online_members"]

    embed = discord.Embed(
        title="📊 Kzz's Lounge Stats",
        description="System is fully functional and awake! 🦋",
        color=0xff1a40
    )
    embed.add_field(name="Total Members", value=str(total), inline=True)
    embed.add_field(name="Online Members", value=str(online), inline=True)
    embed.set_footer(text="Requested via /stats command")
    
    await interaction.response.send_message(embed=embed, ephemeral=False)


@client.event
async def on_ready():
    print(f"Logged in as {client.user}[cite: 5]")
    await update_guild_data()
    
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


@app.route("/")
def home():
    return "Kzz's Lounge is active!"[cite: 5]


@app.route("/api/guild-data")
def get_guild_data():
    with data_lock:
        return jsonify({
            "total_members": guild_data["total_members"],
            "online_members": guild_data["online_members"],
            "members": guild_data["members"]
        })


def run_discord():
    if not TOKEN:
        raise RuntimeError("DISCORD_TOKEN is missing.")[cite: 5]

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
