#### MQTT Bluefors Log Watcher ####

from datetime import datetime, timedelta
import paho.mqtt.client as mqtt
from functools import partial
from pathlib import Path
import time
import json
import pytz
import os

with open('config.json', 'r') as file:
    cofig = json.load(file)

name = cofig["name"]
log_root = cofig["log_root"]

write_interval = timedelta(seconds=2)
timezone = pytz.timezone("America/New_York")

with open('static_varibles.json', 'r') as file:
    static_vars = json.load(file)

mqtt_broker_host = static_vars["mqtt_broker_host"]
mqtt_broker_port = static_vars["mqtt_broker_port"]
mqtt_username = static_vars["mqtt_username"]
mqtt_password = static_vars["mqtt_password"]
mqtt_topic_prefix = static_vars["mqtt_topic_prefix"]

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.username_pw_set(mqtt_username, mqtt_password)

def index(array, value):
    index = array.index(value)
    if index == -1:
        raise Exception(f"{value} not found")
    else:
        return index

class DataSource:
    
    last_update_time = datetime.strptime('01-01-01,00:00:00',"%d-%m-%y,%H:%M:%S")

    def __init__(self, mqtt_subsections, get_value):
        self.mqtt_subsections = mqtt_subsections
        self.get_value = partial(get_value, self)

    @staticmethod
    def get_last_line(filepath):
        file_path = Path(filepath)
        if file_path.is_file():
            with open(file_path, 'rb') as f:
                try:  # catch OSError in case of a one line file
                    f.seek(-2, os.SEEK_END)
                    while f.read(1) != b'\n':
                        f.seek(-2, os.SEEK_CUR)
                except OSError:
                    f.seek(0)
                return f.readline().decode().strip()
        else:
            raise Exception(f"File path: '{file_path}' is not a file")

while True:
    today = datetime.now().strftime("%y-%m-%d")
    
    if not os.path.exists(log_root):
        time.sleep(3)
        continue
         
    dataSources = [ 
        DataSource(["alice_temp_50k", "alice_temp_4k", "alice_temp_still", "alice_temp_mxc"], get_values_from_tempChnFile),
        DataSource(["alice_pressure_ovc", "alice_pressure_still", "alice_pressure_diff_ch4", "alice_pressure_diff_ch3", "alice_pressure_tank"], get_values_from_file_maxiguage),
        DataSource(["alice_compressor_water_in","alice_compressor_water_out", "alice_compressor_oil_temp", "alice_compressor_err"], get_values_from_file_status),
        DataSource(["alice_flowmeter"], get_values_from_file_flowmeter) ]
    
    client.connect(mqtt_broker_host, mqtt_broker_port)
    
    while datetime.now().strftime("%y-%m-%d") == today:
        for enum, dataSource in enumerate(dataSources):
            payload = {}
            for mqtt_subsection in dataSource.mqtt_subsections:
                
                last_value = dataSource.get_value(mqtt_subsection, today)

                if last_value is None:
                    print(f"Value not found: {mqtt_subsection}")
                    continue

                timestamp_str = last_value[0]
                timestamp = datetime.strptime(timestamp_str, "%d-%m-%y,%H:%M:%S")
                value = last_value[1]
                                
                payload[mqtt_subsection] = value 
            
            if (timestamp - dataSource.last_update_time) > write_interval:
                mqtt_payload = json.dumps(payload)
                client.publish(mqtt_topic_prefix, mqtt_payload)
                print('Sent MQTT message:', mqtt_topic_prefix, '-', mqtt_payload)
                dataSource.last_update_time = timestamp
            
        time.sleep(3)

    time.sleep(60)

