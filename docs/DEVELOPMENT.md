# V3 开发与模块交接

## 依赖与职责

配置加载→GameSession→统一动作／战场→公开观察与记录→控制器／界面／报告。
game不导入daylab，通过注入会话钩子记录；绘制不推进战斗，控制器不改实体或推进时钟。

|模块|责任与交接|
|---|---|
|configs/benchmark_v1.json、benchmark.py|十档波次和三套卡组→完整ExperimentConfig，统一加载入口|
|config.py、scenarios.py|配置校验、公开规则、配置与种子→确定性出怪表|
|game/catalog.py、content.py|内容登记、参数白名单、不同原实体所需的构造参数|
|game/experiment_plants.py|保留原攻击模式的时钟、咖啡目标绑定、火炬伤害归属|
|game/entities/、combat.py|原行为、碰撞、范围伤害和特殊交互|
|game/world.py、tracking.py|实体组、跨行子弹、地形和稳定生命周期事件|
|placement.py、actions.py、economy.py|共用种植规则、执行检查、去重、费用与冷却原子提交|
|session.py、runner.py|重置、20ms时钟、终局、实时／暂停思考调度|
|observation.py、board_context.py|白名单公开状态与文字棋盘，不提供隐藏血量和未来安排|
|state_codec.py、recording.py、replay.py|内部校验状态、严格JSON、保存动作重放|
|run_store.py|运行身份、分层路径与记录发现|
|controllers.py、request_limits.py|一个在途请求、输入保护、预算、解析、重试与恢复|
|cloud_transport.py、cloud_status.py|可取消HTTP与总时限、脱敏错误、中文说明|
|cloud_memory.py、prompting.py、prompts/|有界记忆、固定规则、可编辑风格和配置快照|
|cloud_metrics.py、plant_metrics.py、reports.py|从记录生成用量、植物贡献与对照报告|
|ui/、ui/layout.py|入口、8卡几何、输入、绘制、技术暂停、回放|

未加game/前缀的Python模块位于daylab/。

## Python调用

```python
from daylab.benchmark import load_benchmark
from daylab.session import GameSession
with GameSession(headless=True, record=False) as s:
    obs = s.reset(load_benchmark("06", "C"), seed=42)
    s.submit({"type":"PLACE_PLANT","plant_type":"FumeShroom","row":1,"col":3},
             obs["observation_id"], "local-001")
    s.advance(1)  # 仅离线测试／回放
    events = s.events(0)
```

主线程独占状态。正式控制器只调用observe/public_context/submit。submit接收不等于执行成功，以actions/action_result为准；相同command_id不能重复扣费，不同内容复用ID会拒绝。
云端使用CloudConfig.load、make_controller、make_runner，主线程持续runner.pulse(dt,now)；暂停思考时不要另调advance。paused_reason非空表示技术暂停，resume(session)不清零预算。结束先controller.close(session)，再session.close。

## 内容扩展

内容先登记catalog，再在content绑定原实体及依赖。杨桃、三线、大喷菇保留各自攻击，不套单行豌豆实现。
咖啡是临时覆盖物，grid保留蘑菇ID；提交从对应观察绑定目标，执行检查未更换。休眠、费用、唤醒动画和消耗均走共同路径。毁灭菇弹坑是terrain，不可铲。
子弹换行不算移除，一步只更新一次；火炬保留发射来源与增伤来源。自耗、被吃、铲除分别记录。
新增影响未来的计时器、对象引用、复合值要进入state_codec。修改可见状态时同步观察、棋盘、规则说明与校验。Pygame对象、组和内部精确血量不能直接导给模型。

## 配置与比较

load_benchmark为共同入口，实际配置和出怪表随局保存，基准JSON后续变更不改变保存的回放输入。
environment_id排除卡组、植物参数、控制者与显示标签；condition_id保留卡组和植物参数，排除控制者与显示标签。
跨方案保持环境、版本、时间模式、控制者及云端配置相同；同方案允许控制者不同。人工干预、技术故障和未完整结束记录不进入正式配对。

## 云端与验证

一次决策最多两次请求，网络重试和格式纠错共用机会。连续失败按决策计数，WAIT有效。输入裁剪只删旧历史和旧事实，实际payload与diagnostics保存；保守估算不得冒充实际usage。
暂停不补跑等待时间，恢复保留预算并标记。HTTP摘要只保留脱敏code/type/message，不记录环境变量值或Authorization。

维护验证以“配置→操作→观察/事件→保存→回放”贯通为主，新增机制分组验证，云端故障集中模拟。真实服务只做必要端到端验收。
按项目要求，临时脚本、模拟服务和测试记录验收后删除；正式运行诊断和回放校验继续保留。旧主游戏入口已退役，素材、来源声明和现有环境保留。
