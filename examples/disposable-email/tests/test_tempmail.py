#!/usr/bin/env python3
"""Tests for the disposable mailbox generator."""

from __future__ import annotations

import io
import json
import random
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import tempmail  # noqa: E402


class LocalPartTests(unittest.TestCase):
    def test_random_local_part_shape(self) -> None:
        rng = random.Random(42)
        value = tempmail.random_local_part(rng)
        self.assertRegex(value, r"^[a-z]+-[a-z]+-\d{4}$")
        tempmail.normalize_local_part(value)

    def test_random_local_parts_vary(self) -> None:
        rng = random.Random(7)
        values = {tempmail.random_local_part(rng) for _ in range(20)}
        self.assertGreater(len(values), 10)

    def test_normalize_rejects_bad_input(self) -> None:
        with self.assertRaises(tempmail.TempMailError):
            tempmail.normalize_local_part("Jean Dupont")
        with self.assertRaises(tempmail.TempMailError):
            tempmail.normalize_local_part("-start")
        with self.assertRaises(tempmail.TempMailError):
            tempmail.normalize_local_part("")

    def test_split_address(self) -> None:
        local, domain = tempmail.split_address("Amber-Phare-0001@Mail.Tm")
        self.assertEqual(local, "amber-phare-0001")
        self.assertEqual(domain, "mail.tm")

    def test_password_length(self) -> None:
        secret = tempmail.random_password(12)
        self.assertEqual(len(secret), 12)
        with self.assertRaises(ValueError):
            tempmail.random_password(4)


class MailTmProviderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.provider = tempmail.MailTmProvider()

    def test_create_mailbox_parses_hydra_and_token(self) -> None:
        calls: list[tuple[str, str]] = []

        def fake_http(method: str, url: str, **kwargs):
            calls.append((method, url))
            if url.endswith("/domains"):
                return {
                    "hydra:member": [
                        {"domain": "mail.tm", "isActive": True},
                        {"domain": "dead.example", "isActive": False},
                    ]
                }
            if url.endswith("/accounts"):
                self.assertEqual(kwargs["body"]["address"], "demo-kiosque-0001@mail.tm")
                return {"id": "acc-1", "address": "demo-kiosque-0001@mail.tm"}
            if url.endswith("/token"):
                return {"id": "acc-1", "token": "jwt-token"}
            raise AssertionError(url)

        with patch.object(tempmail, "_http_json", side_effect=fake_http):
            mailbox = self.provider.create_mailbox(local="demo-kiosque-0001")

        self.assertEqual(mailbox.address, "demo-kiosque-0001@mail.tm")
        self.assertEqual(mailbox.token, "jwt-token")
        self.assertEqual(mailbox.account_id, "acc-1")
        self.assertEqual(mailbox.provider, "mailtm")
        self.assertEqual([item[0] for item in calls], ["GET", "POST", "POST"])

    def test_list_messages_reads_hydra_member(self) -> None:
        mailbox = tempmail.Mailbox(
            address="a@mail.tm",
            provider="mailtm",
            token="t",
            local="a",
            domain="mail.tm",
        )
        payload = {
            "hydra:member": [
                {
                    "id": "m1",
                    "from": {"address": "bot@example.com"},
                    "subject": "Code",
                    "intro": "123456",
                    "createdAt": "2026-08-13T12:00:00+00:00",
                    "seen": False,
                }
            ]
        }
        with patch.object(tempmail, "_http_json", return_value=payload) as mocked:
            messages = self.provider.list_messages(mailbox)
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].sender, "bot@example.com")
        self.assertEqual(messages[0].subject, "Code")
        mocked.assert_called_once()

    def test_unknown_domain_is_rejected(self) -> None:
        with patch.object(tempmail, "_http_json", return_value={"hydra:member": [{"domain": "mail.tm", "isActive": True}]}):
            with self.assertRaises(tempmail.TempMailError):
                self.provider.create_mailbox(domain="gmail.com")


