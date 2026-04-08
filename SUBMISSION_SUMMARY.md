# 🏆 Hackathon Submission: OpenEnv CS-Ops

**Project Title**: OpenEnv: Customer Support Operations (CS-Ops)
**Track**: OpenEnv Assessment
**Category**: Production-grade AI Evaluation

---

## 📖 Project Overview
We have developed a high-fidelity **OpenEnv evaluation environment** designed to test the operational limits of AI agents in complex, multi-tool customer support scenarios. Unlike static benchmarks, our environment features a dynamic, stateful world where agents must navigate shifting customer sentiments, resolve billing discrepancies, and detect fraud using a suite of simulated enterprise tools.

## 🚀 Technical Innovations

### 1. Adaptive Curriculum Learning (ACL)
The environment implements an **automatic progression system** that shifts difficulty (`EASY` → `MEDIUM` → `HARD` → `EXPERT`) based on a rolling-window average of the agent's performance. This ensures that the agent is always being tested at the edge of its capabilities, preventing "benchmark saturation."

### 2. Multi-Dimensional Dense Rewards
Our reward engine evaluates every step across **5 distinct dimensions**:
- **Action Relevance**: Selecting the correct action type for the current step.
- **Data Correctness**: Accuracy of tool inputs (e.g., correct Order IDs, Refund amounts).
- **Tone Handling**: Matching the agent's response to the customer's sentiment (Empathy vs. Clarity).
- **Tool Protocol**: Following correct SOPs for database lookups and payment systems.
- **Goal Alignment**: Advancing the episode toward a verified resolution.

### 3. Premium Glassmorphic Visualizer
To bridge the gap between "Black-box AI" and human-readable evaluation, we built a **real-time dashboard** using modern glassmorphism design. This visualizer provides:
- **Inference Logic Stream**: A live feed of the agent's structured actions and step-by-step scores.
- **Customer Observation Matrix**: High-fidelity tracking of hidden states (Sentiment, Priority, Tier).
- **Environment Terminal**: Transparent logs of all tool interactions and database queries.

## 🛠️ Built With
- **Core**: Python 3.12+, OpenEnv Specification
- **Engine**: FastAPI, Pydantic v2
- **Agent**: OpenAI GPT-4o-mini, LangChain-inspired structured parsing
- **UI**: Vanilla JS, Modern CSS (Glassmorphism), Mermaid.js

## 🏁 Impact & Evaluation
Our environment provides a **deterministic grading system** that prevents "hallucination-based success." An agent cannot simply claim it resolved a ticket; it must perform the correct tool actions and receive a verified "Resolution" state from the internal environment logic.

---

### **How to Evaluate Our Submission**
1.  Run `bash setup.sh` to install the environment.
2.  Set your `OPENAI_API_KEY` in Hugging Face Spaces environment variable settings.
3.  Run `bash run_demo.sh` to see the AI agent and Visualizer in synchronized action.
