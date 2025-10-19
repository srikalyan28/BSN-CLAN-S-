import discord
from discord.ext import commands
from typing import List, Optional

class BoosterRoleManagementView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=300)
        self.bot = bot
        self.mongo = bot.mongo_manager

    @discord.ui.button(label="Add Booster Role", style=discord.ButtonStyle.primary, emoji="➕", row=0)
    async def add_booster_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AddBoosterRoleModal(self.bot))

    @discord.ui.button(label="View Booster Roles", style=discord.ButtonStyle.secondary, emoji="👁️", row=0)
    async def view_booster_roles(self, interaction: discord.Interaction, button: discord.ui.Button):
        booster_roles = await self.mongo.get_booster_roles(interaction.guild.id)
        
        if not booster_roles:
            embed = discord.Embed(
                title="🚀 Booster Roles",
                description="No booster roles have been configured yet.",
                color=0xffa500
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        embed = discord.Embed(
            title="🚀 Booster Roles",
            description="Here are all the configured booster roles:",
            color=0x9932cc
        )

        for role in booster_roles:
            role_obj = interaction.guild.get_role(role['role_id'])
            if role_obj:
                embed.add_field(
                    name=role_obj.name,
                    value=f"Description: {role['description']}\nID: {role['role_id']}",
                    inline=True
                )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Remove Booster Role", style=discord.ButtonStyle.danger, emoji="🗑️", row=1)
    async def remove_booster_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        booster_roles = await self.mongo.get_booster_roles(interaction.guild.id)
        
        if not booster_roles:
            embed = discord.Embed(
                title="🚀 Remove Booster Role",
                description="No booster roles have been configured yet.",
                color=0xffa500
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        options = []
        for role in booster_roles:
            role_obj = interaction.guild.get_role(role['role_id'])
            if role_obj:
                options.append(
                    discord.SelectOption(
                        label=role_obj.name,
                        value=str(role['role_id']),
                        description=role.get('description', 'No description')
                    )
                )

        if not options:
            embed = discord.Embed(
                title="🚀 Remove Booster Role",
                description="No valid booster roles found.",
                color=0xffa500
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        view = RemoveBoosterRoleView(self.bot, options)
        embed = discord.Embed(
            title="🚀 Remove Booster Role",
            description="Select a booster role to remove:",
            color=0x9932cc
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="Back", style=discord.ButtonStyle.secondary, emoji="⬅️", row=2)
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.parent_view:
            await self.parent_view.show_main_dashboard(interaction)

class AddBoosterRoleModal(discord.ui.Modal, title="Add Booster Role"):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        self.mongo = bot.mongo_manager

    role = discord.ui.TextInput(
        label="Role Mention/ID",
        placeholder="Mention the role or enter its ID",
        required=True
    )

    description = discord.ui.TextInput(
        label="Description",
        placeholder="Enter a description for this booster role",
        required=True,
        max_length=100
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

            # Add to database
            success = await self.mongo.add_booster_role(
                guild_id=interaction.guild.id,
                role_id=role_id,
                description=self.description.value.strip()
            )

            if success:
                embed = discord.Embed(
                    title="✅ Booster Role Added",
                    description=f"Successfully added {role.mention} as a booster role",
                    color=0x00ff00
                )
            else:
                embed = discord.Embed(
                    title="❌ Error",
                    description="Failed to add booster role. Please try again.",
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

class RemoveBoosterRoleView(discord.ui.View):
    def __init__(self, bot, options):
        super().__init__(timeout=300)
        self.bot = bot
        self.mongo = bot.mongo_manager
        
        # Add select menu
        select_menu = discord.ui.Select(
            placeholder="Choose a booster role to remove",
            options=options,
            min_values=1,
            max_values=1
        )
        select_menu.callback = self.role_selected
        self.add_item(select_menu)

    async def role_selected(self, interaction: discord.Interaction):
        role_id = int(interaction.data['values'][0])
        success = await self.mongo.remove_booster_role(
            guild_id=interaction.guild.id,
            role_id=role_id
        )

        if success:
            embed = discord.Embed(
                title="✅ Booster Role Removed",
                description="Successfully removed the booster role.",
                color=0x00ff00
            )
        else:
            embed = discord.Embed(
                title="❌ Error",
                description="Failed to remove booster role. Please try again.",
                color=0xff0000
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)