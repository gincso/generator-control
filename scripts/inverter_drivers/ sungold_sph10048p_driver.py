#!/usr/bin/env python3
"""
Sungold SPH10048P Hybrid Inverter Driver
MODBUS RTU communication protocol for Sungold SPH10048P 10kW hybrid inverter
Integrates with Raspberry Pi generator control system for comprehensive solar + generator management
"""

import asyncio
import logging
import serial
from datetime import datetime
from typing import Dict, Optional, List
from pymodbus.client import AsyncModbusSerialClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SungoldSPH10048P:
    """Sungold SPH10048P 10kW hybrid inverter MODBUS communication driver"""
    
    # MODBUS register map for SPH10048P (Sungold specifications)
    # Default MODBUS slave ID: 1
    REGISTERS = {
        # Power Measurement Registers
        'pv_power': {'addr': 40001, 'factor': 1, 'unit': 'W', 'desc': 'PV Panel Power Output'},
        'grid_power': {'addr': 40002, 'factor': 1, 'unit': 'W', 'desc': 'Grid Exchange Power'},
        'battery_soc': {'addr': 40003, 'factor': 0.1, 'unit': '%', 'desc': 'Battery State of Charge'},
        'battery_voltage': {'addr': 40004, 'factor': 0.01, 'unit': 'V', 'desc': 'Battery Voltage'},
        'battery_current': {'addr': 40005, 'factor': 0.01, 'unit': 'A', 'desc': 'Battery Current'},
        'system_voltage': {'addr': 40006, 'factor': 0.01, 'unit': 'V', 'desc': 'DC Bus Voltage'},
        'system_current': {'addr': 40007, 'factor': 0.01, 'unit': 'A', 'desc': 'DC Bus Current'},
        'efficiency': {'addr': 40008, 'factor': 0.1, 'unit': '%', 'desc': 'System Efficiency'},
        'temperature': {'addr': 40009, 'factor': 1, 'unit': '°C', 'desc': 'Inverter Temperature'},
        
        # Energy Measurement Registers
        'today_energy': {'addr': 40010, 'factor': 0.01, 'unit': 'kWh', 'desc': 'Today's Generated Energy'},
        'total_energy': {'addr': 40011, 'factor': 0.01, 'unit': 'kWh', 'desc': 'Total Generated Energy'},
        'peak_power_today': {'addr': 40012, 'factor': 1, 'unit': 'W', 'desc': 'Peak Power Today'},
        'grid_import_today': {'addr': 40013, 'factor': 0.01, 'unit': 'kWh', 'desc': 'Today's Grid Import'},
        'grid_export_today': {'addr': 40014, 'factor': 0.01, 'unit': 'kWh', 'desc': 'Today\'s Grid Export'},
        
        # System Status Registers
        'operating_mode': {'addr': 40015, 'factor': 1, 'unit': '', 'desc': 'Operating Mode'},
        'charge_controller': {'addr': 40016, 'factor': 1, 'unit': '', 'desc': 'Charge Controller Status'},
        'grid_connection': {'addr': 40017, 'factor': 1, 'unit': '', 'desc': 'Grid Connection Status'},
        'inverter_status': {'addr': 40018, 'factor': 1, 'unit': '', 'desc': 'Inverter Status'},
        'battery_protection': {'addr': 40019, 'factor': 1, 'unit': '', 'desc': 'Battery Protection Status'},
        
        # Additional Diagnostic Registers
        'grid_frequency': {'addr': 40020, 'factor': 0.01, 'unit': 'Hz', 'desc': 'Grid Frequency'},
        'pv_voltage': {'addr': 40021, 'factor': 0.01, 'unit': 'V', 'desc': 'PV Panel Voltage'},
        'pv_current': {'addr': 40022, 'factor': 0.01, 'unit': 'A', 'desc': 'PV Panel Current'},
        'load_power': {'addr': 40023, 'factor': 1, 'unit': 'W', 'desc': 'Load Power'},
        'battery_discharge_power': {'addr': 40024, 'factor': 1, 'unit': 'W', 'desc': 'Battery Discharge Power'},
        'battery_charge_power': {'addr': 40025, 'factor': 1, 'unit': 'W', 'desc': 'Battery Charge Power'},
        'ambient_temperature': {'addr': 40026, 'factor': 1, 'unit': '°C', 'desc': 'Ambient Temperature'},
        'heat_sink_temperature': {'addr': 40027, 'factor': 1, 'unit': '°C', 'desc': 'Heat Sink Temperature'},
        'last_fault_code': {'addr': 40028, 'factor': 1, 'unit': 'code', 'desc': 'Last Fault Code'},
        'total_fault_times': {'addr': 40029, 'factor': 1, 'unit': 'count', 'desc': 'Total Fault Times'},
        'daily_runtime': {'addr': 40030, 'factor': 1, 'unit': 'h', 'desc': 'Daily Runtime Hours'},
        
        # Configuration Registers
        'rated_power': {'addr': 40031, 'factor': 1, 'unit': 'W', 'desc': 'Rated Power'},
        'max_output_power': {'addr': 40032, 'factor': 1, 'unit': 'W', 'desc': 'Maximum Output Power'},
        'battery_capacity': {'addr': 40033, 'factor': 1, 'unit': 'kWh', 'desc': 'Battery Capacity'},
        'install_area': {'addr': 40034, 'factor': 1, 'unit': '', 'desc': 'Installation Area'},
        'backup_time': {'addr': 40035, 'factor': 1, 'unit': 'h', 'desc': 'Backup Time'},
    }
    
    def __init__(self, port: str = '/dev/ttyUSB0', baudrate: int = 9600,
                 slave_id: int = 1, timeout: int = 2):
        self.port = port
        self.baudrate = baudrate
        self.slave_id = slave_id
        self.timeout = timeout
        
        self.client = None
        self.connection_status = False
        
    async def connect(self) -> bool:
        try:
            self.client = AsyncModbusSerialClient(
                method='rtu',
                port=self.port,
                baudrate=self.baudrate,
                bytesize=8,
                parity='Even',
                stopbits=1,
                timeout=self.timeout,
                retries=3
            )
            
            await self.client.connect()
            
            result = await self.client.read_holding_registers(
                address=40001,
                count=1,
                slave_id=self.slave_id
            )
            
            if not result.isError():
                self.connection_status = True
                logger.info(f"✅ Connected to Sungold SPH10048P (ID: {self.slave_id})")
                return True
            else:
                logger.error(f"❌ Connection test failed: {result}")
                return False
        except Exception as e:
            logger.error(f"❌ Connection failed: {str(e)}")
            self.connection_status = False
            return False
    
    async def disconnect(self):
        if self.client:
            await self.client.close()
            self.client = None
        self.connection_status = False
        logger.info("🔌 Disconnected from SPH10048P")
    
    async def read_register(self, address: int) -> Optional[int]:
        if not self.connection_status:
            return None
        
        try:
            result = await self.client.read_holding_registers(
                address=address,
                count=1,
                slave_id=self.slave_id
            )
            return result.registers[0] if not result.isError() else None
        except:
            return None
    
    async def get_power_data(self) -> Dict:
        if not self.connection_status:
            return {}
        
        data = {}
        for key, info in self.REGISTERS.items():
            value = await self.read_register(info['addr'])
            if value is not None:
                factor = info['factor']
                unit = info['unit']
                
                if unit in ['%', 'mode', 'state', 'code', 'count', 'h']:
                    actual_value = value * factor
                else:
                    actual_value = float(value)
                
                data[key] = {
                    'raw': value,
                    'value': actual_value,
                    'unit': unit,
                    'description': info['desc'],
                    'timestamp': datetime.now().isoformat(),
                    'status': self._analyze_status(key, actual_value)
                }
        
        return data
    
    def _analyze_status(self, key: str, value: float) -> str:
        if key == 'battery_soc':
            if value < 20: return 'error'
            elif value > 95: return 'warning'
        elif key == 'battery_voltage':
            if value < 43 or value > 58: return 'error'
        elif key == 'temperature':
            if value > 80: return 'warning'
        elif key == 'system_current':
            if abs(value) > 250: return 'error'
        return 'normal'
    
    async def get_system_summary(self) -> Dict:
        data = await self.get_power_data()
        
        if not data:
            return {}
        
        summary = {
            'device_info': {
                'model': 'SPH10048P',
                'power_rating': '10kW',
                'dc_voltage': '48V',
                'manufacturer': 'Sungold'
            },
            'power_system': {
                'solar_power': data.get('pv_power', {}),
                'grid_power': data.get('grid_power', {}),
                'battery_soc': data.get('battery_soc', {}),
                'efficiency': data.get('efficiency', {}),
                'temperature': data.get('temperature', {})
            },
            'energy_today': {
                'generated': data.get('today_energy', {}),
                'grid_import': data.get('grid_import_today', {}),
                'grid_export': data.get('grid_export_today', {}),
                'peak_power': data.get('peak_power_today', {})
            },
            'system_status': {
                'operating_mode': data.get('operating_mode', {}),
                'grid_connection': data.get('grid_connection', {}),
                'charge_controller': data.get('charge_controller', {}),
                'inverter_status': data.get('inverter_status', {})
            }
        }
        
        return summary
    
    def get_connection_status(self) -> bool:
        return self.connection_status

if __name__ == "__main__":
    async def main():
        print("🔍 Testing Sungold SPH10048P Connection")
        print("=" * 40)
        
        # Initialize SPH10048P (change port to match your setup)
        inverter = SungoldSPH10048P(
            port='/dev/ttyUSB0',
            baudrate=9600,
            slave_id=1
        )
        
        print(f"Attempting to connect to SPH10048P on {inverter.port}...")
        
        if await inverter.connect():
            print("✅ Connection successful!")
            
            # Get system summary
            print("\n📊 System Summary:")
            summary = await inverter.get_system_summary()
            
            ps = summary.get('power_system', {})
            if 'solar_power' in ps:
                pv = ps['solar_power']
                print(f"  Solar Power: {pv.get('value', 0):.1f} {pv.get('unit', 'W')} ({pv.get('status', 'unknown')})")
            
            if 'grid_power' in ps:
                grid = ps['grid_power']
                direction = "exporting to grid" if grid['value'] > 0 else "importing from grid"
                print(f"  Grid Power: {abs(grid['value']):.1f} {grid['unit']} ({direction})")
            
            if 'battery_soc' in ps:
                battery = ps['battery_soc']
                print(f"  Battery SOC: {battery.get('value', 0):.1f}% ({battery.get('status', 'unknown')})")
            
            print(f"\nConnection Status: {'✅ Connected' if inverter.get_connection_status() else '❌ Disconnected'}")
        
        await inverter.disconnect()
        print("\n👋 Test completed!")
    
    asyncio.run(main())