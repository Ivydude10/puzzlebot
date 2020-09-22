import re
import asyncio
import random
from datetime import datetime

import discord
from discord.ext import commands
from discord.ext.commands import has_any_role

bold = lambda s: "**" + s + "**"

EMBED_COLOUR = discord.Colour.dark_red()
TEXT_STRINGS = {
    "Register Clarification": "Please use this format: `?hunt join <team name>`.",
    "Answer Clarification": "Please use this format: `?hunt solve <puzzleid> <answer phrase>`.",
    "Recruit Clarification": "Please use this format: `?hunt recruit \<@your team member>` and explicitly mention the person.",
    "No Hunt Running": "There is no Puzzle Hunt running right now!",
    "Team Exists": "This team exists. If you're joining, ask someone in the team to perform `?hunt recruit <@your account>` to complete this action.",
    "Adding Recruit": "You are recruiting a member to your team. They will have to perform `?hunt join <your team name>` to complete this action.",
    "Team Name Length": "Your team name is too long! Please use a phrase under 30 characters.",
    "Team Name Format": "Your team name cannot be accepted! Please use at least one alphanumeric character.",
    "Created Team": "Team created successfully.",
    "Not in a Team": "You cannot perform this command because you are not in a team. You should start by using `?hunt join <team name>`",
    "Already in a Team": "You cannot perform this command because you are already in a team. If you wish to change team, use `?hunt leave`.",
    "Waiting for Recruitee": "You have recruited a new member to your team. To confirm, ask said member to perform `?hunt join <your team name>`.",
    "Recruitee in Team": "Your recruitee is already in a team. They need to perform `?hunt leave` first to join your team.",
    "Correct Answer": "Your answer is... CORRECT! You have gained {} points!",
    "Wrong Answer": "Sorry, that is not the right answer.",
    "Wrong Channel": "You cannot perform this action in the current channel. Please use your team channel.",
    "Already Solved": "This puzzle has already been solved!",
}

