"""
代码库管理器
支持多个代码库、多Git平台（GitHub/GitLab/本地）
"""
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import uuid


class GitPlatform(str, Enum):
    """Git平台类型"""
    GITHUB = "github"
    GITLAB = "gitlab"
    LOCAL = "local"
    BITBUCKET = "bitbucket"
    GITEA = "gitea"


@dataclass
class PlatformConfig:
    """平台配置"""
    platform: GitPlatform
    api_url: str  # 如 https://github.com 或 https://gitlab.example.com
    token: str
    username: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "platform": self.platform.value,
            "api_url": self.api_url,
            "token_set": bool(self.token),
            "username": self.username
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'PlatformConfig':
        config = cls(
            platform=GitPlatform(data["platform"]),
            api_url=data["api_url"],
            token=data.get("token", ""),
            username=data.get("username")
        )
        return config


@dataclass
class CodeRepository:
    """代码库配置"""
    id: str
    name: str
    platform: GitPlatform
    owner: str  # GitHub用户名或GitLab组/用户
    repo_path: str  # 仓库路径，如 xtopass/code-impact-agent
    local_path: Optional[str] = None  # 本地克隆路径
    branch: str = "main"
    enabled: bool = True
    created_at: str = ""
    last_analyzed: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.created_at:
            from datetime import datetime
            self.created_at = datetime.now().isoformat()
    
    def full_url(self) -> str:
        """获取完整URL"""
        base_url = self._get_base_url()
        return f"{base_url}/{self.owner}/{self.repo_path}"
    
    def _get_base_url(self) -> str:
        """获取平台基础URL"""
        urls = {
            GitPlatform.GITHUB: "https://github.com",
            GitPlatform.GITLAB: "https://gitlab.com",
            GitPlatform.LOCAL: "",
            GitPlatform.BITBUCKET: "https://bitbucket.org",
            GitPlatform.GITEA: "https://gitea.com"
        }
        return urls.get(self.platform, "")
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "platform": self.platform.value,
            "owner": self.owner,
            "repo_path": self.repo_path,
            "local_path": self.local_path,
            "branch": self.branch,
            "enabled": self.enabled,
            "created_at": self.created_at,
            "last_analyzed": self.last_analyzed,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'CodeRepository':
        repo = cls(
            id=data["id"],
            name=data["name"],
            platform=GitPlatform(data["platform"]),
            owner=data["owner"],
            repo_path=data["repo_path"],
            local_path=data.get("local_path"),
            branch=data.get("branch", "main"),
            enabled=data.get("enabled", True),
            created_at=data.get("created_at", ""),
            last_analyzed=data.get("last_analyzed"),
            metadata=data.get("metadata", {})
        )
        return repo


