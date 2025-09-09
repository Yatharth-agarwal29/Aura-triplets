import pandas as pd
import os
import random
import uuid
from flask import Flask, request, redirect, url_for, session, render_template, jsonify ,render_template_string
import time
import threading
import serial

SERIAL_PORT = 'COM6'
BAUD_RATE = 9600

# --- Global Variables ---
latest_data = {
    "values": [0.0] * 9
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
                        parts = [p.strip() for p in line.split(',')]
                        
                        if len(parts) == 9:
                            with data_lock:
                                latest_data["values"] = parts
                        else:
                            print(f"⚠️ Warning: Received {len(parts)} values, expected 9. Data: '{line}'")
                    
                    except (ValueError, IndexError) as e:
                        print(f"❌ Error parsing data: '{line}'. Reason: {e}")

        except serial.SerialException:
            print(f"🔌 Port {SERIAL_PORT} not found or disconnected. Retrying in 5 seconds...")
            if ser and ser.is_open:
                ser.close()
            time.sleep(5)

# --- Flask App Setup ---
app = Flask(__name__)
# A secret key is required to use Flask sessions
app.secret_key = 'a_very_secret_key_for_this_app'

# --- Configuration ---
DATABASE_FILE = 'users.json'

# --- Helper Functions for Data Handling ---
def load_users():
    """
    Loads user data from a JSON file into a pandas DataFrame.
    If the file doesn't exist, it creates an empty DataFrame.
    """
    if os.path.exists(DATABASE_FILE) and os.path.getsize(DATABASE_FILE) > 0:
        df = pd.read_json(DATABASE_FILE)
    else:
        # Create a new, empty DataFrame with the required columns
        df = pd.DataFrame(columns=['unique_id', 'username', 'password', 'boxes'])
    return df

def save_users(df):
    """
    Saves the pandas DataFrame back to the JSON file in records format.
    """
    df.to_json(DATABASE_FILE, orient='records', indent=4)

def generate_unique_id(df):
    """
    Generates a unique 6-digit ID that is not already in the DataFrame.
    """
    if 'unique_id' not in df.columns:
        return random.randint(100000, 999999)
    existing_ids = set(df['unique_id'].tolist())
    while True:
        new_id = random.randint(100000, 999999)
        if new_id not in existing_ids:
            return new_id

def find_box_by_id(box_list, box_id):
    """
    Recursively searches for a box with a specific ID in a list of boxes.
    """
    for box in box_list:
        if box.get('id') == box_id:
            return box
        found = find_box_by_id(box.get('sub_boxes', []), box_id)
        if found:
            return found
    return None

def find_and_add_sub_box(box_list, parent_id, new_sub_box):
    """
    Recursively finds the parent box by its ID and adds a new sub-box.
    """
    for box in box_list:
        if box.get('id') == parent_id:
            if 'sub_boxes' not in box:
                box['sub_boxes'] = []
            box['sub_boxes'].append(new_sub_box)
            return True
        if find_and_add_sub_box(box.get('sub_boxes', []), parent_id, new_sub_box):
            return True
    return False

#########################################################

# --- HTML Template with JavaScript ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Live Sensor Data</title>

    <script src="https://cdn.tailwindcss.com"></script>

    <script>
      tailwind.config = {
        theme: {
          extend: {
            colors: {
              'light-gold': '#f6cf9a',
              'dark-slate': '#474454',
              'medium-slate': '#76737c',
              'muted-tan': '#d0bc8f',
              'terracotta-rose': '#c0786a',
            }
          }
        }
      }
    </script>

    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700&display=swap" rel="stylesheet">
    <style>
      body { font-family: 'Inter', sans-serif; }
    </style>
</head>
<body class="bg-dark-slate flex items-center justify-center min-h-screen">

    <div class="bg-white p-6 sm:p-8 rounded-xl shadow-lg w-full max-w-md">
        
        <h1 class="text-3xl font-bold text-center text-terracotta-rose mb-6">
            🔴 Live Sensor Feed
        </h1>
        
        <ul id="sensor-list" class="space-y-3">
        </ul>

    </div>

    <!-- 🚨 Evacuation Popup Modal -->
    <div id="evac-modal" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center hidden">
      <div class="bg-white p-6 rounded-xl shadow-lg max-w-sm w-full">
        <h2 class="text-xl font-bold text-red-600 mb-4">⚠️ Emergency Warning</h2>
        <p class="mb-6 text-dark-slate">Do you want workers to evacuate?</p>
        <div class="flex justify-end space-x-4">
          <button id="btn-no" class="px-4 py-2 bg-gray-300 rounded-lg hover:bg-gray-400">No</button>
          <button id="btn-yes" class="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700">Yes</button>
        </div>
      </div>
    </div>

    <script>
        const sensorLabels = [
            "ID", "MQ2", "MQ7", "MQ135", "Fall dec", 
            "X-cor", "Y-cor", "SP-O₂", "Heart rate"
        ];

        let popupShown = false; // 🚨 Flag to avoid repeated popups

        // Show/hide popup functions
        function showEvacModal() {
            if (!popupShown) {
                document.getElementById('evac-modal').classList.remove('hidden');
                popupShown = true; // mark popup as shown
            }
        }
        function hideEvacModal() {
            document.getElementById('evac-modal').classList.add('hidden');
        }

        // Button actions
        document.addEventListener("DOMContentLoaded", () => {
            document.getElementById("btn-yes").addEventListener("click", () => {
                alert("🚨 Evacuation initiated!");
                hideEvacModal();
            });
            document.getElementById("btn-no").addEventListener("click", () => {
                hideEvacModal();
            });
        });

        function updateSensorValues() {
            fetch('/data')
                .then(response => response.json())
                .then(data => {
                    const sensorList = document.getElementById('sensor-list');
                    sensorList.innerHTML = ''; // Clear previous data

                    data.values.forEach((value, index) => {
                        // Create the list item with Tailwind classes
                        const listItem = document.createElement('li');
                        listItem.className = 'flex justify-between items-center py-3 border-b border-muted-tan/50';

                        // Create the label span
                        const labelSpan = document.createElement('span');
                        labelSpan.className = 'text-medium-slate';
                        labelSpan.textContent = `${sensorLabels[index]}:`;
                        
                        // Create the value span
                        const valueSpan = document.createElement('span');
                        valueSpan.className = 'font-bold text-dark-slate font-mono text-xl';
                        
                        if (!isNaN(value) && value.trim() !== "") {
                            // Numeric value
                            if (index === 0 ) { 
                                valueSpan.textContent = parseInt(value);
                                valueSpan.classList.add("text-green-800");
                            } else if (index === 4 ) { 
                                valueSpan.textContent = "NORMAL";
                                valueSpan.classList.add("text-green-800");
                            } else if (index === 7 ) { 
                                valueSpan.textContent = parseFloat(value) + "%";
                                valueSpan.classList.add("text-green-800");
                            } else {
                                valueSpan.textContent = parseFloat(value).toFixed(2);
                                valueSpan.classList.add("text-green-800");
                            }
                        } else {
                            // Non-numeric (string alert, error, etc.)
                            valueSpan.textContent = "ALERT";
                            valueSpan.classList.add("text-red-800");

                            // 🚨 Trigger popup only once
                            showEvacModal();
                        }
                        
                        listItem.appendChild(labelSpan);
                        listItem.appendChild(valueSpan);
                        sensorList.appendChild(listItem);
                    });
                })
                .catch(error => console.error('Error fetching data:', error));
        }

        updateSensorValues();
        setInterval(updateSensorValues, 1000); // Refresh every second
    </script>

</body>
</html>


"""

# --- Flask Routes ---
@app.route('/', methods=['GET', 'POST'])
def home():
    return render_template('home.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Handles both GET and POST requests for the login page.
    """
    if request.method == 'POST':
        login_username = request.form.get('login_username')
        login_id_str = request.form.get('login_unique_id')
        login_password = request.form.get('login_password')
        users_df = load_users()
        error = None

        if not login_username or not login_id_str or not login_password:
            error = "All fields are required for login."
        else:
            try:
                login_id = int(login_id_str)
                user_match = users_df[users_df['username'] == login_username]

                if user_match.empty:
                    error = "Invalid username."
                else:
                    user_data = user_match.iloc[0]
                    if user_data['unique_id'] != login_id:
                        error = "Invalid unique ID."
                    elif user_data['password'] != login_password:
                        error = "Invalid password."
                    else:
                        session['username'] = user_data['username']
                        session['unique_id'] = int(user_data['unique_id'])
                        return redirect(url_for('next_page'))

            except (ValueError, KeyError):
                error = "Invalid unique ID format."

        return render_template('login.html', error=error)

    return render_template('login.html', error=None)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """
    Handles both GET and POST requests for the signup page.
    """
    if request.method == 'POST':
        signup_username = request.form.get('signup_username')
        signup_password = request.form.get('signup_password')
        users_df = load_users()
        error = None

        if not signup_username or not signup_password:
            error = "Both username and password are required for sign up."
        elif not users_df[users_df['username'] == signup_username].empty:
            error = "Username already exists. Please choose a different one."
        else:
            new_id = generate_unique_id(users_df)
            new_user = pd.DataFrame([{
                'unique_id': new_id,
                'username': signup_username,
                'password': signup_password,
                'boxes': []  # <-- Important: Initializes the box list
            }])

            users_df = pd.concat([users_df, new_user], ignore_index=True)
            save_users(users_df)

            session['username'] = signup_username
            session['unique_id'] = int(new_id)
            return redirect(url_for('next_page'))

        return render_template('signup.html', error=error)

    return render_template('signup.html', error=None)

@app.route('/next_page')
def next_page():
    """
    Displays the main page for a logged-in user.
    """
    if 'username' not in session or 'unique_id' not in session:
        return redirect(url_for('login'))

    username = session['username']
    unique_id = session['unique_id']

    users_df = load_users()
    user_row = users_df[users_df['unique_id'] == unique_id]

    box_data = []
    if not user_row.empty:
        user_boxes = user_row.iloc[0].get('boxes')
        if isinstance(user_boxes, list):
            box_data = user_boxes

    return render_template('next_page.html',
                           username=username,
                           unique_id=unique_id,
                           boxes=box_data)

@app.route('/add_box', methods=['POST'])
def add_box():
    """
    Handles the form submission for adding a new box.
    """
    if 'unique_id' not in session:
        return redirect(url_for('login'))

    unique_id = session['unique_id']
    box_name = request.form.get('box_name')
    box_location = request.form.get('box_location')

    if not box_name or not box_location:
        return redirect(url_for('next_page'))

    users_df = load_users()
    user_row_index_list = users_df.index[users_df['unique_id'] == unique_id].tolist()

    if user_row_index_list:
        user_row_index = user_row_index_list[0]

        if 'boxes' not in users_df.columns:
            users_df['boxes'] = [[] for _ in range(len(users_df))]

        user_boxes = users_df.at[user_row_index, 'boxes']
        if not isinstance(user_boxes, list):
            user_boxes = []

        # Create a new box with a unique ID and a place for sub-boxes
        new_box = {
            'id': str(uuid.uuid4()),
            'name': box_name,
            'location': box_location,
            'sub_boxes': [],
            'type': 'parent'
        }
        user_boxes.append(new_box)

        users_df.at[user_row_index, 'boxes'] = user_boxes
        save_users(users_df)

    return redirect(url_for('next_page'))

@app.route('/add_sub_box/<parent_box_id>', methods=['POST'])
def add_sub_box(parent_box_id):
    """
    Handles adding a nested (sub) box to a parent box.
    """
    if 'unique_id' not in session:

        return redirect(url_for('login'))

    unique_id = session['unique_id']
    sub_box_name = request.form.get('box_name')
    if not sub_box_name:
        return redirect(url_for('details', box_id=parent_box_id))

    users_df = load_users()
    user_row_index_list = users_df.index[users_df['unique_id'] == unique_id].tolist()

    if user_row_index_list:
        user_row_index = user_row_index_list[0]
        user_boxes = users_df.at[user_row_index, 'boxes']
        return render_template_string(HTML_TEMPLATE)
        

    return redirect(url_for('details', box_id=parent_box_id))

@app.route('/details/<box_id>/okdata')
def okdata(box_id):
     return render_template_string(HTML_TEMPLATE)

@app.route('/details/<box_id>')
def details(box_id):
    """
    Displays the details page for a specific box, using its unique ID.
    """
    if 'unique_id' not in session:
        return redirect(url_for('login'))

    unique_id = session['unique_id']
    users_df = load_users()
    user_row = users_df[users_df['unique_id'] == unique_id]

    if not user_row.empty:
        user_boxes = user_row.iloc[0].get('boxes', [])
        box = find_box_by_id(user_boxes, box_id)
        if box:
            return render_template('details.html', box=box)

    # If the box isn't found, redirect to the main page
    return redirect(url_for('next_page'))

@app.route('/data')
def get_data():
    with data_lock:
        return jsonify(latest_data)
    
@app.route('/fetch_location/<item_id>')
def fetch_location(item_id):
    # This is still a placeholder as requested
    return render_template("fetch_location.html", item_id=item_id, location="Sensor Location Pending")

if __name__ == '__main__':
    serial_thread = threading.Thread(target=read_from_port, daemon=True)
    serial_thread.start()
    app.run(debug=True, host='0.0.0.0', use_reloader=False)
    # Run Flask with host=0.0.0.0 if you want access from other devices on network
    app.run(debug=True , port = 8000)