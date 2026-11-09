import re
import os
import json
import base64
import urllib.error
import threading
import time
from datetime import datetime, timezone

import platform
import subprocess
import urllib.request
from dotenv import load_dotenv
import discord
from discord import app_commands
from discord.ext import tasks
from flask import Flask, jsonify
from flask_cors import CORS
from admin_panel import register_admin_routes

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

load_dotenv(BASE_DIR / ".env", override=True)

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = os.getenv("GUILD_ID")

STATUS_CHANNEL_ID = 1563996333990215750

STARTED_AT = time.monotonic()

app = Flask(__name__)
CORS(app)

# Private owner dashboard and profile-management API.
register_admin_routes(app)

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


def record_community_event(event_type, member, details=""):
    """Store a minimal community event; never stores message content."""
    path = os.environ.get("PROFILE_DB_PATH") or str(
        BASE_DIR / "dreamy-cascade-profiles.sqlite3"
    )
    now = datetime.now(timezone.utc).isoformat()
    display_name = getattr(member, "display_name", None) or getattr(member, "name", "A member")
    try:
        import sqlite3
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with sqlite3.connect(path, timeout=15) as connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS activity_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    member_id TEXT NOT NULL DEFAULT '',
                    display_name TEXT NOT NULL DEFAULT '',
                    details TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL
                )"""
            )
            connection.execute(
                "INSERT INTO activity_events (event_type, member_id, display_name, details, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (event_type, str(getattr(member, "id", "")), display_name[:100], details[:200], now),
            )
            if event_type in ("join", "milestone"):
                connection.execute(
                    """CREATE TABLE IF NOT EXISTS announcements (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT NOT NULL,
                        body TEXT NOT NULL,
                        created_by TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    )"""
                )
                title = "A new face joined Dreamy Cascade!" if event_type == "join" else "Community milestone reached!"
                body = f"{display_name} joined the community. Welcome them!" if event_type == "join" else details
                connection.execute(
                    "INSERT INTO announcements (title, body, created_by, created_at) VALUES (?, ?, ?, ?)",
                    (title, body, "system", now),
                )
                connection.execute("DELETE FROM announcements WHERE id NOT IN (SELECT id FROM announcements ORDER BY id DESC LIMIT 100)")
            connection.commit()
    except Exception as error:
        print(f"Could not record community event: {error}")


def record_guild_snapshot(guild):
    path = os.environ.get("PROFILE_DB_PATH") or str(
        BASE_DIR / "dreamy-cascade-profiles.sqlite3"
    )
    try:
        import sqlite3
        members = list(guild.members)
        total = sum(1 for member in members if not member.bot)
        online = sum(1 for member in members if not member.bot and member.status != discord.Status.offline)
        bots = sum(1 for member in members if member.bot)
        now = datetime.now(timezone.utc).isoformat()
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with sqlite3.connect(path, timeout=15) as connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS guild_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    total_members INTEGER NOT NULL,
                    online_members INTEGER NOT NULL,
                    bot_count INTEGER NOT NULL,
                    recorded_at TEXT NOT NULL
                )"""
            )
            connection.execute(
                "INSERT INTO guild_snapshots (total_members, online_members, bot_count, recorded_at) VALUES (?, ?, ?, ?)",
                (total, online, bots, now),
            )
            connection.execute(
                "DELETE FROM guild_snapshots WHERE id NOT IN (SELECT id FROM guild_snapshots ORDER BY id DESC LIMIT 2016)"
            )
            connection.commit()
    except Exception as error:
        print(f"Could not record guild analytics: {error}")


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
            # Include each assigned role's live hierarchy position so the
            # website can place each person under their highest listed role.
            "roles": [
                {
                    "id": str(role.id),
                    "name": role.name,
                    "position": role.position
                }
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
    checked_at = datetime.now(timezone.utc)

    embed = discord.Embed(
        title="🟢 Kzz | System Status",
        description="All services are running normally.",
        color=0x8B7BFF,
        timestamp=checked_at
    )

    embed.add_field(
        name="Status",
        value="`OPERATIONAL`",
        inline=True
    )

    embed.add_field(
        name="Uptime",
        value=f"`{get_runtime()}`",
        inline=True
    )

    embed.add_field(
        name="Last checked",
        value=f"<t:{int(checked_at.timestamp())}:R>",
        inline=False
    )

    embed.set_footer(
        text="Dreamy Cascade • Kzz Health Monitor • Every 15 minutes"
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


@tasks.loop(seconds=5)
async def cached_guild_refresh_loop():
    guild = get_guild()
    if guild is not None:
        # Read the gateway-maintained cache; do not request a fresh chunk every 5 seconds.
        refresh_member_data(guild)


@cached_guild_refresh_loop.before_loop
async def before_cached_guild_refresh():
    await client.wait_until_ready()


@tasks.loop(minutes=15)
async def system_status_loop():
    guild = get_guild()
    if guild is not None:
        record_guild_snapshot(guild)
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
        title="📊 Dreamy Cascade Stats",
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
    if not cached_guild_refresh_loop.is_running():
        cached_guild_refresh_loop.start()


@client.event
async def on_member_join(member):
    guild = get_guild()

    if guild and member.guild.id == guild.id:
        refresh_member_data(guild)
        if not member.bot:
            record_community_event("join", member)
            human_count = sum(1 for item in guild.members if not item.bot)
            if human_count in (100, 250, 500, 750, 1000, 1500, 2000, 3000, 5000):
                path = os.environ.get("PROFILE_DB_PATH") or str(BASE_DIR / "dreamy-cascade-profiles.sqlite3")
                import sqlite3
                with sqlite3.connect(path, timeout=15) as connection:
                    connection.execute("CREATE TABLE IF NOT EXISTS announced_milestones (milestone INTEGER PRIMARY KEY, announced_at TEXT NOT NULL)")
                    inserted = connection.execute(
                        "INSERT OR IGNORE INTO announced_milestones (milestone, announced_at) VALUES (?, ?)",
                        (human_count, datetime.now(timezone.utc).isoformat())
                    ).rowcount
                    connection.commit()
                if inserted:
                    record_community_event("milestone", member, f"We've reached {human_count:,} members! Thank you for being part of Dreamy Cascade ♡")


@client.event
async def on_member_remove(member):
    guild = get_guild()

    if guild and member.guild.id == guild.id:
        refresh_member_data(guild)
        if not member.bot:
            record_community_event("leave", member, "A member left the community.")


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
    return "Dreamy Cascade is active!"


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

def publish_api_config(public_url):
    """Publish the current Quick Tunnel URL for the GitHub Pages website."""
    token = os.getenv("GITHUB_TOKEN")
    repository = os.getenv("GITHUB_REPOSITORY", "kzzlolz/dreamy-cascade")
    branch = os.getenv("GITHUB_BRANCH", "main")
    config_path = "api-config.json"

    if not token:
        print(
            "WARNING: GITHUB_TOKEN is not configured; "
            "the website API URL will not update automatically."
        )
        return False

    api_url = f"https://api.github.com/repos/{repository}/contents/{config_path}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "Dreamy-Cascade-Kzz",
    }

    try:
        existing_sha = None
        request = urllib.request.Request(
            f"{api_url}?ref={branch}",
            headers=headers,
            method="GET",
        )

        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                existing = json.loads(response.read().decode("utf-8"))
                existing_sha = existing.get("sha")
        except urllib.error.HTTPError as error:
            if error.code != 404:
                raise

        config = json.dumps(
            {"apiBaseUrl": public_url},
            indent=2,
        )

        payload = {
            "message": "Update Dreamy Cascade API tunnel URL",
            "content": base64.b64encode(
                config.encode("utf-8")
            ).decode("ascii"),
            "branch": branch,
        }

        if existing_sha:
            payload["sha"] = existing_sha

        update_request = urllib.request.Request(
            api_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                **headers,
                "Content-Type": "application/json",
            },
            method="PUT",
        )

        with urllib.request.urlopen(update_request, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))

        print(
            "Website API URL published to GitHub successfully. "
            f"Commit: {result.get('commit', {}).get('sha', 'created')}"
        )
        return True

    except Exception as error:
        print(f"ERROR: Could not publish website API URL: {error}")
        return False