class PuzzleHunt(commands.Cog):
    """
    Cog for puzzle hunt
    """

    def __init__(self, bot):
        self.bot = bot    
        self._huntid = None
        self._VARIABLES = {
            "Hide locked puzzles": True,
            "Non-meta same link": True
        }

        self._huntid = 'arcade'
    

    @commands.Cog.listener()
    async def on_ready(self):
        print('Cog "PuzzleHunt" Ready!')


    """
    STATIC METHODS
    """
    @staticmethod
    def sanitize_name(name):
        name = ''.join([c for c in name if c.isalnum() or c in '-_ ']).strip()
        name = name.replace(" ", "-").strip('-').strip('_')
        return name

    """
    BOT FUNCTIONS
    """

    def _get_hunt_info(self, huntid=None):
        if huntid is None and self._huntid is None:
            return None
        elif huntid is None:
            huntid = self._huntid
        cursor = self.bot.db_execute("SELECT * FROM puzzledb.puzzlehunts WHERE huntid = %s", (huntid,))
        matching_hunt = cursor.fetchone()
        if matching_hunt:
            _, _, puzzlecount, huntname, theme, past, starttime, endtime = matching_hunt
            # print(starttime)
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

    def _get_team_info_from_member(self, memberid):
        if memberid is None or self._huntid is None:
            return None
        cursor = self.bot.db_execute("SELECT * FROM puzzledb.puzzlehunt_solvers WHERE huntid = %s AND id = %s", (self._huntid, memberid))
        matching_solver = cursor.fetchone()
        if matching_solver:
            _, teamid, _ = matching_solver
        else:
            return None
        return self._get_team_info(teamid)
        

    def _get_team_info_from_name(self, teamname):
        cursor = self.bot.db_execute("SELECT id FROM puzzledb.puzzlehunt_teams WHERE huntid = %s AND teamname = %s", (self._huntid, teamname))
        try:
            teamid = cursor.fetchone()[0]
        except:
            return None
        return self._get_team_info(teamid)

    def _get_team_info(self, teamid):
        if teamid is None or self._huntid is None:
            return None
        cursor = self.bot.db_execute("SELECT * FROM puzzledb.puzzlehunt_teams WHERE huntid = %s AND id = %s", (self._huntid, teamid))
        matching_team = cursor.fetchone()
        if matching_team:
            teamid, huntid, teamname, teamchannel = matching_team
            cursor = self.bot.db_execute("SELECT * FROM puzzledb.puzzlehunt_solves WHERE huntid = %s AND teamid = %s", (self._huntid, teamid))
            matching_solves = cursor.fetchall()
            
            last_solve = None
            for solve in matching_solves:
                _, _, _, solvetime, puzzleid = solve
                if last_solve is None or solvetime > last_solve:
                    last_solve = solvetime
            
            cursor = self.bot.db_execute("SELECT SUM(points) FROM puzzledb.puzzlehunt_puzzles WHERE huntid = %s AND puzzleid IN (SELECT puzzleid FROM puzzledb.puzzlehunt_solves WHERE huntid = %s AND teamid = %s)", (self._huntid, self._huntid, teamid))
            points = cursor.fetchone()[0]
            if points is None:
                points = 0

            return {
                'Team ID': teamid,
                'Team Name': teamname,
                'Channel ID': teamchannel,
                'Points': points,
                'Latest Solve Time': last_solve
            }
        else:
            return None

    async def _add_to_team(self, ctx, memberid, teamid):
        self.bot.db_execute("INSERT INTO puzzledb.puzzlehunt_solvers (id, huntid, teamid) VALUES (%s, %s, %s)", (memberid, self._huntid, teamid))
        team_info = self._get_team_info(teamid)
        team_channel = ctx.guild.get_channel(team_info['Channel ID'])
        member = ctx.guild.get_member(memberid)
        if team_channel:
            await team_channel.set_permissions(
                member,
                read_messages=True,
                send_messages=True)
        
        await self._send_as_embed(ctx, "Successfully added member @{} to team `{}`.".format(member.display_name, team_info['Team Name']), "You can now access the team channel at #{}.".format(team_channel))
        await team_channel.send("Welcome to team `{}`, <@{}>!".format(team_info['Team Name'], memberid))


    async def _create_team(self, ctx, solverid, teamname):
        channelname = self.sanitize_name(teamname)
        await self._send_as_embed(ctx, "Creating a new team...")
        channel = await ctx.guild.create_text_channel(channelname, category=discord.utils.get(ctx.guild.categories, name='Puzzle Hunt'))
        await channel.set_permissions(
            ctx.guild.default_role,
            read_messages=False,
            send_messages=False,
            read_message_history=False,
        )
        await channel.set_permissions(ctx.author, read_messages=True,
                                                  send_messages=True)
        cursor = self.bot.db_execute("INSERT INTO puzzledb.puzzlehunt_teams (huntid, teamname, teamchannel) VALUES (%s, %s, %s) returning id", (self._huntid, teamname, channel.id))
        teamid = cursor.fetchone()[0]
        await self._add_to_team(ctx, ctx.author.id, teamid)

    """
    MEMBER FUNCTIONS
    """
    @commands.group(name="hunt", invoke_without_command=True)
    async def hunt(self, ctx):
        embed = discord.Embed(colour=EMBED_COLOUR)
        if self._huntid is not None:
            embed.set_author(name="Currently Running Puzzle Hunt:")
            hunt_info = self._get_hunt_info(self._huntid)
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
                    name="-" * 18,
                    value="Use `?hunt join` to begin!",
                    inline=False
                )
                
        else:
            embed.set_author(name=TEXT_STRINGS['No Hunt Running'])
        await ctx.send(embed=embed)


    @hunt.command(name="help", aliases=["commands", "tutorial"])
    async def help(self, ctx):
        """
        Get an explanation of how the hunt function of the bot works.
        """
        embed = discord.Embed(colour=EMBED_COLOUR)
        if self._huntid is not None:
            embed.set_author(name="Puzzle Hunt Commands:")
            embed.add_field(
                name="join <team name>",
                value="Join / create a team",
                inline=True)
            embed.add_field(
                name="recruit <@ user>",
                value="Recruit someone into your team",
                inline=True)
            embed.add_field(
                name="leave",
                value="Leave your current team (deletes team if you are the last member)",
                inline=True)
            embed.add_field(
                name="puzzles",
                value="View available puzzles",
                inline=True)
            embed.add_field(
                name="solve <puzzle id> <your answer>",
                value="Attempt to solve a puzzle",
                inline=True)
            embed.add_field(
                name="team",
                value="View your team info",
                inline=True)
            embed.add_field(
                name="leaderboard",
                value="See the overall leaderboard",
                inline=True)
            embed.add_field(
                name="help",
                value="See this list of commands",
                inline=True)
            embed.add_field(
                name="faq / errata",
                value="See frequently asked questions, errata and clarifications.",
                inline=True)
            embed.set_footer(text="To use any of these commands, send a message beginning with `?hunt` followed by the command in question.")   
        else:
            embed.set_author(name=TEXT_STRINGS['No Hunt Running'])
        await ctx.send(embed=embed)
        
    
    async def _send_as_embed(self, ctx, title, description=None):
        embed = discord.Embed(colour=EMBED_COLOUR)
        if description:
            embed.add_field(
                name=title,
                value=description,
                inline=False
            )
        else:
            embed.set_author(name=title)
        await ctx.send(embed=embed)

    @hunt.command(name='answer', aliases=['solve'])
    async def solve(self, ctx, puzid=None, *attempt):
        if self._huntid is None:
            await self._send_as_embed(ctx, TEXT_STRINGS['No Hunt Running'])
            return
        team_info = self._get_team_info_from_member(ctx.author.id)
        if team_info is None:
            await self._send_as_embed(ctx, TEXT_STRINGS['Not in a Team'])
            return
        if ctx.message.channel != ctx.guild.get_channel(team_info['Channel ID']):
            await self._send_as_embed(ctx, TEXT_STRINGS['Wrong Channel'])
            return

        if puzid is None or len(attempt) == 0:
            await self._send_as_embed(ctx, TEXT_STRINGS['Answer Clarification'])
            return

        cursor = self.bot.db_execute("SELECT puzzleid FROM puzzledb.puzzlehunt_solves WHERE huntid = %s and teamid = %s;", (self._huntid, team_info['Team ID']))
        solves = cursor.fetchall()
        solved = [solve[0] for solve in solves]
        if puzid in solved:
            await self._send_as_embed(ctx, TEXT_STRINGS['Already Solved'])
            return
        
        cursor = self.bot.db_execute("SELECT * FROM puzzledb.puzzlehunt_puzzles where huntid = %s and puzzleid = %s;", (self._huntid, puzid))
        puzzle = cursor.fetchone()
        if not puzzle:
            cursor = self.bot.db_execute("SELECT * FROM puzzledb.puzzlehunt_puzzles where huntid = %s and UPPER(name) = UPPER(%s);", (self._huntid, puzid))
            puzzle = cursor.fetchone()
            if not puzzle:
                await self._send_as_embed(ctx, TEXT_STRINGS['Answer Clarification'])
                return
        _, _, _, name, relatedlink, points, requiredpoints, answer = puzzle
        attempt = ''.join(attempt).lower().replace(' ', '')

        if attempt == answer:
            # Correct solve
            await self._send_as_embed(ctx, TEXT_STRINGS['Correct Answer'].format(points))
            self.bot.db_execute("INSERT INTO puzzledb.puzzlehunt_solves (huntid, puzzleid, solvetime, teamid) VALUES (%s, %s, %s, %s);", (self._huntid, puzid, datetime.now(), team_info['Team ID']))
        else:
            # Wrong
            await self._send_as_embed(ctx, TEXT_STRINGS['Wrong Answer'])
            if len(attempt) <= 50:
                self.bot.db_execute("INSERT INTO puzzledb.puzzlehunt_bad_attempts (huntid, puzzleid, solvetime, teamid, attempt) VALUES (%s, %s, %s, %s, %s);", (self._huntid, puzid, datetime.now(), team_info['Team ID'], attempt))

    @hunt.command(name='join')
    async def join(self, ctx, *, teamname):
        if self._huntid is None:
            await self._send_as_embed(ctx, TEXT_STRINGS['No Hunt Running'])
            return
        if len(teamname) == 0:
            await self._send_as_embed(ctx, TEXT_STRINGS['Register Clarification'])
            return
        if self._get_team_info_from_member(ctx.author.id) is not None:
            await self._send_as_embed(ctx, TEXT_STRINGS['Already in a Team'])
            return
        # teamname = " ".join(teamname).strip()
        if len(teamname) > 30:
            await self._send_as_embed(ctx, TEXT_STRINGS['Team Name Length'])
            return
        if len(self.sanitize_name(teamname)) == 0:
            await self._send_as_embed(ctx, TEXT_STRINGS['Team Name Format'])
            return
        cursor = self.bot.db_execute("SELECT * FROM puzzledb.puzzlehunt_teams where huntid = %s and teamname = %s", (self._huntid, teamname))
        team = cursor.fetchone()
        if team is not None:
            teamid = team[0]
            cursor = self.bot.db_execute("SELECT * FROM puzzledb.puzzlehunt_team_applications where huntid = %s and teamid = %s and solverid = %s", (self._huntid, teamid, ctx.author.id))
            app = cursor.fetchone()
            if app is not None:
                _, _, _, _, recruited, joined = app
                if recruited:
                    await self._add_to_team(ctx, ctx.author.id, teamname)
                else:
                    await self._send_as_embed(ctx, TEXT_STRINGS['Team Exists'])
            else:
                await self._send_as_embed(ctx, TEXT_STRINGS['Team Exists'])
                self.bot.db_execute("INSERT INTO puzzledb.puzzlehunt_team_applications (huntid, teamid, solverid, recruited, joined) VALUES (%s, %s, %s, FALSE, TRUE)", (self._huntid, teamid, ctx.author.id))
        else:
            await self._create_team(ctx, ctx.author.id, teamname)

    @hunt.command(name='recruit')
    async def recruit(self, ctx, *mentions):
        if self._huntid is None:
            await self._send_as_embed(ctx, TEXT_STRINGS['No Hunt Running'])
            return
        
        if len(ctx.message.mentions) != 1:
            await self._send_as_embed(ctx, TEXT_STRINGS['Recruit Clarification'])
            return

        team_info = self._get_team_info_from_member(ctx.author.id)
        if team_info is None:
            await self._send_as_embed(ctx, TEXT_STRINGS['Not in a Team'])
            return
        teamid = team_info['Team ID']

        recruitedid = ctx.message.mentions[0].id
        existed_in_team = self._get_team_info_from_member(recruitedid)
        if existed_in_team is not None:
            await self._send_as_embed(ctx, TEXT_STRINGS["Recruitee in Team"])

        cursor = self.bot.db_execute("SELECT * FROM puzzledb.puzzlehunt_team_applications where huntid = %s and teamid = %s and solverid = %s", (self._huntid, teamid, recruitedid))
        app = cursor.fetchone()
        if app:
            _, _, _, _, recruited, joined = app
            if joined:
                await self._add_to_team(ctx, recruitedid, teamid)
            else:
                await self._send_as_embed(ctx, TEXT_STRINGS['Waiting for Recruitee'])
        else:
            await self._send_as_embed(ctx, TEXT_STRINGS['Waiting for Recruitee'])
            self.bot.db_execute("INSERT INTO puzzledb.puzzlehunt_team_applications WHERE huntid = %s AND teamid = %s AND solverid = %s", (self._huntid, teamid, recruitedid))


    @hunt.command(name='leave')
    async def leave(self, ctx):
        if self._huntid is None:
            await self._send_as_embed(ctx, TEXT_STRINGS['No Hunt Running'])
            return
        team_info = self._get_team_info_from_member(ctx.author.id)
        if team_info is None:
            await self._send_as_embed(ctx, TEXT_STRINGS['Not in a Team'])
            return
        teamid = team_info['Team ID']
        cursor = self.bot.db_execute("SELECT * FROM puzzledb.puzzlehunt_solvers WHERE huntid = %s AND teamid = %s", (self._huntid, teamid))
        members = cursor.fetchall()
        
        self.bot.db_execute("DELETE FROM puzzledb.puzzlehunt_solvers WHERE huntid = %s AND teamid = %s AND id = %s", (self._huntid, teamid, ctx.author.id))
        team_channelid = team_info['Channel ID']
        channel = ctx.guild.get_channel(team_channelid)
        await channel.set_permissions(
            target=ctx.author, read_messages=False, send_messages=False)

        if len(members) == 1:
            await self._send_as_embed(ctx, "You are the last member. The team will be deleted.")
            await channel.delete()
            self.bot.db_execute("DELETE FROM puzzledb.puzzlehunt_teams WHERE huntid = %s AND id = %s", (self._huntid, teamid))
    
    @hunt.command(name="leaderboard")
    async def leaderboard(self, ctx):
        if self._huntid is None:
            await self._send_as_embed(ctx, TEXT_STRINGS['No Hunt Running'])
            return

        hunt_info = self._get_hunt_info()
        embed = discord.Embed(colour=EMBED_COLOUR)
        embed.set_author(name=hunt_info['Name'] + " Leaderboard")
        
        cursor = self.bot.db_execute("SELECT * FROM puzzledb.puzzlehunt_teams WHERE huntid = %s", (self._huntid,))
        all_teams = cursor.fetchall()
        _teaminfos = [
            self._get_team_info(team[0]) 
            for team in all_teams
        ]
        team_infos = [
            (
                team['Team Name'],
                team['Points'],
                team['Latest Solve Time']
            )
            for team in _teaminfos
        ]
        # print(team_infos)
        team_infos = sorted(team_infos, key=lambda x: [-x[1], x[2]])

        names = [team[0] for team in team_infos]

        if len(names) > 0 and team_infos[0][1] > 0: names[0] = "**" + names[0] + ' 🥇**'
        if len(names) > 1 and team_infos[1][1] > 0: names[1] = "**" + names[1] + ' 🥈**'
        if len(names) > 2 and team_infos[2][1] > 0: names[2] = "**" + names[2] + ' 🥉**'

        names = '\n'.join(names)
        points = '\n'.join([str(team[1]) for team in team_infos])
        times = '\n'.join(["--" if type(team[2]) == int or team[2] is None else datetime.strftime(team[2], "%H:%M:%S") for team in team_infos])

        if names == '':
            names = points = times = "--------"

        embed.add_field(name='Team', value=names, inline=True)
        embed.add_field(name='Points', value=points, inline=True)
        embed.add_field(name='Last solve', value=times, inline=True)

        await ctx.send(embed=embed)

    @hunt.command(name="faq", aliases=['errata'])
    async def view_faq(self, ctx):
        if self._huntid is None:
            await self._send_as_embed(ctx, TEXT_STRINGS['No Hunt Running'])
            return
        
        cursor = self.bot.db_execute("SELECT * FROM puzzledb.puzzlehunt_faqs WHERE huntid = %s;", (self._huntid,))
        faqs = cursor.fetchall()
        
        questions = []
        errata = []

        for faq in faqs:
            _, title, content, kind = faq
            desc = '**' + title + '** ' + content
            if kind == 'faq':
                questions += desc,
            else:
                errata += desc,
        
        embed = discord.Embed(colour=EMBED_COLOUR)
        
        embed.add_field(name='FAQ', value='\n'.join(questions) if questions else '--', inline=False)
        embed.add_field(name='Errata', value='\n'.join(errata) if errata else '--', inline=False)
        await ctx.send(embed=embed)



    @hunt.command(name="team", aliases=['myteam', 'viewteam', 'teaminfo'])
    async def view_team(self, ctx):
        if self._huntid is None:
            await self._send_as_embed(ctx, TEXT_STRINGS['No Hunt Running'])
            return
        team_info = self._get_team_info_from_member(ctx.author.id)
        if team_info is None:
            await self._send_as_embed(ctx, TEXT_STRINGS['Not in a Team'])
            return
        
        cursor = self.bot.db_execute(
            """
                SELECT COUNT(points), SUM(points) AS total_points, MAX(solvetime) FROM puzzledb.puzzlehunt_solves solves
                    LEFT JOIN puzzledb.puzzlehunt_puzzles puzzles
                    ON solves.puzzleid = puzzles.puzzleid AND solves.huntid = puzzles.huntid
                    WHERE teamid = %s and solves.huntid = %s
            """,
            (team_info['Team ID'], self._huntid)
        )
        puzzles_solved, points, _ = cursor.fetchone()

        cursor = self.bot.db_execute(
            "SELECT * FROM puzzledb.puzzlehunt_solvers WHERE huntid = %s and teamid = %s",
            (self._huntid, team_info['Team ID'])
        )
        
        members = cursor.fetchall()
        members = [ctx.guild.get_member(mem[0]).display_name for mem in members]

        embed = discord.Embed(colour=EMBED_COLOUR)
        embed.set_author(name="Your Team:")
        
        embed.add_field(name='Name', value=team_info['Team Name'], inline=False)
        embed.add_field(name='Puzzles solved', value=str(puzzles_solved), inline=False)
        embed.add_field(name='Total points', value=points, inline=False)
        embed.add_field(name='Members', value='\n'.join(members), inline=False)
        await ctx.send(embed=embed)

        
    @hunt.command(name="puzzles")
    async def view_puzzles(self, ctx):
        if self._huntid is None:
            await self._send_as_embed(ctx, TEXT_STRINGS['No Hunt Running'])
            return

        hunt_info = self._get_hunt_info()

        team_info = self._get_team_info_from_member(ctx.author.id)
        if team_info is None:
            await self._send_as_embed(ctx, TEXT_STRINGS['Not in a Team'])
            return

        if ctx.message.channel != ctx.guild.get_channel(team_info['Channel ID']):
            await self._send_as_embed(ctx, TEXT_STRINGS['Wrong Channel'])
            return

        cursor = self.bot.db_execute("SELECT * FROM puzzledb.puzzlehunt_puzzles WHERE huntid = %s;", (self._huntid,))
        puzzles = cursor.fetchall()
        cursor = self.bot.db_execute("SELECT puzzleid FROM puzzledb.puzzlehunt_solves WHERE huntid = %s and teamid = %s;", (self._huntid, team_info['Team ID']))
        solves = cursor.fetchall()
        solves = [solve[0] for solve in solves]

        puzzleids = []
        names = []
        statuses = []

        puzzles = sorted(puzzles, key=lambda x: x[0])

        for puzzle in puzzles:
            _, _, puzzleid, name, relatedlink, points, requiredpoints, answer = puzzle
            if team_info['Points'] >= requiredpoints:
                puzzleids.append(puzzleid)
                names.append("[{}]({}) ({} pts)".format(name, relatedlink, points))
                statuses.append("SOLVED" if puzzleid in solves else "_ _")
            elif not self._VARIABLES['Hide locked puzzles']:
                # Puzzle locked, but can still be shown
                puzzleids.append('*' + puzzleid + '*')
                names.append("*{} ({} pts)*".format(name, points))
                statuses.append("*LOCKED*")
        
        embed = discord.Embed(colour=EMBED_COLOUR)
        embed.set_author(name=hunt_info['Name'] + " Puzzles:")
        puzzleids = '\n'.join(puzzleids) if puzzleids else "----"
        names = '\n'.join(names) if names else "----"
        statuses = '\n'.join(statuses) if statuses else "----"
        embed.add_field(name='ID', value=puzzleids, inline=True)
        embed.add_field(name='Puzzle', value=names, inline=True)
        embed.add_field(name='Status', value=statuses, inline=True)

        if self._VARIABLES['Non-meta same link']:
            embed.set_footer(text='All non-meta puzzles use the same link. You only need to open it once.')

        await ctx.send(embed=embed)
        return

    """
    MAINTAINER FUNCTIONS
    """
    @hunt.command(name="toggle")
    @has_any_role("Bot Maintainer")
    async def toggle_variable(self, ctx, *variable):
        if len(variable) == 0:
            await self._send_as_embed(ctx, "Need to include variable to toggle.", "See the list below.")
            return
        variable = ' '.join(variable)
        if variable not in self._VARIABLES:
            await self._send_as_embed(ctx, "Variable not found.", "See the list below.")
            return
        self._VARIABLES[variable] = not self._VARIABLES[variable]
        await self.view_variables(ctx)

    @hunt.command(name="variables")
    @has_any_role("Bot Maintainer")
    async def view_variables(self, ctx):
        variable_names = []
        variable_values = []
        for name, val in self._VARIABLES.items():
            variable_names += name,
            variable_values += 'TRUE' if val else 'FALSE',
        embed = discord.Embed(colour=EMBED_COLOUR)
        embed.set_author(name="Puzzle Hunt Variables:")
        embed.add_field(name='Variable', value="\n".join(variable_names), inline=True)
        embed.add_field(name='Value', value="\n".join(variable_values), inline=True)
        await ctx.send(embed=embed)

    @hunt.command(name="activate")
    @has_any_role("Bot Maintainer")
    async def activate(self, ctx, huntid=None):
        # Activate a hunt
        if huntid is not None:
            hunt_info = self._get_hunt_info(huntid)
            if hunt_info is None:
                await self._send_as_embed(ctx, "Cannot activate hunt", "`huntid` is not found. If this info is correct, please try again later!")
                return
        else:
            await self._send_as_embed(ctx, "Cannot activate hunt.", "Make sure to include the correct `huntid` as parameter!")
            return
        self._huntid = huntid
        await self._send_as_embed(ctx, "Hunt activated.")
    
    @hunt.command(name="deactivate")
    @has_any_role("Bot Maintainer")
    async def deactivate(self, ctx):
        # Deactivate any running hunt
        if self._huntid is not None:
            await self._send_as_embed(ctx, "Deactivated running hunt (`{}`).".format(self._huntid,))
            self._huntid = None
        else:
            await self._send_as_embed(ctx, TEXT_STRINGS["No Hunt Running"])
    
    @hunt.command(name="purgeteam")
    @has_any_role("Bot Maintainer")
    async def purge_team(self, ctx, *, teamname):
        if self._huntid is None:
            await self._send_as_embed(ctx, TEXT_STRINGS["No Hunt Running"])
            return
        if len(teamname) == 0:
            await self._send_as_embed(ctx, "Need to provide team name!")
            return
        # teamname = ' '.join(teamname)
        team_info = self._get_team_info_from_name(teamname)
        if team_info is None:
            await self._send_as_embed(ctx, "No such team!")
            return
        try:
            await ctx.guild.get_channel(team_info['Channel ID']).delete()
        except:
            pass

        self.bot.db_execute("DELETE FROM puzzledb.puzzlehunt_team_applications WHERE huntid = %s AND teamid = %s", (self._huntid, team_info['Team ID']))
        self.bot.db_execute("DELETE FROM puzzledb.puzzlehunt_solvers WHERE huntid = %s AND teamid = %s", (self._huntid, team_info['Team ID']))
        self.bot.db_execute("DELETE FROM puzzledb.puzzlehunt_solves WHERE huntid = %s AND teamid = %s", (self._huntid, team_info['Team ID']))
        self.bot.db_execute("DELETE FROM puzzledb.puzzlehunt_teams WHERE huntid = %s AND id = %s", (self._huntid, team_info['Team ID']))
        await self._send_as_embed(ctx, "Team has been deleted.")



def setup(bot):
    bot.add_cog(PuzzleHunt(bot))
