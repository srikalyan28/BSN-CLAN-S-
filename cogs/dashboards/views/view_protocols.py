from abc import ABC
from typing import Protocol

class BoosterViews(Protocol):
    """Protocol for booster views to avoid circular imports"""
    
    async def show_main_dashboard(self, interaction):
        """Show the main booster dashboard"""
        raise NotImplementedError