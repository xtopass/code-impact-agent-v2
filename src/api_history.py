"""
分析历史 API
提供分析记录的增删查和统计
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any


router = APIRouter(prefix="/api/history", tags=["分析历史"])


class HistoryFilter(BaseModel):
    keyword: str = ""
    risk_level: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    limit: int = 50
    offset: int = 0


@router.get("")
async def list_history(filter: HistoryFilter = None):
    """列出分析历史"""
    from src.learning.engine import get_learning_engine
    engine = get_learning_engine()

    cases = engine.cases
    results = []

    for case in cases:
        d = case.to_dict()
        # 关键词过滤
        if filter and filter.keyword:
            kw = filter.keyword.lower()
            if kw not in d.get("target_file", "").lower() and kw not in d.get("case_id", "").lower():
                continue
        # 风险等级过滤
        if filter and filter.risk_level and d.get("risk_level") != filter.risk_level:
            continue
        # 日期过滤
        if filter and filter.date_from:
            if d.get("timestamp", "") < filter.date_from:
                continue
        if filter and filter.date_to:
            if d.get("timestamp", "") > filter.date_to:
                continue
        results.append(d)

    # 按时间倒序
    results.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    total = len(results)
    return {
        "cases": results[filter.offset:filter.offset + filter.limit] if filter else results,
        "total": total,
        "limit": filter.limit if filter else 50,
        "offset": filter.offset if filter else 0
    }


@router.get("/stats")
async def get_history_stats():
    """分析历史统计"""
    from src.learning.engine import get_learning_engine
    engine = get_learning_engine()
    stats = engine.analyze_patterns()
    return stats


@router.delete("/{case_id}")
async def delete_history(case_id: str):
    """删除历史记录"""
    from src.learning.engine import get_learning_engine
    engine = get_learning_engine()
    engine.cases = [c for c in engine.cases if c.case_id != case_id]
    engine._save_data()
    return {"success": True}


@router.post("/export")
async def export_history():
    """导出全部历史"""
    from src.learning.engine import get_learning_engine
    engine = get_learning_engine()
    return {"cases": [c.to_dict() for c in engine.cases], "total": len(engine.cases)}
