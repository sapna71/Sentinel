from typing import TypedDict, Optional, Annotated, List
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver
from app.services.provider_service import ProviderService, ProviderResponse
from app.core.config import settings
from app.core.chaos import chaos_state
from app.database.session import AsyncSessionLocal
from app.database.models import RequestLog, Provider
from app.tools.mcp_tools import get_all_tools
from app.resilience.circuit_breaker import CircuitBreaker

class AgentState(TypedDict):    
    prompt: str
    response: Optional[str]
    error: Optional[str]
    provider_used: Optional[str]
    attempts: int
    is_fallback: bool
    tool_calls: List[str]
    tool_outputs: List[str]

class SentinelGraph:
    def __init__(self):
        self.provider_service = ProviderService()
        self.tools = get_all_tools()
        # Circuit breakers for each tool
        self.circuit_breakers = {
            name: CircuitBreaker() for name in self.tools.keys()
        }
        # Initialize SqliteSaver for state recovery
        # SqliteSaver.from_conn_string returns a context manager in newer versions
        self.checkpointer = SqliteSaver.from_conn_string("checkpoints.sqlite")
        self.workflow = self._build_graph()

    def _build_graph(self):
        builder = StateGraph(AgentState)

        # Define Nodes
        builder.add_node("call_primary", self.call_primary)
        builder.add_node("call_fallback", self.call_fallback)
        builder.add_node("call_emergency", self.call_emergency)
        builder.add_node("execute_tools", self.execute_tools)
        builder.add_node("log_result", self.log_result)

        # Define Edges
        builder.set_entry_point("call_primary")
        
        # Conditional edge: if primary fails, go to fallback, else check for tools
        builder.add_conditional_edges(
            "call_primary",
            self.should_fallback,
            {
                "fallback": "call_fallback",
                "success": "execute_tools"
            }
        )
        
        builder.add_conditional_edges(
            "call_fallback",
            self.should_emergency,
            {
                "emergency": "call_emergency",
                "success": "execute_tools"
            }
        )

        builder.add_conditional_edges(
            "call_emergency",
            self.check_for_tools_logic,
            {
                "tools": "execute_tools",
                "success": "log_result"
            }
        )

        builder.add_edge("execute_tools", "log_result")
        builder.add_edge("log_result", END)

        # For the demo, we use a simple checkpointer if the complex one fails
        try:
            return builder.compile(checkpointer=self.checkpointer)
        except Exception:
            print("⚠️ Checkpointer failed to compile, falling back to no-checkpoint mode.")
            return builder.compile()

    async def call_primary(self, state: AgentState):
        print(f"🚀 Attempting primary model: {settings.PRIMARY_MODEL}")
        res = await self.provider_service.call_model(settings.PRIMARY_MODEL, state["prompt"])
        
        if res.success:
            # Simple tool detection for demo: if prompt contains 'search', 'calculate', or 'read'
            tool_calls = []
            if "search" in state["prompt"].lower(): tool_calls.append("web_search")
            if "calculate" in state["prompt"].lower(): tool_calls.append("calculator")
            if "read" in state["prompt"].lower(): tool_calls.append("read_file")

            return {
                "response": res.content,
                "provider_used": settings.PRIMARY_MODEL,
                "attempts": 1,
                "is_fallback": False,
                "tool_calls": tool_calls
            }
        return {
            "error": res.error,
            "attempts": 1,
            "provider_used": settings.PRIMARY_MODEL
        }

    async def call_fallback(self, state: AgentState):
        print(f"⚠️ Primary failed. Attempting fallback: {settings.FALLBACK_MODEL}")
        res = await self.provider_service.call_model(settings.FALLBACK_MODEL, state["prompt"])
        
        if res.success:
            tool_calls = []
            if "search" in state["prompt"].lower(): tool_calls.append("web_search")
            if "calculate" in state["prompt"].lower(): tool_calls.append("calculator")
            if "read" in state["prompt"].lower(): tool_calls.append("read_file")

            return {
                "response": res.content,
                "provider_used": settings.FALLBACK_MODEL,
                "attempts": 2,
                "is_fallback": True,
                "tool_calls": tool_calls,
            }
        return {
            "error": res.error,
            "attempts": 2,
            "is_fallback": True,
            "provider_used": settings.FALLBACK_MODEL
        }

    async def call_emergency(self, state: AgentState):
        print(f"🚨 Secondary failover reached. Attempting emergency model: {settings.EMERGENCY_MODEL}")
        res = await self.provider_service.call_model(settings.EMERGENCY_MODEL, state["prompt"])

        if res.success:
            return {
                "response": res.content,
                "provider_used": settings.EMERGENCY_MODEL,
                "attempts": 3,
                "is_fallback": True,
                "tool_calls": state.get("tool_calls", []),
            }

        return {
            "error": res.error,
            "attempts": 3,
            "is_fallback": True,
            "provider_used": settings.EMERGENCY_MODEL,
        }

    def should_emergency(self, state: AgentState):
        if state.get("error") and not state.get("response"):
            return "emergency"
        return "success"

    async def execute_tools(self, state: AgentState):
        print(f"Executing tools: {state.get('tool_calls')}")
        outputs = []
        for tool_name in state.get("tool_calls", []):
            # Check circuit breaker
            cb = self.circuit_breakers.get(tool_name)
            if cb and not await cb.allow_request():
                outputs.append(f"[{tool_name}]: 🔴 Circuit Open. Tool is currently disabled due to repeated failures.")
                continue

            if chaos_state.mcp_crash:
                await cb.record_failure() if cb else None
                outputs.append(f"[{tool_name}]: ❌ Simulated MCP outage. The tool cannot execute.")
                continue

            tool = self.tools.get(tool_name)
            if tool:
                try:
                    # Simple arg extraction for demo
                    args = {"query": state["prompt"], "expression": state["prompt"], "path": state["prompt"]}
                    result = await tool.execute(args)
                    await cb.record_success() if cb else None
                    outputs.append(f"[{tool_name}]: {result}")
                except Exception as e:
                    await cb.record_failure() if cb else None
                    outputs.append(f"[{tool_name}]: ❌ Execution failed: {str(e)}")
        
        return {
            "tool_outputs": outputs,
            "response": f"{state.get('response')}\n\nTool Results:\n" + "\n".join(outputs) if outputs else state.get("response")
        }

    async def log_result(self, state: AgentState):
        print("Logging request result to database...")
        async with AsyncSessionLocal() as session:
            # Find provider ID
            from sqlalchemy import select
            result = await session.execute(select(Provider).where(Provider.model_name == state["provider_used"]))
            provider = result.scalar_one_or_none()
            
            log = RequestLog(
                prompt=state["prompt"],
                response=state["response"],
                provider_id=provider.id if provider else None,
                was_fallback=state["is_fallback"]
            )
            session.add(log)
            await session.commit()
        return state

    def should_fallback(self, state: AgentState):
        if state.get("error") and not state.get("response"):
            return "fallback"
        return "success"

    def check_for_tools_logic(self, state: AgentState):
        if state.get("tool_calls") and len(state["tool_calls"]) > 0:
            return "tools"
        return "success"

    async def run(self, prompt: str):
        initial_state = {
            "prompt": prompt,
            "response": None,
            "error": None,
            "provider_used": None,
            "attempts": 0,
            "is_fallback": False
        }
        final_state = await self.workflow.ainvoke(initial_state)
        return final_state
