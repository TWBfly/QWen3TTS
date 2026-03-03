"""
Logic Verifier (Agent D) - 逻辑验证官
职责：拥有上帝视角，进行 OOC 检测、Bug 检测、战力崩坏检测。
"""

from typing import Dict, Any, List, Optional
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.base_agent import BaseAgent
from models import StoryBible, ChapterOutline
from config import Config

class LogicVerifier(BaseAgent):
    """Logic Verifier - 逻辑验证官"""
    
    def __init__(self, llm_client=None, rag_manager=None, context_manager=None):
        super().__init__(
            name="LogicVerifier",
            role="逻辑验证官 - 负责逻辑风控",
            llm_client=llm_client,
            rag_manager=rag_manager,
            context_manager=context_manager
        )
        
    def get_system_prompt(self) -> str:
        return """你是一位严苛的【逻辑验证官】(The Verifier) 和【设定卫士】。
你的职责是审查【剧情编织者】生成的草稿，寻找逻辑漏洞、人设崩坏(OOC)和战力失衡。

**审查标准 (Aletheia Protocol)**:
1.  **OOC 检测 (Out of Character)**: 角色的行为是否与其性格档案矛盾？
2.  **世界观一致性**: 剧情是否违反了已有的世界设定（如地理、魔法规则）？
3.  **连续性检测**: 道具依然存在？伤口是否突然消失？时间线是否错乱？
4.  **战力合理性**: 是否出现机械降神或战力崩溃？

**行动**:
-   如果发现**严重错误**：直接打回重写 (Reject)。
-   如果发现**轻微瑕疵**：提出修订建议 (Suggest)。
-   如果逻辑**严密**：通过 (Pass)。
"""

    def process(self, bible: StoryBible, **kwargs) -> Any:
        pass

    def verify_outline(
        self, 
        bible: StoryBible, 
        chapter_outline: ChapterOutline
    ) -> Dict[str, Any]:
        """
        验证章节大纲
        """
        self.log(f"正在审查第 {chapter_outline.chapter_number} 章的逻辑...")
        
        # 获取相关世界观规则
        world_rules = bible.world_settings.physics_rules
        
        prompt = f"""请严格审查以下章节大纲的逻辑性。

**章节大纲**:
标题: {chapter_outline.title}
剧情: {chapter_outline.summary}
详细内容: 
{chapter_outline.detailed_outline}

**涉及角色及设定**:
{self._format_character_profiles(bible, chapter_outline.characters)}

**世界观规则**:
{json.dumps(world_rules, ensure_ascii=False)}

**违禁词检测**: 检查是否包含 {Config.FORBIDDEN_CONCEPTS}

**审查任务**:
请像一个挑剔的逻辑学家一样，寻找以下问题：
1. 角色行为是否 OOC？
2. 是否与前文冲突（如死人复活、道具瞬移）？
3. 战力是否崩坏？(任何角色每卷战力成长不得超过 5%，不得超越战力天花板 {bible.world_settings.power_ceiling})
4. 是否通过"强行降智"来推动剧情？
5. 是否使用了“命运”、“巧合”、“天道”等机械降神手段？(严禁！)

**返回格式(JSON)**:
{{
    "status": "PASS" | "REJECT" | "WARN",
    "issues": [
        {{
            "type": "OOC/Logic/Continuity/Power/Forbidden",
            "description": "具体问题描述",
            "severity": "High/Medium/Low",
            "suggestion": "修改建议"
        }}
    ],
    "review_summary": "总体评价"
}}"""
        
        return self.generate_json(prompt, temperature=0.1)  # 低温以保证严谨

    def _format_character_profiles(self, bible: StoryBible, char_names: List[str]) -> str:
        profiles = []
        for name in char_names:
            char = bible.characters.get(name)
            if char:
                profiles.append(f"- {name}: 性格[{', '.join(char.personality_keywords)}], 状态[{char.state.value}]")
        return "\n".join(profiles)

