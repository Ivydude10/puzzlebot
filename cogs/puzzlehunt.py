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
        self._running = False

    @commands.Cog.listener()
    async def on_ready(self):
        print('Cog "PuzzleHunt" Ready!')
    

    def get_hunt_info(self, huntid):
        self.bot.db_cursor.execute("select * from puzzledb.puzzlehunts where huntid = {};".format(huntid))
        matching = self.bot.db_cursor.fetch_one()
        if len(matching):
            hunt = matching[0]
        else:
            return None


    @hunt.command(name="activate")
    @has_any_role(name="Bot Maintainer")
    async def activate(self, ctx, huntid=None):
        if huntid is not None:
            hunt_info = self.get_hunt_info(huntid)
        if huntid is None:
            await ctx.send("Cannot activate hunt. Make sure to include the correct huntid as parameter!")
            return
        self._running = True

    """
    MEMBER FUNCTIONS
    """
    @commands.group(name="hunt", invoke_without_command=True)
    async def hunt(self, ctx):
        hunt_info = self.get_hunt_info()
        await self.help(ctx)

    @hunt.command(name="help")
    async def help(self, ctx):
        """
        Get an explanation of how the hunt function of the bot works.
        """
        embed = discord.Embed(
            colour = discord.Colour.dark_red()
        )
        if self._running:
            embed.set_author(name=f"{self.bot.BOT_NAME}'s' Hunt Commands:")
        else:
            embed.set_author(name=f"There is no Puzzle Hunt running right now!")
        await ctx.send(embed=embed)

        # " by " + self.hunt_info['Author'] + '!'
        
        # "\n\nTime left: " + bold(str(self.end_time - datetime.now())) +
        # "\n(Ends on " + self.hunt_info['End time'] + " AEDT)"

        # "\n\nYou can start by sending \"?hunt join\" to our Puzzle Discord server!\nAfter signing up, you'll have a brand new, awesome team channel to yourself!\n\n" +

        # COMMANDS +

        # "\nHere's a codesheet that might be useful: http://www.puzzledpint.com/files/2415/7835/9513/CodeSheet-201912.pdf\n"
        
        # "\nRanking is based on points and solve time, so get in early!\n"
        # "\nAre you ready? Return to the Puzzle Discord server and begin your solve!"
        # )

    @hunt.command(name='answer', aliases=['solve'])
    async def solve(self, ctx, puzid=None, *attempt):
        if puzid is None or len(attempt) == 0:
            await ctx.send("Please use this format: ?hunt answer <puzzleid> <answer phrase>")
        
        

def setup(bot):
    bot.add_cog(PuzzleHunt(bot))
