import os
import html
import time
import random
import asyncio
import requests
from bs4 import BeautifulSoup
from bs4.element import NavigableString

import discord
from discord.ext import commands

from .utils import levenshtein_ratio

bold = lambda s: "**" + s + "**"

EMBED_COLOUR = discord.Colour.blue()

class Triplet(commands.Cog):
    """
    Cog for triplet puzzles.
    You're given a number, usually three, of words that are related to a different word.
    You have to find the fourth word based on the words that are given.
    e.g. DRAWF, SNOW, HOUSE
    Answer: WHITE

    Word bank found from "https://www.wordexample.com/list/most-common-nouns-english"
    """

    RHYMEZONE_URL = "https://api.rhymezone.com/words?max=100&k=rz_sl&sp=**{}**"
    ONELOOK_URL = "https://onelook.com/?w=*{}*&ssbp=1&scwo=1&sswo=0&loc=commonhint"

    WORD_FILES = ['nouns', 'verbs', 'adjectives']
    # Words or parts of words that are too common
    BANNED_LIST = ['?LY', '?TY', '?ITY', '?NESS', '?IZE', '?ISE', '?IZES', 'UN?', '?ISMS', '?ITIES', '?ED', 'IN?', '?IVES', '?ISTS', '?ING', '?ER', 'NON?', 'CO?', '?ION', '?TIES', '?ST', 'SUPER?', '?EST', '?IZED', '?AL', 'UNI?', '?ISER']

    def __init__(self, bot):
        self.bot = bot
        self.word_bank = []
        self.load_words()
        random.shuffle(self.word_bank)
        self.waiting = False

    def load_words(self):
        for filename in Triplet.WORD_FILES:
            with open(os.path.join(os.path.dirname(__file__), 'data/triplet', filename + '.txt'), 'r') as f:
                words = f.read().split('\n')
        self.word_bank += words

    @commands.Cog.listener()
    async def on_ready(self):
        print('Cog "Triplet" Ready!')

    """
    MEMBER FUNCTIONS
    """
    @commands.group(name="triplet", invoke_without_command=True)
    async def triplet(self, ctx):
        if self.waiting:
            await ctx.send("Please solve the current puzzle first!")
            return
        self.waiting = True
        attempts = 0
        while self.waiting and attempts < 3:
            attempts += 1
            random.shuffle(self.word_bank)
            word = random.choice(self.word_bank)
            print('Triplet:', word)
            async with ctx.typing():
                result = await self.get_html(ctx, Triplet.RHYMEZONE_URL.format(word))
                if result is not None:
                    phrases = [w['word'] for w in result.json() if w['score'] > 3]
                else:
                    phrases = []
                # if result is None or not phrases:
                soup = await self.get_soup(ctx, Triplet.ONELOOK_URL.format(word))
                if soup is not None:
                    a_tags = soup.find_all('a')
                    if not a_tags:
                        break
                    phrases += [str(x).lower().strip() for a in a_tags for x in a.contents if type(x) == NavigableString]
            phrases = [p for p in phrases if (p.startswith(word) or p.endswith(word)) and '(' not in p]
            phrases = list(set(phrases))
            if len(phrases) < 3:
                continue
            clues = []
            while len(clues) < 3 and len(phrases) > 0:
                random.shuffle(phrases)
                clue = random.choice(phrases)
                phrases.remove(clue)
                clue = clue.replace(word, '?').strip().upper()
                # print(clue)
                if len(clue.replace('?', '')) < 2 or clue in Triplet.BANNED_LIST:
                    continue
                if len(clue.replace('?', '')) < 4 and any([len(x.replace('?', '')) < 4 for x in clues]):
                    # Don't want too many short clues
                    continue
                if len(clue.split()) > 2 and any([len(x.split()) > 2 for x in clues]):
                    # Don't want too many multi word clues
                    continue
                if any([levenshtein_ratio(clue, x) > 0.6 for x in clues]):
                    # Don't want similar clues
                    continue
                clues.append(clue)
            if len(clues) < 3:
                continue
            await ctx.send(
                "**What's the missing link?**\n{}\n{}\n{}".format(*clues)
            )
            continue_ = await self.wait_for_answer(ctx, word, 15)
            self.waiting = False
        if self.waiting:
            await ctx.send("Sorry, something went wrong. Please try again.")
        self.waiting = False

    async def wait_for_answer(self, ctx, answer, timeout: float):
        """Wait for a correct answer, and then respond."""
        start = time.time()
        try:
            message = await ctx.bot.wait_for(
                "message", check=self.check_answer(ctx, answer), timeout=timeout
            )
        except asyncio.TimeoutError:
            if time.time() - start >= timeout:
                await ctx.send("Time out! The answer was **{}**.".format(answer.upper()))
                return False
        if message:
            reply = "You got it, {user}! The answer is **{answer}**.".format(user=message.author.display_name, answer=answer.upper())
            await ctx.send(reply)
            return True
        return False

    def check_answer(self, ctx, answer):
        answer = answer.lower()

        def _pred(message: discord.Message):
            early_exit = message.channel != ctx.channel or message.author == ctx.guild.me
            if early_exit:
                return False

            guess = message.content.lower()
            return guess == answer

        return _pred


    @triplet.command()
    async def help(self, ctx):
        embed = discord.Embed(
            colour = EMBED_COLOUR
        )
        embed.set_author(name=f"{self.bot.BOT_NAME}'s Triplet Puzzle")
        embed.add_field(
            name="--------------------------------",
            value="Given three words or parts of words, you have to find a fourth word that can be combined with all three to form common words or phrases.\n\ne.g. SNOW - HOUSE - DWARF --> **WHITE**\n\nI am generating these automatically, so the result may not be up to human standard. Apologies.",
            )
        await ctx.send(embed=embed)

    async def get_soup(self, ctx, url):
        res = await self.get_html(ctx, url)
        if res:
            return BeautifulSoup(res.content, 'html.parser')
        else:
            return None

    async def get_html(self, ctx, url):
        res = requests.get(url)

        # If failed
        count = 0
        while res.status_code != 200 and count < 3:
            res = requests.get(url)
            count += 1
        if res.status_code != 200:
            await ctx.send("Something went wrong. Please try again!")
            return None
        
        return res

def setup(bot):
    bot.add_cog(Triplet(bot))
