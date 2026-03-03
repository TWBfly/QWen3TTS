"""
The Architect (Agent A) - 结构解析与仿写师
职责：分析参考内容，提取叙事节奏和结构模版，不涉及具体内容。
"""

from typing import Dict, Any, List, Optional
import sys
import os
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.base_agent import BaseAgent
from models import StoryBible
from config import Config

class TheArchitect(BaseAgent):
    """The Architect - 结构解析师"""
    
    def __init__(self, llm_client=None):
        super().__init__(
            name="TheArchitect",
            role="结构解析与仿写师 - 提取叙事节奏模版",
            llm_client=llm_client
        )
        
    def get_system_prompt(self) -> str:
        return """你是一位精通叙事学的【架构解析师】(The Architect)。
你的职责是阅读参考文本，剥离具体的名词（人名、地名、招式），仅提取出【叙事语法】(Narrative Grammar)和【节奏模版】。

**工作原则**:
1.  **抽象化**: 将"萧炎被退婚"抽象为"[公开场合的尊严剥夺] -> [契约解除] -> [确立复仇目标]"。
2.  **去名词化**: 严禁在输出中包含参考文本的具体名词。使用符号如 {{Protagonist}}, {{Antagonist}}, {{Event}} 代替。
3.  **节奏感知**: 标注情绪的起伏（如：压抑 -> 爆发 -> 冷却）。

**输出目标**:
为【剧情编织者】提供一个填充了变量的结构骨架。

**负面约束 (Negative Constraints)**:
1. 禁止使用“命运安排”、“巧合”来解决困境。
2. 禁止引入“机械降神”或“天道干预”。
3. 严格遵守【叙事聚光灯】原则：本卷只聚焦于 2-3 条核心叙事线，不要面面俱到。
"""

    def process(self, bible: StoryBible, **kwargs) -> Any:
        # Architect 主要由 GenerationLoop 调用 analyze_reference
        pass

    def analyze_reference(self, reference_text: str) -> Dict[str, Any]:
        """
        分析参考文本，提取结构
        """
        self.log("正在解析参考文本结构...")
        
        prompt = f"""请分析以下参考文本，提取其【叙事结构模版】。

**参考文本**:
{reference_text}

**要求**:
1.  **提取核心节拍**: 将剧情分解为 3-5 个核心节拍 (Beats)。
2.  **识别功能**: 每个节拍起到了什么叙事作用？(如：建立共情、引入危机、展示金手指)。
3.  **抽象化**: 使用变量符号 {{Protagonist}}, {{Antagonist}}, {{Location}}, {{Item}} 等。
4.  **情绪曲线**: 标注每一段的情绪极性 (+/-) 和强度 (1-10)。

**返回格式(JSON)**:
{{
    "structure_name": "结构的名称 (如: 退婚流开篇)",
    "pacing_beats": [
        {{
            "beat_name": "节拍名称",
            "narrative_function": "叙事功能描述",
            "abstract_template": "抽象化的剧情描述 (含变量)",
            "emotional_polarity": "Positive/Negative",
            "intensity": 1-10
        }},
        ...
    ],
    "key_elements": ["需要的一个核心道具", "需要的一个对立角色类型", "需要的一个封闭环境"]
}}"""
        
        return self.generate_json(prompt, temperature=0.3)
