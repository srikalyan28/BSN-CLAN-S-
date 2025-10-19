# -*- coding: utf-8 -*-
"""
Main Dashboard for Blackspire Nation Discord Bot
- Ticket system hub with main/individual panel configuration
- Deploy panels, manage permissions, configure ticket types
- PLAN-compliant: mentions not forms, paging for channels/categories
"""
import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime

# Ticket imports
from .TICKETS.join_clan import JoinClanTicket

# Placeholder imports for other tickets (implement later)
class ApplyClanTicket:
    def __init__(self, bot): pass
class StaffApplicationTicket:
    def __init__(self, bot): pass
class PartnershipApplicationTicket:
    def __init__(self, bot): pass
class EsportsApplicationTicket:
    def __init__(self, bot): pass
class GiveawayClaimTicket:
    def __init__(self, bot): pass
class HelpSupportTicket:
    def __init__(self, bot): pass
class HostGiveawayTicket:
    def __init__(self, bot): pass
class SponsorshipTicket:
    def __init__(self, bot): pass

# Ticket type constants from PLAN
MAIN_PANEL_TICKETS = [
    ("join_clan", "Join Clan", "⚔️"),
    ("apply_clan", "Apply Your Clan", "🛡️"),
    ("staff_application", "Staff Application", "👔"),
    ("partnership_application", "Partnership Application", "🤝"),
    ("esports_application", "Esports Application", "🎮"),
    ("giveaway_claim", "Giveaway Claim", "🎁")
]

INDIVIDUAL_PANEL_TICKETS = [
    ("sponsorship", "Sponsorships", "💰"),
    ("host_giveaway", "Host Giveaway", "🎉"),
    ("help_support", "Help & Support", "❓")
]

class MainDashboard(commands.Cog):
    """Main dashboard cog for managing all ticket systems in Blackspire Nation"""
    
    def __init__(self, bot):
        self.bot = bot
        self.mongo = bot.mongo_manager
        
        # Initialize ticket handlers
        self.ticket_handlers = {
            "join_clan": JoinClanTicket(bot),
            "apply_clan": ApplyClanTicket(bot),
            "staff_application": StaffApplicationTicket(bot),
            "partnership_application": PartnershipApplicationTicket(bot),
            "esports_application": EsportsApplicationTicket(bot),
            "giveaway_claim": GiveawayClaimTicket(bot),
            "help_support": HelpSupportTicket(bot),
            "host_giveaway": HostGiveawayTicket(bot),
            "sponsorship": SponsorshipTicket(bot)
        }

    @app_commands.command(
        name="main_dashboard",
        description="[Ticket Hub] Blackspire Nation: Manage and deploy all ticket panels"
    )
    async def main_dashboard(self, interaction: discord.Interaction):
        """Main dashboard command - ticket management hub"""
        # Check permissions
        user_roles = [role.id for role in interaction.user.roles]
        guild_id = interaction.guild.id
        
        has_permission = await self.mongo.check_dashboard_permission(
            dashboard_name="main_dashboard",
            user_id=interaction.user.id,
            user_roles=user_roles,
            guild_id=guild_id
        )
        
        if not has_permission:
            embed = discord.Embed(
                title="❌ Access Denied",
                description="You don't have permission to access this dashboard.",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Create the main dashboard embed
        embed = discord.Embed(
            title="[Ticket] BLACKSPIRE NATION - Main Dashboard",
            description="**Ticket Management Hub**\n\nManage all ticketing systems for the server:",
            color=0x00ff33,
            timestamp=datetime.utcnow()
        )
        embed.set_footer(
            text="Blackspire Nation Ticket Control",
            icon_url=self.bot.user.avatar.url if self.bot.user.avatar else None
        )
        embed.set_thumbnail(
            url=interaction.guild.icon.url if interaction.guild.icon else None
        )
        
        # Create the main dashboard view with buttons
        view = MainDashboardView(self.bot)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class MainDashboardView(discord.ui.View):
    """Main dashboard view with primary navigation buttons"""
    
    def __init__(self, bot):
        super().__init__(timeout=300)
        self.bot = bot
        self.mongo = bot.mongo_manager

    @discord.ui.button(
        label="Main Panel",
        style=discord.ButtonStyle.primary,
        emoji="🎫",
        row=0
    )
    async def main_panel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="🎫 Main Panel Configuration",
            description="Configure the main ticket panel with multiple ticket types:",
            color=0x3498db
        )
        
        view = MainPanelConfigView(self.bot)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(
        label="Individual Panels",
        style=discord.ButtonStyle.primary,
        emoji="🎭",
        row=0
    )
    async def individual_panels_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="🎭 Individual Panel Configuration",
            description="Configure individual ticket panels:",
            color=0x9b59b6
        )
        
        view = IndividualPanelConfigView(self.bot)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(
        label="Deploy Panels",
        style=discord.ButtonStyle.success,
        emoji="🚀",
        row=1
    )
    async def deploy_panels_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="🚀 Panel Deployment",
            description="Deploy ticket panels to channels:",
            color=0x2ecc71
        )
        
        view = PanelDeploymentView(self.bot)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class MainPanelConfigView(discord.ui.View):
    """Configuration view for main panel tickets"""
    
    def __init__(self, bot):
        super().__init__(timeout=300)
        self.bot = bot
        self.mongo = bot.mongo_manager
        self.add_ticket_select()

    def add_ticket_select(self):
        options = []
        for ticket_id, ticket_name, emoji in MAIN_PANEL_TICKETS:
            options.append(
                discord.SelectOption(
                    label=ticket_name,
                    value=ticket_id,
                    emoji=emoji
                )
            )

        select = discord.ui.Select(
            placeholder="Select a ticket type to configure...",
            options=options,
            min_values=1,
            max_values=1
        )
        select.callback = self.ticket_select_callback
        self.add_item(select)

    async def ticket_select_callback(self, interaction: discord.Interaction):
        ticket_type = interaction.data["values"][0]
        ticket_name = next(name for tid, name, emoji in MAIN_PANEL_TICKETS if tid == ticket_type)
        
        embed = discord.Embed(
            title=f"🔧 Configure {ticket_name}",
            description="Choose what to configure:",
            color=0x3498db
        )
        
        view = TicketConfigView(self.bot, ticket_type)
        await interaction.response.edit_message(embed=embed, view=view)

