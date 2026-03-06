"""
生成前反思模块 (Agentic Reflection)
====================================
在生成每批大纲之前，汇总错题本和高分案例的精华，
自动生成一段"三思而后行"的反思提示，注入到 Prompt 中。
"""

from pathlib import Path
from typing import Optional

from mechanisms.negative_memory import NegativeMemory
from mechanisms.positive_memory import PositiveMemory


class ReflectionEngine:
    """反思引擎：生成前自我提醒"""

    def __init__(self):
        self.neg = NegativeMemory()
        self.pos = PositiveMemory()

    def generate_reflection(
        self,
        novel_name: str,
        batch_num: int
    ) -> str:
        """
        为指定批次生成反思提示词段落。

        综合错题本的高频教训和高分案例的成功经验，
        形成一段简短但有针对性的自我提醒。

        Args:
            novel_name: 当前小说名称
            batch_num: 当前批次号

        Returns:
            格式化的 Markdown 反思段落
        """
        lines = []

        # 1. 从错题本提取教训
        neg_stats = self.neg.get_stats()
        if neg_stats["total"] > 0:
            lines.append("【🪞 生成前反思（三思而后行）】")
            lines.append(f"系统累计记录了 {neg_stats['total']} 次失败教训。")

            # 高频错误警告
            if neg_stats.get("top_forbidden"):
                top3 = neg_stats["top_forbidden"][:3]
                words = "、".join([f"「{w}」(×{c})" for w, c in top3])
                lines.append(f"⚠️ 最常被拦截的禁词: {words}，本次务必彻底回避这些概念。")

            # 按类型提醒
            by_type = neg_stats.get("by_type", {})
            if by_type.get("character_name", 0) >= 2:
                lines.append("⚠️ 角色名违规曾多次发生，请确保所有角色使用 2-3 字具体姓名，严禁泛指。")
            if by_type.get("missing_volume", 0) >= 1:
                lines.append("⚠️ 曾出现过卷号缺失，请严格按格式输出完整的每一卷。")

        # 2. 从高分案例提取经验
        pos_stats = self.pos.get_stats()
        if pos_stats["total"] > 0:
            if not lines:
                lines.append("【🪞 生成前反思（三思而后行）】")
            lines.append(f"\n✅ 系统已积累 {pos_stats['total']} 个高分案例 (平均 {pos_stats['avg_score']} 分)。")
            if len(pos_stats.get("novels", [])) > 1:
                lines.append(f"   跨越 {len(pos_stats['novels'])} 本小说的创作经验。")
            lines.append("请参照高分范例的叙事结构和节奏把控。")

        # 3. 针对性提醒（基于当前批次阶段）
        if batch_num <= 3:
            lines.append("\n📌 当前处于开篇阶段（黄金三章），请特别注意悬念铺设和人物魅力展示。")
        elif batch_num <= 30:
            lines.append("\n📌 当前处于龙头阶段，请确保世界观逐步展开，伏笔种植到位。")
        elif batch_num <= 80:
            lines.append("\n📌 当前处于猪肚阶段，请确保冲突升级、多线交织、群像高潮轮番爆发。")
        else:
            lines.append("\n📌 当前处于豹尾阶段，请确保伏笔回收、理念碰撞、配角高光闭环。")

        if not lines:
            return ""

        return "\n".join(lines) + "\n"
