import discord
from discord.ext import commands
from discord import app_commands

class AddToTicket(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.mongo = bot.mongo_manager

    @app_commands.command(name="add_to_ticket", description="➕ Add user/role to ticket channel with permissions")
    async def add_to_ticket(self, interaction: discord.Interaction, target: discord.Member = None, role: discord.Role = None):
        """Add user or role to ticket channel"""
        # Check permissions
        user_roles = [role.id for role in interaction.user.roles]
        has_permission = await self.mongo.check_command_permission(
            command_name="add_to_ticket",
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

        if not target and not role:
            embed = discord.Embed(
                title="❌ Invalid Usage",
                description="Please mention a user or role to add to this channel.",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        try:
            # Get current channel overwrites
            overwrites = dict(interaction.channel.overwrites)
            
            # Keep default role overwrite if it exists, or add it if it doesn't
            if interaction.guild.default_role not in overwrites:
                overwrites[interaction.guild.default_role] = discord.PermissionOverwrite(read_messages=False)

            # Add new permissions while keeping existing ones
            if target:
                # Add or update target member permissions
                overwrites[target] = discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    view_channel=True
                )
                added_entity = target.mention
                entity_type = "User"
            else:
                # Add or update role permissions
                overwrites[role] = discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    view_channel=True
                )
                added_entity = role.mention
                entity_type = "Role"

            # Apply the updated overwrites
            await interaction.channel.edit(overwrites=overwrites)

            embed = discord.Embed(
                title="✅ Successfully Added",
                description=f"{entity_type} {added_entity} has been added to this channel with view and message permissions.",
                color=0x00ff00,
                timestamp=discord.utils.utcnow()
            )
            embed.set_footer(text="Blackspire Nation Ticket System")

            await interaction.response.send_message(embed=embed)

        except discord.Forbidden:
            embed = discord.Embed(
                title="❌ Permission Error",
                description="I don't have permission to modify this channel.",
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
    await bot.add_cog(AddToTicket(bot))
