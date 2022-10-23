#!/usr/bin/python3




import serial
import binascii
import time
import os
import paho.mqtt.client as mqtt
from datetime import datetime

tempconfigpublished = False
BMS_Online = False



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
STATUS_TOPIC = STATE_TOPIC + '_status'
deviceConf = '"device": {"manufacturer": "unknow", "name": "Smart BMS", "identifiers": ["' + devId + '"]}'


# publish MQTT Discovery configs to Home Assistant
socHaConf = '{"device_class": "battery", "name": "Battery SOC", "state_topic": "' + STATE_TOPIC +'/state", "unit_of_measurement": "%", "value_template": "{{ value_json.soc}}", "unique_id": "' + devId + '_soc", ' + deviceConf + ', "json_attributes_topic": "' + STATUS_TOPIC + '/state"}' 
client.publish(STATE_TOPIC +'_soc/config', socHaConf, 0, True)

voltageHaConf = '{"device_class": "voltage", "name": "Battery Voltage", "state_topic": "' + STATE_TOPIC +'/state", "unit_of_measurement": "V", "value_template": "{{ value_json.voltage}}", "unique_id": "' + devId + '_voltage", ' + deviceConf + '}'
client.publish(STATE_TOPIC + '_voltage/config', voltageHaConf, 0, True)

currentHaConf = '{"device_class": "current", "name": "Battery Current", "state_topic": "' + STATE_TOPIC +'/state", "unit_of_measurement": "A", "value_template": "{{ value_json.current}}", "unique_id": "' + devId + '_current", ' + deviceConf + '}' 
client.publish(STATE_TOPIC + '_current/config', currentHaConf, 0, True)

power_chargingHaConf = '{"device_class": "power", "name": "Battery Power Charging", "state_topic": "' + STATE_TOPIC +'/state", "unit_of_measurement": "W", "value_template": "{{ value_json.power_charging}}", "unique_id": "' + devId + '_power_charging", ' + deviceConf + '}' 
client.publish(STATE_TOPIC + '_power_charging/config', power_chargingHaConf, 0, True)

power_dischargeHaConf = '{"device_class": "power", "name": "Battery Power Discharging", "state_topic": "' + STATE_TOPIC +'/state", "unit_of_measurement": "W", "value_template": "{{ value_json.power_discharging}}", "unique_id": "' + devId + '_power_discharging", ' + deviceConf + '}' 
client.publish(STATE_TOPIC + '_power_discharging/config', power_dischargeHaConf, 0, True)

remaining_capacityHaConf = '{"device_class": "current", "name": "Battery Remaining Capacity", "state_topic": "' + STATE_TOPIC +'/state", "unit_of_measurement": "Ah", "value_template": "{{ value_json.remaining_capacity}}", "unique_id": "' + devId + '_remaining_capacity", ' + deviceConf + '}' 
client.publish(STATE_TOPIC + '_remaining_capacity/config', remaining_capacityHaConf, 0, True)

nominal_capacityHaConf = '{"device_class": "current", "name": "Battery Nominal Capacity", "state_topic": "' + STATE_TOPIC +'/state", "unit_of_measurement": "Ah", "value_template": "{{ value_json.nominal_capacity}}", "unique_id": "' + devId + '_nominal_capacity", ' + deviceConf + '}' 
client.publish(STATE_TOPIC + '_nominal_capacity/config', nominal_capacityHaConf, 0, True)

cyclesHaConf = '{"name": "Battery Cycles", "state_topic": "' + STATE_TOPIC +'/state", "unit_of_measurement": "", "value_template": "{{ value_json.cycles}}", "unique_id": "' + devId + '_cycles", ' + deviceConf + '}' 
client.publish(STATE_TOPIC + '_cycles/config', cyclesHaConf, 0, True)

tempAvgHaConf = '{"device_class": "temperature", "name": "Battery Temperature Avg", "state_topic": "' + STATE_TOPIC + '/state", "unit_of_measurement": "°C", "value_template": "{{ value_json.temp_avg}}", "unique_id": "' + devId + '_temp_avg", ' + deviceConf + '}' 
client.publish(STATE_TOPIC + '_temperature_avg/config', tempAvgHaConf, 0, True)



def cmd(command):
    res = []
    ser.reset_input_buffer()
    ser.write(command)
#    ser.flush()
    s = ser.read(50)
    if (s == b''):
        return res        
  #  print(datetime.now(),binascii.hexlify(s, ' '), flush=True)
    res.append(s)
    return res

def publish(topic, data):
    try:
        client.publish(topic, data, 0, False)
    except Exception as e:
        print(datetime.now(),"Error sending to mqtt: " + str(e))



def get_battery_state():
    global BMS_Online

    res = cmd(b'\xdd\xa5\x03\x00\xff\xfd\x77')
    if len(res) < 1:
        if BMS_Online != False:
            BMS_Online = False
            print(datetime.now(),'Empty response get_battery_state. BMS Offline. Low power mode?', flush=True)
            json = '{'
            json += '"current": 0 ,'            
            json += '"power_charging": 0 ,'  
            json += '"power_discharging": 0'   
            json += '}'
            publish(STATE_TOPIC +'/state', json)
        return
    
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

    remaining_capacity = int.from_bytes(buffer[8:10], byteorder='big', signed=False) / 100
    nominal_capacity = int.from_bytes(buffer[10:12], byteorder='big', signed=False) / 100
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
            tempHaConf = '{"device_class": "temperature", "name": "Battery Temperature '+ str(i) + '", "state_topic": "' + STATE_TOPIC + '/state", "unit_of_measurement": "°C", "value_template": "{{ value_json.temp_' + str(i) +'}}", "unique_id": "' + devId + '_current'+ str(i) + '", ' + deviceConf + '}' 
            client.publish(STATE_TOPIC + '_temperature_'+str(i) +'/config', tempHaConf, 0, True)
    
    tempconfigpublished=True

    json = '{'
    json += '"voltage":' + str(voltage) + ','
    json += '"current":' + str(current) + ','
    json += '"power_charging":' + str(power_charging) + ','  
    json += '"power_discharging":' + str(power_discharging) + ','   
    json += '"remaining_capacity":' + str(remaining_capacity) + ','
    json += '"nominal_capacity":' + str(nominal_capacity) + ','
    json += '"cycles":' + str(cycles) + ','
    json += '"soc":' + str(soc) + ','
    json += '"temp_avg":' + str(round(sum/ntc_count,1))    
    for i in range(ntc_count):
           json +=  ', "temp_' + str(i) + '":' + str(temp[i]) 
    json += '}'
   # print(datetime.now(),json)
    publish(STATE_TOPIC +'/state', json)



while True:
    ser = serial.Serial(os.environ['DEVICE'], 9600, timeout=2, write_timeout=2, exclusive=True)  # open serial port
    get_battery_state()
    ser.close()
    time.sleep(30)
    
ser.close()
print(datetime.now(),'done')