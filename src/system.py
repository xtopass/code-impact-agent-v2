"""
系统核心 - AgentSystem
初始化所有模块并管理系统状态
"""
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
from dataclasses import asdict


class AgentSystem:
    """Agent系统核心 - 统一管理所有模块"""
    
    def __init__(self):
        self.data_dir = Path(os.environ.get("DATA_DIR", "./data"))
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化各模块
        self._init_modules()
    
    def _init_modules(self):
        """初始化所有模块"""
        # MCP
        from src.mcp.client import get_mcp_client, init_mcp
        # Skills
        from src.skills.registry import get_skill_registry, init_skills
        # Agents
        from src.agents.router import get_agent_router
        # Learning
        from src.learning.engine import get_learning_engine
        # LLM (必需)
        from src.llm.client import init_llm, is_llm_enabled, get_llm_client
        # Memory
        from src.memory.system import init_memory, get_memory_manager
        # Context
        from src.context.manager import init_context, get_context_manager
        # Repositories
        from src.repositories.manager import init_repositories, get_repository_manager
        # i18n
        from src.i18n.manager import init_i18n, get_i18n
        
        # 加载MCP配置
        mcp_servers = self._load_config("mcp-servers.json", [])
        init_mcp(mcp_servers)
        
        # 初始化Skill系统
        init_skills(str(self.data_dir / "skills"))
        
        # 初始化记忆系统
        init_memory(str(self.data_dir / "memory"))
        
        # 初始化上下文管理
        init_context(max_sessions=100, default_max_tokens=4000)
        
        # 初始化代码库管理
        init_repositories(str(self.data_dir / "repositories.json"))
        
        # 初始化国际化
        i18n = init_i18n(str(Path(__file__).parent.parent / "i18n"))
        
        # LLM 配置（可选，未配置时部分 AI 功能不可用）
        llm_provider = os.environ.get("LLM_PROVIDER", "deepseek")
        api_key = os.environ.get(f"{llm_provider.upper()}_API_KEY") or \
                  os.environ.get("LLM_API_KEY")

        llm_enabled = bool(api_key)
        if llm_enabled:
            try:
                model = os.environ.get("LLM_MODEL", "deepseek-chat")
                init_llm(provider=llm_provider, api_key=api_key, model=model)
                client = get_llm_client()
                print(f"✅ LLM已启用: {llm_provider}/{client.config.model}")
            except Exception as e:
                print(f"⚠️ LLM初始化失败，将禁用AI功能: {e}")
                llm_enabled = False
        else:
            print("⚠️ LLM未配置，AI分析功能将不可用，请先在设置中配置API Key")
    
    def _load_config(self, filename: str, default: Any = None) -> Any:
        """加载配置文件"""
        config_file = self.data_dir / filename
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return default
    
    def _save_config(self, filename: str, data: Any):
        """保存配置文件"""
        config_file = self.data_dir / filename
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    # ============ MCP接口 ============
    
    def list_mcp_servers(self) -> List[Dict]:
        """列出MCP服务器"""
        from src.mcp.client import get_mcp_client
        return get_mcp_client().list_servers()
    
    def add_mcp_server(self, config: Dict) -> Dict:
        """添加MCP服务器"""
        from src.mcp.client import get_mcp_client, MCPServerConfig
        client = get_mcp_client()

        mc = MCPServerConfig.from_dict(config)
        if client.register_server(mc):
            servers = self._load_config("mcp-servers.json", [])
            servers.append(mc.to_dict())
            self._save_config("mcp-servers.json", servers)
            return {"success": True, "server": mc.to_dict()}
        return {"success": False, "error": "服务器已存在"}
    
    def remove_mcp_server(self, name: str) -> Dict:
        """移除MCP服务器"""
        from src.mcp.client import get_mcp_client
        client = get_mcp_client()
        
        if client.unregister_server(name):
            servers = self._load_config("mcp-servers.json", [])
            servers = [s for s in servers if s["name"] != name]
            self._save_config("mcp-servers.json", servers)
            return {"success": True}
        return {"success": False, "error": "服务器不存在"}
    
    def call_mcp_tool(self, server: str, tool: str, args: Dict) -> Dict:
        """调用MCP工具（同步包装，底层均为 subprocess.run 或 httpx）"""
        import asyncio
        import concurrent.futures
        from src.mcp.client import get_mcp_client
        client = get_mcp_client()

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(
                    lambda: asyncio.get_event_loop().run_until_complete(
                        client.call_tool(server, tool, args)
                    )
                )
                return future.result()
        else:
            return asyncio.get_event_loop().run_until_complete(
                client.call_tool(server, tool, args)
            )
    
    # ============ Skill接口 ============
    
    def list_skills(self, active_only: bool = True) -> List[Dict]:
        """列出Skills"""
        from src.skills.registry import get_skill_registry
        skills = get_skill_registry().list_skills(active_only=active_only)
        return [s.to_dict() for s in skills]
    
    def register_skill(self, metadata: Dict) -> Dict:
        """注册Skill"""
        from src.skills.registry import get_skill_registry, SkillMetadata
        registry = get_skill_registry()
        
        meta = SkillMetadata.from_dict(metadata)
        instance_id = registry.register_skill(meta)
        return {"success": True, "instance_id": instance_id}
    
    def execute_skill(self, skill_id: str, input_data: Dict) -> Dict:
        """执行Skill"""
        from src.skills.registry import get_skill_registry
        registry = get_skill_registry()
        return registry.execute_skill(skill_id, input_data)
    
    # ============ Agent接口 ============
    
    def list_agents(self, role: str = None) -> List[Dict]:
        """列出Agents"""
        from src.agents.router import get_agent_router, AgentRole
        router = get_agent_router()
        
        agents = router.list_agents(
            role=AgentRole(role) if role else None
        )
        return [a.to_dict() for a in agents]
    
    def get_routing_stats(self) -> Dict:
        """获取路由统计"""
        from src.agents.router import get_agent_router
        return get_agent_router().get_routing_stats()
    
    def route_task(self, task_type: str, task_data: Dict) -> Dict:
        """路由任务"""
        from src.agents.router import get_agent_router
        return get_agent_router().route_task(task_type, task_data)
    
    # ============ 学习接口 ============
    
    def record_case(self, case_data: Dict) -> Dict:
        """记录案例"""
        from src.learning.engine import get_learning_engine
        engine = get_learning_engine()
        case = engine.record_case(case_data)
        return {"success": True, "case_id": case.case_id}
    
    def add_feedback(self, case_id: str, is_correct: bool, feedback: str = None) -> Dict:
        """添加反馈"""
        from src.learning.engine import get_learning_engine
        engine = get_learning_engine()
        engine.add_feedback(case_id, is_correct, feedback)
        return {"success": True}
    
    def get_learning_insights(self) -> Dict:
        """获取学习洞察"""
        from src.learning.engine import get_learning_engine
        engine = get_learning_engine()
        return engine.export_insights()
    
    def apply_rule_adjustment(self, rule_id: str, adjustment: Dict) -> Dict:
        """应用规则调整"""
        from src.learning.engine import get_learning_engine
        engine = get_learning_engine()
        
        class Adj:
            def __init__(self, rid, atype, reason, conf, sval):
                self.rule_id = rid
                self.adjustment_type = atype
                self.reason = reason
                self.confidence = conf
                self.suggested_value = sval
        
        adj = Adj(rule_id, adjustment["type"], adjustment["reason"], 
                  adjustment.get("confidence", 0.8), adjustment.get("value", {}))
        engine.apply_adjustments([adj])
        return {"success": True}
    
    # ============ 分析接口 ============
    
    def run_analysis(self, target_file: str, options: Dict = None) -> Dict:
        """运行完整分析 - AI Agent核心流程"""
        import time
        import re
        from src.llm.client import get_llm_client
        from src.memory.system import get_memory_manager

        # 路径安全检查：防止路径注入
        if not target_file or not re.match(r'^[a-zA-Z0-9_\-./]', target_file):
            return {
                "error": "非法文件路径",
                "target_file": target_file,
                "llm_enabled": False
            }
        if '..' in target_file or target_file.startswith('/'):
            return {
                "error": "不允许的绝对路径或父目录引用",
                "target_file": target_file,
                "llm_enabled": False
            }

        start_time = time.time()

        # LLM 检查：分析功能需要 LLM
        if not is_llm_enabled():
            return {
                "error": "LLM 未配置，无法执行 AI 分析。请先在 /setup 页面或 /api/config/save 中配置 API Key。",
                "target_file": target_file,
                "llm_enabled": False
            }

        try:
            # 1. 获取代码变更（通过MCP工具）
            from src.mcp.client import get_mcp_client
            mcp_client = get_mcp_client()

            diff_result = mcp_client.call_tool("git", "git_diff", {"file": target_file})
            if "error" in diff_result:
                return {
                    "error": f"MCP git 工具调用失败: {diff_result['error']}",
                    "target_file": target_file,
                    "llm_enabled": False
                }
            diff_content = diff_result.get("output", "")

            if not diff_content.strip():
                return {
                    "error": f"无法获取 {target_file} 的 diff，请确认文件在 git 仓库中且有变更",
                    "target_file": target_file,
                    "llm_enabled": False
                }

            # 2. LLM语义分析（AI Agent核心能力）
            llm_client = get_llm_client()

            # 分析代码变更
            code_analysis = llm_client.analyze_code_impact(diff_content, {
                "file": target_file,
                "context": options.get("project_context", "") if options else ""
            })

            # 安全风险评估
            security_analysis = llm_client.assess_security_risk(diff_content)

            # 3. 生成综合报告
            analysis_results = {
                "code_impact": code_analysis,
                "security_risk": security_analysis,
                "target_file": target_file,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }

            # 生成自然语言报告
            report = llm_client.generate_report(
                analysis_results=analysis_results,
                project_name=options.get("project_name", "Unknown Project") if options else "Unknown Project",
                audience=options.get("audience", "developers") if options else "developers",
                purpose=options.get("purpose", "code_review") if options else "code_review"
            )

            execution_time = int((time.time() - start_time) * 1000)

            # 动态计算质量评分：基于 findings 数量和执行时间
            findings_count = len(code_analysis.get("direct_impact", []))
            quality_score = min(1.0, max(0.1, findings_count / 10.0))
            if execution_time > 30000:
                quality_score *= 0.8  # 超时惩罚

            result = {
                "target_file": target_file,
                "risk_level": code_analysis.get("risk_level", "medium"),
                "code_analysis": code_analysis,
                "security_analysis": security_analysis,
                "report": report,
                "execution_time_ms": execution_time,
                "agents_used": ["code_expert", "security_expert", "llm_analyzer"],
                "llm_enabled": True
            }

            # 记录案例用于学习
            self.record_case({
                "target_file": target_file,
                "risk_level": result["risk_level"],
                "findings_count": findings_count,
                "agents_used": result["agents_used"],
                "execution_time_ms": result["execution_time_ms"],
                "quality_score": round(quality_score, 2),
                "llm_analysis": True
            })

            return result

        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            return {
                "error": str(e),
                "target_file": target_file,
                "execution_time_ms": execution_time,
                "llm_enabled": False
            }

    def analyze_impact_chain(self, req: Dict) -> Dict:
        """分析代码变更影响链"""
        import time
        import json
        from src.llm.client import get_llm_client, is_llm_enabled
        from src.llm.prompts import render_prompt

        if not is_llm_enabled():
            return {"error": "LLM 未配置", "success": False}

        start_time = time.time()
        client = get_llm_client()

        try:
            depth = req.get("analysis_depth", "medium")
            change_desc = req.get("change_description", "")
            file_path = req.get("file_path", "")
            code_context = req.get("code_context", "")
            project_name = req.get("project_name", "Unknown Project")
            audience = req.get("audience", "developers")

            # 第一步：结构化影响链分析
            messages = render_prompt("impact_chain_analysis",
                                     change_description=change_desc,
                                     file_path=file_path or "N/A",
                                     code_context=code_context,
                                     analysis_depth=depth)
            raw_result = client.chat(messages)
            impact_data = _parse_llm_json(raw_result)

            # 第二步：生成自然语言报告
            report = client.chat(render_prompt("impact_report_generation",
                                               file_path=file_path or "N/A",
                                               analysis_depth=depth,
                                               project_name=project_name,
                                               audience=audience,
                                               analysis_result=json.dumps(impact_data, ensure_ascii=False, indent=2)))

            execution_time = int((time.time() - start_time) * 1000)
            return {
                "success": True,
                "impact_data": impact_data,
                "report": report,
                "execution_time_ms": execution_time,
                "analysis_depth": depth,
                "file_path": file_path,
                "change_description": change_desc
            }

        except Exception as e:
            return {"error": str(e), "success": False}

    def analyze_db_field_impact(self, req: Dict) -> Dict:
        """分析数据库字段变更影响链"""
        import time
        import json
        from src.llm.client import get_llm_client, is_llm_enabled
        from src.llm.prompts import render_prompt

        if not is_llm_enabled():
            return {"error": "LLM 未配置", "success": False}

        start_time = time.time()
        client = get_llm_client()

        try:
            depth = req.get("analysis_depth", "medium")
            change_desc = req.get("change_description", "")
            table_name = req.get("table_name", "")
            field_name = req.get("field_name", "")
            field_change = req.get("field_change", "")
            tech_stack = req.get("tech_stack", "")
            project_name = req.get("project_name", "Unknown Project")
            audience = req.get("audience", "developers")

            messages = render_prompt("db_field_impact_analysis",
                                     change_description=change_desc,
                                     table_name=table_name,
                                     field_name=field_name,
                                     field_change=field_change,
                                     tech_stack=tech_stack,
                                     analysis_depth=depth)
            raw_result = client.chat(messages)
            impact_data = _parse_llm_json(raw_result)

            report = client.chat(render_prompt("impact_report_generation",
                                               file_path=f"{table_name}.{field_name}",
                                               analysis_depth=depth,
                                               project_name=project_name,
                                               audience=audience,
                                               analysis_result=json.dumps(impact_data, ensure_ascii=False, indent=2)))

            execution_time = int((time.time() - start_time) * 1000)
            return {
                "success": True,
                "impact_data": impact_data,
                "report": report,
                "execution_time_ms": execution_time,
                "analysis_depth": depth,
                "table": table_name,
                "field": field_name,
                "change": field_change
            }

        except Exception as e:
            return {"error": str(e), "success": False}


def _parse_llm_json(text: str) -> Dict:
    """从 LLM 返回文本中解析 JSON"""
    try:
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1:
            return json.loads(text[start:end + 1])
    except (json.JSONDecodeError, ValueError):
        pass
    return {"raw_result": text, "parse_error": True}


# 全局系统实例
_system = None

def get_system() -> AgentSystem:
    """获取系统单例"""
    global _system
    if _system is None:
        _system = AgentSystem()
    return _system
