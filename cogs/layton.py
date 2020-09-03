import os
import time
import yaml
import random
import asyncio
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from html.parser import HTMLParser

import discord
from discord.ext import commands
from discord.ext.commands import has_any_role, Cog, group

# bold = lambda s: "**" + s + "**"

EMBED_COLOUR = discord.Colour.purple()

_SUCCESS_SOUNDBITES = [
    "Hmm... that should do it!",
    "Every puzzle has an answer!",
    "Critical thinking is the key to success!",
    "A true gentleman leaves no puzzle unsolved!",
    "I love the thrill of a good solution!"
]

_START_SOUNDBITES = [
    "That reminds me of a puzzle...",
    "Speaking of, have you heard of this puzzle?",
    "Tell me, have you heard this one before?",
    "Oh my, a puzzle!",
    "Think good and hard before you answer.",
    "Speaking of, I've got just the puzzle for you!",
    "Why not try your hand at this puzzle?",
    "Have a gander at this puzzle!",
    "Why don't you give this puzzle a go?",
    "You just reminded me of a splendid puzzle!"
]

HINT_TEXT = """There are no more hints. \n
If you are stuck, use \"?layton solve <puzzleID>\" to see the answer."""


class Layton(commands.Cog):
    """
    Professor Layton cog for UTS Puzzle Discord Bot.
    Thanks to layton.fandom.com for the compiled puzzles.
    """
    def __init__(self, bot):
        # super().__init__()
        self.bot = bot
        self._puzzles = self._load_puzzles()
        self._current_puzzle = None

    @Cog.listener()
    async def on_ready(self):
        print('Cog "Layton" Ready!')

    def _load_puzzles(self):
        with open(os.path.join(os.path.dirname(__file__), 'data/layton/puzzle_list.yaml'), 'r', encoding='utf-8') as f:
            puzzles = yaml.safe_load(f)
        return puzzles

    @group(name="layton", invoke_without_command=True)
    async def layton(self, ctx):
        await self.get_layton_puzzle(ctx)

    @layton.command(name="help")
    async def help(self, ctx):
        embed = discord.Embed(
            colour = EMBED_COLOUR
        )
        embed.set_author(name=f"{self.bot.BOT_NAME}'s Layton Commands:")
        embed.add_field(
            name="?layton",
            value="Get a random puzzle from the Layton series",
            inline=False
        )
        embed.add_field(
            name="?layton hint",
            value="See a hint (if available) for the current puzzle",
            inline=False
        )
        embed.add_field(
            name="?layton solve",
            value="View the answer to the puzzle",
            inline=False
        )
        await ctx.send(embed=embed)

    async def get_layton_puzzle(self, ctx):
        if self._current_puzzle is None or 'set_answer' not in self._current_puzzle:
            id_ = random.choice(list(self._puzzles.keys()))
            answers = [ans for ans in self._puzzles[id_] if ans not in ('', None)]
            self._current_puzzle = grab_puzzle(id_)
            if not self._current_puzzle:
                await ctx.send("I've failed to retrieve a puzzle. Please try again.")
                return
            embed = discord.Embed(
                colour = EMBED_COLOUR
            )
            # await ctx.send(get_puzzle_text(self._current_puzzle))
            puzzle_dict = self._current_puzzle
            if puzzle_dict['image']:
                embed.set_image(url=puzzle_dict['image'])
            else:
                embed.add_field(name="Image missing", value="You may have to look up the image.")
            # embed.set_author(name=puzzle_dict['title'])
            embed.add_field(
                name=puzzle_dict['title'],
                value=puzzle_dict['puzzle'],
                inline=False
            )
            embed.add_field(
                name=f"Puzzle ID: `{puzzle_dict['id']}`",
                value=f"*This is puzzle {puzzle_dict['number']} from {puzzle_dict['game']}.*",
                inline=False
            )
            footer_text = ''
            if self._current_puzzle['hints']:
                footer_text = "There are hints available for this puzzle. Type \"?layton hint\" to see one.\n"
            footer_text += "This puzzle is worth {} Picarats!".format(self._current_puzzle['picarats'])
            if answers:
                self._current_puzzle['set_answer'] = True
                footer_text += "\n**You can attempt an answer by replying.**"
            else:
                footer_text += "\nType \"?layton solve\" to check your answer!"
            embed.set_footer(text=footer_text)
            await ctx.send(embed=embed)
            if answers:
                continue_ = await self.wait_for_answer(ctx, answers, 1, 900)
        else:
            clue, ans_len = self._current_puzzle
            ans = self._all_clues[clue]
            text = "You have one puzzle in progress: **" + self._current_puzzle['id'] + "**. Stuck? Type \"?layton hint\" for a hint, or \"?layton solve\" to get the solution!"
            await ctx.send(text + "\n\n" + self._current_puzzle['puzzle'] + "\n" + self._current_puzzle['image'])

    async def wait_for_answer(self, ctx, answers, delay: float, timeout: float):
        """Wait for a correct answer, and then respond."""
        while self._current_puzzle is not None:
            try:
                message = await self.bot.wait_for(
                    "message", check=self.check_answer(answers), timeout=delay
                )
            except asyncio.TimeoutError:
                continue
            else:
                puzzle = self._current_puzzle
                solution = puzzle['solution']
                title = puzzle['title']
                sol_imgs = puzzle['solution_images']
                await ctx.send(f"\"{random.choice(_SUCCESS_SOUNDBITES)}\"\n\n**{title} - Solution**\n{solution}!\n" + '\n'.join(sol_imgs))
                await ctx.send(f"You got it, {message.author.display_name}! For solving `" + puzzle['id'] +
                                    f"`, you have earned {puzzle['picarats']} picarats!")
                self._current_puzzle = None
                return True
        return True

    def check_answer(self, answers):
        answers = [str(ans).lower() for ans in answers]
        def _pred(message: discord.Message):
            # early_exit = message.channel != self.ctx.channel or message.author == self.ctx.guild.me
            # if early_exit:
            #     return False
            guess = message.content.lower()
            guess = normalize_smartquotes(guess)
            return any([guess == ans for ans in answers])
        return _pred

    @layton.group(name='solve', invoke_without_command=True)
    async def layton_solve(self, ctx: commands.Context, *puzzle_id : str):
        """Get the solution to the last puzzle, or by puzzle ID."""
        print("Layton:", puzzle_id)
        if self._current_puzzle is None and not puzzle_id:
            await ctx.send("I'm not sure which puzzle you mean. Add the Puzzle ID?")
            return
        if not puzzle_id:
            puzzle = self._current_puzzle
        else:
            if puzzle_id[0] not in self._puzzles.keys():
                await ctx.send("Invalid puzzle ID.")
                return
            puzzle = grab_puzzle(puzzle_id[0])
            if not puzzle:
                await ctx.send("Error, maybe invalid puzzle ID.")
                return
        if puzzle == self._current_puzzle and 'set_answer' in puzzle:
            await ctx.send("A gentleman should not give away the answer when there are picarats on the line!")
            return
        embed = discord.Embed(
            colour = EMBED_COLOUR
        )
        embed.set_image(url=puzzle['solution_images'][0])
        embed.add_field(
            name=puzzle['title'] + " SOLUTION",
            value=puzzle['solution'],
            inline=False
        )
        await ctx.send(embed=embed)

    @layton.command(name='hint')
    async def layton_hint(self, ctx: commands.Context):
        """Get available hints to the current puzzle one by one."""
        if self._current_puzzle is None:
            await ctx.send("I'm not sure which puzzle you want to get the hint for.")
            return
        if not self._current_puzzle['hints']:
            await ctx.send("I'm fresh out of hints to give. Looks like you're on your own.")
            return
        puzzle_dict = self._current_puzzle
        hint_no, hint = puzzle_dict['hints'].pop(0)
        title = puzzle_dict['title']
        footer_text = '\nThere are no more hints.'
        if puzzle_dict['hints']:
            footer_text = '\nMore hints are available.'
        embed = discord.Embed(
            colour = EMBED_COLOUR
        )
        embed.add_field(
            name=puzzle_dict['title'] + " HINT " + str(hint_no),
            value=hint,
            inline=False
        )
        embed.set_footer(text=footer_text)
        await ctx.send(embed=embed)


