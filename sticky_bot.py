import discord
from discord.ext import commands

TOKEN = "YOUR_BOT_TOKEN"
CHANNEL_ID = 123456789012345678  # replace with your channel ID
STICKY_TEXT = "📌 **READ THIS OR ELSE:**\nDon't ignore this message."

intents = discord.Intents.default()
intents.message_content = True
intents.messages = True

bot = commands.Bot(command_prefix="!", intents=intents)

last_sticky = None

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

@bot.event
async def on_message(message):
    global last_sticky

    # ignore bot messages
    if message.author.bot:
        return

    # wrong channel? we leave
    if message.channel.id != CHANNEL_ID:
        return

    try:
        # delete previous sticky message if it exists
        if last_sticky:
            try:
                await last_sticky.delete()
            except:
                pass

        # send a new sticky at the bottom
        last_sticky = await message.channel.send(STICKY_TEXT)

    except Exception as e:
        print("Sticky error:", e)

    # process commands too
    await bot.process_commands(message)

bot.run(TOKEN)
