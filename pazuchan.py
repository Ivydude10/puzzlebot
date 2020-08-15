#!/usr/bin/env python3
# ppchan.py
import os
import random
import asyncio
import psycopg2
from datetime import datetime, timezone
from dotenv import load_dotenv

import discord
from discord.ext.commands import Bot, has_permissions, CommandNotFound, has_any_role

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

    BOT_PREFIX = '!puz'
    ADMIN_PREFIX = '!admin'

    """
    INITIALISATION
    """
    def __init__(self):
        self.db = psycopg2.connect(os.getenv("DATABASE_URL"), sslmode="require")
        self.db_cursor = self.db.cursor()

        self.last_updated_status = datetime.now()
        self.add_listener(self.on_ready)
        self.add_listener(self.on_command_error)

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
    async def help(self, channel):
        embed = discord.Embed(
            colour = discord.Colour.dark_red()
        )
        embed.set_author(name=f"{self.BOT_NAME} commands")
        await channel.send(embed=embed)

if __name__ == '__main__':
    pazu = PazuChan()
    pazu.run(os.getenv('DISCORD_TOKEN'))