class RepositoryManager:
    """代码库管理器 - 管理多个代码库和多平台"""
    
    def __init__(self, config_path: str = "./data/repositories.json"):
        self.config_path = Path(config_path)
        self.repositories: Dict[str, CodeRepository] = {}
        self.platform_configs: Dict[str, PlatformConfig] = {}
        self._load()
    
    def _load(self):
        """加载配置"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                # 加载平台配置
                for platform_id, config_data in data.get("platforms", {}).items():
                    self.platform_configs[platform_id] = PlatformConfig.from_dict(config_data)
                
                # 加载代码库
                for repo_data in data.get("repositories", []):
                    repo = CodeRepository.from_dict(repo_data)
                    self.repositories[repo.id] = repo
                    
            except (json.JSONDecodeError, IOError) as e:
                print(f"⚠️ 加载代码库配置失败: {e}")
    
    def _save(self):
        """保存配置"""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            "platforms": {
                pid: config.to_dict() 
                for pid, config in self.platform_configs.items()
            },
            "repositories": [repo.to_dict() for repo in self.repositories.values()]
        }
        
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    # ============ 平台管理 ============
    
    def add_platform(self, platform_id: str, config: PlatformConfig) -> bool:
        """添加Git平台配置"""
        if platform_id in self.platform_configs:
            return False
        self.platform_configs[platform_id] = config
        self._save()
        return True
    
    def remove_platform(self, platform_id: str) -> bool:
        """移除平台配置"""
        if platform_id not in self.platform_configs:
            return False
        
        # 检查是否有仓库使用该平台
        using_repos = [r for r in self.repositories.values() 
                      if r.platform.value == platform_id]
        if using_repos:
            raise ValueError(f"平台 {platform_id} 还有 {len(using_repos)} 个仓库在使用")
        
        del self.platform_configs[platform_id]
        self._save()
        return True
    
    def get_platform(self, platform_id: str) -> Optional[PlatformConfig]:
        """获取平台配置"""
        return self.platform_configs.get(platform_id)
    
    def list_platforms(self) -> List[Dict]:
        """列出所有平台"""
        return [config.to_dict() for config in self.platform_configs.values()]
    
    # ============ 代码库管理 ============
    
    def add_repository(self, repo: CodeRepository) -> str:
        """添加代码库"""
        if repo.id in self.repositories:
            raise ValueError(f"代码库 {repo.id} 已存在")
        
        # 验证平台配置
        if repo.platform != GitPlatform.LOCAL:
            platform_key = f"{repo.platform.value}_{repo.owner}"
            if platform_key not in self.platform_configs:
                raise ValueError(f"请先配置平台: {platform_key}")
        
        self.repositories[repo.id] = repo
        self._save()
        return repo.id
    
    def remove_repository(self, repo_id: str) -> bool:
        """移除代码库"""
        if repo_id not in self.repositories:
            return False
        del self.repositories[repo_id]
        self._save()
        return True
    
    def get_repository(self, repo_id: str) -> Optional[CodeRepository]:
        """获取代码库"""
        return self.repositories.get(repo_id)
    
    def list_repositories(self, platform: GitPlatform = None, 
                         enabled_only: bool = True) -> List[CodeRepository]:
        """列出代码库"""
        repos = list(self.repositories.values())
        
        if platform:
            repos = [r for r in repos if r.platform == platform]
        
        if enabled_only:
            repos = [r for r in repos if r.enabled]
        
        return repos
    
    def search_repositories(self, keyword: str) -> List[CodeRepository]:
        """搜索代码库"""
        keyword_lower = keyword.lower()
        return [
            repo for repo in self.repositories.values()
            if keyword_lower in repo.name.lower() or 
               keyword_lower in repo.repo_path.lower() or
               keyword_lower in repo.owner.lower()
        ]
    
    def update_repository(self, repo_id: str, updates: Dict) -> bool:
        """更新代码库"""
        if repo_id not in self.repositories:
            return False
        
        repo = self.repositories[repo_id]
        for key, value in updates.items():
            if hasattr(repo, key):
                setattr(repo, key, value)
        
        self._save()
        return True
    
    def analyze_repository(self, repo_id: str) -> Dict:
        """分析代码库（触发分析）"""
        repo = self.repositories.get(repo_id)
        if not repo:
            return {"error": "代码库不存在"}
        
        # 更新最后分析时间
        from datetime import datetime
        repo.last_analyzed = datetime.now().isoformat()
        self._save()
        
        return {
            "success": True,
            "repository": repo.to_dict(),
            "message": f"已触发对 {repo.name} 的分析"
        }
    
    # ============ 批量操作 ============
    
    def clone_repository(self, repo_id: str, local_path: str = None) -> Dict:
        """克隆代码库到本地"""
        repo = self.repositories.get(repo_id)
        if not repo:
            return {"error": "代码库不存在"}
        
        if repo.platform == GitPlatform.LOCAL:
            return {
                "success": True,
                "path": repo.local_path,
                "message": "本地仓库，无需克隆"
            }
        
        # 确定本地路径
        if not local_path:
            local_path = repo.local_path or f"./repos/{repo.id}"
        
        # 执行克隆
        import subprocess
        try:
            # 获取克隆URL
            clone_url = self._get_clone_url(repo)
            
            # 克隆仓库
            result = subprocess.run(
                ["git", "clone", "--depth", "1", clone_url, local_path],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                # 更新本地路径
                repo.local_path = local_path
                self._save()
                return {
                    "success": True,
                    "path": local_path,
                    "message": "克隆成功"
                }
            else:
                return {
                    "error": f"克隆失败: {result.stderr}"
                }
        
        except Exception as e:
            return {"error": str(e)}
    
    def _get_clone_url(self, repo: CodeRepository) -> str:
        """获取克隆URL（优先使用平台配置的 api_url）"""
        # 查找匹配的平台配置
        platform_key = f"{repo.platform.value}_"
        matching_configs = [
            cfg for cfg in self.platform_configs.values()
            if cfg.platform == repo.platform
        ]
        primary_url = matching_configs[0].api_url if matching_configs else ""

        if repo.platform == GitPlatform.LOCAL:
            return repo.local_path or ""

        # 私有实例优先使用配置的 api_url
        if primary_url and repo.platform != GitPlatform.GITHUB:
            # 去掉末尾斜杠，拼接 owner/repo
            base = primary_url.rstrip("/")
            return f"{base}/{repo.owner}/{repo.repo_path}.git"

        # 公共实例默认 URL
        defaults = {
            GitPlatform.GITHUB: "https://github.com",
            GitPlatform.GITLAB: "https://gitlab.com",
            GitPlatform.BITBUCKET: "https://bitbucket.org",
            GitPlatform.GITEA: "https://gitea.com",
        }
        base = defaults.get(repo.platform, "")
        return f"{base}/{repo.owner}/{repo.repo_path}.git" if base else ""
    
    # ============ 统计信息 ============
    
    def get_statistics(self) -> Dict:
        """获取统计信息"""
        by_platform = {}
        for repo in self.repositories.values():
            platform = repo.platform.value
            by_platform[platform] = by_platform.get(platform, 0) + 1
        
        return {
            "total_repositories": len(self.repositories),
            "enabled_repositories": sum(1 for r in self.repositories.values() if r.enabled),
            "by_platform": by_platform,
            "platforms_configured": len(self.platform_configs)
        }


# 全局实例
_repository_manager = None

def get_repository_manager() -> RepositoryManager:
    """获取代码库管理器单例"""
    global _repository_manager
    if _repository_manager is None:
        _repository_manager = RepositoryManager()
    return _repository_manager

def init_repositories(config_path: str = "./data/repositories.json"):
    """初始化代码库管理器"""
    global _repository_manager
    _repository_manager = RepositoryManager(config_path)
    return _repository_manager
