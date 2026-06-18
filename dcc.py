#!/usr/bin/env python3
"""
DCC Enterprise Blockchain Tester — unified CLI.

Commands:
  nodes      Discover and rank healthy nodes on the selected network.
  status     Show network health: best node, height, peer count.
  transfer   Run mass transfer from a CSV file.
  stress     Run a stress test (turbo engine) against the network.
  generate   Generate recipient wallets.
  verify     Verify wallet balances post-transfer.
  sweep      Sweep funds back to sender.
  dashboard  Launch the real-time monitoring dashboard.

Examples:
  python dcc.py --network testnet nodes
  python dcc.py --network testnet status
  python dcc.py --network testnet transfer recipients.csv
  python dcc.py --network testnet --node http://139.162.152.128:6863 transfer recipients.csv
  python dcc.py --network testnet stress --wallets 100 --sends 5
  python dcc.py --network testnet generate --count 200 --amount 1.0
  python dcc.py --network testnet verify
  python dcc.py --network testnet sweep
  python dcc.py --network testnet dashboard
"""
import argparse
import os
import sys
import subprocess
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

WORKSPACE = Path(__file__).parent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _set_network_env(args):
    """Push --network and --node into env so all child scripts pick them up."""
    if args.network:
        os.environ['DCC_NETWORK'] = args.network
    if getattr(args, 'node', None):
        os.environ['DCC_NODE'] = args.node


def _run(script: str, extra_args: list = None):
    """Run a sibling script with the current environment."""
    cmd = [sys.executable, str(WORKSPACE / script)] + (extra_args or [])
    result = subprocess.run(cmd, env=os.environ)
    sys.exit(result.returncode)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_nodes(args):
    """Discover and print ranked healthy nodes."""
    from networks import discover_nodes, NETWORKS

    network = args.network
    if network not in NETWORKS:
        print(f'Unknown network "{network}". Valid: {list(NETWORKS.keys())}')
        sys.exit(1)

    print(f'\nDiscovering nodes on {network}...\n')
    nodes = discover_nodes(network, timeout=args.timeout)

    if not nodes:
        print(f'No healthy nodes found on {network}.')
        sys.exit(1)

    print(f'{"#":<4} {"URL":<55} {"Height":>8} {"Latency":>10}  Version')
    print('-' * 90)
    for i, n in enumerate(nodes, 1):
        print(f'{i:<4} {n.url:<55} {n.height:>8} {n.latency_ms:>8.0f}ms  {n.version}')
    print(f'\n{len(nodes)} healthy node(s) found.')


def cmd_status(args):
    """Show network health summary."""
    import requests
    from networks import discover_nodes, NETWORKS

    network = args.network
    nodes = discover_nodes(network, timeout=args.timeout)

    if not nodes:
        print(f'\n❌ No healthy nodes on {network}.')
        sys.exit(1)

    best = nodes[0]
    print(f'\n{"="*60}')
    print(f'  Network : {network}')
    print(f'  Chain ID: {NETWORKS[network]["chain_id"]}')
    print(f'  Explorer: {NETWORKS[network]["explorer"]}')
    print(f'{"="*60}')
    print(f'\n  Best node : {best.url}')
    print(f'  Height    : {best.height:,}')
    print(f'  Latency   : {best.latency_ms:.0f} ms')
    print(f'  Version   : {best.version}')
    print(f'\n  Healthy nodes : {len(nodes)}')

    # Peer count from best node
    try:
        r = requests.get(f'{best.url}/peers/connected', timeout=args.timeout)
        if r.status_code == 200:
            print(f'  Connected peers: {len(r.json().get("peers", []))}')
    except Exception:
        pass
    print()


def cmd_transfer(args):
    _set_network_env(args)
    from config import validate_config
    validate_config()
    extra = [args.csv] if args.csv else []
    _run('turbo_transfer.py', extra)


