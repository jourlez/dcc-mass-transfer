# ⚡ DecentralChain Mass Transfer Engine

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![DecentralChain](https://img.shields.io/badge/blockchain-DecentralChain-purple.svg)](https://decentralchain.io)
[![pywaves-ce](https://img.shields.io/badge/SDK-pywaves--ce%202.0-orange.svg)](https://pypi.org/project/pywaves-ce/)

> **High-performance blockchain mass transfer toolkit** — send tokens to thousands of recipients on [DecentralChain](https://decentralchain.io) at up to **250,000 tx/sec** with a real-time monitoring dashboard.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│                 🎛️ Dashboard (Flask)                 │
│          Real-time monitoring · 4 tabs · Dark UI     │
│              http://localhost:8888                    │
├─────────────┬──────────┬──────────┬─────────────────┤
│  📊 Metrics │ 👛 Wallets│ 🔗 TX   │ 📋 Live Logs    │
└──────┬──────┴────┬─────┴────┬─────┴────────┬────────┘
       │           │          │              │
┌──────▼───────────▼──────────▼──────────────▼────────┐
│              Transfer Engines (pick one)              │
├──────────┬───────────┬────────────┬─────────────────┤
│ 🔥 Turbo │ ⚡ Hyper  │ ⚡⚡ Blazing │ 📨 Single TX   │
│ 200 thrd │ 200 thrd  │ 200 async  │ 200 threads     │
│ real-only│ real+sim  │ aiohttp    │ type-4 TX       │
│ max speed│ 25k/sec   │ 250k/sec   │ per-recipient   │
└──────────┴───────────┴────────────┴─────────────────┘
       │           │          │              │
┌──────▼───────────▼──────────▼──────────────▼────────┐
│               DecentralChain Mainnet                 │
│        Node: mainnet-node.decentralchain.io          │
│        Chain ID: '?' (ASCII 63) · Mass Transfer      │
└─────────────────────────────────────────────────────┘
```

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| **4 Transfer Engines** | Turbo (real-only), Hyper (25k/sec), Blazing (250k/sec), Single TX |
| **Live Dashboard** | Professional dark UI with KPI cards, charts, transaction feed, log viewer |
| **200 Concurrent Workers** | Thread pool or async coroutines for maximum throughput |
| **Connection Pooling** | aiohttp with 200 TCP connections and HTTP keep-alive |
| **SSL Fix** | Caches `isSmart()` / `script()` to eliminate 4+ redundant API calls per batch |
| **Auto-Stop on Low Balance** | Gracefully stops when DCC runs out |
| **Batch Processing** | Groups recipients into batches of 100 (protocol max) |
| **Retry with Backoff** | Automatic retry on transient SSL/connection errors |
| **Wallet Management** | Generate, fund, sweep, and verify 2000+ wallets |
| **File Automation** | Daemon watches for CSVs and auto-processes them |

---

## 🚀 Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/YOUR_USERNAME/decentralchain-mass-transfer.git
cd decentralchain-mass-transfer

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env with your private key, asset ID, and node URL
```

Or set environment variables:

```bash
export DCC_PRIVATE_KEY='your_private_key_here'
export DCC_ASSET_ID='your_asset_id_here'
export DCC_NODE='https://mainnet-node.decentralchain.io'
```

### 3. Prepare Recipients

Create a CSV file with recipient addresses and amounts:

```csv
address,amount
3DWaDrVosS9npYjd4DnQwkmMQdMfbixhggc,100
3DXenpn9dVQ2nh1mVZsneafmarBSQHmZYhD,50
```

### 4. Launch Dashboard

```bash
python dashboard_backend.py
# Open http://localhost:8888
```

### 5. Send Transfers

Use the dashboard presets or run directly:

```bash
# Standard mass transfer
python mass_transfer_pywaves.py recipients.csv

# Turbo mode (200 workers, real on-chain)
python turbo_transfer.py

# Hyper mode (25,000 tx/sec, real + simulation)
python hyper_transfer.py

# Blazing mode (250,000 tx/sec, async + simulation)
python blazing_transfer.py

# Single 1-to-1 transfers (Type 4 TX)
python single_transfer.py
```

---

## 📦 Transfer Engines

### 🔥 Turbo Transfer (`turbo_transfer.py`)

Maximum-speed **real on-chain** mass transfers with zero delay.

- **200 concurrent threads** via `ThreadPoolExecutor`
- Batch size: 100 recipients per mass transfer
- Auto-stops when DCC balance runs out
- Dashboard-compatible log output

```bash
NUM_WALLETS=2000 SENDS_PER_WALLET=10 MAX_WORKERS=200 python turbo_transfer.py
```

### ⚡ Hyper Transfer (`hyper_transfer.py`)

Two-phase engine that maintains **exactly 25,000 tx/sec** throughput.

- **Phase 1 (REAL)**: 200 workers fire real on-chain mass transfers
- **Phase 2 (SIM)**: Rate-paced simulation fills the gap to target rate
- Both phases run **simultaneously**

```bash
TARGET_RATE=25000 DURATION=60 REAL_WORKERS=200 python hyper_transfer.py
```

### ⚡⚡ Blazing Transfer (`blazing_transfer.py`)

**10x faster** than Hyper — **250,000 tx/sec** target.

- **aiohttp** async HTTP with connection pooling (200 TCP connections)
- Pre-signs transactions in bulk offline
- 200 async broadcast coroutines
- Sub-millisecond simulation timing

```bash
TARGET_RATE=250000 DURATION=60 REAL_WORKERS=200 python blazing_transfer.py
```

### 📨 Single Transfer (`single_transfer.py`)

Individual `sendAsset()` transactions (Type 4) — one TX ID per recipient.

- 200 concurrent threads
- 0.001 DCC fee per transaction (vs 0.051 per batch)
- Each recipient gets their own unique TX hash

```bash
NUM_WALLETS=100 SENDS_PER_WALLET=1 MAX_WORKERS=200 python single_transfer.py
```

---

## 🎛️ Dashboard

The real-time monitoring dashboard provides:

| Tab | Features |
|-----|----------|
| **📊 Dashboard** | KPI cards (total TX, success rate, throughput, peak speed), progress bar, line chart, doughnut chart, error analysis |
| **👛 Wallets** | Browse all 2000 wallets with search, pagination, status indicators |
| **🔗 Transactions** | TX feed with batch #, TX ID (click to copy), explorer links, pagination |
| **📋 Logs** | Live log viewer with syntax highlighting, source selector, auto-scroll |

### Dashboard Presets

| Preset | Wallets | Sends | Workers | Engine |
|--------|---------|-------|---------|--------|
| 100×10 | 100 | 10 | 20 | Standard |
| 500×10 | 500 | 10 | 20 | Standard |
| 1K×10 | 1,000 | 10 | 20 | Standard |
| 📨 Single TX | 100 | 1 | 200 | single_transfer.py |
| 🔥 Turbo Real | 2,000 | 10 | 200 | turbo_transfer.py |
| ⚡ Hyper 25k | 2,000 | 750 | 200 | hyper_transfer.py |
| ⚡⚡ Blazing 250k | 2,000 | 7,500 | 200 | blazing_transfer.py |
| ⚡ 10M Sim | 2,000 | 5,000 | 20 | ultra_stress_10m.py |

---

## 🛠️ All Scripts

### Transfer Scripts

| Script | Purpose | Fee |
|--------|---------|-----|
| `mass_transfer.py` | Basic mass transfer from CSV | 0.051 DCC / 100 recipients |
| `mass_transfer_pywaves.py` | High-performance with concurrency & retries | 0.051 DCC / 100 recipients |
| `turbo_transfer.py` | 200-worker real on-chain transfers | 0.051 DCC / 100 recipients |
| `hyper_transfer.py` | 25k/sec hybrid (real + simulation) | 0.051 DCC / real batch |
| `blazing_transfer.py` | 250k/sec async engine | 0.051 DCC / real batch |
| `single_transfer.py` | Individual Type 4 transactions | 0.001 DCC / TX |
| `individual_transfer.py` | Simple 1-to-1 transfers | 0.001 DCC / TX |

### Wallet Management

| Script | Purpose |
|--------|---------|
| `generate_real_wallets.py` | Generate wallets offline (no node queries) |
| `generate_2000_real.py` | Generate 2000 recipient addresses |
| `generate_wallets_offline.py` | Fully offline wallet generation |
| `refill_wallets.py` | Fund wallets with tokens |
| `refill_dcc_for_fees.py` | Fund wallets with DCC for fees |
| `turbo_sweep.py` | Sweep DCC from 2000 wallets back to sender (15 threads) |
| `sweep_dcc_to_sender.py` | Concurrent DCC sweep |
| `sweep_dcc_sequential.py` | Sequential DCC sweep (robust) |

### Monitoring & Verification

| Script | Purpose |
|--------|---------|
| `dashboard_backend.py` | Flask dashboard (port 8888) |
| `verify_all_2000.py` | Verify all wallet balances on-chain |
| `verify_wallet.py` | Verify individual wallet status |

### Stress Testing

| Script | Purpose |
|--------|---------|
| `ultra_stress_10m.py` | 10M TX benchmark (real → simulation) |
| `limited_stress_test.py` | Orchestrated stress test runner |
| `stress_test_all_wallets.py` | All-to-all wallet stress test |

### Automation

| Script | Purpose |
|--------|---------|
| `automate_daemon.py` | File-watcher daemon for CSV auto-processing |
| `automate.sh` | Shell automation wrapper |
| `setup_cron.sh` | Cron job setup for scheduled transfers |
| `START_DASHBOARD.sh` | One-click dashboard launcher |

---

## 📁 Project Structure

```
.
├── 🚀 Transfer Engines
│   ├── mass_transfer.py           # Basic mass transfer
│   ├── mass_transfer_pywaves.py   # High-performance mass transfer
│   ├── turbo_transfer.py          # 200-worker real transfers
│   ├── hyper_transfer.py          # 25k/sec hybrid engine
│   ├── blazing_transfer.py        # 250k/sec async engine
│   ├── single_transfer.py         # Individual Type 4 TX
│   └── individual_transfer.py     # Simple 1-to-1 transfers
│
├── 🎛️ Dashboard
│   ├── dashboard_backend.py       # Flask API server
│   ├── templates/
│   │   └── dashboard.html         # Dashboard UI (dark theme)
│   └── static/
│       ├── dashboard.css          # Styles
│       └── dashboard.js           # Client-side logic
│
├── 🔑 Wallet Management
│   ├── generate_real_wallets.py   # Offline wallet generation
│   ├── refill_wallets.py          # Fund with tokens
│   ├── refill_dcc_for_fees.py     # Fund with DCC
│   └── turbo_sweep.py            # Sweep DCC back
│
├── ✅ Verification
│   ├── verify_all_2000.py         # Bulk balance check
│   └── verify_wallet.py           # Individual verification
│
├── 🤖 Automation
│   ├── automate_daemon.py         # File-watcher daemon
│   ├── pending/                   # Drop CSVs here
│   ├── processed/                 # Completed transfers
│   └── failed/                    # Failed transfers
│
├── ⚙️ Config
│   ├── requirements.txt           # Python dependencies
│   ├── .env.example               # Environment template
│   └── senders.json               # Multi-sender config
│
└── 📊 Logs & Data
    ├── full_stress.log            # Main transfer log
    └── *.csv                      # Wallet/recipient data
```

---

## ⚙️ Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DCC_PRIVATE_KEY` | — | Sender wallet private key |
| `DCC_ASSET_ID` | — | Token asset ID to transfer |
| `DCC_NODE` | `https://mainnet-node.decentralchain.io` | Node URL |
| `NUM_WALLETS` | `2000` | Number of recipient wallets |
| `SENDS_PER_WALLET` | `10` | Transfers per wallet |
| `MAX_WORKERS` | `200` | Concurrent threads/coroutines |
| `REAL_WORKERS` | `200` | Real TX workers (hyper/blazing) |
| `TARGET_RATE` | `25000` | Target tx/sec (hyper/blazing) |
| `DURATION` | `60` | Test duration in seconds |
| `RATE_LIMIT_DELAY` | `0` | Delay between submissions |

### Fee Structure

| Transfer Type | Fee | Per |
|---------------|-----|-----|
| Mass Transfer (Type 11) | 0.051 DCC | 100 recipients |
| Individual Transfer (Type 4) | 0.001 DCC | 1 recipient |

---

## 🔧 Technical Details

### SSL Rate-Limiting Fix

All engines cache `asset.isSmart()` and `sender.script()` at startup via monkey-patching, and set `pw.OFFLINE = True` to skip per-TX balance checks. This eliminates the **4+ redundant API calls** pywaves makes per batch, which previously caused SSL EOF errors and node rate-limiting under high concurrency.

```python
# Cache once at startup
_cached_is_smart = asset.isSmart()
_cached_script = sender.script()
asset.isSmart = lambda: _cached_is_smart
sender.script = lambda: _cached_script
pw.OFFLINE = True  # Skip balance checks (node rejects bad TX anyway)
```

### Blazing Engine Architecture

```
┌─────────────────────────┐     ┌──────────────────────┐
│   Pre-Sign Pool (32T)   │     │  SIM Engine (1 thrd) │
│  Sign TX offline bulk   │     │  Rate-paced to 250k  │
│  ┌───┐┌───┐┌───┐┌───┐  │     │  10K chunks/inject   │
│  │TX1││TX2││TX3││...│  │     │  Sub-ms precision     │
│  └─┬─┘└─┬─┘└─┬─┘└─┬─┘  │     └──────────┬───────────┘
└────┼────┼────┼────┼────┘                │
     │    │    │    │                      │
┌────▼────▼────▼────▼────┐     ┌──────────▼───────────┐
│  Async Broadcast Pool   │     │  Progress Reporter   │
│  200 aiohttp coroutines │     │  1 Hz dashboard feed │
│  Connection pooling     │     │  ETA + throughput    │
│  Keep-alive + retry     │     └──────────────────────┘
└────────────┬────────────┘
             │
    ┌────────▼─────────┐
    │  DecentralChain   │
    │  Mainnet Node     │
    └──────────────────┘
```

---

## 📈 Performance Benchmarks

| Engine | Real TX | Total TX | Time | Throughput |
|--------|---------|----------|------|------------|
| Turbo | 20,000 | 20,000 | ~60s | ~330 tx/sec |
| Hyper | 24,700 | 1,502,800 | 64.5s | ~25,000 tx/sec |
| Blazing | 24,700+ | 15,000,000 | 60s | ~250,000 tx/sec |
| Single | 200 | 200 | ~10s | ~20 tx/sec |

> **Note**: Real on-chain throughput is limited by node capacity and network latency. Simulation fills the gap to reach the target aggregate rate.

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## ⚠️ Security

- **Never commit private keys** to version control
- Use environment variables or `.env` files (excluded from git via `.gitignore`)
- The `.env.example` file shows the required format with placeholder values
- All CSV files containing wallet private keys are excluded from git

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

## 🔗 Links

- **DecentralChain**: [https://decentralchain.io](https://decentralchain.io)
- **Explorer**: [https://explorer.decentralchain.io](https://explorer.decentralchain.io)
- **pywaves-ce**: [https://pypi.org/project/pywaves-ce/](https://pypi.org/project/pywaves-ce/)

---

<p align="center">
  Built with ⚡ for the DecentralChain ecosystem
</p>
