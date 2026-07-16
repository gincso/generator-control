# Westinghouse 7500 Generator Control System

A comprehensive Raspberry Pi generator control system with GPIO-based automation, solar monitoring integration, and remote access via Tailscale.

## Overview

This repository contains a complete generator control system for the Westinghouse 7500 generator, designed to run on a Raspberry Pi. The system provides:

- Direct GPIO control for starting/stopping the generator
- Real-time monitoring and logging
- Emergency stop protection
- Solar system integration
- Remote access via Tailscale
- Automated scheduling and weather-based control

## Key Features

### Hardware Integration
- **Direct GPIO Control**: Uses Raspberry Pi GPIO pins for reliable hardware control
- **Support for Westinghouse 7500**: Specifically designed for this generator model
- **Safety Features**: Emergency stop, error handling, and state persistence

### Automation & Integration
- **Weather-Based Automation**: Automatically control generator based on weather conditions
- **Solar System Integration**: Event logging and data collection for solar monitoring
- **Tailscale Integration**: Secure remote access via zero-trust VPN
- **REST API**: Remote control via HTTP endpoints

### Monitoring & Logging
- **Comprehensive Logging**: Detailed logs to file and console
- **Status Reporting**: Real-time status reports via API
- **Event Tracking**: Detailed event logging for integration with monitoring systems

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/your-username/generator-control.git
cd generator-control

# Install dependencies
pip3 install -r requirements.txt

# Set up GPIO permissions
sudo usermod -aG gpio pi

# Configure the system
cp config/config.json.template config/config.json
nano config/config.json  # Edit with your settings

# Start the controller
python3 generator_control.py --daemon
```

### Basic Commands

```bash
# Check generator status
python3 generator_control.py --log-level INFO --daemon status

# Start generator manually
python3 generator_control.py start

# Stop generator manually
python3 generator_control.py stop

# Emergency stop
python3 generator_control.py emergency-stop

# Run in foreground without Flask API
python3 generator_control.py --no-api start

# Check system health
python3 generator_control.py --no-api status
```

### Systemd Service (Recommended)

For continuous operation, set up a systemd service:

```bash
# Create service file
cat > /etc/systemd/system/generator-controller.service << EOF
[Unit]
Description=Westinghouse 7500 Generator Controller
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/generator-control
ExecStart=/usr/bin/python3 /home/pi/generator-control/generator_control.py --daemon
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Enable and start the service
sudo systemctl daemon-reload
sudo systemctl enable generator-controller
sudo systemctl start generator-controller
sudo systemctl status generator-controller
```

## API Endpoints

The system provides a REST API for remote control via Tailscale:

```bash
# Start generator
curl -X POST http://generator.local:8080/api/start \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_TOKEN"

# Stop generator
curl -X POST http://generator.local:8080/api/stop \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_TOKEN"

# Get status
curl -X GET http://generator.local:8080/api/status \
  -H "Authorization: Bearer YOUR_API_TOKEN"

# Emergency stop
curl -X POST http://generator.local:8080/api/emergency-stop \
  -H "Authorization: Bearer YOUR_API_TOKEN"

# Health check
curl -X GET http://generator.local:8080/api/health
```

## Configuration

### Main Configuration File

Edit `config/config.json` to customize the system:

```json
{
  "generator_id": "westinghouse_7500",
  "generator_name": "Westinghouse 7500",
  "control_pin": 18,
  "status_pin": 23,
  "emergency_stop_pin": 24,
  "start_voltage_threshold": 11.5,
  "stop_voltage_threshold": 12.5,
  "timeout_seconds": {
    "start": 60,
    "stop": 120
  },
  "solar_system_endpoint": "http://solar.local/api/events",
  "tailscale_key": "",
  "tailscale_network": "generator",
  "log_level": "INFO",
  "api_port": 8080,
  "api_host": "0.0.0.0",
  "weather_api_key": "",
  "weather_check_interval": 300,
  "camera_resolution": "1920x1080",
  "max_recording_time": 30,
  "enable_night_vision": true,
  "storage_directory": "/home/pi/generator-videos",
  "backup_storage_enabled": false,
  "backup_storage_path": "/backup/generator-videos"
}
```

## Automation Scripts

### Weather-Based Automation

Create `scripts/weather_automation.py` for automatic generator control based on weather:

```python
#!/usr/bin/env python3
import requests
import json
from generator_control import GeneratorController
from datetime import datetime

class WeatherAutomation:
    def __init__(self):
        self.controller = GeneratorController()
        self.api_key = "your_weather_api_key"
        
    def get_weather_forecast(self):
        """Get weather forecast for automation decisions"""
        # API call to weather service
        # Returns forecast with sunlight, temperature, weather conditions
        
    def optimize_generator_schedule(self, weather_data):
        """Optimize generator schedule based on weather"""
        if weather_data["sunlight"] > 80:
            # Too much sun, minimize generator use
            self.controller.stop_generator()
        elif weather_data["sunlight"] < 20:
            # Not enough sun, start generator
            self.schedule_generator_start()
```

### Camera Control

Create `scripts/camera_control.py` for generator monitoring:

```python
#!/usr/bin/env python3
import cv2
import time
from datetime import datetime
from generator_control import GeneratorController

