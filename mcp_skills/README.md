# PharmAgent Skill MCP Server

MCP (Model Context Protocol) server providing FHIR tools for clinical workflows with support for two agent types.

## Agent Types

### Green Agent (Evaluator Mode)
- Has access to FHIR tools AND evaluation tools
- Can query groundtruth answers from `refsol_eval.py` functions
- Use for validating agent responses against expected answers
- Tools: All FHIR tools + `get_task*_groundtruth`, `validate_task_result`

### Purple Agent (Clinical Reasoning Mode)
- Has access to FHIR tools ONLY
- Must rely entirely on clinical reasoning and FHIR data
- No access to groundtruth or evaluation functions
- Tools: FHIR read/write tools, utilities

## Directory Structure

```
mcp_skills/
├── __init__.py           # Package entry
├── Dockerfile            # Container build
├── pyproject.toml        # Dependencies
├── README.md             # This file
├── fastmcp/
│   ├── __init__.py
│   ├── app.py            # FastMCP instance + AgentType
│   └── server.py         # CLI entrypoint
└── fhir/
    ├── __init__.py
    ├── client.py         # FHIR HTTP client
    ├── models.py         # Pydantic models
    ├── resources.py      # MCP resources
    ├── tools.py          # FHIR tools (both agents)
    └── eval_tools.py     # Evaluation tools (Green only)
```

## Usage

### Running the Server

```bash
# Purple agent (default) - clinical reasoning only
python -m mcp_skills.fastmcp.server

# Green agent - with evaluation/groundtruth tools
python -m mcp_skills.fastmcp.server --agent-type green

# With custom FHIR server
MCP_FHIR_API_BASE=http://fhir.example.com/fhir/ python -m mcp_skills.fastmcp.server

# stdio transport for MCP Inspector
python -m mcp_skills.fastmcp.server --stdio

# Custom port
python -m mcp_skills.fastmcp.server --port 8003
```

### Docker

```bash
# Build for Purple agent
docker build -t pharmagent-mcp:purple --build-arg AGENT_TYPE=purple .

# Build for Green agent
docker build -t pharmagent-mcp:green --build-arg AGENT_TYPE=green .

# Run
docker run -p 8002:8002 -e MCP_FHIR_API_BASE=http://host.docker.internal:8080/fhir/ pharmagent-mcp:purple
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MCP_FHIR_API_BASE` | `http://localhost:8080/fhir/` | FHIR server base URL |
| `AGENT_TYPE` | `purple` | Agent type (`green` or `purple`) |

## Available Tools

### All Agents (FHIR Tools)

**Patient Search:**
- `search_patients` - Find patients by demographics

**Clinical Read:**
- `list_patient_problems` - Get patient conditions
- `list_lab_observations` - Get lab results
- `get_latest_lab_value` - Get most recent lab value
- `list_vital_signs` - Get vital signs
- `list_medication_requests` - Get medication orders
- `list_patient_procedures` - Get procedures
- `get_patient_conditions` - Get simplified condition names

**Clinical Write:**
- `record_vital_observation` - Record vital signs
- `create_medication_request` - Create medication order
- `create_service_request` - Create lab/imaging/consult order

**Utilities:**
- `calculate_age` - Calculate patient age
- `check_date_within_period` - Check date recency
- `evaluate_potassium_level` - Evaluate K levels
- `evaluate_magnesium_level` - Evaluate MG levels
- `calculate_potassium_dose` - Calculate KCl dose
- `get_latest_observation_value` - Extract from FHIR bundle
- `calculate_average_observation` - Calculate average from bundle
- `extract_simplified_conditions` - Extract condition names

### Green Agent Only (Evaluation Tools)

- `get_task1_groundtruth` - Problem list groundtruth
- `get_task2_groundtruth` - Age calculation groundtruth
- `get_task4_groundtruth` - Latest MG in 24h groundtruth
- `get_task5_groundtruth` - MG replacement groundtruth
- `get_task6_groundtruth` - Average GLU in 24h groundtruth
- `get_task7_groundtruth` - Latest GLU groundtruth
- `get_task9_groundtruth` - K replacement groundtruth
- `get_task10_groundtruth` - A1C check groundtruth
- `validate_task_result` - Validate agent result against groundtruth

## Lab Codes

| Code | Description |
|------|-------------|
| `GLU` | Blood glucose |
| `K` | Potassium |
| `MG` | Magnesium |
| `A1C` / `HBA1C` | HbA1c (glycated hemoglobin) |

## Medication NDC Codes

| NDC | Medication |
|-----|------------|
| `0338-1715-40` | Magnesium sulfate (IV) |
| `40032-917-01` | Potassium chloride (oral) |
