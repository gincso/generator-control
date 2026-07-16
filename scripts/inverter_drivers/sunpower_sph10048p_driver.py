#!/usr/bin/env python3
"""
Sungold SPH10048P Hybrid Inverter Driver
MODBUS RTU communication for Sungold SPH10048P 10kW hybrid solar inverter
Integrates with Raspberry Pi generator control system for comprehensive solar power management
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional
from pymodbus.client import AsyncModbusSerialClient

# Configure logging for system operations
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

class SungoldSPH10048P:
    """
    Sungold SPH10048P 10kW Hybrid Inverter Driver
    
    MODBUS RTU communication protocol implementation for Sungold's hybrid solar inverter
    with integrated battery storage and grid interaction capabilities.
    
    Key Features:
    - 10kW solar power rating with 48V DC input
    - Hybrid operation (solar + battery + grid)
    - Comprehensive power flow management
    - Real-time monitoring and logging
    - Status analysis and alerts
    
    Device Specifications:
    - Model: SPH10048P
    - Power Rating: 10kW
    - DC Input: 48V
    - Communication: MODBUS RTU RS485 (9600 baud, Even parity)
    - MODBUS Slave ID: 1 (configurable)
    """
    
    # MODBUS register map for Sungold SPH10048P inverter
    # Based on Sungold hybrid inverter MODBUS protocol specifications
    # Addresses are register numbers (1-based indexing)
    REGISTERS = {
        # ====================================================================
        # POWER MEASUREMENT REGISTERS
        # ====================================================================
        'pv_power': {
            'addr': 40001, 
            'factor': 1, 
            'unit': 'W', 
            'desc': 'PV Panel Power Output',
            'access': 'R'
        },
        'grid_power': {
            'addr': 40002, 
            'factor': 1, 
            'unit': 'W', 
            'desc': 'Power Exchange with Grid',
            'access': 'R'
        },
        'battery_soc': {
            'addr': 40003, 
            'factor': 0.1, 
            'unit': '%', 
            'desc': 'Battery State of Charge',
            'access': 'R'
        },
        'battery_voltage': {
            'addr': 40004, 
            'factor': 0.01, 
            'unit': 'V', 
            'desc': 'Battery Pack Voltage',
            'access': 'R'
        },
        'battery_current': {
            'addr': 40005, 
            'factor': 0.01, 
            'unit': 'A', 
            'desc': 'Battery Charging/Discharging Current',
            'access': 'R'
        },
        'system_voltage': {
            'addr': 40006, 
            'factor': 0.01, 
            'unit': 'V', 
            'desc': 'DC Bus Voltage',
            'access': 'R'
        },
        'system_current': {
            'addr': 40007, 
            'factor': 0.01, 
            'unit': 'A', 
            'desc': 'DC Bus Current',
            'access': 'R'
        },
        'efficiency': {
            'addr': 40008, 
            'factor': 0.1, 
            'unit': '%', 
            'desc': 'System Operating Efficiency',
            'access': 'R'
        },
        'temperature': {
            'addr': 40009, 
            'factor': 1, 
            'unit': '°C', 
            'desc': 'Inverter Heat Sink Temperature',
            'access': 'R'
        },
        
        # ====================================================================
        # ENERGY MANAGEMENT REGISTERS
        # ====================================================================
        'today_energy': {
            'addr': 40010, 
            'factor': 0.01, 
            'unit': 'kWh', 
            'desc': 'Energy Generated Today',
            'access': 'R'
        },
        'total_energy': {
            'addr': 40011, 
            'factor': 0.01, 
            'unit': 'kWh', 
            'desc': 'Cumulative Energy Generated',
            'access': 'R'
        },
        'peak_power_today': {
            'addr': 40012, 
            'factor': 1, 
            'unit': 'W', 
            'desc': 'Maximum Power Output Today',
            'access': 'R'
        },
        'grid_import_today': {
            'addr': 40013, 
            'factor': 0.01, 
            'unit': 'kWh', 
            'desc': 'Grid Power Imported Today',
            'access': 'R'
        },
        'grid_export_today': {
            'addr': 40014, 
            'factor': 0.01, 
            'unit': 'kWh', 
            'desc': 'Grid Power Exported Today',
            'access': 'R'
        },
        
        # ====================================================================
        # SYSTEM STATUS REGISTERS
        # ====================================================================
        'operating_mode': {
            'addr': 40015, 
            'factor': 1, 
            'unit': '', 
            'desc': 'Operating Mode',
            'access': 'R'
        },
        'charge_controller': {
            'addr': 40016, 
            'factor': 1, 
            'unit': '', 
            'desc': 'Charge Controller Status',
            'access': 'R'
        },
        'grid_connection': {
            'addr': 40017, 
            'factor': 1, 
            'unit': '', 
            'desc': 'Grid Connection Status',
            'access': 'R'
        },
        'inverter_status': {
            'addr': 40018, 
            'factor': 1, 
            'unit': '', 
            'desc': 'Inverter Status',
            'access': 'R'
        },
        'battery_protection': {
            'addr': 40019, 
            'factor': 1, 
            'unit': '', 
            'desc': 'Battery Protection Status',
            'access': 'R'
        },
        
        # ====================================================================
        # DIAGNOSTIC & PERFORMANCE REGISTERS
        # ====================================================================
        'grid_frequency': {
            'addr': 40020, 
            'factor': 0.01, 
            'unit': 'Hz', 
            'desc': 'Grid Frequency',
            'access': 'R'
        },
        'pv_voltage': {
            'addr': 40021, 
            'factor': 0.01, 
            'unit': 'V', 
            'desc': 'PV Panel Voltage',
            'access': 'R'
        },
        'pv_current': {
            'addr': 40022, 
            'factor': 0.01, 
            'unit': 'A', 
            'desc': 'PV Panel Current',
            'access': 'R'
        },
        'load_power': {
            'addr': 40023, 
            'factor': 1, 
            'unit': 'W', 
            'desc': 'Load Power Consumption',
            'access': 'R'
        },
        'battery_discharge_power': {
            'addr': 40024, 
            'factor': 1, 
            'unit': 'W', 
            'desc': 'Battery Discharge Power',
            'access': 'R'
        },
        'battery_charge_power': {
            'addr': 40025, 
            'factor': 1, 
            'unit': 'W', 
            'desc': 'Battery Charge Power',
            'access': 'R'
        },
        'ambient_temperature': {
            'addr': 40026, 
            'factor': 1, 
            'unit': '°C', 
            'desc': 'Ambient Temperature',
            'access': 'R'
        },
        'heat_sink_temperature': {
            'addr': 40027, 
            'factor': 1, 
            'unit': '°C', 
            'desc': 'Heat Sink Temperature',
            'access': 'R'
        },
        'last_fault_code': {
            'addr': 40028, 
            'factor': 1, 
            'unit': 'code', 
            'desc': 'Last Fault Code',
            'access': 'R'
        },
        'total_fault_times': {
            'addr': 40029, 
            'factor': 1, 
            'unit': 'count', 
            'desc': 'Total Fault Occurrences',
            'access': 'R'
        },
        'daily_runtime': {
            'addr': 40030, 
            'factor': 1, 
            'unit': 'h', 
            'desc': 'Daily Operating Hours',
            'access': 'R'
        },
        
        # ====================================================================
        # SYSTEM CONFIGURATION REGISTERS
        # ====================================================================
        'rated_power': {
            'addr': 40031, 
            'factor': 1, 
            'unit': 'W', 
            'desc': 'System Rated Power',
            'access': 'R'
        },
        'max_output_power': {
            'addr': 40032, 
            'factor': 1, 
            'unit': 'W', 
            'desc': 'Maximum Output Power',
            'access': 'R'
        },
        'battery_capacity': {
            'addr': 40033, 
            'factor': 1, 
            'unit': 'kWh', 
            'desc': 'Battery Energy Storage Capacity',
            'access': 'R'
        },
        'install_area': {
            'addr': 40034, 
            'factor': 1, 
            'unit': '', 
            'desc': 'Installation Area Type',
            'access': 'R'
        },
        'backup_time': {
            'addr': 40035, 
            'factor': 1, 
            'unit': 'h', 
            'desc': 'Backup Operating Time',
            'access': 'R'
        },
    }
    
    # Operating modes mapping for SPH10048P
    OPERATING_MODES = {
        0: 'Self-Use Mode',
        1: 'Self-Sufficiency Mode (Hybrid)',
        2: 'Feed-in Mode (Grid-Tie)'
    }
    
    # System status codes
    STATUS_CODES = {
        0: 'Normal Operation',
        1: 'Warning Condition',
        2: 'Fault/Serious Error'
    }
    
    def __init__(self, port: str = '/dev/ttyUSB0', baudrate: int = 9600,
                 slave_id: int = 1, timeout: int = 2):
        """
        Initialize Sungold SPH10048P inverter communication interface.
        
        Args:
            port (str): Serial port path for MODBUS communication
            baudrate (int): Communication baud rate (default: 9600)
            slave_id (int): MODBUS slave address (default: 1)
            timeout (int): Communication timeout in seconds (default: 2)
        
        Raises:
            ValueError: If invalid parameters are provided
        """
        if baudrate not in [9600, 19200, 38400]:
            raise ValueError("Invalid baudrate. Must be 9600, 19200, or 38400")
        
        if slave_id < 1 or slave_id > 247:
            raise ValueError("Invalid slave ID. Must be between 1 and 247")
        
        self.port = port
        self.baudrate = baudrate
        self.slave_id = slave_id
        self.timeout = timeout
        
        # Communication components
        self.client = None
        self.connection_status = False
        
        # System state
        self.last_data = {}
        self.connection_attempts = 0
        self.last_connection_time = None
        
        # Callbacks for asynchronous operations
        self.connection_callback = None
        self.data_callback = None
        
        # Configure logger for this instance
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
    async def connect(self) -> bool:
        """
        Establish MODBUS RTU connection with Sungold SPH10048P inverter.
        
        Returns:
            bool: True if connection successful, False otherwise
            
        Raises:
            Exception: If connection fails for any reason
        """
        try:
            # Log connection attempt
            self.connection_attempts += 1
            self.last_connection_time = datetime.now()
            
            self.logger.info(f"🔌 Attempting connection to Sungold SPH10048P (Attempt #{self.connection_attempts})")
            self.logger.info(f"   Port: {self.port}, Baud: {self.baudrate}, Slave ID: {self.slave_id}")
            
            # Initialize MODBUS client for RTU communication
            self.client = AsyncModbusSerialClient(
                method='rtu',
                port=self.port,
                baudrate=self.baudrate,
                bytesize=8,
                parity='Even',
                stopbits=1,
                timeout=self.timeout,
                retries=3,
                retry_on_empty=False
            )
            
            # Establish connection
            await self.client.connect()
            
            # Verify connection by reading basic diagnostic data
            connection_test = await self.client.read_holding_registers(
                address=40001,  # Read PV power register
                count=1,
                slave_id=self.slave_id
            )
            
            if not connection_test.isError():
                self.connection_status = True
                
                self.logger.info(f"✅ Successfully connected to Sungold SPH10048P!")
                self.logger.info(f"   Device Model: SPH10048P")
                self.logger.info(f"   Power Rating: 10kW (48V DC Input)")
                self.logger.info(f"   Communication: MODBUS RTU @ {self.baudrate} baud")
                
                # Execute connection callback if registered
                if self.connection_callback:
                    await self.connection_callback({
                        'type': 'connection established',
                        'timestamp': datetime.now().isoformat(),
                        'device_info': {
                            'model': 'SPH10048P',
                            'power_rating': '10kW',
                            'dc_input_voltage': '48V',
                            'slave_id': self.slave_id,
                            'communication_protocol': 'MODBUS RTU',
                            'baud_rate': self.baudrate,
                            'connection_time': self.last_connection_time.isoformat()
                        }
                    })
                
                return True
                
            else:
                self.logger.error(f"❌ MODBUS connection test failed: {connection_test}")
                return False
                
        except Exception as connection_error:
            self.logger.error(f"❌ Failed to connect to Sungold SPH10048P: {str(connection_error)}")
            self.connection_status = False
            return False
    
    async def disconnect(self):
        """Gracefully disconnect from the inverter."""
        try:
            if self.client:
                await self.client.close()
                self.client = None
            
            self.connection_status = False
            self.logger.info("🔌 Disconnected from Sungold SPH10048P inverter")
        except Exception as e:
            self.logger.error(f"❌ Error during disconnection: {str(e)}")
    
    async def read_single_register(self, address: int) -> Optional[int]:
        """
        Read a single MODBUS register from the inverter.
        
        Args:
            address (int): Register address (e.g., 40001)
            
        Returns:
            Optional[int]: Register value if successful, None if error
        """
        if not self.connection_status:
            self.logger.warning("⚠️ Not connected to device, cannot read register")
            return None
        
        try:
            result = await self.client.read_holding_registers(
                address=address,
                count=1,
                slave_id=self.slave_id
            )
            
            if not result.isError():
                return result.registers[0]
            else:
                self.logger.error(f"❌ Failed to read register {address}: {result}")
                return None
        except Exception as e:
            self.logger.error(f"❌ Error reading register {address}: {str(e)}")
            return None
    
    async def read_multiple_registers(self, address: int, count: int) -> Optional[list]:
        """
        Read multiple consecutive registers from the inverter.
        
        Args:
            address (int): Starting register address
            count (int): Number of registers to read
            
        Returns:
            Optional[list]: List of register values if successful, None if error
        """
        if not self.connection_status:
            self.logger.warning("⚠️ Not connected to device, cannot read registers")
            return None
        
        try:
            result = await self.client.read_holding_registers(
                address=address,
                count=count,
                slave_id=self.slave_id
            )
            
            if not result.isError():
                return result.registers
            else:
                self.logger.error(f"❌ Failed to read registers {address}-{address+count-1}: {result}")
                return None
        except Exception as e:
            self.logger.error(f"❌ Error reading registers: {str(e)}")
            return None
    
    async def get_power_system_data(self) -> Dict:
        """
        Retrieve complete power system data from the SPH10048P inverter.
        
        Returns:
            Dict: Comprehensive power system measurements and status information
        """
        if not self.connection_status:
            self.logger.warning("⚠️ Not connected to inverter, cannot retrieve power data")
            return {}
        
        collected_data = {}
        
        for key, register_info in self.REGISTERS.items():
            register_address = register_info['addr']
            
            # Read register data
            raw_value = await self.read_single_register(register_address)
            
            if raw_value is not None:
                # Calculate actual value based on register specifications
                factor = register_info['factor']
                unit = register_info['unit']
                description = register_info['desc']
                
                # Apply scaling factor based on unit type
                if unit in ['%', 'mode', 'state', 'status', 'code', 'count', 'h']:
                    actual_value = raw_value * factor
                else:
                    actual_value = float(raw_value)
                
                # Analyze operational status
                operational_status = self._analyze_operational_status(key, actual_value)
                
                # Store collected data with comprehensive metadata
                collected_data[key] = {
                    'raw': raw_value,
                    'value': actual_value,
                    'unit': unit,
                    'description': description,
                    'timestamp': datetime.now().isoformat(),
                    'status': operational_status,
                    'scaling_factor': factor,
                    'is_valid': self._validate_reading(key, actual_value)
                }
        
        # Update last known data
        self.last_data = collected_data
        
        return collected_data
    
    def _analyze_operational_status(self, parameter_key: str, value: float) -> str:
        """
        Analyze the operational status of a specific parameter.
        
        Args:
            parameter_key (str): The parameter identifier
            value (float): The measured value
            
        Returns:
            str: Status level ('normal', 'warning', or 'error')
        """
        try:
            # Define critical thresholds and warning levels for each parameter
            if parameter_key == 'battery_soc':
                if value < 20: return 'error'
                elif value > 95: return 'warning'
            
            elif parameter_key == 'battery_voltage':
                if value < 43 or value > 58: return 'error'
            
            elif parameter_key == 'temperature':
                if value > 80: return 'warning'
            
            elif parameter_key == 'system_current':
                if abs(value) > 250: return 'error'
            
            elif parameter_key == 'grid_power':
                if abs(value) > self.REGISTERS['rated_power']['value']: return 'warning'
            
            elif parameter_key == 'pv_power':
                if value > self.REGISTERS['rated_power']['value']: return 'warning'
            
            return 'normal'
        
        except Exception:
            return 'unknown'
    
    def _validate_reading(self, parameter_key: str, value: float) -> bool:
        """
        Validate if a measurement reading is within acceptable ranges.
        
        Args:
            parameter_key (str): Parameter identifier
            value (float): Measured value
            
        Returns:
            bool: True if valid, False if invalid
        """
        try:
            # Parameter-specific validation logic
            if parameter_key == 'battery_soc':
                return 0 <= value <= 100
            elif parameter_key == 'battery_voltage':
                return 40 <= value <= 60
            elif parameter_key == 'temperature':
                return -10 <= value <= 100
            elif parameter_key == 'pv_power':
                return 0 <= value <= self.REGISTERS['rated_power']['value']
            elif parameter_key == 'grid_power':
                return -self.REGISTERS['rated_power']['value'] <= value <= self.REGISTERS['rated_power']['value']
            else:
                return True  # Default validation for other parameters
        
        except Exception:
            return False
    
    async def get_system_summary(self) -> Dict:
        """
        Generate comprehensive system summary and performance analysis.
        
        Returns:
            Dict: System overview with performance metrics and operational status
        """
        collected_data = await self.get_power_system_data()
        
        if not collected_data:
            return {'error': 'Unable to retrieve system data'}
        
        # System information
        system_info = {
            'device_info': {
                'model': 'SPH10048P',
                'power_rating': '10kW',
                'dc_input_voltage': '48V',
                'communication_interface': 'MODBUS RTU RS485',
                'manufacturer': 'Sungold'
            },
            'current_power_status': {},
            'today_energy_performance': {},
            'system_health_indicators': {},
            'operational_analysis': {}
        }
        
        # Extract and categorize power system data
        power_data = collected_data
        
        # Current power status metrics
        if 'pv_power' in power_data:
            system_info['current_power_status']['solar'] = power_data['pv_power']
        
        if 'grid_power' in power_data:
            grid_info = power_data['grid_power']
            system_info['current_power_status']['grid'] = grid_info
            system_info['current_power_status']['grid_direction'] = (
                'export' if grid_info['value'] > 0 else 'import'
            )
        
        if 'battery_soc' in power_data:
            system_info['current_power_status']['battery'] = power_data['battery_soc']
        
        if 'efficiency' in power_data:
            system_info['current_power_status']['efficiency'] = power_data['efficiency']
        
        # Today's energy performance
        energy_metrics = ['today_energy', 'grid_import_today', 'grid_export_today', 'peak_power_today']
        for metric in energy_metrics:
            if metric in power_data:
                system_info['today_energy_performance'][metric] = power_data[metric]
        
        # System health indicators
        health_metrics = ['inverter_status', 'grid_connection', 'charge_controller', 'temperature']
        for metric in health_metrics:
            if metric in power_data:
                system_info['system_health_indicators'][metric] = power_data[metric]
        
        # Operational analysis
        system_info['operational_analysis'] = {
            'power_source_mix': self._calculate_power_source_mix(power_data),
            'operational_mode': self._get_operating_mode(power_data),
            'system_efficiency_rating': self._calculate_efficiency_rating(power_data),
            ' battery_health': self._analyze_battery_health(power_data),
            'thermal_status': self._analyze_thermal_status(power_data)
        }
        
        return system_info
    
    def _calculate_power_source_mix(self, power_data: Dict) -> Dict:
        """Analyze the current power source utilization."""
        mix_analysis = {
            'primary_source': 'unknown',
            'solar_contribution': 0,
            'grid_contribution': 0,
            'battery_contribution': 0,
            'status': 'normal'
        }
        
        try:
            pv_power = power_data.get('pv_power', {}).get('value', 0)
            load_power = power_data.get('load_power', {}).get('value', 0)
            battery_charge = power_data.get('battery_charge_power', {}).get('value', 0)
            battery_discharge = power_data.get('battery_discharge_power', {}).get('value', 0)
            
            # Determine primary power source
            if pv_power > load_power:
                if battery_charge > 0:
                    mix_analysis['primary_source'] = 'solar surplus'
                    mix_analysis['solar_contribution'] = 100
                    mix_analysis['battery_contribution'] = (battery_charge / (pv_power + battery_charge)) * 100
                elif battery_discharge > 0:
                    mix_analysis['primary_source'] = 'solar'
                    mix_analysis['solar_contribution'] = 100
                    mix_analysis['battery_contribution'] = (battery_discharge / pv_power) * 100
            elif load_power > pv_power:
                if battery_discharge > 0:
                    mix_analysis['primary_source'] = 'battery'
                    mix_analysis['battery_contribution'] = 100
                    mix_analysis['grid_contribution'] = (load_power - pv_power - battery_discharge) / load_power * 100
                else:
                    mix_analysis['primary_source'] = 'grid'
                    mix_analysis['grid_contribution'] = 100
            
            # Check for anomalies
            if pv_power > self.REGISTERS['rated_power']['value'] * 1.1:
                mix_analysis['status'] = 'warning'
        
        except Exception:
            pass
        
        return mix_analysis
    
    def _get_operating_mode(self, power_data: Dict) -> Dict:
        """Determine current operating mode from inverter."""
        mode_register = power_data.get('operating_mode', {})
        if not mode_register:
            return {'mode': 'unknown', 'status': 'error'}
        
        try:
            mode_code = int(mode_register['value'])
            mode_name = self.OPERATING_MODES.get(mode_code, f'Unknown Mode ({mode_code})')
            
            return {
                'mode_code': mode_code,
                'mode_name': mode_name,
                'status': 'active' if mode_code in self.OPERATING_MODES else 'unknown'
            }
        
        except Exception:
            return {'mode': 'unknown', 'status': 'error'}
    
    def _calculate_efficiency_rating(self, power_data: Dict) -> Dict:
        """Calculate system efficiency rating."""
        efficiency = power_data.get('efficiency', {})
        pv_power = power_data.get('pv_power', {})
        load_power = power_data.get('load_power', {})
        
        if not efficiency or not pv_power:
            return {'rating': 0, 'status': 'unknown'}
        
        try:
            system_efficiency = efficiency['value']
            
            if system_efficiency > 95:
                rating = 'Excellent'
            elif system_efficiency > 90:
                rating = 'Good'
            elif system_efficiency > 85:
                rating = 'Acceptable'
            else:
                rating = 'Below Average'
            
            return {
                'efficiency_percentage': system_efficiency,
                'rating': rating,
                'status': 'good' if system_efficiency > 90 else 'needs_attention'
            }
        
        except Exception:
            return {'rating': 0, 'status': 'error'}
    
    def _analyze_battery_health(self, power_data: Dict) -> Dict:
        """Analyze battery health and status."""
        battery_soc = power_data.get('battery_soc', {})
        battery_voltage = power_data.get('battery_voltage', {})
        battery_current = power_data.get('battery_current', {})
        
        health_status = {
            'soc': battery_soc.get('value', 0),
            'voltage': battery_voltage.get('value', 0),
            'current': battery_current.get('value', 0),
            'overall_health': 'unknown',
            'charging_status': 'unknown',
            'warnings': []
        }
        
        try:
            if battery_soc:
                soc = battery_soc['value']
                if soc < 20:
                    health_status['overall_health'] = 'critical'
                    health_status['warnings'].append('Battery SOC below 20%')
                elif soc < 40:
                    health_status['overall_health'] = 'warning'
                    health_status['warnings'].append('Battery SOC below 40%')
                elif soc > 95:
                    health_status['warnings'].append('Battery SOC above 95% (keep charging)')
                else:
                    health_status['overall_health'] = 'good'
            
            if battery_current:
                current = battery_current['value']
                if current > 0:
                    health_status['charging_status'] = 'charging'
                elif current < 0:
                    health_status['charging_status'] = 'discharging'
                else:
                    health_status['charging_status'] = 'idle'
        
        except Exception:
            pass
        
        return health_status
    
    def _analyze_thermal_status(self, power_data: Dict) -> Dict:
        """Analyze thermal conditions and cooling status."""
        ambient_temp = power_data.get('ambient_temperature', {})
        heat_sink_temp = power_data.get('heat_sink_temperature', {})
        
        thermal_status = {
            'ambient_temp': ambient_temp.get('value', 0),
            'heat_sink_temp': heat_sink_temp.get('value', 0),
            'temperature_delta': 0,
            'cooling_status': 'normal',
            'heat_warning': False
        }
        
        try:
            if heat_sink_temp and ambient_temp:
                thermal_status['temperature_delta'] = heat_sink_temp['value'] - ambient_temp['value']
                
                if thermal_status['heat_sink_temp'] > 80:
                    thermal_status['cooling_status'] = 'warning'
                    thermal_status['heat_warning'] = True
                elif thermal_status['heat_sink_temp'] > 90:
                    thermal_status['cooling_status'] = 'critical'
                    thermal_status['heat_warning'] = True
        
        except Exception:
            pass
        
        return thermal_status
    
    def get_connection_status(self) -> bool:
        """Get current connection status with the inverter."""
        return self.connection_status
    
    def set_connection_callback(self, callback):
        """
        Set callback function for connection status changes.
        
        Args:
            callback: Async function to be called on connection events
        """
        self.connection_callback = callback
    
    def set_data_callback(self, callback):
        """
        Set callback function for data updates.
        
        Args:
            callback: Async function to be called on data updates
        """
        self.data_callback = callback
    
    async def start_data_collection(self, interval: int = 5):
        """
        Start continuous monitoring and data collection.
        
        Args:
            interval: Collection interval in seconds
        """
        logger.info(f"Starting data collection with {interval}s interval")
        
        while self.connection_status:
            try:
                # Collect comprehensive power system data
                collected_data = await self.get_power_system_data()
                
                # Execute data callback if registered
                if self.data_callback:
                    await self.data_callback({
                        'type': 'data_update',
                        'timestamp': datetime.now().isoformat(),
                        'data': collected_data,
                        'connection_status': self.connection_status
                    })
                
                # Log critical status warnings
                for key, info in collected_data.items():
                    status = info.get('status', 'unknown')
                    if status == 'error':
                        logger.error(f"🚨 CRITICAL: {key} = {info.get('value', 0)} {info.get('unit', '')} - SYSTEM ERROR")
                    elif status == 'warning':
                        logger.warning(f"⚠️ WARNING: {key} = {info.get('value', 0)} {info.get('unit', '')} - Status Alert")
                
                # Wait for next collection cycle
                await asyncio.sleep(interval)
                
            except Exception as e:
                logger.error(f"❌ Data collection error: {str(e)}")
                await asyncio.sleep(interval)
    
    async def run_initial_diagnostic(self) -> Dict:
        """
        Perform comprehensive initial diagnostic of the inverter system.
        
        Returns:
            Dict: Diagnostic results including status, warnings, and recommendations
        """
        diagnostic_results = {
            'timestamp': datetime.now().isoformat(),
            'connection_status': self.connection_status,
            'data_accessible': False,
            'diagnostic_passed': True,
            'warnings': [],
            'errors': [],
            'performance_metrics': {},
            'maintenance_recommendations': []
        }
        
        if not self.connection_status:
            diagnostic_results['errors'].append('Cannot connect to inverter')
            diagnostic_results['diagnostic_passed'] = False
            return diagnostic_results
        
        try:
            # Get system data for analysis
            system_data = await self.get_power_system_data()
            
            if not system_data:
                diagnostic_results['errors'].append('Cannot read inverter data')
                diagnostic_results['diagnostic_passed'] = False
                return diagnostic_results
            
            diagnostic_results['data_accessible'] = True
            
            # Analyze system performance
            diagnostic_results['performance_metrics'] = self._analyze_performance_metrics(system_data)
            
            # Check for critical issues
            diagnostic_results['warnings'] = self._generate_system_warnings(system_data)
            
            # Generate maintenance recommendations
            diagnostic_results['maintenance_recommendations'] = self._generate_maintenance_recommendations(system_data)
            
            # Validate overall system health
            if diagnostic_results['errors'] or diagnostic_results['warnings']:
                diagnostic_results['diagnostic_passed'] = False
        
        except Exception as e:
            diagnostic_results['errors'].append(f'Diagnostic error: {str(e)}')
            diagnostic_results['diagnostic_passed'] = False
        
        return diagnostic_results
    
    def _analyze_performance_metrics(self, system_data: Dict) -> Dict:
        """Analyze key performance metrics."""
        performance = {
            'solar_efficiency': 0,
            'grid_interaction': 'normal',
            'battery_utilization': 'optimal',
            'overall_system_score': 0
        }
        
        try:
            # Calculate solar efficiency
            pv_power = system_data.get('pv_power', {}).get('value', 0)
            rated_power = self.REGISTERS['rated_power']['value']
            
            if rated_power > 0:
                performance['solar_efficiency'] = min(100, (pv_power / rated_power) * 100)
            
            # Analyze grid interaction
            grid_power = system_data.get('grid_power', {}).get('value', 0)
            if abs(grid_power) > rated_power * 0.8:
                performance['grid_interaction'] = 'high_load'
            elif grid_power > 0:
                performance['grid_interaction'] = 'exporting'
            elif grid_power < 0:
                performance['grid_interaction'] = 'importing'
            
            # Analyze battery utilization
            battery_soc = system_data.get('battery_soc', {}).get('value', 0)
            if battery_soc < 20:
                performance['battery_utilization'] = 'critically_low'
            elif battery_soc < 40:
                performance['battery_utilization'] = 'low'
            elif battery_soc > 90:
                performance['battery_utilization'] = 'charging_fully'
            else:
                performance['battery_utilization'] = 'optimal'
            
            # Calculate overall system score
            score_components = []
            
            # Efficiency score (0-25 points)
            if performance['solar_efficiency'] >= 90:
                score_components.append(25)
            elif performance['solar_efficiency'] >= 80:
                score_components.append(20)
            elif performance['solar_efficiency'] >= 70:
                score_components.append(15)
            else:
                score_components.append(5)
            
            # Grid interaction score (0-25 points)
            if performance['grid_interaction'] == 'normal':
                score_components.append(25)
            elif performance['grid_interaction'] == 'high_load':
                score_components.append(15)
            else:
                score_components.append(10)
            
            # Battery utilization score (0-25 points)
            battery_scores = {'optimal': 25, 'low': 15, 'critically_low': 5, 'charging_fully': 20}
            score_components.append(battery_scores.get(performance['battery_utilization'], 0))
            
            # System health score (0-25 points)
            health_score = sum(1 for key, info in system_data.items() if info.get('status') == 'normal')
            health_percentage = (health_score / len(system_data)) * 25
            score_components.append(health_percentage)
            
            performance['overall_system_score'] = sum(score_components)
        
        except Exception:
            pass
        
        return performance
    
    def _generate_system_warnings(self, system_data: Dict) -> List[str]:
        """Generate system warnings based on current readings."""
        warnings = []
        
        try:
            # Battery warnings
            battery_soc = system_data.get('battery_soc', {})
            if battery_soc.get('status') == 'error':
                warnings.append(f"🚨 BATTERY CRITICAL: State of charge at {battery_soc.get('value', 0):.1f}%")
            
            # Temperature warnings
            heat_sink_temp = system_data.get('heat_sink_temperature', {})
            if heat_sink_temp.get('status') == 'warning':
                warnings.append(f"⚠️ TEMPERATURE WARNING: Heat sink at {heat_sink_temp.get('value', 0):.1f}°C")
            
            # Power output warnings
            pv_power = system_data.get('pv_power', {})
            if pv_power.get('status') == 'warning':
                warnings.append(f"⚠️ SOLAR OUTPUT WARNING: {pv_power.get('value', 0):.1f}W above normal")
            
            # Grid interaction warnings
            grid_power = system_data.get('grid_power', {})
            if grid_power.get('status') == 'warning':
                warnings.append(f"⚠️ GRID INTERACTION WARNING: {grid_power.get('value', 0):.1f}W")
        
        except Exception:
            pass
        
        return warnings
    
    def _generate_maintenance_recommendations(self, system_data: Dict) -> List[str]:
        """Generate maintenance recommendations based on current status."""
        recommendations = []
        
        try:
            # Check for battery maintenance needs
            battery_soc = system_data.get('battery_soc', {})
            if battery_soc.get('value', 100) < 40:
                recommendations.append("🔋 Battery maintenance recommended - SOC below 40%")
            
            # Check temperature-related maintenance
            heat_sink_temp = system_data.get('heat_sink_temperature', {})
            if heat_sink_temp.get('value', 0) > 75:
                recommendations.append("🌡️ Cooling system inspection recommended - high temperature warning")
            
            # Check system efficiency
            efficiency = system_data.get('efficiency', {})
            if efficiency.get('value', 100) < 90:
                recommendations.append("⚡ Performance optimization recommended - efficiency below 90%")
            
            # Check for fault codes
            fault_code = system_data.get('last_fault_code', {})
            if fault_code and fault_code.get('value', 0) > 0:
                recommendations.append(f"🛠️ Fault code analysis required - Last fault: {fault_code.get('value', 'unknown')}")
            
            # Check daily runtime
            daily_runtime = system_data.get('daily_runtime', {})
            if daily_runtime.get('value', 0) < 24:
                recommendations.append("⏱️ Operational time monitoring - daily runtime recorded")
        
        except Exception:
            pass
        
        return recommendations
    
    async def get_emergency_status(self) -> Dict:
        """
        Get critical system status for emergency situations.
        
        Returns:
            Dict: Critical system status information for emergency response
        """
        emergency_status = {
            'timestamp': datetime.now().isoformat(),
            'emergency_mode': True,
            'critical_parameters': {},
            'system_health': 'unknown',
            'immediate_actions': []
        }
        
        if not self.connection_status:
            emergency_status['critical_parameters']['connection'] = 'critical - disconnected'
            emergency_status['system_health'] = 'critical'
            emergency_status['immediate_actions'].append('Reconnect inverter immediately')
            return emergency_status
        
        # Collect critical parameters
        critical_params = ['pv_power', 'grid_power', 'battery_soc', 'battery_voltage', 
                          'system_voltage', 'temperature', 'inverter_status']
        
        system_data = await self.get_power_system_data()
        
        for param in critical_params:
            if param in system_data:
                emergency_status['critical_parameters'][param] = {
                    'value': system_data[param]['value'],
                    'unit': system_data[param]['unit'],
                    'status': system_data[param]['status']
                }
        
        # Analyze overall system health
        critical_count = sum(1 for param in critical_params 
                           if param in system_data and system_data[param]['status'] == 'error')
        warning_count = sum(1 for param in critical_params 
                          if param in system_data and system_data[param]['status'] == 'warning')
        
        if critical_count > 0:
            emergency_status['system_health'] = 'critical'
            emergency_status['immediate_actions'].append('IMMEDIATE ACTION REQUIRED - System in critical state')
        elif warning_count > 2:
            emergency_status['system_health'] = 'warning'
            emergency_status['immediate_actions'].append('Monitor system closely - multiple warnings detected')
        else:
            emergency_status['system_health'] = 'stable'
            emergency_status['immediate_actions'].append('Continue normal monitoring')
        
        return emergency_status

if __name__ == "__main__":
    """
    Example usage and demonstration of Sungold SPH10048P integration.
    """
    async def main():
        print("🔍 Sungold SPH10048P Inverter Integration Demo")
        print("=" * 50)
        print("This example demonstrates complete integration of the")
        print("Sungold SPH10048P hybrid inverter with communication")
        print("protocols, data monitoring, and status analysis.\n")
        
        # Initialize inverter (change serial port as needed)
        inverter = SungoldSPH10048P(
            port='/dev/ttyUSB0',      # Replace with your actual serial port
            baudrate=9600,
            slave_id=1
        )
        
        print(f"Attempting to connect to Sungold SPH10048P...")
        print(f"Communication parameters:")
        print(f"  Serial Port: {inverter.port}")
        print(f"  Baud Rate: {inverter.baudrate}")
        print(f"  MODBUS Slave ID: {inverter.slave_id}")
        print(f"  Protocol: MODBUS RTU with Even Parity\n")
        
        # Connect to inverter
        if await inverter.connect():
            print(f"✅ Connection successful!")
            
            # Run initial diagnostic
            print("\n🔧 Performing initial system diagnostic...")
            diagnostic = await inverter.run_initial_diagnostic()
            
            print("\n📊 Diagnostic Results:")
            print(f"  Connection Status: {'✅ Connected' if diagnostic['connection_status'] else '❌ Failed'}")
            print(f"  Data Accessible: {'✅ Yes' if diagnostic['data_accessible'] else '❌ No'}")
            print(f"  System Passed: {'✅ Yes' if diagnostic['diagnostic_passed'] else '❌ No'}")
            
            if diagnostic['warnings']:
                print(f"  Warnings ({len(diagnostic['warnings'])}):")
                for warning in diagnostic['warnings']:
                    print(f"    ⚠️  {warning}")
            
            if diagnostic['errors']:
                print(f"  Errors ({len(diagnostic['errors'])}):")
                for error in diagnostic['errors']:
                    print(f"    🚨 {error}")
            
            # Get system summary
            print("\n📈 System Summary:")
            summary = await inverter.get_system_summary()
            
            current_status = summary.get('current_power_status', {})
            if 'solar' in current_status:
                solar_data = current_status['solar']
                print(f"  Solar Power: {solar_data.get('value', 0):.1f} {solar_data.get('unit', 'W')} ({solar_data.get('status', 'unknown')})")
            
            if 'grid' in current_status:
                grid_data = current_status['grid']
                direction = "exporting" if grid_data['value'] > 0 else "importing"
                print(f"  Grid Power: {abs(grid_data.get('value', 0)):.1f} {grid_data.get('unit', 'W')} ({direction})")
            
            if 'battery' in current_status:
                battery_data = current_status['battery']
                print(f"  Battery SOC: {battery_data.get('value', 0):.1f}% ({battery_data.get('status', 'unknown')})")
            
            print("\n⏱️ Starting continuous data collection (30 seconds)...")
            print("Press Ctrl+C to stop monitoring\n")
            
            # Start continuous monitoring (comment out for one-time query)
            await inverter.start_data_collection(interval=5)
            
            # Monitor for 30 seconds (for demonstration)
            await asyncio.sleep(30)
            
        else:
            print("❌ Failed to connect to inverter")
            print("\nTroubleshooting Tips:")
            print("1. Check that the inverter is powered on")
            print("2. Verify the serial port connection")
            print("3. Ensure correct baud rate (9600 for SPH10048P)")
            print("4. Check MODBUS slave ID settings")
            print("5. Verify communication protocol (MODBUS RTU)")
            print("6. Check for loose cable connections")
        
        # Clean disconnection
        await inverter.disconnect()
        print("\n👋 Example completed successfully!")
    
    # Run the example
    asyncio.run(main())