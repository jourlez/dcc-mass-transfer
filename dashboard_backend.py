"""
Enhanced Dashboard Backend for DecentralChain Stress Test Management
"""

from flask import Flask, render_template, request, jsonify, Response
from flask_cors import CORS
import os
import subprocess
import json
import threading
import time
import re
from datetime import datetime
from pathlib import Path
import csv
from collections import deque
import logging

app = Flask(__name__, template_folder='templates', static_folder='static')
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.config['TEMPLATES_AUTO_RELOAD'] = True
CORS(app)

# Global state
state = {
    'processes': {},
    'metrics': {
        'total_tx': 0, 'successful_tx': 0, 'failed_tx': 0, 'retry_tx': 0,
        'throughput': 0.0, 'elapsed_time': 0, 'current_status': 'idle',
        'start_time': None, 'error_count': 0, 'asset_errors': 0,
        'balance_errors': 0, 'checksum_errors': 0, 'success_rate': 0.0,
        'real_tx': 0, 'sim_tx': 0, 'target_tx': 10000000,
        'phase': 'idle', 'peak_throughput': 0.0
    },
    'wallets': { 'total': 0, 'loaded': 0, 'valid': 0, 'funded': 0, 'depleted': 0 },
    'history': {
        'timestamps': deque(maxlen=300), 'tx_counts': deque(maxlen=300),
        'success_counts': deque(maxlen=300), 'failed_counts': deque(maxlen=300),
        'throughputs': deque(maxlen=300)
    }
}

WORKSPACE = os.path.dirname(os.path.abspath(__file__))
LOGS_DIR = WORKSPACE
LOG_FILE_PATH = os.path.join(LOGS_DIR, 'dashboard.log')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Count wallets on startup
def _count_wallets():
    try:
        csv_path = os.path.join(WORKSPACE, 'real_wallets_2000_details.csv')
        with open(csv_path, 'r') as f:
            return sum(1 for _ in f) - 1
    except FileNotFoundError:
        return 0

_initial_wallet_count = _count_wallets()

# Global state — starts clean
state = {
    'processes': {},
    'metrics': {
        'total_tx': 0, 'successful_tx': 0, 'failed_tx': 0, 'retry_tx': 0,
        'throughput': 0.0, 'elapsed_time': 0, 'current_status': 'idle',
        'start_time': None, 'error_count': 0, 'asset_errors': 0,
        'balance_errors': 0, 'checksum_errors': 0, 'success_rate': 0.0,
        'real_tx': 0, 'sim_tx': 0, 'target_tx': 0,
        'phase': 'idle', 'peak_throughput': 0.0
    },
    'wallets': { 'total': _initial_wallet_count, 'loaded': 0, 'valid': 0, 'funded': 0, 'depleted': 0 },
    'history': {
        'timestamps': deque(maxlen=300), 'tx_counts': deque(maxlen=300),
        'success_counts': deque(maxlen=300), 'failed_counts': deque(maxlen=300),
        'throughputs': deque(maxlen=300)
    }
}


