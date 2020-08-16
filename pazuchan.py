#!/usr/bin/env python3
# ppchan.py
import os
import random
import asyncio
import psycopg2
from datetime import datetime, timezone
from dotenv import load_dotenv

import discord
from discord.ext.commands import Bot, has_permissions, CommandNotFound, has_any_role, command

from cogs.chatter import Chatter
from cogs.puzzlehunt import PuzzleHunt

load_dotenv()

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


    """
    HELPER FUNCTIONS
    """
    async def on_ready(self):
        print(f'{self.user} is connected to the following guild(s):')
        for guild in self.guilds:
            print(f'{guild.name} (id: {guild.id})')

    """
    MEMBER FUNCTIONS
    """
    @command(name="help")
    async def help(self, channel):
        embed = discord.Embed(
            colour = discord.Colour.green()
        )
        embed.set_author(name=f"{self.BOT_NAME} commands")
        await channel.send(embed=embed)


if __name__ == '__main__':
    pazu = PazuChan()
    pazu.run(os.getenv('DISCORD_TOKEN'))