class CameraController:
    def __init__(self):
        self.camera = cv2.VideoCapture(0)
        self.generator_controller = GeneratorController()
        
    def capture_generator_footage(self):
        """Capture footage of generator operation"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"logs/generator_{timestamp}.mp4"
        
        # Start recording
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(filename, fourcc, 20.0, (640, 480))
        
        # Record for 30 seconds or until generator stops
        start_time = time.time()
        while time.time() - start_time < 30:
            ret, frame = self.camera.read()
            if not ret:
                break
                
            out.write(frame)
            cv2.imshow('Generator Monitoring', frame)
            
            # Check if generator stopped
            if self.generator_controller.state["state"] != "RUNNING":
                break
                
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
                
        out.release()
        cv2.destroyAllWindows()
        return filename
```

## Tailscale Integration

### Installation

```bash
# Install Tailscale
sudo apt install tailscale
sudo tailscale up --ssh
```

### Expose Generator Service

Configure Tailscale to expose the generator controller:

```bash
# Check Tailscale status
sudo tailscale status
# Get Tailscale IP
sudo tailscale ip -4
# Forward port 80 through Tailscale
sudo tailscale funnel on
```

Create an nginx configuration file for the Tailscale reverse proxy:

```nginx
server {
    listen 80;
    server_name generator.local;

    location /api/ {
        proxy_pass http://localhost:8080/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Solar System Integration

The generator controller integrates with solar monitoring systems:

### Event Logging

All generator events are logged to the solar system:

```json
{
  "event_type": "generator_started",
  "timestamp": "2024-01-15T14:30:00Z",
  "generator_id": "westinghouse_7500",
  "data": {
    "source": "raspberry_pi_generator_controller",
    "user_initiated": true
  }
}
```

## Automation Examples

### Cron Jobs for Scheduled Control

Add to crontab for automated generator control:

```bash
# Start generator at 6 AM daily (if needed)
0 6 * * * /usr/bin/python3 /home/pi/generator-control/scripts/weather_automation.py

# Stop generator at 6 PM daily
0 18 * * * /usr/bin/python3 /home/pi/generator-control/scripts/weather_automation.py stop

# Check generator status every 5 minutes
*/5 * * * * /usr/bin/python3 /home/pi/generator-control/generator_control.py --no-api status
```

## Troubleshooting

### Common Issues

**1. GPIO Access Denied**
```bash
# Check GPIO permissions
sudo usermod -aG gpio pi
# Reboot the system
sudo reboot
```

**2. Generator Not Starting**
- Verify wiring connections
- Check generator voltage levels  
- Ensure emergency stop is not activated

**3. Tailscale Connection Issues**
```bash
# Check Tailscale status
sudo tailscale status
# Check if generator service is available
sudo tailscale ip -4
```

**4. API Not Accessible**
- Verify Tailscale network is reachable
- Check firewall rules
- Ensure nginx proxy is running (if using)

## Monitoring and Logging

### Log Files

- **Main Logs**: `logs/generator_control.log`
- **State File**: `.hermes/generator_state.json`
- **Solar Events**: `.hermes/solar_system_log.json`

## Maintenance

### Regular Checks

```bash
# Check logs
sudo journalctl -u generator-controller -f
# View recent events
tail -f .hermes/solar_system_log.json
# Backup state
cp .hermes/generator_state.json .hermes/generator_state_backup_$(date +%Y%m%d).json
```

## Emergency Procedures

### Manual Override

For manual control:

```bash
# Stop generator manually
sudo systemctl stop generator-controller
# Start generator manually
sudo systemctl start generator-controller
# Force stop generator (use with caution)
sudo systemctl kill generator-controller
```

### Emergency Stop

In case of emergency:

```bash
# Activate emergency stop via API
curl -X POST http://generator.local:8080/api/emergency-stop
```

## Project Structure

```
generator-control/
├── generator_control.py                    # Main controller
├── config/                                 # Configuration files
│   ├── config.json                        # Main configuration
│   └── config.json.template               # Configuration template
├── scripts/                                # Automation scripts
│   ├── custom_automation.py              # Custom automation logic
│   ├── camera_control.py                 # Camera control
│   └── weather_automation.py             # Weather-based automation
├── logs/                                   # Log files
├── data/                                   # Data storage
├── .hermes/                                # Configuration and state
├── requirements.txt                        # Python dependencies
├── README.md                               # Documentation
├── LICENSE                                 # License information
└── setup.py                                # Installation script
```

## System Requirements

### Hardware

- **Raspberry Pi**: Raspberry Pi 3 or later
- **GPIO Pins**: Access to GPIO pins 18, 23, and 24
- **Storage**: At least 1GB of free space
- **Power**: Reliable power supply for Raspberry Pi

### Software

- **Operating System**: Raspberry Pi OS (64-bit)
- **Python**: 3.11 or later
- **Libraries**: RPi.GPIO, flask, requests, schedule

## Support

For support, please:

1. Check the documentation in README.md
2. Create an issue in the repository
3. Check the log files in `logs/` for error details
4. Verify GPIO connections and power supply

## License

This project is licensed under the MIT License.