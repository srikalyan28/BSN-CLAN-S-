# -*- coding: utf-8 -*-
"""
Join Clan Ticket System for Blackspire Nation
- Implements the complete join clan application flow from PLAN
- Integrates with Clash King API for player stats
- Handles continent selection, age brackets, multiple accounts
- Creates threads and manages clan selection with TH matching
"""
import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
from typing import Optional, Dict, List, Any
import aiohttp
import asyncio
import json
from .views.question_views import QuestionSelectView, QuestionTextView
from .base_ticket import BaseTicketHandler

from .base_ticket import BaseTicketHandler

class JoinClanTicket(BaseTicketHandler):
    """Join Clan ticket handler with Clash King integration"""
    
    def __init__(self, bot):
        super().__init__(bot)
        self.data_manager = bot.data_manager
        
        # Continent options from PLAN
        self.continents = [
            ("Asia", "🌏"),
            ("North America", "🌎"),
            ("South America", "🌎"),
            ("Africa", "🌍"),
            ("Australia", "🌏"),
            ("Europe", "🌍")
        ]
        
        # Age brackets from PLAN
        self.age_brackets = [
            ("Below 17", "👶"),
            ("17-25", "👨"),
            ("25+", "👴")
        ]
        
        # Clan types from PLAN
        self.clan_types = [
            ("Regular", "⚔️", "Very strict about wars, events and raids"),
            ("Cruise", "🚢", "Allow 2 hero down for wars and do competitive CWL and events"),
            ("FWA/GFL Farming", "🌾", "Extremely chill with easy wars and lazy CWLS")
        ]

    async def start_join_clan_ticket(self, interaction: discord.Interaction):
        """Start the join clan ticket process"""
        embed = discord.Embed(
            title="⚔️ Join Our Clans",
            description="Welcome to the Blackspire Nation clan application system!\n\nLet's get started with your application:",
            color=0xff6600
        )
        embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else None)
        
        view = ContinentSelectionView(self.bot, self)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    async def get_player_stats(self, player_tag: str) -> Optional[Dict[str, Any]]:
        """Get player stats from Clash King API"""
        try:
            # Remove # if present and URL encode
            clean_tag = player_tag.replace("#", "").replace("+", "%2B")
            url = f"https://api.clashking.ing/player/{clean_tag}/stats"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self.parse_player_data(data)
                    else:
                        print(f"Clash King API error: {response.status}")
                        return None
        except Exception as e:
            print(f"Error fetching player stats: {str(e)}")
            return None

    def parse_player_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse player data from Clash King API response"""
        try:
            return {
                'name': data.get('name', 'Unknown'),
                'tag': data.get('tag', ''),
                'town_hall_level': data.get('townHallLevel', 0),
                'exp_level': data.get('expLevel', 0),
                'trophies': data.get('trophies', 0),
                'best_trophies': data.get('bestTrophies', 0),
                'war_stars': data.get('warStars', 0),
                'clan': data.get('clan', {}).get('name', 'No Clan'),
                'league': data.get('league', {}).get('name', 'Unranked'),
                'heroes': self.extract_heroes(data.get('heroes', [])),
                'troops': self.extract_troops(data.get('troops', [])),
                'spells': self.extract_spells(data.get('spells', [])),
                'siege_machines': self.extract_siege_machines(data.get('siegeMachines', []))
            }
        except Exception as e:
            print(f"Error parsing player data: {str(e)}")
            
    def get_ticket_type(self) -> str:
        """Get the ticket type identifier"""
        return "join_clan"
        
    async def _start_ticket_process(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Start the join clan application process"""
        try:
            # Get saved questions
            questions = await self.mongo.get_questions(interaction.guild_id, "join_clan")
            if not questions:
                # Use default questions if none are configured
                questions = [
                    {
                        "id": "continent",
                        "question": "Which continent are you from?",
                        "type": "select",
                        "options": self.continents
                    },
                    {
                        "id": "age",
                        "question": "What is your age bracket?",
                        "type": "select",
                        "options": self.age_brackets
                    },
                    {
                        "id": "clan_type",
                        "question": "What type of clan are you looking for?",
                        "type": "select",
                        "options": self.clan_types
                    },
                    {
                        "id": "player_tag",
                        "question": "What is your Clash of Clans player tag?",
                        "type": "text"
                    }
                ]

            # Store questions in database if they don't exist
            await self.mongo.update_questions(interaction.guild_id, "join_clan", questions)

            # Create thread for the application
            thread = await channel.create_thread(
                name=f"Join Clan - {interaction.user.name}",
                type=discord.ChannelType.private_thread
            )

            # Update ticket with thread ID
            await self.mongo.update_ticket_thread(channel.id, thread.id)

            # Start the question flow
            await self._ask_next_question(interaction, thread, questions, {})
            
        except Exception as e:
            print(f"Error starting ticket process: {e}")
            await interaction.followup.send(
                "❌ An error occurred while starting your application. Please try again.",
                ephemeral=True
            )
            
    async def _ask_next_question(
        self,
        interaction: discord.Interaction,
        thread: discord.Thread,
        questions: List[Dict],
        answers: Dict,
        current_index: int = 0
    ):
        """Ask the next question in the flow"""
        try:
            # Check if we're done with questions
            if current_index >= len(questions):
                await self._handle_completion(interaction, thread, answers)
                return

            # Get current question
            question = questions[current_index]
            
            # Create embed for question
            embed = discord.Embed(
                title=f"Question {current_index + 1}/{len(questions)}",
                description=question['question'],
                color=0x00ff00
            )

            # Create appropriate view based on question type
            if question['type'] == 'select':
                view = QuestionSelectView(
                    self,
                    questions,
                    answers,
                    current_index,
                    question['options']
                )
            else:
                view = QuestionTextView(
                    self,
                    questions,
                    answers,
                    current_index
                )

            await thread.send(embed=embed, view=view)
            
        except Exception as e:
            print(f"Error asking question: {e}")
            await thread.send("❌ An error occurred. Please contact staff for assistance.")
            
    async def _handle_completion(
        self,
        interaction: discord.Interaction,
        thread: discord.Thread,
        answers: Dict
    ):
        """Handle completion of the question flow"""
        try:
            # Format a summary of answers
            embed = discord.Embed(
                title="✅ Application Summary",
                description="Thank you for your application! Here's a summary:",
                color=0x00ff00
            )

            for question_id, answer in answers.items():
                if isinstance(answer, tuple):
                    embed.add_field(
                        name=question_id.replace('_', ' ').title(),
                        value=f"{answer[1]} {answer[0]}",
                        inline=False
                    )
                else:
                    embed.add_field(
                        name=question_id.replace('_', ' ').title(),
                        value=answer,
                        inline=False
                    )

            # If player tag provided, get and display stats
            if 'player_tag' in answers:
                stats = await self.data_manager.get_player_stats(answers['player_tag'])
                if stats:
                    stats_embed = self._create_stats_embed(stats)
                    await thread.send(embed=stats_embed)

            await thread.send(embed=embed)
            await thread.send(
                content=(
                    "Your application has been submitted! "
                    "Staff will review it and get back to you soon.\n\n"
                    "Feel free to add any additional information in this thread."
                )
            )
            
        except Exception as e:
            print(f"Error handling completion: {e}")
            await thread.send("❌ An error occurred while finalizing your application. Please contact staff for assistance.")
            return {}

    def extract_heroes(self, heroes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract hero information"""
        hero_info = {}
        for hero in heroes:
            name = hero.get('name', '')
            level = hero.get('level', 0)
            max_level = hero.get('maxLevel', 0)
            hero_info[name] = {
                'level': level,
                'max_level': max_level,
                'percentage': (level / max_level * 100) if max_level > 0 else 0
            }
        return hero_info

    def extract_troops(self, troops: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract troop information"""
        troop_info = {}
        for troop in troops:
            name = troop.get('name', '')
            level = troop.get('level', 0)
            max_level = troop.get('maxLevel', 0)
            troop_info[name] = {
                'level': level,
                'max_level': max_level,
                'percentage': (level / max_level * 100) if max_level > 0 else 0
            }
        return troop_info

    def extract_spells(self, spells: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract spell information"""
        spell_info = {}
        for spell in spells:
            name = spell.get('name', '')
            level = spell.get('level', 0)
            max_level = spell.get('maxLevel', 0)
            spell_info[name] = {
                'level': level,
                'max_level': max_level,
                'percentage': (level / max_level * 100) if max_level > 0 else 0
            }
        return spell_info

    def extract_siege_machines(self, siege_machines: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract siege machine information"""
        siege_info = {}
        for siege in siege_machines:
            name = siege.get('name', '')
            level = siege.get('level', 0)
            max_level = siege.get('maxLevel', 0)
            siege_info[name] = {
                'level': level,
                'max_level': max_level,
                'percentage': (level / max_level * 100) if max_level > 0 else 0
            }
        return siege_info

    def create_player_stats_embed(self, player_data: Dict[str, Any], account_number: int = 1) -> discord.Embed:
        """Create embed for player stats"""
        embed = discord.Embed(
            title=f"📊 Account {account_number}: {player_data.get('name', 'Unknown')}",
            color=0x3498db,
            timestamp=datetime.utcnow()
        )
        
        # Basic info
        embed.add_field(
            name="🏰 Basic Info",
            value=(
                f"**Name:** {player_data.get('name', 'Unknown')}\n"
                f"**Tag:** {player_data.get('tag', 'Unknown')}\n"
                f"**Town Hall:** {player_data.get('town_hall_level', 0)}\n"
                f"**Level:** {player_data.get('exp_level', 0)}"
            ),
            inline=True
        )
        
        # Trophies and War
        embed.add_field(
            name="🏆 Trophies & War",
            value=(
                f"**Trophies:** {player_data.get('trophies', 0):,}\n"
                f"**Best Trophies:** {player_data.get('best_trophies', 0):,}\n"
                f"**War Stars:** {player_data.get('war_stars', 0)}\n"
                f"**League:** {player_data.get('league', 'Unranked')}"
            ),
            inline=True
        )
        
        # Current Clan
        embed.add_field(
            name="🏛️ Current Clan",
            value=player_data.get('clan', 'No Clan'),
            inline=True
        )
        
        # Heroes (top 4)
        heroes = player_data.get('heroes', {})
        if heroes:
            hero_text = ""
            for i, (hero_name, hero_data) in enumerate(list(heroes.items())[:4]):
                hero_text += f"**{hero_name}:** {hero_data['level']}/{hero_data['max_level']}\n"
            embed.add_field(
                name="🦸 Heroes",
                value=hero_text or "No heroes found",
                inline=True
            )
        
        embed.set_footer(text="Clash King API • Blackspire Nation")
        return embed

class ContinentSelectionView(discord.ui.View):
    """View for continent selection"""
    
    def __init__(self, bot, ticket_handler):
        super().__init__(timeout=300)
        self.bot = bot
        self.ticket_handler = ticket_handler

    @discord.ui.select(
        placeholder="Choose your continent...",
        options=[
            discord.SelectOption(label="Asia", value="Asia", emoji="🌏"),
            discord.SelectOption(label="North America", value="North America", emoji="🌎"),
            discord.SelectOption(label="South America", value="South America", emoji="🌎"),
            discord.SelectOption(label="Africa", value="Africa", emoji="🌍"),
            discord.SelectOption(label="Australia", value="Australia", emoji="🌏"),
            discord.SelectOption(label="Europe", value="Europe", emoji="🌍")
        ]
    )
    async def continent_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        continent = select.values[0]
        
        embed = discord.Embed(
            title="🌍 Continent Selected",
            description=f"Selected: **{continent}**\n\nPlease confirm your selection:",
            color=0x00ff00
        )
        
        view = ContinentConfirmationView(self.bot, self.ticket_handler, continent)
        await interaction.response.edit_message(embed=embed, view=view)

class ContinentConfirmationView(discord.ui.View):
    """View for confirming continent selection"""
    
    def __init__(self, bot, ticket_handler, continent):
        super().__init__(timeout=300)
        self.bot = bot
        self.ticket_handler = ticket_handler
        self.continent = continent

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.success, emoji="✅")
    async def confirm_continent(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="👶 Age Bracket Selection",
            description="Please select your age bracket:",
            color=0x3498db
        )
        
        view = AgeBracketSelectionView(self.bot, self.ticket_handler, self.continent)
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="Reselect", style=discord.ButtonStyle.secondary, emoji="🔄")
    async def reselect_continent(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="🌍 Choose Your Continent",
            description="Please select your continent:",
            color=0x3498db
        )
        
        view = ContinentSelectionView(self.bot, self.ticket_handler)
        await interaction.response.edit_message(embed=embed, view=view)

