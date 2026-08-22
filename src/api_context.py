"""
上下文管理API
提供对话历史和上下文操作的REST接口
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any


router = APIRouter(prefix="/api/context", tags=["上下文管理"])


class MessageRequest(BaseModel):
    role: str
    content: str
    session_id: Optional[str] = None


class MessageResponse(BaseModel):
    session_id: str
    message_id: str
    role: str
    content: str
    timestamp: str


class SessionInfo(BaseModel):
    session_id: str
    message_count: int
    token_usage: int
    created_at: str
    updated_at: str


@router.post("/sessions", response_model=SessionInfo)
async def create_session():
    """创建新对话会话"""
    from src.context.manager import get_context_manager
    
    cm = get_context_manager()
    session = cm.create_session()
    
    return SessionInfo(
        session_id=session.session_id,
        message_count=0,
        token_usage=0,
        created_at=session.created_at,
        updated_at=session.updated_at
    )


@router.post("/sessions/{session_id}/messages", response_model=MessageResponse)
async def send_message(session_id: str, message: MessageRequest):
    """发送消息到指定会话"""
    from src.context.manager import get_context_manager
    
    cm = get_context_manager()
    session = cm.get_session(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    msg = session.send(message.role, message.content)
    
    return MessageResponse(
        session_id=session_id,
        message_id=msg.message_id,
        role=msg.role,
        content=msg.content,
        timestamp=msg.timestamp
    )


@router.get("/sessions/{session_id}/history", response_model=List[Dict])
async def get_history(session_id: str, limit: int = 50):
    """获取会话历史"""
    from src.context.manager import get_context_manager
    
    cm = get_context_manager()
    session = cm.get_session(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    return session.get_history(limit)


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """删除会话"""
    from src.context.manager import get_context_manager
    
    cm = get_context_manager()
    success = cm.delete_session(session_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    return {"success": True}


@router.get("/sessions", response_model=List[SessionInfo])
async def list_sessions():
    """列出所有会话"""
    from src.context.manager import get_context_manager
    
    cm = get_context_manager()
    sessions = cm.list_sessions()
    
    return [SessionInfo(**s) for s in sessions]


@router.post("/sessions/cleanup")
async def cleanup_sessions(max_age_hours: int = 24):
    """清理过期会话"""
    from src.context.manager import get_context_manager
    
    cm = get_context_manager()
    expired = cm.cleanup_expired(max_age_hours)
    
    return {
        "deleted_count": len(expired),
        "expired_sessions": expired
    }


# 记忆管理API
@router.api_route("/memory", methods=["POST", "GET"])
async def memory_operations(operation: str = "get",
                           content: str = None,
                           memory_type: str = "short_term",
                           importance: float = 0.5,
                           tags: List[str] = None):
    """记忆操作"""
    from src.memory.system import get_memory_manager
    
    mm = get_memory_manager()
    
    if operation == "remember":
        if not content:
            raise HTTPException(status_code=400, detail="content is required")
        
        memory_id = mm.remember(
            content=content,
            memory_type=memory_type,
            importance=importance,
            tags=tags
        )
        return {"memory_id": memory_id}
    
    elif operation == "recall":
        memories = mm.recall(content or "", memory_type=memory_type, limit=10)
        return {"memories": memories}
    
    elif operation == "consolidate":
        count = mm.consolidate_memories()
        return {"consolidated": count}
    
    elif operation == "stats":
        stats = mm.get_statistics()
        return stats
    
    else:
        raise HTTPException(status_code=400, detail="Invalid operation")


@router.get("/memory/contexts/{task}")
async def get_memory_context(task: str, max_items: int = 10):
    """获取与任务相关的记忆上下文"""
    from src.memory.system import get_memory_manager
    
    mm = get_memory_manager()
    context = mm.get_context(task, max_tokens=max_items * 500)
    
    return {"context": context, "item_count": len(context)}
