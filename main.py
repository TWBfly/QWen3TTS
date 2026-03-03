"""
Story-Sisyphus 主程序入口
"""

import sys
import argparse
from pathlib import Path

# 添加当前目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from config import Config
from storage import StorageManager
from workflow.initialization import InitializationPhase
from workflow.generation_loop import GenerationLoop


def init_command(args):
    """初始化命令"""
    storage = Config.get_storage_manager(args.story)
    init_phase = InitializationPhase(storage)
    
    # 解析写作标签
    writing_tags = []
    if args.tags:
        writing_tags = [tag.strip() for tag in args.tags.split(',') if tag.strip()]
    
    # 初始化故事
    bible = init_phase.initialize_story(
        genre=args.genre,
        target_chapters=args.chapters,
        protagonist_info=args.protagonist,
        world_type=args.world,
        power_system_description=args.power_system,
        ending_type=args.ending,
        writing_tags=writing_tags
    )
    
    print(f"\n✓ 故事初始化完成: {bible.story_title}")
    print(f"  类型: {bible.genre}")
    print(f"  目标章节: {bible.target_chapters}")
    if bible.writing_tags:
        print(f"  写作标签: {', '.join(bible.writing_tags)}")


def generate_command(args):
    """生成命令"""
    storage = Config.get_storage_manager(args.story)
    init_phase = InitializationPhase(storage)
    gen_loop = GenerationLoop(storage)
    
    # 加载故事
    bible = init_phase.load_existing_story(args.file)
    
    if not bible:
        print("✗ 故事文件不存在,请先运行 init 命令初始化")
        return
    
    # 确定生成范围
    start_chapter = bible.current_chapter + 1
    end_chapter = min(start_chapter + args.count - 1, bible.target_chapters)
    
    print(f"\n准备生成第 {start_chapter}-{end_chapter} 章...")
    
    # 生成章节 (Fix #4: 使用新的 generate_chapters 签名)
    outlines = gen_loop.generate_chapters(
        bible=bible,
        start_chapter=start_chapter,
        end_chapter=end_chapter
    )
    
    print(f"\n✓ 生成完成!共生成 {len(outlines)} 章")
    print(f"  当前进度: {bible.current_chapter}/{bible.target_chapters}")


def export_command(args):
    """导出命令"""
    storage = Config.get_storage_manager(args.story)
    init_phase = InitializationPhase(storage)
    
    bible = init_phase.load_existing_story(args.file)
    
    if not bible:
        print("✗ 故事文件不存在")
        return
        
    path = storage.export_bible_to_markdown(bible, args.output)
    print(f"\n✓ 导出完成: {path}")


def status_command(args):
    """状态命令"""
    storage = Config.get_storage_manager(args.story)
    init_phase = InitializationPhase(storage)
    
    bible = init_phase.load_existing_story(args.file)
    
    if not bible:
        print("✗ 故事文件不存在")
        return
    
    print("\n" + "=" * 60)
    print(f"故事状态: {bible.story_title}")
    print("=" * 60)
    print(f"类型: {bible.genre}")
    if bible.writing_tags:
        print(f"写作标签: {', '.join(bible.writing_tags)}")
    print(f"进度: {bible.current_chapter}/{bible.target_chapters} 章")
    print(f"完成度: {bible.current_chapter/bible.target_chapters*100:.1f}%")
    print(f"版本: v{bible.version}")
    print(f"\n角色数: {len(bible.characters)}")
    print(f"卷规划: {len(bible.volume_plans)}")
    print(f"活跃伏笔: {len(bible.get_active_loops())}")
    print(f"超期伏笔: {len(bible.get_overdue_loops())}")
    print(f"事件记录: {len(bible.event_history)}")
    
    # 显示卷规划详情
    if hasattr(args, 'show_volumes') and args.show_volumes and bible.volume_plans:
        print("\n" + "-" * 60)
        print("卷规划详情:")
        print("-" * 60)
        for vol_num in sorted(bible.volume_plans.keys()):
            plan = bible.volume_plans[vol_num]
            print(f"  第{vol_num}卷《{plan.title}》[{plan.phase}]")
            print(f"    冲突: {plan.main_conflict}")
            print(f"    主角成长: {plan.protagonist_growth}")

