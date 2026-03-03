"""
存储管理器 - 负责 Story Bible 的持久化和版本控制
"""

import json
import os
from typing import Optional
from datetime import datetime
from pathlib import Path

from models import (
    StoryBible, CharacterCard, WorldSettings, PlotArc,
    ChapterOutline, OpenLoop, EventRecord, VolumePlan,
    CharacterState, LoopStatus
)


class StorageManager:
    """存储管理器"""
    
    def __init__(self, storage_dir: str = "./story_data"):
        """
        初始化存储管理器
        
        Args:
            storage_dir: 存储目录路径
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # 子目录
        self.bible_dir = self.storage_dir / "bibles"
        self.backup_dir = self.storage_dir / "backups"
        self.bible_dir.mkdir(exist_ok=True)
        self.backup_dir.mkdir(exist_ok=True)
    
    def save_story_bible(self, bible: StoryBible, filename: str = "story_bible.json") -> str:
        """
        保存故事圣经
        
        Args:
            bible: StoryBible 对象
            filename: 文件名
            
        Returns:
            保存的文件路径
        """
        filepath = self.bible_dir / filename
        
        # 如果文件已存在,先备份
        if filepath.exists():
            self._backup_file(filepath)
        
        # 转换为字典
        bible_dict = self._bible_to_dict(bible)
        
        # 保存
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(bible_dict, f, ensure_ascii=False, indent=2)
        
        return str(filepath)

    def save_character_profile(self, character: CharacterCard) -> str:
        """
        保存人物小传为 Markdown 文件
        """
        char_dir = self.storage_dir / "characters"
        char_dir.mkdir(exist_ok=True)
        
        filename = f"{character.name}.md"
        filepath = char_dir / filename
        
        # 渲染 Markdown
        content = f"""# 人物档案: {character.name}

> "{character.identity}"

## 1. 基础信息
- **姓名**: {character.name}
- **别名**: {', '.join(character.alias) if character.alias else '无'}
- **战力/境界**: {character.cultivation_stage} (Lv.{character.power_level})
- **性格关键词**: {', '.join(character.personality_keywords)}
- **特殊能力**: {', '.join(character.special_abilities)}

## 2. 人物小传 (Biography)
{character.biography}

## 3. 高光时刻 (Highlights)
"""
        for i, highlight in enumerate(character.highlights, 1):
            content += f"- {highlight}\n"
            
        content += f"""
## 4. 人物关系 (Detailed Relationships)
{character.detailed_relationships}

