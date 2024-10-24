from dotenv import load_dotenv, dotenv_values 
import requests
import argparse
import json
import sys
import os

BLUE = "\033[94m"
GREEN = "\033[92m"
RESET = "\033[0m"

load_dotenv()

grafana_token = os.getenv("GRAPHANA_TOKEN")
grafana_url = "http://192.168.1.104:3000/"
infludb_url = "http://192.168.1.104:8086/"

provisioning_header = {
    "Content-Type":"application/json",
    "Authorization":f"Bearer {grafana_token}"
}

datasource_header = {
    "Content-Type":"application/json",
    "Applicaiton":"application/json",
    "Authorization":f"Bearer {grafana_token}"
}

influx_db_get_measurments_header = lambda database_name : {
    "db": database_name,
    "q": "SHOW MEASUREMENTS"
}

influxdb_get_fields_header = lambda database_name, measurment_name : {
    "db": database_name,
    "q": f"SHOW FIELD KEYS FROM {measurment_name}" 
}

alert_rules_url = "api/v1/provisioning/alert-rules/"
dashboard_url = "api/dashboards/uid/"
update_dashboard_url = "api/dashboards/db/"
datasource_url = "api/datasources/"
query_url = "query/"
search_url = "api/search/"

main_dashboard_uid = "c675bf69-22d2-4803-a767-9a20f7eb3869"
main_folder_uid = "c647d423-8003-4ae5-b26a-8495098f82b2"
rule_group = "10 Sec Evaluation Group"

