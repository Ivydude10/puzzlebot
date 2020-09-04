import os
import time
import random
import asyncio
import requests
from bs4 import BeautifulSoup
from html.parser import HTMLParser

import discord
from discord.ext import commands
from discord.ext.commands import has_any_role, Cog, group

EMBED_COLOUR = discord.Colour.dark_grey()

class Cryptic(commands.Cog):
    """
    Cryptic Crossword Clue cog for UTS Puzzle Discord Bot.
    Thanks to xsolver.net for the compiled clues.
    """
    MAIN_URL = "https://xsolver.net"
    CRYPTIC_URLS = [
        "{}/crosswords/Guardian%20Cryptic".format(MAIN_URL),
        "{}/crosswords/Daily%20Cryptic".format(MAIN_URL),
        "{}/crosswords/Cryptic%20crossword".format(MAIN_URL)
    ]

    def __init__(self, bot):
        self.bot = bot
        self.clues = None
        self.last_get = 0
        self.current_clue = None

    @Cog.listener()
    async def on_ready(self):
        print('Cog "Cryptic" Ready!')

    @group(name="cryptic", invoke_without_command=True)
    async def cryptic(self, ctx):
        url = random.choice(Cryptic.CRYPTIC_URLS)

        async with ctx.typing():
            # Use a saved list of 100 clues, refresh every hour
            if self.clues is None or len(self.clues) == 0 or time.time() - self.last_get > 3600:
                res = self.get_site(url)
                if res is None:
                    await ctx.send("Failed to connect to cryptic database!")
                    return
                soup = BeautifulSoup(res.content, 'html.parser')
                self.clues = soup.find_all('li')
                self.last_get = time.time()

            attempts = 3
            while attempts > 0:
                attempts -= 1
                clue = random.choice(self.clues)
                self.clues.remove(clue)
                clue = clue.find('a')
                clue_text = clue.text.strip()
                clue_answer_res = self.get_site(clue.attrs['href'].replace('..', Cryptic.MAIN_URL))
                if clue_answer_res is not None:
                    soup = BeautifulSoup(clue_answer_res.content, 'html.parser')
                    answer_boxes = soup.find_all('li', class_='box')
                    answer = ''.join([box.text.strip() for box in answer_boxes])
                    break
            else:
                await ctx.send("Failed to pull from cryptic database!")
                return
        clue_text += f" ({', '.join([str(len(a)) for a in answer.split(' ')])})"
        self.current_clue = (clue_text, answer)
        embed = discord.Embed(
            colour = EMBED_COLOUR
        )
        embed.set_author(name=clue_text)
        await ctx.send(embed=embed)
        await self.wait_for_answer(ctx, answer, 1, 900)

    async def wait_for_answer(self, ctx, answer, delay: float, timeout: float):
        """Wait for a correct answer, and then respond."""
        while self.current_clue is not None:
            try:
                message = await self.bot.wait_for(
                    "message", check=self.check_answer(answer), timeout=delay
                )
            except asyncio.TimeoutError:
                continue
            else:
                await ctx.send(f"You got it, {message.author.display_name}! The answer is **{answer.upper()}**!")
                self.current_clue = None
                return True
        return True

    def check_answer(self, answer):
        answer = answer.upper()
        def _pred(message: discord.Message):
            guess = message.content.upper().strip()
            return guess == answer
        return _pred
        
    @staticmethod
    def get_site(url):
        res = requests.get(url)
        attempts = 3
        
        while res.status_code != 200 and attempts > 0:
            attempts -= 1
            res = requests.get(url)
        if res.status_code != 200:
            return None
        return res

    @cryptic.command(name="answer", aliases=['solve'])
    async def answer(self, ctx):
        if self.current_clue is not None:
            clue_text, answer = self.current_clue
            embed = discord.Embed(
                colour = EMBED_COLOUR
            )
            embed.add_field(
                name="Clue: " + clue_text,
                value="Answer: ||" + answer + "||"
            )
            await ctx.send(embed=embed)
            self.current_clue = None
        else:
            await ctx.send("No cryptic clue currently active. Reply `?cryptic` to start.")

    @cryptic.command(name="help")
    async def help(self, ctx):
        embed = discord.Embed(
            colour = EMBED_COLOUR
        )
        embed.add_field(
            name=f"{self.bot.BOT_NAME}'s cryptic crossword clues",
            value="""\n\nAre you looking to solve cryptic crossword clues but don't know where to start? Here are some websites with great explanations and examples.\n\nhttps://www.theguardian.com/lifeandstyle/2010/may/03/how-to-solve-cryptic-crossword\nhttps://bestforpuzzles.com/cryptic-crossword-tutorial/\nhttps://solving-cryptics.com/\n\nIf you are stuck, you can use `?cryptic answer` to peek the answer.\nReady to jump into it? Reply `?cryptic` to start and I will give you a cryptic crossword clue!"""
        )
        embed.set_footer(text="Cryptic Clues are sourced from The Guardians and Daily Cryptic Crosswords.")
        await ctx.send(embed=embed)

def setup(bot):
    bot.add_cog(Cryptic(bot))