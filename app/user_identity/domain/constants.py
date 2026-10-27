import re

CELLPHONE_PATTERN = re.compile(r'^\+51 9\d{8}$')
USERNAME_PATTERN = re.compile(r'^[a-z][a-z0-9]*$')
PASSWORD_PATTERN = re.compile(r'^[a-zA-Z0-9]{8,50}$')
EMAIL_PATTERN = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
MAX_LENGTH = 250
MAX_USERNAME_LENGTH = 50
NAME_PATTERN = re.compile(r'^[a-záéíóúñü]+( [a-záéíóúñü]+)*$')
