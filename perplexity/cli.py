import argparse
import sys
from typing import Optional, TextIO

import argcomplete

from perplexity.config import configure_mail
from perplexity import AnswerStreamParser, Perplexity


class OutputWriter:
    def __init__(self, raw: bool = False, stream: Optional[TextIO] = None) -> None:
        self.raw = raw
        self.stream = stream or sys.stdout
        self._renderer = None

    def write(self, text: str) -> None:
        if not text:
            return

        if self.raw:
            self.stream.write(text)
            self.stream.flush()
            return

        self._streamdown().render(text)

    def close(self) -> None:
        if self._renderer is not None:
            self._renderer.tidyup()
        self.stream.flush()

    def _streamdown(self):
        if self._renderer is None:
            self._renderer = _load_streamdown()
        return self._renderer


def _load_streamdown():
    from streamdown import Streamdown

    return Streamdown()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Perplexity CLI")
    parser.add_argument("-a", "--account", metavar="EMAIL", help="account email for authenticated requests")
    parser.add_argument("-r", "--raw", action="store_true", help="print parsed markdown without terminal rendering")
    parser.add_argument("-s", "--sources", action="store_true", help="append sources")
    parser.add_argument("-p", "--pro", action="store_true", help="use Pro search")
    parser.add_argument("prompt", nargs="+", help="search prompt")
    return parser


def configure(argv: list[str]) -> int:
    config_parser = argparse.ArgumentParser(
        prog=f"{argv[0]} config",
        description="Configure perplexity-cli",
    )
    config_subparsers = config_parser.add_subparsers(dest="config_command", required=True)
    config_subparsers.add_parser("mail", help="configure IMAP mail login")
    config_args = config_parser.parse_args(argv[2:])
    if config_args.config_command == "mail":
        configure_mail()
    return 0


def run(args: argparse.Namespace) -> int:
    perplexity = Perplexity(args.account)
    writer = OutputWriter(raw=args.raw)
    try:
        answer = perplexity.search(" ".join(args.prompt), mode="copilot" if args.pro else "concise")
        stream_parser = AnswerStreamParser()
        for event in answer:
            delta = stream_parser.feed(event)
            writer.write(delta)

        if stream_parser.text:
            writer.write("\n")

        if args.sources:
            sources = stream_parser.format_sources(cited_only=stream_parser.has_citations())
            if sources:
                writer.write(sources + "\n")
        return 0
    finally:
        try:
            writer.close()
        finally:
            perplexity.close()


def main(argv: Optional[list[str]] = None) -> int:
    argv = argv or sys.argv
    try:
        if len(argv) > 1 and argv[1] == "config":
            return configure(argv)

        parser = build_parser()
        argcomplete.autocomplete(parser)
        return run(parser.parse_args(argv[1:]))
    except KeyboardInterrupt:
        sys.stderr.write("\n")
        sys.stderr.flush()
        return 130
