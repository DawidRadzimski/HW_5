import aiohttp
import asyncio
import json
import os
import logging
import names
import websockets
from datetime import datetime, timedelta
from aiofile import async_open
from aiopath import AsyncPath
from websockets import WebSocketServerProtocol
from websockets.exceptions import ConnectionClosedOK

logging.basicConfig(level=logging.INFO)

class ExchangeRatesFetcher:
    def __init__(self):
        self.base_url = 'http://api.nbp.pl/api/exchangerates/tables/C/'

    async def fetch_exchange_rates(self, days):
        async with aiohttp.ClientSession() as session:
            tasks = [self.fetch_exchange_rates_for_day(session, days - i) for i in range(days)]
            return await asyncio.gather(*tasks)

    async def fetch_exchange_rates_for_day(self, session, days_ago):
        date = datetime.now() - timedelta(days=days_ago)
        url = f"{self.base_url}{date.strftime('%Y-%m-%d')}/"
        try:
            async with session.get(url) as response:
                data = await response.json()
                return {date.strftime('%d.%m.%Y'): self.extract_currency_info(data)}
        except aiohttp.ClientError as e:
            logging.error(f"Error fetching data for {date.strftime('%d.%m.%Y')}: {e}")
            return {}

    def extract_currency_info(self, data):
        currencies = {}
        for item in data[0]['rates']:
            if item['code'] in ['EUR', 'USD']:
                currencies[item['code']] = {'sale': item['ask'], 'purchase': item['bid']}
        return currencies

    def format_exchange_rate(self, exchange_rate):
        return f"EUR: {exchange_rate['EUR']['sale']} / {exchange_rate['EUR']['purchase']}, USD: {exchange_rate['USD']['sale']} / {exchange_rate['USD']['purchase']}"

class Server:
    def __init__(self):
        self.clients = set()
        self.exchange_fetcher = ExchangeRatesFetcher()

    async def register(self, ws: WebSocketServerProtocol):
        ws.name = names.get_full_name()
        self.clients.add(ws)
        logging.info(f'{ws.remote_address} connects')

    async def unregister(self, ws: WebSocketServerProtocol):
        self.clients.remove(ws)
        logging.info(f'{ws.remote_address} disconnects')

    async def send_to_clients(self, message: str):
        if self.clients:
            [await client.send(message) for client in self.clients]

    async def handle_command(self, ws: WebSocketServerProtocol, command: str):
        if command.startswith("exchange"):
            params = command.split(" ")
            if len(params) == 1:
                exchange_rate = await self.exchange_fetcher.fetch_exchange_rates(1)
                await self.send_to_clients(f"Current exchange rate: {self.exchange_fetcher.format_exchange_rate(exchange_rate[0])}")
            elif len(params) == 2 and params[1].isdigit():
                days = int(params[1])
                exchange_rates = await self.exchange_fetcher.fetch_exchange_rates(days)
                for date, rate in exchange_rates.items():
                    await self.send_to_clients(f"Exchange rate for {date}: {self.exchange_fetcher.format_exchange_rate(rate)}")

    async def ws_handler(self, ws: WebSocketServerProtocol):
        await self.register(ws)
        try:
            async for message in ws:
                await self.handle_command(ws, message)
        except ConnectionClosedOK:
            pass
        finally:
            await self.unregister(ws)

async def main():
    server = Server()
    async with websockets.serve(server.ws_handler, 'localhost', 8080):
        await asyncio.Future()  # run forever

if __name__ == '__main__':
    asyncio.run(main())