def parse_log_line(line):
    data = {}

    # Match: "Loaded N wallets/recipients"
    if 'Loaded' in line and ('wallets' in line or 'recipients' in line):
        m = re.search(r'Loaded (\d+)', line)
        if m: data['wallets_loaded'] = int(m.group(1))

    # Match: "Initialized N valid wallets"
    if 'Initialized' in line and 'valid wallets' in line:
        m = re.search(r'Initialized (\d+)', line)
        if m: data['wallets_valid'] = int(m.group(1))

    # Match: "Generated ... with N recipients, M total transfers"
    if 'Generated' in line and 'total transfers' in line:
        m = re.search(r'(\d+) recipients.*?(\d+) total transfers', line)
        if m:
            data['wallets_loaded'] = int(m.group(1))
            data['tx_total'] = int(m.group(2))

    # Match batch success: "✓ Batch N: M recipients | TX: ... | mode: REAL/SIM"
    if ('Batch' in line and 'recipients' in line and 'TX:' in line and
            ('✓' in line or 'Batch' in line)):
        m = re.search(r'Batch\s+(\d+):\s+(\d+)\s+recipients', line)
        if m:
            data['batch_num'] = int(m.group(1))
            data['batch_size'] = int(m.group(2))
            data['batch_success'] = True
        # Extract TX hash
        tx_m = re.search(r'TX:\s*([A-Za-z0-9]{30,50})', line)
        if tx_m:
            data['tx_id'] = tx_m.group(1)
        # Detect mode (REAL vs SIM)
        if 'mode: SIM' in line:
            data['sim_batch'] = True
        elif 'mode: REAL' in line:
            data['real_batch'] = True

    # Match single transfer success: "✓ TX #N/M (pct%) | rate tx/sec | to: addr | TX: hash | mode: REAL"
    if '✓' in line and 'TX #' in line and 'to:' in line and 'TX:' in line:
        sm = re.search(r'TX #(\d+)/(\d+)\s*\((\d+\.?\d*)%\)\s*\|\s*([\d.]+)\s*tx/sec', line)
        if sm:
            data['tx_count'] = int(sm.group(1))
            data['tx_total'] = int(sm.group(2))
            data['throughput'] = float(sm.group(4))
            data['batch_success'] = True
            data['batch_size'] = 1  # single tx = 1 recipient
        tx_m = re.search(r'TX:\s*([A-Za-z0-9]{30,50})', line)
        if tx_m:
            data['tx_id'] = tx_m.group(1)
        if 'mode: REAL' in line:
            data['real_batch'] = True

    # Match phase transitions
    if 'PHASE 1' in line:
        data['phase'] = 'real'
    elif 'PHASE 2' in line:
        data['phase'] = 'simulation'

    # Match progress line: "📊 Progress: N/M (pct%) | rate tx/sec | ETA: Ns"
    pm = re.search(r'Progress:\s*([\d,]+)/([\d,]+)\s*\(([\d.]+)%\)\s*\|\s*([\d,.]+)\s*tx/sec', line)
    if pm:
        data['progress_current'] = int(pm.group(1).replace(',', ''))
        data['progress_target'] = int(pm.group(2).replace(',', ''))
        data['throughput'] = float(pm.group(4).replace(',', ''))

    # Match target reached line
    if 'Target reached' in line:
        data['target_reached'] = '✅' in line

    # Match batch failure: "✗ Batch N failed"
    if 'Batch' in line and 'failed' in line and '✗' in line:
        m = re.search(r'Batch\s+(\d+)\s+failed.*?:\s*(.*)', line)
        if m:
            data['batch_num'] = int(m.group(1))
            data['batch_failed'] = True

    # Match old-style: "TX #N/Total (pct%) | throughput tx/sec"
    if 'TX #' in line:
        m = re.search(r'TX #(\d+)/(\d+)\s*\([\d.]+%\)\s*\|\s*([\d.]+)\s*tx/sec', line)
        if m:
            data['tx_count'] = int(m.group(1))
            data['tx_total'] = int(m.group(2))
            data['throughput'] = float(m.group(3))

    # Match summary lines (each stat is on its own line)
    sm = re.search(r'Successful:\s+(\d+)', line)
    if sm: data['successful'] = int(sm.group(1))

    fm = re.search(r'Failed:\s+(\d+)', line)
    if fm: data['failed'] = int(fm.group(1))

    rm = re.search(r'Retries:\s+(\d+)', line)
    if rm: data['retries'] = int(rm.group(1))

    sr = re.search(r'Success rate:\s*([\d.]+)%', line)
    if sr: data['success_rate'] = float(sr.group(1))

    tm = re.search(r'Time elapsed:\s*([\d.]+)', line)
    if tm: data['elapsed'] = float(tm.group(1))

    tp = re.search(r'Throughput:\s*([\d.]+)', line)
    if tp: data['throughput'] = float(tp.group(1))

    tr = re.search(r'Total recipients:\s+(\d+)', line)
    if tr: data['tx_total'] = int(tr.group(1))

    # Match errors (but not the "Failed: 0" summary line)
    if ('ERROR' in line or ('error' in line.lower() and 'Failed:' not in line)):
        data['error'] = 1
        if 'Asset' in line: data['asset_error'] = 1
        elif 'Insufficient' in line: data['balance_error'] = 1
        elif 'checksum' in line.lower(): data['checksum_error'] = 1

    return data


