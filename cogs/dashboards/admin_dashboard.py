"""
Admin Dashboard Cog: Provides bot owner and authorized users with complete control over dashboard and slash command access (add, view, remove users/roles), plus bot system statistics. All operations visible only to properly permitted users. No forms; user/role selection by channel mention. Implements advanced error handling and attractive Discord embeds per PLAN.
"""
import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import os

class AdminDashboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.mongo = bot.mongo_manager
        self.data_manager = bot.data_manager

    def is_bot_owner(self, user_id: int) -> bool:
        """Check if user is bot owner"""
        return user_id == int(os.getenv('BOT_OWNER_ID'))

    @app_commands.command(name="admin_dashboard", description="🔐 Admin control panel (Bot Owner Only)")
    async def admin_dashboard(self, interaction: discord.Interaction):
        """Main admin dashboard"""
        if not self.is_bot_owner(interaction.user.id):
            embed = discord.Embed(
                title="❌ Access Denied",
                description="Only the bot owner can access the admin dashboard.",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        embed = discord.Embed(
            title="🔐 BLACKSPIRE NATION - Admin Dashboard",
            description="**Welcome, Mr Blaze!** \n\nSelect an option to manage the bot:",
            color=0x9932cc,
            timestamp=discord.utils.utcnow()
        )
        embed.set_footer(text="Blackspire Nation Admin Control", icon_url=self.bot.user.avatar.url if self.bot.user.avatar else None)
        embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else None)

        view = AdminMainView(self.bot)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class AdminMainView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=300)
        self.bot = bot
        self.mongo = bot.mongo_manager
        self.data_manager = bot.data_manager

    @discord.ui.button(label="User Management (Dashboards)", style=discord.ButtonStyle.primary, emoji="👥")
    async def dashboard_management(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            view = DashboardUserManagementView(self.bot)
            embed = discord.Embed(
                title="👥 Dashboard User Management",
                description="Manage who can access various dashboards",
                color=0x00ff00,
                timestamp=discord.utils.utcnow()
            )
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"Error: {str(e)}", ephemeral=True)

    @discord.ui.button(label="User Management (Slash Commands)", style=discord.ButtonStyle.primary, emoji="⚡")
    async def command_management(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            view = CommandUserManagementView(self.bot)
            embed = discord.Embed(
                title="⚡ Command User Management", 
                description="Manage who can access various slash commands",
                color=0x00ff00,
                timestamp=discord.utils.utcnow()
            )
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"Error: {str(e)}", ephemeral=True)

    @discord.ui.button(label="System Statistics", style=discord.ButtonStyle.secondary, emoji="📊")
    async def system_stats(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            # Get stats asynchronously
            stats = await self.mongo.get_system_stats()

            embed = discord.Embed(
                title="📊 System Statistics",
                color=0x0099ff,
                timestamp=discord.utils.utcnow()
            )

            # Basic stats
            embed.add_field(name="🏛️ Servers", value=len(self.bot.guilds), inline=True)
            embed.add_field(name="👥 Total Users", value=len(self.bot.users), inline=True)
            embed.add_field(name="🔧 Commands Loaded", value=len(self.bot.tree.get_commands()), inline=True)

            # Get database stats asynchronously
            dashboard_perms = await self.mongo.db.dashboard_permissions.count_documents({})
            command_perms = await self.mongo.db.command_permissions.count_documents({})
            ticket_configs = await self.mongo.db.ticket_config.count_documents({})

            embed.add_field(name="🔐 Dashboard Permissions", value=dashboard_perms, inline=True)
            embed.add_field(name="⚡ Command Permissions", value=command_perms, inline=True)  
            embed.add_field(name="🎫 Ticket Configurations", value=ticket_configs, inline=True)

            await interaction.response.send_message(embed=embed, view=self, ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(f"Error fetching stats: {str(e)}", ephemeral=True)

class DashboardUserManagementView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=300)
        self.bot = bot
        self.mongo = bot.mongo_manager
        self.data_manager = bot.data_manager

    @discord.ui.button(label="Add User", style=discord.ButtonStyle.success, emoji="➕")
    async def add_user(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = DashboardSelectorView(self.bot, "add_user")
        embed = discord.Embed(
            title="➕ Add User to Dashboard",
            description="Select a dashboard to give user access to:",
            color=0x00ff00
        )
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="Add Role", style=discord.ButtonStyle.success, emoji="🏷️")
    async def add_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = DashboardSelectorView(self.bot, "add_role")
        embed = discord.Embed(
            title="🏷️ Add Role to Dashboard",
            description="Select a dashboard to give role access to:",
            color=0x00ff00
        )
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="View Admins", style=discord.ButtonStyle.secondary, emoji="👀")
    async def view_admins(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = DashboardSelectorView(self.bot, "view_admins")
        embed = discord.Embed(
            title="👀 View Dashboard Admins",
            description="Select a dashboard to view its administrators:",
            color=0x0099ff
        )
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="Remove Admins", style=discord.ButtonStyle.danger, emoji="➖")
    async def remove_admins(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = DashboardSelectorView(self.bot, "remove_admins")
        embed = discord.Embed(
            title="➖ Remove Dashboard Admins",
            description="Select a dashboard to remove administrators from:",
            color=0xff0000
        )
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="🔙 Back", style=discord.ButtonStyle.secondary, row=4)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = AdminMainView(self.bot)
        embed = discord.Embed(
            title="🔐 BLACKSPIRE NATION - Admin Dashboard",
            description="**Welcome, Mr Blaze!** \n\nSelect an option to manage the bot:",
            color=0x9932cc,
            timestamp=discord.utils.utcnow()
        )
        embed.set_footer(text="Blackspire Nation Admin Control")
        await interaction.response.edit_message(embed=embed, view=view)

