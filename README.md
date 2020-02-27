# BöilerKey

1. Use python 3
2. Install some packages `pip3 install pyotp requests`
3. `python3 boilerkey.py`
4. ???
5. PROFIT!!!

# Authenticator Support

1. Run the initial setup
2. `python3 gencode.py`
3. Use the qr code or the link
4. Remove `config.json` and `counter.json` (You should not use the same duo configuration for your local script and authenticator since it will eventually desync. Configure them as separate devices on the boilerkey page)

## Warning! Not as [safe](https://xkcd.com/538/) as boilerkey.
