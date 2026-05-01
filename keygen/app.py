import os
import re
import aiohttp
import discord
from discord import app_commands
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN")
API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:5000")

if not DISCORD_TOKEN:
    raise RuntimeError("Missing DISCORD_TOKEN environment variable.")


def parse_duration(duration_str: str) -> dict | None:
    """
    Parse duration string like 7d, 30m, 2mo, 1y into API params.
    Supported: m=minutes, d=days, mo=months, y=years
    """
    duration_str = duration_str.strip().lower()

    # Order matters: check 'mo' before 'm'
    match = re.fullmatch(r"(\d+(?:\.\d+)?)(mo|m|d|y)", duration_str)
    if not match:
        return None

    value, unit = float(match.group(1)), match.group(2)

    if unit == "m":
        return {"duration_minutes": value, "label": f"{int(value)} minute(s)"}
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
@app_commands.describe(duration="How long the key lasts: e.g. 7d, 30m, 2mo, 1y (default: 1d)")
async def generate_key(interaction: discord.Interaction, duration: str = "1d"):
    await interaction.response.defer(ephemeral=True)

    parsed = parse_duration(duration)
    if not parsed:
        await interaction.followup.send(
            "? Invalid duration format.\n"
            "Use: `30m` (minutes), `7d` (days), `2mo` (months), `1y` (years)",
            ephemeral=True
        )
        return

    label = parsed.pop("label")
    payload = parsed  # remaining keys are the API params

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{API_BASE_URL}/generate",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 201:
                    data = await resp.json()
                    key = data.get("key", "Unknown")
                    expires = data.get("expires_at", "Unknown")
                    await interaction.followup.send(
                        f"?? **Your access key:**\n```\n{key}\n```\n"
                        f"? **Expires in:** {label}\n"
                        f"?? **Expires at:** {expires[:19].replace('T', ' ')} UTC\n"
                        f"*Keep this key safe — it will not be shown again.*",
                        ephemeral=True
                    )
                elif resp.status == 429:
                    await interaction.followup.send(
                        "?? Rate limit reached. Please wait before generating another key.",
                        ephemeral=True
                    )
                else:
                    error_data = await resp.json()
                    await interaction.followup.send(
                        f"? Failed to generate key: {error_data.get('error', 'Unknown error')}",
                        ephemeral=True
                    )
    except aiohttp.ClientConnectorError:
        await interaction.followup.send(
            "? Could not connect to the key API. Please try again later.",
            ephemeral=True
        )
    except Exception as e:
        await interaction.followup.send(
            f"? Unexpected error: {str(e)}",
            ephemeral=True
        )


client.run(DISCORD_TOKEN)
