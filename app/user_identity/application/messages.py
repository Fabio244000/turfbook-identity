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

ACCOUNT_NOT_FOUND = 'The account does not exist.'

ACCOUNT_BLOCKED_BY_TURFBOOK_NOTICE_BODY = (
    'Hola {name}, TurfBook bloqueó tu cuenta. Comunícate con TurfBook al {phone} o a '
    '{email} dentro de los próximos 7 días; si no, tu cuenta se cerrará.'
)
ACCOUNT_UNBLOCKED_NOTICE_SUBJECT = 'Tu cuenta de TurfBook fue desbloqueada'
ACCOUNT_UNBLOCKED_NOTICE_BODY = (
    'Hola {name}, tu cuenta de TurfBook fue desbloqueada. Ya puedes ingresar con tu '
    'usuario y contraseña. Si tienes dudas, comunícate con TurfBook al {phone} o a '
    '{email}.'
)
ACCOUNT_CLOSED_NOTICE_SUBJECT = 'Tu cuenta de TurfBook fue cerrada'
ACCOUNT_CLOSED_NOTICE_BODY = (
    'Hola {name}, tu cuenta de TurfBook fue cerrada porque estuvo bloqueada 7 días sin '
    'que te comunicaras con TurfBook. Ya no podrás ingresar con ella. Si tienes dudas, '
    'comunícate con TurfBook al {phone} o a {email}.'
)
