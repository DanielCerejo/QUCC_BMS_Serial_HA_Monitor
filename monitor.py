#!/usr/bin/python3




import serial
import binascii
import time
import os
import paho.mqtt.client as mqtt
from datetime import datetime

tempconfigpublished=False
cellvoltagepublished=False
BMS_Online=False
voltage=0
current=0
power=0
power_charging=0
power_discharging =0
remaining_capacity=0
remaining_capacity_ah=0
nominal_capacity=0
nominal_capacity_ah=0
cycles=0
soc=0
temp_avg=0
temp= []
cell_voltage = []
cell_voltageMin=100
cell_voltageMax=0
ntc_count=0

print(datetime.now(),'Starting QUCC Serial BMS monitor...', flush=True)

# ser = serial.Serial('/dev/ttyUSB0', 9600, timeout=1)  # open serial port
#ser = serial.Serial(os.environ['DEVICE'], 9600, timeout=3, write_timeout=2, exclusive=True)  # open serial port

# connect to MQTT server
client = mqtt.Client(client_id=os.environ['MQTT_CLIENT_ID'])
client.username_pw_set(os.environ['MQTT_USER'], os.environ['MQTT_PASS'])
client.connect(os.environ['MQTT_SERVER'])
client.loop_start()

devId = os.environ['DEVICE_ID']
BASE_TOPIC = os.environ['MQTT_DISCOVERY_PREFIX'] + '/sensor/'
STATE_TOPIC = BASE_TOPIC + devId
deviceConf = '"device": {"manufacturer": "unknow", "name": "Smart BMS", "identifiers": ["' + devId + '"]}'

# Nominal voltage for Ah to Wh conversion (default 76.8V for 24S LiFePO4)
NOMINAL_VOLTAGE = float(os.environ.get('NOMINAL_VOLTAGE', '76.8'))

# requests of the "Smart BMS" protocol, checksum documented in the frame notes
CMD_BATTERY_STATE = b'\xdd\xa5\x03\x00\xff\xfd\x77'
CMD_CELL_VOLTAGES = b'\xdd\xa5\x04\x00\xff\xfc\x77'


# publish MQTT Discovery configs to Home Assistant
socHaConf = '{"device_class": "battery", "name": "Battery SOC", "state_topic": "' + STATE_TOPIC +'/state", "unit_of_measurement": "%", "value_template": "{{ value_json.soc}}", "unique_id": "' + devId + '_soc", ' + deviceConf + '}' 
client.publish(STATE_TOPIC +'_soc/config', socHaConf, 0, True)

voltageHaConf = '{"device_class": "voltage", "name": "Battery Voltage", "state_topic": "' + STATE_TOPIC +'/state", "unit_of_measurement": "V", "value_template": "{{ value_json.voltage}}", "unique_id": "' + devId + '_voltage", ' + deviceConf + '}'
client.publish(STATE_TOPIC + '_voltage/config', voltageHaConf, 0, True)

currentHaConf = '{"device_class": "current", "name": "Battery Current", "state_topic": "' + STATE_TOPIC +'/state", "unit_of_measurement": "A", "value_template": "{{ value_json.current}}", "unique_id": "' + devId + '_current", ' + deviceConf + '}' 
client.publish(STATE_TOPIC + '_current/config', currentHaConf, 0, True)

power_HaConf = '{"device_class": "power", "name": "Battery Power", "state_topic": "' + STATE_TOPIC +'/state", "unit_of_measurement": "W", "value_template": "{{ value_json.power}}", "unique_id": "' + devId + '_power", ' + deviceConf + '}' 
client.publish(STATE_TOPIC + '_power/config', power_HaConf, 0, True)

power_chargingHaConf = '{"device_class": "power", "name": "Battery Power Charging", "state_topic": "' + STATE_TOPIC +'/state", "unit_of_measurement": "W", "value_template": "{{ value_json.power_charging}}", "unique_id": "' + devId + '_power_charging", ' + deviceConf + '}' 
client.publish(STATE_TOPIC + '_power_charging/config', power_chargingHaConf, 0, True)

power_dischargeHaConf = '{"device_class": "power", "name": "Battery Power Discharging", "state_topic": "' + STATE_TOPIC +'/state", "unit_of_measurement": "W", "value_template": "{{ value_json.power_discharging}}", "unique_id": "' + devId + '_power_discharging", ' + deviceConf + '}' 
client.publish(STATE_TOPIC + '_power_discharging/config', power_dischargeHaConf, 0, True)

