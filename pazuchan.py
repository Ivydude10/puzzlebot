#!/usr/bin/env python3
# ppchan.py
import os
import random
import asyncio
import psycopg2
from datetime import datetime, timezone
from dotenv import load_dotenv

import discord
from discord.ext.commands import Bot, has_permissions, CommandNotFound, has_any_role, command, ExtensionAlreadyLoaded, ExtensionNotFound, ExtensionFailed, ExtensionNotLoaded

from cogs.core import Core
from cogs.puzzlehunt import PuzzleHunt
from cogs.database import Database
from cogs.trivia import Trivia
from cogs.triplet import Triplet
from cogs.layton import Layton
from cogs.cryptic import Cryptic
from cogs.chess import Chess
from cogs.codenames import Codenames

load_dotenv()

EMBED_COLOUR = discord.Colour.green()

class PazuChan(Bot):
    """
    ##################
    # UTS Puzzle Soc #
    #   Puzzle Bot   #
    # made by Duc Vu #
    ##################
    """
    BOT_NAME = os.getenv('BOT_NAME')
    BOT_PREFIX = os.getenv('BOT_PREFIX')
    # ADMIN_PREFIX = '?'

    CHANNELS = {
    }

    """
    INITIALISATION
    """
    def __init__(self):
        super().__init__(command_prefix=PazuChan.BOT_PREFIX)
        self.db = psycopg2.connect(os.getenv("DATABASE_URL"), sslmode="require")
        self.db.autocommit = True

        self.startup_time = datetime.now()
        self.last_updated_status = datetime.now()

        self.add_listener(self.on_ready)
        self.add_listener(self.on_command_error)

        # Override help command
        self.remove_command("help")

        # Cogs
        self.add_cog(Core(self))
        self.add_cog(PuzzleHunt(self))
        self.add_cog(Database(self))
        self.add_cog(Trivia(self))
        self.add_cog(Triplet(self))
        self.add_cog(Layton(self))
        self.add_cog(Cryptic(self))
        self.add_cog(Chess(self))
        self.add_cog(Codenames(self))


    """
    HELPER FUNCTIONS
    """
    async def on_ready(self):
        print(f'{self.user} is connected to the following guild(s):')
        for guild in self.guilds:
            print(f'{guild.name} (id: {guild.id})')

    async def on_command_error(self, ctx, error):
        if isinstance(error, CommandNotFound):
            return
        await self.log(ctx, str(error))
        raise error

    async def log(self, ctx, error_str):
        print(str(error_str))
        try:
            log_channel = self.CHANNELS[ctx.guild.id]['LOG']
            # print(ctx.guild.id)
            # print(list(self.CHANNELS.keys())[0] == ctx.guild.id)
            await log_channel.send(str(error_str))
        except Exception as e:
            print("No log channel found!!!")
            print(error_str)

    """
    DATABASE WRAPPER
    """
    def db_execute(self, query, arguments=()):
        cursor = self.db.cursor()
        cursor.execute(query, arguments)
        return cursor

if __name__ == '__main__':
    pazu = PazuChan()
    
    # Override help
    @pazu.command()
    async def help(ctx, *cogname):
        embed = discord.Embed(
            colour = EMBED_COLOUR
        )
        if len(cogname) != 1 or cogname[0] not in pazu.cogs.keys():
            embed.set_author(name=f"{pazu.BOT_NAME} Commands:")
            embed.add_field(name="?trivia", value="Test your trivia skills")
            embed.add_field(name="?hunt", value="Join a running puzzle hunt")
            embed.add_field(name="?roll NdN", value="Roll N dice each with N faces")
            embed.add_field(name="?triplet", value="Try a triplet word puzzle")
            embed.add_field(name="?layton", value="Try a puzzle from Professor Layton")
            embed.add_field(name="?cryptic", value="Try a cryptic crossword clue")
            embed.set_footer(text="Type `?<command> help` to see more details about each command.")
        else:
            embed.set_author(name=f"{pazu.BOT_NAME} {cogname[0].strip().title()} Commands:")
        await ctx.send(embed=embed)

    """
    COG SETUP FUNCTIONS
    """
    @pazu.command(name="loadcog")
    @has_any_role("Bot Maintainer")
    async def load_cog(ctx, cog_name):
        if not cog_name.startswith('cogs.'):
            cog_name = 'cogs.' + cog_name
        try:
            pazu.load_extension(cog_name)
            await ctx.send("Cog loaded.")
        except ExtensionAlreadyLoaded:
            pazu.unload_extension(cog_name)
            pazu.load_extension(cog_name)
            await ctx.send("Cog reloaded.")
        except ExtensionNotFound:
            await ctx.send("Cog not found.")
        except ExtensionFailed:
            pazu.load_extension(cog_name)
            await ctx.send("Cog reloaded.")
        except Exception as e:
            raise e

    @pazu.command(name="unloadcog")
    @has_any_role("Bot Maintainer")
    async def unload_cog(ctx, cog_name):
        if not cog_name.startswith('cogs.'):
            cog_name = 'cogs.' + cog_name
        try:
            pazu.unload_extension(cog_name)
            await ctx.send("Cog unloaded.")
        except ExtensionNotFound:
            await ctx.send("Cog not found.")
        except ExtensionNotLoaded:
            await ctx.send("Cog is either not found or already unloaded.")
        except Exception as e:
            raise e

    # Due to strange errors, we have to reload cog once at the start
    # for test_cog in ['core', 'trivia', 'triplet', 'database', 'puzzlehunt', 'layton', 'cryptic']:
    test_cog = 'core'
    try:
        pazu.load_extension("cogs." + test_cog)
    except ExtensionFailed:
        pazu.load_extension("cogs." + test_cog)

    pazu.run(os.getenv('DISCORD_TOKEN'))