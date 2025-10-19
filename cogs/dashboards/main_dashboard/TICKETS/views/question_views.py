import discord
from typing import List, Dict, Tuple, Any

class QuestionSelectView(discord.ui.View):
    """View for handling select-type questions"""
    
    def __init__(
        self,
        handler,
        questions: List[Dict],
        answers: Dict,
        current_index: int,
        options: List[Tuple[str, str]]
    ):
        super().__init__(timeout=None)
        self.handler = handler
        self.questions = questions
        self.answers = answers
        self.current_index = current_index
        
        # Add select menu
        select = discord.ui.Select(
            placeholder="Choose your answer...",
            options=[
                discord.SelectOption(
                    label=option[0],
                    value=str(i),
                    emoji=option[1]
                )
                for i, option in enumerate(options)
            ]
        )
        select.callback = self.select_callback
        self.add_item(select)

    async def select_callback(self, interaction: discord.Interaction):
        """Handle select menu response"""
        try:
            # Get selected option
            selected_index = int(interaction.data['values'][0])
            selected_option = self.questions[self.current_index]['options'][selected_index]
            
            # Save answer
            self.answers[self.questions[self.current_index]['id']] = selected_option
            
            # Move to next question
            await self.handler._ask_next_question(
                interaction,
                interaction.channel,
                self.questions,
                self.answers,
                self.current_index + 1
            )
            
        except Exception as e:
            await interaction.response.send_message(
                f"❌ An error occurred: {str(e)}",
                ephemeral=True
            )

class QuestionTextView(discord.ui.View):
    """View for handling text-type questions"""
    
    def __init__(
        self,
        handler,
        questions: List[Dict],
        answers: Dict,
        current_index: int
    ):
        super().__init__(timeout=None)
        self.handler = handler
        self.questions = questions
        self.answers = answers
        self.current_index = current_index

    @discord.ui.button(label="Answer", style=discord.ButtonStyle.primary)
    async def answer_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show modal for text answer"""
        await interaction.response.send_modal(
            QuestionTextModal(
                self.handler,
                self.questions,
                self.answers,
                self.current_index
            )
        )

class QuestionTextModal(discord.ui.Modal):
    """Modal for text answers"""
    
    def __init__(
        self,
        handler,
        questions: List[Dict],
        answers: Dict,
        current_index: int
    ):
        super().__init__(title=questions[current_index]['question'])
        self.handler = handler
        self.questions = questions
        self.answers = answers
        self.current_index = current_index
        
        # Add text input
        self.answer = discord.ui.TextInput(
            label="Your Answer",
            style=discord.TextStyle.short,
            required=True
        )
        self.add_item(self.answer)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Save answer
            self.answers[self.questions[self.current_index]['id']] = self.answer.value
            
            # Move to next question
            await self.handler._ask_next_question(
                interaction,
                interaction.channel,
                self.questions,
                self.answers,
                self.current_index + 1
            )
            
        except Exception as e:
            await interaction.response.send_message(
                f"❌ An error occurred: {str(e)}",
                ephemeral=True
            )