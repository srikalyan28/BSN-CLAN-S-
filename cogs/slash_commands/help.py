import discord
from discord.ext import commands
from discord import app_commands

class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.mongo = bot.mongo_manager

    @app_commands.command(name="help", description="❓ Get help with bot commands and features")
    async def help_command(self, interaction: discord.Interaction):
        """Show help information"""
        embed = discord.Embed(
            title="❓ Blackspire Nation Bot Help",
            description="Welcome to the Blackspire Nation Discord Bot! Here are the available commands and features:",
            color=0x0099ff,
            timestamp=discord.utils.utcnow()
        )

        embed.add_field(
            name="🎫 Ticket System",
            value="`/main_dashboard` - Manage all ticket panels and configurations\n`/add_to_ticket` - Add members/roles to ticket channels\n`/reject_player` - Reject player applications (Staff Only)",
            inline=False
        )

        embed.add_field(
            name="⚔️ Clan Management", 
            value="`/clan_dashboard` - Add/edit clan data and requirements",
            inline=False
        )

        embed.add_field(
            name="🚀 Booster Features",
            value="`/booster_dashboard` - Manage color roles and booster panels",
            inline=False
        )

        embed.add_field(
            name="🔢 Counting System",
            value="`/setup_counting` - Enable counting in a channel\n`/disable_counting` - Disable counting system",
            inline=False
        )

        embed.add_field(
            name="🔐 Admin Panel",
            value="`/admin_dashboard` - Manage permissions and access (Owner Only)",
            inline=False
        )

        embed.set_footer(text="Blackspire Nation • For support, contact the staff team")
        embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else None)

        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Help(bot))
