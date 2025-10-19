from motor import motor_asyncio
import os
import asyncio
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import discord
from .permission_responses import PermissionResponses

class MongoManager:
    def __init__(self):
        """Initialize MongoDB connection"""
        self._load_env_variables()
        self.client = None
        self.db = None
        
    async def initialize(self):
        """Initialize MongoDB connection and setup collections"""
        try:
            # Connect to MongoDB
            self.client = motor_asyncio.AsyncIOMotorClient(os.getenv('MONGO_URI'))
            self.db = self.client[os.getenv('MONGO_DB_NAME')]
            
            # Initialize collections and indexes
            await self._initialize_collections()
            print("MongoDB initialization complete")
            
        except Exception as e:
            print(f"Failed to initialize MongoDB: {str(e)}")
            raise

    def _load_env_variables(self):
        """Load and validate required environment variables"""
        required_vars = {
            'MONGO_URI': 'MongoDB connection URI',
            'MONGO_DB_NAME': 'Database name',
            'BOT_OWNER_ID': 'Bot owner Discord ID'
        }
        
        missing_vars = []
        for var, description in required_vars.items():
            if not os.getenv(var):
                missing_vars.append(f"{var} ({description})")
        
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

    async def _initialize_collections(self):
        """Initialize collections with proper schemas and indexes safely"""
        try:
            # Create collections if they don't exist
            collections = [
                'dashboard_permissions',
                'command_permissions',
                'color_roles',
                'booster_roles',
                'panel_images',
                'ticket_config',
                'counting_system',
                'clan_info'
            ]
            
            for collection in collections:
                if collection not in await self.db.list_collection_names():
                    await self.db.create_collection(collection)
            
            # Create indexes
            await self._create_indexes()
        except Exception as e:
            print(f"Error initializing collections: {e}")
            raise
            
    async def _create_indexes(self):
        """Create required indexes for collections"""
        try:
            # Color roles indexes
            await self.db.color_roles.create_index([
                ('guild_id', 1),
                ('role_id', 1)
            ], unique=True)

            # Booster roles indexes
            await self.db.booster_roles.create_index([
                ('guild_id', 1),
                ('role_id', 1)
            ], unique=True)

            # Panel images indexes
            await self.db.panel_images.create_index([
                ('guild_id', 1),
                ('panel_type', 1)
            ], unique=True)
            
            # Counting system indexes
            await self.db.counting_system.create_index([
                ('guild_id', 1),
                ('channel_id', 1)
            ], unique=True)
            
            # Questions system indexes
            await self.db.questions.create_index([
                ('guild_id', 1),
                ('ticket_type', 1)
            ])

            # Active tickets indexes
            await self.db.active_tickets.create_index([
                ('guild_id', 1),
                ('user_id', 1),
                ('ticket_type', 1)
            ], unique=True)
            await self.db.active_tickets.create_index([
                ('channel_id', 1)
            ], unique=True)
            await self.db.active_tickets.create_index([
                ('created_at', 1)
            ])
        except Exception as e:
            print(f"Error creating indexes: {e}")
            raise
            
    # Questions Management Methods
    async def get_questions(self, guild_id: int, ticket_type: str) -> List[Dict]:
        """Get questions for a specific ticket type"""
        try:
            cursor = self.db.questions.find({
                'guild_id': guild_id,
                'ticket_type': ticket_type
            })
            return await cursor.to_list(length=None)
        except Exception as e:
            print(f"Error getting questions: {e}")
            return []

    async def update_questions(self, guild_id: int, ticket_type: str, questions: List[Dict]) -> bool:
        """Update questions for a specific ticket type"""
        try:
            await self.db.questions.update_one(
                {
                    'guild_id': guild_id,
                    'ticket_type': ticket_type
                },
                {
                    '$set': {
                        'questions': questions,
                        'updated_at': datetime.utcnow()
                    }
                },
                upsert=True
            )
            return True
        except Exception as e:
            print(f"Error updating questions: {e}")
            return False

    async def add_question(self, guild_id: int, ticket_type: str, question: Dict) -> bool:
        """Add a new question to a ticket type"""
        try:
            await self.db.questions.update_one(
                {
                    'guild_id': guild_id,
                    'ticket_type': ticket_type
                },
                {
                    '$push': {
                        'questions': question
                    },
                    '$set': {
                        'updated_at': datetime.utcnow()
                    }
                },
                upsert=True
            )
            return True
        except Exception as e:
            print(f"Error adding question: {e}")
            return False

    async def remove_question(self, guild_id: int, ticket_type: str, question_id: str) -> bool:
        """Remove a question from a ticket type"""
        try:
            await self.db.questions.update_one(
                {
                    'guild_id': guild_id,
                    'ticket_type': ticket_type
                },
                {
                    '$pull': {
                        'questions': {
                            'id': question_id
                        }
                    },
                    '$set': {
                        'updated_at': datetime.utcnow()
                    }
                }
            )
            return True
        except Exception as e:
            print(f"Error removing question: {e}")
            return False

    # Ticket Tracking Methods
    async def create_ticket(
        self,
        guild_id: int,
        channel_id: int,
        user_id: int,
        ticket_type: str,
        thread_id: Optional[int] = None
    ) -> bool:
        """Create a new active ticket"""
        try:
            await self.db.active_tickets.insert_one({
                'guild_id': guild_id,
                'channel_id': channel_id,
                'thread_id': thread_id,
                'user_id': user_id,
                'ticket_type': ticket_type,
                'status': 'open',
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            })
            return True
        except Exception as e:
            print(f"Error creating ticket: {e}")
            return False

    async def get_active_ticket(
        self,
        guild_id: int,
        user_id: int,
        ticket_type: str
    ) -> Optional[Dict]:
        """Get active ticket for a user"""
        try:
            return await self.db.active_tickets.find_one({
                'guild_id': guild_id,
                'user_id': user_id,
                'ticket_type': ticket_type,
                'status': 'open'
            })
        except Exception as e:
            print(f"Error getting active ticket: {e}")
            return None

    async def close_ticket(
        self,
        guild_id: int,
        channel_id: int,
        closed_by: int,
        reason: str
    ) -> bool:
        """Close an active ticket"""
        try:
            await self.db.active_tickets.update_one(
                {
                    'guild_id': guild_id,
                    'channel_id': channel_id,
                    'status': 'open'
                },
                {
                    '$set': {
                        'status': 'closed',
                        'closed_by': closed_by,
                        'close_reason': reason,
                        'closed_at': datetime.utcnow(),
                        'updated_at': datetime.utcnow()
                    }
                }
            )
            return True
        except Exception as e:
            print(f"Error closing ticket: {e}")
            return False

    async def get_ticket_by_channel(
        self,
        channel_id: int
    ) -> Optional[Dict]:
        """Get ticket information by channel ID"""
        try:
            return await self.db.active_tickets.find_one({
                'channel_id': channel_id
            })
        except Exception as e:
            print(f"Error getting ticket: {e}")
            return None

    async def update_ticket_thread(
        self,
        channel_id: int,
        thread_id: int
    ) -> bool:
        """Update ticket with thread information"""
        try:
            await self.db.active_tickets.update_one(
                {
                    'channel_id': channel_id
                },
                {
                    '$set': {
                        'thread_id': thread_id,
                        'updated_at': datetime.utcnow()
                    }
                }
            )
            return True
        except Exception as e:
            print(f"Error updating ticket thread: {e}")
            return False
            
    # Counting System Methods
    async def setup_counting(self, guild_id: int, channel_id: int) -> bool:
        """Setup counting system for a channel"""
        try:
            await self.db.counting_system.update_one(
                {
                    'guild_id': guild_id,
                    'channel_id': channel_id
                },
                {
                    '$set': {
                        'enabled': True,
                        'current_count': 0,
                        'updated_at': datetime.utcnow()
                    }
                },
                upsert=True
            )
            return True
        except Exception as e:
            print(f"Error setting up counting: {e}")
            return False

    async def disable_counting(self, guild_id: int, channel_id: int) -> bool:
        """Disable counting system for a channel"""
        try:
            await self.db.counting_system.update_one(
                {
                    'guild_id': guild_id,
                    'channel_id': channel_id
                },
                {
                    '$set': {
                        'enabled': False,
                        'updated_at': datetime.utcnow()
                    }
                }
            )
            return True
        except Exception as e:
            print(f"Error disabling counting: {e}")
            return False

    async def get_counting_data(self, guild_id: int) -> Optional[dict]:
        """Get counting data for a guild"""
        try:
            return await self.db.counting_system.find_one({'guild_id': guild_id, 'enabled': True})
        except Exception as e:
            print(f"Error getting counting data: {e}")
            return None

    async def update_count(self, guild_id: int, channel_id: int, count: int, user_id: int) -> bool:
        """Update the current count for a channel"""
        try:
            await self.db.counting_system.update_one(
                {
                    'guild_id': guild_id,
                    'channel_id': channel_id
                },
                {
                    '$set': {
                        'current_count': count,
                        'last_counter': user_id,
                        'updated_at': datetime.utcnow()
                    }
                }
            )
            return True
        except Exception as e:
            print(f"Error updating count: {e}")
            return False

    async def get_guild_counting_channels(self, guild_id: int) -> list:
        """Get all counting channels for a guild"""
        try:
            cursor = self.db.counting_system.find({
                'guild_id': guild_id,
                'enabled': True
            })
            return await cursor.to_list(length=None)
        except Exception as e:
            print(f"Error getting counting channels: {e}")
            return []

    # Color Roles Management
    async def add_color_role(self, guild_id: int, role_id: int, color_hex: str) -> bool:
        """Add a color role to the database"""
        try:
            await self.db.color_roles.update_one(
                {'guild_id': guild_id, 'role_id': role_id},
                {
                    '$set': {
                        'color_hex': color_hex,
                        'updated_at': datetime.utcnow()
                    }
                },
                upsert=True
            )
            return True
        except Exception as e:
            print(f"Error adding color role: {e}")
            return False

    async def get_color_roles(self, guild_id: int) -> List[Dict]:
        """Get all color roles for a guild"""
        try:
            cursor = self.db.color_roles.find({'guild_id': guild_id})
            return await cursor.to_list(length=None)
        except Exception as e:
            print(f"Error getting color roles: {e}")
            return []

    async def remove_color_role(self, guild_id: int, role_id: int) -> bool:
        """Remove a color role from the database"""
        try:
            result = await self.db.color_roles.delete_one({
                'guild_id': guild_id,
                'role_id': role_id
            })
            return result.deleted_count > 0
        except Exception as e:
            print(f"Error removing color role: {e}")
            return False

    # Booster Roles Management
    async def add_booster_role(self, guild_id: int, role_id: int, description: str) -> bool:
        """Add a booster role to the database"""
        try:
            await self.db.booster_roles.update_one(
                {'guild_id': guild_id, 'role_id': role_id},
                {
                    '$set': {
                        'description': description,
                        'updated_at': datetime.utcnow()
                    }
                },
                upsert=True
            )
            return True
        except Exception as e:
            print(f"Error adding booster role: {e}")
            return False

    async def get_booster_roles(self, guild_id: int) -> List[Dict]:
        """Get all booster roles for a guild"""
        try:
            cursor = self.db.booster_roles.find({'guild_id': guild_id})
            return await cursor.to_list(length=None)
        except Exception as e:
            print(f"Error getting booster roles: {e}")
            return []

    async def remove_booster_role(self, guild_id: int, role_id: int) -> bool:
        """Remove a booster role from the database"""
        try:
            result = await self.db.booster_roles.delete_one({
                'guild_id': guild_id,
                'role_id': role_id
            })
            return result.deleted_count > 0
        except Exception as e:
            print(f"Error removing booster role: {e}")
            return False

    # Panel Images Management
    async def save_panel_image(self, panel_type: str, image_url: str, guild_id: int) -> bool:
        """Save a panel image URL to the database"""
        try:
            await self.db.panel_images.update_one(
                {
                    'guild_id': guild_id,
                    'panel_type': panel_type
                },
                {
                    '$set': {
                        'image_url': image_url,
                        'updated_at': datetime.utcnow()
                    }
                },
                upsert=True
            )
            return True
        except Exception as e:
            print(f"Error saving panel image: {e}")
            return False

    async def get_panel_image(self, panel_type: str, guild_id: int) -> Optional[str]:
        """Get the panel image URL for a specific panel type"""
        try:
            doc = await self.db.panel_images.find_one({
                'guild_id': guild_id,
                'panel_type': panel_type
            })
            return doc['image_url'] if doc else None
        except Exception as e:
            print(f"Error getting panel image: {e}")
            return None

    async def delete_panel_image(self, panel_type: str, guild_id: int) -> bool:
        """Delete a panel image from the database"""
        try:
            result = await self.db.panel_images.delete_one({
                'guild_id': guild_id,
                'panel_type': panel_type
            })
            return result.deleted_count > 0
        except Exception as e:
            print(f"Error deleting panel image: {e}")
            return False
            # Define collection configurations with indexes
            collections_config = {
                'tickets': {
                    'indexes': [
                        [("ticket_type", 1), ("status", 1)],
                        [("guild_id", 1), ("created_at", -1)]
                    ]
                },
                'ticket_config': {
                    'indexes': [
                        [("ticket_type", 1), ("guild_id", 1)],
                        [("updated_at", -1)]
                    ],
                    'unique_indexes': [
                        [("ticket_type", 1), ("guild_id", 1)]
                    ]
                },
                'ticket_staff': {
                    'indexes': [
                        [("ticket_type", 1), ("guild_id", 1)],
                        [("user_id", 1)],
                        [("role_id", 1)]
                    ],
                    'unique_indexes': [
                        [("ticket_type", 1), ("guild_id", 1), ("user_id", 1)],
                        [("ticket_type", 1), ("guild_id", 1), ("role_id", 1)]
                    ]
                },
                'panel_channels': {
                    'indexes': [
                        [("panel_type", 1), ("guild_id", 1)],
                        [("channel_id", 1)]
                    ],
                    'unique_indexes': [
                        [("panel_type", 1), ("guild_id", 1)]
                    ]
                },
                'panel_images': {
                    'indexes': [
                        [("panel_type", 1), ("guild_id", 1)],
                        [("updated_at", -1)]
                    ],
                    'unique_indexes': [
                        [("panel_type", 1), ("guild_id", 1)]
                    ]
                },
                'clans': {
                    'indexes': [
                        [("name", 1), ("guild_id", 1)],
                        [("updated_at", -1)]
                    ],
                    'unique_indexes': [
                        [("name", 1), ("guild_id", 1)]
                    ]
                },
                'guild_settings': {
                    'indexes': [
                        [("guild_id", 1), ("type", 1)],
                        [("updated_at", -1)]
                    ],
                    'unique_indexes': [
                        [("guild_id", 1), ("type", 1)]
                    ]
                },
                'dashboard_permissions': {
                    'indexes': [
                        [("dashboard_name", 1), ("guild_id", 1)],
                        [("user_id", 1)],
                        [("role_id", 1)]
                    ]
                },
                'command_permissions': {
                    'indexes': [
                        [("command_name", 1), ("guild_id", 1)],
                        [("user_id", 1)],
                        [("role_id", 1)]
                    ]
                },
                'counting_channels': {
                    'indexes': [
                        [("channel_id", 1), ("guild_id", 1)],
                        [("enabled", 1)]
                    ],
                    'unique_indexes': [
                        [("channel_id", 1), ("guild_id", 1)]
                    ]
                }
            }

            # Create collections if they don't exist
            existing_collections = await self.db.list_collection_names()
            for collection_name in collections_config.keys():
                if collection_name not in existing_collections:
                    await self.db.create_collection(collection_name)
                    print(f"Created collection: {collection_name}")

            # Create indexes for each collection
            for collection_name, config in collections_config.items():
                collection = self.db[collection_name]
                
                # Helper to create index name
                def index_name(fields):
                    return '_'.join([f"{k}_{v}" for k, v in fields])
                
                # Create regular indexes
                if 'indexes' in config:
                    for index in config['indexes']:
                        try:
                            await collection.create_index(index, name=index_name(index))
                        except Exception as e:
                            # Ignore index conflicts
                            if 'already exists' not in str(e):
                                print(f"Index creation error: {e}")
                
                # Create unique indexes
                if 'unique_indexes' in config:
                    for index in config['unique_indexes']:
                        try:
                            await collection.create_index(index, unique=True, name=index_name(index))
                        except Exception as e:
                            if 'already exists' not in str(e) and 'IndexKeySpecsConflict' not in str(e):
                                print(f"Unique index creation error: {e}")

            print("MongoDB collections and indexes initialized successfully")
            collections = await self.db.list_collection_names()
            print(f"Available collections: {', '.join(collections)}")
            
        except Exception as e:
            print(f"Error initializing collections: {str(e)}")

    async def check_dashboard_permission(self, dashboard_name: str, user_id: int, user_roles: List[int], guild_id: int) -> bool:
        """Check if user has permission to use a dashboard"""
        try:
            # Check if user is bot owner
            if str(user_id) == os.getenv('BOT_OWNER_ID'):
                return True

            # Get guild roles to check for admin
            admin_roles = await self.db.dashboard_permissions.find_one({
                'dashboard_name': dashboard_name,
                'guild_id': guild_id,
                'is_admin': True
            })

            # Check admin roles
            if admin_roles and any(role_id in user_roles for role_id in admin_roles.get('role_ids', [])):
                return True

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

    # Ticket System Methods
    async def save_ticket_questions(self, ticket_type: str, questions: List[str], guild_id: int) -> bool:
        """Save questions for a ticket type"""
        try:
            await self.db.ticket_config.update_one(
                {
                    'ticket_type': ticket_type,
                    'guild_id': guild_id
                },
                {
                    '$set': {
                        'questions': questions,
                        'updated_at': datetime.utcnow()
                    }
                },
                upsert=True
            )
            return True
        except Exception as e:
            print(f"Error saving ticket questions: {str(e)}")
            return False

    async def get_ticket_questions(self, ticket_type: str, guild_id: int) -> List[str]:
        """Get questions for a ticket type"""
        try:
            config = await self.db.ticket_config.find_one({
                'ticket_type': ticket_type,
                'guild_id': guild_id
            })
            return config.get('questions', []) if config else []
        except Exception as e:
            print(f"Error getting ticket questions: {str(e)}")
            return []

    async def add_ticket_staff(self, ticket_type: str, guild_id: int, 
                             user_id: Optional[int] = None, role_id: Optional[int] = None) -> bool:
        """Add staff member or role to a ticket type"""
        try:
            # Check if this staff member/role is already added
            existing = await self.db.ticket_staff.find_one({
                'ticket_type': ticket_type,
                'guild_id': guild_id,
                '$or': [
                    {'user_id': user_id} if user_id else {'_id': None},
                    {'role_id': role_id} if role_id else {'_id': None}
                ]
            })
            
            if existing:
                return False  # Already exists
            
            # Add new staff entry
            doc = {
                'ticket_type': ticket_type,
                'guild_id': guild_id,
                'added_at': datetime.utcnow()
            }
            if user_id:
                doc['user_id'] = user_id
            if role_id:
                doc['role_id'] = role_id
            
            await self.db.ticket_staff.insert_one(doc)
            return True
        except Exception as e:
            print(f"Error adding ticket staff: {str(e)}")
            return False

    async def remove_ticket_staff(self, ticket_type: str, guild_id: int,
                                user_id: Optional[int] = None, role_id: Optional[int] = None) -> bool:
        """Remove staff member or role from a ticket type"""
        try:
            query = {
                'ticket_type': ticket_type,
                'guild_id': guild_id
            }
            if user_id:
                query['user_id'] = user_id
            if role_id:
                query['role_id'] = role_id
            
            result = await self.db.ticket_staff.delete_one(query)
            return result.deleted_count > 0
        except Exception as e:
            print(f"Error removing ticket staff: {str(e)}")
            return False

    async def save_ticket(self, ticket_type: str, ticket_data: Dict[str, Any]) -> bool:
        """Save a new ticket"""
        try:
            ticket_data['created_at'] = datetime.utcnow()
            ticket_data['ticket_type'] = ticket_type
            ticket_data['status'] = ticket_data.get('status', 'pending')
            await self.db.tickets.insert_one(ticket_data)
            return True
        except Exception as e:
            print(f"Error saving ticket: {str(e)}")
            return False

    async def update_ticket_status(self, ticket_id: str, new_status: str, 
                                 updated_by: int, reason: Optional[str] = None) -> bool:
        """Update ticket status"""
        try:
            update_data = {
                'status': new_status,
                'updated_at': datetime.utcnow(),
                'updated_by': updated_by
            }
            if reason:
                update_data['status_reason'] = reason

            result = await self.db.tickets.update_one(
                {'_id': ticket_id},
                {'$set': update_data}
            )
            return result.modified_count > 0
        except Exception as e:
            print(f"Error updating ticket status: {str(e)}")
            return False

    # Panel Methods
    async def save_panel_channel(self, panel_type: str, channel_id: int, guild_id: int) -> bool:
        """Save channel for a panel"""
        try:
            await self.db.panel_channels.update_one(
                {
                    'panel_type': panel_type,
                    'guild_id': guild_id
                },
                {
                    '$set': {
                        'channel_id': channel_id,
                        'updated_at': datetime.utcnow()
                    }
                },
                upsert=True
            )
            return True
        except Exception as e:
            print(f"Error saving panel channel: {str(e)}")
            return False

    async def get_panel_channel(self, panel_type: str, guild_id: int) -> Optional[int]:
        """Get channel for a panel"""
        try:
            doc = await self.db.panel_channels.find_one({
                'panel_type': panel_type,
                'guild_id': guild_id
            })
            return doc['channel_id'] if doc else None
        except Exception as e:
            print(f"Error getting panel channel: {str(e)}")
            return None

    async def save_panel_image(self, panel_type: str, image_url: str, guild_id: int) -> bool:
        """Save panel image URL"""
        try:
            await self.db.panel_images.update_one(
                {
                    'panel_type': panel_type,
                    'guild_id': guild_id
                },
                {
                    '$set': {
                        'image_url': image_url,
                        'updated_at': datetime.utcnow()
                    }
                },
                upsert=True
            )
            return True
        except Exception as e:
            print(f"Error saving panel image: {str(e)}")
            return False

    async def get_panel_image(self, panel_type: str, guild_id: int) -> Optional[str]:
        """Get panel image URL"""
        try:
            doc = await self.db.panel_images.find_one({
                'panel_type': panel_type,
                'guild_id': guild_id
            })
            return doc['image_url'] if doc else None
        except Exception as e:
            print(f"Error getting panel image: {str(e)}")
            return None

    async def get_ticket_staff(self, ticket_type: str, guild_id: int) -> Dict[str, List[int]]:
        """Get all staff members and roles for a ticket type"""
        try:
            cursor = self.db.ticket_staff.find({
                'ticket_type': ticket_type,
                'guild_id': guild_id
            })
            
            staff = {
                'users': [],
                'roles': []
            }
            
            async for doc in cursor:
                if 'user_id' in doc:
                    staff['users'].append(doc['user_id'])
                if 'role_id' in doc:
                    staff['roles'].append(doc['role_id'])
                    
            return staff
            
        except Exception as e:
            print(f"Error getting ticket staff: {str(e)}")
            return {'users': [], 'roles': []}

    # Clan Methods
    async def save_clan_data(self, clan_data: Dict[str, Any], guild_id: int) -> bool:
        """Save clan data"""
        try:
            clan_data['guild_id'] = guild_id
            clan_data['updated_at'] = datetime.utcnow()
            await self.db.clans.update_one(
                {
                    'name': clan_data['name'],
                    'guild_id': guild_id
                },
                {'$set': clan_data},
                upsert=True
            )
            return True
        except Exception as e:
            print(f"Error saving clan data: {str(e)}")
            return False

    # Settings Methods
    async def save_guild_settings(self, guild_id: int, settings_type: str, settings: Dict[str, Any]) -> bool:
        """Save guild settings"""
        try:
            settings['updated_at'] = datetime.utcnow()
            await self.db.guild_settings.update_one(
                {
                    'guild_id': guild_id,
                    'type': settings_type
                },
                {
                    '$set': settings
                },
                upsert=True
            )
            return True
        except Exception as e:
            print(f"Error saving guild settings: {str(e)}")
            return False

    async def get_guild_settings(self, guild_id: int, settings_type: str) -> Optional[Dict[str, Any]]:
        """Get guild settings"""
        try:
            return await self.db.guild_settings.find_one({
                'guild_id': guild_id,
                'type': settings_type
            })
        except Exception as e:
            print(f"Error getting guild settings: {str(e)}")
            return None

    # Missing methods that other cogs are trying to use
    async def add_dashboard_permission(self, dashboard_name: str, guild_id: int, user_id: Optional[int] = None, role_id: Optional[int] = None) -> bool:
        """Add dashboard permission for user or role"""
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

    async def add_color_role(self, role_id: int, guild_id: int) -> bool:
        """Add color role for booster dashboard"""
        try:
            doc = {
                'role_id': role_id,
                'guild_id': guild_id,
                'created_at': datetime.utcnow()
            }
            await self.db.guild_settings.update_one(
                {'guild_id': guild_id, 'type': 'color_roles'},
                {'$set': doc},
                upsert=True
            )
            return True
        except Exception as e:
            print(f"Error adding color role: {str(e)}")
            return False

    async def get_counting_data(self, guild_id: int) -> Optional[Dict[str, Any]]:
        """Get counting system data"""
        try:
            return await self.db.counting_channels.find_one({'guild_id': guild_id})
        except Exception as e:
            print(f"Error getting counting data: {str(e)}")
            return None

    async def save_counting_data(self, guild_id: int, channel_id: int, enabled: bool = True) -> bool:
        """Save counting system data"""
        try:
            await self.db.counting_channels.update_one(
                {'guild_id': guild_id},
                {
                    '$set': {
                        'channel_id': channel_id,
                        'enabled': enabled,
                        'updated_at': datetime.utcnow()
                    }
                },
                upsert=True
            )
            return True
        except Exception as e:
            print(f"Error saving counting data: {str(e)}")
            return False

    async def remove_panel_image(self, panel_type: str, guild_id: int) -> bool:
        """Remove panel image"""
        try:
            await self.db.panel_images.delete_one({
                'panel_type': panel_type,
                'guild_id': guild_id
            })
            return True
        except Exception as e:
            print(f"Error removing panel image: {str(e)}")
            return False

    # Clan management methods
    async def get_all_clans(self, guild_id: int) -> list:
        """Get all clans for a guild"""
        try:
            cursor = self.db.clans.find({'guild_id': guild_id})
            return await cursor.to_list(length=None)
        except Exception as e:
            print(f"Error getting clans: {str(e)}")
            return []

    async def get_clan_by_id(self, clan_id: str) -> Optional[Dict[str, Any]]:
        """Get clan by ID"""
        try:
            from bson import ObjectId
            return await self.db.clans.find_one({'_id': ObjectId(clan_id)})
        except Exception as e:
            print(f"Error getting clan by ID: {str(e)}")
            return None

    async def save_clan_data(self, clan_data: Dict[str, Any], guild_id: int) -> bool:
        """Save clan data"""
        try:
            clan_data['guild_id'] = guild_id
            await self.db.clans.insert_one(clan_data)
            return True
        except Exception as e:
            print(f"Error saving clan data: {str(e)}")
            return False

    async def update_clan_field(self, clan_id: str, field: str, value: Any) -> bool:
        """Update a specific field in clan data"""
        try:
            from bson import ObjectId
            result = await self.db.clans.update_one(
                {'_id': ObjectId(clan_id)},
                {'$set': {field: value}}
            )
            return result.modified_count > 0
        except Exception as e:
            print(f"Error updating clan field: {str(e)}")
            return False

    async def update_clan_data(self, clan_id: str, updates: Dict[str, Any]) -> bool:
        """Update multiple fields in clan data"""
        try:
            from bson import ObjectId
            result = await self.db.clans.update_one(
                {'_id': ObjectId(clan_id)},
                {'$set': updates}
            )
            return result.modified_count > 0
        except Exception as e:
            print(f"Error updating clan data: {str(e)}")
            return False

    async def delete_clan(self, clan_id: str) -> bool:
        """Delete a clan"""
        try:
            from bson import ObjectId
            result = await self.db.clans.delete_one({'_id': ObjectId(clan_id)})
            return result.deleted_count > 0
        except Exception as e:
            print(f"Error deleting clan: {str(e)}")
            return False

    # Ticket system methods
    async def save_ticket_questions(self, ticket_type: str, guild_id: int, questions: list) -> bool:
        """Save ticket questions"""
        try:
            await self.db.ticket_config.update_one(
                {'ticket_type': ticket_type, 'guild_id': guild_id},
                {'$set': {'questions': questions, 'updated_at': datetime.utcnow()}},
                upsert=True
            )
            return True
        except Exception as e:
            print(f"Error saving ticket questions: {str(e)}")
            return False

    async def get_ticket_questions(self, ticket_type: str, guild_id: int) -> list:
        """Get ticket questions"""
        try:
            doc = await self.db.ticket_config.find_one({
                'ticket_type': ticket_type,
                'guild_id': guild_id
            })
            return doc.get('questions', []) if doc else []
        except Exception as e:
            print(f"Error getting ticket questions: {str(e)}")
            return []

    async def add_ticket_staff(self, ticket_type: str, guild_id: int, user_id: Optional[int] = None, role_id: Optional[int] = None) -> bool:
        """Add ticket staff"""
        try:
            doc = {
                'ticket_type': ticket_type,
                'guild_id': guild_id,
                'created_at': datetime.utcnow()
            }
            if user_id:
                doc['user_id'] = user_id
            if role_id:
                doc['role_id'] = role_id
            
            await self.db.ticket_staff.insert_one(doc)
            return True
        except Exception as e:
            print(f"Error adding ticket staff: {str(e)}")
            return False

    async def get_ticket_staff(self, ticket_type: str, guild_id: int) -> list:
        """Get ticket staff"""
        try:
            cursor = self.db.ticket_staff.find({
                'ticket_type': ticket_type,
                'guild_id': guild_id
            })
            return await cursor.to_list(length=None)
        except Exception as e:
            print(f"Error getting ticket staff: {str(e)}")
            return []

    async def remove_ticket_staff(self, ticket_type: str, guild_id: int, user_id: Optional[int] = None, role_id: Optional[int] = None) -> bool:
        """Remove ticket staff"""
        try:
            query = {
                'ticket_type': ticket_type,
                'guild_id': guild_id
            }
            if user_id:
                query['user_id'] = user_id
            if role_id:
                query['role_id'] = role_id
            
            result = await self.db.ticket_staff.delete_one(query)
            return result.deleted_count > 0
        except Exception as e:
            print(f"Error removing ticket staff: {str(e)}")
            return False

    async def set_ticket_category(self, ticket_type: str, guild_id: int, category_id: int) -> bool:
        """Set ticket category"""
        try:
            await self.db.ticket_config.update_one(
                {'ticket_type': ticket_type, 'guild_id': guild_id},
                {'$set': {'category_id': category_id, 'updated_at': datetime.utcnow()}},
                upsert=True
            )
            return True
        except Exception as e:
            print(f"Error setting ticket category: {str(e)}")
            return False

    async def get_panel_image(self, panel_type: str, guild_id: int) -> Optional[str]:
        """Get panel image URL"""
        try:
            doc = await self.db.panel_images.find_one({
                'panel_type': panel_type,
                'guild_id': guild_id
            })
            return doc.get('image_url') if doc else None
        except Exception as e:
            print(f"Error getting panel image: {str(e)}")
            return None

    async def set_panel_image(self, panel_type: str, guild_id: int, image_url: str) -> bool:
        """Set panel image"""
        try:
            await self.db.panel_images.update_one(
                {'panel_type': panel_type, 'guild_id': guild_id},
                {'$set': {'image_url': image_url, 'updated_at': datetime.utcnow()}},
                upsert=True
            )
            return True
        except Exception as e:
            print(f"Error setting panel image: {str(e)}")
            return False

    async def get_clans_by_type_and_th(self, clan_type: str, min_th: int, guild_id: int) -> list:
        """Get clans by type and minimum TH level"""
        try:
            cursor = self.db.clans.find({
                'guild_id': guild_id,
                'clan_type': clan_type,
                'min_town_hall': {'$lte': min_th}  # Player's TH must be >= clan's minimum TH
            })
            return await cursor.to_list(length=None)
        except Exception as e:
            print(f"Error getting clans by type and TH: {str(e)}")
            return []