def plan_volumes_command(args):
    """独立生成/补全百卷总纲 (Fix #3)"""
    storage = Config.get_storage_manager(args.story)
    init_phase = InitializationPhase(storage)
    
    bible = init_phase.load_existing_story(args.file)
    
    if not bible:
        print("✗ 故事文件不存在，请先运行 init 命令初始化")
        return
    
    total_volumes = bible.target_chapters // Config.VOLUME_SIZE
    existing_count = len(bible.volume_plans)
    
    print(f"\n当前已有 {existing_count}/{total_volumes} 卷规划")
    
    if existing_count >= total_volumes and not args.force:
        print("✓ 百卷总纲已完整，无需重新生成")
        print("  如需重新生成，请使用 --force 参数")
        return
    
    from agents.main_agent import MainAgent
    from agents.logic_verifier import LogicVerifier
    main_agent = MainAgent()
    verifier = LogicVerifier()
    
    limit = getattr(args, 'limit', 5)
    
    if args.force:
        end_volume = min(total_volumes, limit)
        print(f"\n⚠️ 强制重新生成全部 {total_volumes} 卷规划... (为保证质量，本次只生成第 1 到 {end_volume} 卷)")
        volume_plans = main_agent.generate_all_volumes_plan(
            bible=bible,
            total_volumes=total_volumes,
            start_volume=1,
            end_volume=end_volume,
            verifier=verifier
        )
    else:
        # 从缺失的卷开始补全
        start_vol = existing_count + 1
        end_vol = min(total_volumes, existing_count + limit)
        print(f"\n📝 补全缺失的卷规划... 本次计划生成第 {start_vol} 到 {end_vol} 卷 (限制: 每次最多 {limit} 卷)")
        volume_plans = main_agent.generate_all_volumes_plan(
            bible=bible,
            total_volumes=total_volumes,
            start_volume=start_vol,
            end_volume=end_vol,
            verifier=verifier
        )
    
    print(f"\n✓ 卷规划生成完成: 共 {len(bible.volume_plans)} 卷")
    
    # 保存
    storage.save_story_bible(bible)
    print(f"✓ 已保存到 {args.file}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="Story-Sisyphus - 多智能体网文创作系统"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="命令")
    
    # init 命令
    init_parser = subparsers.add_parser("init", help="初始化新故事")
    init_parser.add_argument("--story", required=False, default=None, help="内部数据隔离用的故事名称标记")
    init_parser.add_argument("--genre", required=True, help="类型(修仙/玄幻/都市等)")
    init_parser.add_argument("--chapters", type=int, default=1000, help="目标章节数 (默认1000章=100卷)")
    init_parser.add_argument("--protagonist", required=True, help="主角信息")
    init_parser.add_argument("--world", required=True, help="世界类型")
    init_parser.add_argument("--power-system", required=True, help="战力体系描述")
    init_parser.add_argument("--ending", default="开放式", help="结局类型")
    init_parser.add_argument("--tags", default="", help="写作标签，多个用逗号分隔，如: 群像,团宠,甜宠")
    
    # generate 命令
    gen_parser = subparsers.add_parser("generate", help="生成章节大纲")
    gen_parser.add_argument("--story", required=False, default=None, help="故事名称以用于文件夹隔离")
    gen_parser.add_argument("--file", default="story_bible.json", help="故事文件")
    gen_parser.add_argument("--count", type=int, default=10, help="生成章节数 (默认一卷=10章)")
    
    # export 命令
    export_parser = subparsers.add_parser("export", help="导出故事文件")
    export_parser.add_argument("--story", required=False, default=None, help="故事名称")
    export_parser.add_argument("--file", default="story_bible.json", help="源文件")
    export_parser.add_argument("--output", default="story_export.md", help="输出文件")
    
    # status 命令
    status_parser = subparsers.add_parser("status", help="查看故事状态")
    status_parser.add_argument("--story", required=False, default=None, help="故事名称")
    status_parser.add_argument("--file", default="story_bible.json", help="故事文件")
    status_parser.add_argument("--show-volumes", action="store_true", help="显示卷规划详情")
    
    # plan-volumes 命令 (Fix #3)
    plan_parser = subparsers.add_parser("plan-volumes", help="独立生成/补全百卷总纲")
    plan_parser.add_argument("--story", required=False, default=None, help="故事名称")
    plan_parser.add_argument("--file", default="story_bible.json", help="故事文件")
    plan_parser.add_argument("--force", action="store_true", help="强制重新生成全部卷规划")
    plan_parser.add_argument("--limit", type=int, default=5, help="单次最大生成卷数，防止模型生产品质下降")
    
    args = parser.parse_args()
    
    # 补充逻辑：如果用户没有提供 --story 参数，尝试在初始化时自动从 --title 获取（如果存在的话）
    if getattr(args, 'story', None) is None:
        if hasattr(args, 'title') and args.title:
            args.story = args.title
        else:
            args.story = "default_story"
    
    if args.command == "init":
        init_command(args)
    elif args.command == "generate":
        generate_command(args)
    elif args.command == "plan-volumes":
        plan_volumes_command(args)
    elif args.command == "export":
        export_command(args)
    elif args.command == "status":
        status_command(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
