#---[ Python Imports ]---#
#import re
#import os
#import time
import json
#import random

#---[ External Imports ]---#
import discord
import asyncio
#import aiofiles
from discord.ext import commands

#---[ Local Imports ]---#
import lib
import boxes

def read_json_file(f):
	with open(f, 'r') as f:
		return json.loads(f.read())

def write_json_file(f, data):
	with open(f, 'w') as f:
		return json.dump(data, f)

#---[ Bot Initiation ]---#

command_prefix = "!"
def get_prefix(bot, message): return command_prefix
bot = commands.Bot(command_prefix=get_prefix,case_insensitive=True,status=discord.Status('online'),activity=discord.Activity())

def is_me(m):
	return m.author == bot.user

def is_bot(m):
	return m.author.bot

@bot.event
async def on_ready():
	print('Logged in as')
	print(bot.user.name)
	print(bot.user.id)
	print('------')

		


@bot.command()
async def stop(ctx):
	await ctx.message.delete()
	await bot.logout()
	exit()

# Run the Bot #
bot.run("NjI4OTgxOTA3ODYxOTI5OTg0.XZTLYQ.JpcMc3fpz2SgbiBq8WEO7veZWWY")
