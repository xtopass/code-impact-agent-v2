"""
LLM集成模块 - AI Agent的核心能力
提供语义理解、智能推理和自然语言生成
"""
import os
import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
import asyncio


class LLMProvider(str, Enum):
    """LLM提供商"""
    DEEPSEEK = "deepseek"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    ZHIPU = "zhipu"


@dataclass
class LLMConfig:
    """LLM配置"""
    provider: LLMProvider
    api_key: str
    model: str = "deepseek-chat"
    temperature: float = 0.3
    max_tokens: int = 2000
    timeout: int = 60
    
    def to_dict(self) -> dict:
        return {
            "provider": self.provider.value,
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "api_key_set": bool(self.api_key)
        }


class LLMClient:
    """LLM客户端 - AI Agent的"大脑"
    
    核心能力：
    1. 语义理解 - 理解代码变更意图
    2. 智能推理 - 分析影响和风险
    3. 自然语言生成 - 输出人类可读报告
    4. 持续学习 - 从反馈中优化
    """
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self.client = None
        self._init_client()
    
    def _init_client(self):
        """初始化LLM客户端"""
        try:
            if self.config.provider == LLMProvider.DEEPSEEK:
                from openai import OpenAI
                self.client = OpenAI(
                    api_key=self.config.api_key,
                    base_url="https://api.deepseek.com"
                )
                
            elif self.config.provider == LLMProvider.OPENAI:
                from openai import OpenAI
                self.client = OpenAI(api_key=self.config.api_key)
                
            elif self.config.provider == LLMProvider.ANTHROPIC:
                import anthropic
                self.client = anthropic.Anthropic(api_key=self.config.api_key)
                
            elif self.config.provider == LLMProvider.ZHIPU:
                from openai import OpenAI
                self.client = OpenAI(
                    api_key=self.config.api_key,
                    base_url="https://open.bigmodel.cn/api/paas/v4"
                )
                
        except ImportError as e:
            raise ImportError(f"请先安装对应SDK: pip install openai anthropic")
    
    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """聊天对话 - 核心推理能力"""
        if not self.client:
            raise RuntimeError("LLM客户端未初始化")
        
        try:
            if self.config.provider in [LLMProvider.DEEPSEEK, LLMProvider.OPENAI, LLMProvider.ZHIPU]:
                response = self.client.chat.completions.create(
                    model=self.config.model,
                    messages=messages,
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens,
                    **kwargs
                )
                return response.choices[0].message.content
                
            elif self.config.provider == LLMProvider.ANTHROPIC:
                response = self.client.messages.create(
                    model=self.config.model,
                    messages=messages,
                    max_tokens=self.config.max_tokens,
                    temperature=self.config.temperature,
                    **kwargs
                )
                return response.content[0].text
                
        except Exception as e:
            raise RuntimeError(f"LLM调用失败: {str(e)}")
    
    def analyze_code_impact(self, diff: str, context: Dict = None) -> Dict:
        """分析代码变更影响 - AI Agent核心功能
        
        会结合记忆中的历史分析结果进行综合判断
        """
        from src.llm.prompts import render_prompt
        from src.memory.system import get_memory_manager
        
        # 获取相关记忆作为上下文
        memory_mgr = get_memory_manager()
        related_memories = memory_mgr.get_context(diff[:200], max_tokens=10)
        
        # 构建系统提示，包含历史参考
        base_system = """你是一位资深软件架构师，专注于代码影响范围分析。
你的职责：
1. 深入理解代码变更的意图
2. 识别直接和间接影响
3. 评估技术风险和业务风险
4. 提供可操作的改进建议

分析原则：
- 关注变更的语义而非仅语法
- 考虑向后兼容性
- 评估对上下游模块的影响
- 识别潜在的性能和安全风险"""
        
        # 如果有相关历史记忆，加入提示
        if related_memories:
            history_context = "\n\n## 相关历史分析参考\n"
            for mem in related_memories[:3]:
                history_context += f"- {mem.get('content', '')[:100]}...\n"
            base_system += history_context
        
        messages = render_prompt("code_diff_analysis", 
                                file_path=context.get("file", "unknown") if context else "unknown",
                                diff_content=diff,
                                project_context=context.get("context", "") if context else "")
        
        # 替换系统提示
        messages[0]["content"] = base_system
        
        result = self.chat(messages)
        
        # 记录到长期记忆
        memory_mgr.remember(
            content=f"代码分析: {context.get('file', 'unknown')} - 风险等级: {result.get('risk_level', 'unknown')}",
            memory_type="episodic",
            importance=result.get("risk_level", "medium") in ["high", "critical"] and 0.8 or 0.5,
            tags=["code_analysis", context.get("file", "").split(".")[-1] if context else "unknown"]
        )
        
        # 尝试解析JSON
        try:
            start = result.find('{')
            end = result.rfind('}')
            if start != -1 and end != -1:
                json_str = result[start:end+1]
                return json.loads(json_str)
        except:
            pass
        
        return {"raw_result": result}
    
    def assess_security_risk(self, diff: str) -> Dict:
        """评估安全风险 - AI Agent安全能力"""
        from src.llm.prompts import render_prompt
        
        messages = render_prompt("security_risk_analysis", diff_content=diff)
        result = self.chat(messages)
        
        try:
            start = result.find('{')
            end = result.rfind('}')
            if start != -1 and end != -1:
                return json.loads(result[start:end+1])
        except:
            pass
        
        return {"raw_result": result}
    
    def check_api_compatibility(self, api_diff: str, endpoints: str) -> Dict:
        """检查API兼容性 - AI Agent契约理解"""
        from src.llm.prompts import render_prompt
        
        messages = render_prompt("api_compatibility_check", 
                                api_diff=api_diff,
                                endpoints=endpoints)
        result = self.chat(messages)
        
        try:
            start = result.find('{')
            end = result.rfind('}')
            if start != -1 and end != -1:
                return json.loads(result[start:end+1])
        except:
            pass
        
        return {"raw_result": result}
    
    def generate_report(self, analysis_results: Dict, 
                       project_name: str = "",
                       audience: str = "developers",
                       purpose: str = "code_review") -> str:
        """生成自然语言报告 - AI Agent表达能力"""
        from src.llm.prompts import render_prompt
        
        messages = render_prompt("comprehensive_report",
                                analysis_results=json.dumps(analysis_results, indent=2, ensure_ascii=False),
                                project_name=project_name,
                                audience=audience,
                                purpose=purpose)
        
        return self.chat(messages)
    
    def learn_from_feedback(self, original_analysis: Dict,
                           is_correct: bool,
                           feedback_text: str,
                           actual_outcome: str = "") -> Dict:
        """从反馈中学习 - AI Agent进化能力"""
        from src.llm.prompts import render_prompt
        
        messages = render_prompt("feedback_learning",
                                original_analysis=json.dumps(original_analysis, indent=2, ensure_ascii=False),
                                is_correct=is_correct,
                                feedback_text=feedback_text,
                                actual_outcome=actual_outcome)
        
        result = self.chat(messages)
        
        try:
            start = result.find('{')
            end = result.rfind('}')
            if start != -1 and end != -1:
                return json.loads(result[start:end+1])
        except:
            pass
        
        return {"raw_result": result}
    
    def stream_response(self, messages: List[Dict[str, str]], 
                       on_chunk=None, **kwargs) -> str:
        """流式响应 - 实时输出"""
        if not self.client:
            raise RuntimeError("LLM客户端未初始化")
        
        full_response = ""
        
        try:
            if self.config.provider in [LLMProvider.DEEPSEEK, LLMProvider.OPENAI, LLMProvider.ZHIPU]:
                stream = self.client.chat.completions.create(
                    model=self.config.model,
                    messages=messages,
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens,
                    stream=True,
                    **kwargs
                )
                
                for chunk in stream:
                    if chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        full_response += content
                        if on_chunk:
                            on_chunk(content)
                            
            elif self.config.provider == LLMProvider.ANTHROPIC:
                stream = self.client.messages.stream(
                    model=self.config.model,
                    messages=messages,
                    max_tokens=self.config.max_tokens,
                    temperature=self.config.temperature,
                    **kwargs
                )
                
                with stream as stream_obj:
                    for text in stream_obj.text_stream:
                        full_response += text
                        if on_chunk:
                            on_chunk(text)
                            
        except Exception as e:
            raise RuntimeError(f"流式响应失败: {str(e)}")
        
        return full_response


# 全局单例
_llm_config = None
_llm_client = None


def init_llm(provider: str = "deepseek", api_key: str = None, model: str = "deepseek-chat") -> LLMConfig:
    """初始化LLM配置"""
    global _llm_config, _llm_client
    
    if not api_key:
        api_key = os.environ.get(f"{provider.upper()}_API_KEY") or \
                  os.environ.get("LLM_API_KEY")
    
    if not api_key:
        raise ValueError(f"未找到 {provider.upper()}_API_KEY 或 LLM_API_KEY")
    
    _llm_config = LLMConfig(
        provider=LLMProvider(provider),
        api_key=api_key,
        model=model
    )
    
    _llm_client = LLMClient(_llm_config)
    
    return _llm_config


def get_llm_client() -> Optional[LLMClient]:
    """获取LLM客户端"""
    return _llm_client


def is_llm_enabled() -> bool:
    """检查LLM是否启用"""
    return _llm_client is not None


def chat_with_llm(prompt: str, system_prompt: str = None) -> str:
    """快速聊天"""
    if not _llm_client:
        raise RuntimeError("LLM未配置，请先调用 init_llm()")
    
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    
    return _llm_client.chat(messages)
