import corec_utils
import boilerkey
import time
import datetime

def getAndCancel(username, password, timeStr, targetDate):
    # initialize CorecSession
    with corec_utils.CorecSession() as sesh:
        # log in to recwell
        if not sesh.authWithRecwell(username, boilerkey.generatePassword()):
            print("Error authenticating!!!")

        # This will store dictionary of availble CorecAppointment instances
        #   in appData
        appData = sesh.getAppointmentsData(targetDate)
        if not appData:
            print("Error getting data!!! Did you authenticate?")

        # Getting appointment requires a CorecAppointent instance as an argument
        if timeStr in appData:
            if not sesh.getAppointment(appData[timeStr]):
                print("Error getting appointment!!! Did you authenticate?")

        # This will store dictionary of availble CorecAppointment instances
        #   in appData
        # NOTE: you must re-get the appointment data after an update
        appData = sesh.getAppointmentsData(targetDate)
        if not appData:
            print("Error getting data!!! Did you authenticate?")

        if timeStr in appData:
            # Canceling an appointment requires a CorecAppointent instance as an argument
            if sesh.cancelAppointment(appData[timeStr]):
                print(f"Canceled appointment for {targetDate} at {targetDate}")
