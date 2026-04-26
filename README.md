# Vox-Dispatcher

Vox-Dispatcher is a modular Python-based AI hub that converts natural language voice commands into executable program actions.

It uses local LLMs for intent interpretation and MQTT pub/sub for decoupled message routing, making it easy to add voice control to existing systems without rewriting their core logic.

## Why Vox-Dispatcher

Most projects are not built around natural language interaction. Retrofitting voice control often means invasive rewrites, fragile adapters, or tight coupling between UI and runtime internals.

Vox-Dispatcher solves this by acting as a protocol bridge:
- Human intent in natural language
- Structured command dispatch over MQTT
- Existing services remain independent and unchanged

## Core Features

- Local LLM integration for private, low-latency inference
- MQTT-based pub/sub messaging for modular interoperability
- Python-first orchestration layer that is simple to extend
- Project-agnostic design for games, robotics, RL pipelines, and automation
- Non-invasive integration with existing runtimes and codebases

## Architecture Overview

Vox-Dispatcher sits between user intent and execution targets:

1. Input layer receives voice text (or pre-transcribed command text).
2. LLM layer interprets intent and outputs a structured action payload.
3. Dispatcher layer publishes action messages to MQTT topics.
4. Subscribers in external systems consume and execute actions.

Because communication is topic-based, each subsystem can evolve independently.

## Repository Structure

- app.py: application entry point and orchestration startup
- logging_config.py: centralized logging setup
- clients/llm_client.py: local LLM request/response handling
- clients/mqtt_client.py: MQTT connection and publish/subscribe utilities

## Example Use Cases

- C++ game engine control:
  - "Spawn 10 NPCs near the player"
  - "Switch to cinematic camera"
- Reinforcement learning workflow control:
  - "Start training with curriculum mode"
  - "Pause training and save checkpoint"
- General automation:
  - "Run diagnostics on service group B"
  - "Restart the perception module"

## Message Contract Strategy

Keep integration stable by defining explicit message contracts:
- Topic naming conventions by domain and action
- JSON schema for action payloads
- Correlation IDs for traceability
- Ack/error topics for delivery and execution status

Recommended baseline payload fields:
- source
- intent
- action
- target
- parameters
- timestamp
- correlation_id

## Getting Started

## 1) Prerequisites

- Python 3.10+
- An MQTT broker (local or remote)
- A local LLM runtime compatible with your llm_client implementation

## 2) Clone and enter project

```powershell
git clone <your-repo-url>
cd vox-dispatcher
```

## 3) Create and activate virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

## 4) Install dependencies

If you have a requirements file:

```powershell
pip install -r requirements.txt
```

Otherwise, install package dependencies used by your current implementation.

## 5) Configure runtime

Set environment variables (example names):
- MQTT_HOST
- MQTT_PORT
- MQTT_USERNAME
- MQTT_PASSWORD
- LLM_ENDPOINT or local model config
- LLM_MODEL

## 6) Run

```powershell
python app.py
```

## Faster-Whisper Quick Start

Install dependencies:

```powershell
pip install -r requirements.txt
```

Set environment variables (PowerShell example):

```powershell
$env:MQTT_HOST = "127.0.0.1"
$env:MQTT_PORT = "1883"

$env:STT_MODEL = "small.en"
$env:STT_DEVICE = "auto"
$env:STT_COMPUTE_TYPE = "int8"
$env:STT_LANGUAGE = "en"
$env:STT_CHUNK_SECONDS = "3.0"

$env:ENABLE_LLM_ROUTING = "true"
$env:LLM_MODEL = "llama3"
$env:LLM_HOST = "http://127.0.0.1:11434"
```

Run the pipeline:

```powershell
python app.py
```

Default MQTT topics:
- Transcript text: `vox/input/text`
- Structured actions: `vox/output/action`

You can override topic names with:
- `MQTT_TRANSCRIPT_TOPIC`
- `MQTT_ACTION_TOPIC`

## Integration Pattern

For each target system:
1. Subscribe to the agreed action topics.
2. Validate incoming payload against your schema.
3. Map action fields to local function calls.
4. Publish success/failure acknowledgments.

This keeps Vox-Dispatcher as a control plane while each target remains owner of execution policy.

## Design Principles

- Decoupling over direct binding
- Explicit contracts over implicit parsing
- Local-first AI for privacy and reliability
- Observable flows with structured logging
- Extend by adding adapters, not modifying core services

## Security and Safety Notes

When bridging language to execution, always add guardrails:
- Allowlist executable actions by service
- Validate payload shape and value ranges
- Require explicit confirmation for sensitive operations
- Log all command intents and outcomes
- Use role/topic-based access controls on MQTT

## Testing Recommendations

- Unit tests for LLM output parsing and validation
- Contract tests for MQTT payload schemas
- Integration tests with a test broker and mock subscribers
- Failure-path tests (broker disconnect, malformed payload, timeout)

## Roadmap

- Add formal JSON schema validation layer
- Add retry and dead-letter topic strategy
- Add policy engine for action authorization
- Add adapter templates for common engines/frameworks
- Add observability dashboard for command flow metrics

## Contributing

Contributions are welcome. A good pull request should include:
- Clear problem statement
- Minimal and modular changes
- Tests for new behavior
- Notes on message-contract impact

## License

Add your preferred license here (MIT, Apache-2.0, etc.).

## Elevator Pitch

Vox-Dispatcher makes voice-driven control practical for real systems by translating natural language into structured MQTT actions, powered by local LLMs and designed for plug-in interoperability.
