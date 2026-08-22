"""
记忆管理系统
为AI Agent提供短期记忆、长期记忆和会话记忆
"""
import json
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import heapq


@dataclass
class MemoryItem:
    """记忆条目"""
    id: str
    content: str
    memory_type: str  # 'short_term', 'long_term', 'episodic', 'semantic'
    timestamp: str
    importance: float = 0.5  # 0.0-1.0
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "content": self.content,
            "memory_type": self.memory_type,
            "timestamp": self.timestamp,
            "importance": self.importance,
            "tags": self.tags,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'MemoryItem':
        return cls(
            id=data["id"],
            content=data["content"],
            memory_type=data["memory_type"],
            timestamp=data["timestamp"],
            importance=data.get("importance", 0.5),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {})
        )


class ShortTermMemory:
    """短期记忆 - 工作记忆，有限容量
    
    特点：
    - 容量有限（类似人类工作记忆7±2）
    - 快速遗忘
    - 用于当前任务处理
    """
    
    def __init__(self, capacity: int = 10, ttl_hours: float = 24.0):
        self.capacity = capacity
        self.ttl_hours = ttl_hours
        self.memories: List[MemoryItem] = []
    
    def add(self, content: str, importance: float = 0.5, 
            tags: List[str] = None, metadata: Dict = None) -> str:
        """添加记忆到短期记忆"""
        if len(self.memories) >= self.capacity:
            # 移除最不重要或最旧的记忆
            self._evict()
        
        memory = MemoryItem(
            id=str(uuid.uuid4())[:8],
            content=content,
            memory_type="short_term",
            timestamp=datetime.now().isoformat(),
            importance=importance,
            tags=tags or [],
            metadata=metadata or {}
        )
        
        self.memories.append(memory)
        # 按时间排序，最新的在前
        self.memories.sort(key=lambda x: x.timestamp, reverse=True)
        
        return memory.id
    
    def get_recent(self, limit: int = 5) -> List[MemoryItem]:
        """获取最近的记忆"""
        return self.memories[:limit]
    
    def get_by_tag(self, tag: str) -> List[MemoryItem]:
        """按标签检索"""
        return [m for m in self.memories if tag in m.tags]
    
    def clear(self):
        """清空短期记忆"""
        self.memories.clear()
    
    def _evict(self):
        """遗忘机制 - 移除最不重要的记忆"""
        if not self.memories:
            return
        
        # 按重要性排序，移除最低的
        self.memories.sort(key=lambda x: x.importance)
        self.memories.pop(0)
    
    def get_all(self) -> List[Dict]:
        """获取所有记忆"""
        return [m.to_dict() for m in self.memories]
    
    def cleanup_expired(self):
        """清理过期记忆"""
        now = datetime.now()
        expired = []
        remaining = []
        
        for memory in self.memories:
            memory_time = datetime.fromisoformat(memory.timestamp)
            age_hours = (now - memory_time).total_seconds() / 3600
            
            if age_hours > self.ttl_hours:
                expired.append(memory.id)
            else:
                remaining.append(memory)
        
        self.memories = remaining
        return expired


