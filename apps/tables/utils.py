import secrets


def generate_qr_token() -> str:
    return secrets.token_urlsafe(24)


def generate_table_pin() -> str:
    return ''.join(secrets.choice('0123456789') for _ in range(4))
