#!/usr/bin/env python3
"""Disposable mailbox generator using public temporary-mail APIs.

Creates a throwaway inbox (via mail.tm, with 1secmail as fallback) so you can
receive verification messages without using a personal address. This tool does
not register accounts on Gmail, Outlook, Yahoo, or other durable providers.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import secrets
import string
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

MAILTM_BASE = "https://api.mail.tm"
SECMAIL_BASE = "https://www.1secmail.com/api/v1/"
USER_AGENT = "ephemere-tempmail/1.0 (+https://github.com/delatrhack23/john-core)"
SESSION_PATH = Path.home() / ".ephemere-session.json"
STATIC_DIR = Path(__file__).resolve().parent / "static"

ADJECTIVES = (
    "ambre",
    "brume",
    "celadon",
    "cuivre",
    "dune",
    "encre",
    "fauve",
    "givre",
    "ivoire",
    "jade",
    "kaki",
    "lin",
    "miel",
    "nacre",
    "ocre",
    "perle",
    "quartz",
    "roseau",
    "sauge",
    "taupe",
)
NOUNS = (
    "atelier",
    "balcon",
    "cahier",
    "delta",
    "ecluse",
    "figuier",
    "galerie",
    "hangar",
    "ilot",
    "jetee",
    "kiosque",
    "lavoir",
    "marais",
    "noyer",
    "observatoire",
    "phare",
    "quai",
    "rivage",
    "sentier",
    "tonnelle",
)


class TempMailError(RuntimeError):
    """Raised when a temporary-mail provider rejects or fails a request."""

    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


@dataclass
class Mailbox:
    address: str
    provider: str
    token: str
    local: str
    domain: str
    password: str | None = None
    account_id: str | None = None

    def to_public_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        return payload


@dataclass
class MessageSummary:
    id: str
    sender: str
    subject: str
    intro: str
    created_at: str
    seen: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Message:
    id: str
    sender: str
    subject: str
    created_at: str
    text: str
    html: str
    to: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def random_local_part(rng: random.Random | None = None) -> str:
    """Return a readable, unique-enough local part such as ambre-phare-4821."""
    dice = rng or random.SystemRandom()
    adjective = dice.choice(ADJECTIVES)
    noun = dice.choice(NOUNS)
    suffix = f"{dice.randint(0, 9999):04d}"
    return f"{adjective}-{noun}-{suffix}"


def random_password(length: int = 20) -> str:
    if length < 8:
        raise ValueError("password length must be at least 8")
    alphabet = string.ascii_letters + string.digits + "-_."
    return "".join(secrets.choice(alphabet) for _ in range(length))


def normalize_local_part(local: str) -> str:
    cleaned = local.strip().lower()
    if not cleaned or len(cleaned) > 42:
        raise TempMailError("la partie locale doit faire entre 1 et 42 caractères")
    allowed = set(string.ascii_lowercase + string.digits + ".-_")
    if any(char not in allowed for char in cleaned):
        raise TempMailError("la partie locale ne peut contenir que lettres, chiffres, . - _")
    if cleaned[0] in ".-_" or cleaned[-1] in ".-_" or ".." in cleaned:
        raise TempMailError("la partie locale commence, finit ou répète un séparateur")
    return cleaned


def split_address(address: str) -> tuple[str, str]:
    if address.count("@") != 1:
        raise TempMailError(f"invalid email address: {address}")
    local, domain = address.split("@", 1)
    if not local or not domain or "." not in domain:
        raise TempMailError(f"invalid email address: {address}")
    return normalize_local_part(local), domain.lower()


def _http_json(
    method: str,
    url: str,
    *,
    body: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 20.0,
) -> Any:
    payload = None if body is None else json.dumps(body).encode("utf-8")
    request_headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
    }
    if payload is not None:
        request_headers["Content-Type"] = "application/json"
    if headers:
        request_headers.update(headers)
    request = urllib.request.Request(url, data=payload, headers=request_headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
            if not raw:
                return None
            return json.loads(raw.decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        snippet = detail.strip().replace("\n", " ")[:240]
        raise TempMailError(
            f"{method} {url} failed with HTTP {exc.code}: {snippet or exc.reason}",
            status=exc.code,
        ) from exc
    except urllib.error.URLError as exc:
        raise TempMailError(f"{method} {url} failed: {exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise TempMailError(f"{method} {url} returned invalid JSON") from exc


def _hydra_members(payload: Any) -> list[Any]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        members = payload.get("hydra:member")
        if isinstance(members, list):
            return members
    return []


class MailTmProvider:
    name = "mailtm"

    def list_domains(self) -> list[str]:
        payload = _http_json("GET", f"{MAILTM_BASE}/domains")
        domains: list[str] = []
        for item in _hydra_members(payload):
            if not isinstance(item, dict):
                continue
            if item.get("isActive") is False:
                continue
            domain = str(item.get("domain") or "").strip().lower()
            if domain:
                domains.append(domain)
        if not domains:
            raise TempMailError("mail.tm returned no active domains")
        return domains

    def create_mailbox(self, local: str | None = None, domain: str | None = None) -> Mailbox:
        domains = self.list_domains()
        chosen_domain = (domain or domains[0]).lower()
        if chosen_domain not in domains:
            raise TempMailError(
                f"domain {chosen_domain} is not offered by mail.tm; try: {', '.join(domains)}"
            )
        local_part = normalize_local_part(local or random_local_part())
        password = random_password()
        address = f"{local_part}@{chosen_domain}"
        created = _http_json(
            "POST",
            f"{MAILTM_BASE}/accounts",
            body={"address": address, "password": password},
        )
        if not isinstance(created, dict) or not created.get("id"):
            raise TempMailError("mail.tm did not return an account id")
        token_payload = _http_json(
            "POST",
            f"{MAILTM_BASE}/token",
            body={"address": address, "password": password},
        )
        if not isinstance(token_payload, dict) or not token_payload.get("token"):
            raise TempMailError("mail.tm did not return an auth token")
        return Mailbox(
            address=str(created.get("address") or address).lower(),
            provider=self.name,
            token=str(token_payload["token"]),
            local=local_part,
            domain=chosen_domain,
            password=password,
            account_id=str(created["id"]),
        )

    def restore(self, mailbox: Mailbox) -> Mailbox:
        if not mailbox.password:
            return mailbox
        token_payload = _http_json(
            "POST",
            f"{MAILTM_BASE}/token",
            body={"address": mailbox.address, "password": mailbox.password},
        )
        if not isinstance(token_payload, dict) or not token_payload.get("token"):
            raise TempMailError("could not restore the mail.tm session")
        mailbox.token = str(token_payload["token"])
        mailbox.account_id = str(token_payload.get("id") or mailbox.account_id)
        return mailbox

    def list_messages(self, mailbox: Mailbox) -> list[MessageSummary]:
        payload = _http_json(
            "GET",
            f"{MAILTM_BASE}/messages",
            headers={"Authorization": f"Bearer {mailbox.token}"},
        )
        messages: list[MessageSummary] = []
        for item in _hydra_members(payload):
            if not isinstance(item, dict):
                continue
            sender = item.get("from") or {}
            sender_addr = ""
            if isinstance(sender, dict):
                sender_addr = str(sender.get("address") or sender.get("name") or "")
            messages.append(
                MessageSummary(
                    id=str(item.get("id") or ""),
                    sender=sender_addr,
                    subject=str(item.get("subject") or "(sans objet)"),
                    intro=str(item.get("intro") or ""),
                    created_at=str(item.get("createdAt") or ""),
                    seen=bool(item.get("seen")),
                )
            )
        return messages

    def read_message(self, mailbox: Mailbox, message_id: str) -> Message:
        payload = _http_json(
            "GET",
            f"{MAILTM_BASE}/messages/{urllib.parse.quote(message_id, safe='')}",
            headers={"Authorization": f"Bearer {mailbox.token}"},
        )
        if not isinstance(payload, dict):
            raise TempMailError("mail.tm returned an empty message")
        sender = payload.get("from") or {}
        sender_addr = ""
        if isinstance(sender, dict):
            sender_addr = str(sender.get("address") or sender.get("name") or "")
        recipients = payload.get("to") or []
        to_addr = ""
        if isinstance(recipients, list) and recipients:
            first = recipients[0]
            if isinstance(first, dict):
                to_addr = str(first.get("address") or "")
        html = payload.get("html") or ""
        if isinstance(html, list):
            html = "\n".join(str(part) for part in html)
        return Message(
            id=str(payload.get("id") or message_id),
            sender=sender_addr,
            subject=str(payload.get("subject") or "(sans objet)"),
            created_at=str(payload.get("createdAt") or ""),
            text=str(payload.get("text") or ""),
            html=str(html),
            to=to_addr,
        )

    def delete_message(self, mailbox: Mailbox, message_id: str) -> None:
        _http_json(
            "DELETE",
            f"{MAILTM_BASE}/messages/{urllib.parse.quote(message_id, safe='')}",
            headers={"Authorization": f"Bearer {mailbox.token}"},
        )

    def delete_mailbox(self, mailbox: Mailbox) -> None:
        if not mailbox.account_id:
            raise TempMailError("missing account id; cannot delete mailbox")
        _http_json(
            "DELETE",
            f"{MAILTM_BASE}/accounts/{urllib.parse.quote(mailbox.account_id, safe='')}",
            headers={"Authorization": f"Bearer {mailbox.token}"},
        )


class OneSecMailProvider:
    name = "1secmail"

    def list_domains(self) -> list[str]:
        payload = _http_json("GET", f"{SECMAIL_BASE}?action=getDomainList")
        if not isinstance(payload, list) or not payload:
            raise TempMailError("1secmail returned no domains")
        return [str(item).lower() for item in payload if item]

    def create_mailbox(self, local: str | None = None, domain: str | None = None) -> Mailbox:
        domains = self.list_domains()
        chosen_domain = (domain or domains[0]).lower()
        if chosen_domain not in domains:
            raise TempMailError(
                f"domain {chosen_domain} is not offered by 1secmail; try: {', '.join(domains)}"
            )
        local_part = normalize_local_part(local or random_local_part())
        address = f"{local_part}@{chosen_domain}"
        return Mailbox(
            address=address,
            provider=self.name,
            token=f"{local_part}:{chosen_domain}",
            local=local_part,
            domain=chosen_domain,
        )

    def restore(self, mailbox: Mailbox) -> Mailbox:
        return mailbox

    def list_messages(self, mailbox: Mailbox) -> list[MessageSummary]:
        query = urllib.parse.urlencode(
            {"action": "getMessages", "login": mailbox.local, "domain": mailbox.domain}
        )
        payload = _http_json("GET", f"{SECMAIL_BASE}?{query}")
        if not isinstance(payload, list):
            raise TempMailError("1secmail returned an unexpected inbox payload")
        messages: list[MessageSummary] = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            messages.append(
                MessageSummary(
                    id=str(item.get("id") or ""),
                    sender=str(item.get("from") or ""),
                    subject=str(item.get("subject") or "(sans objet)"),
                    intro="",
                    created_at=str(item.get("date") or ""),
                )
            )
        return messages

    def read_message(self, mailbox: Mailbox, message_id: str) -> Message:
        query = urllib.parse.urlencode(
            {
                "action": "readMessage",
                "login": mailbox.local,
                "domain": mailbox.domain,
                "id": message_id,
            }
        )
        payload = _http_json("GET", f"{SECMAIL_BASE}?{query}")
        if not isinstance(payload, dict):
            raise TempMailError("1secmail returned an empty message")
        html = payload.get("htmlBody") or ""
        text = payload.get("textBody") or payload.get("body") or ""
        return Message(
            id=str(payload.get("id") or message_id),
            sender=str(payload.get("from") or ""),
            subject=str(payload.get("subject") or "(sans objet)"),
            created_at=str(payload.get("date") or ""),
            text=str(text),
            html=str(html),
            to=mailbox.address,
        )

    def delete_message(self, mailbox: Mailbox, message_id: str) -> None:
        del mailbox, message_id
        raise TempMailError("1secmail does not support deleting individual messages")

    def delete_mailbox(self, mailbox: Mailbox) -> None:
        del mailbox
        return None


PROVIDERS = {
    MailTmProvider.name: MailTmProvider(),
    OneSecMailProvider.name: OneSecMailProvider(),
}
DEFAULT_PROVIDERS = (MailTmProvider.name, OneSecMailProvider.name)


def get_provider(name: str):
    try:
        return PROVIDERS[name]
    except KeyError as exc:
        known = ", ".join(PROVIDERS)
        raise TempMailError(f"unknown provider {name!r}; choose one of: {known}") from exc


def create_mailbox(
    *,
    local: str | None = None,
    domain: str | None = None,
    provider: str | None = None,
) -> Mailbox:
    errors: list[str] = []
    names = (provider,) if provider else DEFAULT_PROVIDERS
    for name in names:
        try:
            return get_provider(name).create_mailbox(local=local, domain=domain)
        except TempMailError as exc:
            errors.append(f"{name}: {exc}")
    raise TempMailError("could not create a disposable mailbox (" + "; ".join(errors) + ")")


def save_session(mailbox: Mailbox, path: Path = SESSION_PATH) -> None:
    path.write_text(json.dumps(mailbox.to_public_dict(), indent=2) + "\n", encoding="utf-8")


def load_session(path: Path = SESSION_PATH) -> Mailbox:
    if not path.is_file():
        raise TempMailError(f"no saved session at {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    return mailbox_from_dict(payload)


def mailbox_from_dict(payload: dict[str, Any]) -> Mailbox:
    required = ("address", "provider", "token", "local", "domain")
    missing = [key for key in required if not payload.get(key)]
    if missing:
        raise TempMailError("incomplete mailbox payload: " + ", ".join(missing))
    return Mailbox(
        address=str(payload["address"]).lower(),
        provider=str(payload["provider"]),
        token=str(payload["token"]),
        local=str(payload["local"]).lower(),
        domain=str(payload["domain"]).lower(),
        password=payload.get("password"),
        account_id=payload.get("account_id"),
    )


def restore_mailbox(mailbox: Mailbox) -> Mailbox:
    return get_provider(mailbox.provider).restore(mailbox)


def format_message_list(messages: list[MessageSummary]) -> str:
    if not messages:
        return "Boîte vide — aucun message pour le moment."
    lines = []
    for index, message in enumerate(messages, start=1):
        flag = " " if message.seen else "*"
        lines.append(
            f"{index:2d}{flag}  {message.created_at:25}  {message.sender}\n"
            f"     {message.subject}\n"
            f"     {message.intro}"
        )
    return "\n".join(lines)


def _print_json(payload: Any) -> None:
    json.dump(payload, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")


def cmd_new(args: argparse.Namespace) -> int:
    if args.count < 1:
        raise TempMailError("count must be >= 1")
    mailboxes = []
    for _ in range(args.count):
        mailbox = create_mailbox(local=args.local, domain=args.domain, provider=args.provider)
        save_session(mailbox)
        mailboxes.append(mailbox)
        if args.json:
            continue
        print(mailbox.address)
        if args.verbose:
            print(f"  fournisseur : {mailbox.provider}")
            print(f"  domaine     : {mailbox.domain}")
            if mailbox.password:
                print(f"  mot de passe: {mailbox.password}")
    if args.json:
        _print_json([box.to_public_dict() for box in mailboxes] if args.count > 1 else mailboxes[0].to_public_dict())
    return 0


def cmd_domains(args: argparse.Namespace) -> int:
    names = (args.provider,) if args.provider else DEFAULT_PROVIDERS
    result: dict[str, list[str]] = {}
    for name in names:
        try:
            result[name] = get_provider(name).list_domains()
        except TempMailError as exc:
            result[name] = [f"erreur: {exc}"]
    if args.json:
        _print_json(result)
        return 0
    for name, domains in result.items():
        print(f"[{name}]")
        for domain in domains:
            print(f"  {domain}")
    return 0


def _require_mailbox(args: argparse.Namespace) -> Mailbox:
    if args.session:
        mailbox = load_session(Path(args.session))
    elif getattr(args, "address", None) and getattr(args, "password", None):
        local, domain = split_address(args.address)
        mailbox = Mailbox(
            address=args.address.lower(),
            provider=args.provider or MailTmProvider.name,
            token="",
            local=local,
            domain=domain,
            password=args.password,
        )
    else:
        mailbox = load_session()
    return restore_mailbox(mailbox)


def cmd_inbox(args: argparse.Namespace) -> int:
    mailbox = _require_mailbox(args)
    messages = get_provider(mailbox.provider).list_messages(mailbox)
    if args.json:
        _print_json([message.to_dict() for message in messages])
        return 0
    print(f"Boîte : {mailbox.address}")
    print(format_message_list(messages))
    return 0


def cmd_read(args: argparse.Namespace) -> int:
    mailbox = _require_mailbox(args)
    message = get_provider(mailbox.provider).read_message(mailbox, args.message_id)
    if args.json:
        _print_json(message.to_dict())
        return 0
    print(f"De      : {message.sender}")
    print(f"À       : {message.to or mailbox.address}")
    print(f"Sujet   : {message.subject}")
    print(f"Date    : {message.created_at}")
    print("-" * 60)
    print(message.text or message.html or "(message vide)")
    return 0


def cmd_watch(args: argparse.Namespace) -> int:
    if args.new or not SESSION_PATH.is_file():
        mailbox = create_mailbox(local=args.local, domain=args.domain, provider=args.provider)
        save_session(mailbox)
    else:
        mailbox = restore_mailbox(load_session())
    print(f"Adresse : {mailbox.address}")
    print("En attente de messages (Ctrl-C pour arrêter)...")
    seen: set[str] = set()
    try:
        while True:
            messages = get_provider(mailbox.provider).list_messages(mailbox)
            for message in messages:
                if message.id in seen:
                    continue
                seen.add(message.id)
                print(f"\nNouveau message de {message.sender}")
                print(f"  {message.subject}")
                if message.intro:
                    print(f"  {message.intro}")
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nArrêt de la surveillance.")
        return 0


def cmd_serve(args: argparse.Namespace) -> int:
    os.chdir(Path(__file__).resolve().parent)
    server = ThreadingHTTPServer((args.host, args.port), TempMailHandler)
    url = f"http://{args.host}:{args.port}/"
    print(f"Éphémère écoute sur {url}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServeur arrêté.")
    finally:
        server.server_close()
    return 0


class TempMailHandler(BaseHTTPRequestHandler):
    server_version = "Ephemere/1.0"

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        sys.stderr.write("%s - %s\n" % (self.address_string(), format % args))

    def _send(self, status: int, payload: Any, content_type: str = "application/json; charset=utf-8") -> None:
        if isinstance(payload, (dict, list)):
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        elif isinstance(payload, bytes):
            body = payload
        else:
            body = str(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        if not raw:
            return {}
        try:
            payload = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise TempMailError("invalid JSON body") from exc
        if not isinstance(payload, dict):
            raise TempMailError("JSON body must be an object")
        return payload

    def _mailbox_from_request(self, extra: dict[str, Any] | None = None) -> Mailbox:
        payload = extra or {}
        header_token = ""
        auth = self.headers.get("Authorization") or ""
        if auth.lower().startswith("bearer "):
            header_token = auth[7:].strip()
        data = {
            "address": payload.get("address") or self.headers.get("X-Mailbox-Address"),
            "provider": payload.get("provider") or self.headers.get("X-Mailbox-Provider"),
            "token": payload.get("token") or header_token,
            "local": payload.get("local") or self.headers.get("X-Mailbox-Local"),
            "domain": payload.get("domain") or self.headers.get("X-Mailbox-Domain"),
            "password": payload.get("password") or self.headers.get("X-Mailbox-Password"),
            "account_id": payload.get("account_id") or self.headers.get("X-Mailbox-Id"),
        }
        if data["address"] and (not data["local"] or not data["domain"]):
            local, domain = split_address(str(data["address"]))
            data["local"] = data["local"] or local
            data["domain"] = data["domain"] or domain
        return mailbox_from_dict(data)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)
        try:
            if path in {"/", "/index.html"}:
                self._serve_static("index.html", "text/html; charset=utf-8")
                return
            if path == "/api/health":
                self._send(200, {"ok": True, "service": "ephemere"})
                return
            if path == "/api/domains":
                provider = (query.get("provider") or [None])[0]
                names = (provider,) if provider else DEFAULT_PROVIDERS
                result: dict[str, list[str]] = {}
                for name in names:
                    try:
                        result[name] = get_provider(name).list_domains()
                    except TempMailError as exc:
                        result[name] = []
                        result.setdefault("_errors", [])
                        result["_errors"].append(f"{name}: {exc}")
                self._send(200, result)
                return
            if path == "/api/messages":
                mailbox = self._mailbox_from_request()
                messages = get_provider(mailbox.provider).list_messages(mailbox)
                self._send(200, [message.to_dict() for message in messages])
                return
            if path.startswith("/api/messages/"):
                message_id = urllib.parse.unquote(path.rsplit("/", 1)[-1])
                mailbox = self._mailbox_from_request()
                message = get_provider(mailbox.provider).read_message(mailbox, message_id)
                self._send(200, message.to_dict())
                return
            if path.startswith("/static/"):
                self._serve_static(path[len("/static/") :], None)
                return
            self._send(404, {"error": "not found"})
        except TempMailError as exc:
            status = exc.status if exc.status and 400 <= exc.status < 600 else 502
            self._send(status, {"error": str(exc)})

    def do_POST(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        try:
            payload = self._read_json()
            if parsed.path == "/api/accounts":
                mailbox = create_mailbox(
                    local=payload.get("local") or None,
                    domain=payload.get("domain") or None,
                    provider=payload.get("provider") or None,
                )
                save_session(mailbox)
                self._send(201, mailbox.to_public_dict())
                return
            if parsed.path == "/api/session":
                mailbox = restore_mailbox(self._mailbox_from_request(payload))
                save_session(mailbox)
                self._send(200, mailbox.to_public_dict())
                return
            self._send(404, {"error": "not found"})
        except TempMailError as exc:
            status = exc.status if exc.status and 400 <= exc.status < 600 else 502
            self._send(status, {"error": str(exc)})

    def do_DELETE(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        try:
            if parsed.path.startswith("/api/messages/"):
                message_id = urllib.parse.unquote(parsed.path.rsplit("/", 1)[-1])
                mailbox = self._mailbox_from_request()
                get_provider(mailbox.provider).delete_message(mailbox, message_id)
                self._send(200, {"ok": True})
                return
            if parsed.path == "/api/accounts":
                mailbox = self._mailbox_from_request()
                get_provider(mailbox.provider).delete_mailbox(mailbox)
                if SESSION_PATH.is_file():
                    SESSION_PATH.unlink()
                self._send(200, {"ok": True})
                return
            self._send(404, {"error": "not found"})
        except TempMailError as exc:
            status = exc.status if exc.status and 400 <= exc.status < 600 else 502
            self._send(status, {"error": str(exc)})

    def _serve_static(self, relative: str, content_type: str | None) -> None:
        candidate = (STATIC_DIR / relative).resolve()
        if not str(candidate).startswith(str(STATIC_DIR.resolve())) or not candidate.is_file():
            self._send(404, {"error": "not found"})
            return
        data = candidate.read_bytes()
        guessed = content_type
        if guessed is None:
            if candidate.suffix == ".html":
                guessed = "text/html; charset=utf-8"
            elif candidate.suffix == ".css":
                guessed = "text/css; charset=utf-8"
            elif candidate.suffix == ".js":
                guessed = "application/javascript; charset=utf-8"
            elif candidate.suffix == ".svg":
                guessed = "image/svg+xml"
            else:
                guessed = "application/octet-stream"
        self._send(200, data, guessed)

    def do_HEAD(self) -> None:  # noqa: N802
        if self.path in {"/", "/index.html"}:
            self._serve_static("index.html", "text/html; charset=utf-8")
            return
        self._send(404, b"", "text/plain")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tempmail",
        description="Générateur d'adresses e-mail jetables (mail.tm / 1secmail).",
    )
    parser.add_argument(
        "--provider",
        choices=sorted(PROVIDERS),
        default=None,
        help="Forcer un fournisseur (sinon mail.tm, puis 1secmail).",
    )
    parser.add_argument("--json", action="store_true", help="Sortie JSON.")

    # Same flags on subcommands, but SUPPRESS so they do not reset parent values.
    shared = argparse.ArgumentParser(add_help=False)
    shared.add_argument("--provider", choices=sorted(PROVIDERS), default=argparse.SUPPRESS)
    shared.add_argument("--json", action="store_true", default=argparse.SUPPRESS)

    sub = parser.add_subparsers(dest="command", required=True)

    new_cmd = sub.add_parser("new", help="Créer une adresse jetable.", parents=[shared])
    new_cmd.add_argument("--local", help="Partie locale choisie (avant le @).")
    new_cmd.add_argument("--domain", help="Domaine parmi ceux du fournisseur.")
    new_cmd.add_argument("--count", type=int, default=1, help="Nombre d'adresses à créer.")
    new_cmd.add_argument("-v", "--verbose", action="store_true")
    new_cmd.set_defaults(func=cmd_new)

    domains_cmd = sub.add_parser("domains", help="Lister les domaines disponibles.", parents=[shared])
    domains_cmd.set_defaults(func=cmd_domains)

    inbox_cmd = sub.add_parser("inbox", help="Lister les messages de la session courante.", parents=[shared])
    inbox_cmd.add_argument("--session", help="Fichier de session JSON.")
    inbox_cmd.add_argument("--address", help="Adresse existante (mail.tm).")
    inbox_cmd.add_argument("--password", help="Mot de passe de l'adresse existante.")
    inbox_cmd.set_defaults(func=cmd_inbox)

    read_cmd = sub.add_parser("read", help="Lire un message.", parents=[shared])
    read_cmd.add_argument("message_id")
    read_cmd.add_argument("--session", help="Fichier de session JSON.")
    read_cmd.add_argument("--address")
    read_cmd.add_argument("--password")
    read_cmd.set_defaults(func=cmd_read)

    watch_cmd = sub.add_parser("watch", help="Créer (si besoin) et surveiller la boîte.", parents=[shared])
    watch_cmd.add_argument("--local")
    watch_cmd.add_argument("--domain")
    watch_cmd.add_argument("--new", action="store_true", help="Forcer une nouvelle adresse.")
    watch_cmd.add_argument("--interval", type=float, default=5.0)
    watch_cmd.set_defaults(func=cmd_watch)

    serve_cmd = sub.add_parser("serve", help="Lancer l'interface web locale.", parents=[shared])
    serve_cmd.add_argument("--host", default="127.0.0.1")
    serve_cmd.add_argument("--port", type=int, default=8765)
    serve_cmd.set_defaults(func=cmd_serve)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except TempMailError as exc:
        if getattr(args, "json", False):
            _print_json({"error": str(exc)})
        else:
            print(f"erreur: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
