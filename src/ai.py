from __future__ import annotations

import base64
import json
import re
from typing import Any

from openai import OpenAI


LANGUAGES = [
    "Eesti",
    "English",
    "Deutsch",
    "Suomi",
    "Svenska",
    "Latviešu",
    "Lietuvių",
    "Polski",
    "Русский",
    "Français",
    "Español",
]


def _response_text(response: Any) -> str:
    text = getattr(response, "output_text", None)
    if text:
        return text
    chunks: list[str] = []
    for item in getattr(response, "output", []) or []:
        for content in getattr(item, "content", []) or []:
            value = getattr(content, "text", None)
            if value:
                chunks.append(value)
    return "\n".join(chunks)


def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.I)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start : end + 1])
        raise


def ocr_image(client: OpenAI, image_bytes: bytes, mime_type: str, language: str, model: str) -> str:
    encoded = base64.b64encode(image_bytes).decode("ascii")
    prompt = (
        f"Read all educational text visible in this image. The source language is {language}. "
        "Preserve headings, lists, formulas and paragraph order. Do not summarize and do not invent missing text. "
        "Return only the transcription."
    )
    response = client.responses.create(
        model=model,
        input=[
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt},
                    {
                        "type": "input_image",
                        "image_url": f"data:{mime_type};base64,{encoded}",
                        "detail": "high",
                    },
                ],
            }
        ],
    )
    return _response_text(response).strip()


def describe_image(client: OpenAI, image_bytes: bytes, mime_type: str, model: str) -> str:
    encoded = base64.b64encode(image_bytes).decode("ascii")
    response = client.responses.create(
        model=model,
        input=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": (
                            "Describe this image in one compact sentence for an educational slide designer. "
                            "Say what is visibly depicted; do not infer facts not visible. If it is mostly a page of text, say so."
                        ),
                    },
                    {
                        "type": "input_image",
                        "image_url": f"data:{mime_type};base64,{encoded}",
                        "detail": "low",
                    },
                ],
            }
        ],
    )
    return _response_text(response).strip()


def _chunk_text(text: str, max_chars: int = 16000) -> list[str]:
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if len(text) <= max_chars:
        return [text]
    chunks: list[str] = []
    pos = 0
    while pos < len(text):
        end = min(pos + max_chars, len(text))
        if end < len(text):
            split = text.rfind("\n\n", pos, end)
            if split <= pos + max_chars // 2:
                split = text.rfind(". ", pos, end)
            if split > pos:
                end = split + 1
        chunks.append(text[pos:end].strip())
        pos = end
    return [c for c in chunks if c]


def summarize_source(client: OpenAI, text: str, input_language: str, model: str) -> str:
    chunks = _chunk_text(text)
    summaries: list[str] = []
    for idx, chunk in enumerate(chunks, start=1):
        prompt = f"""
You are preparing source notes for an educational presentation.
Source language: {input_language}.
Summarize chunk {idx}/{len(chunks)} faithfully. Keep definitions, mechanisms, formulas, dates, names, examples,
important caveats and likely misconceptions. Do not add outside facts yet.

SOURCE CHUNK:
{chunk}
""".strip()
        response = client.responses.create(model=model, input=prompt)
        summaries.append(_response_text(response).strip())
    return "\n\n".join(f"CHUNK {i+1}:\n{s}" for i, s in enumerate(summaries))


def _deck_prompt(
    source_summary: str,
    input_language: str,
    output_language: str,
    slide_count: int,
    audience: str,
    image_descriptions: list[str],
) -> str:
    image_context = "\n".join(f"- uploaded:{i+1}: {d}" for i, d in enumerate(image_descriptions)) or "- none"
    return f"""
You are an expert teacher and instructional slide designer.
Create a concise classroom PowerPoint plan from the supplied educational source.

SOURCE LANGUAGE: {input_language}
OUTPUT LANGUAGE: {output_language}
AUDIENCE: {audience}
TARGET CONTENT SLIDES: {slide_count}

Requirements:
- Preserve the source's core learning content and correct terminology.
- You may add a small number of genuinely useful, surprising or clarifying facts from reliable web sources.
- Distinguish source-derived content from supplementary web facts internally; do not overwhelm the slides with citations.
- Each slide should communicate one main idea.
- Use 3-5 short bullets per slide, normally no more than 12 words per bullet.
- Teacher notes must be substantially richer than the visible bullets: about 90-180 words, with explanation, examples,
  questions to ask pupils, common misconceptions, or demonstration ideas where appropriate.
- Use formulas in Unicode/plain text that PowerPoint can display.
- For every slide provide an image_query suitable for Wikimedia Commons search.
- If one of the uploaded images clearly matches a slide, set uploaded_image_index to that 1-based number; otherwise null.
- Do not claim an uploaded image matches unless its description actually fits.
- references must contain reliable URLs for supplementary web facts you used. Keep it short.

UPLOADED IMAGE DESCRIPTIONS:
{image_context}

SOURCE SUMMARY:
{source_summary}

Return ONLY valid JSON with this exact top-level shape:
{{
  "deck_title": "...",
  "deck_subtitle": "...",
  "slides": [
    {{
      "title": "...",
      "bullets": ["..."],
      "teacher_notes": "...",
      "image_query": "...",
      "uploaded_image_index": null
    }}
  ],
  "references": [
    {{"title": "...", "url": "...", "used_for": "..."}}
  ]
}}
""".strip()


def generate_deck_plan(
    client: OpenAI,
    source_summary: str,
    input_language: str,
    output_language: str,
    slide_count: int,
    audience: str,
    image_descriptions: list[str],
    model: str,
    use_web: bool = True,
) -> dict[str, Any]:
    prompt = _deck_prompt(
        source_summary,
        input_language,
        output_language,
        slide_count,
        audience,
        image_descriptions,
    )

    kwargs: dict[str, Any] = {"model": model, "input": prompt}
    response = None
    if use_web:
        # The Responses API web tool has had two names across SDK/API versions.
        # Try the current name first, then the preview alias, then fall back gracefully.
        for tool_name in ("web_search", "web_search_preview"):
            try:
                response = client.responses.create(**kwargs, tools=[{"type": tool_name}])
                break
            except Exception:
                response = None
    if response is None:
        response = client.responses.create(**kwargs)

    plan = _extract_json(_response_text(response))
    if not isinstance(plan.get("slides"), list) or not plan["slides"]:
        raise ValueError("AI response did not contain a usable slides array.")
    return plan
