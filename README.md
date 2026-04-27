# Vox-Dispatcher

Vox-Dispatcher turns typed or spoken commands into structured JSON and publishes the result to MQTT.

It is built for local-first control flows: a desktop UI for direct input, optional Faster-Whisper speech-to-text, a local LLM for intent routing, and one MQTT output topic for downstream systems.

## Core Features

- Desktop UI for direct text input
- Optional Faster-Whisper speech input
- Local LLM routing to structured JSON
- Single MQTT output topic for downstream consumers
- Thin orchestration entrypoint with isolated services

## How It Works

1. The UI accepts typed text directly.
2. An optional STT loop captures voice and converts it to text.
3. The dispatcher service sends command text to the local LLM.
4. The LLM returns a structured JSON action payload.
5. The dispatcher publishes that JSON as text to an MQTT output topic.

The application entrypoint stays thin and only wires together UI, services, and optional background loops.

## Repository Structure

- app.py: application entry point and orchestration startup
- logging_config.py: centralized logging setup
- clients/llm_client.py: local LLM request/response handling
- clients/mqtt_client.py: MQTT connection and publish/subscribe utilities
- clients/stt_client.py: Faster-Whisper speech-to-text client
- services/dispatcher_service.py: command processing and MQTT output publishing
- services/stt_loop.py: background STT worker loop
- ui/ui_chat.py: desktop chat UI for direct text input

## Output Contract

The dispatcher publishes one JSON payload as text to one MQTT topic.

Current payload fields:
- intent
- action
- target
- parameters

Default topic:
- `vox/output/text`

Override with:
- `MQTT_OUTPUT_TEXT_TOPIC`

## Quick Start

### 1) Prerequisites

- Python 3.10+
- An MQTT broker (local or remote)
- A local LLM runtime compatible with your llm_client implementation

### 2) Create and activate a virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3) Install dependencies

```powershell
pip install -r requirements.txt
```

### 4) Set minimum environment

PowerShell example:

```powershell
$env:MQTT_HOST = "127.0.0.1"
$env:MQTT_PORT = "1883"
$env:ENABLE_LLM_ROUTING = "true"
$env:LLM_MODEL = "qwen2.5:7b"
$env:LLM_HOST = "http://127.0.0.1:11434"
```

### 5) Run

```powershell
python app.py
```

## Runtime Behavior

By default:
- The desktop UI starts immediately.
- Typed text is sent directly to the dispatcher service.
- The LLM response is shown in the UI.
- The structured JSON response is published to `vox/output/text`.
- STT is disabled unless explicitly enabled.

## Configuration

Set environment variables as needed:
- MQTT_HOST
- MQTT_PORT
- MQTT_USERNAME
- MQTT_PASSWORD
- MQTT_OUTPUT_TEXT_TOPIC
- ENABLE_LLM_ROUTING
- LLM_MODEL
- LLM_HOST
- FEATURE_STT_ENABLED
- STT_MODEL
- STT_DEVICE
- STT_COMPUTE_TYPE
- STT_LANGUAGE
- STT_BEAM_SIZE
- STT_VAD_FILTER
- STT_SAMPLE_RATE
- STT_CHUNK_SECONDS

## Faster-Whisper Quick Start

Set environment variables (PowerShell example):

```powershell
$env:MQTT_HOST = "127.0.0.1"
$env:MQTT_PORT = "1883"

$env:FEATURE_STT_ENABLED = "true"
$env:STT_MODEL = "small.en"
$env:STT_DEVICE = "auto"
$env:STT_COMPUTE_TYPE = "int8"
$env:STT_LANGUAGE = "en"
$env:STT_CHUNK_SECONDS = "3.0"

$env:ENABLE_LLM_ROUTING = "true"
$env:LLM_MODEL = "llama3"
$env:LLM_HOST = "http://127.0.0.1:11434"
$env:MQTT_OUTPUT_TEXT_TOPIC = "vox/output/text"
```

Run the pipeline:

```powershell
python app.py
```

## Integration Pattern

For each target system:
1. Subscribe to the configured output topic.
2. Parse the incoming JSON payload.
3. Validate the payload against your schema.
4. Map action fields to local function calls.
5. Optionally publish success/failure acknowledgments.

This keeps Vox-Dispatcher as a control plane while each target remains owner of execution policy.

## Security and Safety Notes

When bridging language to execution, always add guardrails:
- Allowlist executable actions by service
- Validate payload shape and value ranges
- Require explicit confirmation for sensitive operations
- Log all command intents and outcomes
- Use role/topic-based access controls on MQTT

## Contributing

Contributions are welcome. A good pull request should include:
- Clear problem statement
- Minimal and modular changes
- Tests for new behavior
- Notes on message-contract impact

## License

Open source under the MIT License. Take it, modify it, and build cool things with it. See LICENSE for the serious legal words.
