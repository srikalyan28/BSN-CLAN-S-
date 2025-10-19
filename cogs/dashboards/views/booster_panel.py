import discord
from discord.ext import commands
from typing import List, Optional

class BoosterPanelView(discord.ui.View):
    def __init__(self, bot, color_roles: List[dict], panel_image: Optional[str] = None):
        super().__init__(timeout=None)  # Persistent view
        self.bot = bot
        self.color_roles = color_roles
        self.panel_image = panel_image

    @discord.ui.select(
        placeholder="Choose your color!",
        min_values=1,
        max_values=1,
        row=0
    )
    async def select_color(self, interaction: discord.Interaction, select: discord.ui.Select):
        try:
            selected_role_id = int(select.values[0])
            
            # Get all available color roles
            color_roles = await self.bot.mongo_manager.get_color_roles(interaction.guild.id)
            valid_role_ids = [role['role_id'] for role in color_roles]
            
            if selected_role_id not in valid_role_ids:
                await interaction.response.send_message(
                    "❌ This color role is no longer available.",
                    ephemeral=True
                )
                return
            
            # Remove existing color roles
            member = interaction.user
            for role in member.roles:
                if role.id in valid_role_ids:
                    await member.remove_roles(role)
            
            # Add selected role
            new_role = interaction.guild.get_role(selected_role_id)
            if new_role:
                await member.add_roles(new_role)
                await interaction.response.send_message(
                    f"✅ Your color has been changed to {new_role.mention}!",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    "❌ Could not find the selected role. Please contact an administrator.",
                    ephemeral=True
                )
                
        except Exception as e:
            await interaction.response.send_message(
                f"❌ An error occurred: {str(e)}",
                ephemeral=True
            )

    async def update_options(self, color_roles: List[dict]):
        """Update the select menu options with current color roles"""
        select = self.children[0]
        select.options = []
        
        for role in color_roles:
            role_obj = self.bot.get_guild(role['guild_id']).get_role(role['role_id'])
            if role_obj:
                select.add_option(
                    label=role_obj.name,
                    value=str(role_obj.id),
                    description=f"Color: {role['color_hex']}",
                )
                
    def get_embed(self) -> discord.Embed:
        """Get the panel embed"""
        embed = discord.Embed(
            title="🎨 Booster Color Selection",
            description=(
                "As a booster, you have access to exclusive color roles!\n\n"
                "Select a color from the menu below to change your name color."
            ),
            color=0xff69b4
        )
        
        if self.panel_image:
            embed.set_image(url=self.panel_image)
            
        return embed