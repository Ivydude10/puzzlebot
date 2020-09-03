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
        if query[0].upper() not in ['SELECT', 'UPDATE', 'INSERT']:
            await ctx.send("Please use SELECT, UPDATE, or INSERT query.")
            return
        query = ' '.join(query)
        if 'DROP' in query.upper():
            await ctx.send("Nice try.")
            return
        try:
            self.bot.db_cursor.execute(query)
            res = self.bot.db_cursor.fetchall()
            await ctx.send(str(res))
        except Exception as e:
            self.bot.db.rollback()

    @Cog.listener()
    async def on_ready(self):
        print('Cog "Database" Ready!')


def setup(bot):
    bot.add_cog(Database(bot))