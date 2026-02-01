# PharmAgent Leaderboard Setup Guide

This guide walks you through setting up the PharmAgent leaderboard using the AgentBeats template for standardized, reproducible evaluations.

Based on: [agentbeats-leaderboard-template](https://github.com/RDI-Foundation/agentbeats-leaderboard-template)

## Prerequisites

1. **AgentBeats Account**: Register at [agentbeats.dev](https://agentbeats.dev)
2. **Green Agent Registration**: Register your PharmAgent green agent on AgentBeats
3. **Docker Image**: Publish your green agent image (e.g., to Docker Hub or GHCR)

## Repository Structure

Since the leaderboard is a subdirectory of `AI-PharmD-MedAgentBench`, the structure is:

```
AI-PharmD-MedAgentBench/
├── .github/workflows/
│   └── run-scenario.yml       # Assessment workflow (MUST be at repo root)
├── leaderboard/
│   ├── scenario.toml          # Assessment configuration
│   ├── generate_compose.py    # Docker Compose generator
│   ├── record_provenance.py   # Provenance recorder
│   ├── results_format_adapter.py # Transforms results for leaderboard compatibility
│   ├── README.md              # Leaderboard documentation
│   ├── results/               # Assessment results (leaderboard format)
│   └── submissions/           # Submission configs and provenance
└── ... (other project files)
```

**Important**: GitHub Actions workflows must be in the repository root's `.github/workflows/` directory, not in subdirectories.

## Results Format Transformation

The workflow automatically transforms PharmAgent's detailed evaluation results into AgentBeats-compatible format:

1. **AgentBeats Client** produces `output/results.json` with A2A protocol artifacts
2. **Results Format Adapter** transforms this into leaderboard-compatible metrics
3. **Final results.json** contains only the scoring metrics defined in `leaderboard-config.json`

This ensures compatibility between PharmAgent's rich evaluation data and AgentBeats' leaderboard display requirements.

## Step-by-Step Setup

### Step 1: Create Leaderboard Repository

Option A: Use this `leaderboard/` directory as your repository root.

Option B: Create from template:
1. Go to [agentbeats-leaderboard-template](https://github.com/RDI-Foundation/agentbeats-leaderboard-template)
2. Click "Use this template" to create a new repository
3. Copy PharmAgent-specific files from this directory

### Step 2: Configure Repository Permissions

1. Go to **Settings > Actions > General**
2. Under "Workflow permissions", select **"Read and write permissions"**
3. This enables the workflow to push results to submission branches

### Step 3: Register Green Agent on AgentBeats

1. Go to [agentbeats.dev](https://agentbeats.dev)
2. Register your green agent:
   - **Name**: PharmAgent Evaluator
   - **Docker Image**: `hxwh/ai-pharmd-medagentbench-green:latest`
   - **Description**: Medical AI agent benchmark for clinical reasoning
3. Note the `agentbeats_id` for your green agent

### Step 4: Update scenario.toml

```toml
[green_agent]
# Add your AgentBeats green agent ID (or use image for local testing)
agentbeats_id = "your-green-agent-id"
# OR for local testing only:
# image = "hxwh/ai-pharmd-medagentbench-green:latest"
env = { GOOGLE_API_KEY = "${GOOGLE_API_KEY}" }

[[participants]]
# Leave empty - submitters fill in their purple agent
agentbeats_id = ""
name = "medical_agent"
image = ""
env = { GOOGLE_API_KEY = "${GOOGLE_API_KEY}" }

[config]
subtask = "subtask1"
task_ids = ["task1_5"]
max_rounds = 10
timeout = 600
```

### Step 5: Test Locally

```bash
# Install dependencies
pip install tomli tomli-w pyyaml requests

# For local testing, set image fields instead of agentbeats_id
# Then generate docker-compose.yml
python generate_compose.py --scenario scenario.toml

# Run the assessment
docker compose up --exit-code-from agentbeats-client

# Check results in output/results.json
```

### Step 6: Push and Test Workflow

1. Push changes to your repository
2. Fork the repository from another account
3. Update `scenario.toml` with a test participant agent
4. Add `GOOGLE_API_KEY` as a GitHub secret in your fork
5. Push changes - workflow triggers automatically on `scenario.toml` changes
6. Check Actions tab for the submission branch link

## Configuration Reference

### Subtask 1: Medical Record Tasks

```toml
[config]
subtask = "subtask1"
task_ids = ["task1_5"]         # Single task instance (fast)
task_ids = ["task1"]           # All task1 instances
task_ids = ["task1", "task2"]  # Multiple task types
max_rounds = 10                # Maximum reasoning rounds
timeout = 600                  # Timeout in seconds
```

### Subtask 2: Confabulation Detection

```toml
[config]
subtask = "subtask2"
dataset = "brand"              # Options: brand, generic, all
condition = "default"          # Options: default, mitigation
evaluation_mode = "subset"     # Options: subset, full
subset_size = 2                # Number of cases for subset mode
```

## How Assessment Works

1. **Trigger**: Workflow runs on `scenario.toml` changes (forks or non-main branches only)
2. **Generate**: `generate_compose.py` creates `docker-compose.yml` and `a2a-scenario.toml`
3. **Pull**: Docker images pulled for green agent and participants
4. **Run**: `agentbeats-client` orchestrates the A2A assessment
5. **Record**: `record_provenance.py` captures image digests and metadata
6. **Submit**: Results pushed to submission branch with PR link

## Security

- Use `${VARIABLE_NAME}` syntax for secrets in `scenario.toml`
- Add secrets as GitHub Secrets in fork repositories
- Never commit API keys directly to the repository
- When creating PRs, uncheck "Allow edits and access to secrets by maintainers"

## Troubleshooting

### Workflow Not Running
- Check that you're on a fork or non-main branch
- Verify `scenario.toml` was modified in the push

### Image Pull Fails
- Ensure images are publicly accessible
- For private GHCR images, add `GHCR_TOKEN` secret

### Assessment Timeout
- Increase `timeout` in `[config]` section
- Use smaller `task_ids` or `subset_size` for faster tests

### Missing Results
- Check workflow logs for errors
- Verify `GOOGLE_API_KEY` secret is set correctly

## Links

- [AgentBeats](https://agentbeats.dev) - Leaderboard platform
- [AgentBeats Template](https://github.com/RDI-Foundation/agentbeats-leaderboard-template) - Base template
- [Debate Leaderboard](https://github.com/RDI-Foundation/agentbeats-debate-leaderboard) - Example implementation