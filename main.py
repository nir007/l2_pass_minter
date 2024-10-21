import os
import json
import asyncio
from dotenv import load_dotenv
from unicodedata import numeric

from client import Client
from web3.exceptions import Web3RPCError

async def main():
    load_dotenv()

    with open("chains.json") as file:
        chains: {} = json.load(file)

    is_valid_chain = False
    chain_name = ""

    while not is_valid_chain:
        chain_name = input(f"Enter one of chain names\n{chains.keys()}: ")

        is_valid_chain = chain_name in chains.keys()

    is_valid_count = False
    count: int = 0
    while not is_valid_count:
        count_str = input(f"Enter count nfts to mint: ")

        is_valid_count = numeric(count_str) and int(count_str) > 0
        count = int(count_str) if is_valid_count else 0

    cl = Client(
        proxy=os.getenv("PROXY"),
        private_key=os.getenv("PRIVATE"),
        chain=chains.get(chain_name)
    )

    await cl.mint_nft(count=count)

try:
    asyncio.run(main())
except Web3RPCError as e:
    print(f"RPC error: {e}")
except FileNotFoundError as e:
    print(f"File with chains is not found: {e}")
except Exception as e:
    print(f"Something went wrong: {e}")