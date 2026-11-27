"""Two-stage instrument classifier on the xAI API, plus a Signals extraction path.

The shape, gates and anti-hallucination rules follow Patricia Zhai's classifier.
Calls go to https://api.x.ai/v1 with XAI_API_KEY. OpenAI is not called and
OPENAI_API_KEY is not read. Results are not written into the register here.
"""

from __future__ import annotations

import json
import os
from typing import Any, Callable
from urllib.request import Request, urlopen

from pydantic import BaseModel, Field

from ts_monitor.signal_weights import actor_weight, band_for_weight
from ts_monitor.vocabularies import load_vocabularies

XAI_BASE_URL = "https://api.x.ai/v1"
XAI_CHAT_URL = f"{XAI_BASE_URL}/chat/completions"
DEFAULT_XAI_MODEL = "grok-4.7"
XAI_TEMPERATURE = 0.1

STATUS_ALIASES = {
    "breach identified": "under_review",
    "breach found": "under_review",
    "preliminary findings": "under_review",
    "investigation opened": "under_review",
    "investigation launched": "under_review",
    "consultation launched": "under_review",
    "consultation opened": "under_review",
    "entered into force": "effective",
    "comes into force": "effective",
    "in force": "effective",
}

STAGE1_SYSTEM = """You are a regulatory news classifier for online safety and trust and safety developments.

Decide whether the item is relevant official, regulatory or incident material. Relevant material includes:
- regulator or minister statements
- parliamentary debate
- child safety
- age assurance
- CSAM, NCII or deepfakes
- platform regulation
- gaming harms
- AI companions or chatbot harms
- social incidents that may trigger a government response

Drop items that are clearly not regulatory, official or incident-relevant.
Age assurance remains in scope. It is no longer the only topic that can pass this filter.

You will receive a title and a short snippet. Answer yes or no."""

STAGE1_USER = """Article Title: {title}
Article Snippet: {snippet}

Is this item regulatory, official or incident-relevant for online safety?"""

STAGE2_SYSTEM = """You are a regulatory intelligence analyst for online safety and trust and safety developments.

Classify this item into one of these categories:

1. "new_regulation_proposed" — A NEW regulation or bill has been proposed, introduced or announced for the first time.
2. "existing_regulation_development" — There is a DEVELOPMENT regarding an EXISTING regulation: a status change such as passage, signature, enforcement, a court challenge, an injunction or repeal.
3. "existing_regulation_report" — This is a REPORT or ANALYSIS about an existing regulation, or an official or political statement, with NO new bill and NO status change.
4. "not_relevant" — Not regulatory, official or incident-relevant.

Guidelines:
- If a law is being challenged in court, that is "existing_regulation_development" with status_change="challenged" or "enjoined".
- If a law takes effect or begins enforcement, that is "existing_regulation_development" with an appropriate status_change.
- If you provide status_change, it must be ONLY one of: {allowed_statuses}.
- Preliminary findings, breach notices, investigations and consultations should map to "under_review", not a custom label.
- Opinion pieces and analyses about existing laws without new actions are "existing_regulation_report".
- Only classify as "new_regulation_proposed" if this is genuinely the first report of a new legislative proposal.
- Do not infer exact age thresholds unless the article clearly states them.
- Do not convert broad minors-protection duties into "age verification" or "parental consent" unless the article explicitly describes those mechanisms.
- Treat "minimum age", "under X", and "X or older" carefully. Do not reverse the direction of the threshold.
- If the article protects minors generally but does not give a concrete age threshold, describe it in broad terms rather than inventing a number.
- If only high-level reporting is available, keep the summary conservative and avoid legal-detail hallucinations.
- A minister statement, parliamentary comment or incident response that does not itself change a legal instrument is "existing_regulation_report", not a new regulation.

Provide a confidence score from 0 to 1.

Here is the current database of existing regulations for reference:
{regulations_context}"""

STAGE2_USER = """Article Title: {title}
Article Snippet: {snippet}
URL: {url}

Classify this article according to the instructions."""

SIGNAL_SYSTEM = """You extract a regulatory signal from an official or political statement, or from an incident that may draw a government response.

This path is for items that are not themselves a new bill or a status change.
Use only people, offices and markets that the text supports. Do not invent a person, a title or a URL.

Set actor_class to a short label such as minister, head of government or president, european commissioner, regulator head, legislator, us state governor, attorney general, or ngo or civil society organisation.
Set speaking_as_department true only when a deputy or junior minister is clearly speaking for the department.
Set specific_risk_or_mechanism true only when the text names a concrete risk or mechanism, such as an age gate, a duty of care, a game restriction or a CSAM notice.
Set is_signal false when the item is not an attributable statement or incident response."""