class Threshold:
    thresholds  = []

    def __init__(self, alertJson):
        self.alertJson = alertJson

    def getName(self): # Returns title of Alert
        return self.alertJson["title"] 

    def getThreshold(self): # Returns numerical value of Alert
        return self.alertJson["data"][2]["model"]["conditions"][0]["evaluator"]["params"][0]

    def getStateString(self): # Return 'True' or 'False' state of Alert
        return "True" if self.alertJson["isPaused"] else "False"

    def getAnnotatedDashboardUid(self): # returns Uid of Dashboad associated with Alert
        return self.alertJson["annotations"]["__dashboardUid__"]

    def getAlertId(self): # Returns Alert Uid
        return self.alertJson["uid"]
    
    def getDatasourceUid(self): # Returns the Uid of the Data source, i.e. which Influx DB database 
        return self.alertJson["data"][Threshold.getJsonArrayIndex("refId", self.alertJson["data"], "A")[0]]["datasourceUid"]

    def getMeasurement(self): # Returns name of measurement from Influx DB database 
        return self.alertJson["data"][Threshold.getJsonArrayIndex("refId", self.alertJson["data"], "A")[0]]["measurement"]
    
    def getFeild(self): # Returns name of Feild from Influx DB measurement
        a_refId_index = Threshold.getJsonArrayIndex("refId", self.alertJson["data"], "A")[0]
        feild_type_index = Threshold.getJsonArrayIndex("type", self.alertJson["data"][a_refId_index]["select"][0], "field")
        return self.alertJson["data"][a_refId_index]["select"][0][feild_type_index]["params"][0]
    
    def getAllDashboards(self): # Returns dictionary of dashboard Ui 
        dashboards = {}
        for dashboard in httpGetRequest(grafana_url+search_url):
            if dashboard["type"] != "dash-db":
                continue
            for panel in httpGetRequest(grafana_url+dashboard_url+dashboard["uid"])["dashboard"]["panels"]:
                if self.checkPanelMatch(panel):
                    dashboards[dashboard] = panel["num"]
    
        return dashboards
    
    def checkPanelMatch(self, panel): # Checks to see if datasource parameters match for a dashboad panel
        return panel["targets"][0]["datasource"]["uid"] == self.getDatasourceUid() \
            and panel["targets"][0]["measurement"] == self.getMeasurement() \
            and panel["targets"][0]["select"][0][Threshold.getJsonArrayIndex("type", panel["targets"][0]["select"][0], "field")]["params"][0] == self.getFeild()
    
    def setThresholdValue(self, value):
        self.alertJson["data"][2]["model"]["conditions"][0]["evaluator"]["params"][0] = value
        httpPutRequest(alert_rules_url+self.getAlertId(), self.alertJson)

    def setDashboardThreshold(self, value, editJustAlertJson=True):
        if editJustAlertJson is None or editJustAlertJson is True:
            self.alertJson["data"][2]["model"]["conditions"][0]["evaluator"]["params"][0] = value

            httpPutRequest(alert_rules_url+self.getAlertId(), self.alertJson)
        if editJustAlertJson is False or editJustAlertJson is True:

            for dashboardId, panelNum in self.getAllDashboards().items():

                thresholdNum = None
                dashboardJson = json.loads(httpGetRequest(grafana_url+dashboard_url+dashboardId))

                if (Threshold.getJsonArrayIndex("color", dashboardJson["dashboard"]["panels"][panelNum]["fieldConfig"]["defaults"]["thresholds"]["steps"], "orange")):

                if "Warning" in self.getName() and "Upper" in self.getName():
                    thresholdNum = Threshold.getJsonArrayIndex("color", dashboardJson["dashboard"]["panels"][panelNum]["fieldConfig"]["defaults"]["thresholds"]["steps"], "orange")[0]
                elif "Critical" in self.getName() and "Upper" in self.getName():
                    thresholdNum = Threshold.getJsonArrayIndex("color", dashboardJson["dashboard"]["panels"][panelNum]["fieldConfig"]["defaults"]["thresholds"]["steps"], "red")[0]
                elif "Warning" in self.getName() and "Lower" in self.getName():
                    thresholdNum = Threshold.getJsonArrayIndex("color", dashboardJson["dashboard"]["panels"][panelNum]["fieldConfig"]["defaults"]["thresholds"]["steps"], "orange")[-1]
                elif "Critical" in self.getName() and "Lower" in self.getName():
                    thresholdNum = Threshold.getJsonArrayIndex("color", dashboardJson["dashboard"]["panels"][panelNum]["fieldConfig"]["defaults"]["thresholds"]["steps"], "red")[-1]

                dashboardJson["dashboard"]["panels"][panelNum]["fieldConfig"]["defaults"]["thresholds"]["steps"][thresholdNum]["value"] = value

                httpPostRequest(update_dashboard_url, dashboardJson)

    def setDashboardThresholdState(self, state):
        if state == "ON":
            self.alertJson["isPaused"] = bool(False)
            self.setDashboardThreshold(self.alertJson["data"][2]["model"]["conditions"][0]["evaluator"]["params"][0], False)

            for dashboardId in self.getAllDashboards():
                dashboardJson = json.loads(httpGetRequest(grafana_url+dashboard_url+dashboardId))

                for panelNum in Threshold.getJsonArrayIndex("title", dashboardJson["dashboard"]["panels"], Threshold.removeDescriptors(self.getName())):
                    thresholdNum = Threshold.getJsonArrayIndex("value", dashboardJson["dashboard"]["panels"][panelNum]["fieldConfig"]["defaults"]["thresholds"]["steps"], None)[0]
                    dashboardJson["dashboard"]["panels"][panelNum]["fieldConfig"]["defaults"]["thresholds"]["steps"][thresholdNum]["color"] = "green"

                    httpPostRequest(update_dashboard_url, dashboardJson)

        elif state == "OFF":
            self.alertJson["isPaused"] = bool(True)
            self.setDashboardThreshold(999999, False)

            for dashboardId in self.getAllDashboards():
                dashboardJson = json.loads(httpGetRequest(grafana_url+dashboard_url+dashboardId))
                for panelNum in Threshold.getJsonArrayIndex("title", dashboardJson["dashboard"]["panels"], Threshold.removeDescriptors(self.getName())):
                    thresholdNum = Threshold.getJsonArrayIndex("value", dashboardJson["dashboard"]["panels"][panelNum]["fieldConfig"]["defaults"]["thresholds"]["steps"], None)[0]
                    dashboardJson["dashboard"]["panels"][panelNum]["fieldConfig"]["defaults"]["thresholds"]["steps"][thresholdNum]["color"] = "text"

                    httpPostRequest(update_dashboard_url, dashboardJson)
        else:
            raise Exception(f"\"{state}\" not a valid state, must be \"ON\" or \"OFF\"")

        httpPutRequest(alert_rules_url+self.getAlertId(), self.alertJson)

    def __str__(self):
        return f"Name: {BLUE}{self.getName():<{50}}{RESET} | Value: {GREEN}{self.getThreshold():<{15}}{RESET} | Silenced: {GREEN}{self.getStateString():<{20}}{RESET}"

    @staticmethod
    def getJsonArrayIndex(subfield, json, value):
        arrIndices = []
        for index, subJson in enumerate(json):
            if value == subJson[subfield]:
                arrIndices.append(index)
                break

        if len(arrIndices) == 0:
            raise Exception(f"{value} is not found in Json Array {json}")
        return arrIndices

    @staticmethod
    def getThresholdFromName(name, multipleThresholds=False):
        result = []
        for threshold in Threshold.thresholds:
            if name in threshold.getName():
                result.append(threshold)

        if result is []:
            raise Exception(f"Threshold {name} does not exist")
        return result if multipleThresholds else result[0]

    @staticmethod
    def removeDescriptors(string):
        return string.replace("Warning", "").replace("Critical", "").replace("Alert", "").replace("Upper").replace("Lower").rstrip()

