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

    settings[ctx.guild].loop = not settings[ctx.guild].loop

    return await ctx.send(f"Repeat set to {settings[ctx.guild].loop}.")

@bot.command()
async def queue(ctx):
    if ctx.guild not in settings or len(settings[ctx.guild].queue) == 0:
        return await ctx.send("There is nothing in the queue.")

    content = "```\n"
    count = 1
    for song in settings[ctx.guild].queue:
        content += f"{count}. {song}\n"
        count += 1

    result = discord.Embed()
    result.title = "Queue"
    result.description = content + "\n```"
    return await ctx.send(embed=result)

@bot.command()
async def remove(ctx, arg):
    arg = int(arg)
    if arg <= 0:
        return
    i = arg - 1
    if ctx.guild not in settings or len(settings[ctx.guild].queue) == 0:
        return await ctx.send("There is nothing in the queue.")
    elif len(settings[ctx.guild].queue) == 1 or i == 0:
        return await skip(ctx)
    else:
        try:
            settings[ctx.guild].queue.pop(i)
            return await ctx.send(f"Sucessfully removed item number {i+1} from the queue.")
        except:
            await ctx.send(f"Failed to remove item number {i+1} from the queue.")
            raise

@bot.command()
async def play(ctx: commands.Context, *, arg):
    client = find_voice_client(ctx.message.guild)
    if client is None or not client.is_connected():
        try:
            vc = ctx.author.voice.channel
            client = await vc.connect()
        except:
            return await ctx.send("This command must be used while you're in a voice channel.")

    # No settings object yet, lets make a new one and add this song to its queue
    if ctx.guild not in settings:
        settings[ctx.guild] = MusicSettings()

    settings[ctx.guild].queue.append(arg)
    if len(settings[ctx.guild].queue) == 1:
        return await process_queue(ctx, client)
    else:
        return await ctx.send(f"Added \"{arg}\" to queue!")

async def process_queue(ctx, client):
    #if client.is_playing() or settings[ctx.guild].is_downloading:
        #return

    ydl_opts["outtmpl"] = f"downloads/{ctx.message.id}.%(ext)s"
    
    arg = settings[ctx.guild].queue[0]

    await ctx.send("Attempting to DL")
    
    try:
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            settings[ctx.guild].is_downloading = True
            await bot.loop.run_in_executor(None, ydl.download, [arg])
            settings[ctx.guild].is_downloading = False

        await ctx.send("DL finished, joining VC")
    except Exception as ex:
        settings[ctx.guild].queue.remove(arg)
        settings[ctx.guild].is_downloading = False
        if ex is youtube_dl.utils.DownloadError:
            await ctx.send("youtube-dl was unable to download the video.")
        else:
            await ctx.send("An exception was raised of type {0} while downloading the video.".format(type(ex)))
        raise

    try:
        file = f"downloads/{ctx.message.id}.opus"
        client.play(discord.FFmpegOpusAudio(file), after=lambda err : song_complete(ctx, client))
        settings[ctx.guild].current_filename = file
    except:
        await ctx.send("Failed to play audio. (am I in a voice channel?)")
        
def song_complete(ctx, client):
    if len(settings[ctx.guild].queue) == 0:
        return

    if settings[ctx.guild].loop:
        client.play(discord.FFmpegOpusAudio(settings[ctx.guild].current_filename), after=lambda err : song_complete(ctx, client))
        return

    settings[ctx.guild].queue.pop(0)

    # Delete the song
    filename = settings[ctx.guild].current_filename
    try:
        os.remove(filename)
        logging.info("Successfully deleted " + filename)
    except:
        logging.error(f"Failed to delete song: {filename}")

    # Queue is empty, leave the voice channel
    if len(settings[ctx.guild].queue) == 0:
        coro = client.disconnect()
    else:
        coro = process_queue(ctx, client)

    fut = asyncio.run_coroutine_threadsafe(coro, bot.loop)
    fut.result()

@bot.command()
async def skip(ctx):
    client = find_voice_client(ctx.guild)
    
    if client.is_playing():
        client.stop()


bot.run(os.environ["MusicToken"])