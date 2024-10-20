def get_values_from_tempChnFile(self, mqtt_subsection, today):
    channel = ""
    if mqtt_subsection == "alice_temp_50k": 
        channel = "CH1"
    elif mqtt_subsection == "alice_temp_4k":
        channel = "CH2"
    elif mqtt_subsection == "alice_temp_still":
        channel = "CH5"
    elif mqtt_subsection == "alice_temp_mxc":
        channel = "CH6"
       
    path = log_root + today + "\\" + channel + " T " + today + ".log"

    if not os.path.exists(path) and channel == "CH6": # CH6 may not be present due to Bluefors Config
        return None

    lastline = self.get_last_line(path).rsplit(",")
    timestamp = lastline[0] + "," + lastline[1]
    
    return (timestamp, float(lastline[2]))