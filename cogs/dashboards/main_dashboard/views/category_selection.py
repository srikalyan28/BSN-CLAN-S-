import discord
from typing import List, Optional
import math

class CategorySelectionView(discord.ui.View):
    def __init__(self, bot, ticket_type: str, guild_id: int, page: int = 0):
        super().__init__(timeout=300)
        self.bot = bot
        self.ticket_type = ticket_type
        self.guild_id = guild_id
        self.mongo = bot.mongo_manager
        self.page = page
        self.categories_per_page = 10  # Reduced for better UI
        self._refresh_buttons()

    def _refresh_buttons(self):
        # Clear existing buttons
        self.clear_items()
        
        # Get all categories from the guild
        guild = self.bot.get_guild(self.guild_id)
        if not guild:
            return
            
        categories = [cat for cat in guild.categories]
        categories.sort(key=lambda x: x.position)  # Sort by position
        
        # Calculate total pages
        self.total_pages = math.ceil(len(categories) / self.categories_per_page)
        
        # Add category buttons for current page
        start_idx = self.page * self.categories_per_page
        end_idx = min(start_idx + self.categories_per_page, len(categories))
        
        for category in categories[start_idx:end_idx]:
            button = CategoryButton(category)
            self.add_item(button)
        
        # Add navigation buttons if needed
        if self.page > 0:
            self.add_item(PreviousPageButton())
        if self.page < self.total_pages - 1:
            self.add_item(NextPageButton())
        
        # Add back button
        self.add_item(BackButton())
        
        # Add page indicator
        if self.total_pages > 1:
            self.add_item(PageIndicator(self.page + 1, self.total_pages))

class CategoryButton(discord.ui.Button):
    def __init__(self, category: discord.CategoryChannel):
        super().__init__(
            label=category.name,
            style=discord.ButtonStyle.secondary,
            custom_id=f"category_{category.id}"
        )
        self.category = category

    async def callback(self, interaction: discord.Interaction):
        await self.view.mongo.save_ticket_category(self.view.ticket_type, self.category.id)
        
        embed = discord.Embed(
            title="✅ Category Set",
            description=f"Tickets will now be created in the {self.category.name} category",
            color=0x00ff00
        )
        
        # Return to ticket config
        from ..views import StaffManagementView
        view = StaffManagementView(self.view.bot)
        
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
            title="📋 Category Selection",
            description="Select a category for tickets:",
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
            title="📋 Category Selection",
            description="Select a category for tickets:",
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
        # Return to the staff management view
        from ..views import StaffManagementView
        view = StaffManagementView(self.view.bot)
        
        embed = discord.Embed(
            title="👮‍♂️ Staff Management",
            description="Manage staff settings and permissions:",
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