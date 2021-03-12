import corec_utils
import boilerkey
import time
import datetime


def getWhenAvailable(username, password, timeStr, targetDate, interval):
    # initialize CorecSession
    with corec_utils.CorecSession() as sesh:
        # ensure we log in by allowing 3 attempts
        for i in range(0,3):
            # log in to recwell
            if not sesh.authWithRecwell(username, boilerkey.generatePassword()):
                print("Error authenticating!!!")
                time.sleep(10)
            else:
                break
        if not sesh.authed:
            print("Could not authenticate! Check username/password")
            return False

        apptBooked = False
        while not apptBooked:
            appData = None

            for i in range(0,3):
                # This will store dictionary of availble CorecAppointment instances
                #   in appData
                appData = sesh.getAppointmentsData(targetDate)
                if not appData:
                    print("Error getting data! Did you enter an invalid date?")
                    time.sleep(10)
                else:
                    break

            if appData and timeStr in appData:
                # check if appointment already reserved
                if appData[timeStr].canCancel():
                    print(f"Appointment already reserved at {datetime.datetime.now()}")
                    return False
                # only move forward if spots available
                if appData[timeStr].canReserve():
                    for i in range(0,3):
                        # Getting appointment requires a CorecAppointent instance as an argument
                        if not sesh.getAppointment(appData[timeStr]):
                            print("Error getting appointment!")
                            time.sleep(10)
                        else:
                            return True
            else:
                print("Invalid data for attempting to get appointment!")

            time.sleep(interval)

def main():
    USERNAME = input("Enter Purdue Username: ")
    if not USERNAME:
        USERNAME = "jgleeson"

    targetMonth = input("Enter target month(0-12): ")
    targetDay = input("Enter target day(0-31): ")
    targetYear = input("Enter target year: ")

    targetMonth = int(targetMonth)
    targetDay = int(targetDay)
    targetYear = int(targetYear)

    TARGET_DAY = datetime.date(targetYear, targetMonth, targetDay)


    TARGET_TIME = input("Enter time interval EXACTLY as shown on corec website\nExample: '9:20 - 10:40 AM'\n:")

    INTERVAL = 30

    # ensure credentials are set up
    boilerkey.check_setup()

    # get appointment
    if getWhenAvailable(USERNAME, boilerkey.generatePassword(), TARGET_TIME, TARGET_DAY, INTERVAL):
        print(f"Successfully got appointment at {datetime.datetime.now()}")

if __name__ == "__main__":
    main()