def httpGetRequest(url, header=provisioning_header):
    request = requests.get(url, headers=header)
    if request.status_code != 200:
        raise Exception(f"Error in request GET: {json.dumps(request.json())}")
    return json.dumps(request.json())

def httpPutRequest(url, jsonMessage, header=provisioning_header):
    request = requests.put(url, data=json.dumps(jsonMessage), headers=header)
    if request.status_code != 200:
        raise Exception(f"Error in request PUT: {json.dumps(request.json())}")
    return json.dumps(request.json())

def httpPostRequest(url, jsonMessage, header=provisioning_header):
    request = requests.post(url, data=json.dumps(jsonMessage), headers=header)
    if request.status_code != 200:
        raise Exception(f"Error in request POST: {json.dumps(request.json())}")
    return json.dumps(request.json())

def httpDeleteRequest(url, jsonMessage, header=provisioning_header):
    request = requests.delete(url, data=json.dumps(jsonMessage), headers=header)
    if request.status_code != 200:
        raise Exception(f"Error in request DELETE: {json.dumps(request.json())}")
    return json.dumps(request.json())

def createAlert(threshold, state, bound_type, alert_type):
    print(f"Creating alert ... Enter in values below:")
            
    databases = {database["name"]:database["uid"] for database in httpGetRequest(grafana_url+datasource_url, datasource_header)}
    database = getCheck("Influx DB databases", databases.keys)

    measurements = httpGetRequest(infludb_url+query_url, influx_db_get_measurments_header(database))['results'][0]['series'][0]['values']
    measurment = getCheck(f"measurement from database {database}", measurements)

    fields = [field[0] for field in httpGetRequest(infludb_url+query_url, influxdb_get_fields_header(database, measurment))['results'][0]['series'][0]['values']]
    field = getCheck(f"field from measurment {measurment}", fields)

    no_data = strictInput("State alert when no data? ('OK'/'Alerting')", ["OK", "Alerting"])

    with open('alert_template.json', 'r') as file:
        alert_template = json.loads(file)

        alert_template["ruleGroup"] = main_dashboard_uid
        alert_template["folderUID"] = main_folder_uid
        alert_template["title"] = 

        a_refId_index = Threshold.getJsonArrayIndex("refId", alert_template["data"], "A")[0]
        c_refId_index = Threshold.getJsonArrayIndex("refId", alert_template["data"], "C")[0]

        alert_template["data"][a_refId_index]["datasourceUid"] = databases[database]
        alert_template["data"][a_refId_index]["model"]["datasource"]["uid"] = databases[database]
        alert_template["data"][a_refId_index]["measurement"] = measurment

        feild_type_index = Threshold.getJsonArrayIndex("type", alert_template["data"][a_refId_index]["select"][0], "field")
        alert_template["data"][a_refId_index]["select"][0][feild_type_index]["params"][0] = field
        alert_template["data"][a_refId_index]["select"][0][feild_type_index]["type"] = bound_type

        alert_template["data"][c_refId_index]["model"]["conditions"][0]["evaluator"]["params"][0] = threshold

        alert_template["noDataState"] = no_data
        
        if strictInput("Configure additional dashboard? (y/n) ", ["y", "n"]) == "y":

            alert_template["annotations"]["__dashboardUid__"] =  $$$$
            alert_template["annotations"]["__panelId__"] =  $$$$

        if state == "ON":
            alert_template["isPaused"] = bool(False)
        elif state == "OFF":
            alert_template["isPaused"] = bool(True)
        else:
            raise Exception(f"State {state} must be 'ON' or 'OFF'")

        print(f"Successfully created ")
    return Threshold(alert_template)

