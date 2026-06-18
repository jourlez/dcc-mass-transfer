#!/usr/bin/env python3
"""
Centralized configuration resolver for dcc-mass-transfer.

Resolution order for node and chain ID:
  1. Explicit env var (DCC_NODE / DCC_CHAIN_ID) — direct override.
  2. DCC_NETWORK name — auto-discover best node + derive chain ID.
  3. Neither set → hard fail with actionable error message.

Usage in scripts:
    from dotenv import load_dotenv
    load_dotenv()
    from config import resolve_node, resolve_chain_id, validate_config
    validate_config()
    NODE     = resolve_node()
    CHAIN_ID = resolve_chain_id()
"""
import os
import sys
from pathlib import Path

WORKSPACE = Path(__file__).parent


# ---------------------------------------------------------------------------
# Network resolution
# ---------------------------------------------------------------------------

def resolve_network():
    """Return DCC_NETWORK env var, or None if not set."""
    return os.getenv('DCC_NETWORK', '').strip() or None


def resolve_node(silent=False):
    """
    Resolve the node URL to use.

    Precedence:
      1. DCC_NODE env var (explicit override — no discovery).
      2. DCC_NETWORK -> auto-discover best node via networks.discover_nodes().

    Args:
        silent: Suppress discovery progress output.

    Returns:
        Node URL string (no trailing slash).

    Raises:
        SystemExit(1): If neither DCC_NODE nor DCC_NETWORK is set, or no
                       healthy node is found on the selected network.
    """
    explicit = os.getenv('DCC_NODE', '').strip()
    if explicit:
        return explicit.rstrip('/')

    network = resolve_network()
    if not network:
        _die(
            'Neither DCC_NODE nor DCC_NETWORK is set.\n'
            '  Set DCC_NETWORK=testnet (or mainnet) to auto-discover a node,\n'
            '  or set DCC_NODE=<url> for an explicit override.'
        )

    from networks import best_node, known_networks, NETWORKS
    if network not in NETWORKS:
        _die(
            f'Unknown network "{network}". '
            f'Valid options: {known_networks()}'
        )

    if not silent:
        print(f'[config] Discovering best node on {network}...', flush=True)
    try:
        info = best_node(network)
    except RuntimeError as exc:
        _die(str(exc))

    if not silent:
        print(
            f'[config] Selected {info.url} '
            f'(height={info.height}, latency={info.latency_ms:.0f}ms)',
            flush=True,
        )
    return info.url


def resolve_chain_id():
    """
    Resolve the chain ID character.

    Precedence:
      1. DCC_CHAIN_ID env var (explicit override).
      2. DCC_NETWORK -> derive from networks.NETWORKS registry.

    Raises:
        SystemExit(1): If chain ID cannot be determined.
    """
    explicit = os.getenv('DCC_CHAIN_ID', '').strip()
    if explicit:
        return explicit

    network = resolve_network()
    if not network:
        _die(
            'Neither DCC_CHAIN_ID nor DCC_NETWORK is set.\n'
            '  Set DCC_NETWORK=testnet (or mainnet) to auto-derive the chain ID,\n'
            '  or set DCC_CHAIN_ID=! (testnet) / DCC_CHAIN_ID=? (mainnet).'
        )

    from networks import chain_id_for
    return chain_id_for(network)


def resolve_private_key():
    """Resolve DCC_PRIVATE_KEY. Fails loudly if not set or still a placeholder."""
    pk = os.getenv('DCC_PRIVATE_KEY', '').strip()
    if not pk or pk.startswith('YOUR_PRIVATE_KEY'):
        _die(
            'DCC_PRIVATE_KEY is not set.\n'
            '  Edit your .env file and set a real base58 private key.'
        )
    return pk


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_config(require_private_key=True, require_node=True):
    """
    Validate required configuration before any network call.

    Checks:
      - At least one of DCC_NODE or DCC_NETWORK is set.
      - DCC_PRIVATE_KEY is set and not a placeholder (if require_private_key=True).

    Raises:
        SystemExit(1): On any validation failure.
    """
    errors = []

    if require_node:
        has_node = bool(os.getenv('DCC_NODE', '').strip())
        has_network = bool(os.getenv('DCC_NETWORK', '').strip())
        if not has_node and not has_network:
            errors.append(
                'Set DCC_NETWORK=testnet (or mainnet) for auto-discovery, '
                'or DCC_NODE=<url> for an explicit node.'
            )

    if require_private_key:
        pk = os.getenv('DCC_PRIVATE_KEY', '').strip()
        if not pk or pk.startswith('YOUR_PRIVATE_KEY'):
            errors.append(
                'DCC_PRIVATE_KEY is not set. Add your base58 private key to .env.'
            )

    if errors:
        print('\n❌ Configuration error:\n', file=sys.stderr)
        for err in errors:
            print(f'  • {err}\n', file=sys.stderr)
        print(
            'Copy the appropriate template and fill in your values:\n'
            '  cp .env.testnet .env   # testnet\n'
            '  cp .env.mainnet .env   # mainnet\n',
            file=sys.stderr,
        )
        sys.exit(1)


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def get_workspace():
    return str(WORKSPACE)


def get_log_file(script_name='transfer'):
    return str(WORKSPACE / f'{script_name}.log')


def get_wallets_csv():
    return str(WORKSPACE / 'real_wallets_2000_details.csv')


# ---------------------------------------------------------------------------
# Internal
# ---------------------------------------------------------------------------

def _die(message):
    print(f'\n❌ {message}\n', file=sys.stderr)
    sys.exit(1)
