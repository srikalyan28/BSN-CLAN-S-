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
            # Create private thread for partnership review
            thread = await interaction.channel.create_thread(
                name=f"Partnership - {interaction.user.name}",
                type=discord.ChannelType.private_thread
            )

            # Get partnership questions
            questions = await self.mongo.get_ticket_questions('partnership_application')
            responses = {}

            # Send initial embed
            embed = discord.Embed(
                title="🤝 Partnership Application",
                description="Welcome! Let's explore a potential partnership between our communities.",
                color=0x9b59b6
            )
            embed.add_field(
                name="Important",
                value="Please make sure you have the authority to represent your server in partnership discussions.",
                inline=False
            )
            await interaction.response.send_message(embed=embed, ephemeral=False)

            # Ask each question
            for i, question in enumerate(questions, 1):
                question_embed = discord.Embed(
                    title=f"Question {i}/{len(questions)}",
                    description=question,
                    color=0x9b59b6
                )
                await interaction.followup.send(embed=question_embed)

                def check(m):
                    return m.author == interaction.user and m.channel == interaction.channel

                try:
                    response = await self.bot.wait_for('message', timeout=300.0, check=check)
                    responses[question] = response.content

                    # If this is asking for server invite, validate it
                    if 'invite' in question.lower() or 'link' in question.lower():
                        try:
                            invite = await self.bot.fetch_invite(response.content)
                            responses['server_info'] = {
                                'name': invite.guild.name,
                                'member_count': invite.guild.member_count if invite.guild.member_count else 'Unknown',
                                'verified': invite.guild.verified if hasattr(invite.guild, 'verified') else False
                            }
                        except:
                            pass  # If invite validation fails, continue without server info

                except asyncio.TimeoutError:
                    await interaction.followup.send("Application timed out. Please try again.", ephemeral=True)
                    return

            # Create summary embed for staff
            summary_embed = discord.Embed(
                title="🤝 New Partnership Application",
                description=f"From: {interaction.user.mention}",
                color=0x9b59b6
            )

            if 'server_info' in responses:
                summary_embed.add_field(
                    name="Server Information",
                    value=f"Name: {responses['server_info']['name']}\n"
                          f"Members: {responses['server_info']['member_count']}\n"
                          f"Verified: {'Yes' if responses['server_info']['verified'] else 'No'}",
                    inline=False
                )

            for question, answer in responses.items():
                if question != 'server_info':
                    summary_embed.add_field(
                        name=question,
                        value=answer[:1024],  # Discord field value limit
                        inline=False
                    )

            # Add partnership review controls
            view = PartnershipControls(self.bot)
            await thread.send(
                content="New partnership application received!",
                embed=summary_embed,
                view=view
            )

            # Notify applicant
            await interaction.followup.send(
                "Your partnership application has been submitted! Our team will review it shortly.",
                ephemeral=False
            )

            # Save application to database
            await self.mongo.save_ticket('partnership_application', {
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

class PartnershipControls(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.success, emoji="✅")
    async def accept_partnership(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = PartnershipAcceptModal()
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Request More Info", style=discord.ButtonStyle.primary, emoji="❓")
    async def request_info(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = InfoRequestModal()
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Reject", style=discord.ButtonStyle.danger, emoji="❌")
    async def reject_partnership(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = RejectionModal()
        await interaction.response.send_modal(modal)

class PartnershipAcceptModal(discord.ui.Modal, title="Accept Partnership"):
    welcome_message = discord.ui.TextInput(
        label="Welcome Message",
        style=discord.TextStyle.paragraph,
        placeholder="Enter a welcome message for the new partner...",
        required=True
    )
    
    requirements = discord.ui.TextInput(
        label="Partnership Requirements",
        style=discord.TextStyle.paragraph,
        placeholder="List any specific requirements or expectations...",
        required=True
    )
    
    next_steps = discord.ui.TextInput(
        label="Next Steps",
        style=discord.TextStyle.paragraph,
        placeholder="Outline the next steps to finalize the partnership...",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🎉 Partnership Application Accepted!",
            description="Congratulations! Your partnership application has been approved!",
            color=0x00ff00
        )
        embed.add_field(
            name="Welcome",
            value=self.welcome_message.value,
            inline=False
        )
        embed.add_field(
            name="Partnership Requirements",
            value=self.requirements.value,
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
            {
                'welcome_message': self.welcome_message.value,
                'requirements': self.requirements.value,
                'next_steps': self.next_steps.value
            }
        )
        await interaction.response.send_message("Partnership accepted! The applicant has been notified.")

class InfoRequestModal(discord.ui.Modal, title="Request Additional Information"):
    questions = discord.ui.TextInput(
        label="Additional Questions",
        style=discord.TextStyle.paragraph,
        placeholder="List the additional information needed...",
        required=True
    )
    
    context = discord.ui.TextInput(
        label="Context",
        style=discord.TextStyle.paragraph,
        placeholder="Explain why this information is needed...",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="ℹ️ Additional Information Requested",
            description="Our team needs some additional information to process your partnership application.",
            color=0x3498db
        )
        embed.add_field(
            name="Questions",
            value=self.questions.value,
            inline=False
        )
        embed.add_field(
            name="Context",
            value=self.context.value,
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
            'info_requested',
            interaction.user.id,
            {'requested_info': self.questions.value, 'context': self.context.value}
        )
        await interaction.response.send_message("Information request sent! The applicant has been notified.")

class RejectionModal(discord.ui.Modal, title="Reject Partnership"):
    reason = discord.ui.TextInput(
        label="Reason for rejection",
        style=discord.TextStyle.paragraph,
        placeholder="Enter the reason for rejecting this partnership...",
        required=True
    )
    
    suggestions = discord.ui.TextInput(
        label="Suggestions",
        style=discord.TextStyle.paragraph,
        placeholder="Provide suggestions for future applications...",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="❌ Partnership Application Status",
            description="Thank you for your interest in partnering with us.",
            color=0xff0000
        )
        embed.add_field(
            name="Status",
            value="We regret to inform you that we cannot proceed with the partnership at this time.",
            inline=False
        )
        embed.add_field(
            name="Reason",
            value=self.reason.value,
            inline=False
        )
        embed.add_field(
            name="Suggestions",
            value=self.suggestions.value,
            inline=False
        )
        embed.add_field(
            name="Note",
            value="You're welcome to apply again in the future once your server meets our partnership criteria.",
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
            {'reason': self.reason.value, 'suggestions': self.suggestions.value}
        )
        await interaction.response.send_message("Partnership rejected! The applicant has been notified.")