# Track cumulative batch counts (not reset by individual line parsing)
_batch_tracker = {'seen_batches': set(), 'success_count': 0, 'fail_count': 0}

# Track transactions for the feed
_transaction_log = []  # list of dicts: {batch, recipients, tx_id, timestamp, status}


def update_state_from_metrics(d):
    if 'tx_count' in d: state['metrics']['total_tx'] = d['tx_count']
    if 'tx_total' in d: state['metrics']['total_tx'] = max(state['metrics']['total_tx'], d.get('tx_total', 0))

    # Track batch-level progress incrementally
    if 'batch_success' in d and 'batch_num' in d:
        batch_key = d['batch_num']
        if batch_key not in _batch_tracker['seen_batches']:
            _batch_tracker['seen_batches'].add(batch_key)
            batch_size = d.get('batch_size', 100)
            _batch_tracker['success_count'] += batch_size
            state['metrics']['successful_tx'] = _batch_tracker['success_count']
            state['metrics']['total_tx'] = _batch_tracker['success_count'] + _batch_tracker['fail_count']
            # Track real vs simulated
            if d.get('sim_batch'):
                state['metrics']['sim_tx'] = state['metrics'].get('sim_tx', 0) + batch_size
            elif d.get('real_batch'):
                state['metrics']['real_tx'] = state['metrics'].get('real_tx', 0) + batch_size
            # Record transaction in feed (limit to avoid memory issues at 10M scale)
            if len(_transaction_log) < 10000:
                _transaction_log.append({
                    'batch': batch_key,
                    'recipients': batch_size,
                    'tx_id': d.get('tx_id', ''),
                    'timestamp': datetime.now().isoformat(),
                    'status': 'confirmed',
                    'mode': 'sim' if d.get('sim_batch') else 'real'
                })

    if 'phase' in d:
        state['metrics']['phase'] = d['phase']
    if 'progress_current' in d:
        state['metrics']['total_tx'] = d['progress_current']
        state['metrics']['successful_tx'] = d['progress_current']
    if 'progress_target' in d:
        state['metrics']['target_tx'] = d['progress_target']
    if 'target_reached' in d:
        state['metrics']['phase'] = 'completed'

    if 'batch_failed' in d and 'batch_num' in d:
        batch_key = d['batch_num']
        if batch_key not in _batch_tracker['seen_batches']:
            _batch_tracker['seen_batches'].add(batch_key)
            _batch_tracker['fail_count'] += 100
            state['metrics']['failed_tx'] = _batch_tracker['fail_count']
            state['metrics']['total_tx'] = _batch_tracker['success_count'] + _batch_tracker['fail_count']
            if len(_transaction_log) < 10000:
                _transaction_log.append({
                    'batch': batch_key,
                    'recipients': 100,
                    'tx_id': '',
                    'timestamp': datetime.now().isoformat(),
                    'status': 'failed'
                })

    # Summary-level stats override batch tracking when available
    if 'successful' in d: state['metrics']['successful_tx'] = d['successful']
    if 'failed' in d: state['metrics']['failed_tx'] = d['failed']
    if 'retries' in d: state['metrics']['retry_tx'] = d['retries']
    if 'throughput' in d: state['metrics']['throughput'] = d['throughput']
    if 'elapsed' in d: state['metrics']['elapsed_time'] = d['elapsed']
    if 'success_rate' in d: state['metrics']['success_rate'] = d['success_rate']
    if 'wallets_loaded' in d: state['wallets']['loaded'] = d['wallets_loaded']
    if 'wallets_valid' in d: state['wallets']['valid'] = d['wallets_valid']
    if 'error' in d: state['metrics']['error_count'] += 1
    if 'asset_error' in d: state['metrics']['asset_errors'] += 1
    if 'balance_error' in d: state['metrics']['balance_errors'] += 1
    if 'checksum_error' in d: state['metrics']['checksum_errors'] += 1

    # Calculate success rate from counts if not explicitly provided
    total = state['metrics']['successful_tx'] + state['metrics']['failed_tx']
    if total > 0 and 'success_rate' not in d:
        state['metrics']['success_rate'] = round(
            (state['metrics']['successful_tx'] / total) * 100, 1
        )


