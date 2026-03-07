#!/usr/bin/env python3
"""
小说分析 CLI (Novel Analysis CLI)
====================================
从原著 TXT 中提取叙事 DNA 并存入知识库。

用法:
  # 分析小说
  python analyze_novel.py --novel-dir /path/to/大王饶命 --name "大王饶命"
  
  # 限制分析前 5 卷
  python analyze_novel.py --novel-dir /path/to/大王饶命 --name "大王饶命" --max-volumes 5
  
  # 强制重新分析
  python analyze_novel.py --novel-dir /path/to/大王饶命 --name "大王饶命" --force
  
  # 查看知识库统计
  python analyze_novel.py --stats
  
  # 搜索模式
  python analyze_novel.py --search "底层逆袭型主角"
  
  # 搜索特定类别
  python analyze_novel.py --search "扮猪吃虎" --category plot_pattern
  
  # 查看某本小说的所有模式
  python analyze_novel.py --list-source "大王饶命"
  
  # 删除某本小说的分析结果
  python analyze_novel.py --delete-source "大王饶命"
"""

import os
import sys
import argparse

# 确保项目根目录在 path 中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from knowledge.knowledge_store import KnowledgeStore, ALL_CATEGORIES
from knowledge.novel_analyzer import NovelAnalyzer
from knowledge.pattern_injector import PatternInjector


def cmd_analyze(args):
    """分析小说"""
    if not args.novel_dir or not args.name:
        print("❌ 请提供 --novel-dir 和 --name 参数")
        return
    
    if not os.path.isdir(args.novel_dir):
        print(f"❌ 目录不存在: {args.novel_dir}")
        return
    
    store = KnowledgeStore()
    
    if args.force:
        print(f"🗑️ 清除《{args.name}》旧数据...")
        store.delete_source_patterns(args.name)
    
    analyzer = NovelAnalyzer(knowledge_store=store)
    result = analyzer.analyze_novel(
        novel_dir=args.novel_dir,
        novel_name=args.name,
        max_volumes=args.max_volumes or 0,
        skip_existing=not args.force,
    )
    
    if not result.get("skipped"):
        print(f"\n✅ 分析完成! 共提取 {result['total_patterns']} 个叙事模式")
    
    store.close()


def cmd_stats(args):
    """查看统计"""
    store = KnowledgeStore()
    stats = store.get_stats()
    
    print(f"\n{'='*50}")
    print(f"📊 知识库统计")
    print(f"{'='*50}")
    print(f"  总模式数: {stats['total_patterns']}")
    
    category_names = {
        "archetype": "角色原型",
        "plot_pattern": "剧情模式",
        "relationship": "关系动态",
        "pacing": "节奏模板",
    }
    
    for cat, count in stats['by_category'].items():
        name = category_names.get(cat, cat)
        print(f"  - {name}: {count}")
    
    if stats.get('avg_quality_score'):
        print(f"  平均质量分: {stats['avg_quality_score']}")
    
    if stats['sources']:
        print(f"\n  📚 已分析小说:")
        for src in stats['sources']:
            status_icon = "✅" if src['analysis_status'] == 'completed' else "🔄"
            print(f"    {status_icon} {src['name']} ({src['analyzed_volumes']}/{src['total_volumes']} 卷)")
    else:
        print(f"\n  📚 暂无已分析的小说")
    
    print(f"{'='*50}")
    store.close()


def cmd_search(args):
    """搜索模式"""
    store = KnowledgeStore()
    
    results = store.search(
        query=args.search,
        category=args.category,
        top_k=args.top_k or 5,
    )
    
    if not results:
        print(f"未找到与 \"{args.search}\" 相关的模式")
        store.close()
        return
    
    category_names = {
        "archetype": "角色原型",
        "plot_pattern": "剧情模式",
        "relationship": "关系动态",
        "pacing": "节奏模板",
    }
    
    print(f"\n🔍 搜索: \"{args.search}\"  (找到 {len(results)} 个结果)\n")
    
    for i, r in enumerate(results, 1):
        cat_name = category_names.get(r['category'], r['category'])
        tags_str = f" [{', '.join(r['tags'])}]" if r.get('tags') else ""
        print(f"  {i}. [{cat_name}] 【{r['name']}】{tags_str}")
        print(f"     {r['description']}")
        print(f"     来源: 《{r['source_novel']}》第{r['source_volume']}卷 | "
              f"评分: {r['quality_score']:.1f} | 相似度: {r['similarity']:.3f}")
        print()
    
    store.close()


