import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import math
from typing import List, Optional
from .views.view_protocols import BoosterViews
from .views.color_role_management import ColorRoleManagementView
from .views.booster_panel import BoosterPanelView

class BoosterDashboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.mongo = bot.mongo_manager
        self.data_manager = bot.data_manager

    @app_commands.command(name="booster_dashboard", description="🚀 Manage booster roles and color panels")
    async def booster_dashboard(self, interaction: discord.Interaction):
        try:
            # Check permissions
            user_roles = [role.id for role in interaction.user.roles]
            has_permission = await self.mongo.check_dashboard_permission(
            dashboard_name="booster_dashboard",
            user_id=interaction.user.id,
            user_roles=user_roles,
            guild_id=interaction.guild_id
        )

            if not has_permission:
                embed = discord.Embed(
                    title="❌ Access Denied",
                    description="You don't have permission to access this dashboard.",
                    color=0xff0000
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
        except Exception as e:
            embed = discord.Embed(
                title="❌ Error",
                description=f"An error occurred while checking permissions: {str(e)}",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        embed = discord.Embed(
            title="🚀 BLACKSPIRE NATION - Booster Dashboard",
            description="**Booster Management System**\n\nManage booster perks and color roles:",
            color=0xff69b4,
            timestamp=discord.utils.utcnow()
        )
        embed.set_footer(text="Blackspire Nation Booster Control", icon_url=self.bot.user.avatar.url if self.bot.user.avatar else None)
        embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else None)

        view = BoosterDashboardView(self.bot)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=False)