class AgeBracketSelectionView(discord.ui.View):
    """View for age bracket selection"""
    
    def __init__(self, bot, ticket_handler, continent):
        super().__init__(timeout=300)
        self.bot = bot
        self.ticket_handler = ticket_handler
        self.continent = continent

    @discord.ui.select(
        placeholder="Choose your age bracket...",
        options=[
            discord.SelectOption(label="Below 17", value="Below 17", emoji="👶"),
            discord.SelectOption(label="17-25", value="17-25", emoji="👨"),
            discord.SelectOption(label="25+", value="25+", emoji="👴")
        ]
    )
    async def age_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        age_bracket = select.values[0]
        
        embed = discord.Embed(
            title="👶 Age Bracket Selected",
            description=f"Selected: **{age_bracket}**\n\nPlease confirm your selection:",
            color=0x00ff00
        )
        
        view = AgeConfirmationView(self.bot, self.ticket_handler, self.continent, age_bracket)
        await interaction.response.edit_message(embed=embed, view=view)

class AgeConfirmationView(discord.ui.View):
    """View for confirming age bracket selection"""
    
    def __init__(self, bot, ticket_handler, continent, age_bracket):
        super().__init__(timeout=300)
        self.bot = bot
        self.ticket_handler = ticket_handler
        self.continent = continent
        self.age_bracket = age_bracket

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.success, emoji="✅")
    async def confirm_age(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="📱 Number of Accounts",
            description="How many accounts would you like to join our clans with?",
            color=0x3498db
        )
        
        view = AccountNumberSelectionView(self.bot, self.ticket_handler, self.continent, self.age_bracket)
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="Reselect", style=discord.ButtonStyle.secondary, emoji="🔄")
    async def reselect_age(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="👶 Age Bracket Selection",
            description="Please select your age bracket:",
            color=0x3498db
        )
        
        view = AgeBracketSelectionView(self.bot, self.ticket_handler, self.continent)
        await interaction.response.edit_message(embed=embed, view=view)

