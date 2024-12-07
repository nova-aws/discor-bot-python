import hikari
import lightbulb
import os
import re
import random
from dotenv import load_dotenv
from collections import defaultdict

load_dotenv()

# Initialize bot
bot = lightbulb.BotApp(
    token=os.getenv("DISCORD_TOKEN"),
    prefix="!",
    intents=hikari.Intents.ALL,
)

# Global Variables
image_list = []
triggered_channels = set()  # Tracks channels already responded to
triggers = {}  # Stores trigger-response pairs

# Utility Functions
def is_valid_image_url(url):
    return re.match(r"^https?:\/\/.*\.(jpg|jpeg|png|gif)$", url, re.IGNORECASE)

def should_respond(channel_id):
    return channel_id not in triggered_channels

# Event: Bot Ready
@bot.listen(hikari.StartedEvent)
async def on_ready(event):
    print(f"Logged in as {bot.get_me().username}!")

# Command: Image Embed
@bot.command
@lightbulb.option("urls", "Image URLs (space-separated)", type=str, required=True)
@lightbulb.command("image", "Send image embeds from provided URLs")
@lightbulb.implements(lightbulb.PrefixCommand)
async def send_images(ctx):
    urls = ctx.options.urls.split()
    if len(urls) > 10:
        await ctx.respond("You can only send up to 10 images at once.")
        return

    for url in urls:
        if is_valid_image_url(url):
            embed = hikari.Embed().set_image(url)
            await ctx.respond(embed=embed)
        else:
            await ctx.respond(f"Invalid image URL: {url}")

# Command: Random Image
@bot.command
@lightbulb.command("randomimage", "Send a random image from the list")
@lightbulb.implements(lightbulb.PrefixCommand)
async def random_image(ctx):
    if image_list:
        random_url = random.choice(image_list)
        embed = hikari.Embed().set_image(random_url)
        await ctx.respond(embed=embed)
    else:
        await ctx.respond("No images available in the list.")

# Command: Add Image
@bot.command
@lightbulb.option("url", "Image URL to add", type=str, required=True)
@lightbulb.command("addimage", "Add an image URL to the list")
@lightbulb.implements(lightbulb.PrefixCommand)
async def add_image(ctx):
    url = ctx.options.url
    if is_valid_image_url(url):
        image_list.append(url)
        await ctx.respond(f"Image added: {url}")
    else:
        await ctx.respond("Invalid image URL. Please provide a valid link (jpg, png, gif).")

# Command: Remove Image
@bot.command
@lightbulb.option("url", "Image URL to remove", type=str, required=True)
@lightbulb.command("removeimage", "Remove an image URL from the list")
@lightbulb.implements(lightbulb.PrefixCommand)
async def remove_image(ctx):
    url = ctx.options.url
    if url in image_list:
        image_list.remove(url)
        await ctx.respond(f"Image removed: {url}")
    else:
        await ctx.respond("Image not found in the list.")

# Command: Ping
@bot.command
@lightbulb.command("ping", "Check bot's latency")
@lightbulb.implements(lightbulb.PrefixCommand)
async def ping(ctx):
    latency = bot.heartbeat_latency * 1000
    await ctx.respond(f"Pong! Bot latency is {latency:.2f}ms.")

# Trigger Word Commands
# Command: Add Trigger (Using !janes <word> <response>)
@bot.command
@lightbulb.command("janes", "Add a trigger-response pair (e.g., !janes <word> <response>)")
@lightbulb.implements(lightbulb.PrefixCommand)
async def add_trigger(ctx):
    content = ctx.event.message.content[len(ctx.prefix + "janes "):]  # Extract everything after the command prefix
    args = content.split(" ", 1)  # Split into trigger and response
    if len(args) < 2:
        await ctx.respond("Usage: !janes <word> <response>")
        return

    trigger, response = args[0].lower(), args[1]
    triggers[trigger] = response
    await ctx.respond(f"Trigger configured: `{trigger}` will respond with: `{response}`")

# Command: Remove Specific Trigger
@bot.command
@lightbulb.option("trigger", "The trigger word to remove", type=str, required=True)
@lightbulb.command("removejanes", "Remove a specific trigger word (e.g., !removejanes <word>)")
@lightbulb.implements(lightbulb.PrefixCommand)
async def remove_trigger(ctx):
    trigger = ctx.options.trigger.lower()
    if trigger in triggers:
        del triggers[trigger]
        await ctx.respond(f"Trigger removed: `{trigger}`")
    else:
        await ctx.respond(f"Trigger `{trigger}` not found.")

# Command: Reset All Triggers
@bot.command
@lightbulb.command("resetjanes", "Reset all triggers (e.g., !resetjanes)")
@lightbulb.implements(lightbulb.PrefixCommand)
async def reset_triggers(ctx):
    triggers.clear()
    await ctx.respond("All triggers have been reset.")

# Command: List All Triggers
@bot.command
@lightbulb.command("listjanes", "List all trigger-response pairs")
@lightbulb.implements(lightbulb.PrefixCommand)
async def list_triggers(ctx):
    if triggers:
        response = "\n".join([f"`{trigger}`: {response}" for trigger, response in triggers.items()])
        await ctx.respond(f"**Current Triggers:**\n{response}")
    else:
        await ctx.respond("No triggers configured.")

# Command: Update Specific Trigger
@bot.command
@lightbulb.command("updatejanes", "Update a specific trigger's response (e.g., !updatejanes <word> <new_response>)")
@lightbulb.implements(lightbulb.PrefixCommand)
async def update_trigger(ctx):
    content = ctx.event.message.content[len(ctx.prefix + "updatejanes "):]  # Extract everything after the command prefix
    args = content.split(" ", 1)  # Split into trigger and new response
    if len(args) < 2:
        await ctx.respond("Usage: !updatejanes <word> <new_response>")
        return

    trigger, new_response = args[0].lower(), args[1]
    if trigger in triggers:
        triggers[trigger] = new_response
        await ctx.respond(f"Trigger updated: `{trigger}` will now respond with: `{new_response}`")
    else:
        await ctx.respond(f"Trigger `{trigger}` not found.")

# Event: Channel Create
@bot.listen(hikari.GuildChannelCreateEvent)
async def on_channel_create(event):
    channel_name = event.channel.name.lower()
    channel_id = event.channel.id

    for trigger, response in triggers.items():
        if trigger in channel_name and should_respond(channel_id):
            try:
                await bot.rest.create_message(channel_id, response)
                triggered_channels.add(channel_id)
                break
            except Exception as e:
                print(f"Error sending message in channel {channel_name}: {e}")

# Command: Kill (Delete Last Bot Message)
@bot.command
@lightbulb.command("kill", "Delete the bot's last message")
@lightbulb.implements(lightbulb.PrefixCommand)
async def kill(ctx):
    async for message in ctx.app.rest.fetch_messages(ctx.channel_id).limit(50):
        if message.author.id == ctx.app.application.id:
            await ctx.app.rest.delete_message(ctx.channel_id, message.id)
            confirmation = await ctx.respond("Deleted my last message.")
            await confirmation.delete_after(1)
            break
    else:
        await ctx.respond("No recent messages from me to delete.").delete_after(1)

# Error Handling
@bot.listen(hikari.ExceptionEvent)
async def on_error(event):
    print(f"Error occurred: {event.exception}")

# Run the Bot
if __name__ == "__main__":
    bot.run()
