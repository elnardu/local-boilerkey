import json
import os
import pyqrcode
import base64
import sys

from boilerkey import getConfig, getCounter

config = getConfig()
counter = getCounter()

url = "otpauth://hotp/{name}?secret={secret}&counter={counter}".format(
    name=config["customer_name"],
    secret=base64.b32encode(config["hotp_secret"].encode()).decode(),
    counter=counter,
)

print("Authenticator url:")
print(url)


try:
    import pyqrcode
except ImportError:
    print("pyqrcode is not found")
    print("pip3 install pyqrcode")
    sys.exit(1)

url = pyqrcode.create(url)
url.svg("qrcode.svg", scale=4)
print('QR code saved in "qrcode.svg"')