class AccountNumberSelectionView(discord.ui.View):
    """View for selecting number of accounts"""
    
    def __init__(self, bot, ticket_handler, continent, age_bracket):
        super().__init__(timeout=300)
        self.bot = bot
        self.ticket_handler = ticket_handler
        self.continent = continent
        self.age_bracket = age_bracket

    @discord.ui.select(
        placeholder="Select number of accounts...",
        options=[
            discord.SelectOption(label="1 Account", value="1", emoji="1️⃣"),
            discord.SelectOption(label="2 Accounts", value="2", emoji="2️⃣"),
            discord.SelectOption(label="3 Accounts", value="3", emoji="3️⃣")
        ]
    )
    async def account_number_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        num_accounts = int(select.values[0])
        
        embed = discord.Embed(
            title="📱 Account Number Selected",
            description=f"Selected: **{num_accounts} Account(s)**\n\nNow let's get your player tags:",
            color=0x00ff00
        )
        
        view = PlayerTagInputView(self.bot, self.ticket_handler, self.continent, self.age_bracket, num_accounts)
        await interaction.response.edit_message(embed=embed, view=view)

class PlayerTagInputView(discord.ui.View):
    """View for inputting player tags"""
    
    def __init__(self, bot, ticket_handler, continent, age_bracket, num_accounts):
        super().__init__(timeout=300)
        self.bot = bot
        self.ticket_handler = ticket_handler
        self.continent = continent
        self.age_bracket = age_bracket
        self.num_accounts = num_accounts
        self.player_tags = []
        self.player_data = []
        self.current_account = 1

    @discord.ui.button(label="Start Tag Input", style=discord.ButtonStyle.primary, emoji="🏷️")
    async def start_tag_input(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title=f"🏷️ Account {self.current_account} - Player Tag",
            description=f"Please send the player tag for Account {self.current_account} in this channel:",
            color=0x3498db
        )
        embed.add_field(
            name="Format",
            value="Send the player tag (with or without #)\nExample: `#ABC123` or `ABC123`",
            inline=False
        )
        
        await interaction.response.edit_message(embed=embed, view=None)
        
        def check(m):
            return (m.author.id == interaction.user.id and 
                   m.channel.id == interaction.channel.id and 
                   m.content and not m.content.startswith('/'))

        try:
            msg = await self.bot.wait_for('message', check=check, timeout=120.0)
            player_tag = msg.content.replace("#", "").strip()
            
            if not player_tag:
                await interaction.followup.send("❌ Invalid player tag. Please try again.", ephemeral=True)
                return
            
            # Get player stats
            embed = discord.Embed(
                title="⏳ Fetching Player Stats...",
                description=f"Getting stats for {player_tag}...",
                color=0xffa500
            )
            status_msg = await interaction.followup.send(embed=embed, ephemeral=True)
            
            player_data = await self.ticket_handler.get_player_stats(player_tag)
            
            if not player_data:
                embed = discord.Embed(
                    title="❌ Error",
                    description=f"Could not fetch stats for tag `{player_tag}`. Please check the tag and try again.",
                    color=0xff0000
                )
                await status_msg.edit(embed=embed)
                return
            
            self.player_tags.append(player_tag)
            self.player_data.append(player_data)
            
            # Show stats
            stats_embed = self.ticket_handler.create_player_stats_embed(player_data, self.current_account)
            await status_msg.edit(embed=stats_embed)
            
            # Continue to next account or clan type selection
            if self.current_account < self.num_accounts:
                self.current_account += 1
                await self.continue_to_next_account(interaction)
            else:
                await self.proceed_to_clan_type_selection(interaction)
                
        except asyncio.TimeoutError:
            await interaction.followup.send("⏰ Timeout. Please restart the process.", ephemeral=True)

    async def continue_to_next_account(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title=f"🏷️ Account {self.current_account} - Player Tag",
            description=f"Please send the player tag for Account {self.current_account} in this channel:",
            color=0x3498db
        )
        embed.add_field(
            name="Format",
            value="Send the player tag (with or without #)\nExample: `#ABC123` or `ABC123`",
            inline=False
        )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
        def check(m):
            return (m.author.id == interaction.user.id and 
                   m.channel.id == interaction.channel.id and 
                   m.content and not m.content.startswith('/'))

        try:
            msg = await self.bot.wait_for('message', check=check, timeout=120.0)
            player_tag = msg.content.replace("#", "").strip()
            
            if not player_tag:
                await interaction.followup.send("❌ Invalid player tag. Please try again.", ephemeral=True)
                return
            
            # Get player stats
            embed = discord.Embed(
                title="⏳ Fetching Player Stats...",
                description=f"Getting stats for {player_tag}...",
                color=0xffa500
            )
            status_msg = await interaction.followup.send(embed=embed, ephemeral=True)
            
            player_data = await self.ticket_handler.get_player_stats(player_tag)
            
            if not player_data:
                embed = discord.Embed(
                    title="❌ Error",
                    description=f"Could not fetch stats for tag `{player_tag}`. Please check the tag and try again.",
                    color=0xff0000
                )
                await status_msg.edit(embed=embed)
                return
            
            self.player_tags.append(player_tag)
            self.player_data.append(player_data)
            
            # Show stats
            stats_embed = self.ticket_handler.create_player_stats_embed(player_data, self.current_account)
            await status_msg.edit(embed=stats_embed)
            
            # Continue to next account or clan type selection
            if self.current_account < self.num_accounts:
                self.current_account += 1
                await self.continue_to_next_account(interaction)
            else:
                await self.proceed_to_clan_type_selection(interaction)
                
        except asyncio.TimeoutError:
            await interaction.followup.send("⏰ Timeout. Please restart the process.", ephemeral=True)

    async def proceed_to_clan_type_selection(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🏰 Clan Type Selection",
            description="Now let's select clan types for each account:",
            color=0x3498db
        )
        
        view = ClanTypeSelectionView(self.bot, self.ticket_handler, self.continent, self.age_bracket, self.player_data)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

