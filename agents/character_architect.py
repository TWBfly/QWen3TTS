"""
Character Architect (角色架构师) - 负责角色管理、弧光监测、铺垫设计
"""

from typing import Dict, Any, List
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.base_agent import BaseAgent
from models import StoryBible, CharacterCard


class CharacterArchitect(BaseAgent):
    """Character Architect - 角色架构师"""
    
    def __init__(self, llm_client=None):
        super().__init__(
            name="CharacterArchitect",
            role="角色架构师 - 负责角色管理、弧光监测、铺垫设计",
            llm_client=llm_client
        )
    
    def get_system_prompt(self) -> str:
        return """你是一位专业的角色架构师(Character Architect),负责管理小说中的所有人物。

你的职责:
1. **动态卡片管理**: 维护所有登场人物的详细档案(姓名、身份、位置、能力、性格、心理状态)
2. **弧光监测**: 检查人物行为是否符合其当前心理状态和既往经历
3. **铺垫设计**: 在新人物登场前 5-10 章,提出铺垫建议

**核心人物设计原则 (特别是反派)**:
-   **严禁反派降智**: 反派绝对不能是给主角送经验的"经验包"。
-   **反派魅力**: 反派必须有自己的**愿景**、**理想**和**道**。他们坚信自己是正确的。
-   **复杂性**: 反派要有魅力，有让人信服的动机（救世？复仇？秩序？）。
-   **去脸谱化**: 拒绝为了坏而坏。

你的工作原则:
- 人物行为必须符合性格设定和心理状态
- 重视人物成长轨迹,避免 OOC (Out of Character)
- 确保重要人物有充分的铺垫,不能突兀登场
- 维护人物关系网络的一致性

在分析人物时,请特别关注:
1. 性格坐标的变化(如:天真 -> 成熟)
2. 心理状态的合理演进
3. 重大事件对人物的影响"""
    
    def process(self, bible: StoryBible, **kwargs) -> Any:
        """处理任务"""
        pass
    
    def create_character(
        self,
        name: str,
        identity: str,
        personality_keywords: List[str],
        power_level: int,
        role_in_story: str,
        first_appearance_chapter: int
    ) -> CharacterCard:
        """
        创建角色卡片
        
        Args:
            name: 姓名
            identity: 身份
            personality_keywords: 性格关键词
            power_level: 战力值
            role_in_story: 在故事中的作用
            first_appearance_chapter: 首次登场章节
            
        Returns:
            角色卡片
        """
        self.log(f"创建角色: {name}")
        
        prompt = f"""请为以下角色创建详细的人物设定。

**基本信息**:
- 姓名: {name}
- 身份: {identity}
- 性格关键词: {', '.join(personality_keywords)}
- 战力值: {power_level}
- 角色定位: {role_in_story}
- 首次登场: 第 {first_appearance_chapter} 章

**核心要求 (必须详细,尤其是反派)**:
1. **人物小传 (Biography)**: 至少 500 字。包含角色的前史、核心欲望、性格成因。
2. **高光时刻 (Highlights)**: 设计 3-5 个该角色在未来故事中可能展现的震撼时刻或反差萌时刻。
3. **深度关系 (Relationships)**: 详细描述由于主角及其他主要角色的关系（不仅仅是标签，要有情感羁绊和互动模式）。
4. **属性设定**: 
    - 性格坐标系
    - 初始心理状态
    - 特殊能力 (2-3个)
    - 初始位置

**特别指令 (如果角色是反派/对手)**:
- 必须回答: **他的理想是什么？他的"道"是什么？**
- 必须回答: **他认为自己为什么是正义的？**
- 必须设计: **他的人格魅力点在哪里？**
- **严禁**: 设计成无脑挑衅的经验包。

请以 JSON 格式返回:
{{
    "cultivation_stage": "修炼境界",
    "special_abilities": ["能力1", "能力2"],
    "psychological_state": "初始心理状态",
    "personality_coordinates": {{
        "naive_to_mature": 0.0-1.0,
        "kind_to_ruthless": 0.0-1.0
    }},
    "current_location": "初始位置",
    "biography": "人物小传全文...",
    "highlights": ["时刻1: ...", "时刻2: ..."],
    "detailed_relationships": "与主角...; 与反派..."
}}"""
        
        result = self.generate_json(prompt, temperature=0.8)
        
        # 创建角色卡片
        character = CharacterCard(
            name=name,
            identity=identity,
            personality_keywords=personality_keywords,
            power_level=power_level,
            first_appearance_chapter=first_appearance_chapter,
            cultivation_stage=result.get("cultivation_stage", ""),
            special_abilities=result.get("special_abilities", []),
            psychological_state=result.get("psychological_state", ""),
            personality_coordinates=result.get("personality_coordinates", {}),
            current_location=result.get("current_location", ""),
            biography=result.get("biography", "未生成小传"),
            highlights=result.get("highlights", []),
            detailed_relationships=result.get("detailed_relationships", "")
        )
        
        self.log(f"角色 {name} 创建完成")
        return character
    
    def check_character_consistency(
        self,
        bible: StoryBible,
        character_name: str,
        proposed_action: str,
        context: str
    ) -> Dict[str, Any]:
        """
        检查角色行为一致性
        
        Args:
            bible: 故事圣经
            character_name: 角色名称
            proposed_action: 拟定的行为
            context: 上下文
            
        Returns:
            检查结果
        """
        character = bible.get_character(character_name)
        if not character:
            return {"consistent": False, "reason": f"角色 {character_name} 不存在"}
        
        self.log(f"检查角色 {character_name} 的行为一致性...")
        
        prompt = f"""请检查以下角色行为是否符合人设。

**角色信息**:
- 姓名: {character.name}
- 性格关键词: {', '.join(character.personality_keywords)}
- 当前心理状态: {character.psychological_state}
- 性格坐标: {character.personality_coordinates}
- 重大经历: {character.major_events[-5:] if character.major_events else '无'}

**拟定行为**:
{proposed_action}

**上下文**:
{context}

**要求**:
判断该行为是否符合角色的性格和当前心理状态。

请以 JSON 格式返回:
{{
    "consistent": true/false,
    "confidence": 0.0-1.0,
    "reason": "判断理由",
    "suggestions": "修改建议(如果不一致)"
}}"""
        
        result = self.generate_json(prompt, temperature=0.5)
        self.log(f"一致性检查完成: {'通过' if result['consistent'] else '不通过'}")
        return result
    
    def suggest_character_development(
        self,
        bible: StoryBible,
        character_name: str,
        upcoming_events: str
    ) -> Dict[str, Any]:
        """
        建议角色发展方向
        
        Args:
            bible: 故事圣经
            character_name: 角色名称
            upcoming_events: 即将发生的事件
            
        Returns:
            发展建议
        """
        character = bible.get_character(character_name)
        if not character:
            return {"error": f"角色 {character_name} 不存在"}
        
        self.log(f"为角色 {character_name} 规划发展方向...")
        
        prompt = f"""基于即将发生的事件,建议角色的发展方向。

**角色当前状态**:
- 姓名: {character.name}
- 性格坐标: {character.personality_coordinates}
- 弧光进度: {character.character_arc_progress}
- 心理状态: {character.psychological_state}

**即将发生的事件**:
{upcoming_events}

**要求**:
1. 建议性格坐标的变化方向
2. 建议新的心理状态
3. 建议需要添加的重大经历

请以 JSON 格式返回:
{{
    "personality_coordinate_changes": {{
        "坐标名": 变化量(正负浮点数)
    }},
    "new_psychological_state": "新心理状态",
    "major_event_to_add": "需要记录的重大经历",
    "reasoning": "建议理由"
}}"""
        
        result = self.generate_json(prompt, temperature=0.6)
        self.log("发展建议生成完成")
        return result
    
    def plan_character_foreshadowing(
        self,
        bible: StoryBible,
        character_name: str,
        planned_appearance_chapter: int
    ) -> Dict[str, Any]:
        """
        规划角色铺垫
        
        Args:
            bible: 故事圣经
            character_name: 角色名称
            planned_appearance_chapter: 计划登场章节
            
        Returns:
            铺垫计划
        """
        self.log(f"规划角色 {character_name} 的铺垫...")
        
        current_chapter = bible.current_chapter
        chapters_ahead = planned_appearance_chapter - current_chapter
        
        if chapters_ahead < 5:
            self.log(f"警告: 距离登场只有 {chapters_ahead} 章,铺垫时间可能不足")
        
        prompt = f"""请为即将登场的角色设计铺垫方案。

**角色信息**:
- 姓名: {character_name}
- 计划登场: 第 {planned_appearance_chapter} 章
- 当前进度: 第 {current_chapter} 章
- 可用铺垫章节: {chapters_ahead} 章

**要求**:
设计至少 3 次铺垫,通过以下方式:
1. 路人闲聊提及
2. 新闻/传说/传闻
3. 其他角色的对话
4. 环境描写中的暗示

请以 JSON 格式返回:
{{
    "foreshadowing_plan": [
        {{
            "chapter": 章节号,
            "method": "铺垫方式",
            "content": "具体铺垫内容(50字以内)"
        }},
        ...
    ],
    "total_mentions": 总提及次数
}}"""
        
        result = self.generate_json(prompt, temperature=0.7)
        self.log(f"铺垫计划完成,共 {result.get('total_mentions', 0)} 次提及")
        return result
