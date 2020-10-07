import os
import re
import glob
import time
import yaml
import asyncio
import random
from datetime import datetime

import discord
from discord.ext.commands import Cog, group

EMBED_COLOUR = discord.Colour.orange()

_ = lambda s: s
bold = lambda s: "**" + s + "**"

_REVEAL_MESSAGES = (
    _("You didn't know this? It's {answer}!"),
    _("It's {answer}! I'm surprised you didn't know!"),
    _("Ezpz, lemon squeezy. It's {answer}."),
    _("{answer} is what you were looking for."),
    _("It was, of course, {answer}."),
    _("Oops, time's up. It is {answer}."),
    _("The answer is... {answer}!"),
)
_FAIL_MESSAGES = (
    _("Onto the next one I guess..."),
    _("Moving on..."),
    _("Well, there's always next time."),
    _("No taker for that one, it seems."),
    _("I'm sure you'll know the answer of the next one."),
    _("\N{PENSIVE FACE} Next one."),
)

SMART_QUOTE_REPLACEMENT_DICT = {
    "\u2018": "'",  # Left single quote
    "\u2019": "'",  # Right single quote
    "\u201C": '"',  # Left double quote
    "\u201D": '"',  # Right double quote
}
SMART_QUOTE_REPLACE_RE = re.compile("|".join(SMART_QUOTE_REPLACEMENT_DICT.keys()))

DELAY = 15      # How long between questions
TIMEOUT = 90    # How long before session stops if no one responds
MAX_SCORE = 10  # How many points to win

