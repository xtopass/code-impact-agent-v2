"""
Express API服务器
"""
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import uvicorn
import os
import json


# 创建FastAPI应用
app = FastAPI(
    title="Code Impact Agent API",
    description="代码影响范围调查多Agent协作系统API",
    version="2.0.0"
)

# CORS配置
# 注意：allow_origins=["*"] 与 allow_credentials=True 在浏览器中互斥，
# 这里改为显式允许来源，或去掉 allow_credentials
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 从系统导入实例
from src.system import get_system
system = get_system()


# ============ 数据模型 ============

class MCPConfig(BaseModel):
    name: str
    command: str = ""
    args: List[str] = []
    transport: str = "stdio"          # stdio | sse | http
    url: str = ""                     # sse/http 模式下的服务端地址
    scope: str = "local"              # local | remote
    timeout: int = 30
    enabled: bool = True
    # 认证
    auth_type: str = "none"           # none | bearer | basic | api_key
    auth_token: str = ""
    auth_header: str = "Authorization"
    auth_prefix: str = "Bearer"
    # 环境变量 & 自定义工具
    env: Dict[str, str] = {}
    custom_tools: List[Dict[str, Any]] = []
    description: str = ""


class SkillMetadata(BaseModel):
    id: str
    name: str
    version: str = "1.0.0"
    description: str
    entry_point: str
    tags: List[str] = []


class CaseRecord(BaseModel):
    target_file: str
    risk_level: str
    findings_count: int
    agents_used: List[str]
    execution_time_ms: int
    quality_score: float


class FeedbackRequest(BaseModel):
    case_id: str
    is_correct: bool
    feedback: Optional[str] = None


class RuleAdjustment(BaseModel):
    type: str
    reason: str
    confidence: float = 0.8
    value: Dict[str, Any] = {}


# ============ MCP端点 ============

@app.get("/api/mcp/servers")
async def list_mcp_servers():
    """列出所有MCP服务器"""
    return system.list_mcp_servers()


@app.post("/api/mcp/servers")
async def add_mcp_server(config: MCPConfig):
    """添加MCP服务器"""
    return system.add_mcp_server(config.dict())


@app.delete("/api/mcp/servers/{name}")
async def remove_mcp_server(name: str):
    """移除MCP服务器"""
    return system.remove_mcp_server(name)


@app.post("/api/mcp/tools/{server}/{tool}")
async def call_mcp_tool(server: str, tool: str, args: Dict[str, Any]):
    """调用MCP工具"""
    return system.call_mcp_tool(server, tool, args)


# ============ Skill端点 ============

@app.get("/api/skills")
async def list_skills(active_only: bool = True):
    """列出所有Skills"""
    return system.list_skills(active_only=active_only)


@app.post("/api/skills")
async def register_skill(metadata: SkillMetadata):
    """注册新Skill"""
    return system.register_skill(metadata.dict())


@app.post("/api/skills/{skill_id}/execute")
async def execute_skill(skill_id: str, input_data: Dict[str, Any]):
    """执行Skill"""
    return system.execute_skill(skill_id, input_data)


# ============ Agent端点 ============

@app.get("/api/agents")
async def list_agents(role: Optional[str] = None):
    """列出Agents"""
    return system.list_agents(role)


@app.get("/api/agents/stats")
async def get_agent_stats():
    """获取Agent路由统计"""
    return system.get_routing_stats()


@app.post("/api/agents/route")
async def route_task(task_type: str, task_data: Dict[str, Any]):
    """路由任务"""
    return system.route_task(task_type, task_data)


# ============ 学习端点 ============

@app.post("/api/cases")
async def record_case(case: CaseRecord):
    """记录分析案例"""
    return system.record_case(case.dict())


@app.post("/api/cases/{case_id}/feedback")
async def add_feedback(case_id: str, feedback: FeedbackRequest):
    """添加用户反馈"""
    return system.add_feedback(case_id, feedback.is_correct, feedback.feedback)


@app.get("/api/learning/insights")
async def get_learning_insights():
    """获取学习洞察"""
    return system.get_learning_insights()


@app.post("/api/learning/rules/{rule_id}/adjust")
async def apply_rule_adjustment(rule_id: str, adjustment: RuleAdjustment):
    """应用规则调整"""
    return system.apply_rule_adjustment(rule_id, adjustment.dict())


# ============ 分析端点 ============

@app.post("/api/analyze")
async def run_analysis(target_file: str, options: Optional[Dict[str, Any]] = None):
    """运行完整分析"""
    return system.run_analysis(target_file, options or {})


@app.get("/api/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0"
    }


# ============ 配置管理端点 ============
from src.api_config import router as config_router
app.include_router(config_router)

# ============ 上下文管理端点 ============
from src.api_context import router as context_router
app.include_router(context_router)

# ============ 代码库管理端点 ============
from src.api_repositories import router as repositories_router
app.include_router(repositories_router)

# ============ 国际化端点 ============
from src.api_i18n import router as i18n_router
app.include_router(i18n_router)

# ============ 影响链分析端点 ============
from src.api_impact import router as impact_router
app.include_router(impact_router)

# ============ 记忆管理端点 ============
from src.api_memory import router as memory_router
app.include_router(memory_router)

# ============ 分析历史端点 ============
from src.api_history import router as history_router
app.include_router(history_router)

# ============ 自监督端点 ============
from src.api_supervision import router as supervision_router
app.include_router(supervision_router)


# ============ WebSocket端点 ============

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket实时通信"""
    await websocket.accept()
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # 处理消息
            if message.get("type") == "analysis_start":
                # 开始分析通知
                await websocket.send_json({
                    "type": "analysis_progress",
                    "status": "started",
                    "target": message.get("target_file")
                })
            
            elif message.get("type") == "feedback":
                # 用户反馈
                system.add_feedback(
                    message["case_id"],
                    message["is_correct"],
                    message.get("feedback")
                )
                await websocket.send_json({
                    "type": "feedback_ack",
                    "case_id": message["case_id"]
                })
    
    except WebSocketDisconnect:
        print("客户端断开连接")
    except Exception as e:
        print(f"WebSocket错误: {e}")
        await websocket.close()


# ============ 启动 ============

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    uvicorn.run(app, host="0.0.0.0", port=port)
