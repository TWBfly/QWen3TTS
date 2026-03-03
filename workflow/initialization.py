"""
Initialization Phase (创世纪阶段) - 初始化 Story Bible
"""

import sys
import os
from typing import Dict, Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import StoryBible
from agents.main_agent import MainAgent
from agents.character_architect import CharacterArchitect
from agents.world_keeper import WorldKeeper
from storage import StorageManager


class InitializationPhase:
    """初始化阶段"""
    
    def __init__(self, storage_manager: StorageManager):
        """
        初始化
        
        Args:
            storage_manager: 存储管理器
        """
        self.storage = storage_manager
        self.main_agent = MainAgent()
        self.character_agent = CharacterArchitect()
        self.world_agent = WorldKeeper()
    
    def initialize_story(
        self,
        genre: str,
        target_chapters: int,
        protagonist_info: str,
        world_type: str,
        power_system_description: str,
        ending_type: str = "开放式",
        writing_tags: list = None,
        background_theme: str = ""
    ) -> StoryBible:
        """
        初始化故事
        
        Args:
            genre: 类型
            target_chapters: 目标章节数
            protagonist_info: 主角信息
            world_type: 世界类型
            power_system_description: 战力体系描述
            ending_type: 结局类型
            writing_tags: 写作标签列表，如 ["群像", "团宠"]，用于引导写作风格
            background_theme: 背景题材，如 "仙侠"、"东方玄幻"、"架空古代"，确保内容符合设定
            
        Returns:
            初始化的 Story Bible
        """
        print("=" * 60)
        print("开始创世纪阶段...")
        print("=" * 60)
        
        # 创建 Story Bible
        bible = StoryBible(
            genre=genre,
            target_chapters=target_chapters,
            writing_tags=writing_tags or [],
            background_theme=background_theme
        )
        
        # 输出选择的背景题材
        if bible.background_theme:
            print(f"\n🎭 背景题材: {bible.background_theme}")
            theme_constraints = bible.get_theme_constraints()
            if theme_constraints:
                print(f"   分类: {theme_constraints.get('category', '')}")
                print(f"   禁止元素: {', '.join(theme_constraints.get('forbidden_elements', [])[:5])}...")
        
        # 输出选择的写作标签
        if bible.writing_tags:
            print(f"\n📝 写作标签: {', '.join(bible.writing_tags)}")
        
        # Step 1: 创建世界观设定
        print("\n[Step 1/5] 创建世界观设定...")
        world_settings = self.world_agent.create_world_settings(
            world_type=world_type,
            genre=genre,
            power_system_description=power_system_description
        )
        # 将背景题材同步到世界观设定
        world_settings.background_theme = background_theme
        bible.world_settings = world_settings
        print(f"✓ 世界观创建完成: {world_settings.world_name}")
        
        # Step 2: 创建主线骨架
        print("\n[Step 2/5] 创建主线骨架...")
        plot_skeleton = self.main_agent.create_main_plot_skeleton(
            genre=genre,
            target_chapters=target_chapters,
            protagonist_info=protagonist_info,
            world_type=world_type,
            ending_type=ending_type
        )
        
        bible.story_title = plot_skeleton.get("story_title", "未命名")
        bible.main_plot_summary = plot_skeleton.get("main_plot_summary", "")
        bible.ending = plot_skeleton.get("ending", "")
        bible.major_turning_points = plot_skeleton.get("major_turning_points", [])
        
        print(f"✓ 主线骨架创建完成: {bible.story_title}")
        print(f"  转折点数量: {len(bible.major_turning_points)}")
        
        # Step 3: 生成全卷规划 (核心新增步骤)
        total_volumes = target_chapters // 10  # 计算总卷数
        print(f"\n[Step 3/5] 生成 {total_volumes} 卷宏观规划...")
        print("  ⚠️ 这一步骤需要较长时间，请耐心等待...")
        volume_plans = self.main_agent.generate_all_volumes_plan(
            bible=bible,
            total_volumes=total_volumes
        )
        print(f"✓ 卷规划生成完成: 共 {len(volume_plans)} 卷")
        
        # 中间保存，防止后续步骤失败导致卷规划丢失
        self.storage.save_story_bible(bible)
        print("  ✓ 卷规划已保存")
        
        # Step 4: 创建主角
        print("\n[Step 4/5] 创建主角...")
        protagonist = self.character_agent.create_character(
            name="主角",  # 可以从 protagonist_info 中提取
            identity=protagonist_info,
            personality_keywords=["勇敢", "坚韧"],
            power_level=10,
            role_in_story="主角",
            first_appearance_chapter=1
        )
        bible.add_character(protagonist)
        self.storage.save_character_profile(protagonist)
        print(f"✓ 主角创建完成: {protagonist.name} (已生成人物档案 .md)")
        
        # Step 5: 保存
        print("\n[Step 5/5] 保存 Story Bible...")
        saved_path = self.storage.save_story_bible(bible)
        print(f"✓ Story Bible 已保存: {saved_path}")
        
        print("\n" + "=" * 60)
        print("创世纪阶段完成!")
        print(f"  📖 故事: {bible.story_title}")
        print(f"  📚 卷数: {len(bible.volume_plans)}")
        print(f"  📝 章节目标: {bible.target_chapters}")
        print("=" * 60)
        
        return bible
    
    def load_existing_story(self, filename: str = "story_bible.json") -> StoryBible:
        """
        加载已有故事
        
        Args:
            filename: 文件名
            
        Returns:
            Story Bible
        """
        print(f"加载故事: {filename}...")
        bible = self.storage.load_story_bible(filename)
        
        if bible:
            print(f"✓ 故事加载成功: {bible.story_title}")
            print(f"  当前进度: 第 {bible.current_chapter} 章")
            print(f"  目标章节: {bible.target_chapters} 章")
            return bible
        else:
            print(f"✗ 文件不存在: {filename}")
            return None
