from abc import ABC, abstractmethod
from typing import List, Optional, Tuple
from datetime import datetime
from .models import Transaction, Account


class FinancialProvider(ABC):
    @abstractmethod
    async def get_accounts(self) -> Tuple[List[Account], List[str]]:
        """Fetch balances. Returns (accounts, error_messages)."""
        pass

    @abstractmethod
    async def get_transactions(
        self, start_date: Optional[datetime] = None, days: int = 30
    ) -> Tuple[List[Transaction], List[str]]:
        """Fetch transactions. Returns (transactions, error_messages)."""
        pass