def strictInput(question, correctValues):
    while True:
        answer = input(question)
        if answer in correctValues:
            return answer
        else:
            print(f"Incorrect value: {answer}, enter correct value: '{', '.join(correctValues)}'")

def getCheck(parameterName, parameters):
    print(f"Choose {parameterName}, or number from list:")
    print("\n".join(f"{index}. {parameter}" for index, parameter in enumerate(parameters)))
    
    parameter = input("Name or Index: ")

    while True:
        if parameter in parameters:
            return parameter
        elif parameter.isdigit() and int(parameter) < len(parameters):
            return parameters[parameter]
        else:
            parameter = input(f"'{parameter}' not in {parameterName} list or in range of possible indexes, retry: ")
    
def getArguments():
    parser = argparse.ArgumentParser(description='edit and view threshold values')

    parser.add_argument("--name", default=None, type=str, help="enter EXACT threshold name, to view names run program w/o arguments")
    parser.add_argument("--threshold", default=None, type=float, help="float value for threshold")
    parser.add_argument("--state", default=None, type=str, help="'ON' or 'OFF'")
    parser.add_argument("--create_upper_critical", action="store_true", help="create critical upper bound alert")
    parser.add_argument("--create_lower_critical", action="store_true", help="create critical lower bound alert")
    parser.add_argument("--create_upper_warning", action="store_true", help="create critical upper bound alert")
    parser.add_argument("--create_lower_warning", action="store_true", help="create critical lower bound alert")
    parser.add_argument("--delete", action="store_true", type=str, help="delete alert")
    parser.add_argument("--json", default=None, type=str, help="debug only")

    return parser.parse_args()

if __name__ == "__main__":
    try:
        arguments = getArguments()

        alerts = json.loads(httpGetRequest(grafana_url+alert_rules_url))

        for alert in alerts:
            Threshold.thresholds.append(Threshold(alert))

        if arguments.create_upper_critical is not None ^ arguments.create_upper_warning is not None ^ \
           arguments.create_lower_critical is not None ^ arguments.create_lower_warning ^ \
           arguments.delete is not None:
            if arguments.create_upper_critical and arguments.threshold and arguments.state:                
                Threshold.thresholds.append(createAlert(arguments.threshold, arguments.state, "gt", "Critical"))
            elif arguments.create_lower_critical and arguments.threshold and arguments.state:
                Threshold.thresholds.append(createAlert(arguments.threshold, arguments.state, "lt", "Critical"))
            elif arguments.create_upper_warning and arguments.threshold and arguments.state:
                Threshold.thresholds.append(createAlert(arguments.threshold, arguments.state, "lt", "Warning"))
            elif arguments.create_lower_warning and arguments.threshold and arguments.state:
                Threshold.thresholds.append(createAlert(arguments.threshold, arguments.state, "gt", "Warning"))

            elif :
                confirmation = strictInput(f"Are you sure you want to delete: '{arguments.delete}' (Y/n)", ["Y", "n"])
                if confirmation == "Y":
                    httpDeleteRequest()
                else:
                    quit()
                
        if arguments.name is not None:
            if arguments.threshold is not None and arguments.state is not None:
                raise Exception("Edit one property per request")

            if arguments.threshold is not None:
                threshold = Threshold.getThresholdFromName(arguments.name)
                if threshold.getStateString() == "False":
                    threshold.setDashboardThreshold(arguments.threshold)
                else:
                    threshold.setThresholdValue(arguments.threshold)

            if arguments.state is not None:
                thresholds = Threshold.getThresholdFromName(arguments.name, True)
                for threshold in thresholds:
                    threshold.setDashboardThresholdState(arguments.state)

            if arguments.json == "alert":
                print(json.dumps(httpGetRequest(grafana_url+alert_rules_url+threshold.getAlertId())))
                quit()

            if arguments.json == "dashboard":
                print(json.dumps(httpGetRequest(grafana_url+dashboard_url+threshold.getDashboardId())))
                quit()

        for enum, threshold in enumerate(json.loads(httpGetRequest(grafana_url+alert_rules_url))):
            Threshold.thresholds[enum] = Threshold(threshold)
            print(Threshold(threshold))

    except Exception as exception:
        if "Error in request" in str(exception):
            print(f"ERROR in request: {str(exception)}")
            print("Rerunning Program ... ")

            python = sys.executable
            os.execv(python, [python] + sys.argv)
        else:
            raise exception
        