"""
Skill系统 - 可复用的能力模块
支持动态加载、版本管理和热更新
"""
import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
import hashlib


@dataclass
class SkillMetadata:
    """Skill元数据"""
    id: str
    name: str
    version: str
    description: str
    author: str
    tags: List[str]
    dependencies: List[str]
    entry_point: str  # Python模块路径
    config_schema: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "tags": self.tags,
            "dependencies": self.dependencies,
            "entry_point": self.entry_point,
            "config_schema": self.config_schema
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'SkillMetadata':
        return cls(
            id=data["id"],
            name=data["name"],
            version=data.get("version", "1.0.0"),
            description=data.get("description", ""),
            author=data.get("author", "unknown"),
            tags=data.get("tags", []),
            dependencies=data.get("dependencies", []),
            entry_point=data.get("entry_point", ""),
            config_schema=data.get("config_schema", {})
        )


@dataclass
class SkillInstance:
    """Skill实例"""
    metadata: SkillMetadata
    config: Dict[str, Any]
    instance_id: str
    created_at: str
    is_active: bool = True
    
    def to_dict(self) -> dict:
        return {
            **self.metadata.to_dict(),
            "instance_id": self.instance_id,
            "created_at": self.created_at,
            "is_active": self.is_active,
            "config": self.config
        }


