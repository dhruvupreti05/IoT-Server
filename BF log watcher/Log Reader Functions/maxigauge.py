def get_values_from_file_maxiguage(self, mqtt_subsection, today):

    path = log_root + today + "\\" + "maxigauge " + today + ".log"

    #if os.not os.path.exists(path):
        #return None

    lastline = self.get_last_line(path).rsplit(",")
    timestamp = lastline[0] + "," + lastline[1]
    
    if (mqtt_subsection == "alice_pressure_ovc"):
        return (timestamp, float(lastline[index(lastline, "CH1")+3])) # CH 1
    elif (mqtt_subsection == "alice_pressure_still"):
        return (timestamp, float(lastline[index(lastline, "CH2")+3])) # CH 2
    elif (mqtt_subsection == "alice_pressure_diff_ch4"):
        return (timestamp, float(lastline[index(lastline, "CH4")+3])) # CH 4
    elif (mqtt_subsection == "alice_pressure_diff_ch3"):
        return (timestamp, float(lastline[index(lastline, "CH3")+3])) # CH 3
    elif (mqtt_subsection == "alice_pressure_tank"):
        return (timestamp, float(lastline[index(lastline, "CH5")+3])) # CH 5
    raise Exception(f"'{self.mqtt_subsection}' is not a valid request")