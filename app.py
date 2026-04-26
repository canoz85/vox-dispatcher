import json
import logging
import os

from clients import FasterWhisperSTTClient, LLMClient, MQTTClient
from logging_config import log_extra, setup_logging

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


def build_clients() -> tuple[MQTTClient, FasterWhisperSTTClient, LLMClient | None]:
	mqtt_host = os.getenv("MQTT_HOST", "127.0.0.1")
	mqtt_port = int(os.getenv("MQTT_PORT", "1883"))
	mqtt_user = os.getenv("MQTT_USERNAME")
	mqtt_pass = os.getenv("MQTT_PASSWORD")

	mqtt_client = MQTTClient(broker=mqtt_host, port=mqtt_port, client_id="vox-dispatcher")
	mqtt_client.connect(username=mqtt_user, password=mqtt_pass)

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

	input_topic = os.getenv("MQTT_TRANSCRIPT_TOPIC", "vox/input/text")
	action_topic = os.getenv("MQTT_ACTION_TOPIC", "vox/output/action")
	chunk_duration = float(os.getenv("STT_CHUNK_SECONDS", "3.0"))

	mqtt_client, stt_client, llm_client = build_clients()
	logger.info(
		"Voice pipeline started input_topic=%s action_topic=%s chunk=%.1fs",
		input_topic,
		action_topic,
		chunk_duration,
		extra=log_extra("APP"),
	)

	try:
		while True:
			logger.info("Listening for %.1fs... speak now", chunk_duration, extra=log_extra("STT"))
			transcript = stt_client.listen_and_transcribe_once(duration_sec=chunk_duration)
			if not transcript:
				continue
			
			mqtt_client.publish(input_topic, transcript)
			logger.info("STT_TEXT: %s", transcript, extra=log_extra("APP"))

			if llm_client is None:
				continue

			llm_input_text = transcript
			logger.info("LLM_INPUT_TEXT: %s", llm_input_text, extra=log_extra("APP"))

			prompt = (
				"Convert the voice command into one JSON object with keys: "
				"intent, action, target, parameters.\n"
				f"command: {llm_input_text}"
			)
			action = llm_client.ask_json(prompt)
			mqtt_client.publish(action_topic, json.dumps(action))
			logger.info("Action: %s", action, extra=log_extra("APP"))
	except KeyboardInterrupt:
		logger.info("Shutting down", extra=log_extra("APP"))
	finally:
		mqtt_client.disconnect()


if __name__ == "__main__":
	main()

