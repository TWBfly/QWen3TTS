# Story-Sisyphus 多智能体网文创作系统

基于 Manager-Worker 分层架构的自动化网文创作系统,能够生成 200 章以上逻辑严谨的长篇小说大纲。

## 系统架构

### 核心组件

- **Main Agent (总编)**: 宏观控盘、任务分发、决策仲裁
- **Character Architect (角色架构师)**: 角色管理、弧光监测、铺垫设计
- **World Keeper (逻辑守门人)**: 世界观管理、战力体系、逻辑校验
- **Plot Weaver (情节推演师)**: 细纲输出、冲突制造
- **Continuity Tracker (伏笔稽查员)**: 伏笔管理、回收提醒、一致性检索

### 核心机制

1. **Shadow Registry (影子注册表)**: 确保重要人物在登场前有充分铺垫
2. **Event Sourcing (事件溯源)**: 只记忆事实,用于逻辑一致性检查
3. **Trajectory Analysis (轨迹分析)**: 监测角色性格坐标变化,检测 OOC
4. **Chekhov's Gun Scheduler (契诃夫之枪调度器)**: 管理伏笔 TTL 和回收

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
# OpenAI
export LLM_PROVIDER=openai
export LLM_MODEL=gpt-4
export LLM_API_KEY=your_api_key

# 或使用 Anthropic
export LLM_PROVIDER=anthropic
export LLM_MODEL=claude-3-opus-20240229
export LLM_API_KEY=your_api_key

# 或使用本地模型
export LLM_PROVIDER=local
export LLM_BASE_URL=http://localhost:8000/v1
```

### 3. 初始化故事

```bash
python main.py init \
  --genre 修仙 \
  --chapters 200 \
  --protagonist "一个普通少年,意外获得神秘传承" \
  --world "修仙世界" \
  --power-system "练气、筑基、金丹、元婴、化神"
```

### 4. 生成章节大纲

```bash
python main.py generate --count 10 --arc "主角获得传承,开始修炼"
```

### 5. 查看状态

```bash
python main.py status
```

## 使用示例

查看 `example.py` 了解详细的 API 使用方法:

```python
from config import Config
from storage import StorageManager
from workflow.initialization import InitializationPhase
from workflow.generation_loop import GenerationLoop

# 初始化
storage = Config.get_storage_manager()
init_phase = InitializationPhase(storage)

bible = init_phase.initialize_story(
    genre="修仙",
    target_chapters=200,
    protagonist_info="普通少年获得传承",
    world_type="修仙世界",
    power_system_description="练气到渡劫九个境界"
)

# 生成章节
gen_loop = GenerationLoop(storage)
outlines = gen_loop.generate_chapters(
    bible=bible,
    start_chapter=1,
    end_chapter=10,
    arc_description="主角开始修炼"
)
```

## 项目结构

```
story/
├── models.py                    # 核心数据模型
├── storage.py                   # 存储管理器
├── config.py                    # 系统配置
├── main.py                      # 主程序入口
├── example.py                   # 使用示例
├── agents/                      # Agent 层
│   ├── base_agent.py           # Agent 基类
│   ├── main_agent.py           # Main Agent
│   ├── character_architect.py  # 角色架构师
│   ├── world_keeper.py         # 逻辑守门人
│   ├── plot_weaver.py          # 情节推演师
│   └── continuity_tracker.py   # 伏笔稽查员
├── mechanisms/                  # 机制层
│   ├── shadow_registry.py      # 影子注册表
│   ├── event_sourcing.py       # 事件溯源
│   ├── trajectory_analysis.py  # 轨迹分析
│   └── chekhov_gun.py          # 契诃夫之枪调度器
├── workflow/                    # 工作流层
│   ├── initialization.py       # 初始化阶段
│   └── generation_loop.py      # 生成循环
└── utils/                       # 工具层
    └── llm_client.py           # LLM 客户端
```

## 核心特性

### 1. 长线逻辑保证

- 事件溯源机制确保前后一致
- 自动检测逻辑矛盾(如已死角色再次出现)
- 战力体系严格校验

### 2. 人物弧光管理

- 性格坐标系追踪角色成长
- OOC (Out of Character) 自动检测
- 重要人物强制铺垫机制

### 3. 伏笔智能管理

- TTL (Time To Live) 自动提醒
- 权重优先级调度
- 超期伏笔警告

### 4. 滑动窗口生成

- 批量生成 5-10 章
- 状态持久化和版本控制
- 支持断点续写

## 工作流程

### 创世纪阶段 (Initialization)

1. 创建世界观设定
2. 设计主线骨架和转折点
3. 创建主角和核心人物
4. 保存 Story Bible

### 增量生成循环 (Generation Loop)

每次生成一个剧情单元(5-10 章):

1. **Context Loading**: 加载当前状态、活跃伏笔、待铺垫角色
2. **Planning**: 规划伏笔回收和新伏笔埋下
3. **Simulation & Drafting**: Plot Weaver 生成大纲
4. **Validation**: World Keeper 进行逻辑校验
5. **Commit & Update**: 更新 Story Bible 和状态

## 配置选项

在 `config.py` 中可以配置:

- LLM 提供商和模型
- 默认伏笔 TTL
- 人物铺垫最少提及次数
- 生成批次大小

## 注意事项

1. **LLM API 成本**: 生成 200 章大纲需要大量 API 调用,请注意成本控制
2. **生成质量**: 依赖 LLM 质量,建议使用 GPT-4 或 Claude-3-Opus
3. **人工审核**: 系统生成的是大纲,仍需人工审核和调整
4. **存储空间**: Story Bible 会随着章节增加而变大,注意磁盘空间

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request!
