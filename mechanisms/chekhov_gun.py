"""
Chekhov's Gun Scheduler (契诃夫之枪调度器) - 伏笔回收管理
管理伏笔的 TTL 和权重,主动提醒回收
"""

from typing import Dict, List, Any, Optional
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import StoryBible, OpenLoop, LoopStatus


class ChekhovGunScheduler:
    """契诃夫之枪调度器"""
    
    def __init__(
        self,
        warning_threshold: float = 0.8,
        critical_threshold: float = 1.0
    ):
        """
        初始化调度器
        
        Args:
            warning_threshold: 警告阈值(TTL 使用率)
            critical_threshold: 严重阈值(TTL 使用率)
        """
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold
    
    def schedule_loop(
        self,
        loop: OpenLoop,
        current_chapter: int,
        target_chapters: int
    ) -> Dict[str, Any]:
        """
        为伏笔制定回收计划
        
        Args:
            loop: 伏笔对象
            current_chapter: 当前章节
            target_chapters: 总章节数
            
        Returns:
            回收计划
        """
        # 计算 TTL 使用率
        age = current_chapter - loop.planted_chapter
        ttl_usage = age / loop.ttl if loop.ttl > 0 else 0
        
        # 计算建议回收章节
        suggested_chapter = loop.planted_chapter + int(loop.ttl * 0.9)
        
        # 计算剩余章节
        remaining_chapters = target_chapters - current_chapter
        
        # 确定优先级
        if ttl_usage >= self.critical_threshold:
            priority = "critical"
            urgency = "立即回收"
        elif ttl_usage >= self.warning_threshold:
            priority = "high"
            urgency = "尽快回收"
        elif remaining_chapters < loop.ttl * 0.3:
            priority = "medium"
            urgency = "考虑回收"
        else:
            priority = "low"
            urgency = "可以等待"
        
        return {
            "loop_id": loop.loop_id,
            "loop_title": loop.title,
            "planted_chapter": loop.planted_chapter,
            "current_chapter": current_chapter,
            "age": age,
            "ttl": loop.ttl,
            "ttl_usage": ttl_usage,
            "weight": loop.weight,
            "priority": priority,
            "urgency": urgency,
            "suggested_chapter": suggested_chapter,
            "remaining_chapters": remaining_chapters
        }
    
    def get_loops_to_resolve(
        self,
        bible: StoryBible,
        current_chapter: int,
        lookahead_chapters: int = 10
    ) -> List[Dict[str, Any]]:
        """
        获取应该回收的伏笔列表
        
        Args:
            bible: 故事圣经
            current_chapter: 当前章节
            lookahead_chapters: 向前看多少章
            
        Returns:
            应该回收的伏笔列表,按优先级排序
        """
        active_loops = bible.get_active_loops()
        
        if not active_loops:
            return []
        
        schedules = []
        
        for loop in active_loops:
            schedule = self.schedule_loop(loop, current_chapter, bible.target_chapters)
            
            # 只包含需要关注的伏笔
            if schedule["priority"] in ["critical", "high", "medium"]:
                schedules.append(schedule)
        
        # 排序:优先级 > 权重 > TTL 使用率
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        
        schedules.sort(
            key=lambda x: (
                priority_order[x["priority"]],
                -x["weight"],
                -x["ttl_usage"]
            )
        )
        
        return schedules
    
    def get_overdue_loops(
        self,
        bible: StoryBible,
        current_chapter: int
    ) -> List[Dict[str, Any]]:
        """
        获取超期伏笔
        
        Args:
            bible: 故事圣经
            current_chapter: 当前章节
            
        Returns:
            超期伏笔列表
        """
        overdue_loops = bible.get_overdue_loops()
        
        results = []
        for loop in overdue_loops:
            age = current_chapter - loop.planted_chapter
            overdue_by = age - loop.ttl
            
            results.append({
                "loop_id": loop.loop_id,
                "loop_title": loop.title,
                "category": loop.category,
                "weight": loop.weight,
                "planted_chapter": loop.planted_chapter,
                "ttl": loop.ttl,
                "age": age,
                "overdue_by": overdue_by,
                "description": loop.description,
                "action": "必须立即回收或标记为红鲱鱼"
            })
        
        # 按超期程度排序
        results.sort(key=lambda x: -x["overdue_by"])
        
        return results
    
    def suggest_resolution_timing(
        self,
        bible: StoryBible,
        loop_id: str,
        current_chapter: int,
        upcoming_arc_description: str
    ) -> Dict[str, Any]:
        """
        建议伏笔回收时机
        
        Args:
            bible: 故事圣经
            loop_id: 伏笔ID
            current_chapter: 当前章节
            upcoming_arc_description: 即将到来的剧情弧描述
            
        Returns:
            回收时机建议
        """
        loop = bible.open_loops.get(loop_id)
        if not loop:
            return {"error": f"伏笔 {loop_id} 不存在"}
        
        schedule = self.schedule_loop(loop, current_chapter, bible.target_chapters)
        
        # 基于剧情弧和伏笔类别建议时机
        suggestions = []
        
        if schedule["priority"] == "critical":
            suggestions.append({
                "timing": "立即",
                "chapter_range": f"{current_chapter}-{current_chapter+2}",
                "reasoning": "伏笔已超期,必须立即回收"
            })
        elif schedule["priority"] == "high":
            suggestions.append({
                "timing": "尽快",
                "chapter_range": f"{current_chapter}-{current_chapter+5}",
                "reasoning": "伏笔接近 TTL,建议尽快回收"
            })
        else:
            # 基于权重建议
            if loop.weight >= 8:
                suggestions.append({
                    "timing": "高潮时刻",
                    "chapter_range": f"{schedule['suggested_chapter']}-{schedule['suggested_chapter']+5}",
                    "reasoning": "高权重伏笔,建议在剧情高潮时回收以获得最大效果"
                })
            else:
                suggestions.append({
                    "timing": "合适时机",
                    "chapter_range": f"{current_chapter+5}-{schedule['suggested_chapter']}",
                    "reasoning": "可以等待合适的剧情节点自然回收"
                })
        
        return {
            "loop_id": loop_id,
            "loop_title": loop.title,
            "schedule": schedule,
            "suggestions": suggestions,
            "upcoming_arc": upcoming_arc_description
        }
    
    def mark_for_abandonment(
        self,
        bible: StoryBible,
        loop_id: str,
        reason: str
    ) -> Dict[str, Any]:
        """
        标记伏笔为红鲱鱼(放弃回收)
        
        Args:
            bible: 故事圣经
            loop_id: 伏笔ID
            reason: 放弃原因
            
        Returns:
            操作结果
        """
        loop = bible.open_loops.get(loop_id)
        if not loop:
            return {"success": False, "error": f"伏笔 {loop_id} 不存在"}
        
        loop.status = LoopStatus.ABANDONED
        loop.resolution = f"标记为红鲱鱼: {reason}"
        
        print(f"[ChekhovGun] 伏笔 '{loop.title}' 已标记为红鲱鱼: {reason}")
        
        return {
            "success": True,
            "loop_id": loop_id,
            "loop_title": loop.title,
            "reason": reason
        }
    
    def get_dashboard(
        self,
        bible: StoryBible,
        current_chapter: int
    ) -> Dict[str, Any]:
        """
        获取伏笔管理仪表板
        
        Args:
            bible: 故事圣经
            current_chapter: 当前章节
            
        Returns:
            仪表板数据
        """
        all_loops = bible.open_loops.values()
        active_loops = bible.get_active_loops()
        overdue_loops = bible.get_overdue_loops()
        
        # 统计
        total = len(all_loops)
        active = len(active_loops)
        closed = sum(1 for loop in all_loops if loop.status == LoopStatus.CLOSED)
        abandoned = sum(1 for loop in all_loops if loop.status == LoopStatus.ABANDONED)
        overdue = len(overdue_loops)
        
        # 按优先级分类
        critical = []
        high = []
        medium = []
        low = []
        
        for loop in active_loops:
            schedule = self.schedule_loop(loop, current_chapter, bible.target_chapters)
            priority = schedule["priority"]
            
            if priority == "critical":
                critical.append(schedule)
            elif priority == "high":
                high.append(schedule)
            elif priority == "medium":
                medium.append(schedule)
            else:
                low.append(schedule)
        
        # 按类别统计
        category_stats = {}
        for loop in active_loops:
            cat = loop.category or "未分类"
            if cat not in category_stats:
                category_stats[cat] = 0
            category_stats[cat] += 1
        
        return {
            "current_chapter": current_chapter,
            "statistics": {
                "total": total,
                "active": active,
                "closed": closed,
                "abandoned": abandoned,
                "overdue": overdue,
                "closure_rate": closed / total if total > 0 else 0
            },
            "by_priority": {
                "critical": len(critical),
                "high": len(high),
                "medium": len(medium),
                "low": len(low)
            },
            "by_category": category_stats,
            "critical_loops": critical[:5],  # 最紧急的 5 个
            "overdue_loops": [
                {
                    "loop_id": loop.loop_id,
                    "title": loop.title,
                    "overdue_by": current_chapter - loop.planted_chapter - loop.ttl
                }
                for loop in overdue_loops[:5]
            ]
        }
