"""
上下文管理系统
管理LLM对话上下文，支持多轮对话、上下文压缩和历史跟踪
"""
import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import uuid


@dataclass
class Message:
    """对话消息"""
    role: str  # 'system', 'user', 'assistant'
    content: str
    timestamp: str
    message_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.message_id:
            self.message_id = str(uuid.uuid4())[:8]
    
    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
            "message_id": self.message_id,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(self, data: dict) -> 'Message':
        return self(
            role=data["role"],
            content=data["content"],
            timestamp=data["timestamp"],
            message_id=data.get("message_id", ""),
            metadata=data.get("metadata", {})
        )


@dataclass
class ContextWindow:
    """上下文窗口"""
    messages: List[Message] = field(default_factory=list)
    max_tokens: int = 4000
    current_tokens: int = 0
    created_at: str = ""
    updated_at: str = ""
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.updated_at:
            self.updated_at = datetime.now().isoformat()
    
    def add_message(self, role: str, content: str, metadata: Dict = None):
        """添加消息"""
        message = Message(
            role=role,
            content=content,
            timestamp=datetime.now().isoformat(),
            metadata=metadata or {}
        )
        self.messages.append(message)
        self.updated_at = datetime.now().isoformat()
        
        # 估算token数量（简化：按字符数/4估算）
        self.current_tokens += len(content) // 4
    
    def remove_oldest(self, count: int = 1):
        """移除最旧的消息"""
        for _ in range(min(count, len(self.messages))):
            if self.messages:
                removed = self.messages.pop(0)
                self.current_tokens -= len(removed.content) // 4
        self.updated_at = datetime.now().isoformat()
    
    def clear(self):
        """清空上下文"""
        self.messages.clear()
        self.current_tokens = 0
        self.updated_at = datetime.now().isoformat()
    
    def is_full(self) -> bool:
        """检查是否已满"""
        return self.current_tokens >= self.max_tokens
    
    def get_messages_for_llm(self) -> List[Dict]:
        """获取LLM可用的消息列表"""
        return [m.to_dict() for m in self.messages]
    
    def compact(self) -> str:
        """压缩上下文 - 生成摘要
        
        TODO: 使用LLM生成智能摘要
        """
        if len(self.messages) <= 2:
            return self.get_messages_for_llm()
        
        # 简化：保留第一条和最后几条
        system_msg = next((m for m in self.messages if m.role == "system"), None)
        recent_msgs = self.messages[-3:] if len(self.messages) > 3 else self.messages
        
        result = []
        if system_msg:
            result.append(system_msg.to_dict())
        result.extend([m.to_dict() for m in recent_msgs])
        
        return result


class ConversationSession:
    """对话会话"""
    
    def __init__(self, session_id: str, context_window: ContextWindow):
        self.session_id = session_id
        self.context = context_window
        self.created_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()
        self.metadata: Dict[str, Any] = {}
    
    def send(self, role: str, content: str) -> Message:
        """发送消息"""
        self.context.add_message(role, content)
        self.updated_at = datetime.now().isoformat()
        
        # 如果上下文已满，进行压缩
        if self.context.is_full():
            self._compact_context()
        
        return self.context.messages[-1]
    
    def receive(self, content: str) -> Message:
        """接收回复"""
        return self.send("assistant", content)
    
    def _compact_context(self):
        """压缩上下文"""
        # TODO: 集成LLM进行智能压缩
        self.context.compact()
    
    def get_history(self, limit: int = None) -> List[Dict]:
        """获取对话历史"""
        messages = self.context.messages
        if limit:
            messages = messages[-limit:]
        return [m.to_dict() for m in messages]
    
    def reset(self):
        """重置会话"""
        self.context.clear()
        self.updated_at = datetime.now().isoformat()


class ContextManager:
    """上下文管理器 - 管理所有对话会话"""
    
    def __init__(self, max_sessions: int = 100, default_max_tokens: int = 4000):
        self.sessions: Dict[str, ConversationSession] = {}
        self.max_sessions = max_sessions
        self.default_max_tokens = default_max_tokens
    
    def create_session(self, session_id: str = None, 
                       max_tokens: int = None) -> ConversationSession:
        """创建新会话"""
        if not session_id:
            session_id = str(uuid.uuid4())[:12]
        
        # 如果会话已满，清理最旧的
        if len(self.sessions) >= self.max_sessions:
            self._evict_old_session()
        
        context = ContextWindow(max_tokens=max_tokens or self.default_max_tokens)
        session = ConversationSession(session_id, context)
        self.sessions[session_id] = session
        
        return session
    
    def get_session(self, session_id: str) -> Optional[ConversationSession]:
        """获取会话"""
        return self.sessions.get(session_id)
    
    def delete_session(self, session_id: str) -> bool:
        """删除会话"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False
    
    def _evict_old_session(self):
        """淘汰最旧的会话"""
        if not self.sessions:
            return
        
        oldest_id = min(
            self.sessions.keys(),
            key=lambda k: self.sessions[k].updated_at
        )
        del self.sessions[oldest_id]
    
    def list_sessions(self) -> List[Dict]:
        """列出所有会话"""
        return [
            {
                "session_id": sid,
                "created_at": session.created_at,
                "updated_at": session.updated_at,
                "message_count": len(session.context.messages),
                "token_usage": session.context.current_tokens
            }
            for sid, session in self.sessions.items()
        ]
    
    def cleanup_expired(self, max_age_hours: int = 24):
        """清理过期会话"""
        cutoff = datetime.now() - timedelta(hours=max_age_hours)
        expired = []
        
        for sid, session in self.sessions.items():
            session_time = datetime.fromisoformat(session.updated_at)
            if session_time < cutoff:
                expired.append(sid)
        
        for sid in expired:
            del self.sessions[sid]
        
        return expired


# 全局实例
_context_manager = None

def get_context_manager() -> ContextManager:
    """获取上下文管理器单例"""
    global _context_manager
    if _context_manager is None:
        _context_manager = ContextManager()
    return _context_manager

def init_context(max_sessions: int = 100, default_max_tokens: int = 4000):
    """初始化上下文管理"""
    global _context_manager
    _context_manager = ContextManager(max_sessions, default_max_tokens)
    return _context_manager
