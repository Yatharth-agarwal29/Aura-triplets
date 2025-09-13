Smart Worker Safety Helmet

Developed by: AURA Triplets | Award: 1st Runner-Up at hacxerve 2.0

🚀 Overview

The Smart Worker Safety Helmet is a comprehensive IoT-based system designed to enhance the safety and security of industrial workers. By integrating a network of environmental and biometric sensors directly into a standard safety helmet, our platform provides real-time monitoring of both the worker's health and their immediate surroundings. This data is transmitted wirelessly to a centralized web dashboard, empowering supervisors with actionable insights to prevent accidents and respond instantly to emergencies.

✨ Key Features
Real-Time Data Monitoring: Live feed of all sensor data accessible through a secure web dashboard.

Environmental Hazard Detection:
  MQ-2: Detects LPG, smoke, and combustible gases.
  MQ-7: Monitors for carbon monoxide (CO) concentrations.
  MQ-135: Senses air quality and the presence of harmful gases like ammonia and benzene.

Worker Vitals & Status:
  Fall Detection: 
  		Instantly alerts supervisors if a worker suffers a fall.
  		SpO₂ & Heart Rate: Monitors blood oxygen saturation and pulse.

Centralized Dashboard: 
	An intuitive web interface for managing projects (work sites) and individual workers, and for visualizing live and historical data.
	Wireless Communication: Robust and long-range data transmission from the helmet to the base station.

🛠️ System Architecture & Data Transmission
		The system operates in a continuous loop of data collection, transmission, and visualization. A key component of this architecture is the HC-12 wireless transceiver module, which enables reliable long-			range communication between the helmet and the central server.

How it Works:
  Data Acquisition: 
  		The microcontroller (e.g., Arduino Nano/ESP32) integrated into the helmet collects data from all connected sensors (MQ series, fall sensor, SpO₂/heart rate, etc.).

Wireless Transmission (HC-12):
  The processed data packet is sent from the microcontroller to the helmet's onboard HC-12 module via a serial (UART) connection.
  This HC-12 module, acting as a transmitter, sends the data wirelessly over a 433MHz frequency. This frequency is excellent for achieving long-range communication (up to 1km in open air) and penetrating common workplace obstacles.

Data Reception:

  A second HC-12 module, acting as a receiver, is connected to a computer or a Raspberry Pi at the base station.
  This receiver captures the wireless signal and outputs the data packet through its serial connection to the connected device.

Backend Processing:

  The data is read by a Python script which then forwards it to our Flask web server.
  The Flask application processes the incoming data, updates the database, and uses WebSockets to push the live information to all connected dashboard clients.
  Visualization: Supervisors view the updated, real-time worker status and environmental conditions on the web dashboard from any authorized device.

💻 Technology Stack
  Hardware:  	Arduino/ESP32, MQ-2, MQ-7, MQ-135 Gas Sensors, MPU-6050 (for fall detection), MAX30100 (for SpO₂/Heart Rate), GPS Module.
  
  Wireless Communication: HC-12 SI4463 Wireless Transceiver Module (433MHz)
  
  Backend: Python (Flask)
  
  Frontend: HTML, Tailwind CSS, JavaScript

🔧 Setup and Installation
Clone the Repository:

 	 git clone "https://github.com/Yatharth-agarwal29/Aura-triplets"

  You can also reffer this post :
  
  linkedin :- https://www.linkedin.com/posts/yatharth-agarwal-77b281288_we-are-beyond-excited-to-share-that-our-activity-7372655149724528640-p87zutm_source=social_share_send&utm_medium=member_desktop_web&rcm=ACoAAEXOqw8BDpOtoQZDnd1G1obVvbdPEMbv8FA

Install Dependencies:
  pip install -r requirements.txt

Hardware Setup:
  Assemble the helmet with all sensors connected to the microcontroller.
  Connect the receiver HC-12 module to the computer running the server.

Run the Application:
         	 python app.py

Navigate to  http://127.0.0.1:5000 in your web browser.

👥 Team
This project was proudly developed by AURA Triplets.


