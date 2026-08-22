"""
国际化(i18n)模块
支持中日英三语切换
"""
import json
from pathlib import Path
from typing import Dict, Any, Optional
from enum import Enum


class Locale(str, Enum):
    """支持的语言"""
    EN = "en"      # 英语
    ZH = "zh"      # 中文
    JA = "ja"      # 日语


class I18nManager:
    """国际化管理器"""
    
    def __init__(self, i18n_dir: str = "./i18n"):
        self.i18n_dir = Path(i18n_dir)
        self.current_locale: Locale = Locale.EN
        self.messages: Dict[str, Dict[str, str]] = {}
        self._load_messages()
    
    def _load_messages(self):
        """加载所有语言消息"""
        supported_locales = [Locale.EN, Locale.ZH, Locale.JA]
        
        for locale in supported_locales:
            lang_file = self.i18n_dir / f"{locale.value}.json"
            if lang_file.exists():
                try:
                    with open(lang_file, 'r', encoding='utf-8') as f:
                        self.messages[locale.value] = json.load(f)
                except (json.JSONDecodeError, IOError) as e:
                    print(f"⚠️ 加载 {locale.value} 语言文件失败: {e}")
            else:
                print(f"⚠️ 未找到语言文件: {lang_file}")
    
    def set_locale(self, locale: Locale) -> bool:
        """设置当前语言"""
        if locale.value in self.messages:
            self.current_locale = locale
            return True
        return False
    
    def get_locale(self) -> Locale:
        """获取当前语言"""
        return self.current_locale
    
    def t(self, key: str, **kwargs) -> str:
        """翻译函数 - 获取翻译文本
        
        Args:
            key: 翻译键，支持点号分隔，如 'common.app_name'
            **kwargs: 变量替换，如 name='World'
        
        Returns:
            翻译后的文本，如果找不到则返回key
        """
        # 尝试当前语言
        result = self._get_translation(self.current_locale.value, key)
        
        # 如果找不到，尝试英语（fallback）
        if result == key and self.current_locale != Locale.EN:
            result = self._get_translation(Locale.EN.value, key)
        
        # 替换变量
        if kwargs and result:
            for k, v in kwargs.items():
                result = result.replace(f"{{{k}}}", str(v))
        
        return result
    
    def _get_translation(self, locale: str, key: str) -> str:
        """获取指定语言的翻译"""
        messages = self.messages.get(locale, {})
        
        # 支持点号分隔的key
        parts = key.split('.')
        current = messages
        
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return key  # 返回key作为fallback
        
        return current if isinstance(current, str) else key
    
    def get_supported_locales(self) -> list:
        """获取支持的语言列表"""
        return list(self.messages.keys())
    
    def get_locale_name(self, locale: Locale) -> str:
        """获取语言显示名称"""
        names = {
            Locale.EN: "English",
            Locale.ZH: "中文",
            Locale.JA: "日本語"
        }
        return names.get(locale, locale.value)


# 全局实例
_i18n_manager = None


def get_i18n() -> I18nManager:
    """获取i18n管理器单例"""
    global _i18n_manager
    if _i18n_manager is None:
        _i18n_manager = I18nManager()
    return _i18n_manager


def init_i18n(i18n_dir: str = "./i18n") -> I18nManager:
    """初始化i18n系统"""
    global _i18n_manager
    _i18n_manager = I18nManager(i18n_dir)
    return _i18n_manager


def translate(key: str, **kwargs) -> str:
    """便捷翻译函数"""
    return get_i18n().t(key, **kwargs)
