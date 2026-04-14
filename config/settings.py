# -*- coding: utf-8 -*-
"""
配置加载器 - 根据 profile 名称加载对应行业的配置
用法：
    from config.settings import load_profile
    profile = load_profile("ai")       # 或 "battery"
    profile.CATEGORIES, profile.REPORT_TITLE, ...
"""

import importlib

AVAILABLE_PROFILES = {
    "ai":      "config.ai",
    "battery": "config.battery",
}


def load_profile(name: str):
    """
    加载指定 profile 的配置模块。
    返回模块对象，可通过 .CATEGORIES / .REPORT_TITLE 访问。
    """
    if name not in AVAILABLE_PROFILES:
        raise ValueError(
            f"未知 profile: {name}，可选值: {list(AVAILABLE_PROFILES.keys())}"
        )
    return importlib.import_module(AVAILABLE_PROFILES[name])


# ═══ 向后兼容：如果有旧代码直接 from config.settings import CATEGORIES ═══
# 默认加载 AI 配置
_default = load_profile("ai")
CATEGORIES   = _default.CATEGORIES
REPORT_TITLE = _default.REPORT_TITLE