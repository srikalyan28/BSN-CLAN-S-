import discord
from typing import Dict, List, Optional
from datetime import datetime

class MainPanelView(discord.ui.View):
    """Persistent view for the main ticket panel"""
    
    def __init__(self, bot):
        super().__init__(timeout=None)  # Make view persistent
        self.bot = bot
        self.mongo = bot.mongo_manager
        self.ticket_types = [
            ("join_clan", "Join Clan", "⚔️"),
            ("apply_clan", "Apply Your Clan", "🛡️"),
            ("staff_application", "Staff Application", "👔"),
            ("partnership_application", "Partnership Application", "🤝"),
            ("esports_application", "Esports Application", "🎮"),
            ("giveaway_claim", "Giveaway Claim", "🎁")
        ]
        self._add_buttons()

    def _add_buttons(self):
        """Add ticket buttons dynamically"""
        for i, (ticket_id, label, emoji) in enumerate(self.ticket_types):
            # Calculate row (2 buttons per row)
            row = i // 2
            
            # Create button with custom ID for persistence
            button = TicketButton(
                label=label,
                emoji=emoji,
                style=discord.ButtonStyle.primary,
                custom_id=f"ticket_{ticket_id}",
                row=row
            )
            self.add_item(button)

class TicketButton(discord.ui.Button):
    """Custom button class for ticket creation"""
    
    async def callback(self, interaction: discord.Interaction):
        """Handle button clicks"""
        try:
            # Get ticket type from custom_id
            ticket_type = self.custom_id.replace("ticket_", "")
            
            # Check if user has existing tickets
            existing_ticket = await self.view.mongo.get_active_ticket(
                guild_id=interaction.guild_id,
                user_id=interaction.user.id,
                ticket_type=ticket_type
            )
            
            if existing_ticket:
                await interaction.response.send_message(
                    f"❌ You already have an active {ticket_type.replace('_', ' ')} ticket!",
                    ephemeral=True
                )
                return

            # Get ticket handler
            ticket_handler = self.view.bot.ticket_handlers.get(ticket_type)
            if not ticket_handler:
                await interaction.response.send_message(
                    "❌ This ticket type is not currently available.",
                    ephemeral=True
                )
                return

            # Start ticket process
            await ticket_handler.start_ticket(interaction)

        except Exception as e:
            await interaction.response.send_message(
                f"❌ An error occurred: {str(e)}",
                ephemeral=True
            )