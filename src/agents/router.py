"""
Agent注册表和路由系统
支持动态注册、智能路由和负载均衡
"""
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import asyncio


class AgentRole(str, Enum):
    """Agent角色类型"""
    EXPERT = "expert"           # 领域专家
    COORDINATOR = "coordinator" # 协调者
    REVIEWER = "reviewer"       # 审查者
    LEARNER = "learner"         # 学习者


class AgentStatus(str, Enum):
    """Agent状态"""
    IDLE = "idle"
    BUSY = "busy"
    OFFLINE = "offline"
    ERROR = "error"


@dataclass
class AgentCapability:
    """Agent能力定义"""
    name: str
    description: str
    input_types: List[str]
    output_types: List[str]
    priority: int = 1  # 优先级，越高越优先


@dataclass
class AgentConfig:
    """Agent配置"""
    id: str
    name: str
    role: AgentRole
    capabilities: List[AgentCapability]
    description: str = ""
    max_concurrent: int = 3
    timeout: int = 60
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role.value,
            "capabilities": [c.__dict__ for c in self.capabilities],
            "description": self.description,
            "max_concurrent": self.max_concurrent,
            "timeout": self.timeout,
            "enabled": self.enabled,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'AgentConfig':
        config = cls(
            id=data["id"],
            name=data["name"],
            role=AgentRole(data.get("role", "expert")),
            capabilities=[
                AgentCapability(**cap) if isinstance(cap, dict) else cap
                for cap in data.get("capabilities", [])
            ],
            description=data.get("description", ""),
            max_concurrent=data.get("max_concurrent", 3),
            timeout=data.get("timeout", 60),
            enabled=data.get("enabled", True),
            metadata=data.get("metadata", {})
        )
        return config


@dataclass
class AgentInstance:
    """Agent实例"""
    config: AgentConfig
    status: AgentStatus = AgentStatus.IDLE
    current_task: Optional[str] = None
    tasks_completed: int = 0
    errors_count: int = 0
    last_seen: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            **self.config.to_dict(),
            "status": self.status.value,
            "current_task": self.current_task,
            "tasks_completed": self.tasks_completed,
            "errors_count": self.errors_count,
            "last_seen": self.last_seen
        }


class AgentRouter:
    """Agent路由器 - 智能任务分发"""
    
    def __init__(self):
        self.agents: Dict[str, AgentInstance] = {}
        self.routing_table: Dict[str, List[str]] = {}  # capability -> agent_ids
        self.priority_queue: List[Dict] = []
    
    def register_agent(self, config: AgentConfig, executor: Callable = None) -> str:
        """注册Agent"""
        if config.id in self.agents:
            raise ValueError(f"Agent {config.id} 已存在")
        
        instance = AgentInstance(config=config)
        self.agents[config.id] = instance
        
        # 构建路由表
        for cap in config.capabilities:
            if cap.name not in self.routing_table:
                self.routing_table[cap.name] = []
            self.routing_table[cap.name].append(config.id)
        
        return config.id
    
    def unregister_agent(self, agent_id: str) -> bool:
        """注销Agent"""
        if agent_id not in self.agents:
            return False
        
        instance = self.agents[agent_id]
        
        # 从路由表移除
        for caps in self.routing_table.values():
            if agent_id in caps:
                caps.remove(agent_id)
        
        del self.agents[agent_id]
        return True
    
    def get_agent(self, agent_id: str) -> Optional[AgentInstance]:
        """获取Agent实例"""
        return self.agents.get(agent_id)
    
    def list_agents(self, role: AgentRole = None, enabled_only: bool = True) -> List[AgentInstance]:
        """列出Agents"""
        agents = list(self.agents.values())
        
        if role:
            agents = [a for a in agents if a.config.role == role]
        
        if enabled_only:
            agents = [a for a in agents if a.config.enabled and a.status != AgentStatus.OFFLINE]
        
        return agents
    
    def find_best_agent(self, task_type: str, priority: int = 0) -> Optional[AgentInstance]:
        """寻找最佳Agent处理任务"""
        candidates = self.routing_table.get(task_type, [])
        
        if not candidates:
            return None
        
        # 过滤可用Agent
        available = [
            self.agents[aid] for aid in candidates
            if self.agents[aid].status in [AgentStatus.IDLE, AgentStatus.BUSY]
        ]
        
        if not available:
            return None
        
        # 选择负载最小的Agent
        best = min(available, key=lambda a: a.tasks_completed)
        return best
    
    def route_task(self, task_type: str, task_data: Dict) -> Dict:
        """路由任务到合适Agent"""
        agent = self.find_best_agent(task_type)
        
        if not agent:
            return {
                "success": False,
                "error": f"无可用Agent处理 {task_type} 类型任务",
                "queue_position": len(self.priority_queue) + 1
            }
        
        # 更新Agent状态
        agent.status = AgentStatus.BUSY
        agent.current_task = task_type
        
        return {
            "success": True,
            "agent_id": agent.config.id,
            "agent_name": agent.config.name,
            "task_type": task_type,
            "task_data": task_data
        }
    
    def complete_task(self, agent_id: str, result: Any = None, error: str = None):
        """标记任务完成"""
        if agent_id not in self.agents:
            return
        
        agent = self.agents[agent_id]
        agent.status = AgentStatus.IDLE
        agent.current_task = None
        agent.last_seen = "just now"
        
        if error:
            agent.errors_count += 1
        else:
            agent.tasks_completed += 1
    
    def get_routing_stats(self) -> Dict:
        """获取路由统计"""
        total = len(self.agents)
        idle = sum(1 for a in self.agents.values() if a.status == AgentStatus.IDLE)
        busy = sum(1 for a in self.agents.values() if a.status == AgentStatus.BUSY)
        offline = sum(1 for a in self.agents.values() if a.status == AgentStatus.OFFLINE)
        
        return {
            "total_agents": total,
            "idle": idle,
            "busy": busy,
            "offline": offline,
            "routing_capacity": idle / total if total > 0 else 0
        }


