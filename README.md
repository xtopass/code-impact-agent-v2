# 代码影响范围调查系统 v2 - 增强版

基于多Agent协作架构的代码变更影响范围分析系统，支持MCP扩展、Skill插件和自学习能力。

## 🚀 快速开始

### 安装依赖

```bash
# 进入项目目录
cd code-impact-agent-v2

# 安装Python依赖
pip install -r requirements.txt

# 安装Node依赖（Web界面）
npm install
```

### 启动服务

```bash
# 方式1: 启动API服务器
python main.py

# 方式2: 启动开发模式（API + Web热更新）
npm run dev
```

### 访问界面

- **API服务器**: http://localhost:3000
- **Web界面**: http://localhost:3000
- **API文档**: http://localhost:3000/docs (Swagger UI)

---

## 📦 核心特性

### 1. MCP集成 (Model Context Protocol)

通过MCP协议扩展Agent能力，支持：

| 内置MCP | 功能 |
|---------|------|
| `git` | Git变更提取、历史记录查询 |
| `semgrep` | 静态安全扫描 |
| `puppet` | Puppet配置解析和验证 |
| `dependency` | 依赖关系图构建 |

**添加自定义MCP:**
```bash
# 通过API添加
curl -X POST http://localhost:3000/api/mcp/servers \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-custom-mcp",
    "command": "npx",
    "args": ["my-mcp-server"]
  }'
```

### 2. Skill系统

可插拔的技能模块，支持：

- **内置Skills**: 代码分析器、Git追踪器、安全扫描器
- **市场Skills**: 从社区下载安装
- **自定义Skills**: 轻松创建自己的Skill

```python
# 注册新Skill
from src.skills.registry import get_skill_registry, SkillMetadata

registry = get_skill_registry()
metadata = SkillMetadata(
    id="my_custom_skill",
    name="我的自定义Skill",
    description="这是我的Skill描述",
    entry_point="skills.my_skill:MySkill.execute",
    tags=["custom", "analysis"]
)
registry.register_skill(metadata)
```

### 3. Agent路由

智能任务分发系统：

- **基于能力的路由**: 根据任务类型选择最合适的Agent
- **负载均衡**: 自动分配任务到空闲Agent
- **优先级队列**: 高优先级任务优先处理

### 4. Agent Crew协作

多Agent团队协作：

```python
from src.agents.router import get_or_create_crew

# 创建团队
crew = get_or_create_crew("分析团队", "crew_001")

# 添加成员
crew.add_member(code_agent, role="代码分析专家")
crew.add_member(security_agent, role="安全审查专家")

# 设置工作流
crew.set_workflow(["code_analysis", "security_review", "final_report"])

# 执行
result = await crew.execute(task_data)
```

### 5. 自学习引擎

从历史案例中学习优化：

- **案例归档**: 自动记录每次分析
- **准确率追踪**: 用户反馈计算准确率
- **规则优化**: 自动调整分析规则阈值
- **性能优化**: 识别慢查询并建议并行化

---

## 📁 项目结构

```
code-impact-agent-v2/
├── src/
│   ├── api.py              # FastAPI服务器
│   ├── system.py           # 系统核心
│   ├── mcp/
│   │   └── client.py       # MCP客户端
│   ├── skills/
│   │   └── registry.py     # Skill注册表
│   ├── agents/
│   │   └── router.py       # Agent路由和Crew
│   └── learning/
│       └── engine.py       # 自学习引擎
├── web/
│   └── index.html          # Vue.js前端界面
├── data/                   # 数据存储
│   ├── mcp-servers.json
│   ├── skills/
│   ├── cases.json
│   └── rules.json
├── main.py                 # 启动入口
├── package.json
└── requirements.txt
```

---

## 🔌 API端点

### MCP管理
```
GET    /api/mcp/servers          # 列出MCP服务器
POST   /api/mcp/servers          # 添加MCP服务器
DELETE /api/mcp/servers/{name}   # 删除MCP服务器
POST   /api/mcp/tools/{server}/{tool}  # 调用MCP工具
```

### Skill管理
```
GET    /api/skills               # 列出Skills
POST   /api/skills               # 注册Skill
POST   /api/skills/{id}/execute  # 执行Skill
```

### Agent管理
```
GET    /api/agents               # 列出Agents
GET    /api/agents/stats         # 路由统计
POST   /api/agents/route         # 路由任务
```

### 学习引擎
```
POST   /api/cases                    # 记录案例
POST   /api/cases/{id}/feedback      # 添加反馈
GET    /api/learning/insights        # 获取学习洞察
POST   /api/learning/rules/{id}/adjust  # 应用规则调整
```

### 分析
```
POST   /api/analyze                  # 运行完整分析
GET    /api/health                   # 健康检查
```

---

## 🎨 Web界面

内置Web界面提供：

- **分析面板**: 可视化分析流程和结果
- **Agent管理**: 查看和管理Agent池
- **Skill市场**: 浏览和安装社区Skills
- **MCP配置**: 管理MCP服务器
- **学习洞察**: 查看系统学习和优化建议

---

## 📝 使用示例

### 基本分析

```python
from src.system import get_system

system = get_system()
result = system.run_analysis("src/app.py", {"depth": 2})

print(f"风险等级: {result['risk_level']}")
print(f"发现项: {len(result['findings'])}")
print(f"执行时间: {result['execution_time_ms']}ms")
```

### 提交反馈

```python
# 标记分析结果准确性
system.add_feedback(
    case_id="abc123",
    is_correct=True,
    feedback="分析准确，覆盖了所有关键变更"
)
```

### 查看学习洞察

```python
insights = system.get_learning_insights()
print(f"总案例数: {insights['stats']['total_cases']}")
print(f"准确率: {insights['stats']['accuracy_rate']:.1%}")
print(f"优化建议: {len(insights['recommendations'])}")
```

---

## 🔧 配置

复制 `.env.example` 为 `.env` 并修改配置：

```bash
cp .env.example .env
```

主要配置项：
- `GITHUB_TOKEN`: GitHub访问令牌
- `PORT`: API服务器端口 (默认3000)
- `DATA_DIR`: 数据存储目录

---

## 📚 扩展开发

### 创建自定义Skill

```python
# skills/my_skill.py
class MySkill:
    async def execute(self, input_data: Dict) -> Dict:
        # 实现你的逻辑
        return {"result": "success"}
```

### 添加新的MCP服务器

在 `config/mcp-servers.json` 中添加：
```json
{
  "name": "my-mcp",
  "command": "npx",
  "args": ["my-mcp-package"],
  "enabled": true
}
```

---

## 🤝 贡献

欢迎提交Issue和Pull Request！

---

## 📄 License

MIT License
