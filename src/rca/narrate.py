"""LLM narration — the only place an LLM touches this pipeline. It receives a
JSON object built entirely from ClickHouse aggregate results (see
pipeline._build_payload) and is instructed to narrate strictly from those
numbers, never to compute or invent new ones.
"""

import json

from google import genai
from google.genai import types

from .config import settings
from .tracing import Tracer

SYSTEM_PROMPT = """You are the narration layer of an automated root-cause analyst for ad-tech metrics.
You will receive a JSON object containing ONLY numbers and labels already computed by deterministic
ClickHouse queries: the anomaly that was detected, a decomposition of the revenue identity
(revenue = requests x fill_rate x render_rate x eCPM/1000) into its factors, and a ranked list of
dimension segments that were checked — split into ones that explain a meaningful share of the movement
and ones that were checked and ruled out (low explanatory power or too small a volume share to matter).

Each segment carries a `lift` value: lift = explanatory_power / volume_share, i.e. how much more of the
movement this segment explains than its size alone would predict. lift near 1 means the segment moved
exactly in proportion to everyone else (not a distinct cause, just following a broad/uniform effect);
lift well above 1 (the pipeline requires >= ~1.8 before calling a segment "primary") means it is
genuinely disproportionate and localized. `primary_segment` (if not null) is the one segment per drill
level that cleared that bar.

Rules:
- Cite only numbers that literally appear in the JSON. Never invent, estimate, or extrapolate a figure.
- State the metric, the direction and size of the move, and which factor(s) drove it.
- If a drill level's primary_segment is set, name that segment (e.g. "device_model=iPhone 13"), backed by
  its lift and explanatory_power, and go one level deeper if `deeper` is present (e.g. "...within iPhone
  13, further concentrated in region=NAM").
- If primary_segment is null at a level, say plainly that the movement was broad-based / proportional
  across segments at that level (cite one segment's lift near 1 as evidence), rather than forcing a cause.
- Explicitly name at least one dimension or segment that was checked and ruled out, citing its number.
- Plain language. No markdown headers, no bullet points. Under 150 words.
"""


def narrate(payload: dict, tracer: Tracer) -> str:
    client = genai.Client(api_key=settings.gemini_api_key)
    user_content = json.dumps(payload, indent=2, default=str)

    with tracer.span("narrate", input=payload, as_type="generation", model=settings.gemini_model) as span:
        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=user_content,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                max_output_tokens=1024,
                # This step only narrates numbers ClickHouse already computed, not
                # a reasoning task — full thinking mode burned the whole token
                # budget on internal thought tokens (~40s latency) before writing
                # any answer. MINIMAL keeps latency down to a couple of seconds,
                # matching the "diagnosed in seconds" requirement.
                thinking_config=types.ThinkingConfig(thinking_level=types.ThinkingLevel.MINIMAL),
            ),
        )
        text = response.text
        span.set_output(text)
        return text
