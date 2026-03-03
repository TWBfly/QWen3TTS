"""
示例:如何使用 Story-Sisyphus 系统
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import Config
from storage import StorageManager
from workflow.initialization import InitializationPhase
from workflow.generation_loop import GenerationLoop


def example_1_initialize():
    """示例 1: 初始化一个修仙小说"""
    print("\n" + "=" * 60)
    print("示例 1: 初始化修仙小说")
    print("=" * 60)
    
    storage = Config.get_storage_manager()
    init_phase = InitializationPhase(storage)
    
    bible = init_phase.initialize_story(
        genre="修仙",
        target_chapters=200,
        protagonist_info="一个普通少年,意外获得神秘传承",
        world_type="修仙世界",
        power_system_description="练气、筑基、金丹、元婴、化神、炼虚、合体、大乘、渡劫",
        ending_type="开放式"
    )
    
    return bible


def example_2_generate_chapters():
    """示例 2: 生成前 10 章大纲"""
    print("\n" + "=" * 60)
    print("示例 2: 生成章节大纲")
    print("=" * 60)
    
    storage = Config.get_storage_manager()
    init_phase = InitializationPhase(storage)
    gen_loop = GenerationLoop(storage)
    
    # 加载故事
    bible = init_phase.load_existing_story()
    
    if not bible:
        print("请先运行 example_1_initialize() 初始化故事")
        return
    
    # 生成第 1-10 章
    outlines = gen_loop.generate_chapters(
        bible=bible,
        start_chapter=1,
        end_chapter=10,
        arc_description="主角获得传承,开始修炼之路"
    )
    
    print(f"\n生成了 {len(outlines)} 章大纲")
    
    # 显示第一章
    if outlines:
        first = outlines[0]
        print(f"\n第一章示例:")
        print(f"  标题: {first.title}")
        print(f"  概要: {first.summary}")


def example_3_check_status():
    """示例 3: 查看故事状态"""
    print("\n" + "=" * 60)
    print("示例 3: 查看故事状态")
    print("=" * 60)
    
    storage = Config.get_storage_manager()
    init_phase = InitializationPhase(storage)
    
    bible = init_phase.load_existing_story()
    
    if not bible:
        print("故事文件不存在")
        return
    
    print(f"\n故事: {bible.story_title}")
    print(f"进度: {bible.current_chapter}/{bible.target_chapters} 章")
    print(f"角色数: {len(bible.characters)}")
    print(f"活跃伏笔: {len(bible.get_active_loops())}")
    
    # 显示主线概要
    print(f"\n主线概要:")
    print(f"  {bible.main_plot_summary}")


if __name__ == "__main__":
    print("Story-Sisyphus 系统示例")
    print("=" * 60)
    
    # 运行示例
    # 注意:需要先设置 LLM API 密钥
    
    # 示例 1: 初始化
    # bible = example_1_initialize()
    
    # 示例 2: 生成章节
    # example_2_generate_chapters()
    
    # 示例 3: 查看状态
    # example_3_check_status()
    
    print("\n提示: 请取消注释上面的示例代码来运行")
    print("注意: 运行前请设置环境变量:")
    print("  export LLM_PROVIDER=openai")
    print("  export LLM_API_KEY=your_api_key")
