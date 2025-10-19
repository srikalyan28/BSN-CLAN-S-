import discord
from discord.ext import commands
import asyncio
from typing import Dict, Set, Optional

class CountingSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.mongo = bot.mongo_manager
        # Cache for counting channels to reduce DB queries
        self.counting_channels = {}  # guild_id -> set of channel_ids
        self.channel_counts = {}  # channel_id -> current_count
        self.last_counters = {}  # channel_id -> last_counter_id
        # Initialize cache
        asyncio.create_task(self._initialize_cache())

    async def _initialize_cache(self):
        """Initialize the counting channels cache"""
        try:
            for guild in self.bot.guilds:
                channels = await self.mongo.get_guild_counting_channels(guild.id)
                self.counting_channels[guild.id] = {
                    channel['channel_id'] for channel in channels
                }
                for channel in channels:
                    self.channel_counts[channel['channel_id']] = channel['current_count']
                    self.last_counters[channel['channel_id']] = channel.get('last_counter')
            print("Counting system cache initialized successfully")
        except Exception as e:
            print(f"Error initializing counting cache: {str(e)}")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Handle counting messages"""
        if message.author.bot or not message.guild:
            return

        # Quick check using cache
        if message.guild.id not in self.counting_channels or \
           message.channel.id not in self.counting_channels[message.guild.id]:
            return

        try:
            # Try to convert message to number
            try:
                number = int(message.content.strip())
            except ValueError:
                return

            # Get settings
            settings = await self.mongo.get_counting_settings(message.guild.id)
            if not settings.get('enabled', True):
                return

            current_count = self.channel_counts.get(message.channel.id, 0)
            last_counter = self.last_counters.get(message.channel.id)

            # Check if count is correct
            if number != current_count + 1:
                if settings.get('reset_on_wrong', True):
                    await self.mongo.reset_count(message.channel.id)
                    self.channel_counts[message.channel.id] = 0
                    self.last_counters[message.channel.id] = None
                    await message.add_reaction('❌')
                    await message.reply(f"❌ Wrong number! The count has been reset to 0. The next number should be 1.")
                else:
                    await message.add_reaction('❌')
                    await message.reply(f"❌ Wrong number! The next number should be {current_count + 1}.")
                return

            # Check double counting
            if not settings.get('allow_double_counting', False) and last_counter == message.author.id:
                if settings.get('reset_on_wrong', True):
                    await self.mongo.reset_count(message.channel.id)
                    self.channel_counts[message.channel.id] = 0
                    self.last_counters[message.channel.id] = None
                    await message.add_reaction('❌')
                    await message.reply(f"❌ You can't count twice in a row! The count has been reset to 0.")
                else:
                    await message.add_reaction('❌')
                    await message.reply(f"❌ You can't count twice in a row! Wait for someone else to continue.")
                return

            # Update count in cache and database
            self.channel_counts[message.channel.id] = number
            self.last_counters[message.channel.id] = message.author.id
            await self.mongo.update_count(message.channel.id, number, message.author.id)

            # Add success reaction
            await message.add_reaction('✅')

            # Check milestones
            milestones = settings.get('milestones', [100, 500, 1000, 5000, 10000])
            if number in milestones:
                for reaction in ['🎉', '🎊', '🥳']:
                    await message.add_reaction(reaction)
                await message.reply(f"🎉 Congratulations! You've reached {number}!")

        except Exception as e:
            print(f"Error in counting system: {str(e)}")

    @commands.command(name="countingstats")
    async def counting_stats(self, ctx):
        """Show counting statistics for the current channel"""
        if not ctx.guild:
            return

        try:
            if ctx.channel.id not in self.channel_counts:
                await ctx.reply("This is not a counting channel!")
                return

            embed = discord.Embed(
                title="📊 Counting Statistics",
                color=discord.Color.blue()
            )

            current_count = self.channel_counts.get(ctx.channel.id, 0)
            embed.add_field(
                name="Current Count",
                value=str(current_count),
                inline=True
            )

            last_counter_id = self.last_counters.get(ctx.channel.id)
            if last_counter_id:
                last_counter = ctx.guild.get_member(last_counter_id)
                embed.add_field(
                    name="Last Counter",
                    value=last_counter.mention if last_counter else "Unknown User",
                    inline=True
                )

            settings = await self.mongo.get_counting_settings(ctx.guild.id)
            features = []
            if settings.get('allow_double_counting'):
                features.append("Double counting allowed")
            if settings.get('reset_on_wrong'):
                features.append("Resets on wrong number")

            if features:
                embed.add_field(
                    name="Features",
                    value="\n".join(f"• {feature}" for feature in features),
                    inline=False
                )

            next_milestones = [m for m in settings.get('milestones', []) if m > current_count]
            if next_milestones:
                embed.add_field(
                    name="Next Milestone",
                    value=str(next_milestones[0]),
                    inline=True
                )

            await ctx.reply(embed=embed)

        except Exception as e:
            print(f"Error showing counting stats: {str(e)}")
            await ctx.reply("An error occurred while getting counting statistics.")

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        """Initialize cache for new guild"""
        channels = await self.mongo.get_guild_counting_channels(guild.id)
        self.counting_channels[guild.id] = {
            channel['channel_id'] for channel in channels
        }
        for channel in channels:
            self.channel_counts[channel['channel_id']] = channel['current_count']
            self.last_counters[channel['channel_id']] = channel.get('last_counter')

async def setup(bot):
    await bot.add_cog(CountingSystem(bot))