remaining_capacityHaConf = '{"device_class": "energy_storage", "name": "Battery Remaining Capacity", "state_topic": "' + STATE_TOPIC +'/state", "unit_of_measurement": "Wh", "value_template": "{{ value_json.remaining_capacity}}", "unique_id": "' + devId + '_remaining_capacity", ' + deviceConf + '}' 
client.publish(STATE_TOPIC + '_remaining_capacity/config', remaining_capacityHaConf, 0, True)

nominal_capacityHaConf = '{"device_class": "energy_storage", "name": "Battery Nominal Capacity", "state_topic": "' + STATE_TOPIC +'/state", "unit_of_measurement": "Wh", "value_template": "{{ value_json.nominal_capacity}}", "unique_id": "' + devId + '_nominal_capacity", ' + deviceConf + '}' 
client.publish(STATE_TOPIC + '_nominal_capacity/config', nominal_capacityHaConf, 0, True)

cyclesHaConf = '{"name": "Battery Cycles", "state_topic": "' + STATE_TOPIC +'/state", "unit_of_measurement": "", "value_template": "{{ value_json.cycles}}", "unique_id": "' + devId + '_cycles", ' + deviceConf + '}' 
client.publish(STATE_TOPIC + '_cycles/config', cyclesHaConf, 0, True)

tempAvgHaConf = '{"device_class": "temperature", "name": "Battery Temperature Avg", "state_topic": "' + STATE_TOPIC + '/state", "unit_of_measurement": "°C", "value_template": "{{ value_json.temp_avg}}", "unique_id": "' + devId + '_temp_avg", ' + deviceConf + '}' 
client.publish(STATE_TOPIC + '_temperature_avg/config', tempAvgHaConf, 0, True)




# ---------------------------------------------------------------------------
# Frame validation
#
# The BMS speaks the "Smart BMS" (QUCC) serial protocol:
#
#   request : dd a5 <cmd> <len>    <payload...> <crc_hi> <crc_lo> 77
#   answer  : dd <cmd> <status> <len> <payload...> <crc_hi> <crc_lo> 77
#
# The checksum is not a polynomial CRC but the 16 bit two's complement of the
# byte sum (0xffff - sum + 1), sent big endian, as documented in
# https://github.com/KrystianD/smart_bms (smart_bms/SmartBMSClient.py).
#
# The requests sent here cover <cmd> and everything after it (checked at start
# up by selftest_requests). The answers cover <status> <len> <payload>, which
# is what the BMS firmware really sends (confirmed on captured frames).
# ---------------------------------------------------------------------------

FRAME_START = 0xdd
FRAME_TAIL = 0x77
CHECKSUM_LEN = 2             # 16 bit checksum, big endian, in front of the 0x77
CRC_RETRIES = 3              # attempts per request before giving up on a corrupted answer
CHECKSUM_START = 2           # answers: checksum covers <status> <len> <payload>


def _env_flag(name, default):
    value = os.environ.get(name, '').strip().lower()
    if value in ('', 'null', 'none'):        # option missing from options.json
        value = default
    return value in ('1', 'true', 'yes', 'on')


VERIFY_CRC = _env_flag('VERIFY_CRC', 'true')
DEBUG_FRAMES = _env_flag('DEBUG_FRAMES', 'false')

frames_bad = 0


def _hex(data):
    return binascii.hexlify(bytes(data), b' ').decode()


def _crc16(data):
    """Protocol checksum: 0xffff - sum(data) + 1, sent big endian."""
    return (0x10000 - sum(data)) & 0xFFFF


def _crc_in_frame(buffer):
    return (buffer[-CHECKSUM_LEN - 1] << 8) | buffer[-CHECKSUM_LEN]


def _crc_of_frame(buffer, offset):
    return _crc16(buffer[offset:-CHECKSUM_LEN - 1])


def selftest_requests(*requests):
    """Verify the hardcoded requests carry a checksum built the documented way."""
    for request in requests:
        want = _crc_of_frame(request, 2)
        if want != _crc_in_frame(request):
            print(datetime.now(), 'WARNING: request %s should end with %04x, please report'
                  % (_hex(request), want), flush=True)


def _check_checksum(buffer):
    """Return None when the checksum is fine, otherwise a short description."""
    got = _crc_in_frame(buffer)
    want = _crc_of_frame(buffer, CHECKSUM_START)
    if want == got:
        return None
    return 'checksum mismatch (want 0x%04x got 0x%04x)' % (want, got)