class Trivia(Cog):
    """
    Cog for trivia questions
    """
    def __init__(self, bot):
        self.bot = bot
        self.session = None
        self.data_location = os.path.join(os.path.dirname(__file__), 'data/trivia/')
        self.trivia_list = self.load_trivia_list()

    @Cog.listener()
    async def on_ready(self):
        print('Cog "Trivia" Ready!')

    def load_trivia_list(self):
        trivia_list = []
        for filename in glob.glob(os.path.join(self.data_location, "*.yaml")):
            _name = filename.split('/')[-1].split('.')[0]
            trivia_list += [_name]
        return trivia_list

    def load_trivia_data(self, categories):
        _database = {}
        for filename in glob.glob(os.path.join(self.data_location, "*.yaml")):
            _name = filename.split('/')[-1].split('.')[0]
            if _name in categories:
                try:
                    with open(filename, 'r', encoding='utf-8') as f:
                        _database[_name] = yaml.safe_load(f)
                except Exception as e:
                    print("Error while loading yaml trivia file:", e)
                    continue
        return _database

    @group(name="trivia", invoke_without_command=True)
    async def trivia(self, ctx, *categories):
        await self.trivia_start(ctx, *categories)

    @trivia.command(name="help")
    async def help(self, ctx):
        embed = discord.Embed(
            colour = EMBED_COLOUR
        )
        embed.set_author(name=f"{self.bot.BOT_NAME}'s Trivia Commands:")
        embed.add_field(
            name="trivia start <category>",
            value="Begin trivia session",
            )
        embed.add_field(
            name="trivia stop",
            value="End trivia session",
            )
        embed.add_field(
            name="trivia list",
            value="View categories",
            )
        await ctx.send(embed=embed)

    @trivia.command(name="list")
    async def trivia_list(self, ctx):
        """Get a list of trivia categories"""
        embed = discord.Embed(
            colour = EMBED_COLOUR
        )
        # embed.set_author(name=self.bot.BOT_NAME + ""'s Trivia Categories:")
        trivia_list = ", ".join(self.trivia_list)
        embed.add_field(
            name=self.bot.BOT_NAME + "'s Trivia Categories",
            value="No category found" if not trivia_list else trivia_list,
            inline=True)
        await ctx.send(embed=embed)


    @trivia.command(name="start")
    async def trivia_start(self, ctx, *categories):
        """Start a trivia session"""
        if not categories:
            await self.help(ctx)
            return
        if self.session is not None:
            await ctx.send("There is already an ongoing trivia session in this channel.")
            return
        categories = [c.lower() for c in categories]
        trivia_database = self.load_trivia_data(categories)
        trivia_dict = {}
        for category in categories:
            if category in trivia_database:
                trivia_dict.update(trivia_database[category])
                trivia_dict.pop("AUTHOR", None)
            else:
                await ctx.send(f"Invalid category '{category}'. Try `{self.bot.BOT_PREFIX}trivia list` to see available categories.")
                return
        self.session = {
            "Names": {},
            "Scores": {},
            "Count": 0
        }
        await ctx.send(f"Starting Trivia: **{', '. join(categories)}**")
        await self.begin_session(ctx, trivia_dict)

            
    @trivia.command(name="stop")
    async def trivia_stop(self, ctx):
        """Stop a trivia session"""
        if self.session is not None:
            await self.end_game(ctx)
            await ctx.send("Trivia session ended.")
        

    async def begin_session(self, ctx, trivia_dict):
        self._last_response = time.time()
        for question, answers in self._iter_questions(trivia_dict):
            if not self.session:
                return
            async with ctx.typing():
                await asyncio.sleep(1.5)
            if self.session:
                self.session["Count"] += 1
                msg = bold(_("Question number {num}!").format(num=self.session["Count"])) + "\n\n" + question
            await ctx.send(msg)
            continue_ = await self.wait_for_answer(ctx, answers, DELAY, TIMEOUT)
            if continue_ is False:
                await self.end_game(ctx)
                break
            if not self.session:
                return
            if any(score >= MAX_SCORE for score in self.session['Scores'].values()):
                await self.end_game(ctx)
                break
        else:
            await ctx.send(_("There are no more questions!"))
            await self.end_game(ctx)
    
    def _iter_questions(self, trivia_dict):
        questions = list(trivia_dict.items())
        random.shuffle(questions)
        for question, answers in questions:
            answers = _parse_answers(answers)
            yield question, answers

    async def wait_for_answer(self, ctx, answers, delay: float, timeout: float):
        """Wait for a correct answer, and then respond."""
        try:
            message = await ctx.bot.wait_for(
                "message", check=self.check_answer(ctx, answers), timeout=delay
            )
        except asyncio.TimeoutError:
            if time.time() - self._last_response >= timeout:
                await ctx.send(_("Hello...? Anyone...? Guess I'll stop :("))
                await self.end_game(ctx)
                return False
            if self.session:
                reply = random.choice(_REVEAL_MESSAGES).format(answer=answers[0])
                await ctx.send(reply)
        else:
            self.session["Scores"][message.author.id] = self.session["Scores"].get(message.author.id, 0) + 1
            self.session["Names"][message.author.id] = message.author.display_name
            reply = _("You got it {user}! **+1** to you!").format(user=message.author.display_name)
            await ctx.send(reply)
        return True
    
    def check_answer(self, ctx, answers):
        answers = tuple(s.lower() for s in answers)

        def _pred(message: discord.Message):
            early_exit = message.channel != ctx.channel or message.author == ctx.guild.me
            if early_exit:
                return False

            self._last_response = time.time()
            guess = message.content.lower()
            guess = normalize_smartquotes(guess)
            guess = ''.join([c for c in guess if c.isalnum()])
            for answer in answers:
                answer = ''.join([c for c in answer if c.isalnum()])
                if " " in answer and answer in guess:
                    # Exact matching, issue #331
                    return True
                elif any(word == answer for word in guess.split(" ")):
                    return True
            return False

        return _pred

    async def end_game(self, ctx):
        """End the trivia session and display scrores."""
        if self.session:
            await self.send_table(ctx)
        self.session = None

    async def send_table(self, ctx):
        table = "+ Results: \n\n"
        for user, score in sorted(self.session['Scores'].items(), key=lambda s: -s[1]):
            table += "+ {}\t\t{}\n".format(self.session['Names'][user], score)
        await ctx.send("```diff\n" + (table) + "```")


def _parse_answers(answers):
    """Parse the raw answers to readable strings.

    The reason this exists is because of YAML's ambiguous syntax. For example,
    if the answer to a question in YAML is ``yes``, YAML will load it as the
    boolean value ``True``, which is not necessarily the desired answer. This
    function aims to undo that for bools, and possibly for numbers in the
    future too.

    answers : `iterable` of `str`
        The raw answers loaded from YAML.

    returns : `tuple` of `str`
        The answers in readable/ guessable strings.
    """
    ret = []
    for answer in answers:
        if isinstance(answer, bool):
            if answer is True:
                ret.extend(["True", "Yes", "On"])
            else:
                ret.extend(["False", "No", "Off"])
        else:
            ret.append(str(answer))
    # Uniquify list
    seen = set()
    return tuple(x for x in ret if not (x in seen or seen.add(x)))

def normalize_smartquotes(to_normalize: str) -> str:
    """
    Get a string with smart quotes replaced with normal ones

    Parameters
    ----------
    to_normalize : str
        The string to normalize.

    Returns
    -------
    str
        The normalized string.
    """

    def replacement_for(obj):
        return SMART_QUOTE_REPLACEMENT_DICT.get(obj.group(0), "")

    return SMART_QUOTE_REPLACE_RE.sub(replacement_for, to_normalize)


def setup(bot):
    bot.add_cog(Trivia(bot))
