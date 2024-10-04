import discord
from discord.ext import commands
from typing import Dict, Callable, Tuple, Set
import os

from config import load_config
from gumroad_verifier import verify_gumroad_sale
from jinxxy_verifier import verify_jinxxy_sale
import itertools
config = load_config()

intents = discord.Intents.default()
intents.message_content = True

VerifierFunction = Callable[[str], Tuple[bool, Set[str]]]

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='/', intents=intents)
        self.verifiers: Dict[str, VerifierFunction] = {
            "gumroad": verify_gumroad_sale,
            "jinxxy": verify_jinxxy_sale,
        }

    async def setup_hook(self):
        # Sync commands and register persistent views
        await self.tree.sync()
        self.add_view(PlatformSelectView())  # Register the view so it persists across restarts
        print(f"Synced slash commands for {self.user}")

    async def on_ready(self):
        print(f'{self.user} has connected successfully.')
        
        # Check if the message was sent already
        if not os.path.exists('message_sent.txt'):
            try:
                # Send the embedded message with buttons when the bot starts (only if not sent before)
                CHANNEL_ID = int(config["channel_id"])
                channel = self.get_channel(CHANNEL_ID) # Replace with channel ID where the bot will be in
                if channel:
                    embed = discord.Embed(
                        title="Verify Your Purchase",
                        description="Please select the platform you purchased from."
                    )
                    await channel.send(embed=embed, view=PlatformSelectView())
                # Write to the file to indicate the message has been sent
                with open('message_sent.txt', 'w') as f:
                    f.write('Message has been sent.')
            except Exception as e:
                print("Please set correct channel ID")

# Persistent View with buttons for platform selection
class PlatformSelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)  # Ensure the view does not timeout

    @discord.ui.button(label="Gumroad", style=discord.ButtonStyle.primary, custom_id="gumroad_button")
    async def gumroad_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(EmailInputModal(platform="gumroad"))

    @discord.ui.button(label="Jinxxy", style=discord.ButtonStyle.primary, custom_id="jinxxy_button")
    async def jinxxy_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(EmailInputModal(platform="jinxxy"))

# Create a modal to get the email input
class EmailInputModal(discord.ui.Modal, title="Enter your email"):
    email = discord.ui.TextInput(
        label="Email",
        placeholder="Enter the email used for the purchase",
        required=True
    )

    def __init__(self, platform: str):
        super().__init__()
        self.platform = platform

    async def on_submit(self, interaction: discord.Interaction):
        email = self.email.value
        await verify_purchase(interaction, self.platform, email)

# Function to verify the purchase and assign roles
async def verify_purchase(interaction: discord.Interaction, platform: str, email: str):
    if platform not in bot.verifiers:
        await interaction.response.send_message(
            f"Sorry, {platform} is not supported.", ephemeral=True
        )
        return

    verifier = bot.verifiers[platform]
    
    # Defer the interaction to keep it alive while processing
    await interaction.response.defer(ephemeral=True)
    
    try:
        verified, purchased_products, discord_usernames = await verifier(email)
        print(verified, purchased_products, discord_usernames)
        if not verified:
            await interaction.followup.send(
                "Sorry, I couldn't verify your purchase. Please check your email and try again.",
                ephemeral=True,
            )
            return

        roles_assigned = []
        roles_not_assigned = []

        # Assign product-specific roles
        for product_id, discord_username in itertools.zip_longest(purchased_products, discord_usernames):

            role_id = config["platforms"][platform]['product_roles'].get(product_id)
            
            if not role_id:
                continue
            
            role = discord.utils.get(interaction.guild.roles, id=int(role_id))
            
            if not role:
                continue
            
            if discord_username and interaction.user.name.lower() == discord_username.lower():
                await interaction.user.add_roles(role)
                roles_assigned.append(role.name)
            else:
                roles_not_assigned.append(role.name)

        if roles_assigned:
            verified_role_id = int(config["verified_role_id"])  # The role ID for verified users
            verified_role = discord.utils.get(interaction.guild.roles, id=verified_role_id)
            # Assign the "verified" role
            if verified_role:   
                await interaction.user.add_roles(verified_role)
                roles_assigned.append(verified_role.name)
            else:
                # Please check config.json and make sure verified_role_id is set correctly
                await interaction.followup.send(
                f"There was an error assigning Supporter Role. Please open a ticket",
                ephemeral=True
                )
            await interaction.followup.send(
                f"Your {platform} purchase has been verified! You've been given the following roles: {', '.join(roles_assigned)}.",
                ephemeral=True
            )
        elif roles_not_assigned:
            await interaction.followup.send(
                f"Discord username does not match with username given at checkout for: {', '.join(roles_not_assigned)}. Please open a ticket.", 
                ephemeral=True
            )
        else:
            # Possible wrong configuration. Check roles IDs in config.json
            await interaction.followup.send(
                f"Your {platform} purchase has been verified, but no roles were assigned. Please open a ticket.",
                ephemeral=True
            )

    except Exception as e:
        await interaction.followup.send(
            "Sorry, there was an error during verification. Please open a ticket.",
            ephemeral=True,
        )

# Instantiate and run the bot
bot = MyBot()

bot.run(config['discord_token'])