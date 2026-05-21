# 🛡️ SENTINEL - Self-Healing AI Orchestration Platform

SENTINEL is a resilience-focused AI agent framework designed for the TrueFoundry Hackathon. It implements a tiered fallback mechanism and tool-augmented generation to ensure continuity of service even when primary LLM providers fail.

## 🚀 Current Status: Sprinting Phase (Day 2/10)
The project is currently in the "Sprinting Phase," focusing on a perfectly working vertical slice.

**Overall Progress: ~30% of total roadmap completed.**

### ✅ Implemented in Detail
- **Tiered Fallback Engine**: 
    - Implemented a `StateGraph` in LangGraph that manages the transition between LLM providers.
    - Logic: `call_primary` $\rightarrow$ `should_fallback` (Conditional Edge) $\rightarrow$ `call_fallback`.
    - Verified via mock testing: successfully switches to backup model when primary returns an error.
- **MCP Tool Suite**: 
    - Created a modular tool architecture (`MCPTool` base class).
    - `web_search`: Simulated real-time information retrieval.
    - `read_file`: Direct workspace filesystem access.
    - `calculator`: Safe mathematical expression evaluation.
- **Tool-Augmented Graph**: 
    - Integrated tool detection logic into the orchestrator.
    - Added an `execute_tools` node that processes tool calls and appends results to the final LLM response.
- **Persistence Layer**: 
    - Configured an asynchronous SQLite database using SQLAlchemy.
    - Implemented `RequestLog` and `Provider` models to track every request, the model used, and whether a fallback occurred.
- **Environment & Config**: 
    - Pydantic-based settings management for API keys, model names, and timeouts.
    - Virtual environment setup with all core dependencies (`langgraph`, `fastapi`, `aiosqlite`).

### 🛠️ Technical Architecture
- **Backend**: FastAPI
- **Orchestration**: LangGraph (StateGraph)
- **Database**: SQLAlchemy (Async)
- **LLM Integration**: ProviderService (Ollama/Gateway compatible)

## 🗺️ Remaining Roadmap (The Final Push)

### 🟠 Phase 3: The Bridge & The Face (High Priority)
- [ ] **FastAPI `/chat` Endpoint**: Implement streaming responses (SSE/WebSockets) to move from terminal to web.
- [ ] **Next.js Frontend**: Build a clean chat interface using Tailwind and shadcn/ui.
- [ ] **Chaos Dashboard**: Create an admin panel to manually trigger LLM failures and monitor health (🟢/🟡/🔴).

### 🟡 Phase 2: Resilience Hardening
- [ ] **Circuit Breakers**: Implement logic to "open the circuit" for tools that fail repeatedly.
- [ ] **State Recovery**: Integrate `SqliteSaver` for LangGraph checkpoints to allow resuming tasks after crashes.

### 🔴 Phase 4: Polish & Pitch
- [ ] **Chaos Scenarios**: Stress test the fail-over UX.
- [ ] **Persona Refinement**: Improve "fail-over" messaging to be more professional and transparent.

## 🛠️ Quick Start for Handover

### Installation
```bash
pip install -r requirements.txt
```

### Running the App
```bash
python app/main.py
```

### Testing the Logic
You can currently test the orchestrator by invoking the `SentinelGraph` in a python shell:
```python
from app.graph.orchestrator import SentinelGraph
graph = SentinelGraph()
result = await graph.workflow.ainvoke({"prompt": "Search for the project status"})
print(result["response"])
```