"""
配置自动演化模块 (Config Evolver / 配置热生长)
================================================
分析校验失败的内容，自动提取新的违规模式，
将新禁词与正则追加到持久化配置中，使系统自动扎紧防线。
"""

import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional


GLOBAL_MEMORY_DIR = Path(__file__).parent.parent / "novel_data" / "_global_memory"


class ConfigEvolver:
    """配置热生长：从失败中提取新禁词并持久化"""

    def __init__(self):
        self.memory_dir = GLOBAL_MEMORY_DIR
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.memory_dir / "evolved_config.json"
        self._config = self._load()

    def _load(self) -> Dict:
        if self.db_path.exists():
            try:
                with open(self.db_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {
            "evolved_forbidden_words": [],
            "evolved_character_patterns": [],
            "candidate_words": {},  # word -> count, 累积达到阈值才正式加入
            "evolution_log": [],
        }

    def _save(self):
        with open(self.db_path, 'w', encoding='utf-8') as f:
            json.dump(self._config, f, ensure_ascii=False, indent=2)

    def learn_new_pattern(self, content: str, error_type: str, details: str = "", setting: str = "架空古代"):
        """
        从一次校验失败中学习新的违规模式。

        当同一个词汇在多次失败中反复出现但不在当前禁词列表中时，
        将其提升为新的禁词。

        Args:
            content: 被拒绝的内容
            error_type: 错误类型
            details: 错误详情
            setting: 当前世界观设定
        """
        from config import Config

        existing_forbidden = set(Config.get_forbidden_concepts(setting))
        existing_forbidden.update(self._config.get("evolved_forbidden_words", []))

        # 提取可疑词汇：出现在被拒内容中且与已有禁词共现的 2-4 字词
        suspicious = self._extract_suspicious_words(content, existing_forbidden)

        candidates = self._config.get("candidate_words", {})
        newly_promoted = []

        for word in suspicious:
            if word in existing_forbidden:
                continue
            candidates[word] = candidates.get(word, 0) + 1
            # 阈值：同一个词汇在 3 次不同的失败中出现，则自动升级为禁词
            if candidates[word] >= 3:
                self._config["evolved_forbidden_words"].append(word)
                newly_promoted.append(word)
                del candidates[word]  # 从候选中移除

        self._config["candidate_words"] = candidates

        if newly_promoted:
            self._config["evolution_log"].append({
                "timestamp": datetime.now().isoformat(),
                "action": "promote_forbidden_words",
                "words": newly_promoted,
                "reason": f"在 3 次以上校验失败中反复出现"
            })
            print(f"   🧬 配置进化: 新增禁词 {newly_promoted}")

        self._save()

    def _extract_suspicious_words(self, content: str, existing: set) -> List[str]:
        """从内容中提取可疑的重复性词汇"""
        # 简单方法：提取2-4字的中文词组，与已有禁词做上下文邻近分析
        pattern = re.compile(r'[\u4e00-\u9fff]{2,4}')
        words = pattern.findall(content)

        # 统计词频
        counter = Counter(words)

        # 筛选：出现 3 次以上、且与已有禁词在 50 字范围内共现的
        suspicious = []
        for word, count in counter.most_common(20):
            if word in existing or count < 3:
                continue
            # 检查是否与禁词共现
            for forbidden in existing:
                if forbidden in content:
                    idx = content.find(forbidden)
                    nearby = content[max(0, idx - 50): idx + 50]
                    if word in nearby:
                        suspicious.append(word)
                        break

        return suspicious[:5]  # 最多返回 5 个

    def get_evolved_forbidden_words(self) -> List[str]:
        """获取所有通过进化机制新增的禁词"""
        return self._config.get("evolved_forbidden_words", [])

    def get_evolved_character_patterns(self) -> List[str]:
        """获取所有通过进化机制新增的角色名正则"""
        return self._config.get("evolved_character_patterns", [])

    def get_all_forbidden_concepts(self, setting: str = "架空古代") -> List[str]:
        """获取合并后的完整禁词列表（世界观禁词 + 进化禁词）"""
        from config import Config
        return list(set(Config.get_forbidden_concepts(setting) + self.get_evolved_forbidden_words()))

    def get_stats(self) -> Dict:
        """获取进化统计"""
        return {
            "evolved_words_count": len(self._config.get("evolved_forbidden_words", [])),
            "candidate_count": len(self._config.get("candidate_words", {})),
            "evolution_events": len(self._config.get("evolution_log", [])),
        }
