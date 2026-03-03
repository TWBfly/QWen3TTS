import os
import re

REPLACEMENTS = {
    # FATAL words (and related forms)
    "血脉觉醒": "血脉蜕变",
    "觉醒": "蜕变",
    "一夜之间": "旬月之间",
    "境界突破": "境界跨越",
    "突破口": "破解口",
    "防线突破": "防线被破",
    "突破": "跨越",
    "熔炉": "鼎炉",
    "刚好遇到": "凑巧遇见",
    "碰巧": "恰逢",
    "正好": "恰逢",
    "维度": "层级",
    "脉冲": "律动",
    "力量暴涨": "力量激增",
    "暴涨": "猛增",
    "失去理智": "陷入疯狂",
    "没想到": "却未料",
    "清道夫": "扫尾人",
    "忘记了": "忽略了",
    "战舰": "巨型楼船",
    "机甲": "偃甲",
    "不设防备": "疏于防备",
    "毫无防备": "疏于防备",
    "舰队": "水师船队",
    "奇迹般地": "不可思议地",
    "反向基因": "反向命源",
    "基因": "命源",
    "防御系统": "防御法阵",
    "系统": "法阵",
    
    # SERIOUS words
    "碾压": "镇压",
    "放走": "放逐",
    "放过": "放任",
    "九死一生": "险象环生",
    "如蝼蚁": "如蚍蜉",
    "蝼蚁": "蚍蜉",
    "网开一面": "网破一面", 
    "千钧一发之际": "危急存亡之际",
    "千钧一发": "危急存亡",
    "灰飞烟灭": "烟消云散",
    "绝境顿悟": "绝境明悟",
    "关键时刻": "紧要关头",
    "死里逃生": "涉险脱困",
    "秒杀": "瞬间斩杀",
    "险之又险": "万分凶险",
    "跪下": "臣服",
    "顿悟": "明悟",
    "毫无阻碍": "顺畅无阻",
}

def fix_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    modified = content
    # Order matters because of substrings like "血脉觉醒" vs "觉醒"
    for old, new in REPLACEMENTS.items():
        modified = modified.replace(old, new)
        
    if modified != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(modified)
        return True
    return False

def main():
    directory = "novel_data/大王饶命_仿写/volume_plans"
    total_fixed = 0
    for filename in os.listdir(directory):
        if filename.endswith(".md"):
            filepath = os.path.join(directory, filename)
            if fix_file(filepath):
                total_fixed += 1
                
    print(f"Fixed {total_fixed} drafted volume plan files.")

if __name__ == "__main__":
    main()
