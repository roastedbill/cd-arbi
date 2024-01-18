import time

from uniswap import Uniswap
from web3 import Web3
import requests
from datetime import datetime

address = ""
private_key = ""
version = 3
provider = "https://rpc.arb1.arbitrum.gateway.fm"
uniswap = Uniswap(address=address, private_key=private_key, version=version, provider=provider)

# Some token addresses we'll be using later in this guide
link = "0xf97f4df75117a78c1A5a0DBb814Af92458539FB4"
usdc = "0xaf88d065e77c8cC2239327C5EDb3A432268e5831"

w3 = Web3(Web3.HTTPProvider(provider))


# 1. get price
def get_link_price_for_amount(amount):
    # set exact out
    link_price = uniswap.get_price_input(link, usdc, amount)
    print("cost {:f} usdc for {:f} link".format(link_price/10**6, amount/10**18))

# 2. Txn cost est
#   2.1 - fee is included
#   2.2 - slippage is included
#   2.3 - unpredictable but can set limit
#   def make_trade(
#         self,
#         input_token: AddressLike,
#         output_token: AddressLike,
#         qty: Union[int, Wei],
#         recipient: Optional[AddressLike] = None,
#         fee: Optional[int] = None,
#         slippage: Optional[float] = None,
#         fee_on_transfer: bool = False,
#     )
#   2.4 - current gas limit
# Get the current gas limit and gas price
def get_gas_info():
    gas_price = w3.eth.gas_price
    print("gas_price {:d}wei".format(gas_price))


#   2.5 - pool details (TBD)
def get_pool_info():
    pool = uniswap.get_pool_instance(link, usdc)
    print("pool {:s}".format(pool.address.lower()))
    return pool


# 3 - trading history is only available through event, fetch from subgraph
def get_trading_history(pool_address, after_timestamp, skip, limit, order):
    subgraph_endpoint = "https://api.thegraph.com/subgraphs/name/ianlapham/arbitrum-minimal"

    graphql_query = """
    {{
    swaps( skip: {skip}, first: {limit}, orderBy: timestamp, orderDirection: {order}, where:
     {{ timestamp_gt: {after_ts}, pool: "{pool}" }}
    ) {{
      sender
      recipient
      amount0
      amount1
      timestamp
     }}
    }}
    """

    variables = {'after_ts': after_timestamp, 'skip': skip, 'limit': limit, 'pool': pool_address, 'order': order}
    graphql_query = graphql_query.format(**variables)
    response = requests.post(subgraph_endpoint, json={'query': graphql_query})

    # Check the status code
    data = {}
    if response.status_code == 200:
        # Parse and print the response JSON
        data = response.json()
        for swap in data['data']['swaps']:
            amount_usdc = float(swap['amount0'])
            amount_link = float(swap['amount1'])
            # Convert the timestamp to a datetime object
            dt_object = datetime.fromtimestamp(int(swap['timestamp']))

            # Format the datetime object into a readable string
            formatted_string = dt_object.strftime("%Y-%m-%d %H:%M:%S")
            if amount_usdc > 0:
                print("{} | {} buy {:f} usdc with {:f} link at {:f}".format(formatted_string, swap['sender'], amount_usdc, amount_link*-1, amount_usdc*-1/amount_link))
            else:
                print("{} | {} buy {:f} link with {:f} usdc at {:f}".format(formatted_string, swap['sender'], amount_link, amount_usdc*-1, amount_usdc*-1/amount_link))
    else:
        print(f"Error: {response.status_code} - {response.text}")

    return data


if __name__ == '__main__':
    get_link_price_for_amount(10**18)

    get_gas_info()

    pool = get_pool_info()

    # Parse the date string and convert it to a timestamp
    timestamp = int(datetime.strptime("2024-01-17", "%Y-%m-%d").timestamp())

    print("<--- Historical Transactions Here --->")
    while True:
        time.sleep(10)
        index = 0
        batch_size = 100
        data = get_trading_history(pool.address.lower(), timestamp, index, batch_size, "asc")
        if len(data['data']['swaps']) > 0:
            timestamp = data['data']['swaps'][-1]['timestamp']
        # if len(data['data']['swaps']) < batch_size:
        #     break


