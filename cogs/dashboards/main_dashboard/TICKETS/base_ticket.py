import discord
from discord.ext import commands
from typing import Dict, List, Optional
from abc import ABC, abstractmethod

class BaseTicketHandler(ABC):
    """Base class for all ticket handlers"""
    
    def __init__(self, bot):
        self.bot = bot
        self.mongo = bot.mongo_manager

    async def start_ticket(self, interaction: discord.Interaction):
        """Start the ticket process"""
        try:
            # Create the ticket channel
            ticket_channel = await self._create_ticket_channel(interaction)
            if not ticket_channel:
                await interaction.response.send_message(
                    "❌ Failed to create ticket channel. Please try again.",
                    ephemeral=True
                )
                return

            # Create ticket in database
            success = await self.mongo.create_ticket(
                guild_id=interaction.guild_id,
                channel_id=ticket_channel.id,
                user_id=interaction.user.id,
                ticket_type=self.get_ticket_type()
            )

            if not success:
                await ticket_channel.delete()
                await interaction.response.send_message(
                    "❌ Failed to create ticket. Please try again.",
                    ephemeral=True
                )
                return

            # Send initial message
            await self._send_initial_message(interaction, ticket_channel)
            
            # Start the actual ticket process
            await self._start_ticket_process(interaction, ticket_channel)

        except Exception as e:
            await interaction.response.send_message(
                f"❌ An error occurred: {str(e)}",
                ephemeral=True
            )

    @abstractmethod
    def get_ticket_type(self) -> str:
        """Get the ticket type identifier"""
        pass

    @abstractmethod
    async def _start_ticket_process(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Start the actual ticket process"""
        pass

    async def _create_ticket_channel(self, interaction: discord.Interaction) -> Optional[discord.TextChannel]:
        """Create a ticket channel"""
        try:
            # Get ticket category
            category = await self._get_tickets_category(interaction.guild)
            if not category:
                return None

            # Create channel name
            channel_name = f"{self.get_ticket_type()}-{interaction.user.name}"

            # Create channel with proper permissions
            channel = await category.create_text_channel(
                name=channel_name,
                reason=f"Ticket created by {interaction.user}"
            )

            # Set permissions
            await channel.set_permissions(
                interaction.guild.default_role,
                read_messages=False
            )
            await channel.set_permissions(
                interaction.user,
                read_messages=True,
                send_messages=True
            )
            await channel.set_permissions(
                interaction.guild.me,
                read_messages=True,
                send_messages=True,
                manage_channels=True,
                manage_permissions=True
            )

            return channel

        except Exception as e:
            print(f"Error creating ticket channel: {e}")
            return None

    async def _get_tickets_category(self, guild: discord.Guild) -> Optional[discord.CategoryChannel]:
        """Get or create the tickets category"""
        try:
            # Look for existing category
            for category in guild.categories:
                if category.name.lower() == "tickets":
                    return category

            # Create new category if not found
            return await guild.create_category(
                name="Tickets",
                reason="Ticket system setup"
            )

        except Exception as e:
            print(f"Error getting tickets category: {e}")
            return None

    async def _send_initial_message(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Send initial ticket message"""
        embed = discord.Embed(
            title=f"Welcome to your {self.get_ticket_type().replace('_', ' ').title()} Ticket!",
            description=(
                f"Hey {interaction.user.mention}! Welcome to your ticket.\n\n"
                "Please answer the questions that will follow to proceed with your request.\n"
                "A staff member will assist you shortly."
            ),
            color=0x00ff00
        )
        embed.set_footer(text="Blackspire Nation Support")
        
        await channel.send(embed=embed)