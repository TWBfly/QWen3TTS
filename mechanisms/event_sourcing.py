"""
Event Sourcing (事件溯源) - 逻辑一致性检查引擎
只记忆事实,不记忆文本,用于检测逻辑矛盾
"""

from typing import Dict, List, Any, Optional
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import EventRecord, StoryBible


class EventSourcingEngine:
    """事件溯源引擎"""
    
    def __init__(self):
        """初始化事件溯源引擎"""
        self.fact_index: Dict[str, List[EventRecord]] = {}
        # 按类型索引事实: {"character_state": [...], "item_ownership": [...]}
    
    def record_event(
        self,
        bible: StoryBible,
        event_id: str,
        chapter: int,
        event_type: str,
        description: str,
        facts: Dict[str, Any],
        affected_characters: List[str] = None
    ):
        """
        记录事件
        
        Args:
            bible: 故事圣经
            event_id: 事件ID
            chapter: 章节号
            event_type: 事件类型
            description: 描述
            facts: 事实性数据
            affected_characters: 受影响的角色
        """
        event = EventRecord(
            event_id=event_id,
            chapter=chapter,
            event_type=event_type,
            description=description,
            facts=facts,
            affected_characters=affected_characters or []
        )
        
        bible.add_event(event)
        
        # 索引事实
        self._index_event(event)
        
        print(f"[EventSourcing] 记录事件: {event_id} (第{chapter}章, 类型:{event_type})")
    
    def _index_event(self, event: EventRecord):
        """索引事件"""
        event_type = event.event_type
        
        if event_type not in self.fact_index:
            self.fact_index[event_type] = []
        
        self.fact_index[event_type].append(event)
    
    def check_fact_consistency(
        self,
        bible: StoryBible,
        fact_type: str,
        fact_key: str,
        proposed_value: Any,
        chapter: int
    ) -> Dict[str, Any]:
        """
        检查事实一致性
        
        Args:
            bible: 故事圣经
            fact_type: 事实类型
            fact_key: 事实键
            proposed_value: 拟定的值
            chapter: 章节号
            
        Returns:
            检查结果
        """
        # 查找相关历史事件
        related_events = self._find_related_events(bible, fact_type, fact_key, chapter)
        
        if not related_events:
            return {
                "consistent": True,
                "reason": "无相关历史记录"
            }
        
        # 检查最新的事实
        latest_event = related_events[-1]
        latest_value = latest_event.facts.get(fact_key)
        
        # 比较
        if latest_value == proposed_value:
            return {
                "consistent": True,
                "reason": "与最新事实一致"
            }
        
        # 不一致
        return {
            "consistent": False,
            "reason": f"与第{latest_event.chapter}章的事实冲突",
            "conflicting_event": {
                "event_id": latest_event.event_id,
                "chapter": latest_event.chapter,
                "description": latest_event.description,
                "recorded_value": latest_value,
                "proposed_value": proposed_value
            },
            "history": [
                {
                    "chapter": e.chapter,
                    "value": e.facts.get(fact_key),
                    "description": e.description
                }
                for e in related_events
            ]
        }
    
    def check_character_state(
        self,
        bible: StoryBible,
        character_name: str,
        proposed_state: str,
        chapter: int
    ) -> Dict[str, Any]:
        """
        检查角色状态一致性
        
        例如:检查已死亡角色是否又出现
        
        Args:
            bible: 故事圣经
            character_name: 角色名称
            proposed_state: 拟定的状态 (alive, dead, missing, etc.)
            chapter: 章节号
            
        Returns:
            检查结果
        """
        # 查找角色相关的状态变更事件
        state_events = [
            event for event in bible.event_history
            if character_name in event.affected_characters
            and event.event_type in ["character_state_change", "death", "injury"]
            and event.chapter < chapter
        ]
        
        if not state_events:
            return {
                "consistent": True,
                "reason": "无历史状态记录"
            }
        
        # 获取最新状态
        latest_event = max(state_events, key=lambda e: e.chapter)
        latest_state = latest_event.facts.get("state", "alive")
        
        # 检查状态转换是否合理
        if latest_state == "dead" and proposed_state == "alive":
            return {
                "consistent": False,
                "reason": f"角色在第{latest_event.chapter}章已死亡,不能复活",
                "conflicting_event": {
                    "event_id": latest_event.event_id,
                    "chapter": latest_event.chapter,
                    "description": latest_event.description
                }
            }
        
        return {
            "consistent": True,
            "reason": "状态转换合理",
            "previous_state": latest_state
        }
    
    def check_body_part_integrity(
        self,
        bible: StoryBible,
        character_name: str,
        body_part: str,
        proposed_action: str,
        chapter: int
    ) -> Dict[str, Any]:
        """
        检查身体部位完整性
        
        例如:检查已被砍断的左手是否又被使用
        
        Args:
            bible: 故事圣经
            character_name: 角色名称
            body_part: 身体部位
            proposed_action: 拟定的动作
            chapter: 章节号
            
        Returns:
            检查结果
        """
        # 查找身体伤害事件
        injury_events = [
            event for event in bible.event_history
            if character_name in event.affected_characters
            and event.event_type == "injury"
            and event.facts.get("body_part") == body_part
            and event.chapter < chapter
        ]
        
        if not injury_events:
            return {
                "consistent": True,
                "reason": "该身体部位无伤害记录"
            }
        
        # 检查最严重的伤害
        for event in sorted(injury_events, key=lambda e: e.chapter, reverse=True):
            injury_type = event.facts.get("injury_type")
            
            if injury_type in ["severed", "lost", "amputated"]:
                return {
                    "consistent": False,
                    "reason": f"角色的{body_part}在第{event.chapter}章已{injury_type},无法使用",
                    "conflicting_event": {
                        "event_id": event.event_id,
                        "chapter": event.chapter,
                        "description": event.description
                    },
                    "suggestion": f"修改为使用其他身体部位,或说明使用了义肢/法术"
                }
        
        return {
            "consistent": True,
            "reason": "身体部位可以使用"
        }
    
    def check_item_ownership(
        self,
        bible: StoryBible,
        character_name: str,
        item_name: str,
        chapter: int
    ) -> Dict[str, Any]:
        """
        检查物品所有权
        
        Args:
            bible: 故事圣经
            character_name: 角色名称
            item_name: 物品名称
            chapter: 章节号
            
        Returns:
            检查结果,包含物品来源
        """
        # 查找物品相关事件
        item_events = [
            event for event in bible.event_history
            if event.event_type in ["item_obtained", "item_lost", "item_transferred"]
            and event.facts.get("item") == item_name
            and event.chapter < chapter
        ]
        
        if not item_events:
            return {
                "has_item": False,
                "reason": "无该物品的获得记录",
                "suggestion": "需要先记录角色如何获得该物品"
            }
        
        # 追踪物品所有权
        current_owner = None
        
        for event in sorted(item_events, key=lambda e: e.chapter):
            if event.event_type == "item_obtained":
                if character_name in event.affected_characters:
                    current_owner = character_name
            elif event.event_type == "item_lost":
                if character_name in event.affected_characters:
                    current_owner = None
            elif event.event_type == "item_transferred":
                from_char = event.facts.get("from")
                to_char = event.facts.get("to")
                if to_char == character_name:
                    current_owner = character_name
                elif from_char == character_name:
                    current_owner = None
        
        if current_owner == character_name:
            return {
                "has_item": True,
                "reason": "角色拥有该物品",
                "acquisition_history": [
                    {
                        "chapter": e.chapter,
                        "event": e.description
                    }
                    for e in item_events
                ]
            }
        else:
            return {
                "has_item": False,
                "reason": f"角色不拥有该物品(当前所有者:{current_owner or '无'})",
                "last_known_owner": current_owner,
                "suggestion": "需要先记录角色如何获得该物品"
            }
    
    def _find_related_events(
        self,
        bible: StoryBible,
        fact_type: str,
        fact_key: str,
        before_chapter: int
    ) -> List[EventRecord]:
        """查找相关事件"""
        related = []
        
        for event in bible.event_history:
            if event.chapter >= before_chapter:
                continue
            
            if event.event_type == fact_type and fact_key in event.facts:
                related.append(event)
        
        return sorted(related, key=lambda e: e.chapter)
    
    def get_character_timeline(
        self,
        bible: StoryBible,
        character_name: str
    ) -> List[Dict[str, Any]]:
        """
        获取角色时间线
        
        Args:
            bible: 故事圣经
            character_name: 角色名称
            
        Returns:
            时间线事件列表
        """
        events = [
            event for event in bible.event_history
            if character_name in event.affected_characters
        ]
        
        timeline = []
        for event in sorted(events, key=lambda e: e.chapter):
            timeline.append({
                "chapter": event.chapter,
                "event_type": event.event_type,
                "description": event.description,
                "facts": event.facts
            })
        
        return timeline
