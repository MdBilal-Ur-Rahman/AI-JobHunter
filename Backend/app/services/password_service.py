from passlib.context import CryptContext


MAX_BCRYPT_PASSWORD_BYTES = 72

_password_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)


def password_within_bcrypt_limit(password: str) -> bool:
    return len(password.encode("utf-8")) <= MAX_BCRYPT_PASSWORD_BYTES


def hash_password(password: str) -> str:
    if not password_within_bcrypt_limit(password):
        raise ValueError(
            "Password must be no more than "
            f"{MAX_BCRYPT_PASSWORD_BYTES} UTF-8 bytes."
        )
    return _password_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return _password_context.verify(password, password_hash)