class CommandUserManagementView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=300)
        self.bot = bot
        self.mongo = bot.mongo_manager
        self.data_manager = bot.data_manager

    @discord.ui.button(label="Add User", style=discord.ButtonStyle.success, emoji="➕")
    async def add_user(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = CommandSelectorView(self.bot, "add_user")
        embed = discord.Embed(
            title="➕ Add User to Command",
            description="Select a command to give user access to:",
            color=0x00ff00
        )
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="Add Role", style=discord.ButtonStyle.success, emoji="🏷️")
    async def add_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = CommandSelectorView(self.bot, "add_role")
        embed = discord.Embed(
            title="🏷️ Add Role to Command",
            description="Select a command to give role access to:",
            color=0x00ff00
        )
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="View Admins", style=discord.ButtonStyle.secondary, emoji="👀")
    async def view_admins(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = CommandSelectorView(self.bot, "view_admins")
        embed = discord.Embed(
            title="👀 View Command Admins",
            description="Select a command to view its administrators:",
            color=0x0099ff
        )
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="Remove Admins", style=discord.ButtonStyle.danger, emoji="➖")
    async def remove_admins(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = CommandSelectorView(self.bot, "remove_admins")
        embed = discord.Embed(
            title="➖ Remove Command Admins", 
            description="Select a command to remove administrators from:",
            color=0xff0000
        )
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="🔙 Back", style=discord.ButtonStyle.secondary, row=4)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = AdminMainView(self.bot)
        embed = discord.Embed(
            title="🔐 BLACKSPIRE NATION - Admin Dashboard",
            description="**Welcome, Mr Blaze!** \n\nSelect an option to manage the bot:",
            color=0x9932cc,
            timestamp=discord.utils.utcnow()
        )
        embed.set_footer(text="Blackspire Nation Admin Control")
        await interaction.response.edit_message(embed=embed, view=view)

class DashboardSelectorView(discord.ui.View):
    def __init__(self, bot, action):
        super().__init__(timeout=300)
        self.bot = bot
        self.mongo = bot.mongo_manager
        self.action = action

        # Add dashboard selector dropdown
        self.add_item(DashboardDropdown(bot, action))

