from pydantic import BaseModel


class ChaosConfig(BaseModel):
    kill_claude: bool = False
    latency_spike: bool = False
    mcp_crash: bool = False


chaos_state = ChaosConfig()
