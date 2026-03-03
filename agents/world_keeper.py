"""
World & Logic Keeper (逻辑守门人) - 负责世界观管理、战力体系、逻辑校验
"""

from typing import Dict, Any, List
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.base_agent import BaseAgent
from models import StoryBible, WorldSettings


class WorldKeeper(BaseAgent):
    """World & Logic Keeper - 逻辑守门人"""
    
    def __init__(self, llm_client=None):
        super().__init__(
            name="WorldKeeper",
            role="逻辑守门人 - 负责世界观管理、战力体系、逻辑校验",
            llm_client=llm_client
        )
    
    def get_system_prompt(self) -> str:
        return """你是一位严谨的逻辑守门人(World & Logic Keeper),负责维护故事世界的一致性。

你的职责:
1. **物理引擎**: 确保战力体系不崩坏(如:练气期不能秒杀元婴期,除非有特定道具)
2. **背景一致性**: 管理地图、势力分布、经济系统
3. **逻辑审查**: 对大纲进行静态检查,发现前后矛盾

你的工作原则:
- 零容忍逻辑错误
- 严格执行世界观规则
- 记录事实而非文本
- 对任何违反物理规则的情节提出警告

在审查时,请特别关注:
1. 战力数值的合理性
2. 时间线的一致性
3. 地理位置的合理性
4. 已死亡/失踪角色不能再次出现
5. 物品/资源的来源和去向"""
    
    def process(self, bible: StoryBible, **kwargs) -> Any:
        """处理任务"""
        pass
    
    def create_world_settings(
        self,
        world_type: str,
        genre: str,
        power_system_description: str
    ) -> WorldSettings:
        """
        创建世界观设定
        
        Args:
            world_type: 世界类型
            genre: 类型
            power_system_description: 战力体系描述
            
        Returns:
            世界观设定
        """
        self.log(f"创建 {world_type} 世界观...")
        
        prompt = f"""请为 {genre} 类型的小说创建详细的世界观设定。

**基本信息**:
- 世界类型: {world_type}
- 战力体系描述: {power_system_description}

**要求**:
1. 设计完整的战力体系(境界、战力范围、规则)
2. 设计地理结构(大陆、城市、旅行时间)
3. 设计主要势力(正派、邪派、中立)
4. 设计经济系统(货币、汇率)
5. 设定物理规则

请以 JSON 格式返回:
{{
    "world_name": "世界名称",
    "power_system": {{
        "stages": ["境界1", "境界2", ...],
        "power_ranges": {{
            "境界1": [最小值, 最大值],
            ...
        }},
        "rules": ["规则1", "规则2", ...]
    }},
    "geography": {{
        "continents": ["大陆1", "大陆2"],
        "cities": {{
            "城市名": {{"location": "所在大陆", "population": 人口}}
        }},
        "travel_times": {{
            "城市A->城市B": "旅行时间"
        }}
    }},
    "factions": {{
        "势力名": {{"type": "正派/邪派/中立", "leader": "领袖", "strength": 1-10}}
    }},
    "economy": {{
        "currency": "货币名称",
        "exchange_rate": {{"金币": 100, "灵石": 1}}
    }},
    "physics_rules": ["物理规则1", "物理规则2", ...]
}}"""
        
        result = self.generate_json(prompt, temperature=0.6)
        
        # 创建世界观设定
        world = WorldSettings(
            world_name=result.get("world_name", ""),
            world_type=world_type,
            power_system=result.get("power_system", {}),
            geography=result.get("geography", {}),
            factions=result.get("factions", {}),
            economy=result.get("economy", {}),
            physics_rules=result.get("physics_rules", [])
        )
        
        self.log("世界观设定创建完成")
        return world
    
    def validate_power_logic(
        self,
        bible: StoryBible,
        attacker: str,
        defender: str,
        outcome: str,
        context: str
    ) -> Dict[str, Any]:
        """
        验证战力逻辑
        
        Args:
            bible: 故事圣经
            attacker: 攻击者
            defender: 防御者
            outcome: 结果
            context: 上下文(特殊道具、环境等)
            
        Returns:
            验证结果
        """
        self.log(f"验证战力逻辑: {attacker} vs {defender}...")
        
        attacker_char = bible.get_character(attacker)
        defender_char = bible.get_character(defender)
        
        if not attacker_char or not defender_char:
            return {"valid": False, "reason": "角色不存在"}
        
        world = bible.world_settings
        
        prompt = f"""请验证以下战斗结果是否符合战力体系。

**战力体系**:
- 境界: {world.power_system.get('stages', [])}
- 战力范围: {world.power_system.get('power_ranges', {{}})}
- 规则: {world.power_system.get('rules', [])}

**战斗信息**:
- 攻击者: {attacker} (境界: {attacker_char.cultivation_stage}, 战力: {attacker_char.power_level})
- 防御者: {defender} (境界: {defender_char.cultivation_stage}, 战力: {defender_char.power_level})
- 结果: {outcome}
- 上下文: {context}

**要求**:
判断该结果是否合理。

请以 JSON 格式返回:
{{
    "valid": true/false,
    "confidence": 0.0-1.0,
    "reason": "判断理由",
    "suggestions": "修改建议(如果不合理)"
}}"""
        
        result = self.generate_json(prompt, temperature=0.3)
        self.log(f"战力逻辑验证: {'通过' if result['valid'] else '不通过'}")
        return result
    
    def validate_timeline(
        self,
        bible: StoryBible,
        character_name: str,
        from_location: str,
        to_location: str,
        available_time: str
    ) -> Dict[str, Any]:
        """
        验证时间线合理性
        
        Args:
            bible: 故事圣经
            character_name: 角色名称
            from_location: 起始位置
            to_location: 目标位置
            available_time: 可用时间
            
        Returns:
            验证结果
        """
        self.log(f"验证时间线: {character_name} 从 {from_location} 到 {to_location}...")
        
        world = bible.world_settings
        travel_time = world.get_travel_time(from_location, to_location)
        
        prompt = f"""请验证角色移动的时间线是否合理。

**地理信息**:
- 旅行时间设定: {world.geography.get('travel_times', {{}})}

**移动信息**:
- 角色: {character_name}
- 起点: {from_location}
- 终点: {to_location}
- 标准旅行时间: {travel_time or '未设定'}
- 可用时间: {available_time}

**要求**:
判断该移动是否在时间上合理。

请以 JSON 格式返回:
{{
    "valid": true/false,
    "reason": "判断理由",
    "suggestions": "修改建议(如果不合理)"
}}"""
        
        result = self.generate_json(prompt, temperature=0.3)
        self.log(f"时间线验证: {'通过' if result['valid'] else '不通过'}")
        return result
    
    def validate_outline(
        self,
        bible: StoryBible,
        outline_text: str,
        chapter_number: int
    ) -> Dict[str, Any]:
        """
        验证大纲的逻辑一致性
        
        Args:
            bible: 故事圣经
            outline_text: 大纲文本
            chapter_number: 章节号
            
        Returns:
            验证结果,包含所有发现的问题
        """
        self.log(f"验证第 {chapter_number} 章大纲的逻辑一致性...")
        
        # 构建上下文
        context = self._build_validation_context(bible, chapter_number)
        
        prompt = f"""请对以下章节大纲进行严格的逻辑审查。

**当前状态**:
{context}

**第 {chapter_number} 章大纲**:
{outline_text}

**检查项**:
1. 角色状态是否一致(已死亡角色不能出现)
2. 战力体系是否合理
3. 时间线是否合理
4. 地理位置是否合理
5. 物品/资源来源是否合理

请以 JSON 格式返回:
{{
    "valid": true/false,
    "issues": [
        {{
            "type": "问题类型(角色/战力/时间线/地理/物品)",
            "severity": "严重程度(critical/warning/info)",
            "description": "问题描述",
            "suggestion": "修改建议"
        }},
        ...
    ],
    "overall_assessment": "总体评估"
}}"""
        
        result = self.generate_json(prompt, temperature=0.2)
        
        critical_issues = [issue for issue in result.get('issues', []) 
                          if issue.get('severity') == 'critical']
        
        if critical_issues:
            self.log(f"发现 {len(critical_issues)} 个严重问题,大纲被驳回")
        else:
            self.log("逻辑验证通过")
        
        return result
    
    def _build_validation_context(self, bible: StoryBible, chapter_number: int) -> str:
        """构建验证上下文"""
        context_parts = []
        
        # 角色状态
        context_parts.append("**角色状态**:")
        for char in bible.characters.values():
            if char.first_appearance_chapter and char.first_appearance_chapter < chapter_number:
                context_parts.append(
                    f"- {char.name}: {char.state.value}, 位于 {char.current_location}, "
                    f"战力 {char.power_level} ({char.cultivation_stage})"
                )
        
        # 世界观规则
        context_parts.append("\n**战力体系规则**:")
        for rule in bible.world_settings.power_system.get('rules', []):
            context_parts.append(f"- {rule}")
        
        # 最近事件
        recent_events = bible.get_recent_events(10)
        if recent_events:
            context_parts.append("\n**最近事件**:")
            for event in recent_events:
                context_parts.append(f"- 第{event.chapter}章: {event.description}")
        
        return "\n".join(context_parts)
