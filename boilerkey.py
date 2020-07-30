import base64
import json
import os
import sys
import pickle # json serialization loses data for cookie jars

try:
    import requests
    import pyotp
except ImportError:
    print("This script requires pyotp and requests packages")
    print("Please run 'pip3 install pyotp requests'")
    sys.exit(1)

CONFIG_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), "config.json")
COUNTER_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), "counter.json")
COOKIE_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), "cookies.p")

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
        return True, code
    except Exception:
        return False, None


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


def setCookies(cookieDict):
    with open(COOKIE_PATH, "wb") as f:
        pickle.dump(cookieDict, f)


def getCookies():
    # returns cookiejar object
    if os.path.isfile(COOKIE_PATH):
        with open(COOKIE_PATH, "rb") as f:
            return pickle.load(f)
    else:
        return None


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

def getLtSecret(html):
    # length of secret is always 41
    ltLen = 41
    preStr = '<input type="hidden" name="lt" value="'
    matchIndex = html.find(preStr)
    if matchIndex != -1:
        if len(html) > matchIndex + ltLen:
            # need to shift index back to include 'LT-'
            startKeyIndex = matchIndex + len(preStr)
            endKeyIndex = startKeyIndex + ltLen
            return html[startKeyIndex:endKeyIndex]
    return None

def getExecutionSecret(html):
    # length of secret is always 4
    executionLen = 4
    preStr = '<input type="hidden" name="execution" value="'
    matchIndex = html.find(preStr)
    if matchIndex != -1:
        if len(html) > matchIndex + executionLen:
            startKeyIndex = matchIndex + len(preStr)
            endKeyIndex = startKeyIndex + executionLen
            return html[startKeyIndex:endKeyIndex]
    return None

def generateAuthCookies(save=False):
    # cookies do not expire, so you can save across runs

    conf = getConfig()
    if 'username' not in conf:
        print("You need to configure your username to use generateAuthCookies")
        return None

    loginUrl = "https://www.purdue.edu/apps/account/cas/login"

    payload = {
        'MIME Type': 'application/x-www-form-urlencoded',
        'username': conf["username"],
        'password': generatePassword(),
        # 'lt': None,
        # 'execution': None,
        '_eventId': 'submit',
        'submit': 'Login'
    }

    with requests.Session() as sesh:
        initGet = sesh.get(loginUrl)

        ltSecret = getLtSecret(initGet.text)
        executionSecret = getExecutionSecret(initGet.text)

        if not ltSecret or not executionSecret:
            print("Error: Secrets could not be parsed")
            return None
        else:
            payload['lt'] = ltSecret
            payload['execution'] = executionSecret
            loginPost = sesh.post(loginUrl, data=payload)

            # post-auth response from loginUrl will always contain this:
            if "Central Authentication Service" in loginPost.text:
                if save:
                    setCookies(sesh.cookies)
                return sesh.cookies
            else:
                print("Error: Check credentials or try again")
    return None

def askForInfo():
    print(
        """Hello there.
1. Please go to the BoilerKey settings (https://purdue.edu/boilerkey)
   and click on 'Set up a new Duo Mobile BoilerKey'
2. Follow the process until you see the qr code
3. Paste the link (https://m-1b9bef70.duosecurity.com/activate/XXXXXXXXXXX)
   under the qr code right here and press Enter"""
    )

    valid = False
    while not valid:
        link = input()
        valid, activationCode = validateLink(link)

        if not valid:
            print("Invalid link. Please try again")

    print(
        """4. (Optional) In order to generate full password (pin,XXXXXX),
   script needs your pin. You can leave this empty."""
    )

    pin = input()
    if len(pin) != 4:
        pin = ""
        print("Invalid pin")

    print(
        """5. (Optional) In order to generate authentication cookies,
    script needs your username (XXXXXXX@purdue.edu). You can leave this empty."""
    )

    username = input()

    activationData = getActivationData(activationCode)
    activationData["pin"] = pin
    if username:
        activationData["username"] = username
    createConfig(activationData)
    setCounter(0)
    print("Setup successful!")

    print("Here is your password: ", generatePassword())


def main():
    if not os.path.isfile(CONFIG_PATH) or not os.path.isfile(COUNTER_PATH):
        print("Configuration files not found! Running setup...")
        askForInfo()
    else:
        print(generatePassword())


if __name__ == "__main__":
    main()
