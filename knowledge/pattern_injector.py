"""
模式注入器 (Pattern Injector)
================================
连接知识库与生成 prompt：
- 根据新小说需求检索匹配的叙事模式
- 格式化为 LLM prompt 段落
- 记录使用和评分反馈
"""

import os
import sys
import logging
from typing import List, Dict, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from knowledge.knowledge_store import (
    KnowledgeStore,
    CATEGORY_ARCHETYPE,
    CATEGORY_PLOT,
    CATEGORY_RELATIONSHIP,
    CATEGORY_PACING,
    ALL_CATEGORIES,
)

logger = logging.getLogger(__name__)


class PatternInjector:
    """
    模式注入器 — 生成小说时检索并注入叙事模式
    
    用法:
        injector = PatternInjector()
        prompt_block = injector.get_injection_prompt("架空古代+底层逆袭+群像")
    """

    def __init__(self, knowledge_store: KnowledgeStore = None):
        self.store = knowledge_store or KnowledgeStore()

    def get_relevant_patterns(
        self,
        description: str,
        top_k_per_category: int = 2,
    ) -> Dict[str, List[Dict]]:
        """
        为新小说检索匹配的模式。
        
        Args:
            description: 新小说的描述（如 "底层逆袭+群像+幽默"）
            top_k_per_category: 每个类别返回几个模式
            
        Returns:
            {"archetype": [...], "plot_pattern": [...], ...}
        """
        results = {}
        for category in ALL_CATEGORIES:
            patterns = self.store.search(
                query=description,
                category=category,
                top_k=top_k_per_category,
                min_score=0.03,
            )
            if patterns:
                results[category] = patterns
        
        return results

    def format_for_prompt(self, patterns: Dict[str, List[Dict]]) -> str:
        """
        将检索到的模式格式化为 prompt 段落。
        
        Args:
            patterns: get_relevant_patterns() 的返回值
            
        Returns:
            可直接注入 LLM prompt 的文本段落
        """
        if not patterns:
            return ""
        
        sections = []
        sections.append("【📚 跨小说叙事模式参考（仅供借鉴，严禁照搬）】")
        sections.append("以下是从优秀小说中提取的可复用叙事模式。"
                       "请参考其结构和思路，但必须在当前世界观下进行原创性改造。\n")
        
        category_names = {
            CATEGORY_ARCHETYPE: "🎭 角色原型参考",
            CATEGORY_PLOT: "📖 剧情模式参考",
            CATEGORY_RELATIONSHIP: "🤝 关系动态参考",
            CATEGORY_PACING: "🎵 节奏模板参考",
        }
        
        for category, cat_patterns in patterns.items():
            cat_name = category_names.get(category, category)
            sections.append(f"\n{cat_name}:")
            
            for i, p in enumerate(cat_patterns, 1):
                score_str = f"(评分:{p['quality_score']:.1f})" if p.get('quality_score') else ""
                tags_str = f" [{', '.join(p['tags'])}]" if p.get('tags') else ""
                sections.append(
                    f"  {i}. 【{p['name']}】{score_str}{tags_str}"
                )
                sections.append(f"     {p['description']}")
        
        sections.append("\n⚠️ 重要：以上模式仅为结构参考，请勿复制具体情节或人名。")
        
        return "\n".join(sections)

    def get_injection_prompt(
        self,
        description: str,
        top_k_per_category: int = 2,
    ) -> str:
        """
        一步到位：检索 + 格式化，返回可直接注入的 prompt 段落。
        
        Args:
            description: 新小说描述
            top_k_per_category: 每类返回数量
        """
        patterns = self.get_relevant_patterns(description, top_k_per_category)
        if not patterns:
            return ""
        
        prompt = self.format_for_prompt(patterns)
        
        # 记录使用
        for cat_patterns in patterns.values():
            for p in cat_patterns:
                try:
                    self.store.record_usage(p["id"])
                except Exception:
                    pass
        
        return prompt

    def record_feedback(self, pattern_ids: List[int], score: float, feedback: str = ""):
        """为使用过的模式批量评分"""
        for pid in pattern_ids:
            self.store.record_feedback(pid, score, feedback)