class FallbackTests(unittest.TestCase):
    def test_create_mailbox_falls_back_to_second_provider(self) -> None:
        mailtm = tempmail.PROVIDERS["mailtm"]
        secmail = tempmail.PROVIDERS["1secmail"]

        def boom(*_args, **_kwargs):
            raise tempmail.TempMailError("mail.tm down", status=503)

        fallback_box = tempmail.Mailbox(
            address="x@1secmail.com",
            provider="1secmail",
            token="x:1secmail.com",
            local="x",
            domain="1secmail.com",
        )
        with patch.object(mailtm, "create_mailbox", side_effect=boom):
            with patch.object(secmail, "create_mailbox", return_value=fallback_box):
                mailbox = tempmail.create_mailbox()
        self.assertEqual(mailbox.provider, "1secmail")


class SessionTests(unittest.TestCase):
    def test_roundtrip_session_file(self) -> None:
        mailbox = tempmail.Mailbox(
            address="ambre-phare-0001@mail.tm",
            provider="mailtm",
            token="tok",
            local="ambre-phare-0001",
            domain="mail.tm",
            password="secret-password",
            account_id="abc",
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "session.json"
            tempmail.save_session(mailbox, path)
            loaded = tempmail.load_session(path)
        self.assertEqual(loaded, mailbox)

    def test_incomplete_payload(self) -> None:
        with self.assertRaises(tempmail.TempMailError):
            tempmail.mailbox_from_dict({"address": "a@b.com"})


class CliTests(unittest.TestCase):
    def test_new_json_output(self) -> None:
        mailbox = tempmail.Mailbox(
            address="a@mail.tm",
            provider="mailtm",
            token="tok",
            local="a",
            domain="mail.tm",
            password="pw",
            account_id="id1",
        )
        with patch.object(tempmail, "create_mailbox", return_value=mailbox):
            with patch.object(tempmail, "save_session"):
                with patch("sys.stdout", new_callable=io.StringIO) as stdout:
                    code = tempmail.main(["--json", "new"])
        self.assertEqual(code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["address"], "a@mail.tm")

    def test_count_must_be_positive(self) -> None:
        code = tempmail.main(["new", "--count", "0"])
        self.assertEqual(code, 1)

    def test_json_flag_accepted_before_and_after_command(self) -> None:
        before = tempmail.build_parser().parse_args(["--json", "new"])
        after = tempmail.build_parser().parse_args(["new", "--json"])
        self.assertTrue(before.json)
        self.assertTrue(after.json)
        self.assertEqual(before.command, "new")
        self.assertEqual(after.command, "new")

    def test_help_exits_zero(self) -> None:
        with self.assertRaises(SystemExit) as caught:
            tempmail.main(["--help"])
        self.assertEqual(caught.exception.code, 0)


class HttpServerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), tempmail.TempMailHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        host, port = self.server.server_address[:2]
        self.base = f"http://{host}:{port}"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def _json(self, path: str, method: str = "GET", body: dict | None = None) -> tuple[int, dict | list]:
        data = None if body is None else json.dumps(body).encode("utf-8")
        request = urllib.request.Request(
            self.base + path,
            data=data,
            method=method,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                return response.status, json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            payload = json.loads(exc.read().decode("utf-8"))
            return exc.code, payload

    def test_health_and_index(self) -> None:
        status, payload = self._json("/api/health")
        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"])
        with urllib.request.urlopen(self.base + "/", timeout=5) as response:
            html = response.read().decode("utf-8")
        self.assertIn("Éphémère", html)
        self.assertIn("Nouvelle adresse", html)

    def test_create_account_endpoint(self) -> None:
        mailbox = tempmail.Mailbox(
            address="a@mail.tm",
            provider="mailtm",
            token="tok",
            local="a",
            domain="mail.tm",
            password="pw",
            account_id="id1",
        )
        with patch.object(tempmail, "create_mailbox", return_value=mailbox):
            with patch.object(tempmail, "save_session"):
                status, payload = self._json("/api/accounts", method="POST", body={})
        self.assertEqual(status, 201)
        self.assertEqual(payload["address"], "a@mail.tm")

    def test_unknown_route(self) -> None:
        status, payload = self._json("/api/nope")
        self.assertEqual(status, 404)
        self.assertIn("error", payload)


if __name__ == "__main__":
    unittest.main()