def tail_log(filepath, num_lines=100):
    try:
        with open(filepath, 'r', errors='ignore') as f:
            lines = f.readlines()
            return ''.join(lines[-num_lines:]) if lines else ''
    except FileNotFoundError:
        return ''


def count_csv_rows(filepath):
    try:
        with open(filepath, 'r') as f:
            return sum(1 for _ in f) - 1
    except FileNotFoundError:
        return 0


def background_metrics_updater():
    # Start at end of existing log file so we don't re-parse stale data from previous runs
    last_pos = 0
    last_mtime = 0
    try:
        if os.path.exists(LOG_FILE_PATH):
            last_pos = os.path.getsize(LOG_FILE_PATH)
            last_mtime = os.path.getmtime(LOG_FILE_PATH)
    except Exception:
        pass
    while True:
        try:
            if os.path.exists(LOG_FILE_PATH):
                # Only parse new log lines when a test is actually running or just completed
                status = state['metrics'].get('current_status', 'idle')
                if status not in ('running', 'completed', 'error', 'stopped'):
                    # Idle — skip to end of file so we don't parse stale/zombie data
                    try:
                        last_pos = os.path.getsize(LOG_FILE_PATH)
                        last_mtime = os.path.getmtime(LOG_FILE_PATH)
                    except Exception:
                        pass
                    time.sleep(1)
                    continue

                cur_mtime = os.path.getmtime(LOG_FILE_PATH)
                cur_size = os.path.getsize(LOG_FILE_PATH)

                # Log file was recreated (new test started)
                if cur_size < last_pos:
                    last_pos = 0

                if cur_mtime != last_mtime or cur_size > last_pos:
                    last_mtime = cur_mtime
                    with open(LOG_FILE_PATH, 'r', errors='ignore') as f:
                        f.seek(last_pos)
                        new_lines = f.readlines()
                        last_pos = f.tell()

                    for line in new_lines:
                        d = parse_log_line(line)
                        if d:
                            update_state_from_metrics(d)
                            # Record history on batch completions, throughput updates, or summary stats
                            if any(k in d for k in ['batch_success', 'batch_failed', 'tx_count',
                                                     'throughput', 'successful', 'elapsed']):
                                state['history']['timestamps'].append(datetime.now().isoformat())
                                state['history']['tx_counts'].append(state['metrics']['total_tx'])
                                state['history']['success_counts'].append(state['metrics']['successful_tx'])
                                state['history']['failed_counts'].append(state['metrics']['failed_tx'])
                                state['history']['throughputs'].append(state['metrics'].get('throughput', 0))

                    # Calculate elapsed time from start_time if running
                    if state['metrics']['current_status'] == 'running' and state['metrics'].get('start_time'):
                        try:
                            start = datetime.fromisoformat(state['metrics']['start_time'])
                            state['metrics']['elapsed_time'] = round((datetime.now() - start).total_seconds(), 1)
                            total_tx = state['metrics']['successful_tx'] + state['metrics']['failed_tx']
                            if state['metrics']['elapsed_time'] > 0 and total_tx > 0:
                                tp = round(total_tx / state['metrics']['elapsed_time'], 1)
                                state['metrics']['throughput'] = tp
                                if tp > state['metrics'].get('peak_throughput', 0):
                                    state['metrics']['peak_throughput'] = tp
                        except Exception:
                            pass
        except Exception as e:
            logger.error(f"Updater error: {e}")
        time.sleep(1)

