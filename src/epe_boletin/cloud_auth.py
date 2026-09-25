"""Password verification and stateless, signed browser sessions for the cloud UI."""

from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import hmac
import json
import os
import re
import secrets
import time
from getpass import getpass
from http.cookies import SimpleCookie


SESSION_SECONDS = 12 * 60 * 60
PASSWORD_ROUNDS = 310_000


def password_hash(password: str, *, salt: bytes | None = None) -> str:
    if not password:
        raise ValueError("La contraseña no puede estar vacía")
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PASSWORD_ROUNDS)
    return f"pbkdf2_sha256${PASSWORD_ROUNDS}${salt.hex()}${digest.hex()}"


def _valid_hash(encoded: str) -> bool:
    try:
        algorithm, rounds, salt, digest = encoded.split("$")
        return (algorithm == "pbkdf2_sha256" and int(rounds) == PASSWORD_ROUNDS
                and len(bytes.fromhex(salt)) == 16
                and len(bytes.fromhex(digest)) == 32)
    except (ValueError, TypeError):
        return False


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


class CloudAuth:
    def __init__(self, users: dict[str, str], secret: str):
        if not users or any(not name or not _valid_hash(value)
                            for name, value in users.items()):
            raise ValueError("EPE_WEB_USERS debe contener usuarios con hashes válidos")
        if len(secret) < 32:
            raise ValueError("EPE_WEB_SESSION_SECRET debe tener al menos 32 caracteres")
        self.users = users
        self.secret = secret.encode("utf-8")

    @classmethod
    def from_env(cls) -> CloudAuth:
        try:
            users = json.loads(os.environ.get("EPE_WEB_USERS", ""))
        except json.JSONDecodeError as exc:
            raise ValueError("EPE_WEB_USERS no es JSON válido") from exc
        if not isinstance(users, dict) or not all(isinstance(k, str) and
                isinstance(v, str) for k, v in users.items()):
            raise ValueError("EPE_WEB_USERS debe ser un objeto JSON")
        return cls(users, os.environ.get("EPE_WEB_SESSION_SECRET", ""))

    def verify_password(self, user: str, password: str) -> bool:
        encoded = self.users.get(user)
        if not encoded:
            return False
        _, rounds, salt, digest = encoded.split("$")
        candidate = hashlib.pbkdf2_hmac("sha256", password.encode(),
                                        bytes.fromhex(salt), int(rounds))
        return hmac.compare_digest(candidate, bytes.fromhex(digest))

    def new_ticket(self, user: str, *, now: int | None = None) -> str:
        if user not in self.users:
            raise ValueError("Usuario desconocido")
        issued = int(time.time()) if now is None else now
        payload = _b64(json.dumps({"u": user, "exp": issued + SESSION_SECONDS,
                                   "n": secrets.token_hex(8)},
                                  separators=(",", ":")).encode())
        signature = _b64(hmac.digest(self.secret, payload.encode(), "sha256"))
        return payload + "." + signature

    def ticket_user(self, ticket: str, *, now: int | None = None) -> str | None:
        if not ticket or len(ticket) > 1024 or ticket.count(".") != 1:
            return None
        payload, signature = ticket.split(".")
        expected = _b64(hmac.digest(self.secret, payload.encode(), "sha256"))
        if not hmac.compare_digest(signature, expected):
            return None
        try:
            data = json.loads(_unb64(payload))
        except (ValueError, UnicodeDecodeError, binascii.Error):
            return None
        user = data.get("u") if isinstance(data, dict) else None
        current = int(time.time()) if now is None else now
        return user if (isinstance(user, str) and user in self.users
                        and isinstance(data.get("exp"), int)
                        and current < data["exp"] <= current + SESSION_SECONDS) else None

    def request_user(self, cookie_header: str) -> tuple[str | None, str]:
        try:
            cookie = SimpleCookie()
            cookie.load(cookie_header)
            ticket = cookie["epe_session"].value if "epe_session" in cookie else ""
        except Exception:
            ticket = ""
        return self.ticket_user(ticket), ticket

    def csrf_token(self, ticket: str) -> str:
        return _b64(hmac.digest(self.secret, ("csrf:" + ticket).encode(), "sha256"))

    def valid_csrf(self, ticket: str, submitted: str) -> bool:
        return bool(ticket and submitted and
                    hmac.compare_digest(self.csrf_token(ticket), submitted))

    @staticmethod
    def new_login_nonce() -> str:
        return secrets.token_urlsafe(24)

    def login_csrf_token(self, nonce: str) -> str:
        return _b64(hmac.digest(self.secret, ("login:" + nonce).encode(), "sha256"))

    def valid_login_csrf(self, cookie_header: str, submitted: str) -> bool:
        try:
            cookie = SimpleCookie()
            cookie.load(cookie_header)
            nonce = cookie["epe_login_nonce"].value if "epe_login_nonce" in cookie else ""
        except Exception:
            return False
        return bool(re.fullmatch(r"[A-Za-z0-9_-]{32}", nonce) and submitted and
                    hmac.compare_digest(self.login_csrf_token(nonce), submitted))


def main() -> None:
    parser = argparse.ArgumentParser(description="Crear hashes de contraseña para usuarios web")
    parser.add_argument("--user", action="append", required=True)
    args = parser.parse_args()
    if len(set(args.user)) != len(args.user) or any(not name.strip() for name in args.user):
        raise SystemExit("Los nombres de usuario deben ser únicos y no vacíos")
    users = {}
    for name in args.user:
        password = getpass(f"Contraseña de {name}: ")
        repeated = getpass(f"Repetir contraseña de {name}: ")
        if password != repeated:
            raise SystemExit(f"Las contraseñas de {name} no coinciden")
        users[name] = password_hash(password)
    print(json.dumps(users, ensure_ascii=False))


if __name__ == "__main__":
    main()
