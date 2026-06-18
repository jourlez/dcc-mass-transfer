#!/usr/bin/env python3
"""
Network registry and live node discovery for DecentralChain.

Supports automatic node selection: probes seed nodes, discovers connected
peers, health-checks all candidates, and returns them ranked by block height
(highest first) then latency (lowest first).
"""
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import List, Optional

import requests

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Network registry
# ---------------------------------------------------------------------------

NETWORKS: dict = {
    'testnet': {
        'chain_id': '!',
        'seed_nodes': [
            'https://testnet-node.decentralchain.io',
            'http://139.162.152.128:6863',
            'http://139.162.152.128:6864',
            'http://139.162.152.128:6865',
        ],
        'explorer': 'https://testnet.decentralscan.com',
        'data_service': 'https://testnet-data-service.decentralchain.io',
    },
    'mainnet': {
        'chain_id': '?',
        'seed_nodes': [
            'https://mainnet-node.decentralchain.io',
        ],
        'explorer': 'https://decentralscan.com',
        'data_service': 'https://data-service.decentralchain.io',
    },
}


def known_networks() -> List[str]:
    return list(NETWORKS.keys())


def chain_id_for(network: str) -> str:
    _require_known(network)
    return NETWORKS[network]['chain_id']


# ---------------------------------------------------------------------------
# Node probing
# ---------------------------------------------------------------------------

@dataclass
class NodeInfo:
    url: str
    height: int = 0
    latency_ms: float = 9999.0
    version: str = 'unknown'
    healthy: bool = False
    error: str = ''

    def __str__(self) -> str:
        if self.healthy:
            return (
                f'{self.url}  '
                f'height={self.height}  '
                f'latency={self.latency_ms:.0f}ms  '
                f'v{self.version}'
            )
        return f'{self.url}  UNHEALTHY ({self.error})'


def probe_node(url: str, timeout: int = 5) -> NodeInfo:
    """
    Probe a single node for liveness, current height, and latency.
    Never raises — always returns a NodeInfo (healthy or not).
    """
    url = url.rstrip('/')
    info = NodeInfo(url=url)
    try:
        t0 = time.time()
        r = requests.get(f'{url}/blocks/height', timeout=timeout)
        info.latency_ms = (time.time() - t0) * 1000
        if r.status_code == 200:
            info.height = r.json().get('height', 0)
            info.healthy = True
        else:
            info.error = f'HTTP {r.status_code}'
    except requests.exceptions.ConnectionError as exc:
        info.error = f'connection refused ({exc.__class__.__name__})'
    except requests.exceptions.Timeout:
        info.error = f'timeout after {timeout}s'
    except (requests.exceptions.RequestException, ValueError, KeyError) as exc:
        info.error = str(exc)

    if info.healthy:
        # Best-effort version fetch — non-fatal
        try:
            rv = requests.get(f'{url}/node/version', timeout=timeout)
            if rv.status_code == 200:
                info.version = rv.json().get('version', 'unknown')
        except (requests.exceptions.RequestException, ValueError):
            pass

    return info


def _discover_peers(seed_url: str, timeout: int = 5) -> List[str]:
    """
    Ask a node for its connected peers and return their URLs.
    Converts peer address strings (/1.2.3.4:6868) to http:// URLs.
    """
    try:
        r = requests.get(
            f'{seed_url.rstrip("/")}/peers/connected',
            timeout=timeout,
        )
        if r.status_code != 200:
            return []
        peers = r.json().get('peers', [])
        urls: List[str] = []
        for peer in peers:
            addr = peer.get('address', '').lstrip('/')
            if not addr:
                continue
            host, _, port = addr.rpartition(':')
            if host and port:
                urls.append(f'http://{host}:{port}')
        return urls
    except (requests.exceptions.RequestException, ValueError, KeyError):
        return []


def discover_nodes(
    network: str,
    *,
    timeout: int = 5,
    max_probe_workers: int = 20,
) -> List[NodeInfo]:
    """
    Discover and rank healthy nodes for *network*.

    Process:
      1. Start from registered seed nodes.
      2. Query /peers/connected on each seed to expand the candidate pool.
      3. Health-check all candidates in parallel.
      4. Return sorted by (-height, latency_ms) — best node first.

    Args:
        network: 'testnet' or 'mainnet' (or any key in NETWORKS).
        timeout: Per-request timeout in seconds.
        max_probe_workers: Concurrent threads for health probing.

    Returns:
        All healthy NodeInfo objects, best-first.  Empty list if none respond.
    """
    _require_known(network)
    seeds = NETWORKS[network]['seed_nodes']
    candidates: set = set(seeds)

    # Peer discovery from seed nodes
    with ThreadPoolExecutor(max_workers=len(seeds)) as pool:
        futures = {pool.submit(_discover_peers, url, timeout): url for url in seeds}
        for future in as_completed(futures):
            candidates.update(future.result())

    # Health-check all candidates
    workers = min(len(candidates), max_probe_workers)
    with ThreadPoolExecutor(max_workers=max(workers, 1)) as pool:
        results: List[NodeInfo] = [
            f.result()
            for f in as_completed(pool.submit(probe_node, url, timeout) for url in candidates)
        ]

    healthy = [n for n in results if n.healthy]
    healthy.sort(key=lambda n: (-n.height, n.latency_ms))
    return healthy


def best_node(network: str, timeout: int = 5) -> NodeInfo:
    """
    Return the single best node for *network*, or raise RuntimeError if none
    are reachable.
    """
    nodes = discover_nodes(network, timeout=timeout)
    if not nodes:
        raise RuntimeError(
            f'No healthy nodes found on {network}. '
            f'Check connectivity to: {NETWORKS[network]["seed_nodes"]}'
        )
    return nodes[0]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _require_known(network: str) -> None:
    if network not in NETWORKS:
        raise ValueError(
            f'Unknown network "{network}". '
            f'Valid options: {known_networks()}'
        )