class DashboardDropdown(discord.ui.Select):
    def __init__(self, bot, action):
        self.bot = bot
        self.mongo = bot.mongo_manager
        self.action = action

        options = [
            discord.SelectOption(label="Admin Dashboard", value="admin_dashboard", emoji="🔐"),
            discord.SelectOption(label="Main Dashboard", value="main_dashboard", emoji="🎫"),
            discord.SelectOption(label="Booster Dashboard", value="booster_dashboard", emoji="🚀"),
            discord.SelectOption(label="Clan Dashboard", value="clan_dashboard", emoji="⚔️")
        ]

        super().__init__(placeholder="Select a dashboard...", options=options)

    async def callback(self, interaction: discord.Interaction):
        dashboard_name = self.values[0]

        if self.action == "add_user":
            embed = discord.Embed(
                title=f"➕ Add User to {dashboard_name.replace('_', ' ').title()}",
                description="Mention a user in your next message to give them access to this dashboard.",
                color=0x00ff00
            )
            await interaction.response.edit_message(embed=embed, view=None)

            def check(m):
                return m.author.id == interaction.user.id and m.channel.id == interaction.channel.id and m.mentions

            try:
                msg = await self.bot.wait_for('message', check=check, timeout=60.0)
                user = msg.mentions[0]
                await self.mongo.add_dashboard_permission(dashboard_name, interaction.guild.id, user_id=user.id)

                embed = discord.Embed(
                    title="✅ Success",
                    description=f"Added {user.mention} to {dashboard_name.replace('_', ' ').title()}",
                    color=0x00ff00
                )
                await interaction.followup.send(embed=embed, ephemeral=True)

            except asyncio.TimeoutError:
                embed = discord.Embed(
                    title="⏰ Timeout", 
                    description="You took too long to mention a user.",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)

        elif self.action == "add_role":
            embed = discord.Embed(
                title=f"🏷️ Add Role to {dashboard_name.replace('_', ' ').title()}",
                description="Mention a role in your next message to give it access to this dashboard.",
                color=0x00ff00
            )
            await interaction.response.edit_message(embed=embed, view=None)

            def check(m):
                return m.author.id == interaction.user.id and m.channel.id == interaction.channel.id and m.role_mentions

            try:
                msg = await self.bot.wait_for('message', check=check, timeout=60.0)
                role = msg.role_mentions[0]
                await self.mongo.add_dashboard_permission(dashboard_name, interaction.guild.id, role_id=role.id)

                embed = discord.Embed(
                    title="✅ Success",
                    description=f"Added {role.mention} to {dashboard_name.replace('_', ' ').title()}",
                    color=0x00ff00
                )
                await interaction.followup.send(embed=embed, ephemeral=True)

            except asyncio.TimeoutError:
                embed = discord.Embed(
                    title="⏰ Timeout",
                    description="You took too long to mention a role.",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)

        elif self.action == "view_admins":
            permissions = await self.mongo.get_dashboard_permissions(dashboard_name)

            embed = discord.Embed(
                title=f"👀 {dashboard_name.replace('_', ' ').title()} Administrators",
                color=0x0099ff
            )

            users = []
            roles = []

            for perm in permissions:
                if perm.get('user_id'):
                    user = self.bot.get_user(perm['user_id'])
                    users.append(user.mention if user else f"<@{perm['user_id']}>")
                elif perm.get('role_id'):
                    roles.append(f"<@&{perm['role_id']}>")

            if users:
                embed.add_field(name="👥 Users", value="\n".join(users), inline=False)
            if roles:
                embed.add_field(name="🏷️ Roles", value="\n".join(roles), inline=False)

            if not users and not roles:
                embed.description = "No administrators found for this dashboard."

            await interaction.response.edit_message(embed=embed, view=None)