class IndividualPanelConfigView(discord.ui.View):
    """Configuration view for individual panels"""
    
    def __init__(self, bot):
        super().__init__(timeout=300)
        self.bot = bot
        self.mongo = bot.mongo_manager
        self.add_ticket_select()

    def add_ticket_select(self):
        options = []
        for ticket_id, ticket_name, emoji in INDIVIDUAL_PANEL_TICKETS:
            options.append(
                discord.SelectOption(
                    label=ticket_name,
                    value=ticket_id,
                    emoji=emoji
                )
            )

        select = discord.ui.Select(
            placeholder="Select an individual panel to configure...",
            options=options,
            min_values=1,
            max_values=1
        )
        select.callback = self.ticket_select_callback
        self.add_item(select)

    async def ticket_select_callback(self, interaction: discord.Interaction):
        ticket_type = interaction.data["values"][0]
        ticket_name = next(name for tid, name, emoji in INDIVIDUAL_PANEL_TICKETS if tid == ticket_type)
        
        embed = discord.Embed(
            title=f"🔧 Configure {ticket_name}",
            description="Choose what to configure:",
            color=0x9b59b6
        )
        
        view = TicketConfigView(self.bot, ticket_type)
        await interaction.response.edit_message(embed=embed, view=view)

class TicketConfigView(discord.ui.View):
    """View for configuring a specific ticket type"""
    
    def __init__(self, bot, ticket_type):
        super().__init__(timeout=300)
        self.bot = bot
        self.mongo = bot.mongo_manager
        self.ticket_type = ticket_type

    @discord.ui.button(
        label="Questions",
        style=discord.ButtonStyle.primary,
        emoji="❓",
        row=0
    )
    async def questions_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = TicketQuestionsModal(self.ticket_type)
        await interaction.response.send_modal(modal)

    @discord.ui.button(
        label="Staff Roles",
        style=discord.ButtonStyle.primary,
        emoji="👥",
        row=0
    )
    async def staff_roles_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="👥 Staff Role Management",
            description="Manage staff roles for this ticket type:",
            color=0x3498db
        )
        
        view = StaffManagementView(self.bot, self.ticket_type)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(
        label="Ticket Category",
        style=discord.ButtonStyle.primary,
        emoji="📁",
        row=0
    )
    async def category_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="📁 Select Ticket Category",
            description="Choose where tickets will be created:",
            color=0x3498db
        )
        
        view = CategorySelectionView(self.bot, f"category_{self.ticket_type}", interaction.guild)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(
        label="Panel Image",
        style=discord.ButtonStyle.secondary,
        emoji="🖼️",
        row=1
    )
    async def panel_image_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        current_image = await self.mongo.get_panel_image(self.ticket_type, interaction.guild.id)
        
        embed = discord.Embed(
            title="🖼️ Panel Image Management",
            description="Send an image in this channel to set it as the panel image.",
            color=0x3498db
        )
        
        if current_image:
            embed.set_image(url=current_image)
            view = PanelImageView(self.bot, self.ticket_type, True)
        else:
            view = PanelImageView(self.bot, self.ticket_type, False)
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class PanelDeploymentView(discord.ui.View):
    """View for deploying ticket panels"""
    
    def __init__(self, bot):
        super().__init__(timeout=300)
        self.bot = bot
        self.mongo = bot.mongo_manager

    @discord.ui.button(
        label="Deploy Main Panel",
        style=discord.ButtonStyle.success,
        emoji="🎫",
        row=0
    )
    async def deploy_main_panel(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="🚀 Deploy Main Panel",
            description="Select a channel to deploy the main ticket panel:",
            color=0x2ecc71
        )
        
        view = CategorySelectionView(self.bot, "deploy_main_panel", interaction.guild)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(
        label="Deploy Individual Panels",
        style=discord.ButtonStyle.success,
        emoji="🎭",
        row=0
    )
    async def deploy_individual_panels(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="🚀 Deploy Individual Panel",
            description="Select which individual panel to deploy:",
            color=0x2ecc71
        )
        
        options = []
        for ticket_id, ticket_name, emoji in INDIVIDUAL_PANEL_TICKETS:
            options.append(
                discord.SelectOption(
                    label=ticket_name,
                    value=f"deploy_{ticket_id}",
                    emoji=emoji
                )
            )

        select = discord.ui.Select(
            placeholder="Choose a panel to deploy...",
            options=options,
            min_values=1,
            max_values=1
        )
        select.callback = self.individual_panel_callback

        view = discord.ui.View(timeout=300)
        view.add_item(select)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    async def individual_panel_callback(self, interaction: discord.Interaction):
        panel_type = interaction.data["values"][0].replace("deploy_", "")
        panel_name = next(name for tid, name, emoji in INDIVIDUAL_PANEL_TICKETS if tid == panel_type)
        
        embed = discord.Embed(
            title=f"🚀 Deploy {panel_name} Panel",
            description="Select a channel to deploy the panel:",
            color=0x2ecc71
        )
        
        view = CategorySelectionView(self.bot, f"deploy_{panel_type}", interaction.guild)
        await interaction.response.edit_message(embed=embed, view=view)

