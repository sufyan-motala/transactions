from typing import Optional
from datetime import datetime
from decimal import Decimal
from sqlmodel import SQLModel, Field, create_engine, Session, Relationship
from sqlalchemy import Column, Numeric
from .config import settings


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    hashed_password: str
    connections: list["Connection"] = Relationship(back_populates="user")


class Connection(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    access_url: str
    name: str = "Bank Connection"
    last_synced_at: Optional[datetime] = Field(default=None)

    user: Optional[User] = Relationship(back_populates="connections")
    accounts: list["CachedAccount"] = Relationship(
        back_populates="connection", sa_relationship_kwargs={"cascade": "all, delete"}
    )
    transactions: list["CachedTransaction"] = Relationship(
        back_populates="connection", sa_relationship_kwargs={"cascade": "all, delete"}
    )


class CachedAccount(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    connection_id: int = Field(foreign_key="connection.id", index=True)
    external_id: str
    name: str
    org_name: str
    currency: str
    # Use Numeric for precision, though SQLite treats as Real/Text
    balance: Decimal = Field(default=0, sa_column=Column(Numeric(20, 2)))

    connection: Optional[Connection] = Relationship(back_populates="accounts")


class CachedTransaction(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    connection_id: int = Field(foreign_key="connection.id", index=True)
    external_id: str
    date: datetime
    # Use Numeric for precision
    amount: Decimal = Field(default=0, sa_column=Column(Numeric(20, 2)))
    payee: str
    description: Optional[str] = None
    account_name: str
    org_name: str

    connection: Optional[Connection] = Relationship(back_populates="transactions")


engine = create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False})


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