SIGNAL_USER = """Article Title: {title}
Article Snippet: {snippet}
URL: {url}

Extract the signal fields."""


class Stage1Result(BaseModel):
    is_regulatory: bool = Field(description="Whether the item is regulatory, official or incident-relevant")
    reasoning: str = Field(description="Brief explanation of the decision")


class Stage2Result(BaseModel):
    action_type: str = Field(description="new_regulation_proposed, existing_regulation_development, existing_regulation_report or not_relevant")
    confidence: float = Field(ge=0, le=1)
    reasoning: str
    regulation_name: str | None = None
    jurisdiction: str | None = None
    status_change: str | None = None
    summary: str | None = None
    matched_regulation_id: str | None = None


class SignalExtraction(BaseModel):
    is_signal: bool
    confidence: float = Field(ge=0, le=1)
    reasoning: str
    actor_name: str | None = None
    office: str | None = None
    actor_class: str | None = None
    market_id: str | None = None
    specific_risk_or_mechanism: bool = False
    speaking_as_department: bool = False
    issue_or_focus: str | None = None
    summary: str | None = None


def _object_schema(properties: dict[str, Any], required: list[str]) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": properties,
        "required": required,
        "additionalProperties": False,
    }


def _nullable_string() -> dict[str, Any]:
    return {"type": ["string", "null"]}


STAGE1_SCHEMA = _object_schema(
    {"is_regulatory": {"type": "boolean"}, "reasoning": {"type": "string"}},
    ["is_regulatory", "reasoning"],
)
STAGE2_SCHEMA = _object_schema(
    {
        "action_type": {
            "type": "string",
            "enum": [
                "new_regulation_proposed",
                "existing_regulation_development",
                "existing_regulation_report",
                "not_relevant",
            ],
        },
        "confidence": {"type": "number"},
        "reasoning": {"type": "string"},
        "regulation_name": _nullable_string(),
        "jurisdiction": _nullable_string(),
        "status_change": _nullable_string(),
        "summary": _nullable_string(),
        "matched_regulation_id": _nullable_string(),
    },
    [
        "action_type",
        "confidence",
        "reasoning",
        "regulation_name",
        "jurisdiction",
        "status_change",
        "summary",
        "matched_regulation_id",
    ],
)
SIGNAL_SCHEMA = _object_schema(
    {
        "is_signal": {"type": "boolean"},
        "confidence": {"type": "number"},
        "reasoning": {"type": "string"},
        "actor_name": _nullable_string(),
        "office": _nullable_string(),
        "actor_class": _nullable_string(),
        "market_id": _nullable_string(),
        "specific_risk_or_mechanism": {"type": "boolean"},
        "speaking_as_department": {"type": "boolean"},
        "issue_or_focus": _nullable_string(),
        "summary": _nullable_string(),
    },
    [
        "is_signal",
        "confidence",
        "reasoning",
        "actor_name",
        "office",
        "actor_class",
        "market_id",
        "specific_risk_or_mechanism",
        "speaking_as_department",
        "issue_or_focus",
        "summary",
    ],
)

ALLOWED_ACTIONS = set(STAGE2_SCHEMA["properties"]["action_type"]["enum"])
Transport = Callable[[dict[str, Any]], dict[str, Any]]


def normalize_regulation_status(value: str | None, allowed: set[str] | None = None) -> str | None:
    """Alias a free-text status onto the frozen list, or return None."""
    if value is None:
        return None
    permitted = allowed if allowed is not None else set(load_vocabularies().get("status") or [])
    token = value.strip().lower().replace("-", "_").replace(" ", "_")
    if token in permitted:
        return token
    mapped = STATUS_ALIASES.get(value.strip().lower())
    if mapped in permitted:
        return mapped
    return None


def compact_regulations(path: str | os.PathLike[str] | None, limit: int = 400) -> str:
    """Read an existing regulation list for the prompt. This function does not write it."""
    if not path:
        return "No existing regulations in database."
    location = os.fspath(path)
    if not os.path.isfile(location):
        return "No existing regulations in database."
    with open(location, encoding="utf-8") as handle:
        data = json.load(handle)
    lines: list[str] = []
    for reg in data.get("regulations") or []:
        lines.append(
            f"- ID: {reg.get('id')} | Name: {reg.get('name')} | "
            f"Jurisdiction: {reg.get('jurisdiction_id')} | Status: {reg.get('status')}"
        )
        if len(lines) >= limit:
            break
    return "\n".join(lines) if lines else "No existing regulations in database."


