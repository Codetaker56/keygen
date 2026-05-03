import os
import re
import threading
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
import aiohttp
import discord
from discord import app_commands
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN")
API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:5000")

if not DISCORD_TOKEN:
    raise RuntimeError("Missing DISCORD_TOKEN environment variable.")


class PingHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"status": "ok"}')

    def log_message(self, format, *args):
        pass


def run_ping_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), PingHandler)
    server.serve_forever()


def parse_duration(duration_str: str) -> dict | None:
    duration_str = duration_str.strip().lower()
    match = re.fullmatch(r"(\d+(?:\.\d+)?)(mo|h|m|d|y)", duration_str)
    if not match:
        return None

    value, unit = float(match.group(1)), match.group(2)

    if unit == "m":
        return {"duration_minutes": value, "label": f"{int(value)} minute(s)"}
    elif unit == "h":
        return {"duration_hours": value, "label": f"{int(value)} hour(s)"}
    elif unit == "d":
        return {"duration_days": value, "label": f"{int(value)} day(s)"}
    elif unit == "mo":
        return {"duration_days": value * 30, "label": f"{int(value)} month(s)"}
    elif unit == "y":
        return {"duration_days": value * 365, "label": f"{int(value)} year(s)"}

    return None


class KeyBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()
        print("Slash commands synced.")

    async def on_ready(self):
        print(f"Logged in as {self.user} (ID: {self.user.id})")


client = KeyBot()


@client.tree.command(name="generate", description="Generate a new access key (private)")
@app_commands.describe(duration="How long the key lasts: e.g. 7d, 12h, 30m, 2mo, 1y (default: 1d)")
async def generate_key(interaction: discord.Interaction, duration: str = "1d"):
    try:
        await interaction.response.defer(ephemeral=True)
    except discord.errors.NotFound:
        return

    parsed = parse_duration(duration)
    if not parsed:
        await interaction.followup.send(
            "❌ Invalid duration format.\n"
            "Use: `30m` (minutes), `12h` (hours), `7d` (days), `2mo` (months), `1y` (years)",
            ephemeral=True
        )
        return

    label = parsed.pop("label")
    payload = parsed

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{API_BASE_URL}/generate",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status == 201:
                    data = await resp.json()
                    key = data.get("key", "Unknown")
                    expires_at_str = data.get("expires_at", None)

                    if expires_at_str:
                        dt = datetime.fromisoformat(expires_at_str)
                        unix_ts = int(dt.replace(tzinfo=timezone.utc).timestamp())
                        timestamp_str = f"<t:{unix_ts}:R> (<t:{unix_ts}:F>)"
                    else:
                        timestamp_str = "Never"

                    await interaction.followup.send(
                        f"🔑 **Your access key:**\n```\n{key}\n```\n"
                        f"⏳ **Key expires:** {timestamp_str}\n"
                        f"*Keep this key safe — it will not be shown again.*",
                        ephemeral=True
                    )
                elif resp.status == 429:
                    await interaction.followup.send(
                        "⚠️ Rate limit reached. Please wait before generating another key.",
                        ephemeral=True
                    )
                else:
                    error_data = await resp.json()
                    await interaction.followup.send(
                        f"❌ Failed to generate key: {error_data.get('error', 'Unknown error')}",
                        ephemeral=True
                    )
    except aiohttp.ClientConnectorError:
        await interaction.followup.send(
            "❌ Could not connect to the key API. Please try again later.",
            ephemeral=True
        )
    except Exception as e:
        await interaction.followup.send(f"❌ Unexpected error: {str(e)}", ephemeral=True)


@client.tree.command(name="listkeys", description="List all active keys (private)")
async def list_keys(interaction: discord.Interaction):
    try:
        await interaction.response.defer(ephemeral=True)
    except discord.errors.NotFound:
        return

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{API_BASE_URL}/listkeys",
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    keys = data.get("keys", [])

                    if not keys:
                        await interaction.followup.send("📭 No active keys found.", ephemeral=True)
                        return

                    lines = []
                    for row in keys:
                        key = row.get("key")
                        expires_at_str = row.get("expires_at")
                        if expires_at_str:
                            dt = datetime.fromisoformat(expires_at_str)
                            unix_ts = int(dt.replace(tzinfo=timezone.utc).timestamp())
                            expiry = f"<t:{unix_ts}:R>"
                        else:
                            expiry = "Never"
                        lines.append(f"`{key}` — expires {expiry}")

                    message = f"🗝️ **Active Keys ({len(keys)}):**\n" + "\n".join(lines)

                    # Discord has a 2000 char limit
                    if len(message) > 2000:
                        message = message[:1990] + "\n..."

                    await interaction.followup.send(message, ephemeral=True)
                else:
                    await interaction.followup.send("❌ Failed to fetch keys.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Unexpected error: {str(e)}", ephemeral=True)


@client.tree.command(name="deletekey", description="Delete an active key")
@app_commands.describe(key="The key to delete (e.g. WATER-XXXXX-XXXXX)")
async def delete_key(interaction: discord.Interaction, key: str):
    try:
        await interaction.response.defer(ephemeral=True)
    except discord.errors.NotFound:
        return

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{API_BASE_URL}/deletekey",
                json={"key": key},
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status == 200:
                    await interaction.followup.send(
                        f"🗑️ Key `{key.upper()}` has been deleted.",
                        ephemeral=True
                    )
                elif resp.status == 404:
                    await interaction.followup.send(
                        f"❌ Key `{key.upper()}` not found.",
                        ephemeral=True
                    )
                else:
                    await interaction.followup.send("❌ Failed to delete key.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Unexpected error: {str(e)}", ephemeral=True)


threading.Thread(target=run_ping_server, daemon=True).start()
client.run(DISCORD_TOKEN)
