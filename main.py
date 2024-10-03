import discord
from discord import app_commands
from discord.ext import commands
from typing import Dict, Callable, Tuple, Set

from config import load_config
from gumroad_verifier import verify_gumroad_sale
from jinxxy_verifier import verify_jinxxy_sale

config = load_config()

intents = discord.Intents.default()
intents.message_content = True

VerifierFunction = Callable[[str, Dict[str, int]], Tuple[bool, Set[str]]]

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='/', intents=intents)
        self.verifiers: Dict[str, VerifierFunction] = {
            "gumroad": verify_gumroad_sale,
            "jinxxy": verify_jinxxy_sale,
            # other platform verifiers here
        }

    async def setup_hook(self):
        await self.tree.sync()
        print(f"Synced slash commands for {self.user}")

bot = MyBot()

@bot.event
async def on_ready():
    print(f'{bot.user} has connected successfully.')

# Button view for selecting a platform
class PlatformSelectView(discord.ui.View):
    def __init__(self, email: str):
        super().__init__()
        self.email = email

    @discord.ui.button(label="Gumroad", style=discord.ButtonStyle.primary)
    async def gumroad_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.verify_sale(interaction, "gumroad")

    @discord.ui.button(label="Jinxxy", style=discord.ButtonStyle.primary)
    async def jinxxy_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.verify_sale(interaction, "jinxxy")

    async def verify_sale(self, interaction: discord.Interaction, platform: str):
        email = self.email

        if platform not in bot.verifiers:
            await interaction.response.send_message(
                f"Sorry, {platform} is not supported.", ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        verifier = bot.verifiers[platform]
        try:
            verified, purchased_products, discord_usernames = await verifier(email)

            if not verified:
                await interaction.followup.send(
                    "Sorry, I couldn't verify your purchase. Please check your email and try again.",
                    ephemeral=True,
                )
                return

            roles_assigned = []

            # Assign Supporter Role
            verified_role_id = int(config["verified_role_id"])
            verified_role = discord.utils.get(interaction.guild.roles, id=verified_role_id)
            if verified_role:
                await interaction.user.add_roles(verified_role)
                roles_assigned.append(verified_role.name)

            # Assign avatar-specific roles
            for product_id, discord_username in zip(purchased_products, discord_usernames):
                role_id = config["platforms"][platform]['product_roles'].get(product_id)
                if not role_id:
                    continue

                role = discord.utils.get(interaction.guild.roles, id=int(role_id))
                if not role:
                    continue
                if interaction.user.name.lower() == discord_username.lower():
                    await interaction.user.add_roles(role)
                    roles_assigned.append(role.name)
                else:
                    await interaction.followup.send(f"Discord username does not match the checkout username for: {role}. Contact an Admin.", ephemeral=True)

            if roles_assigned:
                await interaction.followup.send(f"Purchase verified! You've been assigned the following roles: {', '.join(roles_assigned)}.", ephemeral=True)
            else:
                await interaction.followup.send("Purchase verified! However, no roles were assigned. Please contact an admin.", ephemeral=True)
        
        except Exception as e:
            await interaction.followup.send(
                "Sorry, I couldn't verify your purchase. Please contact an admin.",
                ephemeral=True,
            )

# Modal form for the email input
class EmailInputModal(discord.ui.Modal, title="Verify Your Purchase"):
    email = discord.ui.TextInput(
        label="Email",
        placeholder="Enter the email used for the purchase",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        # After getting the email, present the platform buttons
        await interaction.response.send_message(
            "Select the platform where you made your purchase:",
            view=PlatformSelectView(self.email.value),
            ephemeral=True
        )

@bot.tree.command(
    name="verifypurchase",
    description="Open a form to verify your purchase"
)
async def verifysale(interaction: discord.Interaction):
    await interaction.response.send_modal(EmailInputModal())

bot.run(config['discord_token'])