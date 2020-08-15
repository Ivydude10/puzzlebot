import asyncio
from datetime import datetime
from discord.ext import commands

class Chatter(commands.Cog):
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
    CHANNELS = {
        'LOG': 0,
        'GREET': 0
    }

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if self.CHANNELS['GREET']:
            await self.CHANNELS['GREET'].send(
                """Welcome {0.mention}! Come introduce yourself in #introductions.""".format(member))

    @commands.Cog.listener()
    async def on_ready(self, msg):
        print('Cog "Chatter" Ready!')
        await self.change_status()
        await self.get_channels()
        await self.get_statuses()

    async def get_channels(self):
        for channel_type in self.CHANNELS.keys:
            self.bot.db_cursor.execute("select channelid from puzzledb.channels where channel_type = '{}';".format(channel_type))
            channelid = self.bot.db_cursor.fetchone()[0]
            self.CHANNELS[channel_type] = self.bot.get_channel(channelid)

    async def get_statuses(self):
        self.bot.db_cursor.execute("select status from puzzledb.statuses;")
        self.RANDOM_STATUSES = self.bot.db_cursor.fetchall()

    async def change_status(self):
        wait_time = 0
        last_updated_status = datetime.now()
        while True:
            if datetime.now() - last_updated_status >= wait_time:
                await self.change_presence(
                    discord.Activity(
                        type=discord.ActivityType.playing,
                        name=random.choice(self.RANDOM_STATUSES)
                    )
                )
                last_updated_status = datetime.now()
                wait_time = random.randint(180, 900)
                await asyncio.sleep(wait_time)
            await asyncio.sleep(10) # Generic short wait

    @commands.Cog.listener
    async def on_command_error(self, ctx, error):
        if isinstance(error, CommandNotFound):
            return
        if self.LOG_CHANNEL:
            await self.bot.get_channel(self.LOG_CHANNEL).send(str(error))
        raise error
