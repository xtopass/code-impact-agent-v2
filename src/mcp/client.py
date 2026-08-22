"""
MCP (Model Context Protocol) 客户端
用于集成外部工具和扩展Agent能力
支持 stdio / SSE / HTTP 多种传输方式及自定义认证
"""
import json
import subprocess
import asyncio
import httpx
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum


class MCPTransport(str, Enum):
    """MCP 传输协议"""
    STDIO = "stdio"       # 本地子进程（默认）
    SSE = "sse"           # Server-Sent Events
    HTTP = "http"         # HTTP JSON-RPC


class MCPScope(str, Enum):
    """MCP 作用域"""
    LOCAL = "local"       # 本地工具
    REMOTE = "remote"     # 远程服务（需认证）


@dataclass
class MCPServerConfig:
    """MCP服务器配置"""
    name: str
    command: str = ""                  # stdio 模式下可执行命令
    args: List[str] = field(default_factory=list)
    transport: MCPTransport = MCPTransport.STDIO
    url: str = ""                      # sse/http 模式下的服务端地址
    scope: MCPScope = MCPScope.LOCAL
    timeout: int = 30
    enabled: bool = True
    # 认证信息
    auth_type: str = "none"            # none | bearer | basic | api_key
    auth_token: str = ""               # Bearer token 或 API key 值
    auth_header: str = "Authorization" # 认证请求头名称
    auth_prefix: str = "Bearer"        # Token 前缀
    # 环境变量（子进程用）
    env: Dict[str, str] = field(default_factory=dict)
    # 自定义工具定义（JSON Schema）
    custom_tools: List[Dict[str, Any]] = field(default_factory=list)
    # 备注
    description: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "command": self.command,
            "args": self.args,
            "transport": self.transport.value,
            "url": self.url,
            "scope": self.scope.value,
            "timeout": self.timeout,
            "enabled": self.enabled,
            "auth_type": self.auth_type,
            "auth_header": self.auth_header,
            "auth_prefix": self.auth_prefix,
            "env": self.env,
            "custom_tools": self.custom_tools,
            "description": self.description,
            "token_set": bool(self.auth_token),
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'MCPServerConfig':
        config = cls(
            name=data["name"],
            command=data.get("command", ""),
            args=data.get("args", []),
            url=data.get("url", ""),
            timeout=data.get("timeout", 30),
            enabled=data.get("enabled", True),
            auth_type=data.get("auth_type", "none"),
            auth_header=data.get("auth_header", "Authorization"),
            auth_prefix=data.get("auth_prefix", "Bearer"),
            env=data.get("env", {}),
            custom_tools=data.get("custom_tools", []),
            description=data.get("description", ""),
        )
        if "transport" in data:
            config.transport = MCPTransport(data["transport"])
        if "scope" in data:
            config.scope = MCPScope(data["scope"])
        config.auth_token = data.get("auth_token", "")
        return config


@dataclass
class MCPTool:
    """MCP工具定义"""
    name: str
    description: str
    input_schema: Dict[str, Any]
    example: Optional[Dict] = None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
            "example": self.example,
        }


