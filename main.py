"""
主入口 - 启动API服务器和Web界面
"""
import uvicorn
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(__file__))

from src.api import app


def main():
    """启动服务"""
    port = int(os.environ.get("PORT", 3000))
    
    print(f"🚀 启动 Code Impact Agent v2")
    print(f"📡 API Server: http://localhost:{port}")
    print(f"🌐 Web UI: http://localhost:{port}")
    print(f"📖 API文档: http://localhost:{port}/docs")
    print()
    
    uvicorn.run(
        "src.api:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )


if __name__ == "__main__":
    main()
