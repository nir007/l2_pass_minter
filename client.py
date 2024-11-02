import json
import asyncio
from web3 import AsyncWeb3, AsyncHTTPProvider
from web3.types import TxParams, Wei, HexBytes, HexStr, ChecksumAddress
from web3.exceptions import TransactionNotFound
from web3.contract import AsyncContract
from typing import cast

class Client:
    w3: AsyncWeb3
    __l2_pass_contact = "0x0000049F63Ef0D60aBE49fdD8BEbfa5a68822222"

    def __init__(self, *, private_key, proxy: str, chain: {}):
        self.private_key = private_key
        self.chain = chain

        request_kwargs = {
            "proxy": f"http://{proxy}"
        } if proxy else {}

        self.__load_abi()
        self.w3 = AsyncWeb3(AsyncHTTPProvider(chain.get("rpc_url"), request_kwargs=request_kwargs))

        self.address_from = self.w3.to_checksum_address(
            self.w3.eth.account.from_key(self.private_key).address
        )

    def __load_abi(self):
        with open("l2_pass_abi.json") as file:
            self.abi = json.load(file)

    def to_wei(self, *, amount: float, decimals: int):
        unit_name = {
            6: "mwei",
            9: "gwei",
            18: "ether",
        }.get(decimals)

        if not unit_name:
            raise RuntimeError(f"Can`t find unit for decimals: {decimals}")

        return self.w3.to_wei(amount, unit_name)

    async def __send(self, transaction: any) -> HexBytes:
        signed_tx = self.w3.eth.account.sign_transaction(transaction, self.private_key)
        return await self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)

    async def get_trx_params(self, *, value: Wei) -> TxParams:
        base_fee = await self.w3.eth.gas_price
        max_priority_fee_per_gas = await self.w3.eth.max_priority_fee
        max_fee_per_gas = int(base_fee + max_priority_fee_per_gas)

        trx: TxParams = {
            "from": self.address_from,
            "chainId": await self.w3.eth.chain_id,
            "nonce": await self.w3.eth.get_transaction_count(self.address_from),
            "maxPriorityFeePerGas": max_priority_fee_per_gas,
            "maxFeePerGas": cast(Wei, max_fee_per_gas),
            "type": HexStr("0x2"),
            "value": value
        }

        return trx

    async def mint_nft(self, count: int = 1) -> HexBytes | None:
        if count == 0:
            return None

        contract: AsyncContract = self.w3.eth.contract(
            address=self.w3.to_checksum_address(self.__l2_pass_contact),
            abi=self.abi
        )

        nft_cost: Wei = await contract.functions.mintPrice().call()
        print(f"Mint one nft price is: {int(nft_cost) / (10 ** 18):.5f} ETH")
        print(f"Total mint price is: {(int(nft_cost) / (10 ** 18)) * count:.5f} ETH")

        transaction = await contract.functions.mint(count).build_transaction(
            await self.get_trx_params(value=Wei(nft_cost * count))
        )

        hex_bytes = await self.__send(transaction)

        print(f"Transaction: {hex_bytes.hex()}")

        await self.__wait_tx(hex_bytes)

    async def __wait_tx(self, hex_bytes: HexBytes):
        total_time = 0
        timeout = 100
        poll_latency = 10
        tx_hash: str = hex_bytes.hex()

        while True:
            try:
                receipts = await self.w3.eth.get_transaction_receipt(HexStr(tx_hash))
                status = receipts.get("status")
                if status == 1:
                    print(f"Transaction was successful: {self.chain.get('explorer_url')}tx/0x{tx_hash}")
                    return True
                elif status is None:
                    await asyncio.sleep(poll_latency)
                else:
                    print(f"Transaction failed: {self.chain.get('explorer_url')}tx/0x{tx_hash}")
                    return False
            except TransactionNotFound:
                if total_time > timeout:
                    print(f"Transaction isn`t in the chain after {timeout} seconds")
                    return False
                total_time += poll_latency
                await asyncio.sleep(poll_latency)
