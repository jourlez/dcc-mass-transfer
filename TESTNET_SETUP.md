# Testnet 2.0 Setup & Usage

This guide walks you through setting up and running the dcc-mass-transfer toolkit against **DecentralChain Testnet 2.0**.

## Prerequisites

- Python 3.8+
- Virtual environment (venv)
- Testnet miner wallet private key (has ~50M DCC)
- Testnet node connectivity

## 1. Environment Configuration

### Quick Start (Recommended)

Copy the testnet template:

```bash
cp .env.testnet .env
```

Then edit `.env` with your testnet values:

```bash
# Required: Miner wallet private key (base58)
DCC_PRIVATE_KEY=your_testnet_miner_key_here

# Leave blank to use native DCC (recommended for testnet)
DCC_ASSET_ID=

# Default testnet values are pre-configured:
# DCC_NODE=http://66.228.55.154:6868
# DCC_CHAIN_ID=!
```

Verify configuration:

```bash
python3 -c "from config import validate_config; validate_config()"
```

Should produce no errors. If it complains, `.env` is missing values.

### Manual Configuration

Alternatively, create `.env` from scratch:

```bash
cat > .env << 'EOF'
DCC_NODE=http://66.228.55.154:6868
DCC_CHAIN_ID=!
DCC_PRIVATE_KEY=your_testnet_miner_key_here
DCC_ASSET_ID=
EOF
```

## 2. Launch the Dashboard

The web UI is the primary control interface:

```bash
bash START_DASHBOARD.sh
```

Opens: **http://localhost:8888**

### Dashboard Features

- **Dashboard tab**: Live KPIs, throughput metrics, transaction count
- **Wallets tab**: Browse generated/funded wallet addresses
- **Transactions tab**: Transaction feed with hashes, status, timestamps
- **Logs tab**: Real-time log viewer with syntax highlighting

### Running a Test

1. From Dashboard → select preset (e.g., "100x10") or configure custom
2. Click **"Start"**
3. Watch KPI cards update in real-time
4. Monitor **Logs** tab for any errors
5. Click **"Stop"** to halt early

## 3. Transfer Engines

Choose based on your testing goal:

| Engine | Command | Use Case |
|--------|---------|----------|
| **Turbo** | `python3 turbo_transfer.py recipients.csv` | Real TX at max speed (~500 tx/sec) |
| **Hyper** | `python3 hyper_transfer.py recipients.csv` | Real + simulated (25k tx/sec target) |
| **Blazing** | `python3 blazing_transfer.py recipients.csv` | Async (250k tx/sec target) |
| **Ultra (10M)** | `python3 ultra_stress_10m.py` | Exhausts DCC then simulates to 10M target |
| **Single TX** | `python3 single_transfer.py recipients.csv` | Per-recipient transactions (not mass transfer) |

### Example: Run Turbo Engine

```bash
# Generate recipients
python3 generate_real_wallets.py 1000 test_wallets.csv

# Send them 10 DCC each
python3 turbo_transfer.py test_wallets.csv

# Watch in dashboard at http://localhost:8888
```

## 4. Wallet Management

### Generate Test Wallets

```bash
# Offline (no node queries, fastest)
python3 generate_wallets_offline.py 2000 wallets.csv

# With pywaves (validates addresses)
python3 generate_real_wallets.py 2000 wallets.csv
```

### Fund Wallets

```bash
# Refill all 2000 wallets with DCC for fees
python3 refill_dcc_for_fees.py

# Or refill with tokens (if you issued a testnet asset)
python3 refill_wallets.py
```

### Verify Wallets Received Funds

```bash
python3 verify_all_2000.py
```

Checks balances on testnet and reports:
- ✅ Successfully funded
- ⚠️ Zero balance
- ❌ Unreachable

### Sweep Funds Back to Miner

After testing, recover DCC for future tests:

```bash
# Fast sequential sweep
python3 sweep_dcc_sequential.py

# Or parallel (turbo) sweep
python3 turbo_sweep.py
```

## 5. Common Workflows

### Full End-to-End Stress Test

```bash
# 1. Generate 2000 wallets
python3 generate_wallets_offline.py 2000 wallets.csv

# 2. Fund them from miner (~0.1 DCC each for fees)
python3 refill_dcc_for_fees.py

# 3. Run turbo transfers (real on-chain)
python3 turbo_transfer.py wallets.csv

# 4. Verify all wallets funded
python3 verify_all_2000.py

# 5. Sweep back to miner
python3 turbo_sweep.py

# 6. Check final balance
python3 -c "import pywaves as pw; from config import *; pw.setNode(os.getenv('DCC_NODE'), 'custom', os.getenv('DCC_CHAIN_ID')); print(pw.Address(os.getenv('DCC_PRIVATE_KEY')).balance() / 1e8, 'DCC')"
```