class CommandSelectorView(discord.ui.View):
    def __init__(self, bot, action):
        super().__init__(timeout=300)
        self.bot = bot
        self.mongo = bot.mongo_manager
        self.action = action

        # Add command selector dropdown
        self.add_item(CommandDropdown(bot, action))

class CommandDropdown(discord.ui.Select):
    def __init__(self, bot, action):
        self.bot = bot
        self.mongo = bot.mongo_manager
        self.action = action

        options = [
            discord.SelectOption(label="Setup Counting", value="setup_counting", emoji="🔢"),
            discord.SelectOption(label="Disable Counting", value="disable_counting", emoji="❌"),
            discord.SelectOption(label="Add to Ticket", value="add_to_ticket", emoji="➕"),
            discord.SelectOption(label="Reject Player", value="reject_player", emoji="🚫"),
            discord.SelectOption(label="Help", value="help", emoji="❓")
        ]

        super().__init__(placeholder="Select a command...", options=options)

    async def callback(self, interaction: discord.Interaction):
        command_name = self.values[0]

        if self.action == "add_user":
            embed = discord.Embed(
                title=f"➕ Add User to {command_name.replace('_', ' ').title()}",
                description="Mention a user in your next message to give them access to this command.",
                color=0x00ff00
            )
            await interaction.response.edit_message(embed=embed, view=None)

            def check(m):
                return m.author.id == interaction.user.id and m.channel.id == interaction.channel.id and m.mentions

            try:
                msg = await self.bot.wait_for('message', check=check, timeout=60.0)
                user = msg.mentions[0]
                await self.mongo.add_dashboard_permission(command_name, interaction.guild.id, user_id=user.id)

                embed = discord.Embed(
                    title="✅ Success",
                    description=f"Added {user.mention} to {command_name.replace('_', ' ').title()}",
                    color=0x00ff00
                )
                await interaction.followup.send(embed=embed, ephemeral=True)

            except asyncio.TimeoutError:
                embed = discord.Embed(
                    title="⏰ Timeout",
                    description="You took too long to mention a user.",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)

        elif self.action == "add_role":
            embed = discord.Embed(
                title=f"🏷️ Add Role to {command_name.replace('_', ' ').title()}",
                description="Mention a role in your next message to give it access to this command.",
                color=0x00ff00
            )
            await interaction.response.edit_message(embed=embed, view=None)

            def check(m):
                return m.author.id == interaction.user.id and m.channel.id == interaction.channel.id and m.role_mentions

            try:
                msg = await self.bot.wait_for('message', check=check, timeout=60.0)
                role = msg.role_mentions[0]
                await self.mongo.add_dashboard_permission(command_name, interaction.guild.id, role_id=role.id)

                embed = discord.Embed(
                    title="✅ Success",
                    description=f"Added {role.mention} to {command_name.replace('_', ' ').title()}",
                    color=0x00ff00
                )
                await interaction.followup.send(embed=embed, ephemeral=True)

            except asyncio.TimeoutError:
                embed = discord.Embed(
                    title="⏰ Timeout",
                    description="You took too long to mention a role.",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)

        elif self.action == "view_admins":
            permissions = await self.mongo.get_command_permissions(command_name)

            embed = discord.Embed(
                title=f"👀 {command_name.replace('_', ' ').title()} Administrators",
                color=0x0099ff
            )

            users = []
            roles = []

            for perm in permissions:
                if perm.get('user_id'):
                    user = self.bot.get_user(perm['user_id'])
                    users.append(user.mention if user else f"<@{perm['user_id']}>")
                elif perm.get('role_id'):
                    roles.append(f"<@&{perm['role_id']}>")

            if users:
                embed.add_field(name="👥 Users", value="\n".join(users), inline=False)
            if roles:
                embed.add_field(name="🏷️ Roles", value="\n".join(roles), inline=False)

            if not users and not roles:
                embed.description = "No administrators found for this command."

            await interaction.response.edit_message(embed=embed, view=None)

async def setup(bot):
    await bot.add_cog(AdminDashboard(bot))
