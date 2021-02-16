import base64
import json
import os
import sys
import random
import re
from string import ascii_lowercase

try:
    import requests
    import pyotp
except ImportError:
    print("This script requires pyotp and requests packages")
    print("Please run 'pip3 install pyotp requests'")
    sys.exit(1)

CONFIG_PATH = os.path.dirname(os.path.realpath(__file__)) + "/config.json"
COUNTER_PATH = os.path.dirname(os.path.realpath(__file__)) + "/counter.json"

# DO NOT LOSE YOUR WAAAAAAY!

__license__ = "WTFPL"
__author__ = "Russian election hackers"
__credits__ = ["ITaP", "Mitch Daniels"]


def getActivationData(code):
    print("Requesting activation data...")

    HEADERS = {"User-Agent": "okhttp/3.11.0"}

    PARAMS = {
        "app_id": "com.duosecurity.duomobile.app.DMApplication",
        "app_version": "2.3.3",
        "app_build_number": "323206",
        "full_disk_encryption": False,
        "manufacturer": "Google",
        "model": "Pixel",
        "platform": "Android",
        "jailbroken": False,
        "version": "6.0",
        "language": "EN",
        "customer_protocol": 1,
    }

    ENDPOINT = "https://api-1b9bef70.duosecurity.com/push/v2/activation/{}"

    res = requests.post(ENDPOINT.format(code), headers=HEADERS, params=PARAMS)

    if res.json().get("code") == 40403:
        print(
            "Invalid activation code."
            "Please request a new link in BoilerKey settings."
        )
        sys.exit(1)

    if not res.json()["response"]:
        print("Unknown error")
        print(res.json())
        sys.exit(1)

    return res.json()["response"]


def validateLink(link):
    try:
        assert "m-1b9bef70.duosecurity.com" in link
        code = link.split("/")[-1]
        assert len(code) == 20
        return code
    except Exception:
        return None


def createConfig(activationData):
    with open(CONFIG_PATH, "w") as f:
        json.dump(activationData, f, indent=2)
    print("Activation data saved!")


def getConfig():
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)


def setCounter(number):
    with open(COUNTER_PATH, "w") as f:
        json.dump({"counter": number}, f, indent=2)


def getCounter():
    with open(COUNTER_PATH, "r") as f:
        return json.load(f)["counter"]


def generatePassword():
    config = getConfig()
    counter = getCounter()

    hotp = pyotp.HOTP(base64.b32encode(config["hotp_secret"].encode()))

    hotpPassword = hotp.at(counter)

    if config.get("pin"):
        password = "{},{}".format(config.get("pin"), hotpPassword)
    else:
        password = hotpPassword

    setCounter(counter + 1)

    return password

