import time
import serial
import threading
from flask import Flask, jsonify, render_template_string

# --- Configuration ---
SERIAL_PORT = 'COM6'
BAUD_RATE = 9600

# --- Global Variables ---
latest_data = {
    "values": [0.0] * 7
}
data_lock = threading.Lock()

# --- Background Task for Reading Serial Data ---
def read_from_port():
    """
    Reads data from the serial port in a background thread.
    This function runs in a continuous loop.
    """
    global latest_data
    
    while True:
        ser = None
        try:
            ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
            print(f"✅ Successfully connected to {SERIAL_PORT}")
            
            while True:
                if not ser.is_open:
                    break
                
                line = ser.readline().decode('utf-8').strip()

                if line:
                    try:
                        parts = [float(p) for p in line.split(',')]
                        
                        if len(parts) == 7:
                            with data_lock:
                                latest_data["values"] = parts
                        else:
                            print(f"⚠️ Warning: Received {len(parts)} values, expected 7. Data: '{line}'")
                    
                    except (ValueError, IndexError) as e:
                        print(f"❌ Error parsing data: '{line}'. Reason: {e}")

        except serial.SerialException:
            print(f"🔌 Port {SERIAL_PORT} not found or disconnected. Retrying in 5 seconds...")
            if ser and ser.is_open:
                ser.close()
            time.sleep(5)

# --- Flask Web Application ---
app = Flask(__name__)

# --- HTML Template with JavaScript ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Live Sensor Data</title>
    <style>
        body { font-family: 'Segoe UI', Arial, sans-serif; display: grid; place-content: center; min-height: 100vh; background-color: #f0f2f5; color: #1c1c1c;}
        .container { 
            background-color: #ffffff; 
            padding: 2rem; 
            border-radius: 12px; 
            box-shadow: 0 6px 20px rgba(0,0,0,0.1); 
            width: 400px;
            border: 1px solid #e1e4e8;
        }
        h1 { text-align: center; color: #0366d6; margin-top: 0;}
        ul { list-style: none; padding: 0; }
        li { 
            display: flex; 
            justify-content: space-between; 
            padding: 0.75rem 0.25rem;
            border-bottom: 1px solid #e1e4e8;
            font-size: 1.2rem;
        }
        li:last-child { border-bottom: none; }
        .label { color: #586069; }
        .value { font-weight: 600; color: #24292e; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Live Sensor Feed</h1>
        <ul id="sensor-list">
            </ul>
    </div>

    <script>
        // Define the custom labels for the sensors
        const sensorLabels = [
            "ID", "MQ2", "MQ7", "MQ135", 
            "Fall dec", "X-cor", "Y-cor"
        ];

        function updateSensorValues() {
            fetch('/data')
                .then(response => response.json())
                .then(data => {
                    const sensorList = document.getElementById('sensor-list');
                    sensorList.innerHTML = '';

                    // Loop through the values and use the sensorLabels array
                    data.values.forEach((value, index) => {
                        const listItem = document.createElement('li');
                        
                        const labelSpan = document.createElement('span');
                        labelSpan.className = 'label';
                        // Use the label from our array based on the index
                        labelSpan.textContent = `${sensorLabels[index]}:`;
                        
                        const valueSpan = document.createElement('span');
                        valueSpan.className = 'value';
                        
                        // Display the ID as an integer, others with 2 decimal places
                        if (index === 0 || index === 4) { // ID or Fall dec
                             valueSpan.textContent = parseInt(value);
                        } else {
                             valueSpan.textContent = value.toFixed(2);
                        }
                        
                        listItem.appendChild(labelSpan);
                        listItem.appendChild(valueSpan);
                        sensorList.appendChild(listItem);
                    });
                })
                .catch(error => console.error('Error fetching data:', error));
        }

        updateSensorValues();
        setInterval(updateSensorValues, 1000);
    </script>
</body>
</html>
"""

# --- Web Routes ---
@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/data')
def get_data():
    with data_lock:
        return jsonify(latest_data)

# --- Main Execution ---
if __name__ == '__main__':
    serial_thread = threading.Thread(target=read_from_port, daemon=True)
    serial_thread.start()
    
    app.run(debug=True, host='0.0.0.0', use_reloader=False)
    render_template_string(HTML_TEMPLATE)