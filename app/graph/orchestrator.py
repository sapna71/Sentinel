from typing import TypedDict, Optional, Annotated
from langgraph.graph import StateGraph, END
from app.services.provider_service import ProviderService, ProviderResponse
from app.core.config import settings
from app.database.session import AsyncSessionLocal
from app.database.models import RequestLog, Provider

class AgentState(TypedDict):
    prompt: str
    response: Optional[str]
    error: Optional[str]
    provider_used: Optional[str]
    attempts: int
    is_fallback: bool

class SentinelGraph:
    def __init__(self):
        self.provider_service = ProviderService()
        self.workflow = self._build_graph()

    def _build_graph(self):
        builder = StateGraph(AgentState)

        # Define Nodes
        builder.add_node("call_primary", self.call_primary)
        builder.add_node("call_fallback", self.call_fallback)
        builder.add_node("log_result", self.log_result)

        # Define Edges
        builder.set_entry_point("call_primary")
        
        # Conditional edge: if primary fails, go to fallback, else go to log
        builder.add_conditional_edges(
            "call_primary",
            self.should_fallback,
            {
                "fallback": "call_fallback",
                "success": "log_result"
            }
        )
        
        builder.add_edge("call_fallback", "log_result")
        builder.add_edge("log_result", END)

        return builder.compile()

    async def call_primary(self, state: AgentState):
        print(f"🚀 Attempting primary model: {settings.PRIMARY_MODEL}")
        res = await self.provider_service.call_model(settings.PRIMARY_MODEL, state["prompt"])
        
        if res.success:
            return {
                "response": res.content,
                "provider_used": settings.PRIMARY_MODEL,
                "attempts": 1,
                "is_fallback": False
            }
        return {
            "error": res.error,
            "attempts": 1
        }

    async def call_fallback(self, state: AgentState):
        print(f"⚠️ Primary failed. Attempting fallback: {settings.FALLBACK_MODEL}")
        res = await self.provider_service.call_model(settings.FALLBACK_MODEL, state["prompt"])
        
        if res.success:
            return {
                "response": res.content,
                "provider_used": settings.FALLBACK_MODEL,
                "attempts": 2,
                "is_fallback": True
            }
        return {
            "error": res.error,
            "attempts": 2,
            "is_fallback": True
        }

    async def log_result(self, state: AgentState):
        print("📝 Logging request result to database...")
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
