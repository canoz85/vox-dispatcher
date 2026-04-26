import logging
import json
import time
from typing import Any

import ollama

from logging_config import log_extra

logger = logging.getLogger(__name__)


class LLMClient:
    def __init__(
        self,
        model: str = "llama3",
        system_prompt: str = "",
        host: str = "http://127.0.0.1:11434",
        keep_alive: str = "10m",
        think: bool = False,
        options: dict[str, Any] | None = None,
    ):
        self.model = model
        self.system_prompt = system_prompt
        self.keep_alive = keep_alive
        self.think = think
        self._chat_supports_think = True
        self._last_response_meta: dict[str, Any] = {}
        self.options = options or {
            "temperature": 0.2,
            "num_predict": 2000,
        }
        # Reuse HTTP connection/session to reduce per-request overhead.
        self._client = ollama.Client(host=host)

    def ask(
        self,
        prompt: str,
        response_format: str | None = None,
        options_override: dict[str, Any] | None = None,
        think_override: bool | None = None,
    ) -> str:
        messages = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        messages.append({"role": "user", "content": prompt})
        request_options = dict(self.options)
        if options_override:
            request_options.update(options_override)

        try:
            start = time.perf_counter()
            effective_think = self.think if think_override is None else bool(think_override)
            chat_kwargs = {
                "model": self.model,
                "messages": messages,
                "format": response_format,
                "options": request_options,
                "keep_alive": self.keep_alive,
            }
            if self._chat_supports_think:
                chat_kwargs["think"] = effective_think

            try:
                response = self._client.chat(**chat_kwargs)
            except TypeError as exc:
                # Backward compatibility for ollama-python versions without `think`.
                if "think" not in str(exc):
                    raise
                self._chat_supports_think = False
                logger.warning(
                    "Installed ollama client does not support `think`; continuing without it",
                    extra=log_extra("LLM"),
                )
                chat_kwargs.pop("think", None)
                response = self._client.chat(**chat_kwargs)

            elapsed = time.perf_counter() - start
            answer = response["message"]["content"]
            done_reason = response.get("done_reason")
            thinking_len = len(str(response["message"].get("thinking", "") or ""))
            prompt_eval_count = int(response.get("prompt_eval_count", 0) or 0)
            prompt_eval_duration_ns = int(response.get("prompt_eval_duration", 0) or 0)
            eval_count = int(response.get("eval_count", 0) or 0)
            eval_duration_ns = int(response.get("eval_duration", 0) or 0)
            self._last_response_meta = {
                "done_reason": done_reason,
                "thinking_chars": thinking_len,
                "prompt_eval_count": prompt_eval_count,
                "eval_count": eval_count,
            }
            prompt_tps = 0.0
            gen_tps = 0.0
            total_tps = 0.0
            total_tokens = prompt_eval_count + eval_count
            total_duration_ns = prompt_eval_duration_ns + eval_duration_ns
            if prompt_eval_count > 0 and prompt_eval_duration_ns > 0:
                prompt_tps = prompt_eval_count / (prompt_eval_duration_ns / 1_000_000_000)
            if eval_count > 0 and eval_duration_ns > 0:
                gen_tps = eval_count / (eval_duration_ns / 1_000_000_000)
            if total_tokens > 0 and total_duration_ns > 0:
                total_tps = total_tokens / (total_duration_ns / 1_000_000_000)
            logger.info(
                "LLM latency=%.2fs prompt_tokens=%s gen_tokens=%s total_tokens=%s prompt_tps=%.2f gen_tps=%.2f total_tps=%.2f prompt_chars=%s done_reason=%s think=%s thinking_chars=%s",
                elapsed,
                prompt_eval_count,
                eval_count,
                total_tokens,
                prompt_tps,
                gen_tps,
                total_tps,
                len(prompt),
                done_reason,
                effective_think,
                thinking_len,
                extra=log_extra("LLM"),
            )
            logger.debug("LLM response: %s", answer, extra=log_extra("LLM"))
            # logger.debug("LLM response repr: %r", answer, extra=log_extra("LLM"))
            if not str(answer).strip():
                logger.warning(
                    "LLM returned empty content (repr=%r). raw_response=%s",
                    answer,
                    response,
                    extra=log_extra("LLM"),
                )
            return answer
        except Exception as exc:
            self._last_response_meta = {}
            logger.error("LLM error: %s", exc, extra=log_extra("LLM"))
            return f"ERROR: {exc}"

    def ask_json(
        self,
        prompt: str,
        options_override: dict[str, Any] | None = None,
        think_override: bool | None = None,
    ) -> dict:
        base_num_predict = int(self.options.get("num_predict", 0) or 0)
        # Reasoning models can consume tokens in internal thinking before content.
        initial_num_predict = max(base_num_predict, 160)
        request_options = {"num_predict": initial_num_predict}
        if options_override:
            request_options.update(options_override)

        print(prompt)

        raw = self.ask(
            prompt,
            response_format="json",
            options_override=request_options,
            think_override=think_override,
        )
        if raw.startswith("ERROR:"):
            raise RuntimeError(raw)

        if not raw.strip():
            last_done_reason = str(self._last_response_meta.get("done_reason", "")).strip()
            last_thinking_chars = int(self._last_response_meta.get("thinking_chars", 0) or 0)
            current_num_predict = int(request_options.get("num_predict", initial_num_predict) or initial_num_predict)
            logger.warning(
                "Empty JSON content from LLM (done_reason=%s thinking_chars=%s), retrying with larger num_predict",
                last_done_reason,
                last_thinking_chars,
                extra=log_extra("LLM"),
            )
            retry_num_predict = max(current_num_predict * 2, 1024)
            retry_prompt = (
                prompt
                + "\nReturn one complete JSON object now. No explanation. No thinking."
            )
            raw = self.ask(
                retry_prompt,
                response_format="json",
                options_override={"num_predict": retry_num_predict, "temperature": 0.0},
                think_override=False,
            )
            if raw.startswith("ERROR:"):
                raise RuntimeError(raw)

        if not raw.strip():
            raise ValueError("LLM returned empty JSON content after retry")

        # Accept direct JSON or extract the first JSON object if extra text appears.
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass

        start = raw.find("{")
        end = raw.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("No JSON object found in LLM response")

        return json.loads(raw[start : end + 1])
