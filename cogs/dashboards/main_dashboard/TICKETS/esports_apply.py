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
            # Create private thread for esports application review
            thread = await interaction.channel.create_thread(
                name=f"Esports Application - {interaction.user.name}",
                type=discord.ChannelType.private_thread
            )

            # Get esports application questions
            questions = await self.mongo.get_ticket_questions('esports_application')
            responses = {}

            # Send initial embed
            embed = discord.Embed(
                title="🎮 BSN ESPORTS Application",
                description="Welcome to the BSN ESPORTS application process! Please answer all questions accurately.",
                color=0xf1c40f
            )
            embed.add_field(
                name="Important Note",
                value="Make sure to have your game statistics and achievements ready.",
                inline=False
            )
            await interaction.response.send_message(embed=embed, ephemeral=False)

            # Ask each question
            for i, question in enumerate(questions, 1):
                question_embed = discord.Embed(
                    title=f"Question {i}/{len(questions)}",
                    description=question,
                    color=0xf1c40f
                )
                await interaction.followup.send(embed=question_embed)

                def check(m):
                    return m.author == interaction.user and m.channel == interaction.channel

                try:
                    # For questions asking for screenshots/media
                    if any(keyword in question.lower() for keyword in ['screenshot', 'image', 'record', 'proof']):
                        response_msg = await self.bot.wait_for('message', timeout=300.0, check=check)
                        if response_msg.attachments:
                            responses[question] = [att.url for att in response_msg.attachments]
                        else:
                            responses[question] = response_msg.content
                    else:
                        response_msg = await self.bot.wait_for('message', timeout=300.0, check=check)
                        responses[question] = response_msg.content

                except asyncio.TimeoutError:
                    await interaction.followup.send("Application timed out. Please try again.", ephemeral=True)
                    return

            # Create summary embed for staff
            summary_embed = discord.Embed(
                title="🎮 New Esports Application",
                description=f"From: {interaction.user.mention}",
                color=0xf1c40f
            )

            for question, answer in responses.items():
                if isinstance(answer, list):  # For attachments
                    value = "\n".join(answer)
                else:
                    value = answer
                
                summary_embed.add_field(
                    name=question,
                    value=value[:1024],
                    inline=False
                )

            # Add esports review controls
            view = EsportsApplicationControls(self.bot)
            await thread.send(
                content="New esports application received!",
                embed=summary_embed,
                view=view
            )

            # Notify applicant
            await interaction.followup.send(
                "Your esports application has been submitted! Our team will review it shortly.",
                ephemeral=False
            )

            # Save application to database
            await self.mongo.save_ticket('esports_application', {
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

class EsportsApplicationControls(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.success, emoji="✅")
    async def accept_application(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = EsportsAcceptModal()
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Schedule Tryout", style=discord.ButtonStyle.primary, emoji="🎯")
    async def schedule_tryout(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = TryoutScheduleModal()
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Request VOD", style=discord.ButtonStyle.secondary, emoji="🎥")
    async def request_vod(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = VODRequestModal()
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Reject", style=discord.ButtonStyle.danger, emoji="❌")
    async def reject_application(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = RejectionModal()
        await interaction.response.send_modal(modal)

class EsportsAcceptModal(discord.ui.Modal, title="Accept Esports Application"):
    welcome_message = discord.ui.TextInput(
        label="Welcome Message",
        style=discord.TextStyle.paragraph,
        placeholder="Enter a welcome message for the new team member...",
        required=True
    )
    
    team_assignment = discord.ui.TextInput(
        label="Team Assignment",
        placeholder="Specify which team they'll be joining...",
        required=True
    )
    
    next_steps = discord.ui.TextInput(
        label="Next Steps",
        style=discord.TextStyle.paragraph,
        placeholder="Outline what they need to do next...",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🎉 Welcome to BSN ESPORTS!",
            description="Congratulations! Your application has been accepted!",
            color=0x00ff00
        )
        embed.add_field(
            name="Welcome",
            value=self.welcome_message.value,
            inline=False
        )
        embed.add_field(
            name="Team Assignment",
            value=self.team_assignment.value,
            inline=False
        )
        embed.add_field(
            name="Next Steps",
            value=self.next_steps.value,
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
            'accepted',
            interaction.user.id,
            {
                'welcome_message': self.welcome_message.value,
                'team_assignment': self.team_assignment.value,
                'next_steps': self.next_steps.value
            }
        )
        await interaction.response.send_message("Application accepted! The applicant has been notified.")

class TryoutScheduleModal(discord.ui.Modal, title="Schedule Tryout"):
    tryout_date = discord.ui.TextInput(
        label="Tryout Date/Time",
        placeholder="e.g., Tomorrow at 8 PM EST",
        required=True
    )
    
    tryout_details = discord.ui.TextInput(
        label="Tryout Details",
        style=discord.TextStyle.paragraph,
        placeholder="Enter tryout format, requirements, and what to prepare...",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🎯 Esports Tryout Scheduled",
            description="Your application has progressed to the tryout phase!",
            color=0xf1c40f
        )
        embed.add_field(
            name="Tryout Date/Time",
            value=self.tryout_date.value,
            inline=False
        )
        embed.add_field(
            name="Details",
            value=self.tryout_details.value,
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
            'tryout_scheduled',
            interaction.user.id,
            {'tryout_date': self.tryout_date.value, 'tryout_details': self.tryout_details.value}
        )
        await interaction.response.send_message("Tryout scheduled! The applicant has been notified.")

class VODRequestModal(discord.ui.Modal, title="Request VOD Review"):
    requirements = discord.ui.TextInput(
        label="VOD Requirements",
        style=discord.TextStyle.paragraph,
        placeholder="Specify what kind of gameplay/VOD you need...",
        required=True
    )
    
    instructions = discord.ui.TextInput(
        label="Submission Instructions",
        style=discord.TextStyle.paragraph,
        placeholder="Explain how to submit the VOD...",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🎥 VOD Review Required",
            description="We need to review some gameplay footage to proceed with your application.",
            color=0x3498db
        )
        embed.add_field(
            name="Requirements",
            value=self.requirements.value,
            inline=False
        )
        embed.add_field(
            name="How to Submit",
            value=self.instructions.value,
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
            'vod_requested',
            interaction.user.id,
            {'requirements': self.requirements.value, 'instructions': self.instructions.value}
        )
        await interaction.response.send_message("VOD request sent! The applicant has been notified.")

class RejectionModal(discord.ui.Modal, title="Reject Esports Application"):
    reason = discord.ui.TextInput(
        label="Reason for rejection",
        style=discord.TextStyle.paragraph,
        placeholder="Enter the reason for rejecting this application...",
        required=True
    )
    
    improvement_areas = discord.ui.TextInput(
        label="Areas for Improvement",
        style=discord.TextStyle.paragraph,
        placeholder="Suggest areas where they can improve...",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="❌ Esports Application Status",
            description="Thank you for your interest in BSN ESPORTS.",
            color=0xff0000
        )
        embed.add_field(
            name="Status",
            value="We regret to inform you that your application was not successful at this time.",
            inline=False
        )
        embed.add_field(
            name="Reason",
            value=self.reason.value,
            inline=False
        )
        embed.add_field(
            name="Areas for Improvement",
            value=self.improvement_areas.value,
            inline=False
        )
        embed.add_field(
            name="Note",
            value="You're welcome to apply again after working on the suggested improvements.",
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
            {'reason': self.reason.value, 'improvement_areas': self.improvement_areas.value}
        )
        await interaction.response.send_message("Application rejected! The applicant has been notified.")