### Hybrid Real+Sim Test (25k tx/sec target)

```bash
# 1. Generate test recipients
python3 generate_real_wallets.py 500 recipients.csv

# 2. Run Hyper engine (real + simulation)
python3 hyper_transfer.py recipients.csv

# 3. Watch dashboard for real TPS vs simulated throughput
```

### Maximum Throughput Benchmark (250k tx/sec)

```bash
# 1. Prepare wallets (Blazing requires more wallets for simulation)
python3 generate_wallets_offline.py 5000 wallets.csv
python3 refill_dcc_for_fees.py

# 2. Run Blazing (async, 250k target)
python3 blazing_transfer.py wallets.csv

# 3. Check logs for:
#    - Real phase throughput (actual TX/sec on-chain)
#    - Sim phase throughput (simulated TX/sec)
#    - Total aggregate (should approach 250k if sim padding is correct)
```

## 6. Configuration Reference

`.env` variables:

```bash
# Network
DCC_NODE=http://66.228.55.154:6868         # Testnet node
DCC_CHAIN_ID=!                             # Testnet chain ID (ASCII 33)

# Wallet
DCC_PRIVATE_KEY=...                        # Miner private key (base58)
DCC_ASSET_ID=                              # Leave blank for native DCC

# Transfer Settings
NUM_WALLETS=2000                           # How many wallets to generate
SENDS_PER_WALLET=10                        # How many sends per wallet
MAX_WORKERS=200                            # Concurrent thread/workers

# Performance (for Hyper/Blazing)
REAL_WORKERS=200                           # Real TX workers
SIM_WORKERS=80                             # Simulation workers
TARGET_RATE=25000                          # Target tx/sec (Hyper=25k, Blazing=250k)
DURATION=60                                # Run duration (seconds)

# Rate Limiting
RATE_LIMIT_DELAY=0                         # Delay between requests (0=no delay)
```

## 7. Troubleshooting

### "DCC_PRIVATE_KEY not set"

```bash
# Missing from .env, add it:
echo "DCC_PRIVATE_KEY=your_key_here" >> .env
```

### "Connection refused" / "Cannot reach node"

```bash
# Check testnet node is up:
curl http://66.228.55.154:6868/blocks/height

# If offline, try alternative node:
DCC_NODE=http://139.162.152.128:6863 python3 turbo_transfer.py recipients.csv
```

### "Insufficient balance for DCC"

Miner wallet is out of DCC. Check balance:

```bash
python3 -c "
import pywaves as pw
import os
from dotenv import load_dotenv; load_dotenv()
from config import validate_config
validate_config()

pw.setNode(os.getenv('DCC_NODE'), 'custom', os.getenv('DCC_CHAIN_ID'))
addr = pw.Address(os.getenv('DCC_PRIVATE_KEY'))
print(f'Balance: {addr.balance() / 1e8} DCC')
"
```

If zero, request more from testnet faucet or ask admin.

### Dashboard not opening

```bash
# Check if Flask started:
ps aux | grep dashboard_backend.py

# Manual start:
python3 dashboard_backend.py &
# Then open http://localhost:8888
```

### Verify script takes too long

Uses requests (HTTP) now — much faster than curl. If still slow:

```bash
# Check node latency
time curl -s http://66.228.55.154:6868/addresses/balance/3DXW... | jq .

# If >1sec, node may be under load. Run verify during off-peak.
```

## 8. Next Steps

- **Production testnet load**: Use Blazing engine with 5000+ wallets
- **Real node limits**: Monitor logs for rate-limit errors; adjust MAX_WORKERS down
- **Custom assets**: Issue a testnet token, set `DCC_ASSET_ID`, re-run refill + transfer
- **Mainnet migration**: Change `.env` to mainnet values:
  ```bash
  DCC_NODE=https://mainnet-node.decentralchain.io
  DCC_CHAIN_ID=?
  ```

## Support

For issues or questions, check:
- README.md — architecture & transfer engine details
- Logs in dashboard → Logs tab (real-time streaming)
- `full_stress.log` or `*.log` files in this directory
