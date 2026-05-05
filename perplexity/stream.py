from typing import Any, Dict, Iterable, Optional


class AnswerStreamParser:
    """Extract live answer text deltas from Perplexity websocket events."""

    def __init__(self) -> None:
        self.text = ""
        self._chunk_count = 0

    def feed(self, event: Dict[str, Any]) -> str:
        state = self._event_state(event)
        if state is None:
            return ""
        text, chunk_count = state

        if text.startswith(self.text):
            delta = text[len(self.text):]
            self.text = text
            self._chunk_count = chunk_count
            return delta

        if self.text.startswith(text):
            return ""

        prefix_len = self._common_prefix_len(self.text, text)
        if prefix_len == len(self.text):
            delta = text[prefix_len:]
            self.text = text
            self._chunk_count = chunk_count
            return delta

        return ""

    def parse(self, events: Iterable[Dict[str, Any]]) -> Iterable[str]:
        for event in events:
            delta = self.feed(event)
            if delta:
                yield delta

    def _event_state(self, event: Dict[str, Any]) -> Optional[tuple[str, int]]:
        blocks = event.get("blocks")
        if not isinstance(blocks, list):
            return None

        for usage in ("ask_text_0_markdown", "ask_text"):
            for block in blocks:
                if block.get("intended_usage") == usage:
                    state = self._markdown_block_state(block.get("markdown_block"))
                    if state is not None:
                        return state

        for block in blocks:
            if isinstance(block.get("markdown_block"), dict):
                state = self._markdown_block_state(block["markdown_block"])
                if state is not None:
                    return state

        return None

    def _markdown_block_state(self, block: Any) -> Optional[tuple[str, int]]:
        if not isinstance(block, dict):
            return None

        chunks = block.get("chunks")
        answer = block.get("answer")
        if isinstance(answer, str):
            chunk_count = len(chunks) if isinstance(chunks, list) else self._chunk_count
            return answer, chunk_count

        if not isinstance(chunks, list):
            return None

        chunk_text = "".join(chunk for chunk in chunks if isinstance(chunk, str))
        offset = block.get("chunk_starting_offset", 0)
        if isinstance(offset, int) and offset == self._chunk_count:
            return self.text + chunk_text, offset + len(chunks)

        if offset == 0:
            return chunk_text, len(chunks)

        return None

    def _common_prefix_len(self, left: str, right: str) -> int:
        length = min(len(left), len(right))
        for index in range(length):
            if left[index] != right[index]:
                return index
        return length
