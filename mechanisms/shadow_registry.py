"""
Shadow Registry (影子注册表) - 人物铺垫机制
确保重要人物在正式登场前有充分的铺垫
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime


@dataclass
class ShadowEntry:
    """影子注册表条目"""
    
    character_name: str  # 角色名称
    planned_appearance_chapter: int  # 计划登场章节
    mention_count: int = 0  # 已提及次数
    mentions: List[Dict[str, str]] = field(default_factory=list)
    # 提及记录: [{"chapter": 章节号, "method": "方式", "content": "内容"}]
    
    min_mentions_required: int = 3  # 最少提及次数
    min_chapters_ahead: int = 5  # 最少提前章节数
    
    is_unlocked: bool = False  # 是否解锁(可以正式登场)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def add_mention(self, chapter: int, method: str, content: str):
        """添加一次提及"""
        self.mentions.append({
            "chapter": chapter,
            "method": method,
            "content": content
        })
        self.mention_count += 1
    
    def check_unlock(self, current_chapter: int) -> bool:
        """检查是否可以解锁"""
        # 条件1: 提及次数足够
        mentions_ok = self.mention_count >= self.min_mentions_required
        
        # 条件2: 提前章节数足够
        chapters_ahead = self.planned_appearance_chapter - current_chapter
        chapters_ok = chapters_ahead <= self.min_chapters_ahead
        
        # 条件3: 至少已经提及过一次
        has_mentions = len(self.mentions) > 0
        
        if mentions_ok and has_mentions:
            self.is_unlocked = True
            return True
        
        return False


class ShadowRegistry:
    """影子注册表 - 管理人物铺垫"""
    
    def __init__(
        self,
        min_mentions: int = 3,
        min_chapters_ahead: int = 5
    ):
        """
        初始化影子注册表
        
        Args:
            min_mentions: 最少提及次数
            min_chapters_ahead: 最少提前章节数
        """
        self.min_mentions = min_mentions
        self.min_chapters_ahead = min_chapters_ahead
        self.registry: Dict[str, ShadowEntry] = {}
    
    def register_character(
        self,
        character_name: str,
        planned_appearance_chapter: int,
        min_mentions: Optional[int] = None,
        min_chapters_ahead: Optional[int] = None
    ):
        """
        注册一个待登场角色
        
        Args:
            character_name: 角色名称
            planned_appearance_chapter: 计划登场章节
            min_mentions: 最少提及次数(可选,使用默认值)
            min_chapters_ahead: 最少提前章节数(可选,使用默认值)
        """
        entry = ShadowEntry(
            character_name=character_name,
            planned_appearance_chapter=planned_appearance_chapter,
            min_mentions_required=min_mentions or self.min_mentions,
            min_chapters_ahead=min_chapters_ahead or self.min_chapters_ahead
        )
        
        self.registry[character_name] = entry
        print(f"[ShadowRegistry] 注册角色: {character_name}, "
              f"计划第 {planned_appearance_chapter} 章登场")
    
    def add_mention(
        self,
        character_name: str,
        chapter: int,
        method: str,
        content: str
    ):
        """
        记录一次提及
        
        Args:
            character_name: 角色名称
            chapter: 章节号
            method: 提及方式
            content: 提及内容
        """
        if character_name not in self.registry:
            print(f"[ShadowRegistry] 警告: 角色 {character_name} 未注册")
            return
        
        entry = self.registry[character_name]
        entry.add_mention(chapter, method, content)
        
        print(f"[ShadowRegistry] 记录提及: {character_name} "
              f"(第{chapter}章, 方式:{method}, 总计:{entry.mention_count}次)")
    
    def check_can_appear(
        self,
        character_name: str,
        current_chapter: int
    ) -> Dict[str, any]:
        """
        检查角色是否可以登场
        
        Args:
            character_name: 角色名称
            current_chapter: 当前章节
            
        Returns:
            检查结果
        """
        if character_name not in self.registry:
            return {
                "can_appear": True,
                "reason": "角色未在影子注册表中,可以直接登场"
            }
        
        entry = self.registry[character_name]
        
        # 检查解锁状态
        if entry.check_unlock(current_chapter):
            return {
                "can_appear": True,
                "reason": f"铺垫充分(已提及{entry.mention_count}次)",
                "mentions": entry.mentions
            }
        
        # 未解锁,返回原因
        reasons = []
        if entry.mention_count < entry.min_mentions_required:
            reasons.append(
                f"提及次数不足(当前{entry.mention_count}次, "
                f"需要{entry.min_mentions_required}次)"
            )
        
        chapters_ahead = entry.planned_appearance_chapter - current_chapter
        if chapters_ahead > entry.min_chapters_ahead:
            reasons.append(
                f"距离登场还有{chapters_ahead}章, "
                f"需要在{entry.min_chapters_ahead}章内提及"
            )
        
        return {
            "can_appear": False,
            "reason": "; ".join(reasons),
            "current_mentions": entry.mention_count,
            "required_mentions": entry.min_mentions_required,
            "mentions": entry.mentions
        }
    
    def get_pending_characters(
        self,
        current_chapter: int,
        lookahead_chapters: int = 10
    ) -> List[Dict[str, any]]:
        """
        获取即将登场但铺垫不足的角色
        
        Args:
            current_chapter: 当前章节
            lookahead_chapters: 向前看多少章
            
        Returns:
            待铺垫角色列表
        """
        pending = []
        
        for name, entry in self.registry.items():
            if entry.is_unlocked:
                continue
            
            chapters_until_appearance = entry.planned_appearance_chapter - current_chapter
            
            # 在前瞻范围内且未解锁
            if 0 < chapters_until_appearance <= lookahead_chapters:
                pending.append({
                    "character_name": name,
                    "planned_appearance": entry.planned_appearance_chapter,
                    "chapters_remaining": chapters_until_appearance,
                    "current_mentions": entry.mention_count,
                    "required_mentions": entry.min_mentions_required,
                    "urgency": "high" if chapters_until_appearance <= 3 else "medium"
                })
        
        # 按紧迫程度排序
        pending.sort(key=lambda x: x["chapters_remaining"])
        
        return pending
    
    def get_statistics(self) -> Dict[str, any]:
        """获取统计信息"""
        total = len(self.registry)
        unlocked = sum(1 for entry in self.registry.values() if entry.is_unlocked)
        pending = total - unlocked
        
        return {
            "total_registered": total,
            "unlocked": unlocked,
            "pending": pending,
            "unlock_rate": unlocked / total if total > 0 else 0
        }
