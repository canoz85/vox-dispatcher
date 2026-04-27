import json
import logging
import threading

from clients import LLMClient, MQTTClient
from logging_config import log_extra

logger = logging.getLogger(__name__)


class DispatcherService:
    def __init__(
        self,
        mqtt_client: MQTTClient,
        llm_client: LLMClient | None,
        output_text_topic: str,
        system_prompt: str,
    ) -> None:
        self._mqtt_client = mqtt_client
        self._llm_client = llm_client
        self._output_text_topic = output_text_topic
        self._system_prompt = system_prompt
        self._llm_lock = threading.Lock()

    def process_command(self, text: str) -> str:
        clean_text = text.strip()
        if not clean_text:
            return ""

        logger.info("LLM_INPUT_TEXT: %s", clean_text, extra=log_extra("APP"))

        if self._llm_client is None:
            return "LLM routing is disabled"

        prompt = (
            f"{self._system_prompt}\n"
            f"command: {clean_text}"
        )
        with self._llm_lock:
            action = self._llm_client.ask_json(prompt)
        response_text = json.dumps(action, ensure_ascii=False)
        self._mqtt_client.publish(self._output_text_topic, response_text)
        logger.info("LLM_OUTPUT_TEXT: %s", response_text, extra=log_extra("APP"))
        return response_text
