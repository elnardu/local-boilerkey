import json
import os
import pyqrcode
import base64

from boilerkey import getConfig, getCounter

config = getConfig()
counter = getCounter()

url = 'otpauth://hotp/{name}?secret={secret}&counter={counter}'.format(
    name=config['customer_name'],
    secret=base64.b32encode(config['hotp_secret'].encode()).decode(),
    counter=counter
)

print('Authenticator url:')
print(url)

url = pyqrcode.create(url)
url.svg('qrcode.svg', scale=4)
print('QR code saved in "qrcode.svg"')
