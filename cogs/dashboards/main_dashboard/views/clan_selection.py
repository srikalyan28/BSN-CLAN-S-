import discord
from typing import List, Dict

class ClanSelectionView(discord.ui.View):
    def __init__(self, clans: List[Dict]):
        super().__init__(timeout=300)
        self.value = None
        self.clans = clans
        self.setup_options()

    def setup_options(self):
        # Create a select menu for clans
        select = discord.ui.Select(
            placeholder="Choose a clan to join...",
            min_values=1,
            max_values=1,
            options=[
                discord.SelectOption(
                    label=clan['name'],
                    description=f"TH{clan['th_requirement']}+ | {clan['focus']}",
                    emoji="🛡️",
                    value=clan['name']
                ) for clan in self.clans
            ] if self.clans else [
                discord.SelectOption(
                    label="No Available Clans",
                    description="No clans match your requirements",
                    emoji="❌",
                    value="none"
                )
            ]
        )

        async def select_callback(interaction: discord.Interaction):
            selected_clan = next((clan for clan in self.clans if clan['name'] == select.values[0]), None)
            if selected_clan:
                self.value = selected_clan
                embed = discord.Embed(
                    title="✅ Clan Selected",
                    description=f"You've selected {selected_clan['name']}!\n\n**Requirements:**\n• TH{selected_clan['th_requirement']}+\n• Focus: {selected_clan['focus']}\n\n*Staff will review your application soon.*",
                    color=0x2ecc71
                )
                await interaction.response.edit_message(embed=embed, view=None)
            self.stop()

        select.callback = select_callback
        self.add_item(select)

        # Add a cancel button
        cancel = discord.ui.Button(
            style=discord.ButtonStyle.danger,
            label="Cancel",
            emoji="❌"
        )

        async def cancel_callback(interaction: discord.Interaction):
            self.value = None
            await interaction.response.edit_message(
                embed=discord.Embed(
                    title="❌ Cancelled",
                    description="Clan selection cancelled.",
                    color=0xff0000
                ),
                view=None
            )
            self.stop()

        cancel.callback = cancel_callback
        self.add_item(cancel)