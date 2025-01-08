from flask import Flask, render_template, jsonify, request
import speedtest
import psutil
import platform
from datetime import datetime
import threading
import time
import json
from collections import deque
import socket

app = Flask(__name__)

# Store historical data
speed_history = deque(maxlen=100)
system_history = deque(maxlen=100)

def get_speed(selected_server=None):
    st = speedtest.Speedtest()
    
    # Get server list and select best or specified server
    servers = st.get_servers()
    if selected_server:
        st.get_best_server([servers[selected_server]])
    else:
        st.get_best_server()
    
    # Get speeds
    download_speed = st.download() / 1_000_000  # Convert to Mbps
    upload_speed = st.upload() / 1_000_000  # Convert to Mbps
    ping = st.results.ping
    
    # Get server details
    server_info = st.results.server
    
    return {
        'download': round(download_speed, 2),
        'upload': round(upload_speed, 2),
        'ping': round(ping, 2),
        'server': {
            'name': server_info['sponsor'],
            'location': f"{server_info['name']}, {server_info['country']}",
            'latency': server_info['latency']
        }
    }

def get_detailed_system_info():
    cpu_freq = psutil.cpu_freq()
    disk = psutil.disk_usage('/')
    network_io = psutil.net_io_counters()
    
    return {
        'cpu': {
            'usage_per_cpu': psutil.cpu_percent(interval=1, percpu=True),
            'overall_usage': psutil.cpu_percent(interval=1),
            'frequency': {
                'current': round(cpu_freq.current, 2) if cpu_freq else 0,
                'min': round(cpu_freq.min, 2) if cpu_freq else 0,
                'max': round(cpu_freq.max, 2) if cpu_freq else 0
            }
        },
        'memory': {
            'total': round(psutil.virtual_memory().total / (1024 ** 3), 2),
            'used': round(psutil.virtual_memory().used / (1024 ** 3), 2),
            'percent': psutil.virtual_memory().percent
        },
        'disk': {
            'total': round(disk.total / (1024 ** 3), 2),
            'used': round(disk.used / (1024 ** 3), 2),
            'percent': disk.percent
        },
        'network': {
            'bytes_sent': network_io.bytes_sent,
            'bytes_recv': network_io.bytes_recv,
            'packets_sent': network_io.packets_sent,
            'packets_recv': network_io.packets_recv
        },
        'platform': {
            'system': platform.system(),
            'release': platform.release(),
            'version': platform.version(),
            'machine': platform.machine(),
            'processor': platform.processor()
        }
    }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/test-speed')
def test_speed():
    try:
        selected_server = request.args.get('server')
        results = get_speed(selected_server)
        
        # Store historical data
        timestamp = datetime.now()
        speed_history.append({
            'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'download': results['download'],
            'upload': results['upload'],
            'ping': results['ping']
        })
        
        return jsonify({
            **results,
            'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S')
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/system-info')
def system_info():
    try:
        info = get_detailed_system_info()
        
        # Store historical data
        system_history.append({
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'cpu_usage': info['cpu']['overall_usage'],
            'memory_percent': info['memory']['percent']
        })
        
        return jsonify(info)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/history')
def get_history():
    return jsonify({
        'speed': list(speed_history),
        'system': list(system_history)
    })

@app.route('/speedtest-servers')
def get_speedtest_servers():
    try:
        st = speedtest.Speedtest()
        servers = st.get_servers()
        server_list = []
        
        for server_id, server_info in servers.items():
            for server in server_info:
                server_list.append({
                    'id': server_id,
                    'name': server['sponsor'],
                    'location': f"{server['name']}, {server['country']}",
                    'distance': round(server['d'], 2),
                    'latency': server['latency'] if 'latency' in server else None
                })
        
        return jsonify(sorted(server_list, key=lambda x: x['distance'])[:20])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