def cmd_stress(args):
    _set_network_env(args)
    from config import validate_config
    validate_config()
    if args.wallets:
        os.environ['NUM_WALLETS'] = str(args.wallets)
    if args.sends:
        os.environ['SENDS_PER_WALLET'] = str(args.sends)
    if args.workers:
        os.environ['MAX_WORKERS'] = str(args.workers)
    if args.engine == 'turbo':
        _run('turbo_transfer.py')
    elif args.engine == 'hyper':
        _run('hyper_transfer.py')
    elif args.engine == 'blazing':
        _run('blazing_transfer.py')
    else:
        print(f'Unknown engine "{args.engine}". Choose: turbo, hyper, blazing')
        sys.exit(1)


def cmd_generate(args):
    _set_network_env(args)
    count = str(args.count)
    amount = str(args.amount)
    out = args.output or f'wallets_{count}.csv'
    _run('generate_real_wallets.py', [count, out, amount])


def cmd_verify(args):
    _set_network_env(args)
    from config import validate_config
    validate_config(require_private_key=False)
    _run('verify_all_2000.py')


def cmd_sweep(args):
    _set_network_env(args)
    from config import validate_config
    validate_config()
    _run('turbo_sweep.py')


def cmd_dashboard(args):
    _set_network_env(args)
    _run('dashboard_backend.py')


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog='dcc',
        description='DCC Enterprise Blockchain Tester',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        '--network', '-n',
        choices=['testnet', 'mainnet'],
        help='Target network (overrides DCC_NETWORK env var).',
    )
    parser.add_argument(
        '--node',
        metavar='URL',
        help='Override node URL (skips auto-discovery).',
    )
    parser.add_argument(
        '--timeout', type=int, default=5,
        help='Network probe timeout in seconds (default: 5).',
    )

    sub = parser.add_subparsers(dest='command', required=True)

    # nodes
    p_nodes = sub.add_parser('nodes', help='Discover and rank healthy nodes.')
    p_nodes.set_defaults(func=cmd_nodes)

    # status
    p_status = sub.add_parser('status', help='Network health summary.')
    p_status.set_defaults(func=cmd_status)

    # transfer
    p_tx = sub.add_parser('transfer', help='Mass transfer from CSV.')
    p_tx.add_argument('csv', nargs='?', help='Recipients CSV (default: real_wallets_2000_details.csv).')
    p_tx.set_defaults(func=cmd_transfer)

    # stress
    p_stress = sub.add_parser('stress', help='Stress test the network.')
    p_stress.add_argument('--engine', choices=['turbo', 'hyper', 'blazing'], default='turbo')
    p_stress.add_argument('--wallets', type=int, help='Number of recipient wallets.')
    p_stress.add_argument('--sends', type=int, help='Transfers per wallet.')
    p_stress.add_argument('--workers', type=int, help='Concurrent worker threads.')
    p_stress.set_defaults(func=cmd_stress)

    # generate
    p_gen = sub.add_parser('generate', help='Generate recipient wallets.')
    p_gen.add_argument('--count', type=int, default=2000, help='Number of wallets (default: 2000).')
    p_gen.add_argument('--amount', type=float, default=1.0, help='DCC per wallet (default: 1.0).')
    p_gen.add_argument('--output', help='Output CSV filename.')
    p_gen.set_defaults(func=cmd_generate)

    # verify
    p_verify = sub.add_parser('verify', help='Verify wallet balances.')
    p_verify.set_defaults(func=cmd_verify)

    # sweep
    p_sweep = sub.add_parser('sweep', help='Sweep funds back to sender.')
    p_sweep.set_defaults(func=cmd_sweep)

    # dashboard
    p_dash = sub.add_parser('dashboard', help='Launch real-time monitoring dashboard.')
    p_dash.set_defaults(func=cmd_dashboard)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    # --network flag overrides env var
    if args.network:
        os.environ['DCC_NETWORK'] = args.network
    if getattr(args, 'node', None):
        os.environ['DCC_NODE'] = args.node

    args.func(args)


if __name__ == '__main__':
    main()
