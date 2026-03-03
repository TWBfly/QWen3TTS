"""
Trajectory Analysis (轨迹分析) - 人物弧光监测
监测角色性格坐标的变化,检测 OOC (Out of Character)
"""

from typing import Dict, List, Any, Optional
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import StoryBible, CharacterCard


class TrajectoryAnalyzer:
    """轨迹分析器"""
    
    def __init__(self, ooc_threshold: float = 0.3):
        """
        初始化轨迹分析器
        
        Args:
            ooc_threshold: OOC 阈值(性格坐标单次变化超过此值视为异常)
        """
        self.ooc_threshold = ooc_threshold
        self.trajectory_history: Dict[str, List[Dict[str, Any]]] = {}
        # 角色轨迹历史: {角色名: [{chapter, coordinates, event}]}
    
    def initialize_character_trajectory(
        self,
        character_name: str,
        initial_coordinates: Dict[str, float],
        chapter: int
    ):
        """
        初始化角色轨迹
        
        Args:
            character_name: 角色名称
            initial_coordinates: 初始性格坐标
            chapter: 章节号
        """
        self.trajectory_history[character_name] = [{
            "chapter": chapter,
            "coordinates": initial_coordinates.copy(),
            "event": "角色初始化"
        }]
        
        print(f"[TrajectoryAnalyzer] 初始化角色轨迹: {character_name}")
    
    def record_trajectory_change(
        self,
        character_name: str,
        new_coordinates: Dict[str, float],
        chapter: int,
        trigger_event: str
    ):
        """
        记录轨迹变化
        
        Args:
            character_name: 角色名称
            new_coordinates: 新的性格坐标
            chapter: 章节号
            trigger_event: 触发事件
        """
        if character_name not in self.trajectory_history:
            self.trajectory_history[character_name] = []
        
        self.trajectory_history[character_name].append({
            "chapter": chapter,
            "coordinates": new_coordinates.copy(),
            "event": trigger_event
        })
        
        print(f"[TrajectoryAnalyzer] 记录轨迹变化: {character_name} (第{chapter}章)")
    
    def analyze_trajectory(
        self,
        bible: StoryBible,
        character_name: str,
        proposed_coordinates: Dict[str, float],
        current_chapter: int,
        context: str
    ) -> Dict[str, Any]:
        """
        分析轨迹合理性
        
        Args:
            bible: 故事圣经
            character_name: 角色名称
            proposed_coordinates: 拟定的新坐标
            current_chapter: 当前章节
            context: 上下文(发生了什么事)
            
        Returns:
            分析结果
        """
        character = bible.get_character(character_name)
        if not character:
            return {
                "valid": False,
                "reason": f"角色 {character_name} 不存在"
            }
        
        current_coordinates = character.personality_coordinates
        
        # 计算变化
        changes = {}
        issues = []
        
        for axis, new_value in proposed_coordinates.items():
            old_value = current_coordinates.get(axis, 0.5)
            delta = new_value - old_value
            changes[axis] = {
                "old": old_value,
                "new": new_value,
                "delta": delta
            }
            
            # 检查是否超过阈值
            if abs(delta) > self.ooc_threshold:
                issues.append({
                    "axis": axis,
                    "change": delta,
                    "severity": "warning",
                    "message": f"{axis} 变化过大({delta:.2f}),可能 OOC"
                })
        
        # 检查是否有重大事件支撑
        recent_events = [
            event for event in character.major_events[-5:]
        ]
        
        if issues and not recent_events:
            issues.append({
                "severity": "critical",
                "message": "性格发生重大变化,但缺少重大事件支撑"
            })
        
        # 判断是否有效
        critical_issues = [i for i in issues if i.get("severity") == "critical"]
        
        return {
            "valid": len(critical_issues) == 0,
            "changes": changes,
            "issues": issues,
            "recent_events": recent_events,
            "recommendation": self._generate_recommendation(changes, issues, context)
        }
    
    def check_ooc(
        self,
        bible: StoryBible,
        character_name: str,
        proposed_behavior: str,
        current_chapter: int
    ) -> Dict[str, Any]:
        """
        检查行为是否 OOC
        
        Args:
            bible: 故事圣经
            character_name: 角色名称
            proposed_behavior: 拟定的行为
            current_chapter: 当前章节
            
        Returns:
            检查结果
        """
        character = bible.get_character(character_name)
        if not character:
            return {
                "is_ooc": False,
                "reason": "角色不存在"
            }
        
        # 获取角色性格特征
        coordinates = character.personality_coordinates
        keywords = character.personality_keywords
        psychological_state = character.psychological_state
        
        # 分析行为与性格的匹配度
        # 这里简化处理,实际可以用 LLM 进行更复杂的分析
        
        # 检查是否有轨迹历史
        if character_name in self.trajectory_history:
            trajectory = self.trajectory_history[character_name]
            
            # 获取最近的性格变化
            recent_changes = [
                t for t in trajectory
                if t["chapter"] >= current_chapter - 10
            ]
            
            if recent_changes:
                return {
                    "is_ooc": False,
                    "reason": "角色性格在合理演进中",
                    "trajectory": recent_changes[-3:]
                }
        
        return {
            "is_ooc": False,
            "reason": "需要更多上下文判断",
            "character_profile": {
                "coordinates": coordinates,
                "keywords": keywords,
                "psychological_state": psychological_state
            }
        }
    
    def get_growth_report(
        self,
        bible: StoryBible,
        character_name: str
    ) -> Dict[str, Any]:
        """
        获取角色成长报告
        
        Args:
            bible: 故事圣经
            character_name: 角色名称
            
        Returns:
            成长报告
        """
        character = bible.get_character(character_name)
        if not character:
            return {"error": f"角色 {character_name} 不存在"}
        
        if character_name not in self.trajectory_history:
            return {
                "character_name": character_name,
                "growth_status": "未追踪",
                "message": "该角色的轨迹未被记录"
            }
        
        trajectory = self.trajectory_history[character_name]
        
        if len(trajectory) < 2:
            return {
                "character_name": character_name,
                "growth_status": "初始阶段",
                "trajectory_points": len(trajectory)
            }
        
        # 计算总体变化
        initial = trajectory[0]["coordinates"]
        current = trajectory[-1]["coordinates"]
        
        total_changes = {}
        for axis in initial:
            if axis in current:
                total_changes[axis] = {
                    "initial": initial[axis],
                    "current": current[axis],
                    "total_change": current[axis] - initial[axis]
                }
        
        # 计算成长速度
        chapters_span = trajectory[-1]["chapter"] - trajectory[0]["chapter"]
        growth_rate = len(trajectory) / max(chapters_span, 1)
        
        return {
            "character_name": character_name,
            "growth_status": "正常成长",
            "trajectory_points": len(trajectory),
            "chapters_span": chapters_span,
            "growth_rate": growth_rate,
            "total_changes": total_changes,
            "major_milestones": [
                {
                    "chapter": t["chapter"],
                    "event": t["event"],
                    "coordinates": t["coordinates"]
                }
                for t in trajectory[::max(len(trajectory)//5, 1)]  # 取 5 个里程碑
            ]
        }
    
    def suggest_next_development(
        self,
        bible: StoryBible,
        character_name: str,
        upcoming_events: str
    ) -> Dict[str, Any]:
        """
        建议下一步发展方向
        
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
        
        current_coords = character.personality_coordinates
        arc_progress = character.character_arc_progress
        
        # 基于当前进度建议发展方向
        suggestions = {}
        
        for axis, value in current_coords.items():
            if value < 0.3:
                # 偏向起点,建议向终点发展
                suggestions[axis] = {
                    "current": value,
                    "suggested_direction": "增加",
                    "suggested_delta": 0.1,
                    "reasoning": f"{axis} 还处于起点,可以逐步发展"
                }
            elif value > 0.7:
                # 已接近终点,建议稳定
                suggestions[axis] = {
                    "current": value,
                    "suggested_direction": "稳定",
                    "suggested_delta": 0.0,
                    "reasoning": f"{axis} 已接近终点,建议保持"
                }
            else:
                # 中间阶段,根据弧光进度建议
                suggestions[axis] = {
                    "current": value,
                    "suggested_direction": "适度增加",
                    "suggested_delta": 0.05,
                    "reasoning": f"{axis} 处于成长期,可以适度发展"
                }
        
        return {
            "character_name": character_name,
            "current_arc_progress": arc_progress,
            "suggestions": suggestions,
            "upcoming_events": upcoming_events
        }
    
    def _generate_recommendation(
        self,
        changes: Dict[str, Dict[str, float]],
        issues: List[Dict[str, Any]],
        context: str
    ) -> str:
        """生成建议"""
        if not issues:
            return "性格变化合理,可以继续"
        
        critical_issues = [i for i in issues if i.get("severity") == "critical"]
        
        if critical_issues:
            return "建议: 添加重大事件来支撑性格的剧烈变化,或者减小变化幅度"
        
        return "建议: 注意性格变化的幅度,确保有足够的事件支撑"
