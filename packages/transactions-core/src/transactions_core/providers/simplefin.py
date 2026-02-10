import base64
import httpx
import json
from typing import List, Optional, Tuple
from datetime import datetime, timedelta
from ..interfaces import FinancialProvider
from ..models import Transaction, Account


class SimpleFinProvider(FinancialProvider):
    def __init__(self, access_url: str, client: Optional[httpx.AsyncClient] = None):
        self.access_url = access_url
        # Allow injecting a client (good for web apps to reuse connections)
        # If no client provided, manage our own.
        self._internal_client = client is None
        self.client = client or httpx.AsyncClient(
            timeout=30.0, headers={"User-Agent": "Transactions-Core/0.1.0"}
        )

    async def close(self):
        if self._internal_client:
            await self.client.aclose()

    @staticmethod
    def claim_token(setup_token: str) -> str:
        if setup_token.startswith("sfin:"):
            setup_token = setup_token.replace("sfin:", "")

        try:
            claim_url = base64.b64decode(setup_token).decode("utf-8").strip()
        except Exception as e:
            raise ValueError("Invalid token format") from e

        # This is a sync call usually done once during setup, so standard Client is fine
        with httpx.Client() as client:
            try:
                resp = client.post(claim_url)
                resp.raise_for_status()
                return resp.text.strip()
            except httpx.HTTPError as e:
                raise ValueError(f"Failed to claim token: {e}")

    async def _fetch_data(
        self, start_date_ts: int = 0
    ) -> Tuple[Optional[dict], List[str]]:
        """
        Fetch raw data safely.
        Returns (json_data, list_of_error_strings).
        """
        try:
            resp = await self.client.get(
                f"{self.access_url}/accounts", params={"start-date": start_date_ts}
            )
            resp.raise_for_status()
            return resp.json(), []
        except httpx.HTTPError as e:
            return None, [f"Network Error: {str(e)}"]
        except json.JSONDecodeError:
            return None, ["Invalid API Response: Not JSON"]
        except Exception as e:
            return None, [f"Unexpected Error: {str(e)}"]

    async def get_accounts(self) -> Tuple[List[Account], List[str]]:
        start_ts = int(datetime.now().timestamp())

        data, errors = await self._fetch_data(start_date_ts=start_ts)

        if not data:
            return [], errors

        # Merge API-level errors with HTTP-level errors
        api_errors = data.get("errors", [])
        if isinstance(api_errors, list):
            errors.extend(api_errors)

        accounts = [Account.from_dict(acc) for acc in data.get("accounts", [])]

        return accounts, errors

    async def get_transactions(
        self, start_date: Optional[datetime] = None, days: int = 30
    ) -> Tuple[List[Transaction], List[str]]:

        if start_date is None:
            start_date = datetime.now() - timedelta(days=days)

        start_ts = int(start_date.timestamp())

        data, errors = await self._fetch_data(start_date_ts=start_ts)

        if not data:
            return [], errors

        api_errors = data.get("errors", [])
        if isinstance(api_errors, list):
            errors.extend(api_errors)

        transactions = []
        for acc in data.get("accounts", []):
            for t in acc.get("transactions", []):
                transactions.append(Transaction.from_dict(t, acc))

        transactions.sort(key=lambda x: x.date, reverse=True)
        return transactions, errors
