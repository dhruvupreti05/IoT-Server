def get_values_from_file_flowmeter(self, mqtt_subsection, today):

    path = log_root + today + "\\" + "Flowmeter " + today + ".log"

    lastline = self.get_last_line(path)
    timestamp = lastline.rsplit(",")[0] + "," + lastline.rsplit(",")[1]

    return (timestamp, float(lastline.rsplit(",")[2]))