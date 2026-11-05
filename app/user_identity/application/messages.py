# Texts of the use cases: conflicts with existing data, and the notices to the user
# (in Spanish: the user reads them).

USER_ALREADY_EXISTS = 'User with {field} {value} already exists.'
# A duplicate found by the database (two registrations at once) does not know the value.
USER_FIELD_ALREADY_EXISTS = 'User with this {field} already exists.'

ACCOUNT_BLOCKED_NOTICE_SUBJECT = 'Tu cuenta de TurfBook fue bloqueada'
ACCOUNT_BLOCKED_NOTICE_BODY = (
    'Hola {name}, tu cuenta de TurfBook fue bloqueada por {failed_attempts} intentos '
    'fallidos de ingreso. Comunícate con TurfBook al {phone} o a {email} dentro de '
    'los próximos 7 días; si no, tu cuenta se cerrará.'
)
