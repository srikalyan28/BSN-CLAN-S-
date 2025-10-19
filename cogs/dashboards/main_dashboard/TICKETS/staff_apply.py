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
            # Create private thread for staff review
            thread = await interaction.channel.create_thread(
                name=f"Staff Application - {interaction.user.name}",
                type=discord.ChannelType.private_thread
            )

            # Get staff application questions
            questions = await self.mongo.get_ticket_questions('staff_application')
            responses = {}

            # Send initial embed
            embed = discord.Embed(
                title="👥 Staff Application",
                description="Welcome to the staff application process! Please answer each question thoughtfully.",
                color=0x7289da
            )
            await interaction.response.send_message(embed=embed, ephemeral=False)

            # Ask each question
            for i, question in enumerate(questions, 1):
                question_embed = discord.Embed(
                    title=f"Question {i}/{len(questions)}",
                    description=question,
                    color=0x7289da
                )
                await interaction.followup.send(embed=question_embed)

                def check(m):
                    return m.author == interaction.user and m.channel == interaction.channel

                try:
                    response = await self.bot.wait_for('message', timeout=600.0, check=check)
                    responses[question] = response.content
                except asyncio.TimeoutError:
                    await interaction.followup.send("Application timed out. Please try again.", ephemeral=True)
                    return

            # Create summary embed for staff review
            summary_embed = discord.Embed(
                title="👥 New Staff Application",
                description=f"Applicant: {interaction.user.mention}",
                color=0x7289da
            )
            summary_embed.add_field(
                name="Joined Server",
                value=discord.utils.format_dt(interaction.user.joined_at, 'R') if interaction.user.joined_at else "Unknown",
                inline=True
            )
            summary_embed.add_field(
                name="Account Created",
                value=discord.utils.format_dt(interaction.user.created_at, 'R'),
                inline=True
            )

            for question, answer in responses.items():
                summary_embed.add_field(
                    name=question,
                    value=answer[:1024],  # Discord field value limit
                    inline=False
                )

            # Add staff review controls
            view = StaffApplicationControls(self.bot)
            await thread.send(
                content="New staff application received!",
                embed=summary_embed,
                view=view
            )

            # Notify applicant
            await interaction.followup.send(
                "Your staff application has been submitted! Our admin team will review it shortly.",
                ephemeral=False
            )

            # Save application to database
            await self.mongo.save_ticket('staff_application', {
                'user_id': interaction.user.id,
                'responses': responses,
                'thread_id': thread.id,
                'status': 'pending',
                'joined_at': interaction.user.joined_at.isoformat() if interaction.user.joined_at else None,
                'created_at': interaction.user.created_at.isoformat()
            })

        except Exception as e:
            await interaction.followup.send(
                f"An error occurred while processing your application. Please try again later.\nError: {str(e)}",
                ephemeral=True
            )
            raise

class StaffApplicationControls(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.success, emoji="✅")
    async def accept_application(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = AcceptanceModal()
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Schedule Interview", style=discord.ButtonStyle.primary, emoji="📅")
    async def schedule_interview(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = InterviewScheduleModal()
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Reject", style=discord.ButtonStyle.danger, emoji="❌")
    async def reject_application(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = RejectionModal()
        await interaction.response.send_modal(modal)

class AcceptanceModal(discord.ui.Modal, title="Accept Staff Application"):
    welcome_message = discord.ui.TextInput(
        label="Welcome Message",
        style=discord.TextStyle.paragraph,
        placeholder="Enter a personalized welcome message for the new staff member...",
        required=True,
        max_length=1000
    )
    
    next_steps = discord.ui.TextInput(
        label="Next Steps",
        style=discord.TextStyle.paragraph,
        placeholder="Outline the next steps for the new staff member...",
        required=True,
        max_length=1000
    )

    async def on_submit(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🎉 Staff Application Accepted!",
            description="Congratulations! Your application to join our staff team has been accepted!",
            color=0x00ff00
        )
        embed.add_field(
            name="Welcome Message",
            value=self.welcome_message.value,
            inline=False
        )
        embed.add_field(
            name="Next Steps",
            value=self.next_steps.value,
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
        await interaction.client.mongo.update_ticket_status(
            thread.id, 
            'accepted', 
            interaction.user.id,
            {'acceptance_message': self.welcome_message.value, 'next_steps': self.next_steps.value}
        )
        await interaction.response.send_message("Application accepted! The applicant has been notified.")

class InterviewScheduleModal(discord.ui.Modal, title="Schedule Staff Interview"):
    interview_date = discord.ui.TextInput(
        label="Interview Date/Time",
        placeholder="e.g., Tomorrow at 3 PM EST",
        required=True
    )
    
    interview_details = discord.ui.TextInput(
        label="Interview Details",
        style=discord.TextStyle.paragraph,
        placeholder="Enter any additional details or preparation instructions...",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📅 Staff Interview Scheduled",
            description="Your staff application has moved to the interview phase!",
            color=0x7289da
        )
        embed.add_field(
            name="Interview Date/Time",
            value=self.interview_date.value,
            inline=False
        )
        embed.add_field(
            name="Details",
            value=self.interview_details.value,
            inline=False
        )

        thread = interaction.channel
        original_message = await thread.fetch_message(thread.id)
        applicant_id = int(original_message.embeds[0].description.split('<@')[1].split('>')[0])
        applicant = interaction.guild.get_member(applicant_id)

        if applicant:
            await applicant.send(embed=embed)

        await interaction.client.mongo.update_ticket_status(
            thread.id,
            'interview_scheduled',
            interaction.user.id,
            {'interview_date': self.interview_date.value, 'interview_details': self.interview_details.value}
        )
        await interaction.response.send_message("Interview scheduled! The applicant has been notified.")

class RejectionModal(discord.ui.Modal, title="Reject Staff Application"):
    reason = discord.ui.TextInput(
        label="Reason for rejection",
        style=discord.TextStyle.paragraph,
        placeholder="Enter the reason for rejecting this application...",
        required=True,
        max_length=1000
    )
    
    feedback = discord.ui.TextInput(
        label="Constructive Feedback",
        style=discord.TextStyle.paragraph,
        placeholder="Provide constructive feedback for improvement...",
        required=True,
        max_length=1000
    )

    async def on_submit(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="❌ Staff Application Status",
            description="Thank you for your interest in joining our staff team.",
            color=0xff0000
        )
        embed.add_field(
            name="Status",
            value="We regret to inform you that your application has not been accepted at this time.",
            inline=False
        )
        embed.add_field(
            name="Reason",
            value=self.reason.value,
            inline=False
        )
        embed.add_field(
            name="Feedback",
            value=self.feedback.value,
            inline=False
        )
        embed.add_field(
            name="Note",
            value="You can apply again in the future after addressing the feedback provided.",
            inline=False
        )

        thread = interaction.channel
        original_message = await thread.fetch_message(thread.id)
        applicant_id = int(original_message.embeds[0].description.split('<@')[1].split('>')[0])
        applicant = interaction.guild.get_member(applicant_id)

        if applicant:
            await applicant.send(embed=embed)

        await interaction.client.mongo.update_ticket_status(
            thread.id,
            'rejected',
            interaction.user.id,
            {'reason': self.reason.value, 'feedback': self.feedback.value}
        )
        await interaction.response.send_message("Application rejected! The applicant has been notified.")
