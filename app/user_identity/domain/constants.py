import re

# Digits as `[0-9]`, never `\d`: in Python `\d` also matches the digits of other scripts.
CELLPHONE_PATTERN = re.compile(r'^\+519[0-9]{8}$')
CELLPHONE_LENGTH = 12
EMAIL_PATTERN = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
EMAIL_MIN_LENGTH = 6
EMAIL_MAX_LENGTH = 254
PASSWORD_MIN_LENGTH = 15
PASSWORD_MAX_LENGTH = 64
USERNAME_PATTERN = re.compile(r'^[a-z][a-z0-9]*$')
MAX_USERNAME_LENGTH = 50
NAME_PATTERN = re.compile(r'^[a-záéíóúñü]+( [a-záéíóúñü]+)*$')
MAX_LENGTH = 250
