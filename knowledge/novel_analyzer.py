"""
小说分析管线 (Novel Analyzer)
==============================
从原著 TXT 文件中提取可复用的叙事 DNA：
- 角色原型 (Character Archetypes)
- 剧情模式 (Plot Patterns)
- 关系动态 (Relationship Dynamics)
- 节奏模板 (Pacing Templates)

用法:
    analyzer = NovelAnalyzer()
    analyzer.analyze_novel("/path/to/大王饶命", "大王饶命")
"""

import os
import re
import json
import glob
import logging
from typing import List, Dict, Optional, Tuple
from pathlib import Path

from knowledge.knowledge_store import (
    KnowledgeStore,
    CATEGORY_ARCHETYPE,
    CATEGORY_PLOT,
    CATEGORY_RELATIONSHIP,
    CATEGORY_PACING,
)

logger = logging.getLogger(__name__)


# LLM 提取用的系统提示词
ANALYSIS_SYSTEM_PROMPT = """你是一位资深的叙事结构分析师和创意写作顾问。
你的任务是从小说文本中提取可复用的叙事模式（Narrative DNA），这些模式将被用于指导 AI 写作系统生成新的、不同题材的小说。

关键原则：
1. 提取的是「抽象模式」而非具体剧情 — 要能移植到任何题材
2. 角色原型要剥离具体设定 — "嘴炮重情型主角" 而非 "任平生"
3. 剧情模式要结构化 — Setup→Development→Climax 而非具体情节
4. 只提取真正有价值的、经过验证的优秀模式"""


def _split_into_segments(text: str, max_segment_chars: int = 6000) -> List[str]:
    """
    将长文本按段落边界切分为多个片段。
    
    Args:
        text: 原始文本
        max_segment_chars: 每个片段的最大字符数
        
    Returns:
        片段列表
    """
    # 按双换行分段
    paragraphs = re.split(r'\n\s*\n', text)
    
    segments = []
    current_segment = ""
    
    for para in paragraphs:
        if len(current_segment) + len(para) > max_segment_chars and current_segment:
            segments.append(current_segment.strip())
            current_segment = para
        else:
            current_segment += "\n\n" + para if current_segment else para
    
    if current_segment.strip():
        segments.append(current_segment.strip())
    
    return segments if segments else [text[:max_segment_chars]]


def _build_extraction_prompt(text: str, novel_name: str, volume_num: int, 
                               segment_idx: int = 0, total_segments: int = 1) -> str:
    """构建单卷提取的 prompt"""
    segment_info = ""
    if total_segments > 1:
        segment_info = f"\n（这是第 {volume_num} 卷的第 {segment_idx+1}/{total_segments} 段）\n"
    
    return f"""请分析以下小说《{novel_name}》第 {volume_num} 卷的文本，提取可复用的叙事模式。
{segment_info}
=== 原文节选 ===
{text}
=== 原文结束 ===

请严格以 JSON 格式返回，包含以下 4 个类别的提取结果：

{{
  "archetypes": [
    {{
      "name": "原型名称（如'嘴炮重情型主角'，不要用具体人名）",
      "description": "150字以内的抽象描述，包含：性格特征、行为模式、成长弧线、核心矛盾。必须脱离具体设定，可移植到任何题材。",
      "tags": ["性格标签1", "性格标签2"]
    }}
  ],
  "plot_patterns": [
    {{
      "name": "模式名称（如'扮猪吃虎反转'）",
      "description": "150字以内描述该模式的结构：Setup(铺垫) → Development(发展) → Climax(高潮) → Resolution(收束)。描述抽象结构而非具体剧情。",
      "tags": ["结构标签1", "结构标签2"]
    }}
  ],
  "relationships": [
    {{
      "name": "关系类型名（如'互损型深情兄弟'）",
      "description": "100字以内描述：关系双方的角色类型、互动模式、张力来源、演变方向。",
      "tags": ["关系标签1", "关系标签2"]
    }}
  ],
  "pacing": [
    {{
      "name": "节奏模板名（如'日常喜剧突转危机'）",
      "description": "100字以内描述：松紧节奏分布、转折时机、情绪曲线走向。",
      "tags": ["节奏标签1"]
    }}
  ]
}}

规则：
1. 每个类别提取 1-3 个最有价值的模式（没有优秀模式可以空数组）
2. 名称必须通俗易懂，不用学术术语
3. 描述必须脱离原著具体人名和设定
4. 如果本段内容平淡无亮点，减少提取数量
5. 严格返回 JSON，不要多余文字"""


