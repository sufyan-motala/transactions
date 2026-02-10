from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional


@dataclass
class Account:
    id: str
    org_name: str
    name: str
    currency: str
    balance: Decimal

    @classmethod
    def from_dict(cls, data: dict) -> "Account":
        """Factory to safely parse API data into an Account."""
        balance_raw = data.get("balance", "0")
        # Handle string "1,200.50" -> Decimal("1200.50")
        if isinstance(balance_raw, str):
            balance_raw = balance_raw.replace(",", "")

        return cls(
            id=str(data.get("id")),
            org_name=data.get("org", {}).get("name", "Unknown Bank"),
            name=str(data.get("name", "Unknown Account")),
            currency=str(data.get("currency", "USD")),
            balance=Decimal(balance_raw),
        )


@dataclass
class Transaction:
    id: str
    date: datetime
    amount: Decimal
    payee: str
    account_id: str
    account_name: str
    org_name: str
    description: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict, account: dict) -> "Transaction":
        """
        Factory to safely parse API data into a Transaction.
        Requires the parent account dict to fill in context.
        """
        # Parse Timestamp
        posted = data.get("posted")
        if isinstance(posted, (int, float, str)):
            date_obj = datetime.fromtimestamp(int(posted))
        else:
            date_obj = datetime.now()  # Fallback

        # Parse Amount
        amount_raw = data.get("amount", "0")
        if isinstance(amount_raw, str):
            amount_raw = amount_raw.replace(",", "")

        org_name = account.get("org", {}).get("name", "Unknown Bank")
        acc_name = account.get("name", "Unknown Account")

        return cls(
            id=str(data.get("id")),
            date=date_obj,
            amount=Decimal(amount_raw),
            payee=str(data.get("payee") or data.get("description") or "Unknown"),
            description=data.get("description"),
            account_id=str(account.get("id")),
            account_name=acc_name,
            org_name=org_name,
        )
