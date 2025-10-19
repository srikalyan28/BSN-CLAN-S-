import discord
from discord.ext import commands
import asyncio
from typing import Dict, Optional

class TicketHandler:
    def __init__(self, bot):
        self.bot = bot
        self.mongo = bot.mongo_manager

    async def handle_ticket(self, interaction: discord.Interaction, ticket_data: Dict):
        try:
            # Create private thread for staff
            thread = await interaction.channel.create_thread(
                name=f"Clan Application - {interaction.user.name}",
                type=discord.ChannelType.private_thread
            )

            # Get the questions configured for this ticket type
            questions = await self.mongo.get_ticket_questions('apply_clan')
            responses = {}

            # Send initial embed
            embed = discord.Embed(
                title="🛡️ Clan Application",
                description="Welcome! Please answer the following questions about your clan.",
                color=0x2b2d31
            )
            await interaction.response.send_message(embed=embed, ephemeral=False)

            # Ask each question
            for i, question in enumerate(questions, 1):
                question_embed = discord.Embed(
                    title=f"Question {i}/{len(questions)}",
                    description=question,
                    color=0x2b2d31
                )
                await interaction.followup.send(embed=question_embed)

                def check(m):
                    return m.author == interaction.user and m.channel == interaction.channel

                try:
                    response = await self.bot.wait_for('message', timeout=300.0, check=check)
                    responses[question] = response.content
                except asyncio.TimeoutError:
                    await interaction.followup.send("Application timed out. Please try again.", ephemeral=True)
                    return

            # Create summary embed for staff
            summary_embed = discord.Embed(
                title="📝 New Clan Application",
                description=f"Applicant: {interaction.user.mention}",
                color=0x00ff00
            )

            for question, answer in responses.items():
                summary_embed.add_field(
                    name=question,
                    value=answer,
                    inline=False
                )

            # Add staff controls
            view = ClanApplicationControls(self.bot)
            await thread.send(
                content="New clan application received!",
                embed=summary_embed,
                view=view
            )

            # Notify applicant
            await interaction.followup.send(
                "Your clan application has been submitted! Our staff will review it shortly.",
                ephemeral=False
            )

            # Save application to database
            await self.mongo.save_ticket('apply_clan', {
                'user_id': interaction.user.id,
                'responses': responses,
                'thread_id': thread.id,
                'status': 'pending'
            })

        except Exception as e:
            await interaction.followup.send(
                f"An error occurred while processing your application. Please try again later.\nError: {str(e)}",
                ephemeral=True
            )
            raise

class ClanApplicationControls(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.success, emoji="✅")
    async def accept_application(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Create invite embed
        embed = discord.Embed(
            title="🎉 Clan Application Accepted!",
            description="Congratulations! Your clan application has been accepted.",
            color=0x00ff00
        )
        embed.add_field(
            name="Next Steps",
            value="Our staff will be in touch with you shortly to proceed with the alliance process.",
            inline=False
        )

        # Send acceptance message
        thread = interaction.channel
        original_message = await thread.fetch_message(thread.id)
        applicant_id = int(original_message.embeds[0].description.split('<@')[1].split('>')[0])
        applicant = interaction.guild.get_member(applicant_id)

        if applicant:
            await applicant.send(embed=embed)

        # Update ticket status
        await self.bot.mongo.update_ticket_status(thread.id, 'accepted', interaction.user.id)
        await interaction.response.send_message("Application accepted! The applicant has been notified.")

    @discord.ui.button(label="Reject", style=discord.ButtonStyle.danger, emoji="❌")
    async def reject_application(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Show rejection reason modal
        modal = RejectionModal()
        await interaction.response.send_modal(modal)

class RejectionModal(discord.ui.Modal, title="Rejection Reason"):
    reason = discord.ui.TextInput(
        label="Reason for rejection",
        style=discord.TextStyle.paragraph,
        placeholder="Enter the reason for rejecting this application...",
        required=True,
        max_length=1000
    )

    async def on_submit(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="❌ Clan Application Rejected",
            description="We regret to inform you that your clan application has been rejected.",
            color=0xff0000
        )
        embed.add_field(
            name="Reason",
            value=self.reason.value,
            inline=False
        )
        embed.add_field(
            name="Note",
            value="You can apply again in the future when you meet our requirements.",
            inline=False
        )

        # Send rejection message
        thread = interaction.channel
        original_message = await thread.fetch_message(thread.id)
        applicant_id = int(original_message.embeds[0].description.split('<@')[1].split('>')[0])
        applicant = interaction.guild.get_member(applicant_id)

        if applicant:
            await applicant.send(embed=embed)

        # Update ticket status
        await interaction.client.mongo.update_ticket_status(thread.id, 'rejected', interaction.user.id)
        await interaction.response.send_message("Application rejected! The applicant has been notified.")
