#!/usr/bin/env python3
# ppchan.py
import os
import random
import asyncio
import psycopg2
from datetime import datetime, timezone
from dotenv import load_dotenv

import discord
from discord.ext.commands import Bot, has_permissions, CommandNotFound, has_any_role, command, ExtensionAlreadyLoaded, ExtensionNotFound

from cogs.chatter import Chatter
from cogs.puzzlehunt.puzzlehunt import PuzzleHunt
from cogs.database.database import Database
from cogs.trivia.trivia import Trivia

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
    BOT_NAME = 'Pazu-chan'

    BOT_PREFIX = '?'
    # ADMIN_PREFIX = '?'

    CHANNELS = {
        'LOG': 0,
        'GREET': 0
    }

    """
    INITIALISATION
    """
    def __init__(self):
        super().__init__(PazuChan.BOT_PREFIX)
        self.db = psycopg2.connect(os.getenv("DATABASE_URL"), sslmode="require")
        self.db_cursor = self.db.cursor()

        self.last_updated_status = datetime.now()
        self.add_listener(self.on_ready)
        self.add_listener(self.on_command_error)
        # Cogs
        self.add_cog(Chatter(self))
        self.add_cog(PuzzleHunt(self))
        self.add_cog(Database(self))
        self.add_cog(Trivia(self))


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
        if self.CHANNELS['LOG']:
            await self.CHANNELS['LOG'].send(str(error))
        print(error)
        raise error

    """
    COG SETUP FUNCTIONS
    """
    @command(name="load")
    @has_any_role("Bot Maintainer")
    async def load_cog(self, ctx, cog_name):
        try:
            self.load_extension(f"cogs.{cog_name}")
            await ctx.send("Cog loaded.")
        except ExtensionAlreadyLoaded:
            await ctx.send("Cog reloading...")
            self.remove_extension(f"cogs.{cog_name}")
            self.load_extension(f"cogs.{cog_name}")
            await ctx.send("Reloaded.")
        except ExtensionNotFound:
            await ctx.send("Cog not found.")
        except Exception as e:
            raise e

    @command(name="unload")
    @has_any_role("Bot Maintainer")
    async def unload_cog(self, ctx, cog_name):
        try:
            self.remove_extension(f"cogs.{cog_name}")
        except ExtensionNotFound:
            await ctx.send("Cog not found.")
        except Exception as e:
            raise e

    """
    MEMBER FUNCTIONS
    """
    @command(name="help")
    async def help(self, channel):
        embed = discord.Embed(
            colour = EMBED_COLOUR
        )
        embed.set_author(name=f"{self.BOT_NAME} commands")
        embed.add_field(name="display my balance", value="View your PP balance", inline=True)
        embed.add_field(name="display shop", value="View games PP-chan is selling", inline=True)
        await channel.send(embed=embed)


if __name__ == '__main__':
    pazu = PazuChan()
    pazu.run(os.getenv('DISCORD_TOKEN'))