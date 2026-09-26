# 实验记录与数据格式

本页负责持久化文件、动作契约、公开信息边界和兼容规则。模块修改入口见 [开发与交接](DEVELOPMENT.md)，界面操作见 [使用说明](../README_DAY_LAB.md)。下文路径均相对于单局记录目录；示例命令在项目根目录运行。

## 版本的四个层次

1. `app_version: 2.0.0`：软件架构版本。
2. `config.profile: day_lab_v1` 与完整配置/环境安排：实际实验规则与条件。参数改变会改变配置/环境标识。
3. `schema_version: 2`：实验清单版本；V2 阅读器仍识别 V1 清单。
4. `stream_versions`：observation/action/event/checkpoint/model/result 目前均为 1。迁移没有为了文件拆分而重命名旧数据字段。

`schemas.validate_manifest()` 对未知清单或流版本报错。程序版本、规则版本和数据版本不能相互替代。

## 每局目录

| 文件 | 内容 |
|---|---|
| `manifest.json` | 配置、种子、完整环境安排、规则说明、软件/素材/依赖指纹、版本、实时/离线模式 |
| `result.json` | 状态、持续时间、是否正式结束、干预/时序异常标记、比较资格 |
| `submissions.jsonl` | 所有提交与接收状态，包括重复、拒绝、观察所对应的步 |
| `decisions.jsonl` | 接受的决策提交前公开输入，以及待比较动作标签；模型不能收到标签 |
| `actions.jsonl` | 实际执行动作、成功/失败原因、目标植物 ID |
| `events.jsonl` | 创建、资源变化、命中、伤害、防具破损、死亡、损失、移除、波次、结束等 |
| `observations.jsonl` | 每 100ms 和终局公开观察 |
| `checkpoints.jsonl` | 初始、每秒、终局和关闭时的内部状态及 SHA-256 |
| `wait_samples.jsonl` | 每 5 秒的公开等待样本；离线比较时排除紧邻真实操作的样本 |
| `raw_input.jsonl` | 鼠标/键盘输入，不能直接当成 AI 决策数量 |
| `model_config.jsonl`、`model_requests.jsonl`、`model_results.jsonl` | 分别保存服务配置、实际模型输入、回复/解析/错误/用量；不会保存密钥 |
| `timing.jsonl` | 模拟时间相对现实时间的滞后 |
| `errors.jsonl` | 正常捕获的技术异常 |

未发生相应行为的流可以不存在。所有模拟相关行带 `tick`、`sim_ms`；一般日志的 `event_seq` 表示写入时最近一个游戏事件序号。只有 `events` 的 `seq` 是事件自己的严格递增序号，不能假定不同文件所有行共享一个唯一序号。

## 动作契约

```json
{"type":"PLACE_PLANT","plant_type":"SunFlower","row":0,"col":0}
{"type":"REMOVE_PLANT","plant_id":"plant-00006"}
{"type":"WAIT"}
```

以上是三个独立示例，不是一次提交三个动作。行列从 0 开始。`submit(action, observation_id, command_id)` 先返回 receipt；接受只表示排队。执行时再次检查过期、余额、冷却、占用或目标是否还存在，结果写入 `action_result`。铲除绑定 ID，不绑定“某一格当前的植物”。

常见提交拒绝：`INVALID_ACTION`、`INVALID_OBSERVATION`、`STALE_OBSERVATION`、`RATE_LIMITED`、`COMMAND_ID_CONFLICT`、`EPISODE_ENDED`。

常见执行失败：`DISABLED_PLANT`、`OUT_OF_BOUNDS`、`OCCUPIED`、`INSUFFICIENT_SUN`、`COOLDOWN`、`TARGET_MISSING`。失败不会产生一次正常成功的资源消费。

## 公开观察与内部记录严格分开

公开观察含：局面编号与时间、阳光、卡片成本/冷却/可用性、格子占用、植物、实际可见的僵尸/子弹、小推车状态、已到达波次。

不提供：当前精确剩余血量、防具精确剩余血量、内部攻击倒计时、未来出怪、完全被遮挡/屏幕外敌人、内部目标引用。可见性依据实际绘制次序与不透明像素判断；自己的种植占用作为已知布局保留。

模型 `public_context()` 包含当前观察、此前五秒内每秒一份观察、已完成的公开动作和静态规则。参数覆盖是双方可查看的静态规则，不是运行中的隐藏血量。未来出怪表不进入模型输入。

内部检查点另含资源时钟、队列、命令去重状态、地图占用、未来环境、游戏随机源、实体计时器、帧集合、遮罩摘要、对象引用 ID、伤害来源。无穷大生命值写为 `hp: null` 和 `invulnerable: true`，不写非法 JSON 的 Infinity。实体上其余非有限值也转换为 null。

完整 `events()` 有伤害前后血量，属于研究者的本地调试流，不应原样送给 AI。内置控制器没有这样做。

## 回放与跨版本检查

正常回放要求代码、依赖、素材、锁文件等版本指纹匹配。它按原记录实际提交时刻重放所有提交（包括被拒绝的命令），并校验保存的内部检查点；同一步的多个检查点按最后一条读取。它不重新调用模型，也不重新运行真人输入。

- `verified: true`：版本匹配、检查点一致、动作覆盖完整。
- `state_match: true`：执行到终点且检查点一致；单独这一项不代表版本一致。
- `first_difference`：第一个不一致的时刻和字段。
- `recording_finalized`：原记录是否完整关闭；需单独查看，`verified: true` 本身不等于这局具备正式成绩比较资格。

V1 代码经过结构整理，代码指纹必然变化。原始记录保持不动，可以显式进行：

```powershell
.\.venv\Scripts\python.exe -B -m daylab replay experiments\某局目录 --migration-check
```

这个模式即使状态完全一致，版本不同仍返回 `verified: false`。启动菜单选旧记录时会先说明并请求确认。V2 新记录使用正常 `--verify` 即可。

回放校验不等于逐条比对公开观察文件与完整事件流，也不会把 V1/V2 成绩强行当作同版本配对。若修改这些数据流，需另行验证其输出兼容性。

## 修改字段的规则

- 只新增报告指标：尽量在 `reports.py` 从已有事件推导，不改变原始流。
- 新增公开字段：在 `observation.py` 明确列出，新增泄漏测试；更新公共协议和对应版本/兼容读取。
- 新增事件：明确发生时刻、实体 ID、是否与已有事件重复计数，并补测试。
- 改内部状态：在 `state_codec.py` 编码，检查值是否影响未来行为；复杂容器显式处理。
- 改字段含义/删除字段：升级流版本并实现迁移阅读逻辑，不能静默重解释旧数据。

数据读取与回放兼容不是同一承诺：旧数据可以用于分析，并不保证用新规则还能复现原来整局。跨版本自动转换目前没有通用实现。
