import asyncio
import random
from datetime import datetime

import discord
from discord.ext.commands import Cog

class Chatter(Cog):
    """
    Cog for general chatting, greeting and other text functions
    """
    RANDOM_STATUSES = [
        # For the bot to say: Playing
        #   'Sudoku',
        #   'Nonogram',
        #   'Crosswords',
        #   'Cryptic',
        # and more...
    ]

    def __init__(self, bot):
        self.bot = bot
        self.bot.remove_command("help")

    @Cog.listener()
    async def on_member_join(self, member):
        if self.bot.CHANNELS['GREET']:
            await self.bot.CHANNELS['GREET'].send(
                """Welcome {0.mention}! Come introduce yourself in #introductions.""".format(member))

    @Cog.listener()
    async def on_ready(self):
        print('Cog "Chatter" Ready!')
        await self.get_channels()
        await self.get_statuses()
        await self.change_status()

    async def get_channels(self):
        for channeltype in self.bot.CHANNELS.keys():
            self.bot.db_cursor.execute("select channelid from puzzledb.channels where channeltype = '{}';".format(channeltype))
            channelid = self.bot.db_cursor.fetchone()[0]
            self.bot.CHANNELS[channeltype] = self.bot.get_channel(channelid)

    async def get_statuses(self):
        self.bot.db_cursor.execute("select status from puzzledb.statuses;")
        self.RANDOM_STATUSES = self.bot.db_cursor.fetchall()

    async def change_status(self):
        wait_time = 0
        last_updated_status = datetime.now()
        while True:
            if (datetime.now() - last_updated_status).seconds >= wait_time:
                await self.bot.change_presence(
                    activity=discord.Activity(
                        type=discord.ActivityType.playing,
                        name=random.choice(self.RANDOM_STATUSES)
                    )
                )
                last_updated_status = datetime.now()
                wait_time = random.randint(180, 900)
                await asyncio.sleep(wait_time)
            await asyncio.sleep(10) # Generic short wait

    
    