class MCPClient:
    """MCP客户端 - 管理MCP服务器连接和工具调用"""

    def __init__(self):
        self.servers: Dict[str, MCPServerConfig] = {}
        self.tools: Dict[str, List[MCPTool]] = {}
        self._callbacks: Dict[str, Callable] = {}

    # ---- 服务器管理 ----

    def register_server(self, config: MCPServerConfig) -> bool:
        """注册MCP服务器"""
        if config.name in self.servers:
            return False
        self.servers[config.name] = config
        self.tools[config.name] = []
        return True

    def unregister_server(self, name: str) -> bool:
        """注销MCP服务器"""
        if name not in self.servers:
            return False
        del self.servers[name]
        self.tools.pop(name, None)
        return True

    def get_server(self, name: str) -> Optional[MCPServerConfig]:
        """获取服务器配置"""
        return self.servers.get(name)

    def list_servers(self) -> List[Dict]:
        """列出所有已注册的服务器"""
        return [c.to_dict() for c in self.servers.values() if c.enabled]

    def discover_tools(self, server_name: str) -> List[MCPTool]:
        """发现服务器的工具列表"""
        # 优先使用自定义工具定义
        config = self.servers.get(server_name)
        if config and config.custom_tools:
            return [
                MCPTool(
                    name=t["name"],
                    description=t.get("description", ""),
                    input_schema=t.get("input_schema", {"type": "object", "properties": {}}),
                    example=t.get("example"),
                )
                for t in config.custom_tools
            ]
        # 内置工具回退
        tools_map = {
            "git": self._get_git_tools(),
            "semgrep": self._get_semgrep_tools(),
            "puppet": self._get_puppet_tools(),
            "dependency": self._get_dependency_tools(),
        }
        return tools_map.get(server_name, [])

    # ---- 工具调用 ----

    async def call_tool(self, server_name: str, tool_name: str, arguments: Dict) -> Dict:
        """调用MCP工具"""
        if server_name not in self.servers:
            return {"error": f"服务器 {server_name} 未注册"}
        config = self.servers[server_name]
        if not config.enabled:
            return {"error": f"服务器 {server_name} 已禁用"}

        # 远程 SSE/HTTP 模式：通过 HTTP 调用
        if config.transport in (MCPTransport.SSE, MCPTransport.HTTP):
            return await self._call_remote_tool(config, tool_name, arguments)

        # stdio 模式：本地子进程
        return await self._call_stdio_tool(config, tool_name, arguments)

    async def _call_stdio_tool(self, config: MCPServerConfig, tool_name: str, args: Dict) -> Dict:
        """通过子进程调用本地工具"""
        cmd = [config.command] + config.args + [tool_name]
        try:
            proc_env = {**__import__('os').environ, **config.env}
            result = subprocess.run(
                cmd,
                input=json.dumps(args),
                capture_output=True,
                text=True,
                timeout=config.timeout,
                env=proc_env,
            )
            if result.returncode == 0:
                try:
                    return json.loads(result.stdout)
                except json.JSONDecodeError:
                    return {"output": result.stdout, "raw": True}
            return {"error": result.stderr or f"工具返回码 {result.returncode}"}
        except subprocess.TimeoutExpired:
            return {"error": f"超时（{config.timeout}s）"}
        except FileNotFoundError:
            return {"error": f"命令未找到: {config.command}"}
        except Exception as e:
            return {"error": str(e)}

    async def _call_remote_tool(self, config: MCPServerConfig, tool_name: str, args: Dict) -> Dict:
        """通过 HTTP/SSE 调用远程工具"""
        headers = {"Content-Type": "application/json"}
        if config.auth_type == "bearer" and config.auth_token:
            headers[config.auth_header] = f"{config.auth_prefix} {config.auth_token}"
        elif config.auth_type == "api_key" and config.auth_token:
            headers[config.auth_header] = config.auth_token
        elif config.auth_type == "basic" and config.auth_token:
            import base64
            headers["Authorization"] = f"Basic {base64.b64encode(config.auth_token.encode()).decode()}"

        url = f"{config.url.rstrip('/')}/tools/{tool_name}"
        try:
            async with httpx.AsyncClient(timeout=config.timeout) as client:
                resp = await client.post(url, json=args, headers=headers)
                resp.raise_for_status()
                return resp.json()
        except httpx.TimeoutException:
            return {"error": f"请求超时（{config.timeout}s）"}
        except httpx.HTTPStatusError as e:
            return {"error": f"HTTP {e.response.status_code}: {e.response.text}"}
        except Exception as e:
            return {"error": str(e)}

    # ---- 内置工具集 ----

    def _get_git_tools(self) -> List[MCPTool]:
        return [
            MCPTool(
                name="git_diff",
                description="获取文件变更diff",
                input_schema={
                    "type": "object",
                    "properties": {
                        "file": {"type": "string", "description": "目标文件路径"},
                        "staged": {"type": "boolean", "description": "是否只获取暂存区"},
                    },
                    "required": ["file"],
                },
                example={"file": "src/app.py", "staged": False},
            ),
            MCPTool(
                name="git_log",
                description="获取提交历史",
                input_schema={
                    "type": "object",
                    "properties": {
                        "file": {"type": "string"},
                        "limit": {"type": "integer", "default": 10},
                    },
                    "required": ["file"],
                },
            ),
            MCPTool(
                name="git_changed_files",
                description="获取变更文件列表",
                input_schema={
                    "type": "object",
                    "properties": {
                        "base": {"type": "string", "default": "HEAD"},
                        "head": {"type": "string", "default": "HEAD"},
                    },
                },
            ),
        ]

    def _get_semgrep_tools(self) -> List[MCPTool]:
        return [
            MCPTool(
                name="semgrep_scan",
                description="运行静态安全扫描",
                input_schema={
                    "type": "object",
                    "properties": {
                        "target": {"type": "string", "description": "扫描目标文件或目录"},
                        "rules": {"type": "string", "description": "规则文件路径"},
                        "max_depth": {"type": "integer", "default": 10},
                    },
                    "required": ["target"],
                },
            ),
        ]

    def _get_puppet_tools(self) -> List[MCPTool]:
        return [
            MCPTool(
                name="puppet_validate",
                description="验证Puppet清单语法",
                input_schema={
                    "type": "object",
                    "properties": {"manifest": {"type": "string", "description": "Puppet清单文件路径"}},
                    "required": ["manifest"],
                },
            ),
            MCPTool(
                name="puppet_dependencies",
                description="解析Puppet资源依赖",
                input_schema={
                    "type": "object",
                    "properties": {"manifest": {"type": "string"}},
                    "required": ["manifest"],
                },
            ),
        ]

    def _get_dependency_tools(self) -> List[MCPTool]:
        return [
            MCPTool(
                name="dep_graph_build",
                description="构建依赖图",
                input_schema={
                    "type": "object",
                    "properties": {
                        "root": {"type": "string"},
                        "language": {"type": "string", "enum": ["python", "javascript", "java"]},
                    },
                    "required": ["root"],
                },
            ),
        ]


# 单例实例
_mcp_client = MCPClient()


def get_mcp_client() -> MCPClient:
    """获取MCP客户端单例"""
    return _mcp_client


def init_mcp(servers: List[Dict] = None):
    """初始化MCP客户端"""
    client = get_mcp_client()

    # 注册内置服务器
    built_in = [
        MCPServerConfig(name="git", command="git"),
        MCPServerConfig(name="semgrep", command="semgrep"),
        MCPServerConfig(name="puppet", command="puppet"),
        MCPServerConfig(name="dependency", command="npx", args=["depgraph"]),
    ]
    for server in built_in:
        client.register_server(server)

    # 加载自定义服务器
    if servers:
        for config in servers:
            mc = MCPServerConfig.from_dict(config)
            client.register_server(mc)
