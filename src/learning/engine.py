"""
自学习引擎 - 从历史案例中学习优化
"""
import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import hashlib
import statistics


@dataclass
class CaseRecord:
    """案例记录"""
    case_id: str
    timestamp: str
    target_file: str
    risk_level: str
    findings_count: int
    agents_used: List[str]
    execution_time_ms: int
    quality_score: float
    user_feedback: Optional[str] = None
    is_correct: Optional[bool] = None  # True=正确, False=误报/漏报
    
    def to_dict(self) -> dict:
        return {
            "case_id": self.case_id,
            "timestamp": self.timestamp,
            "target_file": self.target_file,
            "risk_level": self.risk_level,
            "findings_count": self.findings_count,
            "agents_used": self.agents_used,
            "execution_time_ms": self.execution_time_ms,
            "quality_score": self.quality_score,
            "user_feedback": self.user_feedback,
            "is_correct": self.is_correct
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'CaseRecord':
        return cls(
            case_id=data["case_id"],
            timestamp=data["timestamp"],
            target_file=data["target_file"],
            risk_level=data["risk_level"],
            findings_count=data["findings_count"],
            agents_used=data.get("agents_used", []),
            execution_time_ms=data.get("execution_time_ms", 0),
            quality_score=data.get("quality_score", 0.0),
            user_feedback=data.get("user_feedback"),
            is_correct=data.get("is_correct")
        )


@dataclass
class RuleAdjustment:
    """规则调整建议"""
    rule_id: str
    adjustment_type: str  # "tighten", "loosen", "add", "remove"
    reason: str
    confidence: float
    suggested_value: Any
    
    def to_dict(self) -> dict:
        return {
            "rule_id": self.rule_id,
            "adjustment_type": self.adjustment_type,
            "reason": self.reason,
            "confidence": self.confidence,
            "suggested_value": self.suggested_value
        }


class LearningEngine:
    """自学习引擎"""
    
    def __init__(self, data_dir: str = "./data"):
        self.data_dir = Path(data_dir)
        self.cases: List[CaseRecord] = []
        self.rules: Dict[str, Dict] = {}
        self.adjustments: List[RuleAdjustment] = []
        self._load_data()
    
    def _load_data(self):
        """加载历史数据"""
        cases_file = self.data_dir / "cases.json"
        rules_file = self.data_dir / "rules.json"
        
        if cases_file.exists():
            try:
                with open(cases_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.cases = [CaseRecord.from_dict(c) for c in data]
            except (json.JSONDecodeError, IOError):
                pass
        
        if rules_file.exists():
            try:
                with open(rules_file, 'r', encoding='utf-8') as f:
                    self.rules = json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
    
    def _save_data(self):
        """保存数据到磁盘"""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        with open(self.data_dir / "cases.json", 'w', encoding='utf-8') as f:
            json.dump([c.to_dict() for c in self.cases], f, indent=2, ensure_ascii=False)
        
        with open(self.data_dir / "rules.json", 'w', encoding='utf-8') as f:
            json.dump(self.rules, f, indent=2, ensure_ascii=False)
    
    def record_case(self, case_data: Dict) -> CaseRecord:
        """记录新案例"""
        case_id = hashlib.sha256(f"{case_data.get('target_file', '')}:{datetime.now().isoformat()}".encode()).hexdigest()[:16]
        
        case = CaseRecord(
            case_id=case_id,
            timestamp=datetime.now().isoformat(),
            target_file=case_data.get("target_file", ""),
            risk_level=case_data.get("risk_level", "unknown"),
            findings_count=case_data.get("findings_count", 0),
            agents_used=case_data.get("agents_used", []),
            execution_time_ms=case_data.get("execution_time_ms", 0),
            quality_score=case_data.get("quality_score", 0.0)
        )
        
        self.cases.append(case)
        self._save_data()
        
        return case
    
    def add_feedback(self, case_id: str, is_correct: bool, feedback: str = None):
        """添加用户反馈"""
        for case in self.cases:
            if case.case_id == case_id:
                case.is_correct = is_correct
                case.user_feedback = feedback
                self._save_data()
                return True
        return False
    
    def analyze_patterns(self) -> Dict[str, Any]:
        """分析历史模式"""
        if not self.cases:
            return {"message": "暂无历史案例"}
        
        # 风险分布
        risk_dist = {}
        for case in self.cases:
            risk = case.risk_level
            risk_dist[risk] = risk_dist.get(risk, 0) + 1
        
        # 准确率统计
        rated_cases = [c for c in self.cases if c.is_correct is not None]
        if rated_cases:
            accuracy = sum(1 for c in rated_cases if c.is_correct) / len(rated_cases)
        else:
            accuracy = None
        
        # 平均执行时间
        exec_times = [c.execution_time_ms for c in self.cases if c.execution_time_ms > 0]
        avg_exec_time = statistics.mean(exec_times) if exec_times else 0
        
        # 高频Agent
        agent_usage = {}
        for case in self.cases:
            for agent in case.agents_used:
                agent_usage[agent] = agent_usage.get(agent, 0) + 1
        top_agents = sorted(agent_usage.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # 时间趋势(最近7天)
        recent_7days = datetime.now() - timedelta(days=7)
        recent_cases = [c for c in self.cases if datetime.fromisoformat(c.timestamp) > recent_7days]
        
        return {
            "total_cases": len(self.cases),
            "risk_distribution": risk_dist,
            "accuracy_rate": accuracy,
            "avg_execution_time_ms": int(avg_exec_time),
            "top_agents": [{"agent": a, "count": c} for a, c in top_agents],
            "recent_cases_7days": len(recent_cases),
            "last_updated": datetime.now().isoformat()
        }
    
    def generate_adjustments(self) -> List[RuleAdjustment]:
        """生成规则调整建议"""
        adjustments = []
        
        # 分析误报率高的规则
        false_positive_cases = [c for c in self.cases if c.is_correct == False]
        if len(false_positive_cases) > len(self.cases) * 0.3:
            adjustments.append(RuleAdjustment(
                rule_id="general_risk_threshold",
                adjustment_type="loosen",
                reason=f"误报率高达 {len(false_positive_cases)/len(self.cases):.1%}",
                confidence=0.8,
                suggested_value={"threshold": "higher"}
            ))
        
        # 分析漏报情况
        high_risk_missed = [c for c in self.cases 
                           if c.risk_level in ["high", "critical"] and c.findings_count < 3]
        if len(high_risk_missed) > 5:
            adjustments.append(RuleAdjustment(
                rule_id="deep_dependency_check",
                adjustment_type="tighten",
                reason=f"发现 {len(high_risk_missed)} 个高风险但低发现的案例",
                confidence=0.7,
                suggested_value={"min_findings_for_high_risk": 5}
            ))
        
        # 分析执行时间
        slow_cases = [c for c in self.cases if c.execution_time_ms > 30000]
        if len(slow_cases) > len(self.cases) * 0.2:
            adjustments.append(RuleAdjustment(
                rule_id="parallel_execution",
                adjustment_type="add",
                reason=f"{len(slow_cases)} 个案例执行超过30秒",
                confidence=0.9,
                suggested_value={"enable_parallel": True}
            ))
        
        self.adjustments = adjustments
        return adjustments
    
    def apply_adjustments(self, adjustments: List[RuleAdjustment]):
        """应用规则调整"""
        for adj in adjustments:
            if adj.rule_id in self.rules:
                rule = self.rules[adj.rule_id]
                if adj.adjustment_type in ["tighten", "loosen"]:
                    # 调整阈值
                    current = rule.get("threshold", 50)
                    if adj.adjustment_type == "tighten":
                        rule["threshold"] = int(current * 0.8)
                    else:
                        rule["threshold"] = int(current * 1.2)
                elif adj.adjustment_type == "add":
                    rule.update(adj.suggested_value)
            else:
                # 新增规则
                self.rules[adj.rule_id] = {
                    "enabled": True,
                    "threshold": adj.suggested_value.get("threshold", 50),
                    "created_at": datetime.now().isoformat()
                }
        
        self._save_data()
    
    def get_recommendations(self) -> List[Dict]:
        """获取优化建议"""
        stats = self.analyze_patterns()
        adjustments = self.generate_adjustments()
        
        recommendations = []
        
        # 基于准确率的建议
        if stats.get("accuracy_rate") is not None:
            if stats["accuracy_rate"] < 0.7:
                recommendations.append({
                    "type": "accuracy",
                    "priority": "high",
                    "message": f"系统准确率仅 {stats['accuracy_rate']:.1%}，建议重新校准规则"
                })
            elif stats["accuracy_rate"] > 0.9:
                recommendations.append({
                    "type": "accuracy",
                    "priority": "low",
                    "message": f"系统表现良好，准确率 {stats['accuracy_rate']:.1%}"
                })
        
        # 基于执行时间的建议
        if stats.get("avg_execution_time_ms", 0) > 20000:
            recommendations.append({
                "type": "performance",
                "priority": "medium",
                "message": "平均执行时间较长，建议启用并行处理"
            })
        
        # 基于规则调整的建议
        for adj in adjustments:
            recommendations.append({
                "type": "rule_adjustment",
                "priority": "high" if adj.confidence > 0.8 else "medium",
                "message": f"{adj.reason} - 建议{adj.adjustment_type}规则 {adj.rule_id}"
            })
        
        return recommendations
    
    def export_insights(self) -> Dict:
        """导出学习洞察"""
        return {
            "stats": self.analyze_patterns(),
            "adjustments": [a.to_dict() for a in self.generate_adjustments()],
            "recommendations": self.get_recommendations(),
            "exported_at": datetime.now().isoformat()
        }


# 全局学习引擎实例
_learning_engine = LearningEngine()

def get_learning_engine() -> LearningEngine:
    """获取学习引擎单例"""
    return _learning_engine