class AgentCrew:
    """Agent团队 - 协作执行复杂任务"""
    
    def __init__(self, name: str, crew_id: str):
        self.name = name
        self.crew_id = crew_id
        self.members: List[AgentInstance] = []
        self.role_assignments: Dict[str, str] = {}  # member_id -> role
        self.workflow: List[str] = []  # 执行顺序
        self.is_running: bool = False
    
    def add_member(self, agent: AgentInstance, role: str) -> bool:
        """添加成员到团队"""
        if agent.config.id in self.role_assignments:
            return False
        
        self.members.append(agent)
        self.role_assignments[agent.config.id] = role
        return True
    
    def set_workflow(self, workflow: List[str]):
        """设置工作流"""
        self.workflow = workflow
    
    async def execute(self, task: Dict) -> Dict:
        """执行团队任务"""
        self.is_running = True
        results = {}

        try:
            for step in self.workflow:
                # 找到负责该步骤的Agent
                member_id = self._find_member_for_step(step)
                if not member_id:
                    results[step] = {"error": f"无Agent负责步骤: {step}"}
                    continue

                agent = next((a for a in self.members if a.config.id == member_id), None)
                if not agent:
                    results[step] = {"error": f"Agent {member_id} 不存在"}
                    continue

                # 执行步骤
                result = await self._execute_step(agent, step, task)
                results[step] = result

        finally:
            self.is_running = False

        return {
            "crew_id": self.crew_id,
            "results": results,
            "success": all("error" not in r for r in results.values())
        }
    
    def _find_member_for_step(self, step: str) -> Optional[str]:
        """找到负责指定步骤的Agent"""
        for member in self.members:
            for cap in member.config.capabilities:
                if cap.name == step or step in cap.name:
                    return member.config.id
        return None
    
    async def _execute_step(self, agent: AgentInstance, step: str, task: Dict) -> Dict:
        """执行单个步骤"""
        return {
            "step": step,
            "agent": agent.config.name,
            "status": "completed",
            "result": f"Step {step} completed by {agent.config.name}"
        }


# 全局Agent注册表
_agent_router = AgentRouter()
_agent_crews: Dict[str, AgentCrew] = {}

def get_agent_router() -> AgentRouter:
    """获取Agent路由器单例"""
    return _agent_router

def get_or_create_crew(name: str, crew_id: str) -> AgentCrew:
    """获取或创建Agent团队"""
    if crew_id not in _agent_crews:
        _agent_crews[crew_id] = AgentCrew(name=name, crew_id=crew_id)
    return _agent_crews[crew_id]
