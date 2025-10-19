import discord
from discord.ext import commands
from discord import app_commands
import os

class DisableCounting(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.mongo = bot.mongo_manager

    def is_bot_owner(self, user_id: int) -> bool:
        """Check if user is bot owner"""
        return user_id == int(os.getenv('BOT_OWNER_ID'))

    @app_commands.command(name="disable_counting", description="❌ Disable counting system in this channel (Owner Only)")
    async def disable_counting(self, interaction: discord.Interaction):
        """Disable counting in the current channel"""
        try:
            # Check permissions
            if not self.is_bot_owner(interaction.user.id):
                user_roles = [role.id for role in interaction.user.roles]
                has_permission = await self.mongo.check_command_permission(
                    "disable_counting", 
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

            # Check if counting exists in this guild
            counting_data = await self.mongo.get_counting_data(interaction.guild.id)
            if not counting_data or not counting_data.get('enabled'):
                embed = discord.Embed(
                    title="❌ Not Found",
                    description="Counting is not enabled in this server.",
                    color=0xff0000
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Disable counting in this guild
            success = await self.mongo.disable_counting(
                guild_id=interaction.guild.id,
                channel_id=interaction.channel.id
            )

            if success:
                embed = discord.Embed(
                    title="❌ Counting Disabled",
                    description=f"Counting has been disabled in {interaction.channel.mention}",
                    color=0xff6600,
                    timestamp=discord.utils.utcnow()
                )
                embed.set_footer(text="Blackspire Nation Counting System")
                await interaction.response.send_message(embed=embed)
            else:
                embed = discord.Embed(
                    title="❌ Error",
                    description="Failed to disable counting. Please try again.",
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
    await bot.add_cog(DisableCounting(bot))
