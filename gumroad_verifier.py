import aiohttp
from typing import Tuple, Set

from config import load_config

config = load_config()

async def verify_gumroad_sale(email: str) -> Tuple[bool, Set[str]]:
    url = "https://api.gumroad.com/v2/sales"
    headers = {"Authorization": f"Bearer {config["platforms"]["gumroad"]["api_key"]}"}
    params = {"email": email}

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, params=params) as response:
            if response.status == 200:
                data = await response.json()
                sales = data.get('sales', [])
                if sales:
                    purchased_products = set(sale['product_id'] for sale in sales)
                    return True, purchased_products
                return False, set()
            else:
                print(f"Error: {response.status}")
                return False, set()