"""
Context Manager for QWen3TTS
Handles 100-Volume Lookback with Hierarchical Summarization

Fix #1: 分层压缩而非线性拼接，防止 context 窗口溢出
- 最近3卷: 完整摘要
- 4-10卷前: 压缩为 1 段概述
- 11+ 卷前: 超浓缩为「阶段回顾」(按大纲阶段分组)
"""
from typing import List, Dict, Optional
import logging
from dataclasses import dataclass

from models import StoryBible, VolumePlan

logger = logging.getLogger(__name__)


# 分层压缩参数
RECENT_FULL_VOLUMES = 3      # 最近 N 卷保留完整摘要
MEDIUM_WINDOW = 7            # 中等距离卷数 (压缩为概述)
MAX_SUMMARY_CHARS = 200      # 远距离摘要最大字符
MAX_TOTAL_CONTEXT_CHARS = 12000  # 总 context 不超过 ~3000 tokens


class ContextManager:
    def __init__(self, storage_manager):
        self.storage = storage_manager

    def get_generation_context(self, bible: StoryBible, current_chapter: int) -> str:
        """
        构建生成 context (分层压缩, 防止窗口溢出)
        """
        current_volume_num = (current_chapter - 1) // 10 + 1
        
        context_parts = []
        
        # 1. 全局背景 (固定, ~200 字)
        context_parts.append(self._get_global_context(bible))
        
        # 2. 分层回顾 (核心改进: 不再线性拼接)
        context_parts.append(self._get_hierarchical_lookback(bible, current_volume_num))
        
        # 3. 当前卷规划
        if current_volume_num in bible.volume_plans:
            plan = bible.volume_plans[current_volume_num]
            context_parts.append(self._get_current_volume_plan(plan, current_chapter))
            
        # 4. 近期章节 (滑动窗口)
        context_parts.append(self._get_recent_chapters_context(bible, current_chapter))
        
        # 5. 活跃伏笔提醒
        context_parts.append(self._get_active_loops_reminder(bible, current_chapter))
        
        full_context = "\n\n".join([p for p in context_parts if p])
        
        # 安全截断
        if len(full_context) > MAX_TOTAL_CONTEXT_CHARS:
            logger.warning(f"Context 超出 {MAX_TOTAL_CONTEXT_CHARS} 字符, 执行截断")
            full_context = full_context[:MAX_TOTAL_CONTEXT_CHARS] + "\n...(已截断)"
        
        return full_context

    def _get_global_context(self, bible: StoryBible) -> str:
        return f"""【全局故事背景】
标题：{bible.story_title}
类型：{bible.genre}
核心梗概：{bible.main_plot_summary[:300]}
世界观：{bible.world_settings.world_type if bible.world_settings else '未设定'}"""

    def _get_hierarchical_lookback(self, bible: StoryBible, current_vol: int) -> str:
        """
        分层压缩回顾 (Fix #1 核心)
        
        层级:
        - 远期 (1 ~ current-RECENT-MEDIUM): 按阶段分组, 每阶段 1 句话
        - 中期 (current-RECENT-MEDIUM ~ current-RECENT): 每卷 1-2 句
        - 近期 (current-RECENT ~ current-1): 完整摘要
        """
        if current_vol <= 1:
            return "【前情回顾】：无（当前为第一卷）"
            
        lookback_lines = ["【前情回顾 (分层压缩)】"]
        
        recent_start = max(1, current_vol - RECENT_FULL_VOLUMES)
        medium_start = max(1, current_vol - RECENT_FULL_VOLUMES - MEDIUM_WINDOW)
        
        # -------- 远期: 超浓缩 --------
        if medium_start > 1:
            lookback_lines.append(f"\n📌 远期回顾 (第1~{medium_start-1}卷):")
            # 按阶段分组 (每10卷一个阶段)
            phases = {}
            for vol_num in range(1, medium_start):
                phase_key = ((vol_num - 1) // 10) * 10 + 1  # 1-10, 11-20, ...
                if phase_key not in phases:
                    phases[phase_key] = []
                
                summary = self._get_vol_summary(bible, vol_num)
                if summary:
                    # 只取第一句
                    first_sentence = summary.split('。')[0] + '。' if '。' in summary else summary[:80]
                    phases[phase_key].append(first_sentence)
            
            for phase_start, sentences in sorted(phases.items()):
                phase_end = min(phase_start + 9, medium_start - 1)
                combined = ''.join(sentences[:3])  # 每阶段最多3句
                if len(combined) > MAX_SUMMARY_CHARS:
                    combined = combined[:MAX_SUMMARY_CHARS] + "..."
                lookback_lines.append(f"  第{phase_start}~{phase_end}卷: {combined}")
        
        # -------- 中期: 每卷 1-2 句 --------
        if medium_start < recent_start:
            lookback_lines.append(f"\n📋 中期回顾 (第{medium_start}~{recent_start-1}卷):")
            for vol_num in range(medium_start, recent_start):
                summary = self._get_vol_summary(bible, vol_num)
                if summary:
                    short = summary.split('\n')[0][:150]
                    lookback_lines.append(f"  第{vol_num}卷: {short}")
        
        # -------- 近期: 完整摘要 --------
        lookback_lines.append(f"\n📖 近期回顾 (第{recent_start}~{current_vol-1}卷):")
        for vol_num in range(recent_start, current_vol):
            summary = self._get_vol_summary(bible, vol_num)
            if summary:
                lookback_lines.append(f"  === 第{vol_num}卷 ===\n  {summary}")
            else:
                plan = bible.volume_plans.get(vol_num)
                title = plan.title if plan else "未知"
                lookback_lines.append(f"  === 第{vol_num}卷《{title}》=== (摘要缺失)")
                 
        return "\n".join(lookback_lines)
    
    def _get_vol_summary(self, bible: StoryBible, vol_num: int) -> str:
        """获取卷摘要, 优先用 volume_summaries, 退而用 volume_plans.summary"""
        summary = bible.volume_summaries.get(vol_num, "")
        if not summary:
            plan = bible.volume_plans.get(vol_num)
            if plan:
                summary = f"《{plan.title}》: {plan.summary}" if hasattr(plan, 'summary') else ""
        return summary

    def _get_current_volume_plan(self, plan: VolumePlan, current_chapter: int) -> str:
        chapter_in_vol = (current_chapter - 1) % 10 + 1
        key_event = plan.get_event_for_chapter(chapter_in_vol) if hasattr(plan, 'get_event_for_chapter') else "无特定事件"
        
        return f"""【当前卷规划：第{plan.volume_number}卷《{plan.title}》】
本卷主旨：{plan.summary}
核心冲突：{plan.main_conflict}
主角成长：{plan.protagonist_growth}
本章({current_chapter})关键事件：{key_event}"""

    def _get_recent_chapters_context(self, bible: StoryBible, current_chapter: int) -> str:
        """最近 5 章的剧情"""
        start = max(1, current_chapter - 5)
        recent_text = ["【近期章节剧情】"]
        for i in range(start, current_chapter):
            if i in bible.chapter_outlines:
                outline = bible.chapter_outlines[i]
                recent_text.append(f"第{i}章：{outline.summary}")
        
        return "\n".join(recent_text) if len(recent_text) > 1 else ""
    
    def _get_active_loops_reminder(self, bible: StoryBible, current_chapter: int) -> str:
        """提醒当前活跃的伏笔"""
        if not hasattr(bible, 'open_loops') or not bible.open_loops:
            return ""
        
        active = []
        for loop_id, loop in bible.open_loops.items():
            if hasattr(loop, 'status'):
                if loop.status.value == "open":
                    active.append(f"- [{loop_id}] {loop.title}: {loop.description[:60]}")
        
        if not active:
            return ""
        
        return "【活跃伏笔提醒】\n" + "\n".join(active[:10])