class LongTermMemory:
    """长期记忆 - 持久化存储
    
    特点：
    - 容量无限
    - 持久存储
    - 支持语义检索
    - 可沉淀为知识
    """
    
    def __init__(self, storage_path: str = "./data/long_term_memory.json"):
        self.storage_path = Path(storage_path)
        self.memories: Dict[str, MemoryItem] = {}
        self.index_by_tag: Dict[str, List[str]] = {}
        self.index_by_type: Dict[str, List[str]] = {}
        self._load()
    
    def _load(self):
        """加载长期记忆"""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for item in data:
                        memory = MemoryItem.from_dict(item)
                        self.memories[memory.id] = memory
                        self._index(memory)
            except (json.JSONDecodeError, IOError):
                pass
    
    def _save(self):
        """保存长期记忆"""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.storage_path, 'w', encoding='utf-8') as f:
            json.dump([m.to_dict() for m in self.memories.values()], f, indent=2, ensure_ascii=False)
    
    def _index(self, memory: MemoryItem):
        """建立索引"""
        # 按类型索引
        if memory.memory_type not in self.index_by_type:
            self.index_by_type[memory.memory_type] = []
        self.index_by_type[memory.memory_type].append(memory.id)
        
        # 按标签索引
        for tag in memory.tags:
            if tag not in self.index_by_tag:
                self.index_by_tag[tag] = []
            self.index_by_tag[tag].append(memory.id)
    
    def add(self, content: str, memory_type: str = "long_term",
            importance: float = 0.5, tags: List[str] = None,
            metadata: Dict = None) -> str:
        """添加长期记忆"""
        memory_id = str(uuid.uuid4())[:8]
        
        memory = MemoryItem(
            id=memory_id,
            content=content,
            memory_type=memory_type,
            timestamp=datetime.now().isoformat(),
            importance=importance,
            tags=tags or [],
            metadata=metadata or {}
        )
        
        self.memories[memory_id] = memory
        self._index(memory)
        self._save()
        
        return memory_id
    
    def get(self, memory_id: str) -> Optional[MemoryItem]:
        """获取单条记忆"""
        return self.memories.get(memory_id)
    
    def search_by_tag(self, tag: str) -> List[MemoryItem]:
        """按标签搜索"""
        memory_ids = self.index_by_tag.get(tag, [])
        return [self.memories[mid] for mid in memory_ids if mid in self.memories]
    
    def search_by_type(self, memory_type: str) -> List[MemoryItem]:
        """按类型搜索"""
        memory_ids = self.index_by_type.get(memory_type, [])
        return [self.memories[mid] for mid in memory_ids if mid in self.memories]
    
    def search_recent(self, hours: int = 24, limit: int = 20) -> List[MemoryItem]:
        """搜索最近记忆"""
        cutoff = datetime.now() - timedelta(hours=hours)
        recent = []
        
        for memory in self.memories.values():
            memory_time = datetime.fromisoformat(memory.timestamp)
            if memory_time > cutoff:
                recent.append(memory)
        
        # 按重要性和时间排序
        recent.sort(key=lambda x: (x.importance, x.timestamp), reverse=True)
        return recent[:limit]
    
    def search_semantic(self, query: str, top_k: int = 5) -> List[MemoryItem]:
        """语义搜索（简化版：关键词匹配）
        
        TODO: 接入Embedding模型实现真正的语义搜索
        """
        query_keywords = query.lower().split()
        scored_memories = []
        
        for memory in self.memories.values():
            content_lower = memory.content.lower()
            score = sum(1 for kw in query_keywords if kw in content_lower)
            if score > 0:
                scored_memories.append((score, memory))
        
        # 按相关性排序
        scored_memories.sort(key=lambda x: x[0], reverse=True)
        return [m for _, m in scored_memories[:top_k]]
    
    def update_importance(self, memory_id: str, importance: float):
        """更新记忆重要性"""
        if memory_id in self.memories:
            self.memories[memory_id].importance = importance
            self._save()
    
    def delete(self, memory_id: str) -> bool:
        """删除记忆"""
        if memory_id in self.memories:
            memory = self.memories[memory_id]
            del self.memories[memory_id]
            
            # 清理索引
            if memory.memory_type in self.index_by_type:
                self.index_by_type[memory.memory_type].remove(memory_id)
            
            for tag in memory.tags:
                if tag in self.index_by_tag:
                    if memory_id in self.index_by_tag[tag]:
                        self.index_by_tag[tag].remove(memory_id)
            
            self._save()
            return True
        return False
    
    def consolidate(self, from_short_term: List[MemoryItem]) -> int:
        """记忆巩固 - 将短期记忆转为长期记忆
        
        策略：
        - 高重要性记忆直接巩固
        - 中等重要性需要重复出现
        - 低重要性遗忘
        """
        consolidated = 0
        
        for memory in from_short_term:
            # 巩固策略
            if memory.importance >= 0.7:
                # 高重要性，直接巩固
                self.add(
                    content=memory.content,
                    memory_type="semantic",  # 转化为语义记忆
                    importance=memory.importance,
                    tags=memory.tags,
                    metadata=memory.metadata
                )
                consolidated += 1
            elif memory.importance >= 0.4:
                # 中等重要性，检查是否已存在
                existing = self.search_semantic(memory.content[:50])
                if not existing or len(existing) < 2:
                    # 首次或少数几次，暂不巩固
                    pass
                else:
                    # 多次出现，考虑巩固
                    self.add(
                        content=memory.content,
                        memory_type="episodic",
                        importance=memory.importance * 0.8,
                        tags=memory.tags + ["consolidated"]
                    )
                    consolidated += 1
        
        return consolidated
    
    def get_statistics(self) -> Dict:
        """获取记忆统计"""
        by_type = {}
        for m in self.memories.values():
            by_type[m.memory_type] = by_type.get(m.memory_type, 0) + 1
        
        return {
            "total_memories": len(self.memories),
            "by_type": by_type,
            "total_tags": len(self.index_by_tag),
            "avg_importance": sum(m.importance for m in self.memories.values()) / len(self.memories) if self.memories else 0
        }


