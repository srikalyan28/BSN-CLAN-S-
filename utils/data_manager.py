import aiohttp
import asyncio
from typing import Dict, List, Optional
from datetime import datetime

class DataManager:
    def __init__(self, mongo_manager):
        self.mongo = mongo_manager
        self.clash_king_base = "https://api.clashk.ing"

    async def get_player_stats(self, player_tag: str) -> Dict:
        """Get player stats from Clash King API"""
        try:
            # Remove # if present
            if player_tag.startswith('#'):
                player_tag = player_tag[1:]

            url = f"{self.clash_king_base}/player/{player_tag}/stats"

            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data
                    else:
                        return None
        except Exception as e:
            print(f"Error fetching player stats: {e}")
            return None

    def format_player_stats(self, stats: Dict, player_tag: str) -> str:
        """Format player stats for display"""
        if not stats:
            return f"❌ Could not fetch stats for {player_tag}"

        try:
            name = stats.get('name', 'Unknown')
            town_hall = stats.get('townHallLevel', 'Unknown')
            trophies = stats.get('trophies', 'Unknown')
            clan_name = stats.get('clan', {}).get('name', 'No Clan')
            exp_level = stats.get('expLevel', 'Unknown')

            formatted = f"""
**🏷️ Player: {name}**
**🏰 Town Hall:** {town_hall}
**🏆 Trophies:** {trophies}
**⭐ Experience Level:** {exp_level}
**🛡️ Clan:** {clan_name}
**🔗 Player Tag:** #{player_tag}
            """

            return formatted.strip()
        except Exception as e:
            print(f"Error formatting player stats: {e}")
            return f"❌ Error formatting stats for {player_tag}"

    def get_eligible_clans(self, town_hall_level: int, clan_type: str) -> List[Dict]:
        """Get clans that are eligible for the player based on TH level and type"""
        all_clans = self.mongo.get_all_clans()
        eligible_clans = []

        for clan in all_clans:
            clan_th_requirement = clan.get('min_town_hall', 1)
            clan_clan_type = clan.get('clan_type', 'regular')

            if town_hall_level >= clan_th_requirement and clan_clan_type.lower() == clan_type.lower():
                eligible_clans.append(clan)

        return eligible_clans

    def create_clan_dropdown_options(self, eligible_clans: List[Dict]) -> List[Dict]:
        """Create dropdown options for clan selection"""
        options = []
        for clan in eligible_clans:
            option = {
                'label': clan.get('clan_name', 'Unknown Clan'),
                'description': f"TH{clan.get('min_town_hall', '?')}+ • {clan.get('clan_type', 'Regular').title()}",
                'value': clan.get('clan_name', 'unknown')
            }
            options.append(option)

        return options

    def get_dashboard_list(self) -> List[str]:
        """Get list of all available dashboards"""
        return [
            'admin_dashboard',
            'main_dashboard', 
            'booster_dashboard',
            'clan_dashboard'
        ]

    def get_command_list(self) -> List[str]:
        """Get list of all available slash commands"""
        return [
            'setup_counting',
            'disable_counting',
            'add_to_ticket',
            'reject_player',
            'help'
        ]

    def get_ticket_types(self) -> List[Dict]:
        """Get all ticket types with emojis"""
        return [
            {'name': 'Join Our Clans', 'value': 'join_clan', 'emoji': '⚔️'},
            {'name': 'Apply Your Clan', 'value': 'apply_clan', 'emoji': '🏛️'},
            {'name': 'Staff Application', 'value': 'staff_apply', 'emoji': '👨‍💼'},
            {'name': 'Partnership Application', 'value': 'partnership_apply', 'emoji': '🤝'},
            {'name': 'Esports Application', 'value': 'esports_apply', 'emoji': '🎮'},
            {'name': 'Giveaway Claim', 'value': 'giveaway_claim', 'emoji': '🎁'}
        ]

    def get_individual_ticket_types(self) -> List[Dict]:
        """Get individual ticket types"""
        return [
            {'name': 'Sponsorships', 'value': 'sponcerships', 'emoji': '💰'},
            {'name': 'Host Giveaway', 'value': 'host_giveaway', 'emoji': '🎉'},
            {'name': 'Help & Support', 'value': 'help_support', 'emoji': '❓'}
        ]

    def get_continent_options(self) -> List[Dict]:
        """Get continent options for dropdown"""
        return [
            {'label': 'Asia', 'value': 'asia', 'emoji': '🌏'},
            {'label': 'North America', 'value': 'north_america', 'emoji': '🌎'},
            {'label': 'South America', 'value': 'south_america', 'emoji': '🌎'},
            {'label': 'Africa', 'value': 'africa', 'emoji': '🌍'},
            {'label': 'Australia', 'value': 'australia', 'emoji': '🌏'},
            {'label': 'Europe', 'value': 'europe', 'emoji': '🌍'}
        ]

    def get_age_bracket_options(self) -> List[Dict]:
        """Get age bracket options"""
        return [
            {'label': 'Below 17', 'value': 'below_17', 'emoji': '👶'},
            {'label': '17-25', 'value': '17_25', 'emoji': '🧑'},
            {'label': '25+', 'value': '25_plus', 'emoji': '👨'}
        ]

    def get_account_count_options(self) -> List[Dict]:
        """Get account count options"""
        return [
            {'label': '1 Account', 'value': '1', 'emoji': '1️⃣'},
            {'label': '2 Accounts', 'value': '2', 'emoji': '2️⃣'},
            {'label': '3 Accounts', 'value': '3', 'emoji': '3️⃣'}
        ]

    def get_clan_type_options(self) -> List[Dict]:
        """Get clan type options with descriptions"""
        return [
            {
                'label': 'Regular Clans',
                'value': 'regular',
                'description': 'Very strict about wars, events and raids',
                'emoji': '⚔️'
            },
            {
                'label': 'Cruise Clans', 
                'value': 'cruise',
                'description': 'Allow 2 hero down for wars, competitive CWL',
                'emoji': '🚢'
            },
            {
                'label': 'FWA/GFL Farming Clans',
                'value': 'farming',
                'description': 'Extremely chill, easy wars and lazy CWLs',
                'emoji': '🌾'
            }
        ]

    def format_invite_message(self, clan_data: Dict, applicant_mention: str, inviter_mention: str) -> Dict:
        """Format clan invitation message"""
        embed_data = {
            'title': f"Clan Invitation for {applicant_mention}",
            'description': f"""
**{clan_data.get('clan_name', 'Unknown Clan')} Clan Invitation**

WELCOME TO {clan_data.get('clan_name', 'Unknown Clan')} LED BY {clan_data.get('leader_mention', 'Unknown Leader')} & {clan_data.get('leadership_role_mention', 'Leadership Team')}

**BSN Family Rules**

• **Reapply anytime** - If you're not happy with your clan, you're free to apply again
• **Use BSN FAM** in join requests - it helps during recruitment  
• **CWL flexibility** - you can shift between clans for better matches
• **One big family** - all BSN clans support each other!

**Invited By**
{inviter_mention}
            """,
            'color': 0x00ff00,  # Green color
            'image': clan_data.get('clan_icon', None),
            'footer': 'Blackspire Nation • Welcome to the family!'
        }

        return embed_data

    async def create_private_thread(self, channel, thread_name: str, reason: str = None):
        """Create a private thread in the given channel"""
        try:
            thread = await channel.create_thread(
                name=thread_name,
                type=discord.ChannelType.private_thread,
                reason=reason or "Application processing thread"
            )
            return thread
        except Exception as e:
            print(f"Error creating private thread: {e}")
            return None

    def get_milestone_message(self, count: int) -> Optional[str]:
        """Get milestone message for counting system"""
        milestones = {
            69: "Nice! 😎",
            100: "🎉 Century mark! Keep counting!",
            111: "Triple ones! 1️⃣1️⃣1️⃣",
            222: "Triple twos! 2️⃣2️⃣2️⃣", 
            333: "Triple threes! 3️⃣3️⃣3️⃣",
            444: "Triple fours! 4️⃣4️⃣4️⃣",
            500: "Half a thousand! You're doing great! 🌟",
            555: "Triple fives! 5️⃣5️⃣5️⃣",
            666: "Spooky number! 👻",
            777: "Lucky sevens! 🎰",
            888: "Triple eights! 8️⃣8️⃣8️⃣",
            999: "Triple nines! 9️⃣9️⃣9️⃣",
            1000: "🎊 ONE THOUSAND! What an achievement!",
            1234: "Sequential! 1-2-3-4! 🔢",
            2000: "Two thousand! The future is here! 🚀",
            3000: "Three thousand! You're unstoppable! 💪",
            5000: "FIVE THOUSAND! Legendary counting! 👑",
            8888: "Quadruple eights! 8️⃣8️⃣8️⃣8️⃣ So satisfying!",
            9000: "IT'S OVER 9000!!! 💥",
            9999: "One away from 10k! The tension! 😬",
            10000: "🎆 TEN THOUSAND! You've reached counting greatness! 🏆",
            11111: "All ones! 1️⃣1️⃣1️⃣1️⃣1️⃣",
            12345: "Perfect sequence! 1-2-3-4-5! 🎯",
            15000: "Fifteen thousand! Halfway to 30k! 🌈",
            20000: "TWENTY THOUSAND! Double digits! 🎊",
            22222: "All twos! 2️⃣2️⃣2️⃣2️⃣2️⃣",
            25000: "Quarter of 100k! You're amazing! 🌟",
            30000: "THIRTY THOUSAND! Incredible dedication! 💎",
            33333: "All threes! 3️⃣3️⃣3️⃣3️⃣3️⃣",
            44444: "All fours! 4️⃣4️⃣4️⃣4️⃣4️⃣",
            50000: "FIFTY THOUSAND! Half a century of thousands! 🏅",
            55555: "All fives! 5️⃣5️⃣5️⃣5️⃣5️⃣",
            66666: "All sixes! 6️⃣6️⃣6️⃣6️⃣6️⃣",
            69420: "The ultimate meme number! Nice and blazing! 😎🔥",
            77777: "All sevens! 7️⃣7️⃣7️⃣7️⃣7️⃣ JACKPOT!",
            88888: "All eights! 8️⃣8️⃣8️⃣8️⃣8️⃣",
            99999: "All nines! 9️⃣9️⃣9️⃣9️⃣9️⃣",
            100000: "💯 ONE HUNDRED THOUSAND! LEGENDARY STATUS ACHIEVED! 👑🎆🏆"
        }

        return milestones.get(count)
