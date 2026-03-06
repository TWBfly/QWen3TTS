"""
负向反馈记忆模块 (Negative Memory / 错题本)
=============================================
记录每次校验失败的详细信息，在后续生成 Prompt 时自动注入历史教训，
使系统在多本小说的创作过程中不断积累避坑经验。
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional


# 全局记忆存储目录
GLOBAL_MEMORY_DIR = Path(__file__).parent.parent / "novel_data" / "_global_memory"


class NegativeMemory:
    """错题本：记录失败案例，生成历史教训提示"""

    def __init__(self):
        self.memory_dir = GLOBAL_MEMORY_DIR
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.memory_dir / "negative_lessons.json"
        self._lessons = self._load()

    def _load(self) -> List[Dict]:
        if self.db_path.exists():
            try:
                with open(self.db_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return []
        return []

    def _save(self):
        with open(self.db_path, 'w', encoding='utf-8') as f:
            json.dump(self._lessons, f, ensure_ascii=False, indent=2)

    def record_failure(
        self,
        novel_name: str,
        batch_num: int,
        error_type: str,
        details: str,
        forbidden_words_hit: Optional[List[str]] = None,
        content_snippet: str = ""
    ):
        """
        记录一次校验失败的详细信息。

        Args:
            novel_name: 小说名称
            batch_num: 批次号
            error_type: 错误类型 (forbidden_word / character_name / missing_volume / ai_rejected)
            details: 校验报告的详细文本
            forbidden_words_hit: 命中的禁词列表
            content_snippet: 问题内容片段（前200字）
        """
        lesson = {
            "timestamp": datetime.now().isoformat(),
            "novel_name": novel_name,
            "batch_num": batch_num,
            "error_type": error_type,
            "details": details[:500],  # 限制长度
            "forbidden_words_hit": forbidden_words_hit or [],
            "content_snippet": content_snippet[:200],
            "frequency": 1,  # 相同错误出现次数
        }

        # 检查是否有同类错误（相同 error_type + 相同 forbidden_words），合并频率
        merged = False
        for existing in self._lessons:
            if (existing["error_type"] == error_type
                and set(existing.get("forbidden_words_hit", [])) == set(forbidden_words_hit or [])):
                existing["frequency"] += 1
                existing["timestamp"] = lesson["timestamp"]  # 更新时间戳
                existing["details"] = lesson["details"]  # 用最新的细节
                merged = True
                break

        if not merged:
            self._lessons.append(lesson)

        self._save()
        print(f"   📝 错题本已记录: [{error_type}] (累计 {lesson['frequency'] if not merged else existing['frequency']} 次)")

    def get_lessons(
        self,
        novel_name: Optional[str] = None,
        top_k: int = 5,
        error_type: Optional[str] = None
    ) -> str:
        """
        获取格式化的历史教训文本，用于注入到 Prompt 中。

        Args:
            novel_name: 可选，筛选特定小说的教训（None=全部）
            top_k: 返回最多多少条
            error_type: 可选，筛选特定错误类型

        Returns:
            格式化的 Markdown 文本段落
        """
        if not self._lessons:
            return ""

        # 过滤
        filtered = self._lessons
        if error_type:
            filtered = [l for l in filtered if l["error_type"] == error_type]

        # 按频率降序排列（高频错误优先警告）
        filtered = sorted(filtered, key=lambda x: x.get("frequency", 1), reverse=True)

        # 取 top_k
        top = filtered[:top_k]
        if not top:
            return ""

        lines = ["【🧠 历史教训（系统从过往失败中自动提取，请务必避免重蹈覆辙）】"]
        for i, lesson in enumerate(top, 1):
            freq = lesson.get("frequency", 1)
            severity = "🔴 高频" if freq >= 3 else "🟡 中频" if freq >= 2 else "⚪ 低频"
            novel_tag = f"[{lesson['novel_name']}]" if lesson.get("novel_name") else ""

            if lesson["error_type"] == "forbidden_word":
                words = ", ".join(lesson.get("forbidden_words_hit", []))
                lines.append(f"{i}. {severity} {novel_tag} 禁词穿透「{words}」- 已被拦截 {freq} 次，严禁再犯。")
            elif lesson["error_type"] == "character_name":
                lines.append(f"{i}. {severity} {novel_tag} 角色名违规 - {lesson['details'][:100]}")
            elif lesson["error_type"] == "missing_volume":
                lines.append(f"{i}. {severity} {novel_tag} 卷号缺失 - 生成时丢掉了完整卷，必须严格输出完整卷数。")
            elif lesson["error_type"] == "ai_rejected":
                lines.append(f"{i}. {severity} {novel_tag} AI审核驳回 - {lesson['details'][:100]}")
            else:
                lines.append(f"{i}. {severity} {novel_tag} {lesson['error_type']} - {lesson['details'][:100]}")

        return "\n".join(lines) + "\n"

    def get_stats(self) -> Dict:
        """获取错题本统计信息"""
        if not self._lessons:
            return {"total": 0, "by_type": {}, "top_forbidden": []}

        by_type = {}
        all_forbidden = {}
        for l in self._lessons:
            t = l["error_type"]
            by_type[t] = by_type.get(t, 0) + l.get("frequency", 1)
            for w in l.get("forbidden_words_hit", []):
                all_forbidden[w] = all_forbidden.get(w, 0) + l.get("frequency", 1)

        top_forbidden = sorted(all_forbidden.items(), key=lambda x: x[1], reverse=True)[:10]

        return {
            "total": sum(l.get("frequency", 1) for l in self._lessons),
            "by_type": by_type,
            "top_forbidden": top_forbidden,
        }
