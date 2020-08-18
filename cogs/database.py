import asyncio
import random
from datetime import datetime

import discord
from discord.ext.commands import Cog, command, has_any_role

class Database(Cog):
    """
    Cog for handling database calls
    """
    def __init__(self, bot):
        self.bot = bot

    @has_any_role("Bot Maintainer")
    @command(name="query")
    async def query(self, ctx, *query):
        query = ' '.join(query)
        print(query)

    @Cog.listener()
    async def on_ready(self):
        print('Cog "Database" Ready!')