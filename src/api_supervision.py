"""
自监督 API
提供系统质量监控、漂移检测、告警
"""
from fastapi import APIRouter
from typing import Dict, Any, List


router = APIRouter(prefix="/api/supervision", tags=["自监督"])


@router.get("/metrics")
async def get_metrics():
    """获取系统质量指标"""
    from src.learning.engine import get_learning_engine
    from src.memory.system import get_memory_manager
    from src.agents.router import get_agent_router

    engine = get_learning_engine()
    mm = get_memory_manager()
    router = get_agent_router()

    stats = engine.analyze_patterns()

    # 准确率趋势（近7天）
    recent_cases = [c for c in engine.cases if c.timestamp and c.timestamp[:10] >= _days_ago(7)]
    correct_recent = [c for c in recent_cases if c.is_correct is True]
    incorrect_recent = [c for c in recent_cases if c.is_correct is False]
    accuracy_7d = len(correct_recent) / len(recent_cases) if recent_cases else None

    # 平均执行时间趋势
    exec_times = [c.execution_time_ms for c in engine.cases[-30:] if c.execution_time_ms]
    avg_exec_time = sum(exec_times) / len(exec_times) if exec_times else 0

    # Agent 负载
    agent_stats = router.get_routing_stats()

    # 记忆健康度
    memory_stats = mm.get_statistics()

    # 质量评分趋势（近10次）
    recent_scores = [c.quality_score for c in engine.cases[-10:] if c.quality_score]
    avg_quality = sum(recent_scores) / len(recent_scores) if recent_scores else 0

    return {
        "overall": {
            "total_cases": stats.get("total_cases", 0),
            "accuracy_rate": stats.get("accuracy_rate", 0),
            "accuracy_7d": round(accuracy_7d, 4) if accuracy_7d is not None else None,
            "avg_execution_time_ms": int(avg_exec_time),
            "avg_quality_score": round(avg_quality, 4),
            "feedback_count": len([c for c in engine.cases if c.is_correct is not None]),
        },
        "agent_load": agent_stats,
        "memory_health": memory_stats,
        "risk_distribution": stats.get("risk_distribution", {}),
        "trends": {
            "daily_cases": stats.get("daily_cases", []),
            "weekly_accuracy": stats.get("weekly_accuracy", []),
        },
        "generated_at": _now_iso()
    }


@router.get("/alerts")
async def get_alerts():
    """获取告警信息"""
    from src.learning.engine import get_learning_engine
    engine = get_learning_engine()
    stats = engine.analyze_patterns()

    alerts = []

    # 准确率下降告警
    accuracy = stats.get("accuracy_rate", 1.0)
    if accuracy < 0.5 and stats.get("total_cases", 0) >= 5:
        alerts.append({
            "level": "critical",
            "type": "accuracy_drop",
            "message": f"准确率过低: {accuracy:.1%}，建议检查规则配置",
            "timestamp": _now_iso()
        })

    # 执行时间过长告警
    avg_time = stats.get("avg_execution_time_ms", 0)
    if avg_time > 60000:
        alerts.append({
            "level": "warning",
            "type": "slow_analysis",
            "message": f"平均分析时间 {avg_time}ms 过长，建议并行化",
            "timestamp": _now_iso()
        })

    # 案例不足告警
    if stats.get("total_cases", 0) < 3:
        alerts.append({
            "level": "info",
            "type": "insufficient_data",
            "message": "案例数量不足，系统学习效果有限",
            "timestamp": _now_iso()
        })

    return {"alerts": alerts, "count": len(alerts)}


@router.get("/drift")
async def detect_drift():
    """检测模型/规则漂移"""
    from src.learning.engine import get_learning_engine
    engine = get_learning_engine()

    cases = engine.cases
    if len(cases) < 10:
        return {"drift_detected": False, "reason": "案例不足", "confidence": 0}

    # 按周分组计算准确率
    weekly = {}
    for c in cases:
        week = c.timestamp[:7] if c.timestamp else "unknown"
        if week not in weekly:
            weekly[week] = {"total": 0, "correct": 0}
        weekly[week]["total"] += 1
        if c.is_correct is not None:
            if c.is_correct:
                weekly[week]["correct"] += 1

    weeks = sorted(weekly.keys())
    if len(weeks) < 2:
        return {"drift_detected": False, "reason": "数据周期不足"}

    rates = []
    for w in weeks:
        t = weekly[w]["total"]
        c = weekly[w]["correct"]
        rates.append({"week": w, "rate": c / t if t > 0 else 0})

    # 检测下降趋势
    last_two = rates[-2:]
    if len(last_two) == 2:
        drop = last_two[0]["rate"] - last_two[1]["rate"]
        drift = drop > 0.2  # 下降超过20%
        return {
            "drift_detected": drift,
            "trend": "declining" if drift else "stable",
            "recent_rates": last_two,
            "confidence": min(1.0, drop * 5) if drift else 0.3
        }

    return {"drift_detected": False, "trend": "stable"}


def _days_ago(days: int) -> str:
    from datetime import datetime, timedelta
    return (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")


def _now_iso() -> str:
    from datetime import datetime
    return datetime.now().isoformat()