def cmd_list_source(args):
    """列出某本小说的所有模式"""
    store = KnowledgeStore()
    patterns = store.get_patterns_by_source(args.list_source)
    
    if not patterns:
        print(f"未找到来自《{args.list_source}》的模式")
        store.close()
        return
    
    category_names = {
        "archetype": "角色原型",
        "plot_pattern": "剧情模式",
        "relationship": "关系动态",
        "pacing": "节奏模板",
    }
    
    print(f"\n📚 《{args.list_source}》的叙事模式 ({len(patterns)} 个)\n")
    
    current_cat = None
    for p in patterns:
        cat = p.get('category', '')
        if cat != current_cat:
            current_cat = cat
            cat_name = category_names.get(cat, cat)
            print(f"\n  === {cat_name} ===")
        
        tags_str = ""
        if p.get('tags'):
            try:
                import json
                tags = json.loads(p['tags']) if isinstance(p['tags'], str) else p['tags']
                if tags:
                    tags_str = f" [{', '.join(tags)}]"
            except Exception:
                pass
        
        print(f"  #{p['id']} 【{p['name']}】{tags_str}")
        desc = p.get('description', '')
        print(f"    {desc[:100]}{'...' if len(desc)>100 else ''}")
    
    print()
    store.close()


def cmd_inject_test(args):
    """测试模式注入效果"""
    injector = PatternInjector()
    prompt = injector.get_injection_prompt(
        description=args.inject_test,
        top_k_per_category=2,
    )
    
    if prompt:
        print(f"\n{'='*60}")
        print("📝 生成的注入 Prompt:")
        print(f"{'='*60}")
        print(prompt)
        print(f"{'='*60}")
    else:
        print("知识库为空或无匹配模式")


def main():
    parser = argparse.ArgumentParser(
        description="小说分析 CLI — 提取叙事 DNA 存入知识库",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    # 分析模式
    parser.add_argument("--novel-dir", type=str, help="小说 TXT 文件目录")
    parser.add_argument("--name", type=str, help="小说名称")
    parser.add_argument("--max-volumes", type=int, default=0, help="最多分析几卷 (0=全部)")
    parser.add_argument("--force", action="store_true", help="强制重新分析（清除旧数据）")
    
    # 查询模式
    parser.add_argument("--stats", action="store_true", help="查看知识库统计")
    parser.add_argument("--search", type=str, help="搜索模式")
    parser.add_argument("--category", type=str, choices=ALL_CATEGORIES, help="搜索类别过滤")
    parser.add_argument("--top-k", type=int, default=5, help="搜索返回数量")
    parser.add_argument("--list-source", type=str, help="列出某本小说的所有模式")
    
    # 管理
    parser.add_argument("--delete-source", type=str, help="删除某本小说的所有模式")
    
    # 测试
    parser.add_argument("--inject-test", type=str, help="测试模式注入效果")
    
    args = parser.parse_args()
    
    # 路由
    if args.stats:
        cmd_stats(args)
    elif args.search:
        cmd_search(args)
    elif args.list_source:
        cmd_list_source(args)
    elif args.delete_source:
        store = KnowledgeStore()
        store.delete_source_patterns(args.delete_source)
        print(f"✅ 已删除《{args.delete_source}》的所有模式")
        store.close()
    elif args.inject_test:
        cmd_inject_test(args)
    elif args.novel_dir and args.name:
        cmd_analyze(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
