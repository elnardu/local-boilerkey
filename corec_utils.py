import requests
import json
import datetime
from bs4 import BeautifulSoup

class CorecAppointment():
    """An object to hold corec appointment info
    :attribute participantId: :class:`str` instance recwell participantId
        hash string (can be NONE) this is used to cancel said
        appointment
    :attribute spots: :class:`int` instance recwell spots availble
        number (can be NONE)
    :attribute appointmentId: :class:`str` instance recwell appointmentId
        hash string
    :attribute timeSlotId: :class:`str` instance recwell timeSlotId
        hash string
    :attribute timeSlotInstanceId: :class:`str` instance recwell
        timeSlotInstanceId hash string
    :attribute timeStr: :class:`str` instance recwell time string
        ex: '9:00 - 10:00 am'
    :attribute date: :class:`datetime.date` instance appt date
    """
    def __init__(self, participantId, spots, appointmentId, timeSlotId, timeSlotInstanceId, timeStr, date):
        self.participantId = participantId
        self.spots = spots
        self.appointmentId = appointmentId
        self.timeSlotId = timeSlotId
        self.timeSlotInstanceId = timeSlotInstanceId
        self.timeStr = timeStr
        self.date = date

    def canCancel(self):
        """Helper to determine whether Appointment can be canceled
        returns True if user currently has appointment, else False

        :rtype: bool
        """
        if self.participantId:
            return True
        return False

    def canReserve(self):
        """Helper to determine whether Appointment can be acquired
        returns True if user can get appointment, else False

        :rtype: bool
        """
        if self.appointmentId and self.hasSpots():
            return True
        return False

    def hasSpots(self):
        """Helper to determine whether Appointment has spots available
        returns True if spots available, else False

        :rtype: bool
        """
        if self.spots:
            return self.spots > 0
        return False

    def __str__(self):
        """toString equivalen will return string representation of object

        :rtype: str
        """

        return f"date={self.date}, timeStr={self.timeStr}, participantId={self.participantId}, spots={self.spots}, appointmentId={self.appointmentId}, timeSlotId={self.timeSlotId}, timeSlotInstanceId={self.timeSlotInstanceId}"

