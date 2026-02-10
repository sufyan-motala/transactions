import asyncio
import httpx
from datetime import datetime
from sqlmodel import Session, select
from transactions_core import SimpleFinProvider
from .db import Connection, CachedAccount, CachedTransaction
from .config import settings


async def add_connection(session: Session, user_id: int, token: str):
    """Exchanges token using Core and saves encrypted URL to DB."""
    # 1. Exchange token for real URL
    raw_access_url = SimpleFinProvider.claim_token(token)

    # 2. Encrypt URL before storage
    encrypted_url = settings.encryptor.encrypt(raw_access_url)

    conn = Connection(user_id=user_id, access_url=encrypted_url)
    session.add(conn)
    session.commit()

    # 3. Trigger an immediate initial sync so the user sees data
    await sync_data(session, user_id)


async def get_dashboard_data(session: Session, user_id: int):
    """
    READ-ONLY: Fetches transactions from the local database cache.
    Returns (List[CachedTransaction], List[str] errors).
    """
    # Join Connection to filter by user_id
    statement = (
        select(CachedTransaction)
        .join(Connection)
        .where(Connection.user_id == user_id)
        .order_by(CachedTransaction.date.desc())
    )
    transactions = session.exec(statement).all()

    # Check if we have any connections that have never been synced
    connections = session.exec(
        select(Connection).where(Connection.user_id == user_id)
    ).all()
    errors = []

    # Simple check to warn if data might be stale (optional logic)
    if connections and not transactions:
        # If we have connections but no data, it's likely a sync hasn't finished yet
        pass

    return transactions, errors


async def get_accounts(session: Session, user_id: int):
    """
    READ-ONLY: Fetches accounts from the local database cache.
    """
    statement = (
        select(CachedAccount).join(Connection).where(Connection.user_id == user_id)
    )
    accounts = session.exec(statement).all()

    # Convert to dictionary format expected by template
    return [
        {
            "name": acc.name,
            "balance": acc.balance,
            "currency": acc.currency,
            "org": acc.org_name,
            "error": False,
        }
        for acc in accounts
    ]


async def sync_data(session: Session, user_id: int):
    """
    WRITE: Fetches fresh data (Txns AND Accounts), wipes old cache, inserts new.
    """
    connections = session.exec(
        select(Connection).where(Connection.user_id == user_id)
    ).all()

    all_errors = []

    if connections:
        async with httpx.AsyncClient(timeout=30.0) as client:
            tasks = []
            for conn in connections:
                real_url = settings.encryptor.decrypt(conn.access_url)
                provider = SimpleFinProvider(real_url, client=client)

                # Fetch BOTH transactions and accounts in parallel
                t_task = provider.get_transactions(days=60)
                a_task = provider.get_accounts()

                tasks.append(asyncio.gather(t_task, a_task, return_exceptions=True))

            # Wait for all connections
            results = await asyncio.gather(*tasks)

            for conn, conn_result in zip(connections, results):
                # Unpack the results (txns_res, accounts_res)
                # results is a list of lists because of the nested gather
                txns_res, accounts_res = conn_result

                # Handle Transaction Errors
                if isinstance(txns_res, Exception):
                    all_errors.append(f"Conn {conn.id} Txn Error: {str(txns_res)}")
                    txns = []
                else:
                    txns, t_errs = txns_res
                    if t_errs:
                        all_errors.extend(t_errs)

                # Handle Account Errors
                if isinstance(accounts_res, Exception):
                    all_errors.append(f"Conn {conn.id} Acct Error: {str(accounts_res)}")
                    accounts = []
                else:
                    accounts, a_errs = accounts_res
                    if a_errs:
                        all_errors.extend(a_errs)

                # --- DATABASE WIPE & REPLACE ---
                try:
                    conn.last_synced_at = datetime.now()
                    session.add(conn)

                    # 1. Wipe Old Data
                    session.exec(
                        select(CachedTransaction).where(
                            CachedTransaction.connection_id == conn.id
                        )
                    ).all()
                    for t in session.exec(
                        select(CachedTransaction).where(
                            CachedTransaction.connection_id == conn.id
                        )
                    ).all():
                        session.delete(t)

                    for a in session.exec(
                        select(CachedAccount).where(
                            CachedAccount.connection_id == conn.id
                        )
                    ).all():
                        session.delete(a)

                    # 2. Insert New Transactions
                    for t in txns:
                        session.add(
                            CachedTransaction(
                                connection_id=conn.id,
                                external_id=t.id,
                                date=t.date,
                                amount=t.amount,
                                payee=t.payee,
                                description=t.description,
                                account_name=t.account_name,
                                org_name=t.org_name,
                            )
                        )

                    # 3. Insert New Accounts
                    for a in accounts:
                        session.add(
                            CachedAccount(
                                connection_id=conn.id,
                                external_id=a.id,
                                name=a.name,
                                org_name=a.org_name,
                                currency=a.currency,
                                balance=a.balance,
                            )
                        )

                    session.commit()
                except Exception as e:
                    session.rollback()
                    all_errors.append(f"DB Error Conn {conn.id}: {str(e)}")

    return await get_dashboard_data(session, user_id)