class ClanTypeSelectionView(discord.ui.View):
    """View for selecting clan types for each account"""
    
    def __init__(self, bot, ticket_handler, continent, age_bracket, player_data):
        super().__init__(timeout=300)
        self.bot = bot
        self.ticket_handler = ticket_handler
        self.continent = continent
        self.age_bracket = age_bracket
        self.player_data = player_data
        self.current_account = 1
        self.clan_types = []

    @discord.ui.select(
        placeholder="Select clan type for Account 1...",
        options=[
            discord.SelectOption(
                label="Regular Clans", 
                value="regular", 
                emoji="⚔️",
                description="Very strict about wars, events and raids"
            ),
            discord.SelectOption(
                label="Cruise Clans", 
                value="cruise", 
                emoji="🚢",
                description="Allow 2 hero down for wars and do competitive CWL and events"
            ),
            discord.SelectOption(
                label="FWA/GFL Farming Clans", 
                value="fwa", 
                emoji="🌾",
                description="Extremely chill with easy wars and lazy CWLS"
            )
        ]
    )
    async def clan_type_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        clan_type = select.values[0]
        self.clan_types.append(clan_type)
        
        if self.current_account < len(self.player_data):
            self.current_account += 1
            embed = discord.Embed(
                title=f"🏰 Clan Type for Account {self.current_account}",
                description=f"Account {self.current_account}: **{self.player_data[self.current_account-1].get('name', 'Unknown')}**\n\nSelect the clan type for this account:",
                color=0x3498db
            )
            
            # Update the select options for next account
            select.options = [
                discord.SelectOption(
                    label="Regular Clans", 
                    value="regular", 
                    emoji="⚔️",
                    description="Very strict about wars, events and raids"
                ),
                discord.SelectOption(
                    label="Cruise Clans", 
                    value="cruise", 
                    emoji="🚢",
                    description="Allow 2 hero down for wars and do competitive CWL and events"
                ),
                discord.SelectOption(
                    label="FWA/GFL Farming Clans", 
                    value="fwa", 
                    emoji="🌾",
                    description="Extremely chill with easy wars and lazy CWLS"
                )
            ]
            select.placeholder = f"Select clan type for Account {self.current_account}..."
            
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            # All accounts done, proceed to base screenshots
            await self.proceed_to_base_screenshots(interaction)

    async def proceed_to_base_screenshots(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📸 Base Screenshots Required",
            description="Now we need base screenshots for each account. Please send them one by one:",
            color=0x3498db
        )
        
        view = BaseScreenshotView(self.bot, self.ticket_handler, self.continent, self.age_bracket, self.player_data, self.clan_types)
        await interaction.response.edit_message(embed=embed, view=view)

