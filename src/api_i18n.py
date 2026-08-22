"""
国际化API
提供语言切换和翻译查询接口
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any


router = APIRouter(prefix="/api/i18n", tags=["国际化"])


class LocaleRequest(BaseModel):
    locale: str


@router.get("/locales")
async def get_supported_locales():
    """获取支持的语言列表"""
    from src.i18n.manager import get_i18n
    
    i18n = get_i18n()
    locales = i18n.get_supported_locales()
    
    return {
        "locales": locales,
        "current_locale": i18n.get_locale().value,
        "locale_names": {
            "en": "English",
            "zh": "中文",
            "ja": "日本語"
        }
    }


@router.post("/set-locale")
async def set_locale(request: LocaleRequest):
    """设置当前语言"""
    from src.i18n.manager import get_i18n, Locale
    
    i18n = get_i18n()
    
    try:
        locale = Locale(request.locale)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的语言: {request.locale}，支持: {i18n.get_supported_locales()}"
        )
    
    success = i18n.set_locale(locale)
    if not success:
        raise HTTPException(status_code=400, detail="设置语言失败")
    
    return {
        "success": True,
        "locale": locale.value,
        "locale_name": i18n.get_locale_name(locale)
    }


@router.get("/translate")
async def translate_text(key: str, **kwargs):
    """翻译单个文本"""
    from src.i18n.manager import get_i18n
    
    i18n = get_i18n()
    result = i18n.t(key, **kwargs)
    
    return {
        "key": key,
        "locale": i18n.get_locale().value,
        "translation": result
    }


@router.get("/messages")
async def get_all_messages(category: str = None):
    """获取所有翻译消息"""
    from src.i18n.manager import get_i18n
    
    i18n = get_i18n()
    locale = i18n.get_locale().value
    
    if category:
        # 返回指定类别的消息
        messages = i18n.messages.get(locale, {})
        if category in messages:
            return {
                "locale": locale,
                "category": category,
                "messages": messages[category]
            }
        else:
            raise HTTPException(status_code=404, detail=f"类别 {category} 不存在")
    
    # 返回所有消息
    return {
        "locale": locale,
        "messages": i18n.messages.get(locale, {})
    }


@router.get("/compare")
async def compare_locales():
    """比较不同语言的翻译覆盖情况"""
    from src.i18n.manager import get_i18n
    
    i18n = get_i18n()
    
    # 统计每种语言的翻译数量
    stats = {}
    for locale in i18n.get_supported_locales():
        messages = i18n.messages.get(locale, {})
        total_keys = _count_keys(messages)
        stats[locale] = {
            "total_keys": total_keys,
            "coverage": f"{total_keys / _count_keys(i18n.messages.get('en', {})) * 100:.1f}%"
        }
    
    return {
        "stats": stats,
        "current_locale": i18n.get_locale().value
    }


def _count_keys(d: dict) -> int:
    """递归计算字典中的键数量"""
    count = 0
    for value in d.values():
        if isinstance(value, dict):
            count += _count_keys(value)
        else:
            count += 1
    return count
