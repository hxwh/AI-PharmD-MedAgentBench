# PharmAgent-MedAgentBench: Medical AI Agent Evaluation Platform

A comprehensive evaluation system for medical AI agents, implementing the AgentBeats A2A protocol. Benchmarks LLM agents on Stanford MedAgentBench clinical reasoning tasks using dynamic FHIR data and provides automated scoring with failure taxonomy.

**Built on:** [RDI-Foundation/green-agent-template](https://github.com/RDI-Foundation/green-agent-template)  
**Compatible with:** [AgentBeats](https://agentbeats.dev) platform

## Overview

PharmAgent evaluates medical AI agents on 10 clinical reasoning tasks from Stanford MedAgentBench:
- Patient data queries and calculations
- Vital signs recording and lab ordering
- Medication management and consult ordering

**Architecture:**
- **Green Agent** (Evaluator): Orchestrates evaluation and provides ground truth
- **Purple Agent** (Participant): Your AI agent being tested
- **A2A Protocol**: Standardized agent communication
- **MCP Server**: FHIR tools for medical data access
- **PocketFlow**: Workflow orchestration engine

**Compatible with:** [AgentBeats](https://agentbeats.dev) platform

## Quick Start

### Minimal Setup (5 minutes)

```bash
# 1. Install dependencies
uv sync --extra green

# 2. Configure API key
cp sample.env .env
# Edit .env with GOOGLE_API_KEY

# 3. Start evaluator
python src/server.py

# 4. Run evaluation
uv run medagentbench-run config/scenario.toml
```

### Full Setup (with FHIR data)

```bash
# Start all services
./benchmark.sh --serve-only

# Run complete benchmark (300 tasks)
./benchmark.sh --all
```

## Installation

### Prerequisites
- Python 3.10+
- Google Gemini API key ([Get here](https://ai.google.dev/gemini-api/docs/api-key))
- Docker (optional, for FHIR server)

### Setup
```bash
# Clone and enter directory
cd PharmAgent

# Install dependencies
uv sync --extra green

# Configure environment
cp sample.env .env
# Edit .env with your GOOGLE_API_KEY
```

## Usage

### Basic Evaluation

```bash
# Start evaluator agent
python src/server.py

# Run single task evaluation
python scripts/run_evaluation.py --task task1_1
```

### Full Benchmark

```bash
# Run all 300 tasks (task1-task10, 30 instances each)
uv run medagentbench-run config/scenario.toml --show-logs
```

### With FHIR Data (Recommended)

```bash
# Start FHIR server
./scripts/start_fhir.sh

# Start MCP server (provides FHIR tools)
./scripts/start_mcp.sh

# Run evaluation with real medical data
./benchmark.sh --all
```

## Project Structure

```
src/                    # Green Agent (Evaluator)
├─ server.py           # A2A server and agent card
├─ agent.py            # Evaluation orchestration
├─ nodes.py            # PocketFlow workflow nodes
├─ flow.py             # Workflow construction
└─ tasks/              # MedAgentBench tasks
    └─ subtask1/       # 10 clinical reasoning tasks

purple_agent/          # Purple Agent (Example participant)
├─ src/
│  ├─ server.py        # A2A server
│  └─ agent.py         # Clinical reasoning logic
└─ Dockerfile

mcp_skills/           # MCP Server (FHIR tools)
└─ fhir/              # FHIR API integration

tests/                # Test suite
config/               # Scenario configurations
```

## Tasks

PharmAgent evaluates agents on 10 clinical reasoning tasks from Stanford MedAgentBench:

| Task | Type | Description |
|------|------|-------------|
| task1 | read_query | Find patient's current problem list |
| task2 | calculate_age | Calculate patient's age from DOB |
| task3 | record_vitals | Record blood pressure vital sign |
| task4 | read_lab | Get latest magnesium level |
| task5 | check_and_order_magnesium | Check Mg + order IV replacement if low |
| task6 | calculate_average | Average glucose over 24h |
| task7 | read_lab | Get latest glucose level |
| task8 | order_consult | Order orthopedic consult with SBAR note |
| task9 | check_and_order_potassium | Check K + order replacement + recheck |
| task10 | check_and_order_a1c | Check A1C + order if >1 year old |

## Testing

### Unit Tests
```bash
pytest tests/ -v
```

### Integration Tests
```bash
# Start mock purple agent
python tests/mock_purple_agent.py &

# Start green agent
python src/server.py &

# Run integration test
python examples/full_test.py
```

## Configuration

Copy `sample.env` to `.env` and set your `GOOGLE_API_KEY`.

| Variable | Description | Default |
|----------|-------------|---------|
| `GOOGLE_API_KEY` | Google Gemini API key (required) | - |
| `GREEN_AGENT_PORT` | Server port | `9009` |
| `TASK_TIMEOUT` | Task timeout (seconds) | `300` |

## Docker

Build and run with Docker:

```bash
# Build images
docker build -t pharmagent-green .
docker build -f purple_agent/Dockerfile -t pharmagent-purple .

# Run containers
docker run -p 9009:9009 --env-file .env pharmagent-green
docker run -p 9019:9019 --env-file .env pharmagent-purple
```

## Citations

```bibtex
@article{jiang2025medagentbench,
  title={MedAgentBench: a virtual EHR environment to benchmark medical LLM agents},
  author={Jiang, Yixing and Black, Kameron C and Geng, Gloria and Park, Danny and Zou, James and Ng, Andrew Y and Chen, Jonathan H},
  journal={Nejm Ai},
  volume={2},
  number={9},
  pages={AIdbp2500144},
  year={2025},
  publisher={Massachusetts Medical Society}
}

@article{henry2026drug,
  title={Drug or Pokemon? An analysis of the ability of large language models to discern fabricated medications},
  author={Henry, Kelli and Smith, Brooke and Zhao, Xingmeng and Blotske, Kaitlin and Murray, Brian and Gao, Yanjun and Smith, Susan E and Barreto, Erin and Bauer, Seth and Sohn, Sunghwan and others},
  journal={medRxiv},
  pages={2026--01},
  year={2026},
  publisher={Cold Spring Harbor Laboratory Press}
}
```

## License

MIT License - see [LICENSE](LICENSE) file for details.