import stripe
import config

stripe.api_key = config.TOKEN  # assuming token is stripe api key

async def convert_price(amount: float, target_currency: str) -> float:
    try:
        rate = stripe.ExchangeRate.retrieve(target_currency.lower())
        return amount * float(rate['rates'][config.CURRENCY.value.lower()])
    except Exception:
        return amount
