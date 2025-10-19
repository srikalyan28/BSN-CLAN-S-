import discord
from typing import List, Dict, Any
import uuid

class QuestionManagementView(discord.ui.View):
    """View for managing ticket questions"""
    
    def __init__(self, bot, ticket_type: str):
        super().__init__(timeout=300)
        self.bot = bot
        self.mongo = bot.mongo_manager
        self.ticket_type = ticket_type
        
    @discord.ui.button(label="View Questions", style=discord.ButtonStyle.primary, emoji="👁️", row=0)
    async def view_questions(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show current questions"""
        questions = await self.mongo.get_questions(interaction.guild_id, self.ticket_type)
        
        if not questions:
            embed = discord.Embed(
                title="❌ No Questions Found",
                description="No questions have been configured for this ticket type.",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        embed = discord.Embed(
            title="📝 Current Questions",
            description=f"Questions for {self.ticket_type.replace('_', ' ').title()}:",
            color=0x00ff00
        )

        for i, question in enumerate(questions, 1):
            value = f"Type: {question['type']}\n"
            if question['type'] == 'select':
                options = "\n".join(f"{opt[1]} {opt[0]}" for opt in question['options'])
                value += f"Options:\n{options}"
            
            embed.add_field(
                name=f"{i}. {question['question']}",
                value=value,
                inline=False
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Add Question", style=discord.ButtonStyle.success, emoji="➕", row=0)
    async def add_question(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Add a new question"""
        await interaction.response.send_modal(AddQuestionModal(self.bot, self.ticket_type))

    @discord.ui.button(label="Remove Question", style=discord.ButtonStyle.danger, emoji="🗑️", row=0)
    async def remove_question(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Remove a question"""
        questions = await self.mongo.get_questions(interaction.guild_id, self.ticket_type)
        
        if not questions:
            embed = discord.Embed(
                title="❌ No Questions Found",
                description="No questions to remove.",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        options = [
            discord.SelectOption(
                label=f"Question {i+1}",
                value=question['id'],
                description=question['question'][:100]
            )
            for i, question in enumerate(questions)
        ]

        view = RemoveQuestionView(self.bot, self.ticket_type, options)
        embed = discord.Embed(
            title="🗑️ Remove Question",
            description="Select a question to remove:",
            color=0xff0000
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class AddQuestionModal(discord.ui.Modal, title="Add Question"):
    def __init__(self, bot, ticket_type: str):
        super().__init__()
        self.bot = bot
        self.mongo = bot.mongo_manager
        self.ticket_type = ticket_type

    question = discord.ui.TextInput(
        label="Question Text",
        style=discord.TextStyle.short,
        placeholder="Enter the question text",
        required=True
    )

    question_type = discord.ui.TextInput(
        label="Question Type",
        style=discord.TextStyle.short,
        placeholder="Enter 'text' or 'select'",
        required=True
    )

    options = discord.ui.TextInput(
        label="Options (for select type)",
        style=discord.TextStyle.paragraph,
        placeholder="For select type, enter options one per line with emoji: Label|emoji",
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            question_data = {
                'id': str(uuid.uuid4()),
                'question': self.question.value.strip(),
                'type': self.question_type.value.strip().lower()
            }

            if question_data['type'] not in ['text', 'select']:
                raise ValueError("Question type must be 'text' or 'select'")

            if question_data['type'] == 'select':
                if not self.options.value.strip():
                    raise ValueError("Options are required for select type questions")
                
                options = []
                for line in self.options.value.strip().split('\n'):
                    label, emoji = line.strip().split('|')
                    options.append((label.strip(), emoji.strip()))
                question_data['options'] = options

            await self.mongo.add_question(
                interaction.guild_id,
                self.ticket_type,
                question_data
            )

            embed = discord.Embed(
                title="✅ Question Added",
                description="Successfully added the new question!",
                color=0x00ff00
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

        except ValueError as e:
            embed = discord.Embed(
                title="❌ Invalid Input",
                description=str(e),
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            embed = discord.Embed(
                title="❌ Error",
                description=f"An error occurred: {str(e)}",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

class RemoveQuestionView(discord.ui.View):
    def __init__(self, bot, ticket_type: str, options: List[discord.SelectOption]):
        super().__init__(timeout=300)
        self.bot = bot
        self.mongo = bot.mongo_manager
        self.ticket_type = ticket_type
        
        # Add select menu
        select = discord.ui.Select(
            placeholder="Choose a question to remove",
            options=options,
            min_values=1,
            max_values=1
        )
        select.callback = self.question_selected
        self.add_item(select)

    async def question_selected(self, interaction: discord.Interaction):
        try:
            question_id = interaction.data['values'][0]
            success = await self.mongo.remove_question(
                interaction.guild_id,
                self.ticket_type,
                question_id
            )

            if success:
                embed = discord.Embed(
                    title="✅ Question Removed",
                    description="Successfully removed the question!",
                    color=0x00ff00
                )
            else:
                embed = discord.Embed(
                    title="❌ Error",
                    description="Failed to remove question. Please try again.",
                    color=0xff0000
                )

            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            embed = discord.Embed(
                title="❌ Error",
                description=f"An error occurred: {str(e)}",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)