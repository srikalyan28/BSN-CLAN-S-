import discord
from discord.ext import commands
from discord import app_commands
import os

class SetupCounting(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.mongo = bot.mongo_manager

    def is_bot_owner(self, user_id: int) -> bool:
        """Check if user is bot owner"""
        return user_id == int(os.getenv('BOT_OWNER_ID'))

    @app_commands.command(name="setup_counting", description="🔢 Setup counting system in this channel (Owner Only)")
    async def setup_counting(self, interaction: discord.Interaction):
        """Setup counting in the current channel"""
        try:
            # Check if user is bot owner
            if not self.is_bot_owner(interaction.user.id):
                # Check database permissions
                user_roles = [role.id for role in interaction.user.roles]
                has_permission = await self.mongo.check_command_permission(
                    "setup_counting",
                    interaction.user.id,
                    user_roles,
                    interaction.guild_id
                )

                if not has_permission:
                    embed = discord.Embed(
                        title="❌ Access Denied",
                        description="You don't have permission to use this command.",
                        color=0xff0000
                    )
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    return

            # Check if counting is already enabled
            existing_data = await self.mongo.get_counting_data(interaction.guild.id)
            if existing_data and existing_data.get('enabled'):
                embed = discord.Embed(
                    title="⚠️ Channel Already Setup",
                    description=f"Counting is already enabled in <#{existing_data['channel_id']}>.",
                    color=0xffa500
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Setup counting in this channel
            success = await self.mongo.setup_counting(
                guild_id=interaction.guild.id,
                channel_id=interaction.channel.id
            )

            if success:
                embed = discord.Embed(
                    title="🔢 Counting Setup Complete!",
                    description=(
                        f"Counting has been enabled in {interaction.channel.mention}\n\n"
                        "**Rules:**\n"
                        "1️⃣ Only numbers are allowed\n"
                        "2️⃣ Start counting from 1\n"
                        "3️⃣ No back-to-back counting from the same user\n"
                        "4️⃣ Keep the sequence correct\n\n"
                        "The next number should be: **1**"
                    ),
                    color=0x00ff00,
                    timestamp=discord.utils.utcnow()
                )
                embed.set_footer(text="Blackspire Nation Counting System")
                await interaction.response.send_message(embed=embed)
            
            if success:
                embed = discord.Embed(
                    title="🔢 Counting Setup Complete!",
                    description=(
                        f"Counting has been enabled in {interaction.channel.mention}\n\n"
                        "**Rules:**\n"
                        "1️⃣ Only numbers are allowed\n"
                        "2️⃣ Start counting from 1\n"
                        "3️⃣ No back-to-back counting from the same user\n"
                        "4️⃣ Keep the sequence correct\n\n"
                        "The next number should be: **1**"
                    ),
                    color=0x00ff00,
                    timestamp=discord.utils.utcnow()
                )
                embed.set_footer(text="Blackspire Nation Counting System")
                await interaction.response.send_message(embed=embed)
            else:
                embed = discord.Embed(
                    title="❌ Setup Failed",
                    description="Failed to setup counting system. Please try again.",
                    color=0xff0000
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                
        except Exception as e:
            embed = discord.Embed(
                title="❌ Error",
                description=f"An error occurred: {str(e)}",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(SetupCounting(bot))