class CorecSession(requests.Session):
    """A Requests session with included helpers for corec site automation
    Provides cookie persistence, connection-pooling, and configuration.
    Basic Usage:
      >>> import requests
      >>> s = requests.Session()
      >>> s.get('https://httpbin.org/get')
      <Response [200]>
    Or as a context manager::
      >>> with requests.Session() as s:
      ...     s.get('https://httpbin.org/get')
      <Response [200]>


      :attribute bookingId: :class:`str` instance recwell bookingId hash string
      :attribute selectedFacilityId: :class:`str` instance recwell
          selectedFacilityId hash string
    """

    def __init__(self):
        """Override Session constructor to set default attributes for the gym
        Still call super constructor to initialize Session
        """

        # id for the corec gym (opposed to pool etc)
        self.facilityId = "3b2e5aa2-1715-4852-bea4-34f472771330"
        # id for bookings for corec gym (opposed to pool etc)
        self.bookingId = "83456ef4-1d99-4e58-8e66-eb049941f7c1"

        # flag to tell if session is authenticated
        self.authed = False

        # call default Session constructor
        super().__init__()

    def authWithRecwell(self, username, password):
        """Helper function to authenticate session with recwell site

        After execution, session will be authenticated with recwell and able to
        send requests for making/canceling appointments

        :param username: :class:`str` instance purdue username
        :param password: :class:`str` instance one-time-password correlating
            with username (****,******)
        :rtype: Boolean: indicating whether login was successful
        """

        if self.authed:
            return True

        # get form data
        formGet = self.get("https://recwell.purdue.edu/Account/GetLoginOptions?returnURL=%2F&isAdmin=false")

        # find __RequestVerificationToken
        text = formGet.text
        subToFind = 'name="__RequestVerificationToken" type="hidden" value="'
        startInd = text.find(subToFind, text.find("frmExternalLogin")) + len(subToFind)
        RequestVerificationToken = text[startInd:text.find('"', startInd)]

        # create data dict to send as request body
        frmExternalLoginData = {
            '__RequestVerificationToken': RequestVerificationToken,
            'provider': 'Shibboleth'
        }
        formPost = self.post("https://recwell.purdue.edu/Account/ExternalLogin?ReturnUrl=%2Fbooking", data=frmExternalLoginData)

        # now at main purdue login form

        # find lt
        text = formPost.text
        subToFind = '<input type="hidden" name="lt" value="'
        startInd = text.find(subToFind) + len(subToFind)
        lt = text[startInd:text.find('"', startInd)]

        # find post url
        subToFind = '<form id="fm1" action="'
        startInd = text.find(subToFind) + len(subToFind)
        loginFormUrl = "https://www.purdue.edu" + text[startInd:text.find('"', startInd)]

        # create data dict to send as request body
        loginData = {
            'username': username,
            'password': password,
            'lt': lt,
            'execution': 'e1s1',
            '_eventId': 'submit',
            'submit': 'Login'
        }
        loginFormPost = self.post(loginFormUrl, data=loginData)

        # check for auth failure
        if "https://www.recwell.purdue.edu" not in loginFormPost.url and "https://www.purdue.edu/apps/account/cas/login" in loginFormPost.url:
            # possibly invalid credentials
            # raise ValueError("Invalid credentials")
            return False

        # now at continue site (only accessable with js off)

        # find post url
        text = loginFormPost.text
        subToFind = '<form action="'
        startInd = text.find(subToFind) + len(subToFind)
        continuePressUrl = text[startInd:text.find('"', startInd)]
        continuePressUrl = continuePressUrl.replace("&#x3a;", ":").replace("&#x2f;", "/")

        # find RelayState
        subToFind = 'name="RelayState" value="'
        startInd = text.find(subToFind) + len(subToFind)
        RelayState = text[startInd:text.find('"', startInd)]
        RelayState = RelayState.replace("&#x3a;", ":").replace("&#x2f;", "/")

        # find SAMLResponse
        subToFind = 'name="SAMLResponse" value="'
        startInd = text.find(subToFind) + len(subToFind)
        SAMLResponse = text[startInd:text.find('"', startInd)]

        # create data dict to send as request body
        continuePressPayload = {
            "RelayState": RelayState,
            "SAMLResponse": SAMLResponse,
            "submit": "Continue",
        }
        continuePressPayload = self.post(continuePressUrl, data=continuePressPayload)
        self.authed = True
        return True

    def getAppointment(self, appt):
        """Helper function to send booking request

        Send booking request to corec

        :param appt: class: 'CorecAppointment' instance

        :rtype: bool indicating success of appointment acquisition
        """

        if not appt.canReserve():
            return False

        if not self.authed:
            return False

        bookingId = self.bookingId
        selectedFacilityId = self.facilityId

        reqData = {
            "bookingId": bookingId,
            "facilityId": selectedFacilityId,
            "appointmentId": appt.appointmentId,
            "timeSlotId": appt.timeSlotId,
            "timeSlotInstanceId": appt.timeSlotInstanceId,
            "year": appt.date.year,
            "month": appt.date.month,
            "day": appt.date.day
        }

        attempt = self.post("https://recwell.purdue.edu/booking/reserve", data=reqData)

        # parse json out of response
        try:
            response = json.loads(attempt.text)
        except JSONDecodeError:
            # not authenticated
            # raise Exception("Not logged in")
            return False

        return response["Success"]

    def cancelAppointment(self, appt):
        """Helper function to send booking cancelation request

        Send booking cancelation request to corec

        :param appt: class: 'CorecAppointment' instance

        :rtype: bool indicating success of appointment acquisition
        """

        if not appt.canCancel():
            return False

        if not self.authed:
            return False

        bookingId = self.bookingId
        selectedFacilityId = self.facilityId

        delUrl = "https://recwell.purdue.edu/booking/delete/" + appt.participantId

        attempt = self.post(delUrl)

        # parse json out of response
        try:
            response = json.loads(attempt.text)
        except JSONDecodeError:
            # not authenticated
            # raise Exception("Not logged in")
            return False

        return response

    def getAppointmentsData(self, targetDay):
        """Helper function to get appointment data

        Send get request for target day. Returns dict of
        {time_str: `CorecAppointment` instance}
        where time_str is string of type "8 - 9:20 AM"

        :param target_day: :class:`datetime.date` instance target day to scrape
            appointments for
        :rtype: dict
        """

        # sub_to_find = ''
        # start_ind = text.find(sub_to_find) + len(sub_to_find)
        # selectedFacilityId = text[start_ind:text.find('"', start_ind)]
        # print(selectedFacilityId)

        appDataUrl = "https://recwell.purdue.edu/booking/{}/slots/{}/{}/{}/{}".format(self.bookingId, self.facilityId, targetDay.year, targetDay.month, targetDay.day)

        # check if this has odd status
        appData = self.get(appDataUrl)
        # print(app_data.text)
        if appData.text.startswith("<!DOCTYPE html>"):
            # raise Exception("Not logged in")
            return None

        soup = BeautifulSoup(appData.text, 'html.parser')
        bookingDivs = soup.findAll("div", class_="booking-slot-item")
        retData = {}
        for timecard in bookingDivs:
            participantId = timecard['data-participant-id']
            if participantId == "00000000-0000-0000-0000-000000000000":
                participantId = None

            timeRange = timecard.p.strong.text.strip()

            spots = timecard.span.text.strip().split(" ")[0]
            try:
                spots = int(spots)
            except Exception:
                if spots == "Booked":
                    spots = None
                spots = 0

            if timecard.div.button.has_attr('onclick'):
                resStr = timecard.div.button['onclick']
                resLis = resStr[8:-1].split(', ')
                appointmentId = resLis[0][1:-1]
                timeSlotId = resLis[1][1:-1]
                timeSlotInstanceId = resLis[2][1:-1]
                if spots > 0:
                    canRequest = True
            else:
                appointmentId = None
                timeSlotId = None
                timeSlotInstanceId = None
                canRequest = False

            retData[timeRange] = CorecAppointment(participantId, spots, appointmentId, timeSlotId, timeSlotInstanceId, timeRange, targetDay)

        return retData
