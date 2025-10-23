from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs, OrderType
from py_clob_client.order_builder.constants import BUY

def create_and_post_order(
    private_key: str,
    proxy_address: str,
    token_id: str,
    price: float,
    size: float,
    side: str
):
    client = ClobClient(
        "https://clob.polymarket.com",
        key=private_key,
        chain_id=137,
        signature_type=1,
        funder=proxy_address
    )

    # Ensure API credentials are set or derived
    client.set_api_creds(client.create_or_derive_api_creds())

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

    return response
