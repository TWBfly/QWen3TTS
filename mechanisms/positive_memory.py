"""
正向激励模块 (Positive Memory / 高分案例库)
=============================================
收录高分通过的大纲片段作为 Few-Shot 范例，
在后续生成 Prompt 时按需注入，引导生成更优质的内容。
"""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional


GLOBAL_MEMORY_DIR = Path(__file__).parent.parent / "novel_data" / "_global_memory"


class PositiveMemory:
    """高分案例库：收录优秀范例，生成 Few-Shot 提示"""

    def __init__(self):
        self.memory_dir = GLOBAL_MEMORY_DIR
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.memory_dir / "positive_exemplars.json"
        self._exemplars = self._load()

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
            json.dump(self._exemplars, f, ensure_ascii=False, indent=2)

    def record_success(
        self,
        novel_name: str,
        batch_num: int,
        draft_snippet: str,
        tags: Optional[List[str]] = None,
        score: int = 100
    ):
        """
        记录一次成功通过校验的大纲片段。

        Args:
            novel_name: 小说名称
            batch_num: 批次号
            draft_snippet: 大纲片段（截取前800字符作为范例）
            tags: 标签 (如 ['权谋', '战争', '伏笔回收'])
            score: 校验得分 (默认100)
        """
        exemplar = {
            "timestamp": datetime.now().isoformat(),
            "novel_name": novel_name,
            "batch_num": batch_num,
            "score": score,
            "tags": tags or [],
            "draft_snippet": draft_snippet[:800],
        }

        self._exemplars.append(exemplar)

        # 只保留最近 200 条，淘汰低分的
        if len(self._exemplars) > 200:
            self._exemplars = sorted(
                self._exemplars, key=lambda x: x.get("score", 0), reverse=True
            )[:200]

        self._save()
        print(f"   ⭐ 高分案例库已收录: 第{batch_num}卷 (得分: {score})")

    def get_exemplars(
        self,
        tags: Optional[List[str]] = None,
        top_k: int = 2,
        exclude_novel: Optional[str] = None
    ) -> str:
        """
        获取格式化的优质范例文本，用于 Few-Shot 注入。

        Args:
            tags: 可选，按标签筛选
            top_k: 返回最多多少条
            exclude_novel: 可选，排除当前小说的范例（鼓励跨书学习）

        Returns:
            格式化的 Markdown 文本段落
        """
        if not self._exemplars:
            return ""

        filtered = self._exemplars
        if exclude_novel:
            filtered = [e for e in filtered if e.get("novel_name") != exclude_novel]
        if tags:
            tag_set = set(tags)
            filtered = [e for e in filtered if tag_set & set(e.get("tags", []))]

        # 按分数降序
        filtered = sorted(filtered, key=lambda x: x.get("score", 0), reverse=True)
        top = filtered[:top_k]

        if not top:
            return ""

        lines = ["【⭐ 优质范例（系统从过往高分大纲中自动提取，供参考叙事结构）】"]
        for i, ex in enumerate(top, 1):
            lines.append(f"\n--- 范例 {i} (来自《{ex['novel_name']}》第{ex['batch_num']}卷, 得分 {ex['score']}) ---")
            lines.append(ex["draft_snippet"])
            lines.append("--- 范例结束 ---")

        return "\n".join(lines) + "\n"

    def get_stats(self) -> Dict:
        """获取案例库统计信息"""
        if not self._exemplars:
            return {"total": 0, "avg_score": 0, "novels": []}

        novels = list(set(e["novel_name"] for e in self._exemplars))
        avg = sum(e.get("score", 0) for e in self._exemplars) / len(self._exemplars)

        return {
            "total": len(self._exemplars),
            "avg_score": round(avg, 1),
            "novels": novels,
        }
