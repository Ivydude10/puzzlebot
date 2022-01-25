import asyncio
import random
from datetime import datetime

import discord
from discord.utils import get
from discord.ext.commands import Cog, command, has_any_role, ExtensionAlreadyLoaded, ExtensionNotFound

GUILD_ID = {
    'PUZ': 560352591234465793,
}

class Core(Cog):
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

    @Cog.listener()
    async def on_member_join(self, member):
        if member.guild.id == GUILD_ID['PUZ']:
            try:
                greet_channel = get(member.guild.text_channels, name='introductions')
                await greet_channel.send(
                    """{0.mention} *{1}*\nFeel free to introduce yourself here.""".format(
                        member,
                        random.choice([
                            "I've been expecting you.",
                            "Hey! You're finally awake.",
                            "Hello there.",
                            "Took you long enough.",
                            "Glad you could make it."
                        ])
                ))
            except:
                raise Exception("No greet channel found!")

    @Cog.listener()
    async def on_ready(self):
        print('Cog "Core" Ready!')
        await self.get_channels()
        await self.get_statuses()
        await self.change_status()

    async def get_channels(self):
        cursor = self.bot.db_execute("select channelid, serverid, channeltype from puzzledb.channels;")
        for channelid, serverid, channeltype in cursor.fetchall():
            serverid = int(serverid)
            self.bot.CHANNELS[serverid] = self.bot.CHANNELS.get(serverid, {})
            self.bot.CHANNELS[serverid].update({channeltype: self.bot.get_channel(channelid)})
        # print(self.bot.CHANNELS)

    async def get_statuses(self):
        cursor = self.bot.db_execute("select status from puzzledb.statuses;")
        self.RANDOM_STATUSES = cursor.fetchall()

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

    """
    MEMBER FUNCTIONS
    """

    @command(name="roll")
    async def roll(self, ctx, *dice: str):
        """Rolls a dice in NdN format."""
        dice = ''.join(dice).strip()
        if dice == '':
            await ctx.send('Please specify NdN, e.g. ?roll 2d6')
            return
        try:
            rolls, limit = map(int, dice.split('d'))
        except Exception:
            await ctx.send('Format has to be NdN!')
            return
        if rolls > 1024:
            await ctx.send("You're rolling too many dice!")
            return

        try:
            result = ', '.join(str(random.randint(1, limit)) for r in range(rolls))
            await ctx.send('You rolled: ' + result)
        except Exception as e:
            await ctx.send('Failed.')
            await self.bot.log(str(e))

    @has_any_role("Bot Maintainer")
    @command(name="say",
             aliases = ['echo'])
    async def mouthpiece(self, ctx, channel: str, *, sentence):
        if channel.startswith('<'):
            channel = channel[2:-1]
        elif channel.isnumeric():
            channel = ctx.guild.get_channel(int(channel))
        await channel.send(sentence)
        await ctx.message.add_reaction("✅")



def setup(bot):
    bot.add_cog(Core(bot))