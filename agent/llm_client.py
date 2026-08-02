from __future__ import annotations

import json
import logging
import os
import pathlib
from dataclasses import dataclass

from .prompts import SYSTEM_PROMPT, build_user_prompt

logger = logging.getLogger(__name__)

DEFAULT_MODEL = os.getenv("LITELLM_MODEL", "gpt-4o")


@dataclass
class FlakeAnalysisResult:
    is_flaky: bool
    category: str
    category_label: str
    confidence: str
    root_cause_summary: str
    suggested_fix: str
    affected_test: str
    affected_file: str

    @classmethod
    def from_dict(cls, d: dict) -> "FlakeAnalysisResult":
        return cls(
            is_flaky=bool(d.get("is_flaky", True)),
            category=d.get("category", "A"),
            category_label=d.get("category_label", "Unknown"),
            confidence=d.get("confidence", "low"),
            root_cause_summary=d.get("root_cause_summary", ""),
            suggested_fix=d.get("suggested_fix", ""),
            affected_test=d.get("affected_test", ""),
            affected_file=d.get("affected_file", ""),
        )


class FlakeAnalysisAgent:
    """Agent engine that queries the LLM to analyze CI failures."""

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        max_tool_calls: int = 3,
        temperature: float = 0.1,
    ) -> None:
        self.model = model
        self.max_tool_calls = max_tool_calls
        self.temperature = temperature

    def analyse(
        self,
        framework: str,
        test_name: str,
        source_location: str,
        run_id: int | str,
        is_flaky: bool,
        failure_snippet: str,
        source_code: str = "",
    ) -> FlakeAnalysisResult:
        user_msg = build_user_prompt(
            framework=framework,
            test_name=test_name,
            source_location=source_location,
            run_id=run_id,
            is_flaky=is_flaky,
            failure_snippet=failure_snippet,
            source_code=source_code,
        )

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ]

        import litellm

        logger.info("Sending failure to LLM model=%s for test=%s", self.model, test_name)

        response = litellm.completion(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            response_format={"type": "json_object"},
        )

        raw_json = response.choices[0].message.content
        logger.debug("LLM raw response: %s", raw_json[:500])

        try:
            data = json.loads(raw_json)
        except json.JSONDecodeError as exc:
            logger.error("LLM returned invalid JSON: %s", exc)
            return FlakeAnalysisResult(
                is_flaky=is_flaky,
                category="A",
                category_label="Unknown – JSON parse error",
                confidence="low",
                root_cause_summary=f"LLM response could not be parsed: {raw_json[:200]}",
                suggested_fix="Inspect the raw log manually.",
                affected_test=test_name,
                affected_file=source_location,
            )

        return FlakeAnalysisResult.from_dict(data)

    def _maybe_fetch_source(self, file_path: str, codebase_root: str) -> str:
        """Helper to read source files for context enrichment."""
        full = pathlib.Path(codebase_root) / file_path.lstrip("/")
        if not full.exists():
            return f"# File not found: {file_path}"
        try:
            return full.read_text(encoding="utf-8", errors="replace")[:3000]
        except OSError as exc:
            return f"# Could not read {file_path}: {exc}"