def validate_frame(buffer, expect_cmd, min_len):
    """Return None when the frame looks good, otherwise a short description."""
    if len(buffer) < min_len:
        return 'frame too short (%d bytes)' % len(buffer)
    if buffer[0] != FRAME_START:
        return 'bad header 0x%02x' % buffer[0]
    if expect_cmd is not None and buffer[1] != expect_cmd:
        return 'unexpected command echo 0x%02x' % buffer[1]
    if buffer[2] != 0x00:
        return 'BMS error status 0x%02x' % buffer[2]
    if buffer[-1] != FRAME_TAIL:
        return 'bad trailer 0x%02x' % buffer[-1]
    if VERIFY_CRC and len(buffer) >= 8:
        return _check_checksum(buffer)
    return None


def cmd(command, RxLen, expect_cmd=None, min_len=0):
    """Send a request and return [frame] when the answer validates.

    Returns [] when the BMS did not answer at all (sleeping BMS) and None when
    every answer received was corrupt, so callers can tell the two apart.
    """
    global frames_bad

    for attempt in range(1, CRC_RETRIES + 1):
        ser.write(command)
        ser.flush()
        ser.reset_input_buffer()

        s = ser.read(RxLen)
        if (s == b''):
            if attempt == 1:
                return []
            continue

        if DEBUG_FRAMES:
            print(datetime.now(), 'rx', _hex(s), flush=True)

        problem = validate_frame(s, expect_cmd, min_len)
        if problem is None:
            return [s]

        frames_bad += 1
        if DEBUG_FRAMES or frames_bad <= 10 or frames_bad % 100 == 0:
            print(datetime.now(), 'bad frame (%d/%d): %s [%s]' %
                  (attempt, CRC_RETRIES, problem, _hex(s)), flush=True)

    return None

def publish(topic, data):
    try:
        client.publish(topic, data, 0, False)
    except Exception as e:
        print(datetime.now(),"Error sending to mqtt: " + str(e))



def get_battery_state():

    global BMS_Online

    global voltage
    global current
    global power_charging
    global power_discharging
    global remaining_capacity
    global remaining_capacity_ah
    global nominal_capacity
    global nominal_capacity_ah
    global cycles
    global soc
    global temp_avg
    global temp
    global ntc_count
    global power

    res = cmd(CMD_BATTERY_STATE, 50, 0x03, 30)
    if res is None:
        # corrupt answer after all retries, keep publishing the last known state
        return
    if len(res) < 1:

        if BMS_Online == False:
            return
        BMS_Online = False
        print(datetime.now(),'Empty response get_battery_state. BMS Offline. Low power mode?', flush=True)
        current=0
        power=0
        power_charging=0
        power_discharging=0        

    else :
    
        buffer = res[0]

        if len(buffer) < 27:
            print(datetime.now(),' response to short', flush=True)
            return

        if BMS_Online != True:
                BMS_Online = True
                print(datetime.now(),'BMS Online!', flush=True)

        voltage = int.from_bytes(buffer[4:6], byteorder='big', signed=False) / 100
        current = int.from_bytes(buffer[6:8], byteorder='big', signed=True) / 100
        power = round(voltage * current, 2)
        power_charging=0
        power_discharging=0
        if power>0:
            power_charging=power
        if power<0:
            power_discharging=-power

        # Capacity from BMS is in Ah (divided by 100), convert to Wh using nominal voltage
        remaining_capacity_ah = int.from_bytes(buffer[8:10], byteorder='big', signed=False) / 100
        nominal_capacity_ah = int.from_bytes(buffer[10:12], byteorder='big', signed=False) / 100
        remaining_capacity = round(remaining_capacity_ah * NOMINAL_VOLTAGE, 2)
        nominal_capacity = round(nominal_capacity_ah * NOMINAL_VOLTAGE, 2)
        cycles = int.from_bytes(buffer[12:14], byteorder='big', signed=False) 

        soc =  buffer[23]
        ntc_count =  buffer[26]
    #  print(datetime.now(),' ntc_count=' + str(ntc_count), flush=True)
            

        temp  = []
        sum = 0
        for i in range(ntc_count):
            temp.append( int.from_bytes(buffer[27+(i*2):29+(i*2)], byteorder='big', signed=False) )
            temp[i] = temp[i] - 2731
            temp[i] = temp[i] /10
            sum += temp[i]
            global tempconfigpublished
            if tempconfigpublished!=True :  
                tempHaConf = '{"device_class": "temperature", "name": "Battery Temperature '+ str(i) + '", "state_topic": "' + STATE_TOPIC + '/state", "unit_of_measurement": "°C", "value_template": "{{ value_json.temp_' + str(i) +'}}", "unique_id": "' + devId + '_temp_'+ str(i) + '", ' + deviceConf + '}' 
                client.publish(STATE_TOPIC + '_temperature_'+str(i) +'/config', tempHaConf, 0, True)
        
        tempconfigpublished=True
        temp_avg = round(sum/ntc_count,1)
        # end do if

    json = '{'
    json += '"voltage":' + str(voltage) + ','
    json += '"current":' + str(current) + ','
    json += '"power":' + str(power) + ','  
    json += '"power_charging":' + str(power_charging) + ','  
    json += '"power_discharging":' + str(power_discharging) + ','   
    json += '"remaining_capacity":' + str(remaining_capacity) + ','
    json += '"nominal_capacity":' + str(nominal_capacity) + ','
    json += '"cycles":' + str(cycles) + ','
    json += '"soc":' + str(soc) + ','
    json += '"temp_avg":' + str(temp_avg)    
    for i in range(ntc_count):
           json +=  ', "temp_' + str(i) + '":' + str(temp[i]) 
    json += '}'
   # print(datetime.now(),json)
    publish(STATE_TOPIC +'/state', json)




