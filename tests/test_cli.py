from io import StringIO
import unittest
from unittest.mock import patch

from perplexity.cli import OutputWriter, build_parser, run


class FakeRenderer:
    instances = []

    def __init__(self):
        self.rendered = []
        self.closed = False
        FakeRenderer.instances.append(self)

    def render(self, text):
        self.rendered.append(text)

    def tidyup(self):
        self.closed = True


class FakePerplexity:
    instances = []

    def __init__(self, account):
        self.account = account
        self.closed = False
        FakePerplexity.instances.append(self)

    def search(self, prompt, mode):
        self.prompt = prompt
        self.mode = mode
        return [
            {
                "blocks": [
                    {
                        "intended_usage": "ask_text",
                        "markdown_block": {"answer": "# Hello"},
                    }
                ]
            },
            {
                "blocks": [
                    {
                        "intended_usage": "ask_text",
                        "markdown_block": {"answer": "# Hello\n\nWorld"},
                    }
                ]
            },
        ]

    def close(self):
        self.closed = True


class OutputWriterTest(unittest.TestCase):
    def setUp(self):
        FakeRenderer.instances = []

    def test_raw_writes_plain_text_without_streamdown(self):
        stream = StringIO()
        writer = OutputWriter(raw=True, stream=stream)

        with patch("perplexity.cli._load_streamdown", side_effect=AssertionError("unexpected streamdown")):
            writer.write("# Hello")
            writer.write("\n")
            writer.close()

        self.assertEqual(stream.getvalue(), "# Hello\n")
        self.assertEqual(FakeRenderer.instances, [])

    def test_rendered_output_uses_streamdown_and_tidyup(self):
        writer = OutputWriter(raw=False, stream=StringIO())

        with patch("perplexity.cli._load_streamdown", side_effect=FakeRenderer):
            writer.write("# Hello")
            writer.write("\n")
            writer.close()

        self.assertEqual(FakeRenderer.instances[0].rendered, ["# Hello\n"])
        self.assertTrue(FakeRenderer.instances[0].closed)


class CliRunTest(unittest.TestCase):
    def setUp(self):
        FakePerplexity.instances = []
        FakeRenderer.instances = []

    def test_run_streams_parsed_output_to_streamdown_by_default(self):
        args = build_parser().parse_args(["-a", "me@example.com", "hello", "world"])

        with patch("perplexity.cli.Perplexity", FakePerplexity):
            with patch("perplexity.cli._load_streamdown", side_effect=FakeRenderer):
                self.assertEqual(run(args), 0)

        self.assertEqual(FakePerplexity.instances[0].account, "me@example.com")
        self.assertEqual(FakePerplexity.instances[0].prompt, "hello world")
        self.assertEqual(FakePerplexity.instances[0].mode, "concise")
        self.assertEqual(FakeRenderer.instances[0].rendered, ["# Hello\n\n", "World\n"])
        self.assertTrue(FakeRenderer.instances[0].closed)
        self.assertTrue(FakePerplexity.instances[0].closed)

    def test_run_raw_prints_parsed_markdown_without_event_dump(self):
        args = build_parser().parse_args(["--raw", "--pro", "hello"])
        stream = StringIO()

        with patch("perplexity.cli.Perplexity", FakePerplexity):
            with patch("perplexity.cli.sys.stdout", stream):
                self.assertEqual(run(args), 0)

        self.assertEqual(stream.getvalue(), "# Hello\n\nWorld\n")
        self.assertEqual(FakePerplexity.instances[0].mode, "copilot")
        self.assertEqual(FakeRenderer.instances, [])


if __name__ == "__main__":
    unittest.main()
