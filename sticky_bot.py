import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Optional

import discord
from discord import app_commands
from discord.ext import commands
from firebase_admin import credentials, db, initialize_app

TOKEN = "YOUR_BOT_TOKEN"
FIREBASE_DATABASE_URL = os.getenv("FIREBASE_DATABASE_URL", "")
FIREBASE_CREDENTIALS = os.getenv("FIREBASE_CREDENTIALS")


@dataclass
class StickyConfig:
    text: str
    interval_seconds: int = 30
    color: Optional[int] = None
    footer_text: Optional[str] = None
    footer_icon_url: Optional[str] = None
    thumbnail_url: Optional[str] = None

    def to_dict(self) -> Dict[str, Optional[str]]:
        return {
            "text": self.text,
            "interval_seconds": self.interval_seconds,
            "color": self.color,
            "footer_text": self.footer_text,
            "footer_icon_url": self.footer_icon_url,
            "thumbnail_url": self.thumbnail_url,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Optional[str]]):
        raw_color = data.get("color")
        if isinstance(raw_color, str):
            try:
                color_value = int(raw_color, 16) if raw_color.startswith("#") else int(raw_color)
            except ValueError:
                color_value = None
        else:
            color_value = raw_color if isinstance(raw_color, int) else None

        return cls(
            text=data.get("text", ""),
            interval_seconds=int(data.get("interval_seconds", 30)),
            color=color_value,
            footer_text=data.get("footer_text"),
            footer_icon_url=data.get("footer_icon_url"),
            thumbnail_url=data.get("thumbnail_url"),
        )


intents = discord.Intents.default()
intents.message_content = True
intents.messages = True

bot = commands.Bot(command_prefix="!", intents=intents)

sticky_configs: Dict[int, StickyConfig] = {}
sticky_messages: Dict[int, discord.Message] = {}
last_sent_times: Dict[int, datetime] = {}
firebase_initialized = False


def init_firebase_if_needed() -> None:
    global firebase_initialized
    if firebase_initialized:
        return

    if not FIREBASE_DATABASE_URL:
        raise RuntimeError("FIREBASE_DATABASE_URL must be set for Firebase access.")

    if FIREBASE_CREDENTIALS:
        cred = credentials.Certificate(FIREBASE_CREDENTIALS)
    else:
        cred = credentials.ApplicationDefault()

    initialize_app(cred, {"databaseURL": FIREBASE_DATABASE_URL})
    firebase_initialized = True


def get_config_ref():
    init_firebase_if_needed()
    return db.reference("/sticky_configs")


def load_configs_from_firebase():
    remote_data = get_config_ref().get() or {}
    sticky_configs.clear()
    for channel_id_str, config_data in remote_data.items():
        try:
            channel_id = int(channel_id_str)
        except ValueError:
            continue

        sticky_configs[channel_id] = StickyConfig.from_dict(config_data)


def persist_config_to_firebase(channel_id: int, config: StickyConfig):
    get_config_ref().child(str(channel_id)).set(config.to_dict())


def remove_config_from_firebase(channel_id: int):
    get_config_ref().child(str(channel_id)).delete()


def parse_color(color_text: Optional[str]) -> Optional[int]:
    if not color_text:
        return None

    cleaned = color_text.strip().lower().lstrip("#")
    try:
        return int(cleaned, 16)
    except ValueError:
        return None


def format_pinned_entry(message: discord.Message) -> str:
    snippet = message.clean_content or "[Embed/Attachment]"
    snippet = (snippet[:70] + "…") if len(snippet) > 70 else snippet
    author = getattr(message.author, "display_name", message.author.name)
    timestamp = discord.utils.format_dt(message.created_at, "R")
    return f"• {author}: {snippet} ({timestamp}) [Jump]({message.jump_url})"


async def collect_pins(guild: discord.Guild):
    pinned_by_channel = []
    for channel in guild.text_channels:
        try:
            pins = await channel.pins()
        except (discord.Forbidden, discord.HTTPException):
            continue

        if pins:
            pinned_by_channel.append((channel, pins))

    return pinned_by_channel


def build_embed(config: StickyConfig, pinned_data, guild: discord.Guild) -> discord.Embed:
    embed = discord.Embed(title="Server Pinned Messages", description=config.text)
    embed.set_author(name=guild.name)

    if config.color is not None:
        embed.color = discord.Color(config.color)

    if config.footer_text or config.footer_icon_url:
        embed.set_footer(text=config.footer_text or "", icon_url=config.footer_icon_url or discord.Embed.Empty)

    if config.thumbnail_url:
        embed.set_thumbnail(url=config.thumbnail_url)

    for channel, pins in pinned_data:
        entries = [format_pinned_entry(msg) for msg in pins[:5]]
        value = "\n".join(entries)
        embed.add_field(
            name=f"#{channel.name} ({len(pins)} pinned)",
            value=value or "No pinned content",
            inline=False,
        )

    if not pinned_data:
        embed.add_field(name="Pinned status", value="No pinned messages across this server.", inline=False)

    return embed


