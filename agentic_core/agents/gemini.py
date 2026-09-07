"""Google-only model access with controlled generation.

Used by the ablation control arm in `app/ablation.py`, which asks Gemini to
identify a fragment with no tools and no web access at all. That arm has to be a
direct, minimal Gemini call rather than an ADK workflow: the point of the
control is to measure what the model does *without* any of the machinery this
product adds, so it must not inherit any of it.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any

from google import genai
from google.genai import types


class GeminiJsonGenerator:
    def __init__(self, *, project: str, location: str, model: str) -> None:
        self.model = model
        self.client = genai.Client(vertexai=True, project=project, location=location)

    def generate(
        self,
        *,
        prompt: str,
        response_schema: Mapping[str, Any],
        system_instruction: str,
        media: Sequence[tuple[bytes, str]] = (),
        temperature: float = 0.0,
    ) -> dict[str, Any]:
        """Return a schema-conforming JSON object.

        `media` is a sequence of (bytes, mime_type). Temperature defaults to 0 so
        a control measurement is reproducible; the caller can raise it when the
        question is what the model does on a typical sampling run rather than its
        single most likely answer.
        """
        parts: list[types.Part] = [types.Part(text=prompt)]
        for data, mime_type in media:
            parts.append(types.Part.from_bytes(data=data, mime_type=mime_type))
        contents = types.Content(role="user", parts=parts)

        response = self.client.models.generate_content(
            model=self.model,
            contents=[contents],
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                response_json_schema=dict(response_schema),
                temperature=temperature,
            ),
        )
        if not response.text:
            raise RuntimeError("Gemini returned no structured text")
        value = json.loads(response.text)
        if not isinstance(value, dict):
            raise TypeError("Gemini response must be a JSON object")
        usage = getattr(response, "usage_metadata", None)
        if usage is not None:
            value["_usage"] = {
                "prompt_tokens": getattr(usage, "prompt_token_count", None),
                "output_tokens": getattr(usage, "candidates_token_count", None),
                "total_tokens": getattr(usage, "total_token_count", None),
            }
        return value
