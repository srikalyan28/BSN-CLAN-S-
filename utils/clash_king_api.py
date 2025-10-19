import aiohttp
import asyncio
from typing import Dict, Optional, List
import discord
from datetime import datetime

class ClashKingAPI:
    def __init__(self, api_key: str, base_url: str = "https://api.clashk.ing"):
        self.api_key = api_key
        self.base_url = base_url
        self.session = None
        self._cache = {}
        self._cache_time = 300  # 5 minutes cache

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                headers={"Authorization": f"Bearer {self.api_key}"}
            )
        return self.session

    async def close(self):
        """Close the aiohttp session"""
        if self.session and not self.session.closed:
            await self.session.close()

    def _get_cache_key(self, endpoint: str, params: Dict = None) -> str:
        """Generate cache key"""
        if params:
            return f"{endpoint}:{str(sorted(params.items()))}"
        return endpoint

    def _get_cached_data(self, cache_key: str) -> Optional[Dict]:
        """Get data from cache if valid"""
        if cache_key in self._cache:
            data, timestamp = self._cache[cache_key]
            if (datetime.now() - timestamp).seconds < self._cache_time:
                return data
            del self._cache[cache_key]
        return None

    def _set_cache(self, cache_key: str, data: Dict):
        """Cache data with timestamp"""
        self._cache[cache_key] = (data, datetime.now())

    async def _make_request(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """Make API request with caching"""
        cache_key = self._get_cache_key(endpoint, params)
        
        # Check cache first
        cached_data = self._get_cached_data(cache_key)
        if cached_data:
            return cached_data

        # Make API request
        try:
            session = await self._get_session()
            # Format URL correctly for the web stats lookup
            url = f"https://api.clashk.ing/{endpoint}"
            
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    self._set_cache(cache_key, data)
                    return data
                elif response.status == 404:
                    return None
                else:
                    print(f"API Error: {response.status} - {await response.text()}")
                    return None
                    
        except Exception as e:
            print(f"Error making API request: {str(e)}")
            return None

    async def get_player(self, player_tag: str) -> Optional[Dict]:
        """Get player information by scraping stats from the web"""
        try:
            # Remove # if present and validate tag
            tag = player_tag.strip('#')
            if not tag:
                return None

            # Make the web request for stats
            session = await self._get_session()
            url = f"https://api.clashk.ing/playertag/stats?tag={tag}"
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.text()
                    return {"tag": tag, "stats_data": data}
                else:
                    print(f"Error fetching player data: {response.status}")
                    return None
        except Exception as e:
            print(f"Error in get_player: {str(e)}")
            return None

    def create_player_embed(self, player_data: Dict) -> discord.Embed:
        """Create a rich embed for player data"""
        if not player_data:
            return discord.Embed(
                title="❌ Player Not Found",
                description="Could not fetch player data",
                color=0xff0000
            )

        # Create main embed
        embed = discord.Embed(
            title=f"🏰 {player_data.get('name', 'Unknown Player')}",
            description=f"Player Tag: #{player_data.get('tag', 'Unknown')}",
            color=0x2ecc71
        )

        # Basic info
        embed.add_field(
            name="📊 Basic Info",
            value=f"• Town Hall: {player_data.get('townHallLevel', 'Unknown')}\n"
                  f"• Experience: Level {player_data.get('expLevel', 'Unknown')}\n"
                  f"• Trophies: {player_data.get('trophies', 'Unknown')}\n"
                  f"• Best Trophies: {player_data.get('bestTrophies', 'Unknown')}",
            inline=False
        )

        # War stats
        war_stars = player_data.get('warStars', 0)
        embed.add_field(
            name="⚔️ War Statistics",
            value=f"• War Stars: {war_stars}\n"
                  f"• CWL Stars: {player_data.get('clanWarLeagueStars', 0)}\n"
                  f"• Attacks Won: {player_data.get('attackWins', 0)}",
            inline=True
        )

        # Clan info
        clan_info = player_data.get('clan', {})
        if clan_info:
            embed.add_field(
                name="🛡️ Clan Information",
                value=f"• Name: {clan_info.get('name', 'No Clan')}\n"
                      f"• Tag: #{clan_info.get('tag', 'N/A')}\n"
                      f"• Role: {clan_info.get('role', 'N/A')}",
                inline=True
            )

        # Troops and heroes
        troops = player_data.get('troops', [])
        heroes = [troop for troop in troops if troop.get('village') == 'home' and troop.get('type') == 'hero']
        if heroes:
            hero_text = []
            for hero in heroes:
                hero_text.append(f"• {hero.get('name')}: Level {hero.get('level')}/{hero.get('maxLevel')}")
            
            embed.add_field(
                name="👑 Heroes",
                value="\n".join(hero_text) or "No heroes unlocked",
                inline=False
            )

        # Set footer with last updated time
        embed.set_footer(text="Last Updated")
        embed.timestamp = datetime.utcnow()

        return embed

    async def format_clan_requirements(self, player_data: Dict, clan_data: List[Dict]) -> discord.Embed:
        """Format clan requirements compared to player stats"""
        embed = discord.Embed(
            title="🏰 Available Clans",
            description="Here are the clans that match your profile:",
            color=0x3498db
        )

        # Player stats section
        th_level = player_data.get('townHallLevel', 0)
        war_stars = player_data.get('warStars', 0)
        trophies = player_data.get('trophies', 0)

        embed.add_field(
            name="Your Stats",
            value=f"• Town Hall: {th_level}\n"
                  f"• War Stars: {war_stars}\n"
                  f"• Trophies: {trophies}",
            inline=False
        )

        # Sort clans by TH requirement
        sorted_clans = sorted(clan_data, key=lambda x: x.get('th_requirement', 0))

        # Add each clan's info
        for clan in sorted_clans:
            meets_requirements = th_level >= clan.get('th_requirement', 0)
            status = "✅" if meets_requirements else "❌"
            
            embed.add_field(
                name=f"{status} {clan.get('name', 'Unknown Clan')}",
                value=f"• Required TH: {clan.get('th_requirement', 'Any')}\n"
                      f"• Focus: {clan.get('focus', 'Mixed')}\n"
                      f"• Status: {'Available' if meets_requirements else 'Requirements not met'}",
                inline=True
            )

        embed.set_footer(text="Select a clan from the dropdown menu below")
        return embed

    def create_error_embed(self, error_msg: str) -> discord.Embed:
        """Create an error embed"""
        return discord.Embed(
            title="❌ Error",
            description=f"An error occurred: {error_msg}",
            color=0xff0000
        )