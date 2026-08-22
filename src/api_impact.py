"""
影响链分析 API
提供代码影响范围调查的 REST 接口
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import time


router = APIRouter(prefix="/api/impact", tags=["影响链分析"])


class ImpactChainRequest(BaseModel):
    """影响链分析请求"""
    change_description: str          # 变更描述（自然语言）
    file_path: Optional[str] = ""    # 变更文件路径
    code_context: Optional[str] = "" # 代码上下文（可选，提高准确率）
    analysis_depth: str = "medium"   # shallow | medium | deep
    project_name: Optional[str] = ""
    audience: str = "developers"     # developers | managers | stakeholders


class DbFieldImpactRequest(BaseModel):
    """数据库字段变更影响请求"""
    change_description: str
    table_name: str
    field_name: str
    field_change: str                # 例如：varchar(50) -> varchar(100)
    tech_stack: Optional[str] = ""   # 例如：Django/SQLAlchemy/FastAPI
    analysis_depth: str = "medium"
    project_name: Optional[str] = ""
    audience: str = "developers"


@router.post("/chain")
async def analyze_impact_chain(req: ImpactChainRequest):
    """分析代码变更影响链"""
    from src.llm.client import get_llm_client, is_llm_enabled
    from src.llm.prompts import render_prompt
    import json

    if not is_llm_enabled():
        raise HTTPException(status_code=503, detail="LLM 未配置，无法执行影响链分析")

    start_time = time.time()
    client = get_llm_client()

    try:
        # 第一步：结构化影响链分析
        messages = render_prompt("impact_chain_analysis",
                                 change_description=req.change_description,
                                 file_path=req.file_path or "N/A",
                                 code_context=req.code_context or "",
                                 analysis_depth=req.analysis_depth)

        raw_result = client.chat(messages)

        # 解析 JSON
        impact_data = _parse_json_result(raw_result)

        # 第二步：生成自然语言报告
        report = client.chat(render_prompt("impact_report_generation",
                                           file_path=req.file_path or "N/A",
                                           analysis_depth=req.analysis_depth,
                                           project_name=req.project_name or "Unknown Project",
                                           audience=req.audience,
                                           analysis_result=json.dumps(impact_data, ensure_ascii=False, indent=2)))

        execution_time = int((time.time() - start_time) * 1000)

        return {
            "success": True,
            "impact_data": impact_data,
            "report": report,
            "execution_time_ms": execution_time,
            "analysis_depth": req.analysis_depth,
            "file_path": req.file_path,
            "change_description": req.change_description
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")


@router.post("/db-field")
async def analyze_db_field_impact(req: DbFieldImpactRequest):
    """分析数据库字段变更影响链"""
    from src.llm.client import get_llm_client, is_llm_enabled
    from src.llm.prompts import render_prompt
    import json

    if not is_llm_enabled():
        raise HTTPException(status_code=503, detail="LLM 未配置，无法执行影响链分析")

    start_time = time.time()
    client = get_llm_client()

    try:
        # 结构化影响链分析
        messages = render_prompt("db_field_impact_analysis",
                                 change_description=req.change_description,
                                 table_name=req.table_name,
                                 field_name=req.field_name,
                                 field_change=req.field_change,
                                 tech_stack=req.tech_stack or "",
                                 analysis_depth=req.analysis_depth)

        raw_result = client.chat(messages)
        impact_data = _parse_json_result(raw_result)

        # 生成报告
        report = client.chat(render_prompt("impact_report_generation",
                                           file_path=f"{req.table_name}.{req.field_name}",
                                           analysis_depth=req.analysis_depth,
                                           project_name=req.project_name or "Unknown Project",
                                           audience=req.audience,
                                           analysis_result=json.dumps(impact_data, ensure_ascii=False, indent=2)))

        execution_time = int((time.time() - start_time) * 1000)

        return {
            "success": True,
            "impact_data": impact_data,
            "report": report,
            "execution_time_ms": execution_time,
            "analysis_depth": req.analysis_depth,
            "table": req.table_name,
            "field": req.field_name,
            "change": req.field_change
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")


def _parse_json_result(text: str) -> Dict:
    """从 LLM 返回文本中解析 JSON"""
    try:
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1:
            return json.loads(text[start:end + 1])
    except (json.JSONDecodeError, ValueError):
        pass
    return {"raw_result": text, "parse_error": True}
