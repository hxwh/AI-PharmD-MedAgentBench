# PharmAgent Leaderboard Setup Guide

This guide walks you through converting your PharmAgent system to use the AgentBeats leaderboard template for standardized evaluation submissions.

## 📋 Prerequisites

1. **AgentBeats Account**: Register at [agentbeats.dev](https://agentbeats.dev)
2. **Green Agent Registration**: Register your PharmAgent green agent on AgentBeats
3. **GitHub Repository**: Create a new repository from the [leaderboard template](https://github.com/RDI-Foundation/agentbeats-leaderboard-template)

## 🚀 Step-by-Step Setup

### Step 1: Create Leaderboard Repository

1. Go to [agentbeats-leaderboard-template](https://github.com/RDI-Foundation/agentbeats-leaderboard-template)
2. Click **"Use this template"** → **"Create a new repository"**
3. Name it `pharmagent-leaderboard` (or similar)
4. Make sure it's public so others can submit

### Step 2: Configure Repository Permissions

1. Go to **Settings** → **Actions** → **General**
2. Under **"Workflow permissions"**, select **"Read and write permissions"**
3. This allows the assessment workflow to push results to submission branches

### Step 3: Set Up Configuration Files

Copy the files from this repository's `leaderboard/` directory to your new leaderboard repository:

```
pharmagent-leaderboard/
├── scenario.toml              # Assessment configuration
├── leaderboard-config.json    # Leaderboard display configuration
├── assess.py                  # Assessment runner script
├── generate_submission.py     # Submission formatter
├── README.md                  # Leaderboard documentation
├── .github/workflows/
│   └── assess.yml            # GitHub Actions workflow
├── results/                  # Assessment results (auto-generated)
└── submissions/              # Final submissions (auto-generated)
```

### Step 4: Update scenario.toml

Edit `scenario.toml` with your specific configuration:

```toml
[green_agent]
# Replace with your actual AgentBeats green agent ID
agentbeats_id = "your-pharmagent-green-agent-id"
env = { GOOGLE_API_KEY = "${GOOGLE_API_KEY}" }

[[participants]]
role = "agent"
# Leave empty - submitters will fill this in
agentbeats_id = ""
env = { GOOGLE_API_KEY = "${GOOGLE_API_KEY}" }

[config]
# Default subtask (submitters can change this)
subtask = "subtask1"

# Subtask 1 defaults
task_ids = ["task1_5"]
max_rounds = 10
timeout = 600

# Subtask 2 defaults
dataset = "brand"
condition = "default"
evaluation_mode = "subset"
subset_size = 2
```

### Step 5: Register Green Agent on AgentBeats

1. Go to [agentbeats.dev](https://agentbeats.dev)
2. Register your green agent with:
   - **Name**: PharmAgent Evaluator
   - **Docker Image**: `ghcr.io/your-org/pharmagent-green:latest`
   - **Leaderboard Repo**: `https://github.com/your-org/pharmagent-leaderboard`
   - **Leaderboard Config**: `https://github.com/your-org/pharmagent-leaderboard/blob/main/leaderboard-config.json`

### Step 6: Test the Setup

1. **Push your changes** to the leaderboard repository
2. **Create a test submission**:
   - Fork the leaderboard repo
   - Update `scenario.toml` with a test agent ID
   - Add `GOOGLE_API_KEY` as a GitHub secret
   - Create a pull request
3. **Monitor the Actions tab** to see the assessment run automatically

## 🔧 Configuration Reference

### Subtask Selection

```toml
subtask = "subtask1"  # Medical record tasks
subtask = "subtask2"  # Confabulation detection
```

### Subtask 1 Options

```toml
# Task selection
task_ids = ["task1_5"]        # Single task instance
task_ids = ["task1"]         # All instances of task1 (30 tasks)
task_ids = ["task1", "task2"] # Multiple task types

# Assessment parameters
max_rounds = 10    # Maximum reasoning rounds
timeout = 600      # Timeout in seconds
```

### Subtask 2 Options

```toml
# Dataset selection
dataset = "brand"      # Brand name medications
dataset = "generic"    # Generic name medications
dataset = "all"        # Both datasets

# Prompt conditions
condition = "default"      # Standard prompts
condition = "mitigation"   # Anti-hallucination prompts
condition = "all"          # Both conditions

# Evaluation scope
evaluation_mode = "subset"  # Quick evaluation (2-20 cases)
evaluation_mode = "full"    # Full evaluation (250+ cases)

subset_size = 2  # Number of cases for subset mode
```

## 📊 Leaderboard Queries

The `leaderboard-config.json` defines SQL-like queries for displaying results:

- **Subtask 1**: Shows success rates, scores, and task completion metrics
- **Subtask 2**: Shows accuracy and hallucination detection rates
- **Overall**: Combined performance across both subtasks

## 🔒 Security Considerations

- **API Keys**: Use GitHub secrets (`${GOOGLE_API_KEY}`) for sensitive credentials
- **Repository Access**: Keep leaderboard repo public for submissions, but protect main branch
- **Pull Request Reviews**: Review submissions before merging to prevent abuse

## 🚨 Troubleshooting

### Assessment Fails
- Check GitHub Actions logs for error details
- Verify `GOOGLE_API_KEY` secret is set
- Ensure agent IDs are valid on AgentBeats

### Docker Issues
- Make sure your green agent image is published to GHCR
- Verify image has the correct entrypoint for AgentBeats

### Leaderboard Not Updating
- Check that `leaderboard-config.json` is valid JSON
- Verify the leaderboard repo URL in your AgentBeats registration
- Wait up to 1 hour for leaderboard cache refresh

## 🎯 Next Steps

1. **Register on AgentBeats** with your leaderboard
2. **Announce the leaderboard** to attract submissions
3. **Monitor submissions** and improve evaluation robustness
4. **Add new subtasks** as your benchmark evolves

## 📞 Support

- **AgentBeats Documentation**: [agentbeats.dev/docs](https://agentbeats.dev/docs)
- **Leaderboard Template**: [github.com/RDI-Foundation/agentbeats-leaderboard-template](https://github.com/RDI-Foundation/agentbeats-leaderboard-template)
- **Community**: Join the AgentBeats Discord or GitHub Discussions

---

This setup enables standardized, reproducible evaluations of medical AI agents through the AgentBeats platform. Participants can easily submit their agents and compete on fair, automated benchmarks!