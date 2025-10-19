import discord
from discord.ext import commands
import asyncio
import os
from dotenv import load_dotenv
from utils.mongo_manager import MongoManager
from utils.data_manager import DataManager

# Load environment variables
load_dotenv()

class BlackspireBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.guilds = True

        super().__init__(
            command_prefix='!',
            intents=intents,
            help_command=None
        )

        # Initialize managers
        self.mongo_manager = None  # Will be initialized in setup_hook
        self.data_manager = None   # Will be initialized in setup_hook

    async def setup_hook(self):
        """Initialize bot systems and load all cogs"""
        try:
            # Initialize MongoDB connection first
            print("\n🔄 Initializing MongoDB connection...")
            try:
                self.mongo_manager = MongoManager()
                await self.mongo_manager.initialize()
                self.data_manager = DataManager(self.mongo_manager)
                print("✅ MongoDB initialized with all collections")
            except Exception as e:
                print(f"❌ Failed to initialize MongoDB: {str(e)}")
                raise SystemExit("Cannot continue without MongoDB connection")
            
            print("\n🔄 Loading cogs...")
            # Organized by category
            cogs_to_load = {
                "Slash Commands": [
                    'cogs.slash_commands.setup_counting',
                    'cogs.slash_commands.disable_counting',
                    'cogs.slash_commands.add_to_ticket',
                    'cogs.slash_commands.reject_player',
                    'cogs.slash_commands.help'
                ],
                "Dashboards": [
                    'cogs.dashboards.admin_dashboard',
                    'cogs.dashboards.main_dashboard.main_dashboard',
                    'cogs.dashboards.booster_dashboard',
                    'cogs.dashboards.clan_dashboard'
                ],
                "Systems": [
                    'cogs.counting_system.counting_system'
                ]
            }

            # Load cogs by category
            failed_cogs = []
            for category, cogs in cogs_to_load.items():
                print(f"\n📁 Loading {category}:")
                for cog in cogs:
                    try:
                        await self.load_extension(cog)
                        print(f'  ✅ Loaded {cog}')
                    except Exception as e:
                        print(f'  ❌ Failed to load {cog}: {str(e)}')
                        failed_cogs.append((cog, str(e)))

            # Summary
            if failed_cogs:
                print("\n❌ Some cogs failed to load:")
                for cog, error in failed_cogs:
                    print(f"  • {cog}: {error}")
                raise RuntimeError("Not all cogs loaded successfully")
            else:
                print("\n✅ All cogs loaded successfully")
                    
        except Exception as e:
            print(f'\n❌ Critical initialization error: {e}')
            raise  # Re-raise the exception to prevent the bot from starting with incomplete initialization

    async def on_ready(self):
        """Set up bot presence and initialize systems"""
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="BLACKSPIRE NATION"
            ),
            status=discord.Status.online
        )
        print(f'✅ {self.user} is ready!')

        print(f'🚀 {self.user} is now online!')
        print(f'📊 Connected to {len(self.guilds)} guild(s)')

        # Sync slash commands
        try:
            synced = await self.tree.sync()
            print(f'🔄 Synced {len(synced)} command(s)')
        except Exception as e:
            print(f'❌ Failed to sync commands: {e}')

# Bot instance
bot = BlackspireBot()

if __name__ == "__main__":
    bot.run(os.getenv('BOT_TOKEN'))
