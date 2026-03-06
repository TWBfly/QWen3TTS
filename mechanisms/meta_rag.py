"""
跨小说宇宙级知识图谱 (Meta-RAG / 全局作者大脑)
=================================================
超越单本小说的经验积累系统。当用户写完一本小说后，
系统将核心经验沉淀到全局知识库。在写新书时，
可跨库调取相似场景的创作经验。
"""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional


GLOBAL_MEMORY_DIR = Path(__file__).parent.parent / "novel_data" / "_global_memory"


class MetaRAG:
    """全局作者大脑：跨小说知识沉淀与检索"""

    def __init__(self):
        self.memory_dir = GLOBAL_MEMORY_DIR
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.memory_dir / "meta_knowledge.json"
        self._knowledge = self._load()

    def _load(self) -> Dict:
        if self.db_path.exists():
            try:
                with open(self.db_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {
            "completed_novels": [],
            "scene_patterns": [],  # 场景模式库
            "character_archetypes": [],  # 角色原型库
            "narrative_techniques": [],  # 叙事技法库
        }

    def _save(self):
        with open(self.db_path, 'w', encoding='utf-8') as f:
            json.dump(self._knowledge, f, ensure_ascii=False, indent=2)

    def register_novel_completion(
        self,
        novel_name: str,
        setting: str,
        tags: List[str],
        total_volumes: int,
        key_learnings: List[str],
        best_techniques: List[str],
        character_insights: List[str]
    ):
        """
        注册一本小说的完成信息，将关键经验沉淀到全局知识库。

        Args:
            novel_name: 小说名称
            setting: 背景设定
            tags: 标签
            total_volumes: 总卷数
            key_learnings: 关键学习要点
            best_techniques: 最佳叙事技法
            character_insights: 角色塑造心得
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "novel_name": novel_name,
            "setting": setting,
            "tags": tags,
            "total_volumes": total_volumes,
            "key_learnings": key_learnings,
            "best_techniques": best_techniques,
            "character_insights": character_insights,
        }

        # 检查是否已存在，更新
        existing = [n for n in self._knowledge["completed_novels"]
                    if n["novel_name"] == novel_name]
        if existing:
            idx = self._knowledge["completed_novels"].index(existing[0])
            self._knowledge["completed_novels"][idx] = entry
        else:
            self._knowledge["completed_novels"].append(entry)

        # 提取场景模式
        for technique in best_techniques:
            self._knowledge["narrative_techniques"].append({
                "source": novel_name,
                "technique": technique,
                "tags": tags,
            })

        for insight in character_insights:
            self._knowledge["character_archetypes"].append({
                "source": novel_name,
                "insight": insight,
                "tags": tags,
            })

        # 限制总量
        self._knowledge["narrative_techniques"] = self._knowledge["narrative_techniques"][-100:]
        self._knowledge["character_archetypes"] = self._knowledge["character_archetypes"][-100:]

        self._save()
        print(f"   🧠 全局知识库已更新: 《{novel_name}》的创作经验已沉淀")

    def query_cross_novel(
        self,
        current_novel: str,
        batch_num: int,
        tags: Optional[List[str]] = None,
        top_k: int = 3
    ) -> str:
        """
        跨小说检索相关经验，注入到 Prompt 中。

        Args:
            current_novel: 当前正在写的小说
            batch_num: 当前批次
            tags: 当前小说的标签
            top_k: 返回条目数

        Returns:
            格式化的 Markdown 段落
        """
        completed = [n for n in self._knowledge.get("completed_novels", [])
                     if n["novel_name"] != current_novel]

        if not completed:
            return ""

        lines = ["【🌐 跨作品经验（系统从已完成小说中自动提取的创作智慧）】"]

        # 提取关键学习
        all_learnings = []
        for novel in completed:
            for learning in novel.get("key_learnings", []):
                all_learnings.append(f"[{novel['novel_name']}] {learning}")

        if all_learnings:
            lines.append("\n📚 关键经验:")
            for i, l in enumerate(all_learnings[:top_k], 1):
                lines.append(f"  {i}. {l}")

        # 提取与当前阶段相关的叙事技法
        techniques = self._knowledge.get("narrative_techniques", [])
        if techniques:
            # 按标签相关度排序
            if tags:
                tag_set = set(tags)
                scored = [(t, len(tag_set & set(t.get("tags", [])))) for t in techniques]
                scored = sorted(scored, key=lambda x: x[1], reverse=True)
                relevant = [t for t, s in scored if s > 0][:top_k]
            else:
                relevant = techniques[-top_k:]

            if relevant:
                lines.append("\n🎭 叙事技法参考:")
                for i, tech in enumerate(relevant, 1):
                    lines.append(f"  {i}. [{tech['source']}] {tech['technique']}")

        # 角色塑造心得
        archetypes = self._knowledge.get("character_archetypes", [])
        if archetypes and batch_num <= 5:  # 前5卷注入角色经验
            recent = archetypes[-2:]
            if recent:
                lines.append("\n👤 角色塑造心得:")
                for a in recent:
                    lines.append(f"  - [{a['source']}] {a['insight']}")

        if len(lines) <= 1:
            return ""

        return "\n".join(lines) + "\n"

    def generate_novel_summary_prompt(self, novel_name: str, output_path: str) -> str:
        """
        生成用于总结一本已完成小说的 Prompt。
        IDE Agent 读取此 Prompt 后会生成结构化的总结。

        Args:
            novel_name: 小说名称
            output_path: 大纲文件路径

        Returns:
            用于总结的 Prompt 文本
        """
        return f"""你是一位资深小说评论家和创作顾问。请阅读以下小说大纲全文，然后提取关键经验。

【任务】为《{novel_name}》生成创作经验总结报告。

请严格按以下 JSON 格式输出：

```json
{{
  "key_learnings": [
    "学习要点1（一句话）",
    "学习要点2（一句话）",
    "..."
  ],
  "best_techniques": [
    "最佳叙事技法1",
    "最佳叙事技法2",
    "..."
  ],
  "character_insights": [
    "角色塑造心得1",
    "角色塑造心得2",
    "..."
  ],
  "pitfalls_to_avoid": [
    "需要避免的陷阱1",
    "需要避免的陷阱2",
    "..."
  ]
}}
```

每个类别请提取 3-5 条精炼的要点。
请阅读大纲文件: {output_path}
"""

    def get_stats(self) -> Dict:
        """获取知识库统计"""
        return {
            "completed_novels": len(self._knowledge.get("completed_novels", [])),
            "techniques_count": len(self._knowledge.get("narrative_techniques", [])),
            "archetypes_count": len(self._knowledge.get("character_archetypes", [])),
        }