def run_discord():
    if not TOKEN:
        raise RuntimeError("DISCORD_TOKEN is missing.")

    client.run(TOKEN)




if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))

    # Start Discord bot
    discord_thread = threading.Thread(
        target=run_discord,
        daemon=True
    )
    discord_thread.start()

    # Download Cloudflare Tunnel if needed
    cloudflared_path = BASE_DIR / "cloudflared"

    if not cloudflared_path.exists():
        print("Downloading Cloudflare Tunnel...")

        architecture = platform.machine().lower()

        if architecture in ("x86_64", "amd64"):
            binary_name = "cloudflared-linux-amd64"
        elif architecture in ("aarch64", "arm64"):
            binary_name = "cloudflared-linux-arm64"
        else:
            raise RuntimeError(
                f"Unsupported architecture: {architecture}"
            )

        download_url = (
            "https://github.com/cloudflare/cloudflared/releases/latest/download/"
            + binary_name
        )

        urllib.request.urlretrieve(
            download_url,
            cloudflared_path
        )

        cloudflared_path.chmod(0o755)

        print("Cloudflare Tunnel downloaded!")

    # Start Cloudflare Quick Tunnel
    print(f"Starting Cloudflare Tunnel on port {port}...")

    tunnel_process = subprocess.Popen(
        [
            str(cloudflared_path),
            "tunnel",
            "--url",
            f"http://127.0.0.1:{port}",
            "--no-autoupdate"
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    # Detect the generated URL automatically
    def watch_tunnel():
        for line in tunnel_process.stdout:
            print("[Cloudflare]", line, end="", flush=True)

            match = re.search(
                r"https://[a-zA-Z0-9-]+\.trycloudflare\.com",
                line
            )

            if match:
                public_url = match.group(0)

                callback_url = (
                    public_url + "/auth/discord/callback"
                )

                os.environ["DISCORD_REDIRECT_URI"] = callback_url

                print("\n================================")
                print("DREAMY CASCADE PUBLIC URL:")
                print(public_url)
                print("DISCORD OAUTH CALLBACK:")
                print(callback_url)
                print("================================\n")

                publish_api_config(public_url)

    threading.Thread(
        target=watch_tunnel,
        daemon=True
    ).start()

    # Start Flask
    try:
        app.run(
            host="0.0.0.0",
            port=port,
            use_reloader=False
        )
    finally:
        tunnel_process.terminate()

