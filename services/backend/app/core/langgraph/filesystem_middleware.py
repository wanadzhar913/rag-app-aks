"""Custom filesystem middleware tweaks for DeepAgents."""

from typing import cast

from deepagents.middleware.filesystem import (
    NUM_CHARS_PER_TOKEN,
    FilesystemMiddleware,
    ToolMessage,
    _build_evicted_content,
    _create_content_preview,
    _extract_text_from_message,
)


PREVIEW_ONLY_TOOL_MSG = """Tool result was too large to include in full, so only a preview is shown below.

If you need more detail, rerun the tool with a narrower query or stronger filters.

Preview:

{content_sample}
"""


class PreviewOnlyFilesystemMiddleware(FilesystemMiddleware):
    """Avoid persisting oversized tool results to files.

    DeepAgents normally writes large tool outputs to `/large_tool_results/<call_id>`.
    For this app we keep only a preview in the message history so the agent does not
    create artifact files inside the project tree.
    """

    def _process_large_message(self, message: ToolMessage, resolved_backend):  # type: ignore[override]
        del resolved_backend

        if not self._tool_token_limit_before_evict:
            return message, None

        content_str = _extract_text_from_message(message)
        if len(content_str) <= NUM_CHARS_PER_TOKEN * self._tool_token_limit_before_evict:
            return message, None

        content_sample = _create_content_preview(content_str)
        replacement_text = PREVIEW_ONLY_TOOL_MSG.format(content_sample=content_sample)
        evicted = _build_evicted_content(message, replacement_text)
        processed_message = ToolMessage(
            content=cast("str | list[str | dict]", evicted),
            tool_call_id=message.tool_call_id,
            name=message.name,
            id=message.id,
            artifact=message.artifact,
            status=message.status,
            additional_kwargs=dict(message.additional_kwargs),
            response_metadata=dict(message.response_metadata),
        )
        return processed_message, None

    async def _aprocess_large_message(self, message: ToolMessage, resolved_backend):  # type: ignore[override]
        del resolved_backend
        return self._process_large_message(message, None)
