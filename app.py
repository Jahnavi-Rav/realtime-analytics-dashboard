from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import json
import threading
import time

app = Flask(__name__)
app.config['SECRET_KEY'] = 'analytics_dashboard_secret'
socketio = SocketIO(app, cors_allowed_origins="*")

class AnomalyDetector:
    def __init__(self, window_size=50, threshold=3):
        self.window_size = window_size
        self.threshold = threshold
        self.data_window = []
    
    def detect(self, value):
        self.data_window.append(value)
        if len(self.data_window) > self.window_size:
            self.data_window.pop(0)
        
        if len(self.data_window) < 10:
            return False
        
        mean = np.mean(self.data_window)
        std = np.std(self.data_window)
        z_score = abs((value - mean) / (std + 1e-7))
        return z_score > self.threshold

class DataStream:
    def __init__(self):
        self.base_value = 100
        self.trend = 0.1
        self.anomaly_detector = AnomalyDetector()
    
    def generate_datapoint(self):
        noise = np.random.normal(0, 5)
        spike = np.random.choice([0, 50], p=[0.97, 0.03])
        value = self.base_value + noise + spike
        self.base_value += self.trend + np.random.normal(0, 0.5)
        
        is_anomaly = self.anomaly_detector.detect(value)
        
        return {
            'timestamp': datetime.now().isoformat(),
            'value': round(value, 2),
            'is_anomaly': bool(is_anomaly)
        }

data_stream = DataStream()

def background_data_generator():
    while True:
        datapoint = data_stream.generate_datapoint()
        socketio.emit('new_data', datapoint, namespace='/')
        time.sleep(1)

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    print('Client connected')
    emit('connection_response', {'status': 'connected'})

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

@socketio.on('request_historical')
def handle_historical_request(data):
    minutes = data.get('minutes', 60)
    historical_data = []
    for i in range(minutes):
        historical_data.append(data_stream.generate_datapoint())
    emit('historical_data', {'data': historical_data})

if __name__ == '__main__':
    thread = threading.Thread(target=background_data_generator)
    thread.daemon = True
    thread.start()
    socketio.run(app, debug=True, port=5000)
