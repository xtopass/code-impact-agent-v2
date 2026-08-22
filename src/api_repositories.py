"""
代码库管理API
提供多仓库、多平台的REST接口
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any


router = APIRouter(prefix="/api/repositories", tags=["代码库管理"])


class PlatformConfigRequest(BaseModel):
    platform: str
    api_url: str
    token: str
    username: Optional[str] = None


class RepositoryRequest(BaseModel):
    name: str
    platform: str
    owner: str
    repo_path: str
    local_path: Optional[str] = None
    branch: str = "main"


class RepositoryUpdate(BaseModel):
    name: Optional[str] = None
    branch: Optional[str] = None
    local_path: Optional[str] = None
    enabled: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None


@router.get("/platforms")
async def list_platforms():
    """列出所有Git平台配置"""
    from src.repositories.manager import get_repository_manager
    rm = get_repository_manager()
    return rm.list_platforms()


@router.post("/platforms")
async def add_platform(config: PlatformConfigRequest):
    """添加Git平台配置"""
    from src.repositories.manager import get_repository_manager, PlatformConfig, GitPlatform
    
    rm = get_repository_manager()
    
    try:
        platform = GitPlatform(config.platform)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"不支持的平台: {config.platform}")
    
    platform_config = PlatformConfig(
        platform=platform,
        api_url=config.api_url,
        token=config.token,
        username=config.username
    )
    
    # 平台唯一键：platform + api_url（支持同一平台多个私有实例）
    unique_key = f"{platform.value}_{config.api_url}"
    if rm.get_platform(unique_key):
        raise HTTPException(status_code=400, detail="该平台地址已配置")
    
    success = rm.add_platform(unique_key, platform_config)
    if not success:
        raise HTTPException(status_code=400, detail="平台配置已存在")
    
    return {"success": True, "message": "平台配置已添加"}


@router.delete("/platforms/{platform_id}")
async def remove_platform(platform_id: str):
    """移除平台配置"""
    from src.repositories.manager import get_repository_manager
    rm = get_repository_manager()
    
    try:
        rm.remove_platform(platform_id)
        return {"success": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("")
async def list_repositories(
    platform: Optional[str] = None,
    enabled_only: bool = True
):
    """列出所有代码库"""
    from src.repositories.manager import get_repository_manager, GitPlatform
    
    rm = get_repository_manager()
    
    filter_platform = GitPlatform(platform) if platform else None
    repositories = rm.list_repositories(
        platform=filter_platform,
        enabled_only=enabled_only
    )
    
    return [repo.to_dict() for repo in repositories]


@router.post("")
async def add_repository(req: RepositoryRequest):
    """添加代码库"""
    from src.repositories.manager import get_repository_manager, CodeRepository, GitPlatform
    import uuid
    
    rm = get_repository_manager()
    
    try:
        platform = GitPlatform(req.platform)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"不支持的平台: {req.platform}")

    repo = CodeRepository(
        id=str(uuid.uuid4())[:12],
        name=req.name,
        platform=platform,
        owner=req.owner,
        repo_path=req.repo_path,
        local_path=req.local_path,
        branch=req.branch
    )

    try:
        repo_id = rm.add_repository(repo)
        return {"success": True, "repository_id": repo_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{repo_id}")
async def get_repository(repo_id: str):
    """获取代码库详情"""
    from src.repositories.manager import get_repository_manager
    rm = get_repository_manager()
    
    repo = rm.get_repository(repo_id)
    if not repo:
        raise HTTPException(status_code=404, detail="代码库不存在")
    
    return repo.to_dict()


@router.put("/{repo_id}")
async def update_repository(repo_id: str, updates: RepositoryUpdate):
    """更新代码库"""
    from src.repositories.manager import get_repository_manager
    rm = get_repository_manager()
    
    if not rm.get_repository(repo_id):
        raise HTTPException(status_code=404, detail="代码库不存在")
    
    rm.update_repository(repo_id, updates.dict(exclude_none=True))
    return {"success": True}


@router.delete("/{repo_id}")
async def delete_repository(repo_id: str):
    """删除代码库"""
    from src.repositories.manager import get_repository_manager
    rm = get_repository_manager()
    
    if not rm.remove_repository(repo_id):
        raise HTTPException(status_code=404, detail="代码库不存在")
    
    return {"success": True}


@router.post("/{repo_id}/clone")
async def clone_repository(repo_id: str):
    """克隆代码库到本地"""
    from src.repositories.manager import get_repository_manager
    rm = get_repository_manager()
    
    result = rm.clone_repository(repo_id)
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    
    return result


@router.post("/{repo_id}/analyze")
async def analyze_repository(repo_id: str):
    """触发代码库分析"""
    from src.repositories.manager import get_repository_manager
    rm = get_repository_manager()
    
    result = rm.analyze_repository(repo_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    
    return result


@router.get("/search")
async def search_repositories(keyword: str):
    """搜索代码库"""
    from src.repositories.manager import get_repository_manager
    rm = get_repository_manager()
    
    repositories = rm.search_repositories(keyword)
    return [repo.to_dict() for repo in repositories]


@router.get("/stats")
async def get_statistics():
    """获取代码库统计"""
    from src.repositories.manager import get_repository_manager
    rm = get_repository_manager()
    
    return rm.get_statistics()


@router.get("/platforms/{platform_id}/repositories")
async def list_platform_repositories(platform_id: str):
    """列出指定平台的所有仓库"""
    from src.repositories.manager import get_repository_manager, GitPlatform
    
    rm = get_repository_manager()
    
    try:
        platform = GitPlatform(platform_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的平台ID")
    
    repositories = rm.list_repositories(platform=platform)
    return [repo.to_dict() for repo in repositories]
