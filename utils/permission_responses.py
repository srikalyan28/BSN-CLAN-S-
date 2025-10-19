import discord
import random

class PermissionResponses:
    """Sarcastic and fun permission denied responses"""
    
    DENIED_MESSAGES = [
        "🔒 Oh look, someone's trying to be sneaky! Sadly, you're about as authorized as a penguin in a desert.",
        "🚫 Access denied faster than your chances of becoming the next Discord CEO!",
        "⛔ Nice try! But Mr. Blaze keeps this more secure than his secret cookie stash.",
        "🎭 Impersonating staff? That's cute. Next time bring a better disguise!",
        "🚧 Hold up! This area is more exclusive than a VIP party for unicorns.",
        "🎟️ Sorry, your 'I'm Important' card seems to have expired!",
        "🔐 This is locked tighter than Mr. Blaze's legendary vault of dad jokes!",
        "⚡ ZAP! The permission forcefield has spoken: That's a no from me, dawg.",
        "🎭 Identity crisis? You're giving me 'wants to be staff' vibes!",
        "🌟 Stars align... but not for you accessing this command!"
    ]
    
    CONTACT_MESSAGES = [
        "👑 Why not slide into Mr. Blaze's DMs? He might grant you access (if you ask nicely and bring cookies)!",
        "🎯 Hit up Mr. Blaze if you think you've got what it takes!",
        "🎪 Show Mr. Blaze your best circus tricks, maybe he'll be impressed!",
        "🎨 Paint Mr. Blaze a pretty picture of why you deserve access!",
        "🎭 Time to practice your 'please give me access' speech for Mr. Blaze!"
    ]
    
    @staticmethod
    def get_denial_embed(user: discord.Member, command_or_dashboard: str) -> discord.Embed:
        """Get a fun denial embed with sarcastic message"""
        embed = discord.Embed(
            title="🛡️ BSN Security System Activated!",
            description=f"{random.choice(PermissionResponses.DENIED_MESSAGES)}\n\n"
                       f"*You tried to access: `{command_or_dashboard}`*\n\n"
                       f"💡 **What now?**\n{random.choice(PermissionResponses.CONTACT_MESSAGES)}",
            color=0xff0000
        )
        embed.set_footer(text="BSN Security | Keeping the peasants out since 2025 😎")
        return embed

    @staticmethod
    def get_timeout_embed() -> discord.Embed:
        """Get a fun timeout embed"""
        messages = [
            "⏰ Looks like someone's taking a nap at the keyboard!",
            "🐌 Are you trying to break the world record for slowest response?",
            "💤 Did you fall asleep? I'm not waiting forever!",
            "⌛ Time's up! Even sloths move faster than that!",
            "🏃 The response train has left the station without you!"
        ]
        embed = discord.Embed(
            title="Operation Timeout!",
            description=f"{random.choice(messages)}\n\nTry again when you're feeling more... responsive!",
            color=0xffa500
        )
        return embed

    @staticmethod
    def get_error_embed(error_msg: str) -> discord.Embed:
        """Get a fun error embed"""
        messages = [
            "🔧 Oops! The hamsters powering our servers need a coffee break!",
            "🎪 The circus is in town, and they've borrowed our error handler!",
            "🎭 Plot twist: Even our errors have errors!",
            "🎪 Welcome to the Bug Circus! Today's star performer: This Error!",
            "🌋 Error volcano eruption! Duck and cover!"
        ]
        embed = discord.Embed(
            title="🎢 Whoopsie Daisy!",
            description=f"{random.choice(messages)}\n\n**Technical Stuff:**\n```{error_msg}```\n\n*Our code monkeys are already on it!*",
            color=0xff6b6b
        )
        return embed