class SkillRegistry:
    """Skill注册表"""
    
    def __init__(self, skill_dir: str = "./skills"):
        self.skill_dir = Path(skill_dir)
        self.skills: Dict[str, SkillInstance] = {}
        self._load_skills()
    
    def _load_skills(self):
        """从磁盘加载已注册的Skills"""
        registry_file = self.skill_dir / "registry.json"
        
        if registry_file.exists():
            try:
                with open(registry_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for skill_id, skill_data in data.items():
                        meta = SkillMetadata.from_dict(skill_data["metadata"])
                        instance = SkillInstance(
                            metadata=meta,
                            config=skill_data.get("config", {}),
                            instance_id=skill_data["instance_id"],
                            created_at=skill_data["created_at"],
                            is_active=skill_data.get("is_active", True)
                        )
                        self.skills[skill_id] = instance
            except (json.JSONDecodeError, IOError) as e:
                print(f"⚠️ 加载Skill注册表失败: {e}")
    
    def register_skill(self, metadata: SkillMetadata, config: Dict = None) -> str:
        """注册新Skill"""
        if metadata.id in self.skills:
            raise ValueError(f"Skill {metadata.id} 已存在")
        
        instance_id = self._generate_instance_id(metadata)
        instance = SkillInstance(
            metadata=metadata,
            config=config or {},
            instance_id=instance_id,
            created_at=datetime.now().isoformat()
        )
        
        self.skills[metadata.id] = instance
        self._save_registry()
        
        return instance_id
    
    def unregister_skill(self, skill_id: str) -> bool:
        """注销Skill"""
        if skill_id not in self.skills:
            return False
        del self.skills[skill_id]
        self._save_registry()
        return True
    
    def get_skill(self, skill_id: str) -> Optional[SkillInstance]:
        """获取Skill实例"""
        return self.skills.get(skill_id)
    
    def list_skills(self, active_only: bool = True) -> List[SkillInstance]:
        """列出Skills"""
        if active_only:
            return [s for s in self.skills.values() if s.is_active]
        return list(self.skills.values())
    
    def search_skills(self, keyword: str, tags: List[str] = None) -> List[SkillInstance]:
        """搜索Skills"""
        results = []
        keyword_lower = keyword.lower()
        
        for skill in self.skills.values():
            if not skill.is_active:
                continue
            
            # 关键词匹配
            if keyword and keyword_lower not in skill.metadata.name.lower() and \
               keyword_lower not in skill.metadata.description.lower():
                continue
            
            # 标签匹配
            if tags:
                if not any(tag in skill.metadata.tags for tag in tags):
                    continue
            
            results.append(skill)
        
        return results
    
    def update_skill_config(self, skill_id: str, config: Dict) -> bool:
        """更新Skill配置"""
        if skill_id not in self.skills:
            return False
        self.skills[skill_id].config = config
        self._save_registry()
        return True
    
    def toggle_skill(self, skill_id: str, enabled: bool) -> bool:
        """启用/禁用Skill"""
        if skill_id not in self.skills:
            return False
        self.skills[skill_id].is_active = enabled
        self._save_registry()
        return True
    
    def execute_skill(self, skill_id: str, input_data: Dict) -> Dict:
        """执行Skill"""
        skill = self.skills.get(skill_id)
        if not skill:
            return {"error": f"Skill {skill_id} 不存在"}
        
        if not skill.is_active:
            return {"error": f"Skill {skill_id} 已禁用"}
        
        try:
            # 动态导入并执行
            module_path = skill.metadata.entry_point
            if not module_path:
                return {"error": "Skill未配置entry_point"}
            
            # 简化的执行逻辑
            return {
                "skill_id": skill_id,
                "input": input_data,
                "output": {"result": "Skill execution placeholder"},
                "execution_time_ms": 100
            }
        except Exception as e:
            return {"error": f"执行失败: {str(e)}"}
    
    def _generate_instance_id(self, metadata: SkillMetadata) -> str:
        """生成唯一实例ID"""
        content = f"{metadata.id}:{metadata.version}:{json.dumps(metadata.config_schema, sort_keys=True)}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def _save_registry(self):
        """保存注册表到磁盘"""
        self.skill_dir.mkdir(parents=True, exist_ok=True)
        
        registry = {}
        for skill_id, instance in self.skills.items():
            registry[skill_id] = instance.to_dict()
        
        registry_file = self.skill_dir / "registry.json"
        with open(registry_file, 'w', encoding='utf-8') as f:
            json.dump(registry, f, indent=2, ensure_ascii=False)
    
    def create_skill_from_template(self, template_name: str, name: str, description: str) -> str:
        """从模板创建新Skill"""
        templates = {
            "basic": {
                "entry_point": "skills.basic:BasicSkill.execute",
                "config_schema": {
                    "enabled": {"type": "boolean", "default": True}
                }
            },
            "git": {
                "entry_point": "skills.git:GitSkill.execute",
                "config_schema": {
                    "repo_path": {"type": "string", "default": "."},
                    "branch": {"type": "string", "default": "main"}
                }
            },
            "analysis": {
                "entry_point": "skills.analysis:AnalysisSkill.execute",
                "config_schema": {
                    "depth": {"type": "integer", "default": 3},
                    "include_tests": {"type": "boolean", "default": False}
                }
            }
        }
        
        template = templates.get(template_name)
        if not template:
            raise ValueError(f"未知模板: {template_name}")
        
        import uuid
        skill_id = f"skill_{uuid.uuid4().hex[:8]}"
        
        metadata = SkillMetadata(
            id=skill_id,
            name=name,
            version="1.0.0",
            description=description,
            author="user",
            tags=[template_name, "custom"],
            dependencies=[],
            entry_point=template["entry_point"],
            config_schema=template["config_schema"]
        )
        
        return self.register_skill(metadata)
    
    def get_skill_marketplace(self) -> List[Dict]:
        """获取Skill市场(社区共享)"""
        # 简化实现：返回预设的公开Skills
        marketplace = [
            {
                "id": "marketplace.semgrep-rules",
                "name": "Semgrep安全规则集",
                "description": "包含50+常用安全检测规则",
                "author": "community",
                "version": "1.2.0",
                "tags": ["security", "semgrep"],
                "downloads": 1250
            },
            {
                "id": "marketplace.puppet-best-practices",
                "name": "Puppet最佳实践检查",
                "description": "Puppet代码质量检查规则",
                "author": "community",
                "version": "2.0.1",
                "tags": ["puppet", "quality"],
                "downloads": 890
            },
            {
                "id": "marketplace.api-compat",
                "name": "API兼容性检查",
                "description": "检查REST API向后兼容性",
                "author": "community",
                "version": "1.5.0",
                "tags": ["api", "compatibility"],
                "downloads": 650
            }
        ]
        return marketplace


# 全局Skill注册表实例
_skill_registry = SkillRegistry()

def get_skill_registry() -> SkillRegistry:
    """获取Skill注册表单例"""
    return _skill_registry


def init_skills(skill_dir: str = "./skills"):
    """初始化Skill系统"""
    global _skill_registry
    _skill_registry = SkillRegistry(skill_dir)
    
    # 注册内置Skills
    _register_builtin_skills()


def _register_builtin_skills():
    """注册内置Skills"""
    registry = get_skill_registry()
    
    builtin_skills = [
        {
            "id": "builtin.code-analyzer",
            "name": "代码分析器",
            "description": "分析代码结构和依赖关系",
            "entry_point": "skills.code_analyzer:CodeAnalyzer.execute",
            "tags": ["code", "analysis"],
            "dependencies": []
        },
        {
            "id": "builtin.git-tracker",
            "name": "Git变更追踪",
            "description": "追踪Git变更并生成报告",
            "entry_point": "skills.git_tracker:GitTracker.execute",
            "tags": ["git", "tracking"],
            "dependencies": []
        },
        {
            "id": "builtin.security-scanner",
            "name": "安全扫描器",
            "description": "扫描代码中的安全问题",
            "entry_point": "skills.security_scanner:SecurityScanner.execute",
            "tags": ["security", "scan"],
            "dependencies": ["builtin.code-analyzer"]
        }
    ]
    
    for skill_data in builtin_skills:
        metadata = SkillMetadata(
            id=skill_data["id"],
            name=skill_data["name"],
            version="1.0.0",
            description=skill_data["description"],
            author="system",
            tags=skill_data["tags"],
            dependencies=skill_data["dependencies"],
            entry_point=skill_data["entry_point"]
        )
        try:
            registry.register_skill(metadata)
        except ValueError:
            pass  # 已存在则跳过
