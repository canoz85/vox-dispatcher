import json
import logging
import os

from clients import FasterWhisperSTTClient, LLMClient, MQTTClient
from logging_config import log_extra, setup_logging
from services import DispatcherService, STTLoop
from ui.ui_chat import DispatcherUI

logger = logging.getLogger(__name__)


ACTION_JSON_SYSTEM_PROMPT = (
	"You are an intent router for voice commands. "
	"Return only valid JSON with keys: intent, action, target, parameters."
)


def _env_bool(name: str, default: bool) -> bool:
	raw = os.getenv(name)
	if raw is None:
		return default
	return raw.strip().lower() in {"1", "true", "yes", "on"}


def build_clients(
	stt_enabled: bool,
) -> tuple[MQTTClient, FasterWhisperSTTClient | None, LLMClient | None]:
	mqtt_host = os.getenv("MQTT_HOST", "127.0.0.1")
	mqtt_port = int(os.getenv("MQTT_PORT", "1883"))
	mqtt_user = os.getenv("MQTT_USERNAME")
	mqtt_pass = os.getenv("MQTT_PASSWORD")

	mqtt_client = MQTTClient(broker=mqtt_host, port=mqtt_port, client_id="vox-dispatcher")
	mqtt_client.connect(username=mqtt_user, password=mqtt_pass)

	stt_client: FasterWhisperSTTClient | None = None
	if stt_enabled:
		stt_client = FasterWhisperSTTClient(
			model_size=os.getenv("STT_MODEL", "medium"),
			device=os.getenv("STT_DEVICE", "cpu"),
			compute_type=os.getenv("STT_COMPUTE_TYPE", "float32"),
			language=os.getenv("STT_LANGUAGE", "tr"),
			beam_size=int(os.getenv("STT_BEAM_SIZE", "5")),
			vad_filter=_env_bool("STT_VAD_FILTER", True),
			sample_rate=int(os.getenv("STT_SAMPLE_RATE", "16000")),
			channels=1,
		)

	enable_llm = _env_bool("ENABLE_LLM_ROUTING", True)
	llm_client: LLMClient | None = None
	if enable_llm:
		llm_client = LLMClient(
			model=os.getenv("LLM_MODEL", "qwen2.5:7b"),
			host=os.getenv("LLM_HOST", "http://127.0.0.1:11434"),
			system_prompt=os.getenv("LLM_SYSTEM_PROMPT", ACTION_JSON_SYSTEM_PROMPT),
		)

	return mqtt_client, stt_client, llm_client


def main() -> None:
	setup_logging()
	logging.getLogger("httpx").setLevel(logging.WARNING)
	logging.getLogger("httpcore").setLevel(logging.WARNING)
	logging.getLogger("faster_whisper").setLevel(logging.WARNING)

	output_text_topic = os.getenv("MQTT_OUTPUT_TEXT_TOPIC", "vox/output/text")
	chunk_duration = float(os.getenv("STT_CHUNK_SECONDS", "3.0"))
	stt_enabled = _env_bool("FEATURE_STT_ENABLED", False)

	mqtt_client, stt_client, llm_client = build_clients(stt_enabled=stt_enabled)
	dispatcher_service = DispatcherService(
		mqtt_client=mqtt_client,
		llm_client=llm_client,
		output_text_topic=output_text_topic,
		system_prompt=ACTION_JSON_SYSTEM_PROMPT,
	)
	logger.info(
		"Orchestrator started output_text_topic=%s chunk=%.1fs",
		output_text_topic,
		chunk_duration,
		extra=log_extra("APP"),
	)
	stt_loop = STTLoop(
		stt_client=stt_client,
		process_command=dispatcher_service.process_command,
		chunk_duration=chunk_duration,
	)
	if stt_enabled:
		stt_loop.start()
	ui = DispatcherUI(on_submit=dispatcher_service.process_command)

	try:
		ui.run()
	except KeyboardInterrupt:
		logger.info("Shutting down", extra=log_extra("APP"))
	finally:
		stt_loop.stop()
		mqtt_client.disconnect()


if __name__ == "__main__":
	main()

