import asyncio
import random
from datetime import datetime

import discord
from discord.ext import commands

bold = lambda s: "**" + s + "**"

class PuzzleHunt(commands.Cog):
    """
    Cog for puzzle hunt
    """

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print('Cog "PuzzleHunt" Ready!')

    """
    MEMBER FUNCTIONS
    """
    @commands.group(name="hunt", invoke_without_command=True)
    async def hunt(self, ctx):
        await self.help(ctx)

    @hunt.command(name="help")
    async def help(self, ctx):
        """
        Get an explanation of how the hunt function of the bot works.
        """
        embed = discord.Embed(
            colour = discord.Colour.dark_red()
        )
        embed.set_author(name=f"{self.bot.BOT_NAME}'s Puzzle Hunt commands")
        await ctx.send(embed=embed)
        # hunt_info = ("Hello, I am Pazu-chan, and welcome to the " + bold(self.hunt_info['Name']) + " puzzle hunt"

        # " by " + self.hunt_info['Author'] + '!'
        
        # "\n\nTime left: " + bold(str(self.end_time - datetime.now())) +
        # "\n(Ends on " + self.hunt_info['End time'] + " AEDT)"

        # "\n\nYou can start by sending \"?hunt join\" to our Puzzle Discord server!\nAfter signing up, you'll have a brand new, awesome team channel to yourself!\n\n" +

        # COMMANDS +

        # "\nHere's a codesheet that might be useful: http://www.puzzledpint.com/files/2415/7835/9513/CodeSheet-201912.pdf\n"
        
        # "\nRanking is based on points and solve time, so get in early!\n"
        # "\nAre you ready? Return to the Puzzle Discord server and begin your solve!"
        # )