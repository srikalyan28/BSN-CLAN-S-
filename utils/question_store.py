class QuestionStore:
    """Question management functions for MongoDB"""

    async def get_questions(self, guild_id: int, ticket_type: str) -> list:
        """Get all questions for a ticket type"""
        guild_config = await self.guilds.find_one({"_id": guild_id})
        if not guild_config or "ticket_questions" not in guild_config:
            return []

        questions = guild_config["ticket_questions"].get(ticket_type, [])
        return questions

    async def add_question(self, guild_id: int, ticket_type: str, question_data: dict) -> bool:
        """Add a new question to a ticket type"""
        try:
            # Update or create the ticket_questions field
            result = await self.guilds.update_one(
                {"_id": guild_id},
                {
                    "$push": {
                        f"ticket_questions.{ticket_type}": question_data
                    }
                },
                upsert=True
            )
            return result.modified_count > 0 or result.upserted_id is not None
        except Exception as e:
            print(f"Error adding question: {e}")
            return False

    async def remove_question(self, guild_id: int, ticket_type: str, question_id: str) -> bool:
        """Remove a question from a ticket type"""
        try:
            result = await self.guilds.update_one(
                {"_id": guild_id},
                {
                    "$pull": {
                        f"ticket_questions.{ticket_type}": {
                            "id": question_id
                        }
                    }
                }
            )
            return result.modified_count > 0
        except Exception as e:
            print(f"Error removing question: {e}")
            return False

    async def get_question_by_id(self, guild_id: int, ticket_type: str, question_id: str) -> dict:
        """Get a specific question by its ID"""
        questions = await self.get_questions(guild_id, ticket_type)
        for question in questions:
            if question["id"] == question_id:
                return question
        return None