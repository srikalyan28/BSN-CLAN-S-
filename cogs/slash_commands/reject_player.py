import discord
from discord.ext import commands
from discord import app_commands

class RejectPlayer(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.mongo = bot.mongo_manager

    @app_commands.command(name="reject_player", description="🚫 Politely reject a player application")
    async def reject_player(self, interaction: discord.Interaction, player: discord.Member, reason: str = None):
        """Reject a player application"""
        # Check permissions
        user_roles = [role.id for role in interaction.user.roles]
        has_permission = await self.mongo.check_command_permission(
            command_name="reject_player",
            user_id=interaction.user.id,
            user_roles=user_roles,
            guild_id=interaction.guild_id
        )

        if not has_permission:
            embed = discord.Embed(
                title="❌ Access Denied",
                description="You don't have permission to use this command.",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if not player:
            embed = discord.Embed(
                title="❌ Invalid Usage",
                description="Please mention a player to reject.",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Create rejection embed
        embed = discord.Embed(
            title="🚫 Application Update",
            description=f"Dear {player.mention},\n\nThank you for your interest in joining Blackspire Nation. After careful review of your application, we regret to inform you that we cannot proceed with your application at this time.",
            color=0xff0000,
            timestamp=discord.utils.utcnow()
        )

        if reason:
            embed.add_field(
                name="📋 Feedback",
                value=reason,
                inline=False
            )

        embed.add_field(
            name="🔄 Reapplication",
            value="You are welcome to reapply in the future. We encourage you to continue improving and try again later.",
            inline=False
        )

        embed.set_footer(text="Blackspire Nation Staff Team")
        embed.set_image(url="https://cdn.discordapp.com/attachments/placeholder/reject_hammer.png")  # Red ban hammer image

        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(RejectPlayer(bot))