class BaseScreenshotView(discord.ui.View):
    """View for collecting base screenshots"""
    
    def __init__(self, bot, ticket_handler, continent, age_bracket, player_data, clan_types):
        super().__init__(timeout=300)
        self.bot = bot
        self.ticket_handler = ticket_handler
        self.continent = continent
        self.age_bracket = age_bracket
        self.player_data = player_data
        self.clan_types = clan_types
        self.current_account = 1
        self.screenshots = []

    @discord.ui.button(label="Start Screenshot Collection", style=discord.ButtonStyle.primary, emoji="📸")
    async def start_screenshots(self, interaction: discord.Interaction, button: discord.ui.Button):
        player_name = self.player_data[self.current_account - 1].get('name', f'Account {self.current_account}')
        
        embed = discord.Embed(
            title=f"📸 Base Screenshot - Account {self.current_account}",
            description=f"Please send the base screenshot for **{player_name}** in this channel:",
            color=0x3498db
        )
        
        await interaction.response.edit_message(embed=embed, view=None)
        
        def check(m):
            return (m.author.id == interaction.user.id and 
                   m.channel.id == interaction.channel.id and 
                   m.attachments and 
                   m.attachments[0].content_type.startswith('image/'))

        try:
            msg = await self.bot.wait_for('message', check=check, timeout=120.0)
            screenshot_url = msg.attachments[0].url
            self.screenshots.append(screenshot_url)
            
            embed = discord.Embed(
                title="✅ Screenshot Received",
                description=f"Screenshot received for **{player_name}**",
                color=0x00ff00
            )
            embed.set_image(url=screenshot_url)
            await interaction.followup.send(embed=embed, ephemeral=True)
            
            if self.current_account < len(self.player_data):
                self.current_account += 1
                await self.continue_screenshots(interaction)
            else:
                await self.proceed_to_thread_creation(interaction)
                
        except asyncio.TimeoutError:
            await interaction.followup.send("⏰ Timeout. Please restart the process.", ephemeral=True)

    async def continue_screenshots(self, interaction: discord.Interaction):
        player_name = self.player_data[self.current_account - 1].get('name', f'Account {self.current_account}')
        
        embed = discord.Embed(
            title=f"📸 Base Screenshot - Account {self.current_account}",
            description=f"Please send the base screenshot for **{player_name}** in this channel:",
            color=0x3498db
        )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
        def check(m):
            return (m.author.id == interaction.user.id and 
                   m.channel.id == interaction.channel.id and 
                   m.attachments and 
                   m.attachments[0].content_type.startswith('image/'))

        try:
            msg = await self.bot.wait_for('message', check=check, timeout=120.0)
            screenshot_url = msg.attachments[0].url
            self.screenshots.append(screenshot_url)
            
            embed = discord.Embed(
                title="✅ Screenshot Received",
                description=f"Screenshot received for **{player_name}**",
                color=0x00ff00
            )
            embed.set_image(url=screenshot_url)
            await interaction.followup.send(embed=embed, ephemeral=True)
            
            if self.current_account < len(self.player_data):
                self.current_account += 1
                await self.continue_screenshots(interaction)
            else:
                await self.proceed_to_thread_creation(interaction)
                
        except asyncio.TimeoutError:
            await interaction.followup.send("⏰ Timeout. Please restart the process.", ephemeral=True)

    async def proceed_to_thread_creation(self, interaction: discord.Interaction):
        # Create private thread and continue with questions
        try:
            thread_name = f"join-clan-{interaction.user.name}-{datetime.now().strftime('%m%d')}"
            thread = await interaction.channel.create_thread(
                name=thread_name,
                type=discord.ChannelType.private_thread,
                reason="Join clan application thread"
            )
            
            # Send all player stats and screenshots to thread
            for i, (player_data, screenshot) in enumerate(zip(self.player_data, self.screenshots)):
                # Send player stats
                stats_embed = self.ticket_handler.create_player_stats_embed(player_data, i + 1)
                await thread.send(embed=stats_embed)
                
                # Send screenshot
                screenshot_embed = discord.Embed(
                    title=f"📸 Base Screenshot - Account {i + 1}",
                    color=0x3498db
                )
                screenshot_embed.set_image(url=screenshot)
                await thread.send(embed=screenshot_embed)
            
            # Now continue with questions in main channel
            embed = discord.Embed(
                title="✅ Thread Created",
                description=f"Private thread created: {thread.mention}\n\nNow let's continue with the application questions:",
                color=0x00ff00
            )
            
            view = ApplicationQuestionsView(self.bot, self.ticket_handler, self.continent, self.age_bracket, self.player_data, self.clan_types, thread)
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            embed = discord.Embed(
                title="❌ Error",
                description=f"Failed to create thread: {str(e)}",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

class ApplicationQuestionsView(discord.ui.View):
    """View for handling application questions"""
    
    def __init__(self, bot, ticket_handler, continent, age_bracket, player_data, clan_types, thread):
        super().__init__(timeout=300)
        self.bot = bot
        self.ticket_handler = ticket_handler
        self.continent = continent
        self.age_bracket = age_bracket
        self.player_data = player_data
        self.clan_types = clan_types
        self.thread = thread

    @discord.ui.button(label="Start Questions", style=discord.ButtonStyle.primary, emoji="❓")
    async def start_questions(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Get questions from database
        questions = await self.ticket_handler.mongo.get_ticket_questions("join_clan", interaction.guild.id)
        
        if not questions:
            # Use default questions if none configured
            questions = [
                "Why do you want to join Blackspire Nation?",
                "What is your experience with Clash of Clans?",
                "How active are you in wars and events?",
                "Do you have any questions for us?"
            ]
        
        # Start the question flow
        await self.ask_questions(interaction, questions, 0, [])

    async def ask_questions(self, interaction: discord.Interaction, questions: list, current_index: int, answers: list):
        if current_index >= len(questions):
            # All questions answered, proceed to clan selection
            await self.proceed_to_clan_selection(interaction, answers)
            return
        
        question = questions[current_index]
        embed = discord.Embed(
            title=f"❓ Question {current_index + 1}/{len(questions)}",
            description=question,
            color=0x3498db
        )
        
        await interaction.response.edit_message(embed=embed, view=None)
        
        def check(m):
            return (m.author.id == interaction.user.id and 
                   m.channel.id == interaction.channel.id and 
                   m.content and not m.content.startswith('/'))

        try:
            msg = await self.bot.wait_for('message', check=check, timeout=300.0)
            answer = msg.content
            answers.append(answer)
            
            embed = discord.Embed(
                title="✅ Answer Received",
                description=f"**Question {current_index + 1}:** {question}\n\n**Answer:** {answer}",
                color=0x00ff00
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            
            # Continue to next question
            if current_index + 1 < len(questions):
                next_embed = discord.Embed(
                    title=f"❓ Question {current_index + 2}/{len(questions)}",
                    description=questions[current_index + 1],
                    color=0x3498db
                )
                await interaction.followup.send(embed=next_embed, ephemeral=True)
                await self.ask_questions(interaction, questions, current_index + 1, answers)
            else:
                await self.proceed_to_clan_selection(interaction, answers)
                
        except asyncio.TimeoutError:
            await interaction.followup.send("⏰ Timeout. Please restart the process.", ephemeral=True)

    async def proceed_to_clan_selection(self, interaction: discord.Interaction, answers: list):
        # Send summary to thread
        summary_embed = discord.Embed(
            title="📋 Application Summary",
            description="**Application Details:**",
            color=0x3498db
        )
        summary_embed.add_field(name="Continent", value=self.continent, inline=True)
        summary_embed.add_field(name="Age Bracket", value=self.age_bracket, inline=True)
        summary_embed.add_field(name="Number of Accounts", value=str(len(self.player_data)), inline=True)
        
        # Add answers
        for i, answer in enumerate(answers):
            summary_embed.add_field(
                name=f"Answer {i + 1}",
                value=answer[:1000],  # Discord limit
                inline=False
            )
        
        await self.thread.send(embed=summary_embed)
        
        # Now proceed to clan selection for each account
        embed = discord.Embed(
            title="🏰 Clan Selection",
            description="Now let's select clans for each account based on your preferences and Town Hall levels:",
            color=0x3498db
        )
        
        view = ClanSelectionView(self.bot, self.ticket_handler, self.continent, self.age_bracket, self.player_data, self.clan_types, self.thread)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

class ClanSelectionView(discord.ui.View):
    """View for selecting clans for each account"""
    
    def __init__(self, bot, ticket_handler, continent, age_bracket, player_data, clan_types, thread):
        super().__init__(timeout=300)
        self.bot = bot
        self.ticket_handler = ticket_handler
        self.continent = continent
        self.age_bracket = age_bracket
        self.player_data = player_data
        self.clan_types = clan_types
        self.thread = thread
        self.current_account = 1
        self.selected_clans = []

    @discord.ui.button(label="Start Clan Selection", style=discord.ButtonStyle.primary, emoji="🏰")
    async def start_clan_selection(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.select_clan_for_account(interaction)

    async def select_clan_for_account(self, interaction: discord.Interaction):
        player_data = self.player_data[self.current_account - 1]
        clan_type = self.clan_types[self.current_account - 1]
        player_name = player_data.get('name', f'Account {self.current_account}')
        th_level = player_data.get('town_hall_level', 0)
        
        # Get clans that match the criteria
        available_clans = await self.ticket_handler.mongo.get_clans_by_type_and_th(clan_type, th_level, interaction.guild.id)
        
        if not available_clans:
            embed = discord.Embed(
                title="❌ No Available Clans",
                description=f"No clans found for **{clan_type.title()}** type with minimum TH level {th_level}",
                color=0xff0000
            )
            await interaction.response.edit_message(embed=embed, view=None)
            return
        
        options = []
        for clan in available_clans[:25]:  # Discord limit
            options.append(discord.SelectOption(
                label=clan.get('name', 'Unknown'),
                description=f"Min TH: {clan.get('min_town_hall', 'N/A')} • Type: {clan.get('clan_type', 'Unknown')}",
                value=str(clan.get('_id', ''))
            ))
        
        select = discord.ui.Select(
            placeholder=f"Select clan for {player_name} ({clan_type.title()})...",
            options=options,
            min_values=1,
            max_values=1
        )
        select.callback = self.clan_selected

        view = discord.ui.View(timeout=300)
        view.add_item(select)
        
        embed = discord.Embed(
            title=f"🏰 Clan Selection - Account {self.current_account}",
            description=f"**Player:** {player_name} (TH{th_level})\n**Clan Type:** {clan_type.title()}\n\nSelect a clan:",
            color=0x3498db
        )
        
        await interaction.response.edit_message(embed=embed, view=view)

    async def clan_selected(self, interaction: discord.Interaction):
        clan_id = interaction.data["values"][0]
        clan = await self.ticket_handler.mongo.get_clan_by_id(clan_id)
        
        if not clan:
            await interaction.response.send_message("❌ Clan not found!", ephemeral=True)
            return
        
        self.selected_clans.append(clan)
        
        if self.current_account < len(self.player_data):
            self.current_account += 1
            await self.select_clan_for_account(interaction)
        else:
            await self.proceed_to_final_confirmation(interaction)

    async def proceed_to_final_confirmation(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="✅ Final Confirmation",
            description="Please review your clan selections:",
            color=0x00ff00
        )
        
        for i, (player_data, clan) in enumerate(zip(self.player_data, self.selected_clans)):
            embed.add_field(
                name=f"Account {i + 1}: {player_data.get('name', 'Unknown')}",
                value=f"Selected: **{clan.get('name', 'Unknown')}**",
                inline=False
            )
        
        view = FinalConfirmationView(self.bot, self.ticket_handler, self.continent, self.age_bracket, self.player_data, self.clan_types, self.thread, self.selected_clans)
        await interaction.response.edit_message(embed=embed, view=view)

class FinalConfirmationView(discord.ui.View):
    """View for final confirmation and clan invitation"""
    
    def __init__(self, bot, ticket_handler, continent, age_bracket, player_data, clan_types, thread, selected_clans):
        super().__init__(timeout=300)
        self.bot = bot
        self.ticket_handler = ticket_handler
        self.continent = continent
        self.age_bracket = age_bracket
        self.player_data = player_data
        self.clan_types = clan_types
        self.thread = thread
        self.selected_clans = selected_clans

    @discord.ui.button(label="Confirm & Submit", style=discord.ButtonStyle.success, emoji="✅")
    async def confirm_application(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Send application to thread with staff mentions
        embed = discord.Embed(
            title="🎯 NEW CLAN APPLICATION",
            description="A new clan application has been submitted!",
            color=0x00ff00
        )
        
        # Get staff roles for join_clan ticket
        staff_list = await self.ticket_handler.mongo.get_ticket_staff("join_clan", interaction.guild.id)
        
        mentions = []
        for staff in staff_list:
            if 'user_id' in staff:
                mentions.append(f"<@{staff['user_id']}>")
            elif 'role_id' in staff:
                mentions.append(f"<@&{staff['role_id']}>")
        
        # Add clan leadership mentions
        for clan in self.selected_clans:
            if 'leadership_role_id' in clan:
                mentions.append(f"<@&{clan['leadership_role_id']}>")
            if 'leader_id' in clan:
                mentions.append(f"<@{clan['leader_id']}>")
        
        if mentions:
            await self.thread.send(" ".join(mentions))
        
        await self.thread.send(embed=embed)
        
        # Send detailed application info
        for i, (player_data, clan) in enumerate(zip(self.player_data, self.selected_clans)):
            app_embed = discord.Embed(
                title=f"📋 Account {i + 1} Application",
                color=0x3498db
            )
            app_embed.add_field(name="Player", value=player_data.get('name', 'Unknown'), inline=True)
            app_embed.add_field(name="Tag", value=player_data.get('tag', 'Unknown'), inline=True)
            app_embed.add_field(name="Town Hall", value=str(player_data.get('town_hall_level', 0)), inline=True)
            app_embed.add_field(name="Selected Clan", value=clan.get('name', 'Unknown'), inline=True)
            app_embed.add_field(name="Clan Type", value=clan.get('clan_type', 'Unknown').title(), inline=True)
            app_embed.add_field(name="Min TH Required", value=str(clan.get('min_town_hall', 'N/A')), inline=True)
            
            await self.thread.send(embed=app_embed)
        
        # Create clan acceptance/rejection view
        view = ClanDecisionView(self.bot, self.ticket_handler, self.player_data, self.selected_clans, interaction.user)
        await self.thread.send("**Staff Decision Required:**", view=view)
        
        # Confirm in main channel
        embed = discord.Embed(
            title="✅ Application Submitted",
            description=f"Your application has been submitted successfully!\n\nThread: {self.thread.mention}\n\nStaff will review your application and get back to you soon.",
            color=0x00ff00
        )
        await interaction.response.edit_message(embed=embed, view=None)

class ClanDecisionView(discord.ui.View):
    """View for staff to accept/reject clan applications"""
    
    def __init__(self, bot, ticket_handler, player_data, selected_clans, applicant):
        super().__init__(timeout=None)  # Persistent view
        self.bot = bot
        self.ticket_handler = ticket_handler
        self.player_data = player_data
        self.selected_clans = selected_clans
        self.applicant = applicant

    @discord.ui.button(label="Accept Player", style=discord.ButtonStyle.success, emoji="✅")
    async def accept_player(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Check if user has permission to accept for any of the selected clans
        user_roles = [role.id for role in interaction.user.roles]
        has_permission = False
        
        for clan in self.selected_clans:
            if (clan.get('leader_id') == interaction.user.id or 
                clan.get('leadership_role_id') in user_roles):
                has_permission = True
                break
        
        if not has_permission:
            embed = discord.Embed(
                title="❌ Permission Denied",
                description="You don't have permission to accept this application.",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Create clan invitation embeds
        for i, (player_data, clan) in enumerate(zip(self.player_data, self.selected_clans)):
            invite_embed = discord.Embed(
                title=f"🏰 Clan Invitation for {player_data.get('name', 'Unknown')}",
                description=f"**{clan.get('name', 'Unknown')} Clan Invitation**",
                color=0x00ff00
            )
            
            invite_embed.add_field(
                name="Welcome Message",
                value=(
                    f"WELCOME TO **{clan.get('name', 'Unknown')}**\n"
                    f"LED BY <@{clan.get('leader_id', 'Unknown')}> & <@&{clan.get('leadership_role_id', 'Unknown')}>\n\n"
                    f"**BSN Family Rules:**\n"
                    f"• Reapply anytime - If you're not happy with your clan, you're free to apply again\n"
                    f"• Use BSN FAM in join requests - it helps during recruitment\n"
                    f"• CWL flexibility - you can shift between clans for better matches\n"
                    f"• One big family - all BSN clans support each other!"
                ),
                inline=False
            )
            
            invite_embed.add_field(
                name="Invited By",
                value=interaction.user.mention,
                inline=True
            )
            
            if clan.get('icon_url'):
                invite_embed.set_thumbnail(url=clan['icon_url'])
            
            invite_embed.set_footer(text="Blackspire Nation • Welcome to the family!")
            
            # Add clan invite button
            view = discord.ui.View()
            if clan.get('invite_link'):
                button = discord.ui.Button(
                    label=f"Join {clan.get('name', 'Unknown')}",
                    url=clan['invite_link'],
                    style=discord.ButtonStyle.link,
                    emoji="🚀"
                )
                view.add_item(button)
            
            await self.thread.send(embed=invite_embed, view=view)
        
        embed = discord.Embed(
            title="✅ Player Accepted",
            description=f"Application accepted by {interaction.user.mention}",
            color=0x00ff00
        )
        await interaction.response.edit_message(embed=embed, view=None)

    @discord.ui.button(label="Pass On Player", style=discord.ButtonStyle.danger, emoji="❌")
    async def reject_player(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Check if user has permission to reject for any of the selected clans
        user_roles = [role.id for role in interaction.user.roles]
        has_permission = False
        
        for clan in self.selected_clans:
            if (clan.get('leader_id') == interaction.user.id or 
                clan.get('leadership_role_id') in user_roles):
                has_permission = True
                break
        
        if not has_permission:
            embed = discord.Embed(
                title="❌ Permission Denied",
                description="You don't have permission to reject this application.",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        embed = discord.Embed(
            title="❌ Application Passed On",
            description=(
                f"We're sorry, but we've decided to pass on your application at this time.\n\n"
                f"This doesn't mean you can't apply again in the future!\n"
                f"Feel free to reapply anytime when you feel ready.\n\n"
                f"Thank you for your interest in Blackspire Nation."
            ),
            color=0xff6600
        )
        embed.set_footer(text="Decision made by staff")
        
        await interaction.response.edit_message(embed=embed, view=None)