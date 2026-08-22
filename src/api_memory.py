"""
记忆管理 API
提供记忆的增删查和统计
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any


router = APIRouter(prefix="/api/memory", tags=["记忆管理"])


class RememberRequest(BaseModel):
    content: str
    memory_type: str = "short_term"   # short_term | long_term | episodic | semantic
    importance: float = 0.5
    tags: List[str] = []
    metadata: Dict[str, Any] = {}


class RecallRequest(BaseModel):
    query: str = ""
    memory_type: str = "all"
    limit: int = 20


@router.get("")
async def list_memories(
    memory_type: Optional[str] = None,
    tag: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """列出记忆"""
    from src.memory.system import get_memory_manager
    mm = get_memory_manager()

    all_memories = []
    if memory_type is None or memory_type == "short_term":
        all_memories.extend(mm.short_term.get_all())
    if memory_type is None or memory_type == "long_term":
        all_memories.extend(mm.long_term.get_all())
    if memory_type is None or memory_type == "episodic":
        all_memories.extend(mm.episodic.get_recent_episodes(hours=720))  # 30 days
    if memory_type is None or memory_type == "semantic":
        all_memories.extend(mm.semantic.get_all())

    if tag:
        all_memories = [m for m in all_memories if tag in m.get("tags", [])]

    # 按时间倒序
    all_memories.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return all_memories[offset:offset + limit]


@router.post("")
async def remember(req: RememberRequest):
    """添加记忆"""
    from src.memory.system import get_memory_manager
    mm = get_memory_manager()
    mem_id = mm.remember(
        content=req.content,
        memory_type=req.memory_type,
        importance=req.importance,
        tags=req.tags,
        metadata=req.metadata
    )
    return {"memory_id": mem_id, "success": True}


@router.delete("/{memory_id}")
async def forget(memory_id: str):
    """删除记忆"""
    from src.memory.system import get_memory_manager
    mm = get_memory_manager()
    success = mm.forget(memory_id)
    if not success:
        raise HTTPException(status_code=404, detail="记忆不存在")
    return {"success": True}


@router.post("/recall")
async def recall(req: RecallRequest):
    """语义检索记忆"""
    from src.memory.system import get_memory_manager
    mm = get_memory_manager()
    memories = mm.recall(req.query, memory_type=req.memory_type, limit=req.limit)
    return {"memories": memories, "count": len(memories)}


@router.get("/stats")
async def get_stats():
    """记忆统计"""
    from src.memory.system import get_memory_manager
    mm = get_memory_manager()
    return mm.get_statistics()


@router.post("/consolidate")
async def consolidate():
    """执行记忆巩固"""
    from src.memory.system import get_memory_manager
    mm = get_memory_manager()
    count = mm.consolidate_memories()
    return {"consolidated": count}
