from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from perplexity.config import extract_perplexity_login_url, load_config, mail_config_for, save_config


class MailLoginExtractionTest(unittest.TestCase):
    def _message(self, body, date=None):
        msg = EmailMessage()
        msg["Date"] = (date or datetime(2026, 5, 6, 6, 3, 8, tzinfo=timezone.utc)).strftime(
            "%a, %d %b %Y %H:%M:%S %z"
        )
        msg["From"] = "Perplexity <team@mail.perplexity.ai>"
        msg["To"] = "d.grieser@mittwald.de"
        msg["Subject"] = "Sign in to Perplexity"
        msg.set_content(body, cte="quoted-printable")
        return msg.as_bytes()

    def test_extracts_wrapped_quoted_printable_url(self):
        body = (
            "https://www.perplexity.ai/api/auth/callback/email?=\n"
            "callbackUrl=3DdefaultMobileSignIn&email=3Dd.grieser%40mittwald.=\n"
            "de&token=3D543116"
        )
        url = extract_perplexity_login_url(
            self._message(body),
            "d.grieser@mittwald.de",
            now=datetime(2026, 5, 6, 6, 3, 30, tzinfo=timezone.utc),
        )
        self.assertEqual(
            url,
            "https://www.perplexity.ai/api/auth/callback/email?callbackUrl=defaultMobileSignIn&email=d.grieser%40mittwald.de&token=543116",
        )

    def test_extracts_html_entity_url(self):
        body = (
            '<a href="https://www.perplexity.ai/api/auth/callback/email?'
            'callbackUrl=defaultMobileSignIn&amp;email=d.grieser%40mittwald.de&amp;token=543116">'
        )
        url = extract_perplexity_login_url(
            self._message(body),
            "d.grieser@mittwald.de",
            now=datetime(2026, 5, 6, 6, 3, 30, tzinfo=timezone.utc),
        )
        self.assertEqual(
            url,
            "https://www.perplexity.ai/api/auth/callback/email?callbackUrl=defaultMobileSignIn&email=d.grieser%40mittwald.de&token=543116",
        )

    def test_rejects_stale_message(self):
        raw = self._message(
            "https://www.perplexity.ai/api/auth/callback/email?callbackUrl=defaultMobileSignIn&email=d.grieser%40mittwald.de&token=543116",
            date=datetime(2026, 5, 6, 6, 1, 0, tzinfo=timezone.utc),
        )
        url = extract_perplexity_login_url(
            raw,
            "d.grieser@mittwald.de",
            now=datetime(2026, 5, 6, 6, 3, 0, tzinfo=timezone.utc),
        )
        self.assertIsNone(url)


class ConfigStorageTest(unittest.TestCase):
    def test_saves_and_loads_mail_account(self):
        with TemporaryDirectory() as tmp:
            with patch("perplexity.config.Path.home", return_value=Path(tmp)):
                save_config(
                    {
                        "mail": {
                            "accounts": {
                                "login@example.com": {
                                    "address": "mailbox@example.com",
                                    "username": "imap-user",
                                    "password": "secret",
                                    "imap_hostname": "imap.example.com",
                                    "port": 993,
                                }
                            }
                        }
                    }
                )

                self.assertEqual(load_config()["mail"]["accounts"]["login@example.com"]["port"], 993)
                self.assertEqual(mail_config_for("login@example.com")["address"], "mailbox@example.com")
                self.assertEqual(mail_config_for("LOGIN@example.com")["username"], "imap-user")


if __name__ == "__main__":
    unittest.main()
