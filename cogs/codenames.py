import os
import re
import cv2
import time
import glob
import numpy as np
import random
import shutil
import asyncio
import discord
from discord.ext.commands import Cog, group
from discord.ext import tasks


def new_embed():
    return discord.Embed(
        colour=discord.Colour.dark_red()
    )


class Codenames(Cog):
    """
    Codenames with Chess Clock
    """
    RED = (38, 90, 230)
    BLUE = (214, 69, 59)
    WHITE = (247, 248, 248)
    YELLOW = (160, 226, 235)
    BLACK = (24, 36, 45)
    FONT = cv2.FONT_HERSHEY_DUPLEX
    FONT_SCALE = 0.8
    FONT_THICKNESS = 2

    RED_EMOJI = "🟥"
    BLUE_EMOJI = "🟦"
    ANY_TEAM_EMOJI = "❔"
    RED_SPYMASTER_EMOJI = "<:redspymaster:812612601733185556>"
    BLUE_SPYMASTER_EMOJI = "<:bluespymaster:812612601930448924>"

    KEY_CHANNEL = None

    DATA_FOLDER_PATH = os.path.join(os.path.dirname(__file__), 'data/codenames/')
    PICTURES_PATH = os.path.join(DATA_FOLDER_PATH, 'images/')
    WORD_PACKS_PATH = os.path.join(DATA_FOLDER_PATH, '*.txt')
    FILEPATH_REGEX = re.compile(r".*/([A-z0-9_]*).txt.*")
    KEY_IMG_PATH = os.path.join(PICTURES_PATH, "key.png")
    BOARD_IMG_PATH = os.path.join(PICTURES_PATH, "board.png")

    IMG_H = 690
    IMG_W = 980
    LINE_W = 2

    def __init__(self, bot):
        self.bot = bot
        # self.KEY_CHANNEL = self._get_key_channel()
        self.reset_game()
        self._team_timer = 2
        self._word_bank = {}
        self._load_words()
        random.seed()
    
    def _get_key_channel(self):
        for guild in self.bot.guilds:
            if guild.id == 601608082187091978:
                return guild.get_channel(812885454205616158)
        else:
            print("ERROR! Cannot find guilds.")

    @Cog.listener()
    async def on_ready(self):
        print('Cog "Codenames" Ready!')
        self.KEY_CHANNEL = self._get_key_channel()

    def _load_words(self):
        for filepath in glob.glob(Codenames.WORD_PACKS_PATH):
            with open(filepath, 'r') as f:
                words = f.read().split('\n')
            match = Codenames.FILEPATH_REGEX.match(filepath)
            if match:
                filename = match.groups()[0]
            else:
                print("Failed to extract filepath!")
                continue
            print(f"Loading word pack {filename}")
            self._word_bank[filename] = {'enable': 1, 'words': words}
            if filename not in ['classic', 'duet']:
                self._word_bank[filename]['enable'] = 0 # Disable innuendo and custom packs by default

    async def _send_as_embed(self, ctx, title, description=""):
        embed = new_embed()
        if description:
            embed.add_field(
                name=title,
                value=description
            )
        else:
            embed.set_author(name=title)
        return await ctx.send(embed=embed)

    @staticmethod
    def _to_MMSS_str(mins):
        if mins < 0:
            mins = 0
        secs = round((mins % 1) * 60)
        mins = mins // 1
        return "%d:%02d" % (mins, secs)

    """
    HELP AND CONFIG
    """
    @group(name="codenames", invoke_without_command=True)
    async def codenames(self, ctx):
        await self.send_help(ctx)

    async def send_help(self, ctx):
        embed = new_embed()
        embed.set_author(name=f"{self.bot.BOT_NAME}'s Codenames with Chess Clock")
        embed.add_field(
            name=f"{self.bot.BOT_PREFIX}codenames play",
            value="Start a game of Codenames with Chess Clock",
            inline=True)
        embed.add_field(
            name=f"{self.bot.BOT_PREFIX}codenames stop",
            value="Stop the current game",
            inline=True)
        embed.add_field(
            name=f"{self.bot.BOT_PREFIX}codenames packs",
            value="Show word packs",
            inline=True)
        embed.add_field(
            name=f"{self.bot.BOT_PREFIX}codenames toggle [word pack]",
            value="Enable / disable word packs e.g. innuendo",
            inline=True)
        embed.add_field(
            name=f"{self.bot.BOT_PREFIX}codenames timer [time in minutes]",
            value=f"Set the amount of time each team starts with. Current time: {self._to_MMSS_str(self._team_timer)}",
            inline=True)
        embed.set_footer(text="How to play Codenames: https://www.youtube.com/watch?v=zQVHkl8oQEU")

        await ctx.send(embed=embed)

    @codenames.command(name="packs")
    async def show_packs(self, ctx):
        await self._send_as_embed(
            ctx,
            f"{self.bot.BOT_NAME}'s Codenames Word Packs:",
            "\n".join([name.title() + ('' if pack['enable'] else '\t(DISABLED)') for name, pack in self._word_bank.items()])
        )
    
    @codenames.command(name="timer")
    async def set_timer(self, ctx, value=None):
        if not value:
            await self._send_as_embed(ctx, "Set how much time (in minutes) each team has on the clock at the start.", f"Current timer: {self._to_MMSS_str(self._team_timer)}.")
            return
        if not value.isnumeric():
            await self._send_as_embed(ctx, "Argument for timer must be a number i.e. the time in minutes.")
            return
        value = float(value)
        if value < 0.1:
            await self._send_as_embed(ctx, "The timer must be a positive number, at least 0.1 min (6s).")
            return
        if value > 10:
            await self._send_as_embed(ctx, "That's too long to think for, don't you think?")
            return
        self._team_timer = value
        await self._send_as_embed(ctx, f"The time per team is set to {self._to_MMSS_str(value)}.")

    @codenames.command(name="toggle")
    async def toggle_packs(self, ctx, *, pack):
        pack = pack.lower().strip()
        if pack not in self._word_bank:
            await self._send_as_embed(ctx, f"No word pack called '{pack}' found!")
            await self.show_packs(ctx)
            return
        self._word_bank[pack]['enable'] = 1 - self._word_bank[pack]['enable']
        await self._send_as_embed(ctx, ("Enabled" if self._word_bank[pack]['enable'] else "Disabled") + f" word pack '{pack}'!")
        await self.show_packs(ctx)

    """ Timer class """
    @tasks.loop(seconds=1)  # run every 0.5 seconds
    async def timer(self):
        if self._turn:
            self._timers[self._turn] -= 1
        if self._timer_msg:
            time_embed = new_embed()
            bold = '**' if self._turn == 'Red' else ''
            time_embed.add_field(
                name='Red' + ('', '⏰')[self._turn == 'Red'],
                value=bold + self._to_MMSS_str(self._timers['Red'] / 60) + bold,
                inline=True
            )
            bold = '**' if self._turn == 'Blue' else ''
            time_embed.add_field(
                name='Blue' + ('', '⏰')[self._turn == 'Blue'],
                value=bold + self._to_MMSS_str(self._timers['Blue'] / 60) + bold,
                inline=True
            )
            await self._timer_msg.edit(
                embed=time_embed
            )
        if self._timers['Red'] < 0:
            await self._send_as_embed(self._channel, "BLUE WINS!", "by Timeout")
            self.timer.cancel()
            self._game_state['Revealed'] = [1] * 25
            self.generate_board_picture()
            await self._send_board()
            self.reset_game()
        elif self._timers['Blue'] < 0:
            await self._send_as_embed(self._channel, "RED WINS!", "by Timeout")
            self.timer.cancel()
            self._game_state['Revealed'] = [1] * 25
            self.generate_board_picture()
            await self._send_board()
            self.reset_game()


    """
    MAIN GAME
    """
    def reset_game(self):
        self._game_in_progress = False
        self._joining_msg = None
        self._joining_time = 15
        self._turn = None
        self._expected_speakers = []
        self._channel = None
        self._spymasters = {'Red': None, 'Blue': None}
        self._key_msgs = {'Red': None, 'Blue': None}
        self._timer_msg = None
        self.timer.cancel()
        self._game_state = {'Words': [], 'Key': [], 'Revealed': [0] * 25}
        self._participants = {'Blue': set(), 'Red': set(), 'Spymasters': set(), 'Names': {}}
    
    @codenames.command(name="stop")
    async def stop_game(self, ctx):
        if ctx.channel == self._channel:
            await self._send_as_embed(ctx, "GAME OVER.")
            self.reset_game()

    @codenames.command(name="play")
    async def play_codenames(self, ctx):
        if self._joining_msg is not None:
            return
        
        if self._game_in_progress:
            await self._send_as_embed("A game is already in progress.")
            return

        self._game_in_progress = True
        self.reset_game()
        self._channel = ctx.channel
        embed = new_embed()
        embed.add_field(
            name=f"Starting a game in {self._joining_time}s...",
            value="React to join the blue or red team. React to the spy icons to become spymaster." # PVP
        )
        game_starter = ctx.author.id
        if random.random() < 0.5:
            self._participants['Blue'].add(game_starter) # Can uncomment this when testing
        else:
            self._participants['Red'].add(game_starter)
        self._participants['Names'][game_starter] = ctx.author.display_name
        msg = await ctx.send(embed=embed)
        await msg.add_reaction(Codenames.BLUE_EMOJI)
        await msg.add_reaction(Codenames.RED_EMOJI)
        await msg.add_reaction(Codenames.ANY_TEAM_EMOJI)
        await msg.add_reaction(Codenames.BLUE_SPYMASTER_EMOJI)
        await msg.add_reaction(Codenames.RED_SPYMASTER_EMOJI)

        self._joining_msg = msg
        for i in range(self._joining_time * 2 - 1, 0, -1):
            embed = new_embed()
            embed.add_field(
                name=f"Starting a game in {i//2}s...",
                value="React to join the blue or red team. React to the spy icons to become spymaster."
            )
            blue_team = '\n'.join(self._participants['Names'][p] + (f"{Codenames.BLUE_SPYMASTER_EMOJI}" if p in self._participants['Spymasters'] else "") for p in self._participants['Blue'])
            embed.add_field(
                name=f"{Codenames.BLUE_EMOJI} Blue Team",
                value=blue_team if blue_team else "*Empty*"
            )
            red_team = '\n'.join(self._participants['Names'][p] + (f"{Codenames.RED_SPYMASTER_EMOJI}" if p in self._participants['Spymasters'] else "") for p in self._participants['Red'])
            embed.add_field(
                name=f"{Codenames.RED_EMOJI} Red Team",
                value=red_team if red_team else "*Empty*"
            )
            
            await msg.edit(embed=embed)
            await asyncio.sleep(0.5)
        self._joining_msg = None

        blue_spies = self._participants['Blue']
        red_spies = self._participants['Red']
        red_spies.add(game_starter)

        if len(blue_spies) + len(red_spies) < 4:
            await self._send_as_embed(ctx, "You don't have enough players to start!")
            self.reset_game()
            return # Can comment this out for testing with fewer than 4 players
        else:
            if len(blue_spies) - len(red_spies) > 1:
                print("Balancing teams...")
                chosen_one = random.choice(blue_spies)
                self._participants['Blue'].remove(chosen_one)
                self._participants['Red'].add(chosen_one)
            elif len(red_spies) - len(blue_spies) > 1:
                print("Balancing teams...")
                chosen_one = random.choice(red_spies)
                self._participants['Red'].remove(chosen_one)
                self._participants['Blue'].add(chosen_one)
    
        blue_spies = self._participants['Blue']
        red_spies = self._participants['Red']

        blue_spymasters = [p for p in blue_spies if p in self._participants['Spymasters']]
        red_spymasters = [p for p in red_spies if p in self._participants['Spymasters']]
        if len(blue_spymasters) == 0:
            blue_spymasters = list(blue_spies)
        if len(red_spymasters) == 0:
            red_spymasters = list(red_spies)
        blue_spymaster = random.choice(blue_spymasters)
        red_spymaster = random.choice(red_spymasters)
        self._spymasters = {'Blue': blue_spymaster, 'Red': red_spymaster}
        self._participants['Spymasters'] = [blue_spymaster, red_spymaster]
        
        key = self.generate_key()
        words = self.generate_words()
        self._game_state['Key'] = key
        self._game_state['Words'] = words

        match_begin_embed = new_embed()
        match_begin_embed.set_author(name="Spies, here are your teams...")
        blue_team = self._participants['Names'][blue_spymaster] + f"{Codenames.BLUE_SPYMASTER_EMOJI}\n" + '\n'.join(self._participants['Names'][p] for p in self._participants['Blue'] if p not in self._participants['Spymasters'])
        match_begin_embed.add_field(
            name=f"{Codenames.BLUE_EMOJI} Blue Team",
            value=blue_team
        )
        red_team = self._participants['Names'][red_spymaster] + f"{Codenames.RED_SPYMASTER_EMOJI}\n" + '\n'.join(self._participants['Names'][p] for p in self._participants['Red'] if p not in self._participants['Spymasters'])
        match_begin_embed.add_field(
            name=f"{Codenames.RED_EMOJI} Red Team",
            value=red_team
        )
        await ctx.send(embed=match_begin_embed)

        self.generate_board_picture(is_key=True)
        self.generate_board_picture()
        # await self._send_board()

        red_sm_dm = await self.bot.fetch_user(red_spymaster)
        blue_sm_dm = await self.bot.fetch_user(blue_spymaster)
        key_msg = await self.KEY_CHANNEL.send(file=discord.File(Codenames.KEY_IMG_PATH))
        self._key_msgs['Red'] = await red_sm_dm.send("You are RED.\n" + key_msg.attachments[0].url)
        self._key_msgs['Blue'] = await blue_sm_dm.send("You are BLUE.\n" + key_msg.attachments[0].url)

        if list(key).count("Red") == 9:
            self._turn = "Red"
        else:
            self._turn = "Blue"
        await self._send_as_embed(
            ctx,
            "Spymasters, your keys have been delivered...",
            "You should keep it open on a separate screen / device for reference."
        )
        self._timers = {c: self._team_timer * 60 + (10 if c == self._turn else 0) for c in ('Red', 'Blue')}
        self.timer.start()
        await self._start_turn()
    
    async def _start_turn(self):
        if self._turn == 'Red':
            spymaster = self._spymasters['Red']
            spymaster_name = Codenames.RED_SPYMASTER_EMOJI + self._participants['Names'][spymaster]
        else:
            spymaster = self._spymasters['Blue']
            spymaster_name = Codenames.BLUE_SPYMASTER_EMOJI + self._participants['Names'][spymaster]
            
        self._expected_speakers = [p for p in self._participants[self._turn] \
            if p not in self._participants['Spymasters']] # Comment this out when testing
        await self._channel.send(f"<@{spymaster}>")
        await self._send_as_embed(
            self._channel,
            f"{(Codenames.BLUE_EMOJI, Codenames.RED_EMOJI)[self._turn=='Red']}{self._turn} Spymaster, it is your turn.",
            f"{spymaster_name}, say a word and a number as your clue.\n" +
            "Team members, confirm your guess by typing the word by itself.\n" +
            "Think carefully!\n\nType SKIP if you want to pass."
        )
        await self._send_board()
        self._timer_msg = await self._send_as_embed(
            self._channel,
            f"Timer loading..."
        )
    
    @staticmethod
    def rinse_msg(msg):
        return re.sub(r"[-_\s]", '', msg.strip().upper())

    @Cog.listener()
    async def on_message(self, message):
        if not self._channel or message.channel.id != self._channel.id:
            return
        if message.author.id not in self._expected_speakers:
            return

        if self.rinse_msg(message.content) == 'SKIP':
            await self._send_as_embed(self._channel, f"{self._turn} team's turn has ended.")
            self._turn = ('Red', 'Blue')[self._turn == 'Red']
            await self._start_turn()
            return
        else:
            answer = self.rinse_msg(message.content)
            words = [self.rinse_msg(w) for w in self._game_state['Words']]
            if answer in words:
                word_index = words.index(answer)
                key = self._game_state['Key'][word_index]
                await self._send_as_embed(
                    self._channel,
                    f"{message.author.display_name}, you guessed {answer}..."
                )
                self._game_state['Revealed'][word_index] = 1
                self.generate_board_picture()
                await self._send_board()
                lose_turn = False
                if key == self._turn:
                    # Correct guess
                    await self._send_as_embed(
                        self._channel,
                        "Correct!",
                        "You can keep guessing, or type SKIP to pass your turn."
                    )
                elif key == "Assassin":
                    # End game
                    await self._send_as_embed(
                        self._channel,
                        "You've been ASSASSINATED!",
                        f"{('Red', 'Blue')[self._turn == 'Red'].upper()} WINS!"
                    )
                    self._game_state['Revealed'] = [1] * 25
                    self.generate_board_picture()
                    await self._send_board()
                    self.reset_game()
                    return
                else:
                    # Lose turn
                    await self._send_as_embed(
                        self._channel,
                        "Incorrect!"
                    )
                    lose_turn = True
                self.generate_board_picture(is_key=True)
                new_key_msg = await self.KEY_CHANNEL.send(file=discord.File(Codenames.KEY_IMG_PATH))
                await self._key_msgs['Red'].edit(content="You are RED.\n" + new_key_msg.attachments[0].url)
                await self._key_msgs['Blue'].edit(content="You are BLUE.\n" + new_key_msg.attachments[0].url)
                
                # Check for win condition
                blue_and_red_left = [k for idx, k in enumerate(self._game_state['Key']) if self._game_state['Revealed'][idx] == 0 and k in ('Blue', 'Red')]
                if not 'Blue' in blue_and_red_left:
                    # Blue wins
                    # End game
                    await self._send_as_embed(
                        self._channel,
                        "BLUE WINS!"
                    )
                    self._game_state['Revealed'] = [1] * 25
                    self.generate_board_picture()
                    await self._send_board()
                    self.reset_game()
                    return
                if not 'Red' in blue_and_red_left:
                    # Red wins
                    # End game
                    await self._send_as_embed(
                        self._channel,
                        "RED WINS!"
                    )
                    self._game_state['Revealed'] = [1] * 25
                    self.generate_board_picture()
                    await self._send_board()
                    self.reset_game()
                    return
                if lose_turn:
                    await self._send_as_embed(self._channel, f"{self._turn} team's turn has ended.")
                    self._turn = ('Red', 'Blue')[self._turn == 'Red']
                    await self._start_turn()
                    
    async def _send_board(self):
        if self._channel:
            await self._channel.send(file=discord.File(Codenames.BOARD_IMG_PATH))

    @Cog.listener()
    async def on_raw_reaction_add(self, *payload):
        payload = payload[0]
        if self._joining_msg and payload.message_id == self._joining_msg.id and payload.user_id != self.bot.user.id:
            emote = payload.emoji.name
            self._participants['Names'][payload.user_id] = payload.member.display_name
            if emote == Codenames.BLUE_EMOJI:
                self._participants['Blue'].add(payload.user_id)
                if payload.user_id in self._participants['Red']:
                    self._participants['Red'].remove(payload.user_id)
                await self._joining_msg.remove_reaction(payload.emoji.name, payload.member)
            elif emote == Codenames.RED_EMOJI:
                self._participants['Red'].add(payload.user_id)
                if payload.user_id in self._participants['Blue']:
                    self._participants['Blue'].remove(payload.user_id)
                await self._joining_msg.remove_reaction(payload.emoji.name, payload.member)
            elif emote == Codenames.ANY_TEAM_EMOJI:
                if random.random() > 0.5:
                    if payload.user_id in self._participants['Blue']:
                        self._participants['Blue'].remove(payload.user_id)
                    self._participants['Red'].add(payload.user_id)
                else:
                    if payload.user_id in self._participants['Red']:
                        self._participants['Red'].remove(payload.user_id)
                    self._participants['Blue'].add(payload.user_id)
                await self._joining_msg.remove_reaction(payload.emoji.name, payload.member)
            elif emote == "bluespymaster": #Codenames.BLUE_SPYMASTER_EMOJI:
                self._participants['Blue'].add(payload.user_id)
                if payload.user_id in self._participants['Red']:
                    self._participants['Red'].remove(payload.user_id)
                self._participants['Spymasters'].add(payload.user_id)
            elif emote == "redspymaster": #Codenames.RED_SPYMASTER_EMOJI:
                self._participants['Red'].add(payload.user_id)
                if payload.user_id in self._participants['Blue']:
                    self._participants['Blue'].remove(payload.user_id)
                self._participants['Spymasters'].add(payload.user_id)
            else:
                return
       

    @Cog.listener()
    async def on_raw_reaction_remove(self, *payload):
        payload = payload[0]
        if self._joining_msg and payload.message_id == self._joining_msg.id and payload.user_id != self.bot.user.id:
            emote = payload.emoji.name
            if payload.user_id in self._participants['Spymasters']:
                self._participants['Spymasters'].remove(payload.user_id)

    """
    GENERATORS
    """
    def generate_key(self):
        colour = "Blue"
        if random.random() > 0.5:
            colour = "Red"
        
        key = ["Blue"] * 8 + ["Red"] * 8 + ["Innocent"] * 7 + [colour, "Assassin"]
        random.shuffle(key)
        random.shuffle(key)
        return key
    
    def generate_words(self):
        words = [word for pack in self._word_bank.values() for word in pack['words'] if pack['enable']]
        word_list = set()
        while len(word_list) != 25:
            word_list.add(random.choice(words))
        return list(word_list)
    
    def generate_board_picture(self, is_key=False):
        key = self._game_state['Key']
        words = self._game_state['Words']
        img = np.zeros((Codenames.IMG_H, Codenames.IMG_W, 3))
        for j in range(5):
            for i in range(5):
                k = key[j * 5 + i]
                
                if is_key or self._game_state['Revealed'][j * 5 + i] == 1:
                    bg_colour = Codenames.RED if k == 'Red' else Codenames.BLUE if k == 'Blue' else Codenames.YELLOW if k == 'Innocent' else Codenames.BLACK
                else:
                    bg_colour = Codenames.WHITE
                cv2.rectangle(
                    img,
                    (i*Codenames.IMG_W//5 + Codenames.LINE_W, j*Codenames.IMG_H//5 + Codenames.LINE_W),
                    ((i+1)*Codenames.IMG_W//5 - Codenames.LINE_W, (j+1)*Codenames.IMG_H//5 - Codenames.LINE_W),
                    bg_colour,
                    cv2.FILLED
                )
                if is_key and self._game_state['Revealed'][j * 5 + i] == 1:
                    cv2.rectangle(
                        img,
                        (i*Codenames.IMG_W//5 + 10, j*Codenames.IMG_H//5 + Codenames.IMG_H//12),
                        ((i+1)*Codenames.IMG_W//5 - 10, (j+1)*Codenames.IMG_H//5 - Codenames.IMG_H//12),
                        Codenames.BLACK,
                        cv2.FILLED
                    )
                else:
                    word = words[j * 5 + i].upper()
                    text_boundary = cv2.getTextSize(word, Codenames.FONT, Codenames.FONT_SCALE, Codenames.FONT_THICKNESS)[0]
                    cv2.putText(
                        img, word,
                        (
                            i * Codenames.IMG_W // 5 + (Codenames.IMG_W//5 - text_boundary[0])//2,
                            (j+1) * Codenames.IMG_H // 5 - Codenames.IMG_H // 10 + text_boundary[1] // 2
                            ), 
                        Codenames.FONT, 
                        Codenames.FONT_SCALE,
                        Codenames.BLACK if bg_colour in (Codenames.WHITE, Codenames.YELLOW) else Codenames.WHITE,
                        Codenames.FONT_THICKNESS
                    )

        if is_key:
            cv2.imwrite(Codenames.KEY_IMG_PATH, img)
        else:
            cv2.imwrite(Codenames.BOARD_IMG_PATH, img)


def setup(bot):
    bot.add_cog(Codenames(bot))
