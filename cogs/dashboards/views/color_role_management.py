import discord
from discord.ext import commands
from typing import List
import re
from .view_protocols import BoosterViews

class ColorRoleManagementView(discord.ui.View):
    def __init__(self, bot, parent_view: BoosterViews = None):
        super().__init__(timeout=300)
        self.bot = bot
        self.mongo = bot.mongo_manager
        self.parent_view = parent_view
    def __init__(self, bot):
        super().__init__(timeout=300)
        self.bot = bot
        self.mongo = bot.mongo_manager

    @discord.ui.button(label="Add Color Role", style=discord.ButtonStyle.primary, emoji="➕", row=0)
    async def add_color_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Create modal for color role input
        await interaction.response.send_modal(AddColorRoleModal(self.bot))

    @discord.ui.button(label="View Color Roles", style=discord.ButtonStyle.secondary, emoji="👁️", row=0)
    async def view_color_roles(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Get all color roles
        color_roles = await self.mongo.get_color_roles(interaction.guild.id)
        
        if not color_roles:
            embed = discord.Embed(
                title="🎨 Color Roles",
                description="No color roles have been configured yet.",
                color=0xffa500
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Create embed to display color roles
        embed = discord.Embed(
            title="🎨 Color Roles",
            description="Here are all the available color roles:",
            color=0x9932cc
        )

        for role in color_roles:
            role_obj = interaction.guild.get_role(role['role_id'])
            if role_obj:
                embed.add_field(
                    name=role_obj.name,
                    value=f"Color: {role['color_hex']}\nID: {role['role_id']}",
                    inline=True
                )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Remove Color Role", style=discord.ButtonStyle.danger, emoji="🗑️", row=1)
    async def remove_color_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Get all color roles
        color_roles = await self.mongo.get_color_roles(interaction.guild.id)
        
        if not color_roles:
            embed = discord.Embed(
                title="🎨 Remove Color Role",
                description="No color roles have been configured yet.",
                color=0xffa500
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Create select menu for role removal
        options = []
        for role in color_roles:
            role_obj = interaction.guild.get_role(role['role_id'])
            if role_obj:
                options.append(
                    discord.SelectOption(
                        label=role_obj.name,
                        value=str(role['role_id']),
                        description=f"Color: {role['color_hex']}"
                    )
                )

        if not options:
            embed = discord.Embed(
                title="🎨 Remove Color Role",
                description="No valid color roles found.",
                color=0xffa500
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        view = RemoveColorRoleView(self.bot, options)
        embed = discord.Embed(
            title="🎨 Remove Color Role",
            description="Select a color role to remove:",
            color=0x9932cc
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="Back", style=discord.ButtonStyle.secondary, emoji="⬅️", row=2)
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.parent_view:
            await self.parent_view.show_main_dashboard(interaction)

class AddColorRoleModal(discord.ui.Modal, title="Add Color Role"):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        self.mongo = bot.mongo_manager

    role = discord.ui.TextInput(
        label="Role Mention/ID",
        placeholder="Mention the role or enter its ID",
        required=True
    )

    color = discord.ui.TextInput(
        label="Color Hex Code",
        placeholder="Enter the color hex code (e.g., #ff0000)",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Get role ID from mention or ID
            role_input = self.role.value.strip()
            if role_input.startswith('<@&') and role_input.endswith('>'):
                role_id = int(role_input[3:-1])
            else:
                role_id = int(role_input)

            # Verify role exists
            role = interaction.guild.get_role(role_id)
            if not role:
                raise ValueError("Role not found")

            # Validate and format color hex
            color_hex = self.color.value.strip()
            if not color_hex.startswith('#'):
                color_hex = f"#{color_hex}"
            if not all(c in '0123456789ABCDEFabcdef#' for c in color_hex):
                raise ValueError("Invalid color hex code")

            # Add to database
            success = await self.mongo.add_color_role(
                guild_id=interaction.guild.id,
                role_id=role_id,
                color_hex=color_hex
            )

            if success:
                embed = discord.Embed(
                    title="✅ Color Role Added",
                    description=f"Successfully added {role.mention} with color {color_hex}",
                    color=0x00ff00
                )
            else:
                embed = discord.Embed(
                    title="❌ Error",
                    description="Failed to add color role. Please try again.",
                    color=0xff0000
                )

            await interaction.response.send_message(embed=embed, ephemeral=True)

        except ValueError as e:
            embed = discord.Embed(
                title="❌ Invalid Input",
                description=str(e),
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

class RemoveColorRoleView(discord.ui.View):
    def __init__(self, bot, options):
        super().__init__(timeout=300)
        self.bot = bot
        self.mongo = bot.mongo_manager
        
        # Add select menu
        select_menu = discord.ui.Select(
            placeholder="Choose a color role to remove",
            options=options,
            min_values=1,
            max_values=1
        )
        select_menu.callback = self.role_selected
        self.add_item(select_menu)

    async def role_selected(self, interaction: discord.Interaction):
        role_id = int(interaction.data['values'][0])
        success = await self.mongo.remove_color_role(
            guild_id=interaction.guild.id,
            role_id=role_id
        )

        if success:
            embed = discord.Embed(
                title="✅ Color Role Removed",
                description=f"Successfully removed the color role.",
                color=0x00ff00
            )
        else:
            embed = discord.Embed(
                title="❌ Error",
                description="Failed to remove color role. Please try again.",
                color=0xff0000
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)