def _default_transport(payload: dict[str, Any], api_key: str, timeout: int = 60) -> dict[str, Any]:
    request = Request(
        XAI_CHAT_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8", errors="replace"))


def _message_json(completion: dict[str, Any]) -> dict[str, Any]:
    content = completion["choices"][0]["message"]["content"]
    if isinstance(content, dict):
        return content
    text = str(content).strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()
    return json.loads(text)


class XaiClassifier:
    """OpenAI-compatible chat client aimed only at the xAI API."""

    def __init__(
        self,
        api_key: str | None = None,
        *,
        model: str | None = None,
        transport: Transport | None = None,
    ):
        self.api_key = (api_key if api_key is not None else os.environ.get("XAI_API_KEY", "")).strip()
        self.model = model or os.environ.get("XAI_MODEL", DEFAULT_XAI_MODEL)
        self._transport = transport

    def available(self) -> bool:
        return bool(self.api_key)

    def complete(self, messages: list[dict[str, str]], schema_name: str, schema: dict[str, Any]) -> dict[str, Any]:
        if not self.api_key:
            raise RuntimeError("XAI_API_KEY is not set. Classification is skipped.")
        payload = {
            "model": self.model,
            "temperature": XAI_TEMPERATURE,
            "messages": messages,
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": schema_name, "strict": True, "schema": schema},
            },
        }
        if self._transport is not None:
            completion = self._transport(payload)
        else:
            completion = _default_transport(payload, self.api_key)
        return _message_json(completion)

    def classify(self, article: dict[str, Any], regulations_context: str) -> dict[str, Any] | None:
        title = str(article.get("title") or "")
        snippet = str(article.get("description") or article.get("content") or "")
        url = str(article.get("url") or "")
        source = article.get("source") or {}
        source_name = source.get("name") if isinstance(source, dict) else str(source or "")
        stage1 = Stage1Result.model_validate(
            self.complete(
                [
                    {"role": "system", "content": STAGE1_SYSTEM},
                    {
                        "role": "user",
                        "content": STAGE1_USER.format(title=title, snippet=snippet[:500]),
                    },
                ],
                "stage1_result",
                STAGE1_SCHEMA,
            )
        )
        if not stage1.is_regulatory:
            return None
        allowed = ", ".join(load_vocabularies().get("status") or [])
        stage2 = Stage2Result.model_validate(
            self.complete(
                [
                    {
                        "role": "system",
                        "content": STAGE2_SYSTEM.format(
                            allowed_statuses=allowed,
                            regulations_context=regulations_context,
                        ),
                    },
                    {
                        "role": "user",
                        "content": STAGE2_USER.format(
                            title=title,
                            snippet=snippet[:1000],
                            url=url,
                        ),
                    },
                ],
                "stage2_result",
                STAGE2_SCHEMA,
            )
        )
        if stage2.action_type not in ALLOWED_ACTIONS:
            stage2.action_type = "not_relevant"
        status_change = normalize_regulation_status(stage2.status_change)
        instrument_action = stage2.action_type in {
            "new_regulation_proposed",
            "existing_regulation_development",
        }
        signal: SignalExtraction | None = None
        if not instrument_action:
            signal = SignalExtraction.model_validate(
                self.complete(
                    [
                        {"role": "system", "content": SIGNAL_SYSTEM},
                        {
                            "role": "user",
                            "content": SIGNAL_USER.format(title=title, snippet=snippet[:1000], url=url),
                        },
                    ],
                    "signal_extraction",
                    SIGNAL_SCHEMA,
                )
            )
        weight = None
        band = None
        specific = False
        is_signal = False
        confidence = stage2.confidence
        action_type = stage2.action_type
        summary = stage2.summary
        reasoning = stage2.reasoning
        if signal is not None:
            is_signal = signal.is_signal
            specific = signal.specific_risk_or_mechanism
            weight = actor_weight(
                signal.actor_class,
                specific,
                speaking_as_department=signal.speaking_as_department,
            )
            band = band_for_weight(weight)
            if not instrument_action and is_signal:
                confidence = signal.confidence
                action_type = "signal"
                summary = signal.summary or summary
                reasoning = signal.reasoning
        return {
            "title": title,
            "url": url,
            "source": source_name or "",
            "published_at": str(article.get("publishedAt") or article.get("published_at") or ""),
            "snippet": snippet[:1000],
            "action_type": action_type,
            "confidence": confidence,
            "reasoning": reasoning,
            "regulation_name": stage2.regulation_name,
            "jurisdiction": stage2.jurisdiction,
            "status_change": status_change,
            "summary": summary,
            "matched_regulation_id": stage2.matched_regulation_id,
            "is_signal": is_signal,
            "actor_name": signal.actor_name if signal else None,
            "office": signal.office if signal else None,
            "actor_class": signal.actor_class if signal else None,
            "market_id": signal.market_id if signal else None,
            "actor_weight": weight,
            "weight_band": band,
            "specific_risk_or_mechanism": specific,
            "stage1_reasoning": stage1.reasoning,
        }
