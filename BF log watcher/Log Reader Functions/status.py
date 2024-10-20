def get_values_from_file_status(self, mqtt_subsection, today):
    
    path = log_root + today + "\\" + "Status_" + today + ".log"

    #if not os.path.exists(path):
        #return None

    lastline = self.get_last_line(path).rsplit(",")
    timestamp = lastline[0] + "," + lastline[1]
    
    if (mqtt_subsection == "alice_compressor_err"): 
        return (timestamp, float(lastline[index(lastline, "cpaerr")+1])) # cpaerr
    elif (mqtt_subsection == "alice_compressor_water_in"):
        return (timestamp, float(lastline[index(lastline, "cpatempwi")+1])) # cpatempwi
    elif (mqtt_subsection == "alice_compressor_water_out"):
        return (timestamp, float(lastline[index(lastline, "cpatempwo")+1])) # cpatempwo
    elif (mqtt_subsection == "alice_compressor_oil_temp"):
        return (timestamp, float(lastline[index(lastline, "cpatempo")+1])) # cpatempo
    raise Exception(f"'{self.mqtt_subsection}' is not a valid request")