from typing import List, Optional, Dict, Any
from datetime import datetime
import os
from dataclasses import dataclass
import discord
from .permission_responses import PermissionResponses
from .permission_result import PermissionResult

@dataclass
class PermissionCheck:
    allowed: bool
    message: str
    error: Optional[str] = None

class PermissionManager:
    def __init__(self, db):
        self.db = db
        self.bot_owner_id = int(os.getenv('BOT_OWNER_ID', '0'))

    async def check_permission(
        self, 
        permission_type: str,
        target_name: str,
        user: discord.Member,
        guild_id: int
    ) -> PermissionResult:
        """
        Generic permission check for both dashboards and commands
        """
        try:
            # Always allow bot owner
            if user.id == self.bot_owner_id:
                return PermissionResult.allow()

            # Get permissions from appropriate collection
            collection = self.db[f"{permission_type}_permissions"]
            permissions = await collection.find_one({
                'name': target_name,
                'guild_id': guild_id
            })

            # If no permissions set, create default and only allow bot owner
            if not permissions:
                await self._create_default_permissions(
                    collection=collection,
                    permission_type=permission_type,
                    target_name=target_name,
                    guild_id=guild_id
                )
                return PermissionCheck(
                    allowed=False,
                    message=f"No permissions set for this {permission_type}. Contact Mr. Blaze for access."
                )

            # Check user's permissions
            user_roles = [role.id for role in user.roles]
            
            if user.id in permissions.get('allowed_users', []):
                return PermissionCheck(True, "Direct user permission granted")

            allowed_roles = permissions.get('allowed_roles', [])
            if any(role in allowed_roles for role in user.roles):
                return PermissionCheck(True, "Role permission granted")

            # Log failed attempt
            await self._log_access_attempt(
                user_id=user.id,
                guild_id=guild_id,
                target_type=permission_type,
                target_name=target_name,
                success=False
            )

            return PermissionCheck(
                allowed=False,
                message="You don't have permission for this."
            )

        except Exception as e:
            error_msg = f"Error checking {permission_type} permission: {str(e)}"
            await self._log_error(error_msg, user.id, guild_id)
            return PermissionCheck(
                allowed=False,
                message="An error occurred checking permissions",
                error=error_msg
            )

    async def check_dashboard_permission(
        self,
        dashboard_name: str,
        user: discord.Member,
        guild_id: int
    ) -> PermissionCheck:
        """Check dashboard permissions with fun responses"""
        result = await self.check_permission('dashboard', dashboard_name, user, guild_id)
        if not result.allowed:
            embed = PermissionResponses.get_denial_embed(user, f"Dashboard: {dashboard_name}")
            result.message = embed
        return result

    async def check_command_permission(
        self,
        command_name: str,
        user: discord.Member,
        guild_id: int
    ) -> PermissionCheck:
        """Check command permissions with fun responses"""
        result = await self.check_permission('command', command_name, user, guild_id)
        if not result.allowed:
            embed = PermissionResponses.get_denial_embed(user, f"Command: {command_name}")
            result.message = embed
        return result

    async def _create_default_permissions(
        self,
        collection,
        permission_type: str,
        target_name: str,
        guild_id: int
    ):
        """Create default permissions for a target"""
        await collection.insert_one({
            f"{permission_type}_name": target_name,
            'guild_id': guild_id,
            'allowed_users': [self.bot_owner_id],
            'allowed_roles': [],
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        })

    async def _log_access_attempt(
        self,
        user_id: int,
        guild_id: int,
        target_type: str,
        target_name: str,
        success: bool
    ):
        """Log access attempts"""
        try:
            await self.db.access_logs.insert_one({
                'user_id': user_id,
                'guild_id': guild_id,
                'target_type': target_type,
                'target_name': target_name,
                'success': success,
                'timestamp': datetime.utcnow()
            })
        except Exception as e:
            print(f"Failed to log access attempt: {e}")

    async def _log_error(
        self,
        error_msg: str,
        user_id: Optional[int] = None,
        guild_id: Optional[int] = None
    ):
        """Log errors"""
        try:
            log_entry = {
                'error_message': error_msg,
                'timestamp': datetime.utcnow()
            }
            if user_id:
                log_entry['user_id'] = user_id
            if guild_id:
                log_entry['guild_id'] = guild_id
            
            await self.db.error_logs.insert_one(log_entry)
        except Exception as e:
            print(f"Failed to log error: {e}")

    async def add_permission(
        self,
        permission_type: str,
        target_name: str,
        guild_id: int,
        role_id: Optional[int] = None,
        user_id: Optional[int] = None
    ) -> bool:
        """Add a permission for a role or user"""
        try:
            update = {}
            if role_id:
                update = {'$addToSet': {'allowed_roles': role_id}}
            elif user_id:
                update = {'$addToSet': {'allowed_users': user_id}}
            else:
                return False

            update['$set'] = {'updated_at': datetime.utcnow()}
            
            result = await self.db[f"{permission_type}_permissions"].update_one(
                {
                    f"{permission_type}_name": target_name,
                    'guild_id': guild_id
                },
                update,
                upsert=True
            )
            
            return result.modified_count > 0 or result.upserted_id is not None
            
        except Exception as e:
            print(f"Error adding permission: {e}")
            return False

    async def remove_permission(
        self,
        permission_type: str,
        target_name: str,
        guild_id: int,
        role_id: Optional[int] = None,
        user_id: Optional[int] = None
    ) -> bool:
        """Remove a permission for a role or user"""
        try:
            update = {}
            if role_id:
                update = {'$pull': {'allowed_roles': role_id}}
            elif user_id:
                update = {'$pull': {'allowed_users': user_id}}
            else:
                return False

            update['$set'] = {'updated_at': datetime.utcnow()}
            
            result = await self.db[f"{permission_type}_permissions"].update_one(
                {
                    f"{permission_type}_name": target_name,
                    'guild_id': guild_id
                },
                update
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            print(f"Error removing permission: {e}")
            return False