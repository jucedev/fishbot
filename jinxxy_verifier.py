import aiohttp
from typing import Tuple, List

from config import load_config

config = load_config()

async def verify_jinxxy_sale(email: str) -> Tuple[bool, List[str]]:
    url = "https://api.creators.jinxxy.com/v1/orders"
    headers = {"X-Api-Key": config['platforms']['jinxxy']['api_key']}
    params = {"search_query": email}

    purchased_products = []

    async with aiohttp.ClientSession() as session:
        # Get all orders for the user
        async with session.get(url, headers=headers, params=params) as response:
            if response.status == 200:
                data = await response.json()
                orders = data.get("results", [])
                if not orders:
                    return False, []

                # Fetch each order by its ID
                for order in orders:
                    order_id = order['id']
                    order_url = f"{url}/{order_id}"

                    async with session.get(order_url, headers=headers) as order_response:
                        if order_response.status == 200:
                            order_data = await order_response.json()

                            # Extract product names from order items
                            for item in order_data.get("order_items", []):
                                if item.get("target_type") == "DIGITAL_PRODUCT":
                                    purchased_products.append(item["target_id"])
                        else:
                            print(f"Failed to retrieve order {order_id}: {order_response.status}")

                return True, purchased_products
            elif response.status == 401:
                print("Unauthorized: Check your API key")
                return False, []
            else:
                print(f"Failed to retrieve orders: {response.status}")
                return False, []