class PanelDeploymentView(discord.ui.View):
    def __init__(self, bot, panel_type, guild_id):
        super().__init__(timeout=300)
        self.bot = bot
        self.mongo = bot.mongo_manager
        self.panel_type = panel_type
        self.guild_id = guild_id

    @discord.ui.button(label="Set Panel Image", style=discord.ButtonStyle.secondary, emoji="🖼️", row=0)
    async def set_panel_image(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="🖼️ Set Panel Image",
            description="Send an image in this channel to set as the panel image.",
            color=0x0099ff
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
        def check(m):
            return (m.author.id == interaction.user.id and 
                   m.channel.id == interaction.channel.id and 
                   m.attachments)

        try:
            msg = await self.bot.wait_for('message', check=check, timeout=60.0)
            image_url = msg.attachments[0].url
            
            await self.mongo.save_panel_image(self.panel_type, image_url, self.guild_id)
            
            embed = discord.Embed(
                title="✅ Image Set",
                description=f"Panel image has been updated!",
                color=0x00ff00
            )
            embed.set_image(url=image_url)
            await interaction.followup.send(embed=embed, ephemeral=True)
        
        except asyncio.TimeoutError:
            await interaction.followup.send("Image selection timed out. Please try again.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"Error setting image: {str(e)}", ephemeral=True)

    @discord.ui.button(label="Select Channel", style=discord.ButtonStyle.primary, emoji="📁", row=0)
    async def select_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            # Check if color roles are configured
            color_roles = await self.mongo.get_color_roles(self.guild_id)
            if not color_roles:
                embed = discord.Embed(
                    title="⚠️ Configuration Required",
                    description="Please configure color roles before selecting a channel.",
                    color=0xffa500
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            view = ChannelSelectionView(self.bot, self.panel_type, self.guild_id)
            embed = discord.Embed(
                title="📁 Select Channel",
                description="Choose a channel to deploy the booster panel:",
                color=0x00ff00
            )
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Error: {str(e)}", ephemeral=True)

    @discord.ui.button(label="Back", style=discord.ButtonStyle.danger, emoji="⬅️", row=1)
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = BoosterDashboardView(self.bot)
        embed = discord.Embed(
            title="🚀 BLACKSPIRE NATION - Booster Dashboard",
            description="**Booster Management System**\n\nManage booster perks and color roles:",
            color=0xff69b4
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class BoosterDashboardView(discord.ui.View):
    def __init__(self, bot, parent_view=None):
        super().__init__(timeout=300)
        self.bot = bot
        self.mongo = bot.mongo_manager
        self.parent_view = parent_view
        
    @discord.ui.button(label="Back", style=discord.ButtonStyle.danger, emoji="⬅️", row=4)
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.parent_view:
            await interaction.response.edit_message(view=self.parent_view)
            return
            
        embed = discord.Embed(
            title="🚀 BLACKSPIRE NATION - Booster Dashboard",
            description="**Booster Management System**\n\nManage booster perks and color roles:",
            color=0xff69b4,
            timestamp=discord.utils.utcnow()
        )
        embed.set_footer(text="Blackspire Nation Booster Control", icon_url=self.bot.user.avatar.url if self.bot.user.avatar else None)
        embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else None)
        await interaction.response.edit_message(embed=embed, view=self)

    async def show_main_dashboard(self, interaction: discord.Interaction):
        """Show the main booster dashboard"""
        embed = discord.Embed(
            title="🚀 BLACKSPIRE NATION - Booster Dashboard",
            description="**Booster Management System**\n\nManage booster perks and color roles:",
            color=0xff69b4
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Manage Colour Roles", style=discord.ButtonStyle.primary, emoji="🎨", row=0)
    async def manage_colour_roles(self, interaction: discord.Interaction, button: discord.ui.Button):
        from .views.color_role_management import ColorRoleManagementView
        view = ColorRoleManagementView(self.bot, self)
        embed = discord.Embed(
            title="🎨 Manage Colour Roles",
            description="Manage the color roles available for boosters:",
            color=0x9932cc
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="Manage Booster Roles", style=discord.ButtonStyle.primary, emoji="🚀", row=0)
    async def manage_booster_roles(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = BoosterRoleManagementView(self.bot)
        embed = discord.Embed(
            title="🚀 Manage Booster Roles",
            description="Manage which roles are considered booster roles:",
            color=0x9932cc
        )
        await interaction.response.defer()
        new_msg = await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        view.message = new_msg

    @discord.ui.button(label="Deploy Colour Panel", style=discord.ButtonStyle.success, emoji="🎪", row=1)
    async def deploy_colour_panel(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            # Check if color roles are configured
            color_roles = await self.mongo.get_color_roles(interaction.guild_id)
            if not color_roles:
                embed = discord.Embed(
                    title="⚠️ Configuration Required",
                    description="Please configure color roles before deploying the panel.",
                    color=0xffa500
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            view = PanelDeploymentView(self.bot, 'booster_panel', interaction.guild_id)
            embed = discord.Embed(
                title="🎪 Deploy Colour Panel",
                description=(
                    "Configure and deploy the color selection panel:\n\n"
                    "1. Set a panel image (optional)\n"
                    "2. Select the channel for deployment\n"
                    f"3. {len(color_roles)} color roles will be available"
                ),
                color=0x00ff00
            )
            await interaction.response.send_message(embed=embed, view=view, ephemeral=False)
        except Exception as e:
            embed = discord.Embed(
                title="❌ Error",
                description=f"An error occurred while deploying panel: {str(e)}",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Set Panel Image", style=discord.ButtonStyle.secondary, emoji="🖼️", row=1)
    async def set_panel_image(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="🖼️ Set Booster Panel Image",
            description="Send an image in this channel to set as the booster panel image.",
            color=0x0099ff
        )
        await interaction.response.defer()
        await interaction.followup.send(embed=embed, ephemeral=True)

        def check(m):
            return (m.author.id == interaction.user.id and 
                   m.channel.id == interaction.channel.id and 
                   m.attachments)

        try:
            msg = await self.bot.wait_for('message', check=check, timeout=60.0)
            image_url = msg.attachments[0].url

            await self.mongo.save_panel_image('booster_panel', image_url, interaction.guild_id)

            success_embed = discord.Embed(
                title="✅ Image Set",
                description="Booster panel image has been updated successfully!",
                color=0x00ff00
            )
            success_embed.set_image(url=image_url)

            view = BoosterDashboardView(self.bot)
            await interaction.followup.send(embed=success_embed, view=view, ephemeral=True)

        except asyncio.TimeoutError:
            embed = discord.Embed(
                title="⏰ Timeout",
                description="You took too long to send an image.",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

class ColorRoleView(discord.ui.View):
    def __init__(self, bot, page=0, guild_id=None):
        super().__init__(timeout=300)
        self.bot = bot
        self.mongo = bot.mongo_manager
        self.page = page
        self.roles_per_page = 10
        self.guild_id = guild_id
        self._refresh_buttons()

    def _refresh_buttons(self):
        # Clear existing buttons
        self.clear_items()

        # Get color roles
        try:
            # Use self.guild_id instead of interaction.guild_id
            color_roles = []
            if self.guild_id:
                color_roles = self.bot.loop.run_until_complete(self.mongo.get_color_roles(self.guild_id))
            
            # Calculate total pages
            total_pages = (len(color_roles) - 1) // self.roles_per_page + 1 if color_roles else 1

            # Add role buttons for current page
            start_idx = self.page * self.roles_per_page
            end_idx = min(start_idx + self.roles_per_page, len(color_roles)) if color_roles else 0

            if color_roles:
                for i in range(start_idx, end_idx):
                    role_data = color_roles[i]
                    if self.guild_id:
                        guild = self.bot.get_guild(self.guild_id)
                        if guild:
                            role = guild.get_role(role_data['role_id'])
                            if role:
                                self.add_item(RoleRemoveButton(role))
        except Exception:
            pass  # Handle any errors gracefully

        # Add navigation buttons if needed
        if self.page > 0:
            self.add_item(PreviousPageButton(self.bot, "color_roles", self.page))
        if self.page < total_pages - 1:
            self.add_item(NextPageButton(self.bot, "color_roles", self.page))

        # Add back button
        self.add_item(discord.ui.Button(
            label="Back",
            style=discord.ButtonStyle.secondary,
            emoji="⬅️",
            row=4
        ))

class RoleRemoveButton(discord.ui.Button):
    def __init__(self, role):
        super().__init__(
            label=f"Remove {role.name}",
            style=discord.ButtonStyle.danger,
            custom_id=str(role.id)
        )
        self.role = role

    async def callback(self, interaction: discord.Interaction):
        await self.view.mongo.remove_color_role(self.role.id)
        
        embed = discord.Embed(
            title="✅ Role Removed",
            description=f"Removed {self.role.mention} from color roles.",
            color=0x00ff00
        )
        
        view = ColorRoleManagementView(self.bot)
        await interaction.response.defer()
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

class BoosterRoleView(discord.ui.View):
    def __init__(self, bot, page=0, guild_id=None):
        super().__init__(timeout=300)
        self.bot = bot
        self.mongo = bot.mongo_manager
        self.page = page
        self.roles_per_page = 10
        self.guild_id = guild_id
        self._refresh_buttons()

    def _refresh_buttons(self):
        # Clear existing buttons
        self.clear_items()

        # Get booster roles
        try:
            # Use self.guild_id instead of interaction.guild_id
            booster_roles = []
            if self.guild_id:
                booster_roles = self.bot.loop.run_until_complete(self.mongo.get_booster_roles(self.guild_id))
            
            # Calculate total pages
            total_pages = (len(booster_roles) - 1) // self.roles_per_page + 1 if booster_roles else 1

            # Add role buttons for current page
            start_idx = self.page * self.roles_per_page
            end_idx = min(start_idx + self.roles_per_page, len(booster_roles)) if booster_roles else 0

            if booster_roles:
                for i in range(start_idx, end_idx):
                    role_data = booster_roles[i]
                    if self.guild_id:
                        guild = self.bot.get_guild(self.guild_id)
                        if guild:
                            role = guild.get_role(role_data['role_id'])
                            if role:
                                self.add_item(BoosterRoleRemoveButton(role))
        except Exception:
            pass  # Handle any errors gracefully

        # Add navigation buttons if needed
        if self.page > 0:
            self.add_item(PreviousPageButton(self.bot, "booster_roles", self.page))
        if self.page < total_pages - 1:
            self.add_item(NextPageButton(self.bot, "booster_roles", self.page))

        # Add back button
        self.add_item(discord.ui.Button(
            label="Back",
            style=discord.ButtonStyle.secondary,
            emoji="⬅️",
            row=4
        ))

class BoosterRoleRemoveButton(discord.ui.Button):
    def __init__(self, role):
        super().__init__(
            label=f"Remove {role.name}",
            style=discord.ButtonStyle.danger,
            custom_id=str(role.id)
        )
        self.role = role

    async def callback(self, interaction: discord.Interaction):
        await self.view.mongo.remove_booster_role(self.role.id)
        
        embed = discord.Embed(
            title="✅ Role Removed",
            description=f"Removed {self.role.mention} from booster roles.",
            color=0x00ff00
        )
        
        view = BoosterRoleManagementView(self.bot)
        await interaction.response.defer()
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

class ColorRoleManagementView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=300)
        self.bot = bot
        self.mongo = bot.mongo_manager

    @discord.ui.button(label="Add Colour Role", style=discord.ButtonStyle.success, emoji="➕")
    async def add_colour_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="➕ Add Colour Role",
            description="Mention a role in your next message to add it as a color role option.",
            color=0x00ff00
        )
        await interaction.response.edit_message(embed=embed, view=None)

        def check(m):
            return (m.author.id == interaction.user.id and 
                   m.channel.id == interaction.channel.id and 
                   m.role_mentions)

        try:
            msg = await self.bot.wait_for('message', check=check, timeout=60.0)
            role = msg.role_mentions[0]

            await self.mongo.add_color_role(role.id, interaction.guild.id)

            embed = discord.Embed(
                title="✅ Color Role Added",
                description=f"Added {role.mention} as a color role option.",
                color=0x00ff00
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

        except asyncio.TimeoutError:
            embed = discord.Embed(
                title="⏰ Timeout",
                description="You took too long to mention a role.",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

    @discord.ui.button(label="View Colour Roles", style=discord.ButtonStyle.secondary, emoji="👀")
    async def view_colour_roles(self, interaction: discord.Interaction, button: discord.ui.Button):
        color_roles = await self.mongo.get_color_roles(interaction.guild_id)

        embed = discord.Embed(
            title="🎨 Current Colour Roles",
            color=0x0099ff
        )

        if color_roles:
            role_mentions = [f"<@&{role['role_id']}>" for role in color_roles]
            embed.description = "\n".join(role_mentions)
        else:
            embed.description = "No color roles configured."

        await interaction.response.edit_message(embed=embed, view=None)

    @discord.ui.button(label="Remove Colour Role", style=discord.ButtonStyle.danger, emoji="➖")
    async def remove_colour_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        color_roles = await self.mongo.get_color_roles(interaction.guild_id)

class PreviousPageButton(discord.ui.Button):
    def __init__(self, bot, action, page):
        super().__init__(
            label="Previous",
            style=discord.ButtonStyle.secondary,
            emoji="⬅️",
            row=4
        )
        self.bot = bot
        self.action = action
        self.page = page

    async def callback(self, interaction: discord.Interaction):
        if self.action == "color_roles":
            view = ColorRoleView(self.bot, self.page - 1, interaction.guild_id)
            embed = discord.Embed(
                title="🎨 Color Roles",
                description="Select a color role to remove:",
                color=0x9932cc
            )
        else:
            view = BoosterRoleView(self.bot, self.page - 1, interaction.guild_id)
            embed = discord.Embed(
                title="🚀 Booster Roles",
                description="Select a booster role to remove:",
                color=0x9932cc
            )
        await interaction.response.defer()
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

class NextPageButton(discord.ui.Button):
    def __init__(self, bot, action, page):
        super().__init__(
            label="Next",
            style=discord.ButtonStyle.secondary,
            emoji="➡️",
            row=4
        )
        self.bot = bot
        self.action = action
        self.page = page

    async def callback(self, interaction: discord.Interaction):
        if self.action == "color_roles":
            view = ColorRoleView(self.bot, self.page + 1, interaction.guild_id)
            embed = discord.Embed(
                title="🎨 Color Roles",
                description="Select a color role to remove:",
                color=0x9932cc
            )
        else:
            view = BoosterRoleView(self.bot, self.page + 1)
            embed = discord.Embed(
                title="🚀 Booster Roles",
                description="Select a booster role to remove:",
                color=0x9932cc
            )
        await interaction.response.defer()
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

        if not color_roles:
            embed = discord.Embed(
                title="❌ No Color Roles",
                description="No color roles found to remove.",
                color=0xff0000
            )
            await interaction.response.edit_message(embed=embed, view=None)
            return

        view = ColorRoleRemovalView(self.bot, color_roles)
        embed = discord.Embed(
            title="➖ Remove Colour Role",
            description="Select a color role to remove:",
            color=0xff0000
        )
        await interaction.response.edit_message(embed=embed, view=view)

class BoosterRoleManagementView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=300)
        self.bot = bot
        self.mongo = bot.mongo_manager

    @discord.ui.button(label="Add Booster Role", style=discord.ButtonStyle.success, emoji="➕")
    async def add_booster_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="➕ Add Booster Role",
            description="Mention a role in your next message to add it as a booster role.",
            color=0x00ff00
        )
        await interaction.response.edit_message(embed=embed, view=None)

        def check(m):
            return (m.author.id == interaction.user.id and 
                   m.channel.id == interaction.channel.id and 
                   m.role_mentions)

        try:
            msg = await self.bot.wait_for('message', check=check, timeout=60.0)
            role = msg.role_mentions[0]

            self.mongo.add_booster_role(role.id)

            embed = discord.Embed(
                title="✅ Booster Role Added",
                description=f"Added {role.mention} as a booster role.",
                color=0x00ff00
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

        except asyncio.TimeoutError:
            embed = discord.Embed(
                title="⏰ Timeout",
                description="You took too long to mention a role.",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

    @discord.ui.button(label="View Booster Roles", style=discord.ButtonStyle.secondary, emoji="👀")
    async def view_booster_roles(self, interaction: discord.Interaction, button: discord.ui.Button):
        booster_roles = self.mongo.get_booster_roles()

        embed = discord.Embed(
            title="🚀 Current Booster Roles",
            color=0x0099ff
        )

        if booster_roles:
            role_mentions = [f"<@&{role['role_id']}>" for role in booster_roles]
            embed.description = "\n".join(role_mentions)
        else:
            embed.description = "No booster roles configured."

        await interaction.response.edit_message(embed=embed, view=None)

    @discord.ui.button(label="Remove Booster Role", style=discord.ButtonStyle.danger, emoji="➖")
    async def remove_booster_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        booster_roles = self.mongo.get_booster_roles()

        if not booster_roles:
            embed = discord.Embed(
                title="❌ No Booster Roles",
                description="No booster roles found to remove.",
                color=0xff0000
            )
            await interaction.response.edit_message(embed=embed, view=None)
            return

        view = BoosterRoleRemovalView(self.bot, booster_roles)
        embed = discord.Embed(
            title="➖ Remove Booster Role",
            description="Select a booster role to remove:",
            color=0xff0000
        )
        await interaction.response.edit_message(embed=embed, view=view)

class ColorRoleRemovalView(discord.ui.View):
    def __init__(self, bot, color_roles):
        super().__init__(timeout=300)
        self.bot = bot
        self.mongo = bot.mongo_manager
        self.add_item(ColorRoleRemovalDropdown(bot, color_roles))

class ColorRoleRemovalDropdown(discord.ui.Select):
    def __init__(self, bot, color_roles):
        self.bot = bot
        self.mongo = bot.mongo_manager

        options = []
        for role_data in color_roles[:25]:  # Discord limit
            role = bot.get_guild(bot.guilds[0].id).get_role(role_data['role_id']) if bot.guilds else None
            options.append(discord.SelectOption(
                label=role.name if role else f"Role {role_data['role_id']}",
                value=str(role_data['role_id']),
                description=f"Role ID: {role_data['role_id']}"
            ))

        super().__init__(placeholder="Select a color role to remove...", options=options)

    async def callback(self, interaction: discord.Interaction):
        role_id = int(self.values[0])
        role = interaction.guild.get_role(role_id)

        self.mongo.remove_color_role(role_id)

        embed = discord.Embed(
            title="✅ Color Role Removed",
            description=f"Removed {role.mention if role else f'Role {role_id}'} from color roles.",
            color=0x00ff00
        )
        await interaction.response.edit_message(embed=embed, view=None)

class BoosterRoleRemovalView(discord.ui.View):
    def __init__(self, bot, booster_roles):
        super().__init__(timeout=300)
        self.bot = bot
        self.mongo = bot.mongo_manager
        self.add_item(BoosterRoleRemovalDropdown(bot, booster_roles))

class BoosterRoleRemovalDropdown(discord.ui.Select):
    def __init__(self, bot, booster_roles):
        self.bot = bot
        self.mongo = bot.mongo_manager

        options = []
        for role_data in booster_roles[:25]:  # Discord limit
            role = bot.get_guild(bot.guilds[0].id).get_role(role_data['role_id']) if bot.guilds else None
            options.append(discord.SelectOption(
                label=role.name if role else f"Role {role_data['role_id']}",
                value=str(role_data['role_id']),
                description=f"Role ID: {role_data['role_id']}"
            ))

        super().__init__(placeholder="Select a booster role to remove...", options=options)

    async def callback(self, interaction: discord.Interaction):
        role_id = int(self.values[0])
        role = interaction.guild.get_role(role_id)

        self.mongo.remove_booster_role(role_id)

        embed = discord.Embed(
            title="✅ Booster Role Removed",
            description=f"Removed {role.mention if role else f'Role {role_id}'} from booster roles.",
            color=0x00ff00
        )
        await interaction.response.edit_message(embed=embed, view=None)

class ChannelSelectionView(discord.ui.View):
    def __init__(self, bot, panel_type: str, guild_id: int, page: int = 0):
        super().__init__(timeout=300)
        self.bot = bot
        self.panel_type = panel_type
        self.guild_id = guild_id
        self.mongo = bot.mongo_manager
        self.page = page
        self.channels_per_page = 10
        self._refresh_buttons()

    def _refresh_buttons(self):
        # Clear existing buttons
        self.clear_items()
        
        # Get all text channels from the guild
        guild = self.bot.get_guild(self.guild_id)
        if not guild:
            return
            
        # Get channels and sort them by category position then channel position
        channels = [ch for ch in guild.text_channels]
        channels.sort(key=lambda x: (x.category.position if x.category else -1, x.position))
        
        # Calculate total pages
        total_pages = math.ceil(len(channels) / self.channels_per_page)
        
        # Add channel buttons for current page
        start_idx = self.page * self.channels_per_page
        end_idx = min(start_idx + self.channels_per_page, len(channels))
        
        for channel in channels[start_idx:end_idx]:
            self.add_item(ChannelButton(channel))
            
        # Add navigation buttons if needed
        if self.page > 0:
            self.add_item(PreviousPageButton(self.bot, "channels", self.page))
        if self.page < total_pages - 1:
            self.add_item(NextPageButton(self.bot, "channels", self.page))
        
        # Add back button
        self.add_item(discord.ui.Button(
            label="Back",
            style=discord.ButtonStyle.secondary,
            emoji="⬅️",
            row=4
        ))
        
        # Add page indicator if multiple pages
        if total_pages > 1:
            self.add_item(discord.ui.Button(
                label=f"Page {self.page + 1}/{total_pages}",
                disabled=True,
                style=discord.ButtonStyle.secondary,
                row=4
            ))

class ChannelButton(discord.ui.Button):
    def __init__(self, channel: discord.TextChannel):
        category_name = channel.category.name if channel.category else "No Category"
        super().__init__(
            label=f"#{channel.name}",
            style=discord.ButtonStyle.secondary,
            custom_id=f"channel_{channel.id}",
            row=self._get_row_for_channel(channel)
        )
        self.channel = channel

    def _get_row_for_channel(self, channel: discord.TextChannel) -> int:
        # Organize buttons in rows by category
        if not channel.category:
            return 0
        # Use modulo to cycle through rows 0-2
        return (channel.category.position % 3)

    async def callback(self, interaction: discord.Interaction):
        # Deploy the panel to the selected channel
        await self.view.mongo.save_panel_channel(self.view.panel_type, self.channel.id)
        
        # Create embed based on panel type
        title = "🎨 Colour Panel" if self.view.panel_type == "booster_panel" else "🎫 Ticket Panel"
        description = "Select a color role:" if self.view.panel_type == "booster_panel" else "Choose a ticket type:"
        color = 0xff69b4 if self.view.panel_type == "booster_panel" else 0x00ff00
        
        panel_embed = discord.Embed(
            title=title,
            description=description,
            color=color,
            timestamp=discord.utils.utcnow()
        )
        
        # Add panel image if exists
        panel_image = await self.view.mongo.get_panel_image(self.view.panel_type)
        if panel_image:
            panel_embed.set_image(url=panel_image)

        # Get panel view based on type
        if self.view.panel_type == "booster_panel":
            from .booster_panel import BoosterPanelView
            panel_view = BoosterPanelView(self.view.bot)
        else:
            from .main_dashboard import MainPanelView
            panel_view = MainPanelView(self.view.bot)

        # Send panel
        await self.channel.send(embed=panel_embed, view=panel_view)
        
        # Send success message
        success_embed = discord.Embed(
            title="✅ Panel Deployed",
            description=f"Panel has been deployed to {self.channel.mention}",
            color=0x00ff00
        )
        
        # Return to main dashboard
        main_view = BoosterDashboardView(self.view.bot)
        await interaction.response.defer()
        await interaction.followup.send(embed=success_embed, view=main_view, ephemeral=True)
        if self.values[0] == "none":
            return

        channel_id = int(self.values[0])
        channel = interaction.guild.get_channel(channel_id)

        if self.action == 'deploy_color_panel':
            await self.deploy_color_panel(interaction, channel)

    async def deploy_color_panel(self, interaction, channel):
        # Get color roles
        color_roles = self.bot.mongo_manager.get_color_roles()

        if not color_roles:
            embed = discord.Embed(
                title="❌ No Color Roles",
                description="No color roles configured. Please add color roles first.",
                color=0xff0000
            )
            await interaction.response.edit_message(embed=embed, view=None)
            return

        # Create color panel
        embed = discord.Embed(
            title="🎨 Booster Color Selection",
            description="Choose your color role from the dropdown below!\n\n**Note:** You can only have one color role at a time.",
            color=0xff69b4,
            timestamp=discord.utils.utcnow()
        )

        panel_image = self.bot.mongo_manager.get_panel_image('booster_panel')
        if panel_image:
            embed.set_image(url=panel_image)

        embed.set_footer(text="Blackspire Nation Booster Perks")

        view = ColorSelectionView(self.bot, color_roles)

        try:
            await channel.send(embed=embed, view=view)

            embed = discord.Embed(
                title="✅ Panel Deployed",
                description=f"Color selection panel deployed to {channel.mention}",
                color=0x00ff00
            )
            await interaction.response.edit_message(embed=embed, view=None)

        except discord.Forbidden:
            embed = discord.Embed(
                title="❌ Permission Error",
                description=f"I don't have permission to send messages in {channel.mention}",
                color=0xff0000
            )
            await interaction.response.edit_message(embed=embed, view=None)

class ColorSelectionView(discord.ui.View):
    def __init__(self, bot, color_roles):
        super().__init__(timeout=None)  # Persistent view
        self.bot = bot
        self.mongo = bot.mongo_manager
        self.add_item(ColorSelectionDropdown(bot, color_roles))

class ColorSelectionDropdown(discord.ui.Select):
    def __init__(self, bot, color_roles):
        self.bot = bot
        self.mongo = bot.mongo_manager
        self.booster_roles = [role['role_id'] for role in bot.mongo_manager.get_booster_roles()]

        options = [discord.SelectOption(
            label="Remove Color",
            value="remove",
            description="Remove your current color role",
            emoji="🗑️"
        )]

        for role_data in color_roles[:24]:  # Leave room for remove option
            role = bot.get_guild(bot.guilds[0].id).get_role(role_data['role_id']) if bot.guilds else None
            if role:
                options.append(discord.SelectOption(
                    label=role.name,
                    value=str(role.id),
                    description=f"Select {role.name} color"
                ))

        super().__init__(placeholder="Choose your color...", options=options)

    async def callback(self, interaction: discord.Interaction):
        # Check if user has booster role
        user_role_ids = [role.id for role in interaction.user.roles]
        has_booster_role = any(role_id in self.booster_roles for role_id in user_role_ids)

        if not has_booster_role:
            embed = discord.Embed(
                title="❌ Access Denied",
                description="You need a booster role to use color selection!",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if self.values[0] == "remove":
            # Remove all color roles
            color_roles = self.mongo.get_color_roles()
            removed_roles = []

            for role_data in color_roles:
                role = interaction.guild.get_role(role_data['role_id'])
                if role and role in interaction.user.roles:
                    try:
                        await interaction.user.remove_roles(role, reason="Color role removed")
                        removed_roles.append(role.name)
                    except:
                        pass

            if removed_roles:
                embed = discord.Embed(
                    title="✅ Color Removed",
                    description=f"Removed color roles: {', '.join(removed_roles)}",
                    color=0x00ff00
                )
            else:
                embed = discord.Embed(
                    title="ℹ️ No Changes",
                    description="You didn't have any color roles to remove.",
                    color=0x0099ff
                )

            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Add new color role
        new_role_id = int(self.values[0])
        new_role = interaction.guild.get_role(new_role_id)

        if not new_role:
            embed = discord.Embed(
                title="❌ Role Not Found",
                description="The selected role could not be found.",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Remove existing color roles first
        color_roles = self.mongo.get_color_roles()
        for role_data in color_roles:
            role = interaction.guild.get_role(role_data['role_id'])
            if role and role in interaction.user.roles:
                try:
                    await interaction.user.remove_roles(role, reason="Changing color role")
                except:
                    pass

        # Add new color role
        try:
            await interaction.user.add_roles(new_role, reason="Selected new color role")
            embed = discord.Embed(
                title="✅ Color Selected",
                description=f"You now have the {new_role.mention} color role!",
                color=new_role.color if new_role.color.value != 0 else 0x00ff00
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except discord.Forbidden:
            embed = discord.Embed(
                title="❌ Permission Error",
                description="I don't have permission to assign this role.",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(BoosterDashboard(bot))
