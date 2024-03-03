import asyncio
import aiohttp
import json
from datetime import datetime, timedelta
import os

class NBPCurrencyRateRetriever:
    """startDate, endDate format YYYY-MM-DD"""

    def __init__(self, startDate: str, endDate: str, currency_codes={"EUR", "USD"}) -> None:
        self.currency_codes = currency_codes
        self.startDate = startDate
        self.endDate = endDate
        self.output_folder = 'exchange_rates'

    async def fetch_exchange_rates(self, session, table="c"):
        if self.startDate == self.endDate:
            url = f"https://api.nbp.pl/api/exchangerates/tables/{table}/{self.startDate}?format=json"
        else:
            url = f"http://api.nbp.pl/api/exchangerates/tables/{table}/{self.startDate}/{self.endDate}/?format=json"

        try:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    return None
        except aiohttp.ClientConnectorError as err:
            print(f"Connection error when asking NBP API for currency rates: {str(err)}")

    async def retrieve_exchange_rates(self):
        async with aiohttp.ClientSession() as session:
            result = await self.fetch_exchange_rates(session, table="c")
            return result

    def run(self):
        results = asyncio.run(self.retrieve_exchange_rates())
        output = self.pretty_output(results)
        self.save_to_json(output)  # Zapisuje dane do pliku JSON
        return output

    def pretty_output(self, nbp_data) -> str:
        if nbp_data is None:
            return "No data available"

        merged_results = {result["effectiveDate"]: result["rates"] for result in nbp_data}

        exchange_rates = []
        for day, rate_data in merged_results.items():
            if rate_data is None:
                exchange_rates.append({day: "No exchange rates available"})
            else:
                selected_currencies = list(
                    filter(lambda x: x["code"] in self.currency_codes, rate_data)
                )
                reformatted = {
                    curr["code"]: {"sale": curr["ask"], "purchase": curr["bid"]}
                    for curr in selected_currencies
                }
                exchange_rates.append({day: reformatted})

        return json.dumps(exchange_rates, indent=4)

    def save_to_json(self, data):
        if not os.path.exists(self.output_folder):
            os.makedirs(self.output_folder)
        output_file_path = os.path.join(self.output_folder, 'exchange_rates.json')
        with open(output_file_path, 'w') as file:
            file.write(data)
        print(f"Exchange rates saved to {output_file_path}")

if __name__ == "__main__":
    startDate = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")
    endDate = datetime.now().strftime("%Y-%m-%d")
    currency_codes = {"EUR", "USD"}

    retriever = NBPCurrencyRateRetriever(startDate=startDate, endDate=endDate, currency_codes=currency_codes)
    output = retriever.run()

    print(output)
