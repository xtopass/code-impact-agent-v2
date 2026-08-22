"""
测试LLM集成
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from src.llm.client import init_llm, get_llm_client, is_llm_enabled


def test_llm_basic():
    """测试基本聊天"""
    print("\n=== 测试LLM基本功能 ===")
    
    # 初始化（使用环境变量中的API Key）
    provider = os.environ.get("LLM_PROVIDER", "deepseek")
    api_key = os.environ.get(f"{provider.upper()}_API_KEY") or os.environ.get("LLM_API_KEY")
    
    if not api_key:
        print("❌ 未配置LLM API Key")
        print("请在 .env 文件中设置:")
        print(f"  {provider.upper()}_API_KEY=your_key_here")
        return
    
    init_llm(provider=provider, api_key=api_key)
    
    client = get_llm_client()
    print(f"✅ LLM已启用: {provider}")
    print(f"   模型: {client.config.model}")
    print(f"   提供商: {client.config.provider.value}")
    
    # 测试简单对话
    print("\n--- 测试对话 ---")
    response = client.chat([
        {"role": "system", "content": "你是一个简洁的助手"},
        {"role": "user", "content": "用一句话介绍自己"}
    ])
    print(f"响应: {response}")


def test_llm_code_analysis():
    """测试代码变更分析"""
    print("\n=== 测试代码变更分析 ===")
    
    if not is_llm_enabled():
        print("❌ LLM未启用，请先配置API Key")
        return
    
    # 模拟一个代码变更
    sample_diff = """
diff --git a/src/app.py b/src/app.py
index 1234567..abcdefg 100644
--- a/src/app.py
+++ b/src/app.py
@@ -10,7 +10,7 @@
 def process_data(data):
-    result = transform(data)
+    result = transform(data, enable_cache=True)
     
     return result
 
@@ -25,3 +25,10 @@ def transform(data):
     return data
+
+def cache_key(data):
+    \"\"\"生成缓存键\"\"\"
+    import hashlib
+    return hashlib.md5(str(data).encode()).hexdigest()
+
+def get_cached(key):
+    \"\"\"获取缓存数据\"\"\"
+    return None
"""
    
    print("分析代码变更...")
    client = get_llm_client()
    result = client.analyze_code_impact(sample_diff, {"file": "src/app.py"})
    
    print("\n分析结果:")
    print(f"  风险等级: {result.get('risk_level', 'N/A')}")
    print(f"  影响模块: {result.get('direct_impact', [])}")
    print(f"  测试建议: {result.get('test_scenarios', [])}")


if __name__ == "__main__":
    test_llm_basic()
    test_llm_code_analysis()
