import asyncio
import random
from datetime import datetime

import discord
from discord.ext import commands
from discord.ext.commands import has_any_role

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
        self.bot.db_cursor.execute("select * from puzzledb.puzzlehunts where huntid = '{}';".format(huntid))
        matching = self.bot.db_cursor.fetchone()
        if matching:
            _, _, puzzlecount, huntname, theme, past, starttime, endtime = matching
            print(starttime)
            return {
                'ID': huntid,
                'Puzzle count': puzzlecount,
                'Name': huntname,
                'Theme': theme,
                'Past': past,
                'Start time': starttime,
                'End time': endtime
            }
        else:
            return None

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
        if self._running:
            embed.set_author(name="Currently Running Puzzle Hunt:")
            hunt_info = self.get_hunt_info(self.current_huntid)
            if hunt_info is not None:
                remaining = hunt_info['End time'] - datetime.now()
                embed.add_field(
                    name="Name",
                    value=hunt_info['Name'],
                    inline=False
                )
                embed.add_field(
                    name="Theme",
                    value=hunt_info['Theme'],
                    inline=False
                )
                embed.add_field(
                    name="Time remaining",
                    value="N.A." if remaining.total_seconds() < 0 else str(remaining),
                    inline=False
                )
                embed.add_field(
                    name="-"*18,
                    value="Use ?hunt join to begin!",
                    inline=False
                )
                
        else:
            embed.set_author(name=f"There is no Puzzle Hunt running right now!")
        await ctx.send(embed=embed)

    @hunt.command(name="activate")
    @has_any_role("Bot Maintainer")
    async def activate(self, ctx, huntid=None):
        if huntid is not None:
            hunt_info = self.get_hunt_info(huntid)
            if hunt_info is None:
                await ctx.send("Cannot activate hunt. Huntid is not found, if this info is correct please try again later!")
                return
        else:
            await ctx.send("Cannot activate hunt. Make sure to include the correct huntid as parameter!")
            return
        self._running = True
        self.current_huntid = huntid

    @hunt.command(name='answer', aliases=['solve'])
    async def solve(self, ctx, puzid=None, *attempt):
        if puzid is None or len(attempt) == 0:
            await ctx.send("Please use this format: ?hunt answer <puzzleid> <answer phrase>")
        
        

def setup(bot):
    bot.add_cog(PuzzleHunt(bot))