class NovelAnalyzer:
    """
    小说分析管线 — 从原著提取叙事 DNA
    """

    def __init__(self, knowledge_store: KnowledgeStore = None, llm_client=None):
        """
        Args:
            knowledge_store: 知识存储引擎（默认创建新实例）
            llm_client: LLM 客户端（默认使用系统默认客户端）
        """
        self.store = knowledge_store or KnowledgeStore()
        
        if llm_client:
            self.llm = llm_client
        else:
            import sys
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from utils.llm_client import get_default_client
            self.llm = get_default_client()

    # =========================================================================
    # 文件读取
    # =========================================================================

    def _load_novel_files(self, novel_dir: str) -> List[Tuple[int, str]]:
        """
        加载小说 TXT 文件，按卷号排序。
        
        支持格式：
        - 大王饶命_1.txt, 大王饶命_2.txt, ...
        - 001.txt, 002.txt, ...
        
        Returns:
            [(volume_number, file_content), ...]
        """
        txt_files = glob.glob(os.path.join(novel_dir, "*.txt"))
        if not txt_files:
            raise FileNotFoundError(f"在 {novel_dir} 中未找到 TXT 文件")
        
        volumes = []
        for fpath in txt_files:
            fname = os.path.basename(fpath)
            # 提取数字
            nums = re.findall(r'(\d+)', fname)
            if nums:
                vol_num = int(nums[-1])  # 取最后一个数字
                try:
                    with open(fpath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    volumes.append((vol_num, content))
                except Exception as e:
                    logger.warning(f"读取 {fpath} 失败: {e}")
        
        volumes.sort(key=lambda x: x[0])
        return volumes

    # =========================================================================
    # 断点续传
    # =========================================================================

    def _get_last_analyzed_volume(self, novel_name: str) -> int:
        """获取上次分析到的卷号，用于断点续传"""
        conn = self.store._get_conn()
        row = conn.execute(
            "SELECT analyzed_volumes FROM sources WHERE name=?",
            (novel_name,)
        ).fetchone()
        return row["analyzed_volumes"] if row else 0

    # =========================================================================
    # 核心分析
    # =========================================================================

    def analyze_novel(
        self,
        novel_dir: str,
        novel_name: str,
        max_volumes: int = 0,
        skip_existing: bool = True,
    ) -> Dict:
        """
        分析单本小说，提取叙事 DNA 并存入知识库。
        
        支持断点续传：如果之前分析中途失败，会从上次停止的卷号继续。
        
        Args:
            novel_dir: 小说 TXT 文件目录
            novel_name: 小说名称
            max_volumes: 最多分析几卷（0=全部）
            skip_existing: 是否跳过已完成的小说
            
        Returns:
            {"total_patterns": int, "by_category": dict, "errors": list}
        """
        # 检查是否已完成
        last_vol = self._get_last_analyzed_volume(novel_name)
        if skip_existing and last_vol > 0:
            # 检查是否已完成
            conn = self.store._get_conn()
            source_row = conn.execute(
                "SELECT analysis_status, total_volumes FROM sources WHERE name=?",
                (novel_name,)
            ).fetchone()
            
            if source_row and source_row["analysis_status"] == "completed":
                existing = self.store.get_patterns_by_source(novel_name)
                print(f"⚠️ 《{novel_name}》已完成分析 ({len(existing)} 个模式)，跳过（用 --force 强制重新分析）")
                return {"total_patterns": len(existing), "by_category": {}, "skipped": True}
            elif source_row:
                print(f"🔄 《{novel_name}》上次分析到第 {last_vol} 卷，从第 {last_vol + 1} 卷继续...")
        
        print(f"\n{'='*60}")
        print(f"📖 开始分析《{novel_name}》")
        print(f"{'='*60}")
        
        # 加载文件
        volumes = self._load_novel_files(novel_dir)
        total_vols = len(volumes)
        print(f"  找到 {total_vols} 个卷文件")
        
        # 断点续传：跳过已分析的卷
        if last_vol > 0:
            volumes = [(vn, vc) for vn, vc in volumes if vn > last_vol]
            print(f"  跳过前 {last_vol} 卷（已分析），从第 {volumes[0][0] if volumes else '?'} 卷开始")
        
        if max_volumes > 0:
            volumes = volumes[:max_volumes]
            print(f"  限制分析 {max_volumes} 卷")
        
        # 注册来源
        self.store.register_source(novel_name, novel_dir, total_vols)
        
        # 逐卷分析
        total_patterns = 0
        by_category = {
            CATEGORY_ARCHETYPE: 0,
            CATEGORY_PLOT: 0,
            CATEGORY_RELATIONSHIP: 0,
            CATEGORY_PACING: 0,
        }
        errors = []
        
        for idx, (vol_num, content) in enumerate(volumes):
            print(f"\n  [{idx+1}/{len(volumes)}] 分析第 {vol_num} 卷 ({len(content)} 字)...")
            
            try:
                patterns = self._analyze_single_volume(content, novel_name, vol_num)
                
                # 存入知识库
                if patterns:
                    self.store.add_patterns_batch(patterns)
                    for p in patterns:
                        by_category[p["category"]] = by_category.get(p["category"], 0) + 1
                    total_patterns += len(patterns)
                    print(f"    ✅ 提取 {len(patterns)} 个模式")
                else:
                    print(f"    ⚠️ 未提取到有效模式")
                
                # 逐卷更新进度（便于断点续传）
                self.store.update_source_progress(novel_name, vol_num, "in_progress")
                
            except Exception as e:
                error_msg = f"第{vol_num}卷分析失败: {str(e)}"
                errors.append(error_msg)
                print(f"    ❌ {error_msg}")
                # 记录进度但不标记完成，下次可以从这里继续
                self.store.update_source_progress(novel_name, vol_num - 1, "in_progress")
        
        if not errors or len(errors) < len(volumes):
            self.store.update_source_progress(novel_name, total_vols if not volumes else volumes[-1][0], "completed")
        
        print(f"\n{'='*60}")
        print(f"📊 分析完成: {total_patterns} 个模式")
        for cat, count in by_category.items():
            if count > 0:
                print(f"  - {cat}: {count}")
        if errors:
            print(f"  ❌ {len(errors)} 个错误")
        print(f"{'='*60}")
        
        return {
            "total_patterns": total_patterns,
            "by_category": by_category,
            "errors": errors,
        }

    def _analyze_single_volume(
        self, text: str, novel_name: str, volume_num: int
    ) -> List[Dict]:
        """
        分析单卷文本，返回提取的模式列表。
        
        对长文本使用分段策略：
        - <= 12000 字：直接分析
        - > 12000 字：按段落边界切分为多个 ~6000 字片段，逐段分析，合并结果
        """
        max_single_call_chars = 12000
        
        if len(text) <= max_single_call_chars:
            # 短文本直接分析
            return self._extract_patterns_from_text(text, novel_name, volume_num)
        
        # 长文本分段分析
        segments = _split_into_segments(text, max_segment_chars=6000)
        all_patterns = []
        
        for seg_idx, segment in enumerate(segments):
            prompt = _build_extraction_prompt(
                segment, novel_name, volume_num,
                segment_idx=seg_idx, total_segments=len(segments)
            )
            
            try:
                result = self.llm.generate_json(
                    prompt=prompt,
                    system_prompt=ANALYSIS_SYSTEM_PROMPT,
                    temperature=0.3,
                )
                patterns = self._parse_extraction_result(result, novel_name, volume_num)
                all_patterns.extend(patterns)
            except Exception as e:
                logger.warning(f"第{volume_num}卷第{seg_idx+1}段分析失败: {e}")
        
        return all_patterns

    def _extract_patterns_from_text(
        self, text: str, novel_name: str, volume_num: int
    ) -> List[Dict]:
        """单次 LLM 调用提取模式"""
        prompt = _build_extraction_prompt(text, novel_name, volume_num)
        
        try:
            result = self.llm.generate_json(
                prompt=prompt,
                system_prompt=ANALYSIS_SYSTEM_PROMPT,
                temperature=0.3,
            )
        except Exception as e:
            logger.error(f"LLM 调用失败: {e}")
            raise
        
        return self._parse_extraction_result(result, novel_name, volume_num)

    def _parse_extraction_result(
        self, result: Dict, novel_name: str, volume_num: int
    ) -> List[Dict]:
        """解析 LLM 返回的 JSON 提取结果"""
        patterns = []
        
        category_map = {
            "archetypes": CATEGORY_ARCHETYPE,
            "plot_patterns": CATEGORY_PLOT,
            "relationships": CATEGORY_RELATIONSHIP,
            "pacing": CATEGORY_PACING,
        }
        
        for key, category in category_map.items():
            for item in result.get(key, []):
                if item.get("name") and item.get("description"):
                    patterns.append({
                        "category": category,
                        "name": item["name"],
                        "description": item["description"],
                        "source_novel": novel_name,
                        "source_volume": volume_num,
                        "tags": item.get("tags", []),
                    })
        
        return patterns
