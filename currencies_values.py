import aiohttp
import asyncio
import json
import os
from datetime import datetime, timedelta
from aiofile import async_open
from aiopath import AsyncPath

class ExchangeRatesFetcher:
    def __init__(self):
        self.base_url = 'http://api.nbp.pl/api/exchangerates/tables/C/'
        self.output_folder = 'exchange_data'  # nazwa folderu do zapisu danych

    async def fetch_exchange_rates(self, days, currencies):
        async with aiohttp.ClientSession() as session:
            tasks = [self.fetch_exchange_rates_for_day(session, days - i, currencies) for i in range(days)]
            return await asyncio.gather(*tasks)

    async def fetch_exchange_rates_for_day(self, session, days_ago, currencies):
        date = datetime.now() - timedelta(days=days_ago)
        url = f"{self.base_url}{date.strftime('%Y-%m-%d')}/"
        try:
            async with session.get(url) as response:
                data = await response.json()
                return {date.strftime('%d.%m.%Y'): self.extract_currency_info(data, currencies)}
        except aiohttp.ClientError as e:
            print(f"Error fetching data for {date.strftime('%d.%m.%Y')}: {e}")
            return {}

    def extract_currency_info(self, data, currencies):
        currency_info = {}
        for item in data[0]['rates']:
            if item['code'] in currencies:
                currency_info[item['code']] = {'sale': item['ask'], 'purchase': item['bid']}
        return currency_info

    def save_to_json(self, data):
        if not os.path.exists(self.output_folder):  # sprawdź, czy folder istnieje
            os.makedirs(self.output_folder)  # jeśli nie, utwórz go
        output_file_path = os.path.join(self.output_folder, 'exchange_rates.json')
        with open(output_file_path, 'w') as file:
            json.dump(data, file, indent=2)
        print(f"Exchange rates saved to {output_file_path}")

async def main():
    # Pytamy użytkownika o ilość dni i wybrane waluty
    days = int(input("Ile dni? "))
    currencies = input("Jakie waluty? (oddzielone spacją) ").split()

    exchange_fetcher = ExchangeRatesFetcher()
    exchange_rates = await exchange_fetcher.fetch_exchange_rates(days, currencies)
    exchange_fetcher.save_to_json(exchange_rates)
    print(exchange_rates)

if __name__ == "__main__":
    asyncio.run(main())
