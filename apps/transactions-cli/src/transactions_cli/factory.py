from transactions_core import FinancialProvider, SimpleFinProvider
from . import config


def get_provider() -> FinancialProvider:
    """
    Reads config and returns the correct initialized Provider.
    Raises ValueError if config is missing or invalid.
    """
    conf = config.get_config()
    provider_name = conf.get("provider")
    payload = conf.get("payload", {})

    if not provider_name:
        raise ValueError("No provider configured. Run 'finance setup' first.")

    if provider_name == "simplefin":
        url = payload.get("access_url")
        if not url:
            raise ValueError("SimpleFin configuration is missing 'access_url'.")
        return SimpleFinProvider(access_url=url)

    # FUTURE: Add Plaid here
    # elif provider_name == "plaid":
    #     return PlaidProvider(client_id=..., secret=...)

    raise ValueError(f"Unknown provider type: {provider_name}")
