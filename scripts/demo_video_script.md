# PharmAgent Demo Video Script (3 Minutes)

**Target Audience:** AgentBeats Judges & Developers
**Goal:** Demonstrate PharmAgent as a robust, standardized Green Agent for medical AI evaluation.

---

## 0:00 - 0:30 | Introduction: The Challenge
**(Visual: Split screen. Left: Complex Electronic Health Record (EHR). Right: AI agent icon looking confused. Fade to PharmAgent Logo.)**

**Speaker:**
"As Large Language Models enter healthcare, accuracy isn't enough—we need safety and standardized evaluation.

Introducing **PharmAgent**—a complete, AgentBeats-compatible benchmarking platform.

We don't just ask multiple-choice questions. We immerse agents in a realistic virtual hospital environment, testing their ability to query records, reason about clinical data, and execute safe actions."

---

## 0:30 - 1:00 | Live Demo: One-Click Evaluation
**(Visual: Terminal window. User types `./benchmark.sh`. Fast-forward showing colorful log outputs of services starting.)**

**Speaker:**
"Simplicity is key. We've wrapped the entire complex infrastructure—FHIR servers, MCP tools, and agent orchestration—into a single script.

**(Visual: User types `./benchmark.sh task1_1`. Show the Green Agent evaluating the Purple Agent in real-time.)**

With one command, `benchmark.sh`, you spin up the entire environment.
Here, we're running a specific clinical task. The Green Agent (the evaluator) sends the task to the Purple Agent (your model) via the **Agent-to-Agent (A2A)** protocol.

**(Visual: Show "✅ Benchmarking completed successfully!" in green text.)**

It's Dockerized, reproducible, and ready for AgentBeats right out of the box."

---

## 1:00 - 1:45 | Subtask 1: Clinical Reasoning (MedAgentBench)
**(Visual: Animated diagram of the workflow. Agent -> MCP Tool -> FHIR Database. Show a specific task: "Task 5: Check Magnesium".)**

**Speaker:**
"Let's look at **Subtask 1**, based on MedAgentBench.
The agent receives a clinical goal, like 'Check magnesium levels and order replacement if needed.'

It's not a static quiz. The agent must:
1.  **Use Tools**: Call `read_lab` via MCP to query the FHIR database.
2.  **Reason**: Interpret that 1.2 mg/dL is low.
3.  **Act**: Place a valid order for Magnesium Sulfate.

Our Green Agent validates every step against dynamic ground truth, ensuring the agent isn't just guessing, but *doing*."

---

## 1:45 - 2:25 | Subtask 2: Safety & Adversarial Testing
**(Visual: Terminal running `./benchmark.sh --subtask2`. Show a list of meds: "Lisinopril... Metformin... Pikachu". Highlight "Pikachu" in red.)**

**Speaker:**
"But can your agent handle adversarial inputs?
**Subtask 2** is our 'Drug or Pokémon' safety benchmark.

**(Visual: Show "CONFABULATION DETECTED" warning in the logs.)**

We inject fabricated medication names into the patient's record. A naive agent might try to prescribe 'Pikachu 50mg'.
PharmAgent catches this immediately. We test whether your agent can distinguish real pharmacology from plausible-sounding hallucinations—a critical safety check for any medical AI."

---

## 2:25 - 3:00 | Conclusion & Impact
**(Visual: Summary dashboard showing scores for "Clinical Accuracy," "Safety," and "Efficiency." GitHub URL: github.com/your-repo/PharmAgent)**

**Speaker:**
"PharmAgent provides a comprehensive failure taxonomy, distinguishing between retrieval errors, reasoning flaws, and safety violations.

With open-source code, full Docker support, and seamless AgentBeats integration, we're setting the standard for reproducible medical agent evaluation.

Run the benchmark yourself today."

**(Visual: Fade out to PharmAgent Logo and GitHub URL.)**
