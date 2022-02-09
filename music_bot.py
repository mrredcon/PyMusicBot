from __future__ import unicode_literals
import asyncio
import discord
from discord.ext import commands
import logging
import os
import youtube_dl
from state import MusicSettings

logging.basicConfig(level=logging.INFO)

settings = dict()

bot = commands.Bot(command_prefix="$")

ydl_opts = {
    'default_search': 'ytsearch',
    'format': 'bestaudio/best',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'opus',
        'preferredquality': '0',
    }]
}

def find_voice_client(guild) -> discord.VoiceClient:
    for x in bot.voice_clients:
            if x.guild == guild:
                return x
    return None

@bot.event
async def on_ready():
    print('We have logged in as {0.user}'.format(bot))

@bot.command()
async def repeat(ctx: commands.Context):
    if ctx.guild is None:
        return await ctx.send("This command must be used in a guild.")
    if ctx.guild not in settings:
        return await ctx.send("Settings not found for this guild (has any music been played yet?)")

    settings[ctx.guild].loop = not settings[ctx.guild.loop]

    return await ctx.send(f"Repeat set to {settings[ctx.guild].loop}.")

@bot.command()
async def queue(ctx):
    if ctx.guild not in settings:
        return
    result = ""
    for x in settings[ctx.guild].queue:
        result = x + "\n"
    return await ctx.send(result)


@bot.command()
async def play(ctx: commands.Context, *, arg):
    client = find_voice_client(ctx.message.guild)
    if client is None and not client.is_connected():
        try:
            vc = ctx.author.voice.channel
            client = await vc.connect()
        except:
            return await ctx.send("This command must be used while you're in a voice channel.")

    # No settings object yet, lets make a new one and add this song to its queue
    if ctx.guild not in settings:
        settings[ctx.guild] = MusicSettings()

    settings[ctx.guild].queue.append(arg)
    return await process_queue(ctx, client)

async def process_queue(ctx, client):
    if client.is_playing():
        return

    ydl_opts["outtmpl"] = f"downloads/{ctx.message.id}.%(ext)s"
    
    arg = settings[ctx.guild].queue[0]

    await ctx.send("Attempting to DL")
    
    try:
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            result = await bot.loop.run_in_executor(None, ydl.download, [arg])

        await ctx.send("DL finished, joining VC")
    except Exception as ex:
        settings[ctx.guild].queue.remove(arg)
        await ctx.send("An exception was raised of type {0} while downloading the video.".format(type(ex)))
        raise

    try:
        file = f"downloads/{ctx.message.id}.opus"
        client.play(discord.FFmpegOpusAudio(file), after=lambda : song_complete(ctx, client))
        settings[ctx.guild].current_filename = file
    except:
        await ctx.send("Failed to play audio. (am I in a voice channel?)")
        
def song_complete(ctx, client):
    settings[ctx.guild].queue.remove(0)

    # Delete the song
    try:
        os.remove(settings[ctx.guild].current_filename)
    except:
        logging.error(f"Failed to delete song: {settings[ctx.guild].current_filename}")

    # Queue is empty, leave the voice channel
    if settings[ctx.guild].queue.count() == 0:
        coro = client.disconnect()
    else:
        coro = process_queue(ctx, client)

    fut = asyncio.run_coroutine_threadsafe(coro, bot.loop)
    fut.result()

bot.run(os.environ["MusicToken"])