## 5. 当前状态 (动态更新)
- **位置**: {character.current_location}
- **心理状态**: {character.psychological_state}
- **生存状态**: {character.state.value}
- **最后更新**: {character.updated_at}
"""
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
            
        return str(filepath)
    
    def export_bible_to_markdown(self, bible: StoryBible, output_path: str = "story_export.md") -> str:
        """
        导出 Story Bible 为 Markdown 文件
        """
        content = []
        content.append(f"# {bible.story_title}\n")
        content.append(f"**类型**: {bible.genre} | **进度**: {bible.current_chapter}/{bible.target_chapters}章\n")
        content.append(f"**核心梗概**: {bible.main_plot_summary}\n")
        
        content.append("## 1. 世界观设定")
        content.append(f"- **世界名称**: {bible.world_settings.world_name}")
        content.append(f"- **体系**: {bible.world_settings.power_system}")
        content.append(f"- **势力**: {bible.world_settings.factions}\n")
        
        content.append("## 2. 卷规划 (100卷宏观大纲)")
        sorted_volumes = sorted(bible.volume_plans.items(), key=lambda x: x[0])
        for vol_num, plan in sorted_volumes:
            content.append(f"### 第{vol_num}卷：{plan.title} [{plan.phase}]")
            content.append(f"**概要**: {plan.summary}")
            content.append(f"**核心冲突**: {plan.main_conflict}")
            content.append(f"**主角成长**: {plan.protagonist_growth}")
            content.append("**关键事件**:")
            for event in plan.key_events:
                content.append(f"- {event}")
            content.append("")
            
        content.append("## 3. 章节大纲 (已生成)")
        sorted_chapters = sorted(bible.chapter_outlines.items(), key=lambda x: x[0])
        for chap_num, outline in sorted_chapters:
            content.append(f"### 第{chap_num}章：{outline.title}")
            content.append(f"**一句话剧情**: {outline.summary}")
            content.append(f"**详细大纲**:\n{outline.detailed_outline}\n")
            
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(content))
            
        return output_path

    def load_story_bible(self, filename: str = "story_bible.json") -> Optional[StoryBible]:
        """
        加载故事圣经
        
        Args:
            filename: 文件名
            
        Returns:
            StoryBible 对象,如果文件不存在则返回 None
        """
        filepath = self.bible_dir / filename
        
        if not filepath.exists():
            return None
        
        with open(filepath, 'r', encoding='utf-8') as f:
            bible_dict = json.load(f)
        
        return self._dict_to_bible(bible_dict)
    
    def _backup_file(self, filepath: Path):
        """备份文件"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{filepath.stem}_{timestamp}{filepath.suffix}"
        backup_path = self.backup_dir / backup_name
        
        import shutil
        shutil.copy2(filepath, backup_path)
    
    def _bible_to_dict(self, bible: StoryBible) -> dict:
        """将 StoryBible 转换为字典"""
        return {
            "story_title": bible.story_title,
            "genre": bible.genre,
            "target_chapters": bible.target_chapters,
            "world_settings": self._world_settings_to_dict(bible.world_settings),
            "characters": {name: self._character_to_dict(char) for name, char in bible.characters.items()},
            "plot_arcs": {arc_id: self._plot_arc_to_dict(arc) for arc_id, arc in bible.plot_arcs.items()},
            "chapter_outlines": {str(num): self._chapter_outline_to_dict(outline) 
                                for num, outline in bible.chapter_outlines.items()},
            "volume_plans": {str(num): self._volume_plan_to_dict(plan)
                            for num, plan in bible.volume_plans.items()},
            "volume_summaries": {str(num): summary for num, summary in bible.volume_summaries.items()},
            "open_loops": {loop_id: self._open_loop_to_dict(loop) for loop_id, loop in bible.open_loops.items()},
            "event_history": [self._event_to_dict(event) for event in bible.event_history],
            "main_plot_summary": bible.main_plot_summary,
            "ending": bible.ending,
            "major_turning_points": bible.major_turning_points,
            "current_chapter": bible.current_chapter,
            "created_at": bible.created_at,
            "updated_at": bible.updated_at,
            "version": bible.version
        }
    
    def _dict_to_bible(self, data: dict) -> StoryBible:
        """将字典转换为 StoryBible"""
        bible = StoryBible(
            story_title=data.get("story_title", ""),
            genre=data.get("genre", ""),
            target_chapters=data.get("target_chapters", 1000),
            world_settings=self._dict_to_world_settings(data.get("world_settings", {})),
            characters={name: self._dict_to_character(char_data) 
                       for name, char_data in data.get("characters", {}).items()},
            plot_arcs={arc_id: self._dict_to_plot_arc(arc_data) 
                      for arc_id, arc_data in data.get("plot_arcs", {}).items()},
            chapter_outlines={int(num): self._dict_to_chapter_outline(outline_data) 
                            for num, outline_data in data.get("chapter_outlines", {}).items()},
            volume_plans={int(num): self._dict_to_volume_plan(plan_data)
                         for num, plan_data in data.get("volume_plans", {}).items()},
            volume_summaries={int(num): summary for num, summary in data.get("volume_summaries", {}).items()},
            open_loops={loop_id: self._dict_to_open_loop(loop_data) 
                       for loop_id, loop_data in data.get("open_loops", {}).items()},
            event_history=[self._dict_to_event(event_data) 
                          for event_data in data.get("event_history", [])],
            main_plot_summary=data.get("main_plot_summary", ""),
            ending=data.get("ending", ""),
            major_turning_points=data.get("major_turning_points", []),
            current_chapter=data.get("current_chapter", 0),
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat()),
            version=data.get("version", 1)
        )
        return bible
    
    def _character_to_dict(self, char: CharacterCard) -> dict:
        """角色转字典"""
        return {
            "name": char.name,
            "alias": char.alias,
            "identity": char.identity,
            "current_location": char.current_location,
            "state": char.state.value,
            "power_level": char.power_level,
            "power_history": char.power_history,
            "cultivation_stage": char.cultivation_stage,
            "special_abilities": char.special_abilities,
            "personality_keywords": char.personality_keywords,
            "psychological_state": char.psychological_state,
            "character_arc_progress": char.character_arc_progress,
            "personality_coordinates": char.personality_coordinates,
            "relationships": char.relationships,
            "inventory": char.inventory,
            "resources": char.resources,
            "major_events": char.major_events,
            "first_appearance_chapter": char.first_appearance_chapter,
            "biography": char.biography,
            "highlights": char.highlights,
            "detailed_relationships": char.detailed_relationships,
            "created_at": char.created_at,
            "updated_at": char.updated_at
        }
    
    def _dict_to_character(self, data: dict) -> CharacterCard:
        """字典转角色"""
        return CharacterCard(
            name=data["name"],
            alias=data.get("alias", []),
            identity=data.get("identity", ""),
            current_location=data.get("current_location", ""),
            state=CharacterState(data.get("state", "alive")),
            power_level=data.get("power_level", 0),
            power_history=data.get("power_history", []),
            cultivation_stage=data.get("cultivation_stage", ""),
            special_abilities=data.get("special_abilities", []),
            personality_keywords=data.get("personality_keywords", []),
            psychological_state=data.get("psychological_state", ""),
            character_arc_progress=data.get("character_arc_progress", 0.0),
            personality_coordinates=data.get("personality_coordinates", {}),
            relationships=data.get("relationships", {}),
            inventory=data.get("inventory", []),
            resources=data.get("resources", {}),
            major_events=data.get("major_events", []),
            first_appearance_chapter=data.get("first_appearance_chapter"),
            biography=data.get("biography", ""),
            highlights=data.get("highlights", []),
            detailed_relationships=data.get("detailed_relationships", ""),
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat())
        )
    
    def _world_settings_to_dict(self, world: WorldSettings) -> dict:
        """世界观转字典"""
        return {
            "world_name": world.world_name,
            "world_type": world.world_type,
            "power_system": world.power_system,
            "power_ceiling": world.power_ceiling,
            "growth_rate_limit": world.growth_rate_limit,
            "geography": world.geography,
            "factions": world.factions,
            "economy": world.economy,
            "timeline": world.timeline,
            "physics_rules": world.physics_rules,
            "created_at": world.created_at,
            "updated_at": world.updated_at
        }
    
    def _dict_to_world_settings(self, data: dict) -> WorldSettings:
        """字典转世界观"""
        return WorldSettings(
            world_name=data.get("world_name", ""),
            world_type=data.get("world_type", ""),
            power_system=data.get("power_system", {}),
            power_ceiling=data.get("power_ceiling", 1000000.0),
            growth_rate_limit=data.get("growth_rate_limit", 0.05),
            geography=data.get("geography", {}),
            factions=data.get("factions", {}),
            economy=data.get("economy", {}),
            timeline=data.get("timeline", []),
            physics_rules=data.get("physics_rules", []),
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat())
        )
    
    def _plot_arc_to_dict(self, arc: PlotArc) -> dict:
        """剧情弧转字典"""
        return {
            "arc_id": arc.arc_id,
            "arc_type": arc.arc_type,
            "title": arc.title,
            "start_chapter": arc.start_chapter,
            "end_chapter": arc.end_chapter,
            "summary": arc.summary,
            "main_conflict": arc.main_conflict,
            "climax_chapter": arc.climax_chapter,
            "main_characters": arc.main_characters,
            "supporting_characters": arc.supporting_characters,
            "protagonist_goal": arc.protagonist_goal,
            "outcome": arc.outcome,
            "sub_arcs": arc.sub_arcs,
            "created_at": arc.created_at
        }
    
    def _dict_to_plot_arc(self, data: dict) -> PlotArc:
        """字典转剧情弧"""
        return PlotArc(
            arc_id=data["arc_id"],
            arc_type=data["arc_type"],
            title=data["title"],
            start_chapter=data["start_chapter"],
            end_chapter=data["end_chapter"],
            summary=data.get("summary", ""),
            main_conflict=data.get("main_conflict", ""),
            climax_chapter=data.get("climax_chapter"),
            main_characters=data.get("main_characters", []),
            supporting_characters=data.get("supporting_characters", []),
            protagonist_goal=data.get("protagonist_goal", ""),
            outcome=data.get("outcome", ""),
            sub_arcs=data.get("sub_arcs", []),
            created_at=data.get("created_at", datetime.now().isoformat())
        )
    
    def _chapter_outline_to_dict(self, outline: ChapterOutline) -> dict:
        """章节大纲转字典"""
        return {
            "chapter_number": outline.chapter_number,
            "title": outline.title,
            "summary": outline.summary,
            "detailed_outline": outline.detailed_outline,
            "scenes": outline.scenes,
            "characters": outline.characters,
            "loops_planted": outline.loops_planted,
            "loops_resolved": outline.loops_resolved,
            "status": outline.status,
            "created_at": outline.created_at,
            "updated_at": outline.updated_at
        }
    
    def _dict_to_chapter_outline(self, data: dict) -> ChapterOutline:
        """字典转章节大纲"""
        return ChapterOutline(
            chapter_number=data["chapter_number"],
            title=data["title"],
            summary=data.get("summary", ""),
            detailed_outline=data.get("detailed_outline", ""),
            scenes=data.get("scenes", []),
            characters=data.get("characters", []),
            loops_planted=data.get("loops_planted", []),
            loops_resolved=data.get("loops_resolved", []),
            status=data.get("status", "planned"),
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat())
        )
    
    def _open_loop_to_dict(self, loop: OpenLoop) -> dict:
        """伏笔转字典"""
        return {
            "loop_id": loop.loop_id,
            "title": loop.title,
            "description": loop.description,
            "planted_chapter": loop.planted_chapter,
            "planted_content": loop.planted_content,
            "status": loop.status.value,
            "resolved_chapter": loop.resolved_chapter,
            "resolution": loop.resolution,
            "ttl": loop.ttl,
            "weight": loop.weight,
            "category": loop.category,
            "related_entities": loop.related_entities,
            "created_at": loop.created_at
        }
    
    def _dict_to_open_loop(self, data: dict) -> OpenLoop:
        """字典转伏笔"""
        return OpenLoop(
            loop_id=data["loop_id"],
            title=data["title"],
            description=data["description"],
            planted_chapter=data["planted_chapter"],
            planted_content=data["planted_content"],
            status=LoopStatus(data.get("status", "open")),
            resolved_chapter=data.get("resolved_chapter"),
            resolution=data.get("resolution", ""),
            ttl=data.get("ttl", 50),
            weight=data.get("weight", 5),
            category=data.get("category", ""),
            related_entities=data.get("related_entities", []),
            created_at=data.get("created_at", datetime.now().isoformat())
        )
    
    def _event_to_dict(self, event: EventRecord) -> dict:
        """事件转字典"""
        return {
            "event_id": event.event_id,
            "chapter": event.chapter,
            "event_type": event.event_type,
            "description": event.description,
            "facts": event.facts,
            "affected_characters": event.affected_characters,
            "timestamp": event.timestamp
        }
    
    def _dict_to_event(self, data: dict) -> EventRecord:
        """字典转事件"""
        return EventRecord(
            event_id=data["event_id"],
            chapter=data["chapter"],
            event_type=data["event_type"],
            description=data["description"],
            facts=data.get("facts", {}),
            affected_characters=data.get("affected_characters", []),
            timestamp=data.get("timestamp", datetime.now().isoformat())
        )
    
    def list_saved_bibles(self) -> list:
        """列出所有保存的故事圣经"""
        return [f.name for f in self.bible_dir.glob("*.json")]
    
    def list_backups(self) -> list:
        """列出所有备份文件"""
        return sorted([f.name for f in self.backup_dir.glob("*.json")], reverse=True)
    
    def _volume_plan_to_dict(self, plan: VolumePlan) -> dict:
        """卷规划转字典"""
        return {
            "volume_number": plan.volume_number,
            "title": plan.title,
            "summary": plan.summary,
            "main_conflict": plan.main_conflict,
            "protagonist_growth": plan.protagonist_growth,
            "key_events": plan.key_events,
            "key_characters": plan.key_characters,
            "new_characters": plan.new_characters,
            "loops_to_resolve": plan.loops_to_resolve,
            "loops_to_plant": plan.loops_to_plant,
            "phase": plan.phase,
            "created_at": plan.created_at
        }
    
    def _dict_to_volume_plan(self, data: dict) -> VolumePlan:
        """字典转卷规划"""
        return VolumePlan(
            volume_number=data["volume_number"],
            title=data["title"],
            summary=data.get("summary", ""),
            main_conflict=data.get("main_conflict", ""),
            protagonist_growth=data.get("protagonist_growth", ""),
            key_events=data.get("key_events", []),
            key_characters=data.get("key_characters", []),
            new_characters=data.get("new_characters", []),
            loops_to_resolve=data.get("loops_to_resolve", []),
            loops_to_plant=data.get("loops_to_plant", []),
            phase=data.get("phase", ""),
            created_at=data.get("created_at", datetime.now().isoformat())
        )