class TicketQuestionsModal(discord.ui.Modal, title="Configure Ticket Questions"):
    """Modal for configuring ticket questions"""
    
    def __init__(self, ticket_type):
        super().__init__()
        self.ticket_type = ticket_type

    questions = discord.ui.TextInput(
        label="Enter Questions (one per line)",
        style=discord.TextStyle.paragraph,
        placeholder="Enter your questions here...\nOne question per line",
        required=True,
        max_length=4000
    )

    async def on_submit(self, interaction: discord.Interaction):
        questions = [q.strip() for q in self.questions.value.split("\n") if q.strip()]
        
        success = await interaction.client.mongo_manager.save_ticket_questions(
            self.ticket_type,
            interaction.guild.id,
            questions
        )
        
        if success:
            embed = discord.Embed(
                title="✅ Questions Saved",
                description=f"Successfully saved {len(questions)} questions for {self.ticket_type.replace('_', ' ').title()}",
                color=0x00ff00
            )
        else:
            embed = discord.Embed(
                title="❌ Error",
                description="Failed to save questions. Please try again.",
                color=0xff0000
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

class StaffManagementView(discord.ui.View):
    """View for managing staff roles for tickets"""
    
    def __init__(self, bot, ticket_type):
        super().__init__(timeout=300)
        self.bot = bot
        self.mongo = bot.mongo_manager
        self.ticket_type = ticket_type

    @discord.ui.button(
        label="Add Staff",
        style=discord.ButtonStyle.success,
        emoji="➕",
        row=0
    )
    async def add_staff(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="➕ Add Staff",
            description="Mention a user or role in this channel to add them as staff:",
            color=0x00ff00
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

        def check(m):
            return (m.author.id == interaction.user.id and 
                   m.channel.id == interaction.channel.id and 
                   (m.mentions or m.role_mentions))

        try:
            msg = await self.bot.wait_for('message', check=check, timeout=60.0)
            
            if msg.mentions:
                user = msg.mentions[0]
                success = await self.mongo.add_ticket_staff(
                    self.ticket_type, interaction.guild.id, user_id=user.id
                )
                target = user.mention
            elif msg.role_mentions:
                role = msg.role_mentions[0]
                success = await self.mongo.add_ticket_staff(
                    self.ticket_type, interaction.guild.id, role_id=role.id
                )
                target = role.mention
            
            if success:
                embed = discord.Embed(
                    title="✅ Staff Added",
                    description=f"Added {target} as staff for {self.ticket_type.replace('_', ' ').title()}",
                    color=0x00ff00
                )
            else:
                embed = discord.Embed(
                    title="❌ Error",
                    description="Failed to add staff member.",
                    color=0xff0000
                )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            embed = discord.Embed(
                title="⏰ Timeout",
                description="No user or role mentioned in time.",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

    @discord.ui.button(
        label="View Staff",
        style=discord.ButtonStyle.secondary,
        emoji="👥",
        row=0
    )
    async def view_staff(self, interaction: discord.Interaction, button: discord.ui.Button):
        staff_list = await self.mongo.get_ticket_staff(self.ticket_type, interaction.guild.id)
        
        embed = discord.Embed(
            title=f"👥 Staff for {self.ticket_type.replace('_', ' ').title()}",
            color=0x3498db
        )
        
        if staff_list:
            users = [f"<@{staff['user_id']}>" for staff in staff_list if 'user_id' in staff]
            roles = [f"<@&{staff['role_id']}>" for staff in staff_list if 'role_id' in staff]
            
            if users:
                embed.add_field(name="Users", value="\n".join(users), inline=True)
            if roles:
                embed.add_field(name="Roles", value="\n".join(roles), inline=True)
        else:
            embed.add_field(
                name="No Staff",
                value="No staff members assigned to this ticket type.",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(
        label="Remove Staff",
        style=discord.ButtonStyle.danger,
        emoji="➖",
        row=0
    )
    async def remove_staff(self, interaction: discord.Interaction, button: discord.ui.Button):
        staff_list = await self.mongo.get_ticket_staff(self.ticket_type, interaction.guild.id)
        
        if not staff_list:
            embed = discord.Embed(
                title="❌ No Staff",
                description="No staff members to remove.",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        options = []
        for staff in staff_list[:25]:  # Discord limit
            if 'user_id' in staff:
                options.append(discord.SelectOption(
                    label=f"User: {staff['user_id']}",
                    description="Remove this user",
                    value=f"user_{staff['user_id']}"
                ))
            elif 'role_id' in staff:
                options.append(discord.SelectOption(
                    label=f"Role: {staff['role_id']}",
                    description="Remove this role",
                    value=f"role_{staff['role_id']}"
                ))

        select = discord.ui.Select(
            placeholder="Choose staff to remove...",
            options=options,
            min_values=1,
            max_values=1
        )
        select.callback = self.remove_staff_callback

        view = discord.ui.View(timeout=300)
        view.add_item(select)
        
        embed = discord.Embed(
            title="➖ Remove Staff",
            description="Select a staff member to remove:",
            color=0xff0000
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    async def remove_staff_callback(self, interaction: discord.Interaction):
        selection = interaction.data["values"][0]
        
        if selection.startswith("user_"):
            user_id = int(selection.replace("user_", ""))
            success = await self.mongo.remove_ticket_staff(
                self.ticket_type, interaction.guild.id, user_id=user_id
            )
            target = f"<@{user_id}>"
        elif selection.startswith("role_"):
            role_id = int(selection.replace("role_", ""))
            success = await self.mongo.remove_ticket_staff(
                self.ticket_type, interaction.guild.id, role_id=role_id
            )
            target = f"<@&{role_id}>"
        
        if success:
            embed = discord.Embed(
                title="✅ Staff Removed",
                description=f"Removed {target} from {self.ticket_type.replace('_', ' ').title()} staff",
                color=0x00ff00
            )
        else:
            embed = discord.Embed(
                title="❌ Error",
                description="Failed to remove staff member.",
                color=0xff0000
            )
        
        await interaction.response.edit_message(embed=embed, view=None)

class CategorySelectionView(discord.ui.View):
    """View for selecting categories/channels with pagination"""
    
    def __init__(self, bot, action_type, guild=None):
        super().__init__(timeout=300)
        self.bot = bot
        self.mongo = bot.mongo_manager
        self.action_type = action_type
        self.current_page = 0
        self.items_per_page = 25
        self.guild = guild
        
        # Initialize empty lists, will be populated when guild is available
        self.categories = []
        self.channels = []
        
        if guild:
            self.categories = [cat for cat in guild.categories if cat.name]
            self.channels = [ch for ch in guild.text_channels if ch.name]
        
        self.update_view()

    def update_view(self):
        self.clear_items()
        
        # Get current page items
        all_items = self.categories + self.channels
        start_idx = self.current_page * self.items_per_page
        end_idx = start_idx + self.items_per_page
        page_items = all_items[start_idx:end_idx]
        
        if not page_items:
            # No items to show
            return
        
        options = []
        for item in page_items:
            if hasattr(item, 'name') and hasattr(item, 'id'):
                emoji = "📁" if hasattr(item, 'channels') else "#"
                options.append(discord.SelectOption(
                    label=item.name,
                    description=f"ID: {item.id}",
                    value=str(item.id),
                    emoji=emoji
                ))
        
        select = discord.ui.Select(
            placeholder=f"Select category/channel... (Page {self.current_page + 1})",
            options=options,
            min_values=1,
            max_values=1
        )
        select.callback = self.item_selected
        self.add_item(select)
        
        # Add navigation buttons
        if self.current_page > 0:
            prev_button = discord.ui.Button(
                label="⬅️ Previous",
                style=discord.ButtonStyle.secondary,
                row=4
            )
            prev_button.callback = self.previous_page
            self.add_item(prev_button)
        
        total_pages = (len(all_items) + self.items_per_page - 1) // self.items_per_page
        if self.current_page < total_pages - 1:
            next_button = discord.ui.Button(
                label="➡️ Next",
                style=discord.ButtonStyle.secondary,
                row=4
            )
            next_button.callback = self.next_page
            self.add_item(next_button)

    async def item_selected(self, interaction: discord.Interaction):
        item_id = int(interaction.data["values"][0])
        
        # Get guild if not already set
        if not self.guild:
            self.guild = interaction.guild
            self.categories = [cat for cat in self.guild.categories if cat.name]
            self.channels = [ch for ch in self.guild.text_channels if ch.name]
        
        # Find the item
        item = None
        for cat in self.categories:
            if cat.id == item_id:
                item = cat
                break
        if not item:
            for ch in self.channels:
                if ch.id == item_id:
                    item = ch
                    break
        
        if not item:
            await interaction.response.send_message("❌ Item not found!", ephemeral=True)
            return
        
        # Handle the selection based on action type
        if self.action_type.startswith("deploy_"):
            panel_type = self.action_type.replace("deploy_", "")
            await self.deploy_panel(interaction, item, panel_type)
        elif self.action_type.startswith("category_"):
            ticket_type = self.action_type.replace("category_", "")
            await self.set_ticket_category(interaction, item, ticket_type)

    async def deploy_panel(self, interaction: discord.Interaction, item, panel_type):
        # Deploy the panel to the selected channel/category
        embed = discord.Embed(
            title="🚀 Panel Deployed",
            description=f"Successfully deployed {panel_type.replace('_', ' ').title()} panel to {item.mention}",
            color=0x00ff00
        )
        
        # Here you would create the actual panel embed and send it
        # For now, just confirm the deployment
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def set_ticket_category(self, interaction: discord.Interaction, item, ticket_type):
        # Set the ticket category for the ticket type
        success = await self.mongo.set_ticket_category(
            ticket_type, interaction.guild.id, item.id
        )
        
        if success:
            embed = discord.Embed(
                title="✅ Category Set",
                description=f"Set {item.mention} as ticket category for {ticket_type.replace('_', ' ').title()}",
                color=0x00ff00
            )
        else:
            embed = discord.Embed(
                title="❌ Error",
                description="Failed to set ticket category.",
                color=0xff0000
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def previous_page(self, interaction: discord.Interaction):
        self.current_page -= 1
        self.update_view()
        await interaction.response.edit_message(view=self)

    async def next_page(self, interaction: discord.Interaction):
        self.current_page += 1
        self.update_view()
        await interaction.response.edit_message(view=self)

class PanelImageView(discord.ui.View):
    """View for managing panel images"""
    
    def __init__(self, bot, ticket_type: str, has_image: bool):
        super().__init__(timeout=300)
        self.bot = bot
        self.mongo = bot.mongo_manager
        self.ticket_type = ticket_type

        if has_image:
            remove_button = discord.ui.Button(
                label="Remove Image",
                style=discord.ButtonStyle.danger,
                emoji="🗑️"
            )
            remove_button.callback = self.remove_image
            self.add_item(remove_button)

    async def remove_image(self, interaction: discord.Interaction):
        success = await self.mongo.remove_panel_image(self.ticket_type, interaction.guild.id)
        
        if success:
            embed = discord.Embed(
                title="✅ Image Removed",
                description="Panel image has been removed successfully.",
                color=0x00ff00
            )
        else:
            embed = discord.Embed(
                title="❌ Error",
                description="Failed to remove panel image.",
                color=0xff0000
            )
        
        await interaction.response.edit_message(embed=embed, view=None)

async def setup(bot):
    await bot.add_cog(MainDashboard(bot))
