# Transactions Monorepo

A self-hosted financial tracking suite built with **Python 3.12**, **FastAPI**, **HTMX**, and **SimpleFin**. This monorepo is managed by [`uv`](https://github.com/astral-sh/uv).

> [!IMPORTANT]
> To use this application, you must first link your bank accounts on [SimpleFIN](https://beta-bridge.simplefin.org) to obtain a setup token.

## 🚀 Run with Docker Compose (Recommended)

This is the standard way to run the **Web App** in production or on a home server.

### 1. Create a `.env` file

Create a file named `.env` in the root directory. This file will store your security keys so they aren't hardcoded in git.

```ini
# .env
# Security key for session signing and database encryption.
# Generate a random string (e.g., `openssl rand -hex 32`)
SECRET_KEY=replace_this_with_a_long_secure_random_string
```

### 2. Start the Service

Run the following command to start the web server in the background:

```bash
docker-compose up -d
```

* **Web Interface**: [http://localhost:8000](https://www.google.com/search?q=http://localhost:8000)
* **Data Storage**: Data is persisted in the `transaction_data` Docker volume.

---

## 🖥️ CLI Tool Usage (`transactions-cli`)

The CLI is perfect for quick checks or cron jobs. It runs locally and stores credentials in your system's secure keyring.

### Running the CLI

You can run the CLI using `uv` from the root of the repo:

```bash
uv run finance [COMMAND] [OPTIONS]
```

### Command Reference

#### 1. `setup`

Initializes a connection to a financial provider.

```bash
uv run finance setup [PROVIDER] --token [TOKEN]
```

| Argument | Type | Default | Description |
| --- | --- | --- | --- |
| `PROVIDER` | Argument | `simplefin` | The name of the provider to use. Currently only supports `simplefin`. |
| `--token`, `-t` | **Required** | N/A | The Setup Token provided by SimpleFin. |

#### 2. `accounts`

Lists all connected bank accounts and their current balances.

```bash
uv run finance accounts [--json]
```

| Argument | Type | Default | Description |
| --- | --- | --- | --- |
| `--json` | Option | `False` | If set, outputs the data as a raw JSON string instead of a formatted table. |

#### 3. `view`

Fetches and displays transactions for a specific time range.

```bash
uv run finance view [--days N] [--json]
```

| Argument | Type | Default | Description |
| --- | --- | --- | --- |
| `--days`, `-d` | Option | `30` | The number of days of history to fetch (counting back from today). |
| `--json` | Option | `False` | If set, outputs JSON. Useful for piping data to other tools (e.g., `jq`). |

---

## 🛠️ Development Setup (Local)

If you want to contribute code or run the web app outside of Docker.

### Prerequisites

1. **Install `uv**`:

```bash
curl -LsSf [https://astral.sh/uv/install.sh](https://astral.sh/uv/install.sh) | sh
```

1. **Sync Dependencies**:

```bash
uv sync
```

### Running the Web App Locally

1. Set the required environment variable (or let it default to development mode):

```bash
export SECRET_KEY=dev-key
```

1. Run the app:

```bash
uv run web
```

1. The app will be available at `http://localhost:8000`. Database files will be stored in your OS's default data directory (e.g., `~/Library/Application Support/transactions-web` on macOS).

### Running Tests (Manual)

You can test the core logic by entering the virtual environment:

```bash
uv run python
>>> from transactions_core import SimpleFinProvider
>>> # Import and test classes interactively...
```
