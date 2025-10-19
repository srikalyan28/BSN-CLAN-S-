import discord
from typing import Optional, List
import math
from ...booster_dashboard.views.booster_panel import BoosterPanelView
from ..views.main_panel import MainPanelView

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
        
    async def channel_selected(self, interaction: discord.Interaction):
        try:
            channel_id = int(interaction.data['values'][0])
            channel = interaction.guild.get_channel(channel_id)
            
            if not channel:
                await interaction.response.send_message(
                    "❌ Selected channel not found. Please try again.",
                    ephemeral=True
                )
                return

            if self.panel_type == "main_panel":
                await self._deploy_main_panel(interaction, channel)
            elif self.panel_type == "booster_panel":
                await self._deploy_booster_panel(interaction, channel)
            else:
                await self._deploy_ticket_panel(interaction, channel)

        except Exception as e:
            await interaction.response.send_message(
                f"❌ An error occurred: {str(e)}",
                ephemeral=True
            )

    async def _deploy_main_panel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Deploy main ticket panel"""
        try:
            panel_image = await self.mongo.get_panel_image("main_panel", interaction.guild.id)
            # Create and send the main panel embed
            embed = discord.Embed(
                title="🎫 BLACKSPIRE NATION - Support Center",
                description=(
                    "Welcome to the Blackspire Nation Support Center!\n\n"
                    "Select a ticket type from below to get started."
                ),
                color=0x00ff33
            )
            if panel_image:
                embed.set_image(url=panel_image)
                
            await channel.send(embed=embed, view=MainPanelView(self.bot))
            await interaction.response.send_message(
                f"✅ Main panel deployed in {channel.mention}!",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Failed to deploy main panel: {str(e)}",
                ephemeral=True
            )

    async def _deploy_booster_panel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Deploy booster panel"""
        try:
            panel_image = await self.mongo.get_panel_image("booster_panel", interaction.guild.id)
            color_roles = await self.mongo.get_color_roles(interaction.guild.id)
            
            if not color_roles:
                await interaction.response.send_message(
                    "❌ Please configure color roles before deploying the booster panel.",
                    ephemeral=True
                )
                return

            view = BoosterPanelView(self.bot, color_roles, panel_image)
            await channel.send(embed=view.get_embed(), view=view)
            await interaction.response.send_message(
                f"✅ Booster panel deployed in {channel.mention}!",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Failed to deploy booster panel: {str(e)}",
                ephemeral=True
            )

    async def _deploy_ticket_panel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Deploy individual ticket panel"""
        try:
            panel_image = await self.mongo.get_panel_image(self.panel_type, interaction.guild.id)
            # Create and send the individual panel embed
            embed = discord.Embed(
                title=f"🎫 {self.panel_type.replace('_', ' ').title()}",
                description="Click the button below to create a ticket.",
                color=0x00ff33
            )
            if panel_image:
                embed.set_image(url=panel_image)
                
            # Get the appropriate ticket view based on panel type
            view = self.bot.ticket_handlers[self.panel_type].get_panel_view()
            await channel.send(embed=embed, view=view)
            await interaction.response.send_message(
                f"✅ {self.panel_type.replace('_', ' ').title()} panel deployed in {channel.mention}!",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Failed to deploy panel: {str(e)}",
                ephemeral=True
            )

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
        self.total_pages = math.ceil(len(channels) / self.channels_per_page)
        
            # Add channel select dropdown
        start_idx = self.page * self.channels_per_page
        end_idx = min(start_idx + self.channels_per_page, len(channels))
        
        page_channels = channels[start_idx:end_idx]
        if page_channels:
            options = [
                discord.SelectOption(
                    label=ch.name,
                    value=str(ch.id),
                    description=f"#{ch.name} in {ch.category.name if ch.category else 'No Category'}"
                )
                for ch in page_channels
            ]
            
            select = discord.ui.Select(
                placeholder="Select a channel...",
                options=options,
                min_values=1,
                max_values=1,
                row=0
            )
            select.callback = self.channel_selected
            self.add_item(select)        # Add navigation buttons if needed
        if self.page > 0:
            self.add_item(PreviousPageButton())
        if self.page < self.total_pages - 1:
            self.add_item(NextPageButton())
        
        # Add back button
        self.add_item(BackButton())
        
        # Add page indicator
        if self.total_pages > 1:
            self.add_item(PageIndicator(self.page + 1, self.total_pages))

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
        await self.view.mongo.save_panel_channel(self.view.panel_type, self.channel.id)
        
        embed = discord.Embed(
            title="✅ Channel Set",
            description=f"Panel will be deployed in {self.channel.mention}",
            color=0x00ff00
        )
        
        # Return to main dashboard
        from ..views import MainDashboardView
        view = MainDashboardView(self.view.bot)
        
        await interaction.response.defer()
        await interaction.followup.send(embed=embed, view=view)

class PreviousPageButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Previous",
            style=discord.ButtonStyle.primary,
            emoji="⬅️",
            custom_id="prev_page",
            row=3
        )
    
    async def callback(self, interaction: discord.Interaction):
        self.view.page -= 1
        self.view._refresh_buttons()
        
        embed = discord.Embed(
            title="📋 Channel Selection",
            description=f"Select a channel to deploy the {self.view.panel_type} panel:",
            color=0x00ff00
        )
        await interaction.response.edit_message(embed=embed, view=self.view)

class NextPageButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Next",
            style=discord.ButtonStyle.primary,
            emoji="➡️",
            custom_id="next_page",
            row=3
        )
    
    async def callback(self, interaction: discord.Interaction):
        self.view.page += 1
        self.view._refresh_buttons()
        
        embed = discord.Embed(
            title="📋 Channel Selection", 
            description=f"Select a channel to deploy the {self.view.panel_type} panel:",
            color=0x00ff00
        )
        await interaction.response.edit_message(embed=embed, view=self.view)

class BackButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Back",
            style=discord.ButtonStyle.danger,
            emoji="⬅️",
            custom_id="back_button",
            row=4
        )

    async def callback(self, interaction: discord.Interaction):
        # Return to the main dashboard view
        from ..views import MainDashboardView
        view = MainDashboardView(self.view.bot)
        
        embed = discord.Embed(
            title="🎫 BLACKSPIRE NATION - Main Dashboard",
            description="**Ticket Management Hub**\n\nManage all ticketing systems for the server:",
            color=0x00ff00
        )
        await interaction.response.defer()
        await interaction.followup.send(embed=embed, view=view)

class PageIndicator(discord.ui.Button):
    def __init__(self, current_page: int, total_pages: int):
        super().__init__(
            label=f"Page {current_page}/{total_pages}",
            style=discord.ButtonStyle.secondary,
            disabled=True,
            row=4
        )

def create_channel_select_view(bot, panel_type: str, guild: discord.Guild) -> ChannelSelectionView:
    """
    Create a new channel selection view.
    
    Args:
        bot: The Discord bot instance
        panel_type: The type of panel being configured
        guild: The Discord guild where channels will be listed
        
    Returns:
        A configured ChannelSelectionView instance
    """
    return ChannelSelectionView(bot, panel_type, guild.id)