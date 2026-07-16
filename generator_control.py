#!/usr/bin/env python3
"""
Westinghouse 7500 Generator Control System

A comprehensive Raspberry Pi generator control system with GPIO-based automation,
solar monitoring integration, and remote access via Tailscale.

Main control application with REST API, logging, and automation capabilities.
"""

import json
import logging
import signal
import sys
import time
from datetime import datetime
from pathlib import Path
from enum import Enum

import RPi.GPIO as GPIO
from flask import Flask, request, jsonify

app = Flask(__name__)

class GeneratorState(Enum):
    OFF = "OFF"
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    STOPPING = "STOPPING"
    ERROR = "ERROR"

class GeneratorController:
    def __init__(self, config_file="config/config.json"):
        self.config_file = Path(config_file)
        self.config = self.load_config()
        
        # GPIO pin configuration
        self.control_pin = self.config.get("control_pin", 18)
        self.status_pin = self.config.get("status_pin", 23)
        self.emergency_stop_pin = self.config.get("emergency_stop_pin", 24)
        
        # File paths
        self.state_file = Path.home() / ".hermes" / "generator_state.json"
        self.log_file = Path.home() / ".hermes" / "generator_control.log"
        self.solar_log_file = Path.home() / ".hermes" / "solar_system_log.json"
        
        # System configuration
        self.api_port = self.config.get("api_port", 8080)
        self.api_host = self.config.get("api_host", "0.0.0.0")
        self.generator_id = self.config.get("generator_id", "westinghouse_7500")
        
        # Setup logging
        self.setup_logging()
        
        # Initialize GPIO
        self.setup_gpio()
        
        # Load persistent state
        self.state = self.load_state()
        
    def load_config(self):
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"Failed to load config: {e}")
        
        # Default configuration
        return {
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
            "weather_check_interval": 300
        }
    
    def setup_logging(self):
        log_level = getattr(logging, self.config.get("log_level", "INFO").upper())
        
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # Create log directory
        self.log_file.parent.mkdir(exist_ok=True)
    
    def setup_gpio(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.control_pin, GPIO.OUT)
        GPIO.setup(self.status_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        GPIO.setup(self.emergency_stop_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        
        # Ensure control pin is initially low
        GPIO.output(self.control_pin, GPIO.LOW)
    
    def load_state(self):
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"Failed to load state: {e}")
        
        # Default state
        return {
            "state": GeneratorState.OFF.value,
            "last_start_time": None,
            "last_stop_time": None,
            "start_count": 0,
            "error_count": 0,
            "manual_intervention_required": False
        }
    
    def save_state(self):
        try:
            self.state_file.parent.mkdir(exist_ok=True)
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save state: {e}")
    
    def is_generator_running(self):
        try:
            return GPIO.input(self.status_pin) == GPIO.HIGH
        except Exception as e:
            self.logger.error(f"Error checking generator status: {e}")
            return False
    
    def emergency_stop_activated(self):
        return GPIO.input(self.emergency_stop_pin) == GPIO.HIGH
    
    def start_generator(self, user_initiated=True):
        if self.state["state"] == GeneratorState.RUNNING.value:
            self.logger.info("Generator is already running")
            return True, "Generator already running"
        
        if self.emergency_stop_activated():
            self.logger.error("Emergency stop activated - cannot start generator")
            self.state["state"] = GeneratorState.ERROR.value
            self.state["manual_intervention_required"] = True
            self.save_state()
            return False, "Emergency stop activated"
        
        self.logger.info(f"Starting {self.config.get('generator_name', 'Westinghouse 7500')} generator...")
        self.state["state"] = GeneratorState.STARTING.value
        self.save_state()
        
        try:
            # Send start signal
            GPIO.output(self.control_pin, GPIO.HIGH)
            self.logger.info("Start signal sent to generator")
            
            # Wait for generator to start
            timeout = self.config.get("timeout_seconds", {}).get("start", 60)
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                if self.is_generator_running():
                    self.state["state"] = GeneratorState.RUNNING.value
                    self.state["last_start_time"] = datetime.now().isoformat()
                    self.state["start_count"] += 1
                    self.logger.info("Generator started successfully")
                    self.save_state()
                    
                    # Send event to solar system
                    self.send_to_solar_system("generator_started", {
                        "timestamp": datetime.now().isoformat(),
                        "generator_id": self.generator_id,
                        "user_initiated": user_initiated
                    })
                    
                    return True, "Generator started successfully"
                
                time.sleep(2)
            
            # Timeout reached
            self.logger.error("Generator start timeout")
            self.state["state"] = GeneratorState.ERROR.value
            self.state["error_count"] += 1
            self.save_state()
            return False, "Generator start timeout"
            
        except Exception as e:
            self.logger.error(f"Error starting generator: {e}")
            self.state["state"] = GeneratorState.ERROR.value
            self.state["error_count"] += 1
            self.save_state()
            return False, f"Error: {str(e)}"
        finally:
            GPIO.output(self.control_pin, GPIO.LOW)
    
    def stop_generator(self, user_initiated=True):
        if self.state["state"] != GeneratorState.RUNNING.value:
            self.logger.info(f"Generator is not running (state: {self.state['state']})")
            return True, "Generator not running"
        
        self.logger.info("Stopping generator...")
        self.state["state"] = GeneratorState.STOPPING.value
        self.save_state()
        
        try:
            # Send stop signal
            GPIO.output(self.control_pin, GPIO.HIGH)
            self.logger.info("Stop signal sent to generator")
            
            # Wait for generator to stop
            timeout = self.config.get("timeout_seconds", {}).get("stop", 120)
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                if not self.is_generator_running():
                    self.state["state"] = GeneratorState.OFF.value
                    self.state["last_stop_time"] = datetime.now().isoformat()
                    self.logger.info("Generator stopped successfully")
                    self.save_state()
                    
                    # Send event to solar system
                    run_time = 0
                    if self.state["last_start_time"]:
                        start_dt = datetime.fromisoformat(self.state["last_start_time"])
                        run_time = (datetime.now() - start_dt).total_seconds()
                    
                    self.send_to_solar_system("generator_stopped", {
                        "timestamp": datetime.now().isoformat(),
                        "generator_id": self.generator_id,
                        "run_time_seconds": run_time,
                        "user_initiated": user_initiated
                    })
                    
                    return True, "Generator stopped successfully"
                
                time.sleep(2)
            
            # Timeout reached
            self.logger.warning("Generator stop timeout - may still be running")
            self.state["state"] = GeneratorState.RUNNING.value
            self.save_state()
            return False, "Generator stop timeout"
            
        except Exception as e:
            self.logger.error(f"Error stopping generator: {e}")
            self.state["state"] = GeneratorState.ERROR.value
            self.save_state()
            return False, f"Error: {str(e)}"
        finally:
            GPIO.output(self.control_pin, GPIO.LOW)
    
    def emergency_stop(self):
        try:
            self.logger.warning("EMERGENCY STOP ACTIVATED")
            GPIO.output(self.control_pin, GPIO.HIGH)
            self.state["state"] = GeneratorState.OFF.value
            self.state["last_stop_time"] = datetime.now().isoformat()
            self.save_state()
            
            self.send_to_solar_system("emergency_stop", {
                "timestamp": datetime.now().isoformat(),
                "generator_id": self.generator_id,
                "reason": "manual_emergency_stop"
            })
            
            return True, "Emergency stop activated"
        except Exception as e:
            self.logger.error(f"Error during emergency stop: {e}")
            return False, f"Emergency stop error: {str(e)}"
        finally:
            GPIO.output(self.control_pin, GPIO.LOW)
    
    def send_to_solar_system(self, event_type, data):
        try:
            # Create solar event structure
            event = {
                "event_type": event_type,
                "timestamp": datetime.now().isoformat(),
                "generator_id": self.generator_id,
                "data": data,
                "source": "raspberry_pi_generator_controller"
            }
            
            # Log to solar system log file
            with open(self.solar_log_file, 'a') as f:
                f.write(json.dumps(event) + '\n')
            
            self.logger.info(f"Solar system event logged: {event_type}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to send event to solar system: {e}")
            return False
    
    def get_status_report(self):
        status = {
            "current_state": self.state["state"],
            "is_running": self.is_generator_running(),
            "emergency_stop_activated": self.emergency_stop_activated(),
            "last_start_time": self.state["last_start_time"],
            "last_stop_time": self.state["last_stop_time"],
            "total_starts": self.state["start_count"],
            "error_count": self.state["error_count"],
            "manual_intervention_required": self.state["manual_intervention_required"],
            "timestamp": datetime.now().isoformat(),
            "generator_id": self.generator_id
        }
        
        # Calculate runtime if running
        if self.state["state"] == GeneratorState.RUNNING.value and self.state["last_start_time"]:
            start_time = datetime.fromisoformat(self.state["last_start_time"])
            runtime = (datetime.now() - start_time).total_seconds()
            status["runtime_seconds"] = runtime
            status["runtime_formatted"] = f"{int(runtime // 3600)}h {int((runtime % 3600) // 60)}m"
        
        return status

def setup_routes(controller):
    @app.route('/api/start', methods=['POST'])
    def start():
        user_initiated = request.json.get('user_initiated', True) if request.is_json else True
        success, message = controller.start_generator(user_initiated)
        return jsonify({
            "success": success,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }), 200 if success else 400
    
    @app.route('/api/stop', methods=['POST'])
    def stop():
        user_initiated = request.json.get('user_initiated', True) if request.is_json else True
        success, message = controller.stop_generator(user_initiated)
        return jsonify({
            "success": success,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }), 200 if success else 400
    
    @app.route('/api/emergency-stop', methods=['POST'])
    def emergency_stop():
        success, message = controller.emergency_stop()
        return jsonify({
            "success": success,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }), 200 if success else 400
    
    @app.route('/api/status', methods=['GET'])
    def status():
        status_report = controller.get_status_report()
        return jsonify(status_report), 200
    
    @app.route('/api/health', methods=['GET'])
    def health():
        return jsonify({
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "generator_id": controller.generator_id
        }), 200

def signal_handler(signum, frame, controller):
    controller.logger.info("Shutdown signal received, cleaning up...")
    GPIO.cleanup()
    controller.save_state()
    sys.exit(0)

def main():
    """Main entry point for the generator controller"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Westinghouse 7500 Generator Controller",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start the controller with API access
  python3 generator_control.py --daemon

  # Check generator status
  python3 generator_control.py --log-level INFO --daemon status

  # Start generator manually
  python3 generator_control.py start

  # Stop generator manually
  python3 generator_control.py stop

  # Activate emergency stop
  python3 generator_control.py emergency-stop

  # Run in foreground without Flask API
  python3 generator_control.py --no-api start

  # Check system health
  python3 generator_control.py --no-api status
        """
    )
    
    parser.add_argument(
        "action", 
        nargs='?', 
        const="start",
        help="Action to perform: start, stop, status, emergency-stop"
    )
    parser.add_argument(
        "--daemon", 
        action="store_true",
        help="Run as a daemon with Flask API"
    )
    parser.add_argument(
        "--no-api",
        action="store_true",
        help="Run without Flask API (for command-line usage)"
    )
    parser.add_argument(
        "--config",
        default="config/config.json",
        help="Path to configuration file"
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Log level"
    )
    
    args = parser.parse_args()
    
    # Create controller instance
    controller = GeneratorController(args.config)
    
    # Override log level from command line
    controller.logger.setLevel(getattr(logging, args.log_level))
    
    # Setup signal handlers
    def signal_handler_wrapper(signum, frame):
        signal_handler(signum, frame, controller)
    
    signal.signal(signal.SIGTERM, signal_handler_wrapper)
    signal.signal(signal.SIGINT, signal_handler_wrapper)
    
    try:
        if args.action == "start":
            if args.no_api:
                # Run in command-line mode without Flask API
                success, message = controller.start_generator(user_initiated=True)
                print(f"Start {'succeeded' if success else 'failed'}: {message}")
                exit(0 if success else 1)
            else:
                # In daemon mode, start the generator
                if args.daemon:
                    success, message = controller.start_generator(user_initiated=True)
                    if not success:
                        print(f"Failed to start generator: {message}")
                        exit(1)
                else:
                    success, message = controller.start_generator(user_initiated=True)
                    print(f"Start {'succeeded' if success else 'failed'}: {message}")
                    exit(0 if success else 1)
        
        elif args.action == "stop":
            if args.no_api:
                success, message = controller.stop_generator(user_initiated=True)
                print(f"Stop {'succeeded' if success else 'failed'}: {message}")
                exit(0 if success else 1)
            else:
                success, message = controller.stop_generator(user_initiated=True)
                print(f"Stop {'succeeded' if success else 'failed'}: {message}")
                exit(0 if success else 1)
        
        elif args.action == "emergency-stop":
            success, message = controller.emergency_stop()
            print(f"Emergency stop {'succeeded' if success else 'failed'}: {message}")
            exit(0 if success else 1)
        
        elif args.action == "status" or args.action is None:
            if args.no_api:
                status = controller.get_status_report()
                print(json.dumps(status, indent=2))
                exit(0)
            else:
                # If no action specified and using daemon mode, start the controller with API
                setup_routes(controller)
                controller.logger.info(f"Starting generator controller API on {controller.api_host}:{controller.api_port}")
                controller.logger.info(f"Health check: http://{controller.api_host}:{controller.api_port}/api/health")
                app.run(host=controller.api_host, port=controller.api_port, debug=False)
        
        else:
            parser.error(f"Invalid action: {args.action}")
            
    except KeyboardInterrupt:
        controller.logger.info("Generator control interrupted by user")
    except Exception as e:
        controller.logger.error(f"Unexpected error: {e}")
        exit(1)
    finally:
        GPIO.cleanup()

if __name__ == "__main__":
    main()