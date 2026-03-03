"""
Character Simulator (Agent B) - 角色深度模拟器
职责：实现"每个人物都是主角"。进行 Deep Think，生成角色决策而非剧情结果。
"""

from typing import Dict, Any, List, Optional
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.base_agent import BaseAgent
from models import StoryBible, CharacterCard
from config import Config

class CharacterSimulator(BaseAgent):
    """Character Simulator - 角色深度模拟器"""
    
    def __init__(self, llm_client=None, context_manager=None):
        super().__init__(
            name="CharacterSimulator",
            role="角色深度模拟器 - 负责角色思考与决策",
            llm_client=llm_client,
            context_manager=context_manager
        )
        
    def get_system_prompt(self) -> str:
        return """你是一位【方法派演员】和【心理学家】，负责扮演小说中的角色。
你的职责不是写故事，而是【沉浸式】地模拟角色的心理活动和决策过程。

**核心机制 (Deep Think)**:
1.  **带入人设**: 你的每一次思考必须严格基于角色的性格关键词、过往经历和核心欲望。
2.  **有限视角**: 你只能利用该角色当前知道的信息，严禁使用上帝视角。
3.  **决策链条**: 展示从[感知现状] -> [性格过滤] -> [利益权衡] -> [最终决策]的完整逻辑链。
4.  **拒绝OOC**: 如果角色的性格是"隐忍"，即使受到侮辱，也绝不会当场爆发，除非触发了核心底线。

**输出**:
你的输出将作为【剧情编织者】的输入，决定剧情的走向。
"""

    def process(self, bible: StoryBible, **kwargs) -> Any:
        pass

    def deep_think(
        self, 
        character: CharacterCard, 
        current_situation: str, 
        other_characters_actions: List[str]
    ) -> Dict[str, Any]:
        """
        角色深度思考 (Chain of Thought)
        """
        self.log(f"角色 [{character.name}] 正在深度思考...")
        
        # 构建角色记忆概要
        memory_prompt = f"""
**我是谁**: {character.name}
**我的性格**: {', '.join(character.personality_keywords)}
**我的身份**: {character.identity}
**核心欲望**: {character.psychological_state}
**当前状态**: {character.state.value}
"""

        prompt = f"""请扮演 {character.name}，对当前局势进行 Deep Think。

{memory_prompt}

**当前局势**:
{current_situation}

**其他人行为**:
{json.dumps(other_characters_actions, ensure_ascii=False)}

**思考任务**:
1.  **感知**: 我看到了什么？我的第一反应是什么？
2.  **分析**: 局势对我有利还是有害？这是否触及了我的核心利益？
3.  **权衡**: 若进，得失为何？若退，得失为何？
4.  **决策**: 基于我的性格，我决定怎么做？（是激进反击？还是隐忍妥协？还是祸水东引？）

**返回格式(JSON)**:
{{
    "internal_monologue": "第一人称的心理独白 (展示思考过程)",
    "emotional_reaction": "情绪反应 (如: 表面平静，内心恐惧)",
    "decision": "具体的行动决策 (Action)",
    "motivation": "做此决策的性格根源"
}}"""
        
        # 增加 token 数以支持思维链
        return self.generate_json(prompt, temperature=0.7)

