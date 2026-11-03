import re

# Data formats of the project (Ticket Manager's conventions/data.md): `[0-9]`, never `\d`.
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