class MyHTMLParser(HTMLParser):
    raw_data = None
    start_attrs = None
    def handle_starttag(self, tag, attrs):
        self.start_attrs = attrs
    def handle_data(self, x):
        if x.strip() != '':
            self.raw_data = x

parser = MyHTMLParser()

def grab_puzzle(puzzle_id):
    puzzle_dict = {
        'id': puzzle_id,
        'URL': "https://layton.fandom.com/wiki/Puzzle:" + puzzle_id
    }
    puzzle_html = requests.get(puzzle_dict['URL'])
    puzzle_soup = BeautifulSoup(
        puzzle_html.content, 'html.parser')
    print(puzzle_dict['URL'])
    image = puzzle_soup.find('img', class_='pi-image-thumbnail')
    try:
        puzzle_dict['image'] = image['src']
    except:
        puzzle_dict['image'] = ""

    # Game
    try:
        parser.feed(str(puzzle_soup.select("div[data-source='game']")[0]))
        for attr in parser.start_attrs:
            if attr[0] == 'title':
                game = attr[1]
    except:
        game = 'Professor Layton'
    
    # Number
    parser.reset()
    try:
        parser.feed(str(puzzle_soup.select("div[data-source='number']")[0]))
        number = parser.raw_data
    except:
        number = 'xxx'

    # Picarats
    parser.reset()
    try:
        parser.feed(str(puzzle_soup.select("div[data-source='picarats']")[0]))
        picarats = parser.raw_data
    except:
        picarats = '10'

    puzzle_dict['game'] = game
    puzzle_dict['number'] = number
    puzzle_dict['picarats'] = picarats
    
    # Get Puzzle text
    puzzle_text_span = puzzle_soup.find('span', id='Puzzle')
    puzzle_span = puzzle_text_span.parent.parent
    puzzle_txts = []
    s = time.time()
    cur = puzzle_text_span
    while time.time() - s < 0.1:
        t = cur.find_next(['p', 'h2', 'li', 'dt'])
        if t is None:
            break
        txt = t.get_text()
        if 'Hints' in txt:
            break
        else:
            puzzle_txts += txt,
        cur = t
    else:
        return False

    # Get solutions
    puz_txt = '\n'.join(puzzle_txts)
    if 'US Version' in puz_txt:
        puz_txt = puz_txt.split('UK Version\n')[0]
    puzzle_dict['puzzle'] = puz_txt

    # Get puzzle title
    title = puzzle_span.find('h2', class_='pi-title')
    puzzle_dict['title'] = title.get_text()

    correct = puzzle_span.find('span', id='Correct')
    end_table = correct.find_next('table')
    cur = correct
    sol_txts = []
    start = time.time()
    while time.time() - start < 0.5:
        if cur.find_next('table') != end_table:
            break
        p = cur.find_next(['p', 'dt'])
        if p is None:
            break
        sol_txts += p.get_text(),
        cur = p
    else:
        return False
    
    solution_txt = '\n'.join(sol_txts).split('A big thanks to')[0]
    if 'US Version' in solution_txt:
        solution_txt = solution_txt.split('UK Version')[0]
    puzzle_dict['solution'] = solution_txt

    # Get solution image
    cur = correct
    sol_imgs = []
    start = time.time()
    while time.time() - start < 0.5:
        if cur.find_next('table') != end_table:
            break
        i = cur.find_next('img')
        try:
            iurl = i['src']
            if 'http' in iurl:
                sol_imgs += iurl,
            cur = i
        except:
            break
            continue
    else:
        return False
    puzzle_dict['solution_images'] = sol_imgs

    # Get hints
    hints = puzzle_span.find_all('div', class_='tabbertab')
    hints = [hint.get_text().strip() for hint in hints if 'Hint' in hint['title']]
    hint_list = []
    for i, hint in enumerate(hints):
        if 'US Version' in hint:
            hint = hint.split('US Version\n')[1].split('UK Version\n')[0]
        hint_list += (i + 1, hint),
    puzzle_dict['hints'] = hint_list
    return puzzle_dict


def setup(bot):
    bot.add_cog(Layton(bot))