def get_individual_cell_voltage():

    global cell_voltage
    global cell_voltageMax
    global cell_voltageMin

    res = cmd(CMD_CELL_VOLTAGES, 55, 0x04, 9)  # for 24s (4+2*24+3)
    if res is None:
        return
    if len(res) > 0:
        
        buffer = res[0]

        if len(buffer) < 9: # min 1 cell
            print(datetime.now(),' response to short', flush=True)
            return

        n_cells =  int((len(buffer)-7)/2)
                
        cell_voltage  = []
        cell_voltageMax = 0
        cell_voltageMin = 100

        for i in range(n_cells):
            cell_voltage.append( int.from_bytes(buffer[4+(i*2):6+(i*2)], byteorder='big', signed=False) )
            cell_voltage[i] = cell_voltage[i]/1000

            if cell_voltage[i] > cell_voltageMax :
                cell_voltageMax = cell_voltage[i]

            if cell_voltage[i] < cell_voltageMin :
                cell_voltageMin = cell_voltage[i]                

            global cellvoltagepublished
            if cellvoltagepublished!=True :  
                tempCellConf = '{"device_class": "voltage", "name": "Battery Cell '+ str(i+1).zfill(2) + '", "state_topic": "' + STATE_TOPIC + '/state_cell", "unit_of_measurement": "V", "value_template": "{{ value_json.cell_' + str(i+1).zfill(2) +'}}", "unique_id": "' + devId + '_cell_'+ str(i+1).zfill(2) + '", ' + deviceConf + '}' 
                client.publish(STATE_TOPIC + '_cell_'+str(i+1).zfill(2) +'/config', tempCellConf, 0, True)
                if i==0 :
                    tempCellConf = '{"device_class": "voltage", "name": "Battery Cell Min", "state_topic": "' + STATE_TOPIC + '/state_cell", "unit_of_measurement": "V", "value_template": "{{ value_json.cell_Min}}", "unique_id": "' + devId + '_cell_Min", ' + deviceConf + '}' 
                    client.publish(STATE_TOPIC + '_cell_Min/config', tempCellConf, 0, True)
                    tempCellConf = '{"device_class": "voltage", "name": "Battery Cell Max", "state_topic": "' + STATE_TOPIC + '/state_cell", "unit_of_measurement": "V", "value_template": "{{ value_json.cell_Max}}", "unique_id": "' + devId + '_cell_Max", ' + deviceConf + '}' 
                    client.publish(STATE_TOPIC + '_cell_Max/config', tempCellConf, 0, True)

        cellvoltagepublished=True



        json = '{ "cells":' + str(n_cells) 
        for i in range(n_cells):
            json +=  ', "cell_' + str(i+1).zfill(2) + '":' + str(cell_voltage[i]) 

        json +=  ', "cell_Min":' + str(cell_voltageMin) 
        json +=  ', "cell_Max":' + str(cell_voltageMax) 
        json += '}'
    # print(datetime.now(),json)
        publish(STATE_TOPIC +'/state_cell', json)



sleep_time = float(os.environ['DEVICE_POLLING_INTERVAL'])

selftest_requests(CMD_BATTERY_STATE, CMD_CELL_VOLTAGES)

while True:
    ser = serial.Serial(os.environ['DEVICE'], 9600, timeout=2, write_timeout=2, exclusive=True)  # open serial port
    get_battery_state()
    get_individual_cell_voltage()
    ser.close()
    time.sleep(sleep_time)
    
ser.close()
print(datetime.now(),'done')