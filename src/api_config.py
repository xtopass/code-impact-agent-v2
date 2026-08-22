"""
配置管理API
处理Web界面的配置保存和读取
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
import json
import os
from pathlib import Path


router = APIRouter(prefix="/api/config", tags=["配置管理"])

CONFIG_FILE = Path(".env")


class GitHubConfig(BaseModel):
    token: str
    username: str
    skip: bool = False


class LLMConfig(BaseModel):
    provider: str
    api_key: str
    model: str
    base_url: str = ""      # 自定义 provider 用，OpenAI 兼容格式
    skip: bool = False


class ServerConfig(BaseModel):
    api_port: int = 3000
    web_port: int = 5173
    data_dir: str = "./data"


class FullConfig(BaseModel):
    github: GitHubConfig
    llm: LLMConfig
    server: ServerConfig


@router.get("/status")
async def get_config_status():
    """获取配置状态"""
    env_content = ""
    has_env = False
    try:
        if CONFIG_FILE.exists():
            has_env = True
            env_content = CONFIG_FILE.read_text()
    except Exception:
        pass

    has_github = has_env and "GITHUB_TOKEN" in env_content
    has_llm = has_env and any(k in env_content for k in [
        "DEEPSEEK_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "ZHIPU_API_KEY"
    ])

    return {
        "github_configured": has_github,
        "llm_configured": has_llm,
        "has_env_file": has_env,
        "setup_completed": has_github and has_llm
    }


@router.post("/save")
async def save_config(full_config: FullConfig):
    """保存完整配置"""
    try:
        # 读取现有.env文件
        env_content = ""
        if CONFIG_FILE.exists():
            env_content = CONFIG_FILE.read_text()
        
        # 构建新的配置
        lines = []
        
        # GitHub配置
        if not full_config.github.skip:
            lines.append(f"GITHUB_TOKEN={full_config.github.token}")
            lines.append(f"GITHUB_USERNAME={full_config.github.username}")
        
        # LLM配置
        if not full_config.llm.skip:
            provider_key = full_config.llm.provider.upper()
            lines.append(f"{provider_key}_API_KEY={full_config.llm.api_key}")
            lines.append(f"LLM_PROVIDER={full_config.llm.provider}")
            lines.append(f"LLM_MODEL={full_config.llm.model}")
            if full_config.llm.base_url:
                lines.append(f"LLM_BASE_URL={full_config.llm.base_url}")
        
        # 服务配置
        lines.append(f"PORT={full_config.server.api_port}")
        lines.append(f"WEB_PORT={full_config.server.web_port}")
        lines.append(f"DATA_DIR={full_config.server.data_dir}")
        
        # 写入文件
        new_content = "\n".join(lines)
        CONFIG_FILE.write_text(new_content)
        
        return {
            "success": True,
            "message": "配置已保存",
            "config": {
                "github": {"configured": not full_config.github.skip},
                "llm": {"configured": not full_config.llm.skip},
                "server": full_config.server.dict()
            }
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/validate/github")
async def validate_github_token(token: str):
    """验证GitHub Token"""
    try:
        import urllib.request
        req = urllib.request.Request(
            "https://api.github.com/user",
            headers={"Authorization": f"token {token}"}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read())
            return {
                "valid": True,
                "username": data.get("login"),
                "message": "Token有效"
            }
    except Exception as e:
        return {
            "valid": False,
            "message": str(e)
        }


@router.get("/validate/llm")
async def validate_llm_config(provider: str, api_key: str, base_url: str = ""):
    """验证LLM API Key"""
    try:
        if provider == "deepseek":
            import urllib.request
            req = urllib.request.Request(
                "https://api.deepseek.com/chat/completions",
                data=json.dumps({
                    "model": "deepseek-chat",
                    "messages": [{"role": "user", "content": "hi"}],
                    "max_tokens": 1
                }).encode(),
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                json.loads(response.read())
                return {"valid": True, "message": "API Key有效"}

        elif provider == "openai":
            import urllib.request
            req = urllib.request.Request(
                "https://api.openai.com/v1/chat/completions",
                data=json.dumps({
                    "model": "gpt-4o-mini",
                    "messages": [{"role": "user", "content": "hi"}],
                    "max_tokens": 1
                }).encode(),
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                json.loads(response.read())
                return {"valid": True, "message": "API Key有效"}

        elif provider == "custom" and base_url:
            # 自定义 OpenAI 兼容格式
            import urllib.request
            url = f"{base_url.rstrip('/')}/chat/completions"
            req = urllib.request.Request(
                url,
                data=json.dumps({
                    "model": "gpt-4o-mini",
                    "messages": [{"role": "user", "content": "hi"}],
                    "max_tokens": 1
                }).encode(),
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                json.loads(response.read())
                return {"valid": True, "message": "API Key有效"}

        return {"valid": False, "message": "暂不支持此提供商的验证"}

    except Exception as e:
        return {"valid": False, "message": f"验证失败: {str(e)}"}


@router.get("/providers")
async def get_llm_providers():
    """获取支持的LLM提供商列表"""
    return [
        {
            "id": "deepseek",
            "name": "DeepSeek",
            "icon": "fas fa-bolt",
            "description": "性价比高，¥1.5/百万token",
            "recommended": True,
            "models": ["deepseek-chat", "deepseek-coder"]
        },
        {
            "id": "openai",
            "name": "OpenAI",
            "icon": "fas fa-circle",
            "description": "GPT-4o，功能强大",
            "models": ["gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo"]
        },
        {
            "id": "anthropic",
            "name": "Anthropic",
            "icon": "fas fa-comment",
            "description": "Claude，推理能力强",
            "models": ["claude-3-5-sonnet-20241022", "claude-3-opus-20240229"]
        },
        {
            "id": "zhipu",
            "name": "智谱AI",
            "icon": "fas fa-graduation-cap",
            "description": "GLM-4，国产优秀",
            "models": ["glm-4", "glm-4-plus"]
        },
        {
            "id": "custom",
            "name": "自定义 (OpenAI兼容)",
            "icon": "fas fa-puzzle-piece",
            "description": "vLLM / LocalAI / Ollama 等任意 OpenAI 格式 API",
            "models": [],
            "requires_base_url": True,
        },
    ]


@router.post("/import-env")
async def import_from_env(file_content: str):
    """从.env文件内容导入配置"""
    try:
        config = {}
        for line in file_content.strip().split('\n'):
            line = line.strip()
            if line.startswith('#') or '=' not in line:
                continue
            key, value = line.split('=', 1)
            config[key.strip()] = value.strip()
        
        return {
            "success": True,
            "parsed": config
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
