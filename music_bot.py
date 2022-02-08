import asyncio
import discord
from discord.ext import commands
import logging
import os
import youtube_dl

logging.basicConfig(level=logging.INFO)

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

#discord.opus.load_opus("libopus-0.x64")
#print(discord.opus.is_loaded())

def find_voice_client(guild) -> discord.VoiceClient:
    for x in bot.voice_clients:
            if x.guild == guild:
                return x
    return None

@bot.event
async def on_ready():
    print('We have logged in as {0.user}'.format(bot))

@bot.command()
async def join(ctx: commands.Context):
    try:
        vc = ctx.author.voice.channel
        voice = await vc.connect()
        return await ctx.send("I successfully connected to the VC!")
    except:
        return await ctx.send("This command must be used while you're in a voice channel.")

@bot.command()
async def play(ctx: commands.Context, *, arg):
    try:
        await ctx.send("Attempting to DL")
        #x = find_voice_client(ctx.message.guild)
        #x.play(discord.FFmpegOpusAudio("hellomoderator.opus"))
        
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            await bot.loop.run_in_executor(None, ydl.download, [arg])
        #return await ctx.send("Hello Moderator")
        await ctx.send("DL finished")
    except Exception as ex:
        raise
        #await ctx.send("An exception was raised of type {0}".format(type(ex)))

@bot.command()
async def dc(ctx: commands.Context):
    try:
        x = find_voice_client(ctx.message.guild)
        await x.disconnect()
        return await ctx.send("Disconnecting...")
    except:
        return await ctx.send("Failed to disconnect (am I in a voice channel?)")

bot.run(os.environ["MusicToken"])