import discord
from discord.ext import commands
import asyncio
from typing import Dict, Optional
from datetime import datetime

class TicketHandler:
    def __init__(self, bot):
        self.bot = bot
        self.mongo = bot.mongo_manager

    async def handle_ticket(self, interaction: discord.Interaction, ticket_data: Dict):
        try:
            # Create private thread for giveaway claim processing
            thread = await interaction.channel.create_thread(
                name=f"Giveaway Claim - {interaction.user.name}",
                type=discord.ChannelType.private_thread
            )

            # Initial embed
            embed = discord.Embed(
                title="🎁 Giveaway Prize Claim",
                description="Congratulations on winning! Let's process your prize claim.",
                color=0xe74c3c
            )
            await interaction.response.send_message(embed=embed, ephemeral=False)

            # Get claim questions
            questions = await self.mongo.get_ticket_questions('giveaway_claim')
            responses = {}

            # Get giveaway details
            details_embed = discord.Embed(
                title="🏆 Prize Details",
                description="Please provide the following information:",
                color=0xe74c3c
            )
            await interaction.followup.send(embed=details_embed)

            # Ask each question
            for i, question in enumerate(questions, 1):
                question_embed = discord.Embed(
                    title=f"Question {i}/{len(questions)}",
                    description=question,
                    color=0xe74c3c
                )
                await interaction.followup.send(embed=question_embed)

                def check(m):
                    return m.author == interaction.user and m.channel == interaction.channel

                try:
                    response = await self.bot.wait_for('message', timeout=300.0, check=check)
                    responses[question] = response.content

                except asyncio.TimeoutError:
                    await interaction.followup.send("Claim process timed out. Please try again.", ephemeral=True)
                    return

            # Create summary embed for staff
            summary_embed = discord.Embed(
                title="🎁 New Giveaway Claim",
                description=f"Winner: {interaction.user.mention}",
                color=0xe74c3c,
                timestamp=datetime.utcnow()
            )

            for question, answer in responses.items():
                summary_embed.add_field(
                    name=question,
                    value=answer,
                    inline=False
                )

            # Add claim processing controls
            view = GiveawayClaimControls(self.bot)
            await thread.send(
                content="New giveaway claim received!",
                embed=summary_embed,
                view=view
            )

            # Notify winner
            await interaction.followup.send(
                "Your claim has been submitted! Our staff will process it shortly.",
                ephemeral=False
            )

            # Save claim to database
            await self.mongo.save_ticket('giveaway_claim', {
                'user_id': interaction.user.id,
                'responses': responses,
                'thread_id': thread.id,
                'status': 'pending',
                'claim_date': datetime.utcnow().isoformat()
            })

        except Exception as e:
            await interaction.followup.send(
                f"An error occurred while processing your claim. Please try again later.\nError: {str(e)}",
                ephemeral=True
            )
            raise

class GiveawayClaimControls(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Process Claim", style=discord.ButtonStyle.success, emoji="✅")
    async def process_claim(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = ClaimProcessingModal()
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Request Info", style=discord.ButtonStyle.primary, emoji="❓")
    async def request_info(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = InfoRequestModal()
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Mark Invalid", style=discord.ButtonStyle.danger, emoji="❌")
    async def mark_invalid(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = InvalidClaimModal()
        await interaction.response.send_modal(modal)

class ClaimProcessingModal(discord.ui.Modal, title="Process Giveaway Claim"):
    prize_details = discord.ui.TextInput(
        label="Prize Details",
        style=discord.TextStyle.paragraph,
        placeholder="Enter the exact prize details...",
        required=True
    )
    
    delivery_info = discord.ui.TextInput(
        label="Delivery Information",
        style=discord.TextStyle.paragraph,
        placeholder="Enter how and when the prize will be delivered...",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🎉 Prize Claim Processed!",
            description="Your giveaway prize claim has been processed!",
            color=0x00ff00
        )
        embed.add_field(
            name="Prize Details",
            value=self.prize_details.value,
            inline=False
        )
        embed.add_field(
            name="Delivery Information",
            value=self.delivery_info.value,
            inline=False
        )

        thread = interaction.channel
        original_message = await thread.fetch_message(thread.id)
        winner_id = int(original_message.embeds[0].description.split('<@')[1].split('>')[0])
        winner = interaction.guild.get_member(winner_id)

        if winner:
            await winner.send(embed=embed)

        await interaction.client.mongo.update_ticket_status(
            thread.id,
            'processed',
            interaction.user.id,
            {
                'prize_details': self.prize_details.value,
                'delivery_info': self.delivery_info.value
            }
        )
        await interaction.response.send_message("Claim processed! The winner has been notified.")

class InfoRequestModal(discord.ui.Modal, title="Request Additional Information"):
    info_needed = discord.ui.TextInput(
        label="Information Needed",
        style=discord.TextStyle.paragraph,
        placeholder="Specify what additional information is needed...",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="ℹ️ Additional Information Needed",
            description="We need some additional information to process your prize claim.",
            color=0x3498db
        )
        embed.add_field(
            name="Information Required",
            value=self.info_needed.value,
            inline=False
        )

        thread = interaction.channel
        original_message = await thread.fetch_message(thread.id)
        winner_id = int(original_message.embeds[0].description.split('<@')[1].split('>')[0])
        winner = interaction.guild.get_member(winner_id)

        if winner:
            await winner.send(embed=embed)

        await interaction.client.mongo.update_ticket_status(
            thread.id,
            'info_requested',
            interaction.user.id,
            {'requested_info': self.info_needed.value}
        )
        await interaction.response.send_message("Information request sent! The winner has been notified.")

class InvalidClaimModal(discord.ui.Modal, title="Mark Claim as Invalid"):
    reason = discord.ui.TextInput(
        label="Reason",
        style=discord.TextStyle.paragraph,
        placeholder="Explain why this claim is invalid...",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="❌ Invalid Prize Claim",
            description="Your prize claim has been marked as invalid.",
            color=0xff0000
        )
        embed.add_field(
            name="Reason",
            value=self.reason.value,
            inline=False
        )
        embed.add_field(
            name="What Next?",
            value="If you believe this is a mistake, please open a help & support ticket.",
            inline=False
        )

        thread = interaction.channel
        original_message = await thread.fetch_message(thread.id)
        winner_id = int(original_message.embeds[0].description.split('<@')[1].split('>')[0])
        winner = interaction.guild.get_member(winner_id)

        if winner:
            await winner.send(embed=embed)

        await interaction.client.mongo.update_ticket_status(
            thread.id,
            'invalid',
            interaction.user.id,
            {'reason': self.reason.value}
        )
        await interaction.response.send_message("Claim marked as invalid! The user has been notified.")
