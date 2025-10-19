# -*- coding: utf-8 -*-
"""
Clan Dashboard for Blackspire Nation Discord Bot
- Manage clan data, requirements, and settings
- PLAN-compliant: mentions not forms, clean UI
"""
import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
from typing import Optional

class ClanDashboard(commands.Cog):
    """Clan dashboard cog for managing clan data and requirements"""
    
    def __init__(self, bot):
        self.bot = bot
        self.mongo = bot.mongo_manager
        self.data_manager = bot.data_manager

    @app_commands.command(name="clan_dashboard", description="⚔️ Manage clan data and requirements")
    async def clan_dashboard(self, interaction: discord.Interaction):
        """Show clan dashboard main menu"""
        # Check permissions
        user_roles = [role.id for role in interaction.user.roles]
        has_permission = await self.mongo.check_dashboard_permission(
            dashboard_name="clan_dashboard",
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

        # Get current clans
        clans = await self.mongo.get_all_clans(interaction.guild_id)

        embed = discord.Embed(
            title="⚔️ BLACKSPIRE NATION - Clan Dashboard",
            description=(
                "**Clan Management System**\n\n"
                "Manage your clan data, requirements, and settings.\n\n"
                "Current clans:"
            ),
            color=0xff6600,
            timestamp=discord.utils.utcnow()
        )

        if clans:
            for clan in clans[:5]:  # Show first 5 clans
                embed.add_field(
                    name=f"{clan.get('name', 'Unknown')}",
                    value=(
                        f"Min TH: {clan.get('min_town_hall', 'N/A')}\n"
                        f"Type: {clan.get('clan_type', 'N/A').title()}\n"
                        f"Added: {clan.get('added_by', 'Unknown')}"
                    ),
                    inline=True
                )
        else:
            embed.add_field(
                name="No Clans Registered",
                value="Use the dashboard to add your first clan!",
                inline=False
            )
            
        embed.set_footer(text="Blackspire Nation Clan Control", icon_url=self.bot.user.avatar.url if self.bot.user.avatar else None)
        embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else None)

        view = ClanDashboardView(self.bot)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class ClanDashboardView(discord.ui.View):
    """Main clan dashboard view"""
    
    def __init__(self, bot, parent_view=None):
        super().__init__(timeout=300)
        self.bot = bot
        self.mongo = bot.mongo_manager
        self.parent_view = parent_view
        
    @discord.ui.button(label="Add New Clan", style=discord.ButtonStyle.success, emoji="➕")
    async def add_clan(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = AddClanModal(self.bot)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Manage Existing Clan", style=discord.ButtonStyle.primary, emoji="🔧")
    async def manage_existing_clan(self, interaction: discord.Interaction, button: discord.ui.Button):
        clans = await self.mongo.get_all_clans(interaction.guild_id)

        if not clans:
            embed = discord.Embed(
                title="❌ No Clans",
                description="No clans found. Add a clan first!",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        embed = discord.Embed(
            title="🔧 Manage Clan",
            description="Select a clan to manage:",
            color=0xff6600
        )

        options = []
        for clan in clans[:25]:  # Discord limit
            options.append(discord.SelectOption(
                label=clan.get('name', 'Unknown'),
                description=f"TH{clan.get('min_town_hall', '?')} - {clan.get('clan_type', 'Unknown')}",
                value=str(clan.get('_id', 'unknown'))
            ))

        select = discord.ui.Select(
            placeholder="Choose a clan to manage...",
            options=options,
            min_values=1,
            max_values=1
        )
        select.callback = self.clan_selected

        view = discord.ui.View(timeout=300)
        view.add_item(select)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    async def clan_selected(self, interaction: discord.Interaction):
        clan_id = interaction.data["values"][0]
        clan = await self.mongo.get_clan_by_id(clan_id)
        
        if not clan:
            await interaction.response.send_message("❌ Clan not found!", ephemeral=True)
            return

        embed = discord.Embed(
            title=f"🔧 Managing: {clan.get('name', 'Unknown')}",
            description="Choose what to manage:",
            color=0xff6600
        )
        embed.add_field(
            name="Current Info",
            value=(
                f"Min TH: {clan.get('min_town_hall', 'N/A')}\n"
                f"Type: {clan.get('clan_type', 'N/A').title()}\n"
                f"Link: {clan.get('invite_link', 'Not set')}"
            ),
            inline=False
        )

        view = ClanManagementView(self.bot, clan_id)
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="View All Clans", style=discord.ButtonStyle.secondary, emoji="📋")
    async def view_clans(self, interaction: discord.Interaction, button: discord.ui.Button):
        clans = await self.mongo.get_all_clans(interaction.guild_id)

        embed = discord.Embed(
            title="📋 All Clans",
            description="Complete list of registered clans:",
            color=0x3498db
        )

        if clans:
            for clan in clans:
                embed.add_field(
                    name=f"{clan.get('name', 'Unknown')}",
                    value=(
                        f"Min TH: {clan.get('min_town_hall', 'N/A')}\n"
                        f"Type: {clan.get('clan_type', 'N/A').title()}\n"
                        f"Leader: <@{clan.get('leader_id', 'Not set')}>\n"
                        f"Leadership Role: <@&{clan.get('leadership_role_id', 'Not set')}>"
                    ),
                    inline=True
                )
        else:
            embed.add_field(
                name="No Clans",
                value="No clans registered yet.",
                inline=False
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

class AddClanModal(discord.ui.Modal, title="Add New Clan"):
    """Modal for adding a new clan"""
    
    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        self.mongo = bot.mongo_manager

    clan_name = discord.ui.TextInput(
        label="Clan Name",
        placeholder="Enter the clan name...",
        required=True,
        max_length=100
    )

    min_th = discord.ui.TextInput(
        label="Minimum Town Hall",
        placeholder="Enter minimum TH level (e.g., 12)",
        required=True,
        max_length=2
    )

    clan_type = discord.ui.TextInput(
        label="Clan Type",
        placeholder="Regular, Cruise, FWA/GFL, CWL, War, or Farm",
        required=True,
        max_length=20
    )

    invite_link = discord.ui.TextInput(
        label="Clan Invite Link",
        placeholder="Enter the clan invite link...",
        required=True,
        max_length=200
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            min_th_level = int(self.min_th.value)
            
            clan_data = {
                'name': self.clan_name.value,
                'min_town_hall': min_th_level,
                'clan_type': self.clan_type.value.lower(),
                'invite_link': self.invite_link.value,
                'added_by': interaction.user.id,
                'guild_id': interaction.guild_id,
                'created_at': datetime.utcnow()
            }
            
            success = await self.mongo.save_clan_data(clan_data, interaction.guild_id)
            
            if success:
                embed = discord.Embed(
                    title="✅ Clan Added Successfully",
                    description=f"**{self.clan_name.value}** has been added to the system!",
                    color=0x00ff00
                )
                embed.add_field(name="Minimum TH", value=str(min_th_level), inline=True)
                embed.add_field(name="Type", value=self.clan_type.value.title(), inline=True)
                embed.add_field(name="Invite Link", value=self.invite_link.value, inline=False)
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                embed = discord.Embed(
                    title="❌ Error",
                    description="Failed to add clan. Please try again.",
                    color=0xff0000
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                
        except ValueError:
            embed = discord.Embed(
                title="❌ Invalid Input",
                description="Please enter a valid number for minimum Town Hall level.",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

class ClanManagementView(discord.ui.View):
    """View for managing a specific clan"""
    
    def __init__(self, bot, clan_id):
        super().__init__(timeout=300)
        self.bot = bot
        self.mongo = bot.mongo_manager
        self.clan_id = clan_id

    @discord.ui.button(label="Set Clan Leader", style=discord.ButtonStyle.primary, emoji="👑")
    async def set_leader(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="👑 Set Clan Leader",
            description="Mention the clan leader in this channel:",
            color=0xffd700
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

        def check(m):
            return m.author.id == interaction.user.id and m.channel.id == interaction.channel.id and m.mentions

        try:
            msg = await self.bot.wait_for('message', check=check, timeout=60.0)
            leader = msg.mentions[0]
            
            success = await self.mongo.update_clan_field(self.clan_id, 'leader_id', leader.id)
            
            if success:
                embed = discord.Embed(
                    title="✅ Leader Set",
                    description=f"Set {leader.mention} as clan leader.",
                    color=0x00ff00
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                embed = discord.Embed(
                    title="❌ Error",
                    description="Failed to set clan leader.",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                
        except Exception as e:
            embed = discord.Embed(
                title="⏰ Timeout",
                description="No leader mentioned in time.",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

    @discord.ui.button(label="Set Leadership Role", style=discord.ButtonStyle.primary, emoji="🛡️")
    async def set_leadership_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="🛡️ Set Leadership Role",
            description="Mention the leadership role in this channel:",
            color=0xffd700
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

        def check(m):
            return m.author.id == interaction.user.id and m.channel.id == interaction.channel.id and m.role_mentions

        try:
            msg = await self.bot.wait_for('message', check=check, timeout=60.0)
            role = msg.role_mentions[0]
            
            success = await self.mongo.update_clan_field(self.clan_id, 'leadership_role_id', role.id)
            
            if success:
                embed = discord.Embed(
                    title="✅ Leadership Role Set",
                    description=f"Set {role.mention} as leadership role.",
                    color=0x00ff00
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                embed = discord.Embed(
                    title="❌ Error",
                    description="Failed to set leadership role.",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                
        except Exception as e:
            embed = discord.Embed(
                title="⏰ Timeout",
                description="No role mentioned in time.",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

    @discord.ui.button(label="Set Clan Icon", style=discord.ButtonStyle.secondary, emoji="🖼️")
    async def set_clan_icon(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="🖼️ Set Clan Icon",
            description="Send an image in this channel to set as clan icon:",
            color=0x3498db
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

        def check(m):
            return (m.author.id == interaction.user.id and 
                   m.channel.id == interaction.channel.id and 
                   m.attachments)

        try:
            msg = await self.bot.wait_for('message', check=check, timeout=60.0)
            attachment = msg.attachments[0]
            
            if not attachment.content_type.startswith('image/'):
                embed = discord.Embed(
                    title="❌ Invalid File",
                    description="Please send an image file.",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            success = await self.mongo.update_clan_field(self.clan_id, 'icon_url', attachment.url)
            
            if success:
                embed = discord.Embed(
                    title="✅ Icon Set",
                    description="Clan icon has been set successfully.",
                    color=0x00ff00
                )
                embed.set_image(url=attachment.url)
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                embed = discord.Embed(
                    title="❌ Error",
                    description="Failed to set clan icon.",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                
        except Exception as e:
            embed = discord.Embed(
                title="⏰ Timeout",
                description="No image sent in time.",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

    @discord.ui.button(label="Edit Basic Info", style=discord.ButtonStyle.secondary, emoji="✏️")
    async def edit_basic_info(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = EditClanModal(self.bot, self.clan_id)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="View Clan Info", style=discord.ButtonStyle.secondary, emoji="📊")
    async def view_clan_info(self, interaction: discord.Interaction, button: discord.ui.Button):
        clan = await self.mongo.get_clan_by_id(self.clan_id)
        
        if not clan:
            await interaction.response.send_message("❌ Clan not found!", ephemeral=True)
            return

        embed = discord.Embed(
            title=f"📊 {clan.get('name', 'Unknown')} - Clan Information",
            color=0x3498db
        )
        
        embed.add_field(name="Minimum TH", value=str(clan.get('min_town_hall', 'N/A')), inline=True)
        embed.add_field(name="Type", value=clan.get('clan_type', 'N/A').title(), inline=True)
        embed.add_field(name="Leader", value=f"<@{clan.get('leader_id', 'Not set')}>", inline=True)
        embed.add_field(name="Leadership Role", value=f"<@&{clan.get('leadership_role_id', 'Not set')}>", inline=True)
        embed.add_field(name="Invite Link", value=clan.get('invite_link', 'Not set'), inline=False)
        
        if clan.get('icon_url'):
            embed.set_thumbnail(url=clan['icon_url'])
            
        embed.add_field(name="Created", value=clan.get('created_at', 'Unknown'), inline=True)
        embed.add_field(name="Added By", value=f"<@{clan.get('added_by', 'Unknown')}>", inline=True)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Delete Clan", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def delete_clan(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="⚠️ Delete Clan",
            description="Are you sure you want to delete this clan? This action cannot be undone.",
            color=0xff0000
        )
        
        view = ConfirmDeleteView(self.bot, self.clan_id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class EditClanModal(discord.ui.Modal, title="Edit Clan Information"):
    """Modal for editing clan information"""
    
    def __init__(self, bot, clan_id):
        super().__init__()
        self.bot = bot
        self.mongo = bot.mongo_manager
        self.clan_id = clan_id

    clan_name = discord.ui.TextInput(
        label="Clan Name",
        placeholder="Enter the clan name...",
        required=False,
        max_length=100
    )

    min_th = discord.ui.TextInput(
        label="Minimum Town Hall",
        placeholder="Enter minimum TH level (e.g., 12)",
        required=False,
        max_length=2
    )

    clan_type = discord.ui.TextInput(
        label="Clan Type",
        placeholder="Regular, Cruise, FWA/GFL, CWL, War, or Farm",
        required=False,
        max_length=20
    )

    invite_link = discord.ui.TextInput(
        label="Clan Invite Link",
        placeholder="Enter the clan invite link...",
        required=False,
        max_length=200
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            updates = {}
            
            if self.clan_name.value:
                updates['name'] = self.clan_name.value
            if self.min_th.value:
                updates['min_town_hall'] = int(self.min_th.value)
            if self.clan_type.value:
                updates['clan_type'] = self.clan_type.value.lower()
            if self.invite_link.value:
                updates['invite_link'] = self.invite_link.value
            
            if not updates:
                await interaction.response.send_message("❌ No changes provided!", ephemeral=True)
                return
            
            success = await self.mongo.update_clan_data(self.clan_id, updates)
            
            if success:
                embed = discord.Embed(
                    title="✅ Clan Updated",
                    description="Clan information has been updated successfully.",
                    color=0x00ff00
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                embed = discord.Embed(
                    title="❌ Error",
                    description="Failed to update clan information.",
                    color=0xff0000
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                
        except ValueError:
            embed = discord.Embed(
                title="❌ Invalid Input",
                description="Please enter a valid number for minimum Town Hall level.",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

class ConfirmDeleteView(discord.ui.View):
    """View for confirming clan deletion"""
    
    def __init__(self, bot, clan_id):
        super().__init__(timeout=60)
        self.bot = bot
        self.mongo = bot.mongo_manager
        self.clan_id = clan_id

    @discord.ui.button(label="Confirm Delete", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def confirm_delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        success = await self.mongo.delete_clan(self.clan_id)
        
        if success:
            embed = discord.Embed(
                title="✅ Clan Deleted",
                description="Clan has been deleted successfully.",
                color=0x00ff00
            )
        else:
            embed = discord.Embed(
                title="❌ Error",
                description="Failed to delete clan.",
                color=0xff0000
            )
        
        await interaction.response.edit_message(embed=embed, view=None)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancel_delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="✅ Cancelled",
            description="Clan deletion has been cancelled.",
            color=0x00ff00
        )
        await interaction.response.edit_message(embed=embed, view=None)

async def setup(bot):
    await bot.add_cog(ClanDashboard(bot))
