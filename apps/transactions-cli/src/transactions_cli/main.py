import asyncio
import typer
import orjson
from rich.console import Console
from rich.table import Table
from rich import print as rprint
from dataclasses import asdict

from transactions_core import SimpleFinProvider

from . import config, factory

app = typer.Typer(help="Financial Transactions CLI")
console = Console()


async def _fetch_data(action: str, **kwargs):
    """Generic helper to run provider actions."""
    try:
        provider = factory.get_provider()
    except ValueError as e:
        rprint(f"[bold red]Configuration Error:[/bold red] {e}")
        raise typer.Exit(1)

    try:
        if action == "transactions":
            return await provider.get_transactions(**kwargs)
        elif action == "accounts":
            return await provider.get_accounts()
    finally:
        # If the provider has a close method (like httpx client), ensure it's called
        if hasattr(provider, "close"):
            await provider.close()


# --- Commands ---


@app.command()
def setup(
    provider: str = typer.Argument(
        "simplefin", help="The provider to use (e.g., simplefin)"
    ),
    token: str = typer.Option(..., "--token", "-t", help="Setup token or API key"),
):
    """Configure a new financial provider."""

    try:
        if provider == "simplefin":
            with console.status("[green]Exchanging token with SimpleFin..."):
                # SimpleFin specific setup logic
                access_url = SimpleFinProvider.claim_token(token)

            config.save_config("simplefin", {"access_url": access_url})
            rprint("[bold green]Success![/bold green] SimpleFin configured.")

        else:
            rprint(f"[red]Provider '{provider}' is not supported yet.[/red]")
            raise typer.Exit(1)

    except Exception as e:
        rprint(f"[bold red]Setup Failed:[/bold red] {e}")
        raise typer.Exit(1)


@app.command()
def accounts(json_out: bool = typer.Option(False, "--json")):
    """List connected accounts."""
    data, errors = asyncio.run(_fetch_data("accounts"))

    if json_out:
        output = {"accounts": [asdict(a) for a in data], "errors": errors}
        print(orjson.dumps(output).decode())
        return

    if errors:
        rprint(f"[red]Errors: {errors}[/red]")

    table = Table(title="Accounts")
    table.add_column("Bank", style="blue")
    table.add_column("Name", style="white")
    table.add_column("Balance", justify="right", style="green")

    for acc in data:
        table.add_row(acc.org_name, acc.name, f"${acc.balance:,.2f}")
    console.print(table)


@app.command()
def view(
    days: int = typer.Option(30, "--days", "-d"),
    json_out: bool = typer.Option(False, "--json"),
):
    """View transactions."""
    data, errors = asyncio.run(_fetch_data("transactions", days=days))

    if json_out:
        # Convert data for JSON (dates/decimals need casting)
        clean_data = []
        for t in data:
            d = asdict(t)
            d["amount"] = float(d["amount"])
            d["date"] = d["date"].isoformat()
            clean_data.append(d)

        print(orjson.dumps({"transactions": clean_data, "errors": errors}).decode())
        return

    if errors:
        rprint(f"[red]Errors: {errors}[/red]")

    table = Table(title=f"Transactions ({days} days)")
    table.add_column("Date", style="dim")
    table.add_column("Payee")
    table.add_column("Amount", justify="right")

    for t in data:
        color = "red" if t.amount < 0 else "green"
        table.add_row(
            t.date.strftime("%Y-%m-%d"), t.payee, f"[{color}]${t.amount:,.2f}[/{color}]"
        )
    console.print(table)


if __name__ == "__main__":
    app()