class EpisodicMemory:
    """情景记忆 - 记录具体事件和经历
    
    用于记录每次分析的具体过程，支持回溯和反思
    """
    
    def __init__(self):
        self.episodes: Dict[str, Dict] = {}
    
    def add_episode(self, episode_id: str, event_data: Dict):
        """添加事件"""
        self.episodes[episode_id] = {
            "id": episode_id,
            "timestamp": datetime.now().isoformat(),
            "data": event_data
        }
    
    def get_episode(self, episode_id: str) -> Optional[Dict]:
        """获取事件"""
        return self.episodes.get(episode_id)
    
    def list_episodes(self, limit: int = 10) -> List[Dict]:
        """列出事件"""
        sorted_episodes = sorted(
            self.episodes.values(),
            key=lambda x: x["timestamp"],
            reverse=True
        )
        return sorted_episodes[:limit]
    
    def get_recent_episodes(self, hours: int = 24) -> List[Dict]:
        """获取最近事件"""
        cutoff = datetime.now() - timedelta(hours=hours)
        recent = []
        
        for episode in self.episodes.values():
            episode_time = datetime.fromisoformat(episode["timestamp"])
            if episode_time > cutoff:
                recent.append(episode)
        
        return sorted(recent, key=lambda x: x["timestamp"], reverse=True)


# 全局记忆管理器
class MemoryManager:
    """记忆管理器 - 统一管理所有类型的记忆"""
    
    def __init__(self, data_dir: str = "./data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.short_term = ShortTermMemory()
        self.long_term = LongTermMemory(str(self.data_dir / "long_term_memory.json"))
        self.episodic = EpisodicMemory()
    
    def remember(self, content: str, memory_type: str = "short_term",
                 importance: float = 0.5, tags: List[str] = None,
                 metadata: Dict = None) -> str:
        """记住信息"""
        if memory_type == "short_term":
            return self.short_term.add(content, importance, tags, metadata)
        else:
            return self.long_term.add(content, memory_type, importance, tags, metadata)
    
    def recall(self, query: str, memory_type: str = "all", 
               limit: int = 10) -> List[Dict]:
        """回忆信息"""
        results = []
        
        if memory_type in ["short_term", "all"]:
            recent = self.short_term.get_recent(limit)
            results.extend([m.to_dict() for m in recent])
        
        if memory_type in ["long_term", "semantic", "all"]:
            # 语义搜索
            semantic = self.long_term.search_semantic(query, limit)
            results.extend([m.to_dict() for m in semantic])
            
            # 标签搜索
            if query:
                tagged = self.long_term.search_by_tag(query)
                results.extend([m.to_dict() for m in tagged])
        
        # 去重
        seen = set()
        unique_results = []
        for r in results:
            if r["id"] not in seen:
                seen.add(r["id"])
                unique_results.append(r)
        
        return unique_results[:limit]
    
    def consolidate_memories(self):
        """记忆巩固 - 将重要的短期记忆转为长期记忆"""
        short_term_memories = self.short_term.get_all()
        if short_term_memories:
            consolidated = self.long_term.consolidate(
                [MemoryItem.from_dict(m) for m in short_term_memories]
            )
            # 清理已巩固的短期记忆
            self.short_term.clear()
            return consolidated
        return 0
    
    def get_context(self, task_description: str, max_tokens: int = 2000) -> List[Dict]:
        """获取上下文 - 为LLM准备相关记忆
        
        策略：
        1. 回忆与任务相关的历史记忆
        2. 限制总token数量
        3. 优先返回高重要性记忆
        """
        # 搜索相关记忆
        memories = self.recall(task_description, memory_type="long_term", limit=10)
        
        # 添加近期短期记忆
        recent_short = self.short_term.get_recent(5)
        memories.extend([m.to_dict() for m in recent_short])
        
        # 添加最近的事件
        recent_episodes = self.episodic.get_recent_episodes(hours=24)
        memories.extend(recent_episodes)
        
        # 按重要性和时间排序
        memories.sort(key=lambda x: (
            x.get("importance", 0.5) if "importance" in x else 0,
            x.get("timestamp", "")
        ), reverse=True)
        
        return memories[:20]  # 限制数量
    
    def get_statistics(self) -> Dict:
        """获取记忆统计"""
        return {
            "short_term": {
                "count": len(self.short_term.get_all()),
                "capacity": self.short_term.capacity
            },
            "long_term": self.long_term.get_statistics(),
            "episodic": {
                "count": len(self.episodic.episodes)
            }
        }


# 全局实例
_memory_manager = None

def get_memory_manager() -> MemoryManager:
    """获取记忆管理器单例"""
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager()
    return _memory_manager

def init_memory(data_dir: str = "./data"):
    """初始化记忆系统"""
    global _memory_manager
    _memory_manager = MemoryManager(data_dir)
    return _memory_manager