async def send_sticky(channel: discord.TextChannel, force: bool = False) -> None:
    config = sticky_configs.get(channel.id)
    if not config:
        return

    last_sent = last_sent_times.get(channel.id, datetime.min)
    if not force and datetime.utcnow() - last_sent < timedelta(seconds=config.interval_seconds):
        return

    pinned_data = await collect_pins(channel.guild)

    previous_message = sticky_messages.get(channel.id)
    if previous_message:
        try:
            await previous_message.delete()
        except discord.HTTPException:
            pass

    embed = build_embed(config, pinned_data, channel.guild)
    sent = await channel.send(embed=embed)
    sticky_messages[channel.id] = sent
    last_sent_times[channel.id] = datetime.utcnow()


@bot.event
async def on_ready():
    await bot.tree.sync()
    load_configs_from_firebase()
    for guild in bot.guilds:
        await refresh_sticky_for_guild(guild)

    print(f"Logged in as {bot.user}")


@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    await bot.process_commands(message)


async def refresh_sticky_for_guild(guild: discord.Guild):
    for channel_id in list(sticky_configs.keys()):
        target_channel = guild.get_channel(channel_id)
        if target_channel and isinstance(target_channel, discord.TextChannel):
            await send_sticky(target_channel, force=True)


@bot.event
async def on_guild_channel_pins_update(channel: discord.abc.GuildChannel, last_pin: Optional[datetime]):
    guild = channel.guild if hasattr(channel, "guild") else None
    if guild:
        await refresh_sticky_for_guild(guild)


sticky_group = app_commands.Group(name="sticky", description="Manage sticky messages")


@sticky_group.command(name="set", description="Create or update a sticky message")
@app_commands.describe(
    channel="Channel to apply the sticky to",
    text="Sticky message content",
    interval_seconds="Minimum seconds between sticky updates",
    color_hex="Hex color for the embed (e.g., FF0000)",
    footer_text="Footer text for the embed",
    footer_icon_url="URL for the footer icon",
    thumbnail_url="URL for an embed thumbnail",
)
async def set_sticky(
    interaction: discord.Interaction,
    channel: Optional[discord.TextChannel],
    text: str,
    interval_seconds: app_commands.Range[int, 5, 3600] = 30,
    color_hex: Optional[str] = None,
    footer_text: Optional[str] = None,
    footer_icon_url: Optional[str] = None,
    thumbnail_url: Optional[str] = None,
):
    target_channel = channel or interaction.channel
    if target_channel is None:
        await interaction.response.send_message("No channel provided.", ephemeral=True)
        return

    color = parse_color(color_hex)
    if color_hex and color is None:
        await interaction.response.send_message(
            "Invalid color. Use a hex value like FF5733.", ephemeral=True
        )
        return

    sticky_configs[target_channel.id] = StickyConfig(
        text=text,
        interval_seconds=interval_seconds,
        color=color,
        footer_text=footer_text,
        footer_icon_url=footer_icon_url,
        thumbnail_url=thumbnail_url,
    )

    persist_config_to_firebase(target_channel.id, sticky_configs[target_channel.id])

    await interaction.response.send_message(
        f"Sticky saved for {target_channel.mention}. Refreshes every {interval_seconds}s.",
        ephemeral=True,
    )

    await send_sticky(target_channel, force=True)


@sticky_group.command(name="remove", description="Remove a sticky message from a channel")
@app_commands.describe(channel="Channel to clear the sticky from")
async def remove_sticky(
    interaction: discord.Interaction, channel: Optional[discord.TextChannel]
):
    target_channel = channel or interaction.channel
    if target_channel is None:
        await interaction.response.send_message("No channel provided.", ephemeral=True)
        return

    sticky_configs.pop(target_channel.id, None)
    remove_config_from_firebase(target_channel.id)

    previous_message = sticky_messages.pop(target_channel.id, None)
    if previous_message:
        try:
            await previous_message.delete()
        except discord.HTTPException:
            pass

    await interaction.response.send_message(
        f"Sticky removed from {target_channel.mention}.", ephemeral=True
    )


@sticky_group.command(name="info", description="Show sticky configuration for a channel")
@app_commands.describe(channel="Channel to show sticky info for")
async def sticky_info(
    interaction: discord.Interaction, channel: Optional[discord.TextChannel]
):
    target_channel = channel or interaction.channel
    if target_channel is None:
        await interaction.response.send_message("No channel provided.", ephemeral=True)
        return

    config = sticky_configs.get(target_channel.id)
    if not config:
        await interaction.response.send_message(
            f"No sticky is configured for {target_channel.mention}.", ephemeral=True
        )
        return

    embed = discord.Embed(title="Sticky Info", color=config.color or discord.Color.blurple())
    embed.add_field(name="Channel", value=target_channel.mention, inline=False)
    embed.add_field(name="Interval", value=f"{config.interval_seconds}s", inline=False)
    embed.add_field(name="Text", value=config.text, inline=False)
    if config.footer_text:
        embed.add_field(name="Footer", value=config.footer_text, inline=False)
    if config.thumbnail_url:
        embed.add_field(name="Thumbnail", value=config.thumbnail_url, inline=False)

    await interaction.response.send_message(embed=embed, ephemeral=True)


bot.tree.add_command(sticky_group)

if __name__ == "__main__":
    bot.run(TOKEN)