threading.Thread(target=background_metrics_updater, daemon=True).start()


@app.after_request
def add_no_cache(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


@app.route('/favicon.ico')
def favicon():
    return '', 204


@app.route('/')
def index():
    return render_template('dashboard.html')


@app.route('/api/status')
def get_status():
    return jsonify({
        'timestamp': datetime.now().isoformat(),
        'metrics': dict(state['metrics']),
        'wallets': dict(state['wallets']),
        'processes': {k: v.get('status', 'unknown') for k, v in state['processes'].items()}
    })


@app.route('/api/metrics/detailed')
def get_detailed_metrics():
    csv_path = os.path.join(WORKSPACE, 'real_wallets_2000_details.csv')
    total_wallets = count_csv_rows(csv_path)
    state['wallets']['total'] = total_wallets  # Keep it fresh
    return jsonify({
        'timestamp': datetime.now().isoformat(),
        'execution': {
            'total_tx': state['metrics']['total_tx'],
            'successful_tx': state['metrics']['successful_tx'],
            'failed_tx': state['metrics']['failed_tx'],
            'retry_tx': state['metrics']['retry_tx'],
            'success_rate': state['metrics']['success_rate'],
            'throughput_tx_per_sec': state['metrics']['throughput'],
            'elapsed_seconds': state['metrics']['elapsed_time'],
            'status': state['metrics']['current_status']
        },
        'errors': {
            'total_errors': state['metrics']['error_count'],
            'asset_errors': state['metrics']['asset_errors'],
            'balance_errors': state['metrics']['balance_errors'],
            'checksum_errors': state['metrics']['checksum_errors']
        },
        'wallets': {
            'total_available': total_wallets,
            'loaded': state['wallets']['loaded'],
            'valid': state['wallets']['valid'],
            'funded': state['wallets']['funded'],
            'depleted': state['wallets']['depleted']
        },
        'history': {
            'timestamps': list(state['history']['timestamps']),
            'tx_counts': list(state['history']['tx_counts']),
            'success_counts': list(state['history']['success_counts']),
            'failed_counts': list(state['history']['failed_counts']),
            'throughputs': list(state['history']['throughputs'])
        }
    })


@app.route('/api/logs/<script_name>')
def get_logs(script_name):
    log_map = {
        'stress_test': 'full_stress.log',
        'refill_tokens': 'refill_output.log',
        'refill_dcc': 'refill_dcc_for_fees.log'
    }
    log_file = log_map.get(script_name, f'{script_name}.log')
    log_path = os.path.join(LOGS_DIR, log_file)
    return jsonify({'logs': tail_log(log_path, 150), 'script': script_name})


@app.route('/api/logs/stream/<script_name>')
def stream_logs(script_name):
    def generate():
        last_pos = 0
        log_map = {'stress_test': 'full_stress.log', 'refill_tokens': 'refill_output.log', 'refill_dcc': 'refill_dcc_for_fees.log'}
        log_file = log_map.get(script_name, f'{script_name}.log')
        log_path = os.path.join(LOGS_DIR, log_file)
        while True:
            try:
                if os.path.exists(log_path):
                    with open(log_path, 'r', errors='ignore') as f:
                        f.seek(last_pos)
                        new_lines = f.readlines()
                        last_pos = f.tell()
                        for line in new_lines:
                            yield f"data: {json.dumps({'line': line.strip()})}\n\n"
                time.sleep(0.5)
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
                time.sleep(2)
    return Response(generate(), mimetype='text/event-stream')


@app.route('/api/control/start', methods=['POST'])
def start_test():
    data = request.json or {}
    num_wallets = data.get('num_wallets', 1000)
    sends_per = data.get('sends_per_wallet', 10)
    workers = data.get('workers', 20)
    rate_delay = data.get('rate_delay', 0.01)

    try:
        python_bin = os.path.join(WORKSPACE, '.venv', 'bin', 'python')
        if not os.path.exists(python_bin):
            python_bin = 'python3'

        # Use single, blazing (250k/sec), hyper (25k/sec), turbo (real-only), ultra (10M sim), or limited
        use_ultra = data.get('ultra', False) or (num_wallets * sends_per >= 1000000)
        use_turbo = data.get('turbo', False)
        use_hyper = data.get('hyper', False)
        use_single = data.get('single', False)
        use_blazing = data.get('blazing', False)
        ultra_script = os.path.join(WORKSPACE, 'ultra_stress_10m.py')
        turbo_script = os.path.join(WORKSPACE, 'turbo_transfer.py')
        hyper_script = os.path.join(WORKSPACE, 'hyper_transfer.py')
        single_script = os.path.join(WORKSPACE, 'single_transfer.py')
        blazing_script = os.path.join(WORKSPACE, 'blazing_transfer.py')

        if use_single and os.path.exists(single_script):
            script_path = single_script
            use_mass_transfer = False
        elif use_blazing and os.path.exists(blazing_script):
            script_path = blazing_script
            use_mass_transfer = False
        elif use_hyper and os.path.exists(hyper_script):
            script_path = hyper_script
            use_mass_transfer = False
        elif use_turbo and os.path.exists(turbo_script):
            script_path = turbo_script
            use_mass_transfer = False
        elif use_ultra and os.path.exists(ultra_script):
            script_path = ultra_script
            use_mass_transfer = False
        else:
            script_path = os.path.join(WORKSPACE, 'limited_stress_test.py')
            use_mass_transfer = False
            if not os.path.exists(script_path):
                script_path = os.path.join(WORKSPACE, 'mass_transfer.py')
                use_mass_transfer = True
                if not os.path.exists(script_path):
                    return jsonify({'success': False, 'error': 'No script found'}), 500

        with open(LOG_FILE_PATH, 'w') as f:
            f.write(f"=== Test started {datetime.now().isoformat()} ===\n")
            f.write(f"Config: wallets={num_wallets}, sends={sends_per}, workers={workers}\n")

        state['metrics'] = {
            'total_tx': 0, 'successful_tx': 0, 'failed_tx': 0, 'retry_tx': 0,
            'throughput': 0.0, 'elapsed_time': 0, 'current_status': 'running',
            'start_time': datetime.now().isoformat(), 'error_count': 0,
            'asset_errors': 0, 'balance_errors': 0, 'checksum_errors': 0, 'success_rate': 0.0,
            'real_tx': 0, 'sim_tx': 0,
            'target_tx': num_wallets * sends_per,  # Will be overridden for hyper mode below
            'phase': 'starting', 'peak_throughput': 0.0
        }
        # For hyper/blazing mode, target = rate * duration
        if use_hyper or use_blazing:
            target_rate = int(data.get('target_rate', 250000 if use_blazing else 25000))
            duration = int(data.get('duration', 60))
            state['metrics']['target_tx'] = target_rate * duration
        state['wallets']['total'] = _initial_wallet_count
        for k in state['history']:
            state['history'][k].clear()
        _batch_tracker['seen_batches'].clear()
        _batch_tracker['success_count'] = 0
        _batch_tracker['fail_count'] = 0
        _transaction_log.clear()

        env = os.environ.copy()
        env.update({
            'PYTHONUNBUFFERED': '1', 'LOG_DIR': LOGS_DIR,
            'CONCURRENCY': str(workers), 'NUM_WALLETS': str(num_wallets),
            'SENDS_PER_WALLET': str(sends_per), 'MAX_WORKERS': str(workers),
            'RATE_LIMIT_DELAY': str(rate_delay),
            'TARGET_TX': str(num_wallets * sends_per),
            'REAL_WORKERS': str(data.get('real_workers', 100)),
            'SIM_WORKERS': str(data.get('sim_workers', 80)),
            'TARGET_RATE': str(data.get('target_rate', 25000)),
            'DURATION': str(data.get('duration', 60))
        })

        if use_ultra and os.path.exists(ultra_script):
            cmd = [python_bin, script_path]
            total_tx = num_wallets * sends_per
            state['metrics']['target_tx'] = total_tx
        elif use_mass_transfer:
            recipients_file = os.path.join(WORKSPACE, 'stress_test_recipients.csv')
            wallets_csv = os.path.join(WORKSPACE, 'real_wallets_2000_details.csv')
            if not os.path.exists(wallets_csv):
                return jsonify({'success': False, 'error': f'Wallets CSV not found: {wallets_csv}'}), 500
            addresses = []
            with open(wallets_csv, 'r') as f:
                reader = csv.DictReader(f)
                for i, row in enumerate(reader):
                    if i >= num_wallets: break
                    addr = row.get('address', '').strip()
                    if addr: addresses.append(addr)
            if not addresses:
                return jsonify({'success': False, 'error': 'No addresses in CSV'}), 500
            with open(recipients_file, 'w', newline='') as f:
                writer = csv.writer(f)
                for addr in addresses:
                    for _ in range(sends_per):
                        writer.writerow([addr, '1'])
            cmd = [python_bin, script_path, recipients_file]
            total_tx = len(addresses) * sends_per
        else:
            cmd = [python_bin, script_path]
            total_tx = num_wallets * sends_per

        log_fh = open(LOG_FILE_PATH, 'a')
        proc = subprocess.Popen(cmd, cwd=WORKSPACE, stdout=log_fh, stderr=subprocess.STDOUT, text=True, bufsize=1, env=env)

        time.sleep(0.5)
        if proc.poll() is not None:
            log_fh.close()
            state['metrics']['current_status'] = 'error'
            return jsonify({'success': False, 'error': f'Process crashed (code {proc.returncode})', 'logs': tail_log(LOG_FILE_PATH, 50)}), 500

        def monitor():
            proc.wait()
            log_fh.close()
            state['metrics']['current_status'] = 'completed' if proc.returncode == 0 else 'error'
            if 'stress_test' in state['processes']:
                state['processes']['stress_test']['status'] = state['metrics']['current_status']
        threading.Thread(target=monitor, daemon=True).start()

        state['processes']['stress_test'] = {
            'pid': proc.pid, 'status': 'running',
            'start_time': datetime.now().isoformat(),
            'config': {'wallets': num_wallets, 'sends': sends_per, 'workers': workers}
        }
        return jsonify({'success': True, 'pid': proc.pid, 'total_tx': total_tx, 'message': f'Started PID {proc.pid}'})
    except Exception as e:
        logger.exception(f"Start error: {e}")
        state['metrics']['current_status'] = 'error'
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/control/stop', methods=['POST'])
def stop_test():
    try:
        for pattern in ['blazing_transfer', 'hyper_transfer', 'turbo_transfer', 'single_transfer',
                        'ultra_stress', 'limited_stress_test', 'mass_transfer']:
            subprocess.run(['pkill', '-f', pattern], check=False)
        state['metrics']['current_status'] = 'stopped'
        state['processes']['stress_test'] = {'status': 'stopped'}
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/wallets/status')
def wallet_status():
    csv_path = os.path.join(WORKSPACE, 'real_wallets_2000_details.csv')
    total = count_csv_rows(csv_path)
    return jsonify({
        'total': total, 'loaded': state['wallets']['loaded'],
        'valid': state['wallets']['valid'], 'funded': state['wallets']['funded'],
        'depleted': state['wallets']['depleted']
    })


@app.route('/api/wallets/preview')
def wallet_preview():
    limit = request.args.get('limit', 20, type=int)
    csv_path = os.path.join(WORKSPACE, 'real_wallets_2000_details.csv')
    wallets = []
    try:
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                if i >= limit: break
                wallets.append({'address': row.get('address', ''), 'status': 'active'})
    except Exception:
        pass
    return jsonify({'wallets': wallets, 'count': len(wallets)})


@app.route('/api/wallets/all')
def wallet_all():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    search = request.args.get('search', '').strip().lower()
    csv_path = os.path.join(WORKSPACE, 'real_wallets_2000_details.csv')
    wallets = []
    try:
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                addr = row.get('address', '').strip()
                if search and search not in addr.lower():
                    continue
                wallets.append({
                    'index': i + 1,
                    'address': addr,
                    'public_key': row.get('public_key', '')[:12] + '...' if row.get('public_key', '') else '',
                    'status': 'active'
                })
    except Exception:
        pass
    total = len(wallets)
    start = (page - 1) * per_page
    end = start + per_page
    return jsonify({
        'wallets': wallets[start:end],
        'total': total,
        'page': page,
        'per_page': per_page,
        'total_pages': (total + per_page - 1) // per_page
    })


@app.route('/api/transactions')
def get_transactions():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    # Also parse from log if _transaction_log is empty but log exists
    txs = list(_transaction_log)
    if not txs and os.path.exists(LOG_FILE_PATH):
        try:
            with open(LOG_FILE_PATH, 'r', errors='ignore') as f:
                for line in f:
                    # Parse batch mass transfers
                    if 'Batch' in line and 'TX:' in line and '✓' in line:
                        bm = re.search(r'Batch\s+(\d+):\s+(\d+)\s+recipients', line)
                        tm = re.search(r'TX:\s*([A-Za-z0-9]{30,50})', line)
                        ts_m = re.search(r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})', line)
                        if bm and tm:
                            txs.append({
                                'batch': int(bm.group(1)),
                                'recipients': int(bm.group(2)),
                                'tx_id': tm.group(1),
                                'timestamp': ts_m.group(1) if ts_m else '',
                                'status': 'confirmed'
                            })
                    # Parse single transfers: "✓ TX #N/M ... | TX: hash"
                    elif 'TX #' in line and 'to:' in line and 'TX:' in line and '✓' in line:
                        nm = re.search(r'TX #(\d+)/', line)
                        tm = re.search(r'TX:\s*([A-Za-z0-9]{30,50})', line)
                        to_m = re.search(r'to:\s*(\S+)', line)
                        ts_m = re.search(r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})', line)
                        if nm and tm:
                            txs.append({
                                'batch': int(nm.group(1)),
                                'recipients': 1,
                                'tx_id': tm.group(1),
                                'timestamp': ts_m.group(1) if ts_m else '',
                                'status': 'confirmed'
                            })
            # Deduplicate by tx_id
            seen = set()
            unique = []
            for tx in txs:
                if tx['tx_id'] and tx['tx_id'] not in seen:
                    seen.add(tx['tx_id'])
                    unique.append(tx)
            txs = unique
        except Exception:
            pass
    total = len(txs)
    start = (page - 1) * per_page
    end = start + per_page
    return jsonify({
        'transactions': txs[start:end],
        'total': total,
        'page': page,
        'per_page': per_page,
        'total_pages': max(1, (total + per_page - 1) // per_page)
    })


@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found', 'path': request.path}), 404


if __name__ == '__main__':
    os.makedirs(os.path.join(WORKSPACE, 'templates'), exist_ok=True)
    os.makedirs(os.path.join(WORKSPACE, 'static'), exist_ok=True)
    if not os.path.exists(LOG_FILE_PATH):
        open(LOG_FILE_PATH, 'w').close()

    print("\n" + "=" * 60)
    print("🎛️  DecentralChain Stress Test Dashboard")
    print("=" * 60)
    print(f"🌐 Open: http://localhost:8888")
    print(f"📊 Log file: {LOG_FILE_PATH}")
    print("=" * 60 + "\n")

    app.run(debug=False, host='0.0.0.0', port=8888, threaded=True)
