from motor import motor_asyncio
import os
import asyncio
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import discord
from .permission_responses import PermissionResponses
from .permission_manager import PermissionManager
from .permission_result import PermissionResult

class MongoManager:
    def __init__(self):
        """Initialize MongoDB connection and setup collections"""
        try:
            self._load_env_variables()
            self.client = motor_asyncio.AsyncIOMotorClient(os.getenv('MONGO_URI'))
            self.db = self.client[os.getenv('MONGO_DB_NAME')]
            self.permissions = PermissionManager(self.db)
            
            # Initialize collections on startup
            asyncio.create_task(self._initialize_collections())
            
            # Import question management functions
            from .question_store import QuestionStore
            for func_name in dir(QuestionStore):
                if not func_name.startswith('_'):  # Only import public methods
                    setattr(self, func_name, getattr(QuestionStore, func_name).__get__(self))
            
        except Exception as e:
            print(f"Failed to initialize MongoDB: {str(e)}")
            raise

    def _load_env_variables(self):
        """Load and validate required environment variables"""
        required_vars = {
            'MONGO_URI': 'MongoDB connection URI',
            'MONGO_DB_NAME': 'Database name',
            'BOT_OWNER_ID': 'Bot owner Discord ID',
        }
        
        missing_vars = []
        for var, description in required_vars.items():
            if not os.getenv(var):
                missing_vars.append(f"{var} ({description})")
        
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

    async def _initialize_collections(self):
        """Initialize collections with proper schemas and indexes"""
        try:
            # Create indexes for better query performance
            await self.db.tickets.create_index([("ticket_type", 1), ("status", 1)])
            await self.db.dashboard_permissions.create_index([
                ("dashboard_name", 1),
                ("guild_id", 1),
                ("user_id", 1)
            ])
            await self.db.command_permissions.create_index([
                ("command_name", 1),
                ("guild_id", 1),
                ("user_id", 1)
            ])
            await self.db.clans.create_index([("name", 1), ("guild_id", 1)], unique=True)
            
            print("MongoDB collections and indexes initialized successfully")
        except Exception as e:
            print(f"Error initializing collections: {str(e)}")

    async def check_dashboard_permission(self, dashboard_name: str, user_id: int, user_roles: List[int], guild_id: int) -> bool:
        """Check if user has permission to use a dashboard"""
        try:
            # Check if user is bot owner
            if str(user_id) == os.getenv('BOT_OWNER_ID'):
                return True

            # Get dashboard permissions
            permissions = await self.db.dashboard_permissions.find_one({
                'dashboard_name': dashboard_name,
                'guild_id': guild_id
            })

            # If no permissions set, only allow administrators
            if not permissions:
                return False

            # Check user direct permission
            user_perm = await self.db.dashboard_permissions.find_one({
                'dashboard_name': dashboard_name,
                'user_id': user_id,
                'guild_id': guild_id
            })
            if user_perm:
                return True

            # Check role permissions
            role_perm = await self.db.dashboard_permissions.find_one({
                'dashboard_name': dashboard_name,
                'role_id': {'$in': user_roles},
                'guild_id': guild_id
            })
            return bool(role_perm)

        except Exception as e:
            print(f"Error checking dashboard permission: {str(e)}")
            return False

    async def check_command_permission(self, command_name: str, user_id: int, user_roles: List[int], guild_id: int) -> bool:
        """Check if user has permission to use a command"""
        try:
            # Check if user is bot owner
            if str(user_id) == os.getenv('BOT_OWNER_ID'):
                return True

            # Get command permissions
            permissions = await self.db.command_permissions.find_one({
                'command_name': command_name,
                'guild_id': guild_id
            })

            # If no permissions set, allow by default
            if not permissions:
                return True

            # Check user direct permission
            user_perm = await self.db.command_permissions.find_one({
                'command_name': command_name,
                'user_id': user_id,
                'guild_id': guild_id
            })
            if user_perm:
                return True

            # Check role permissions
            role_perm = await self.db.command_permissions.find_one({
                'command_name': command_name,
                'role_id': {'$in': user_roles},
                'guild_id': guild_id
            })
            return bool(role_perm)

        except Exception as e:
            print(f"Error checking command permission: {str(e)}")
            return False

    # Clan Data Management
    async def get_clan_data(self, guild_id: int) -> List[Dict]:
        """Get all clan data for a guild"""
        try:
            cursor = self.db.clans.find({"guild_id": guild_id})
            return await cursor.to_list(length=None)
        except Exception as e:
            print(f"Error getting clan data: {str(e)}")
            return []

    async def get_clan_by_name(self, guild_id: int, clan_name: str) -> Optional[Dict]:
        """Get clan data by name"""
        try:
            return await self.db.clans.find_one({
                "guild_id": guild_id,
                "name": clan_name
            })
        except Exception as e:
            print(f"Error getting clan by name: {str(e)}")
            return None

    async def add_clan(self, guild_id: int, clan_data: Dict) -> bool:
        """Add a new clan"""
        try:
            clan_data['guild_id'] = guild_id
            clan_data['created_at'] = datetime.utcnow()
            await self.db.clans.insert_one(clan_data)
            return True
        except Exception as e:
            print(f"Error adding clan: {str(e)}")
            return False

    async def update_clan(self, guild_id: int, clan_name: str, update_data: Dict) -> bool:
        """Update clan data"""
        try:
            update_data['updated_at'] = datetime.utcnow()
            result = await self.db.clans.update_one(
                {"guild_id": guild_id, "name": clan_name},
                {"$set": update_data}
            )
            return result.modified_count > 0
        except Exception as e:
            print(f"Error updating clan: {str(e)}")
            return False

    async def delete_clan(self, guild_id: int, clan_name: str) -> bool:
        """Delete a clan"""
        try:
            result = await self.db.clans.delete_one({
                "guild_id": guild_id,
                "name": clan_name
            })
            return result.deleted_count > 0
        except Exception as e:
            print(f"Error deleting clan: {str(e)}")
            return False

    # Permission Management
    async def add_dashboard_permission(self, dashboard_name: str, guild_id: int, user_id: Optional[int] = None,
                                     role_id: Optional[int] = None) -> bool:
        """Add dashboard permission"""
        try:
            doc = {
                'dashboard_name': dashboard_name,
                'guild_id': guild_id,
                'created_at': datetime.utcnow()
            }
            if user_id:
                doc['user_id'] = user_id
            if role_id:
                doc['role_id'] = role_id
            
            await self.db.dashboard_permissions.insert_one(doc)
            return True
        except Exception as e:
            print(f"Error adding dashboard permission: {str(e)}")
            return False

    async def remove_dashboard_permission(self, dashboard_name: str, guild_id: int, user_id: Optional[int] = None,
                                       role_id: Optional[int] = None) -> bool:
        """Remove dashboard permission"""
        try:
            query = {
                'dashboard_name': dashboard_name,
                'guild_id': guild_id
            }
            if user_id:
                query['user_id'] = user_id
            if role_id:
                query['role_id'] = role_id
                
            result = await self.db.dashboard_permissions.delete_one(query)
            return result.deleted_count > 0
        except Exception as e:
            print(f"Error removing dashboard permission: {str(e)}")
            return False