def addBoilerKey(username, password, name="local_boilerkey"):
    """
    Send requests to purdue boilerkey management to add new boilerkey device

    Returns 20 digit code used for duomobile registration

    :param username: :class:`str` instance purdue username
    :param password: :class:`str` instance password correlating
        with username OTP: (****,******) OR 2fa password (****,push*)
    :param password: :class:`str` instance name to register new boilerkey as
        (Duplicate will have random string appended)
    :raises ValueError: for invalid credentials (username, password)
    :raises ValueError: for invalid name
    :rtype: str OR None
    """

    headers = {
    "User-Agent":
        "Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2272.101 Safari/537.36",
    }

    name_re = re.compile("^[a-zA-Z0-9_]{1,32}$")
    if not name_re.match(name):
        raise ValueError(f"Invalid name: '{name}'\nMust be:\n"
                         "\t-Under 32 characters\n"
                         "\t-Contain only a-Z 0-9 and '_'")
    with requests.Session() as s:
        s.headers.update(headers)
        main_get = s.get("https://www.purdue.edu/apps/account/BoilerKeySelfServe")

        # find lt secret
        text = main_get.text
        sub_to_find = '<input type="hidden" name="lt" value="'
        start_ind = text.find(sub_to_find) + len(sub_to_find)
        lt = text[start_ind:text.find('"', start_ind)]

        # find post url
        sub_to_find = '<form id="fm1" action="'
        start_ind = text.find(sub_to_find) + len(sub_to_find)
        login_form_url = "https://www.purdue.edu" + text[start_ind:text.find('"', start_ind)]

        login_payload = {
            'username': username,
            'password': password,
            'lt': lt,
            'execution': 'e1s1',
            '_eventId': 'submit',
            'submit': 'Login'
        }
        login_form_post = s.post(login_form_url, data=login_payload)

        # check for auth failure
        if "https://www.purdue.edu/apps/account/flows/BoilerKey" not in login_form_post.url and "https://www.purdue.edu/apps/account/cas/login" in login_form_post.url:
            raise ValueError("Invalid credentials")
        else:
            print("Authenticated successfully\nPlease allow ~1min for slow purdue sites")

        new_post_data = {
            "_eventId": "boilerKeyDuoMobileCreate",
            "_flowExecutionKey": "e1s1",
            "phoneName":None,
        }
        new_post = s.post("https://www.purdue.edu/apps/account/flows/BoilerKey?execution=e1s1", data=new_post_data)

        # get flow string number (required for request to be processed)
        text = new_post.url
        start_ind = text.find("e1s") + 3
        flow_str = "e1s" + text[start_ind:]

        cont_post_data = {
            "_eventId": "duoMobileCreateProcessDownloadAppAction",
            "_flowExecutionKey": flow_str
        }
        cont_post = s.post("https://www.purdue.edu/apps/account/flows/BoilerKey?execution={}".format(flow_str), data=cont_post_data)

        # get flow string number (required for request to be processed)
        text = cont_post.url
        start_ind = text.find("e1s") + 3
        flow_str = "e1s" + text[start_ind:]

        pin_post_data = {
            "_eventId": "duoMobileCreateProcessSetPinAction",
            "_flowExecutionKey": flow_str,
            "existingPin": password.split(",")[0]
        }
        pin_post = s.post("https://www.purdue.edu/apps/account/flows/BoilerKey?execution={}".format(flow_str), data=pin_post_data)

        # get flow string number (required for request to be processed)
        text = pin_post.url
        start_ind = text.find("e1s") + 3
        flow_str = "e1s" + text[start_ind:]

        name_post_data = {
            "_eventId": "duoMobileCreateProcessNameDeviceAction",
            "_flowExecutionKey": flow_str,
            "phoneName": name
        }

        name_post = s.post("https://www.purdue.edu/apps/account/flows/BoilerKey?execution={}".format(flow_str), data=name_post_data)

        for i in range(0,5):
            if "Sorry, you already have a Duo Mobile BoilerKey with that name" not in name_post.text:
                break

            # get flow string number (required for request to be processed)
            text = name_post.url
            start_ind = text.find("e1s") + 3
            flow_str = "e1s" + text[start_ind:]

            new_name = name + "_" + ''.join(random.choice(ascii_lowercase) for i in range(4))
            if not name_re.match(new_name):
                raise ValueError(f"Invalid name: '{name}'\nMust be:\n"
                                 "\t-Under 32 characters\n"
                                 "\t-Contain only a-Z 0-9 and '_'")
            name_post_data = {
                "_eventId": "duoMobileCreateProcessNameDeviceAction",
                "_flowExecutionKey": flow_str,
                "phoneName": new_name
            }

            name_post = s.post("https://www.purdue.edu/apps/account/flows/BoilerKey?execution={}".format(flow_str), data=name_post_data)

        text = name_post.text
        sub_to_find = 'https://m-1b9bef70.duosecurity.com/activate/'
        start_ind = text.find(sub_to_find)
        link = text[start_ind:text.find('"', start_ind)]

        return validateLink(link)

def askForInfo():
    print(
        """Hello there.
1. Please go to the BoilerKey settings (https://purdue.edu/boilerkey)
   and click on 'Set up a new Duo Mobile BoilerKey'
2. Follow the process until you see the qr code
3. Paste the link (https://m-1b9bef70.duosecurity.com/activate/XXXXXXXXXXX)
   under the qr code right here and press Enter"""
    )

    activationCode = None
    while not activationCode:
        link = input()
        activationCode = validateLink(link)

        if not activationCode:
            print("Invalid link. Please try again")

    print(
        """4. (Optional) In order to generate full password (pin,XXXXXX),
   script needs your pin. You can leave this empty."""
    )

    pin = input()
    if len(pin) != 4:
        pin = ""
        print("Invalid pin")

    activationData = getActivationData(activationCode)
    activationData["pin"] = pin
    createConfig(activationData)
    setCounter(0)
    print("Setup successful!")

    print("Here is your password: ", generatePassword())

def getInput():
    """
    Get username and password from user

    :rtype: tuple (username, password)
    """
    username = input("Purdue username\n:")
    while not username:
      username = input("\nYou must enter a username\nPurdue username\n:")

    pass_re = re.compile("\d{4},(\d{6}|push\d*)")
    password = input("Purdue password\n(Password may be of type '****,push', or '****,******')\n:")
    re_match = pass_re.match(password)
    while not re_match:
        password = input("\nInvalid password\nPurdue password\n(Password may be of type '****,push', or '****,******')\n:")
        re_match = pass_re.match(password)

    return username, password


def autoSetup():
    """
    Setup with automated boilerkey device creation

    :rtype: None
    """
    print("This setup will add a new boilerkey device to your account.\n"
          "Please note: you will receive an email notifying you your boilerkey settings have been changed\n"
          "If you choose to use '****,push' type password, you will need to allow login on duo mobile\n"
          "You may revoke access at any time from the boilerkey managment page\n\n"
          "Setup:")
    username, password = getInput()
    link = None
    while not link:
        try:
            link = addBoilerKey(username, password)
        except ValueError as ve:
            print('\n', ve)
            username, password = getInput()

    activationData = getActivationData(link)
    activationData["pin"] = password.split(',')[0]
    createConfig(activationData)
    setCounter(0)
    print("Setup successful!")

    print("Here is your password: ", generatePassword())

def main():
    if not os.path.isfile(CONFIG_PATH) or not os.path.isfile(COUNTER_PATH):
        print("Configuration files not found! Running setup...")
        autoSetup()
    else:
        print(generatePassword())


if __name__ == "__main__":
    main()
