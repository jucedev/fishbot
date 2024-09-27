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

@bot.tree.command(
    name="verifysale",
    description="Verify a purchase and assign roles",
)
@app_commands.describe(
    platform="The platform you purchased from",
    email="The email address used for the purchase"
)
@app_commands.choices(platform=[
    app_commands.Choice(name="Gumroad", value="gumroad"),
    app_commands.Choice(name="Jinxxy", value="jinxxy"),
    # other platforms here
])
async def verifysale(interaction: discord.Interaction, platform: str, email: str):
    platform = platform.lower()
    
    if platform not in bot.verifiers:
        await interaction.response.send_message(f"Sorry, {platform} is not supported.", ephemeral=True)
        return

    if not email:
        await interaction.response.send_message("Please provide an email address.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)

    verifier = bot.verifiers[platform]
    verified, purchased_products = await verifier(email)

    if verified:
        roles_assigned = []
        
        # Assign overall verified role
        verified_role = discord.utils.get(interaction.guild.roles, id=config['verified_role_id'])
        if verified_role:
            await interaction.user.add_roles(verified_role)
            roles_assigned.append(verified_role.name)
        
        # Assign product-specific roles
        for product_id in purchased_products:
            role_id = config["platforms"][platform]['product_roles'].get(product_id)
            if role_id:
                role = discord.utils.get(interaction.guild.roles, id=role_id)
                if role:
                    await interaction.user.add_roles(role)
                    roles_assigned.append(role.name)
        
        if roles_assigned:
            await interaction.followup.send(f"Sale verified! You've been given the following roles: {', '.join(roles_assigned)}.", ephemeral=True)
        else:
            await interaction.followup.send("Sale verified! However, I couldn't assign any roles. Please contact an admin.", ephemeral=True)
    else:
        await interaction.followup.send("Sorry, I couldn't verify your sale. Please check your email and try again.", ephemeral=True)

bot.run(config['discord_token'])