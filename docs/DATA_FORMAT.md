# 实验记录与数据格式

本页负责持久化文件、动作契约、公开信息边界和兼容规则。模块修改入口见 [开发与交接](DEVELOPMENT.md)，界面操作见 [使用说明](../README_DAY_LAB.md)。下文路径均相对于单局记录目录；示例命令在项目根目录运行。

## 版本的四个层次

1. `app_version: 2.0.0`：软件架构版本。
2. `config.profile: day_lab_v1` 与完整配置/环境安排：实际实验规则与条件。参数改变会改变配置/环境标识。
3. `schema_version: 2`：实验清单版本；V2 阅读器仍识别 V1 清单。
4. `stream_versions`：observation/action/event/checkpoint/model/result 目前均为 1。迁移没有为了文件拆分而重命名旧数据字段。

`schemas.validate_manifest()` 对未知清单或流版本报错。程序版本、规则版本和数据版本不能相互替代。

## 每局目录

新增 execution_mode：realtime / offline / pause_think，同时写入清单和最终结果；旧记录缺省按 realtime 布尔值推导。pause_think 的 realtime=false，但不能与普通离线或实时模式混同，报告会分别检查。decision_timing.jsonl 记录每次决策后推进长度及错误。预算耗尽以 budget_exhausted 结束，不算正常战败或正式成绩。

model_config 中 prompt_bundle 保存 framework、style 和 sha256，确保记录能辨识同路径文件后来被修改的情况。模板以 UTF-8 Markdown 编写，只有六个命名占位接口：rules/cards/style/timing/input_format/output_contract。实际 system 消息由 render_prompt() 生成。配置创建时快照；编辑文件后必须重新加载配置。此快照随配置参与报告比较；游戏状态回放不调用模板或模型。

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
| `model_submissions.jsonl` | 云端动作通过校验后提交给统一执行器的接收回执；最终成功与否仍以 actions / action_result 为准 |
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

云端回复还会在提交前按请求时的公开观察预检合法性。因此，同名错误若出现在 `model_results`，表示回复校验未通过，并不等于游戏执行失败。`error_stage` 区分 `format`、`observation` 与 `transport_or_lifecycle`；成功时为 null。收到模型合法动作、提交被接收、游戏实际执行成功是三个不同阶段。

可选的一次纠错以 `repair_of` 关联前一次请求；请求和结果都记录此字段，普通首答为 null，旧记录可缺省。纠错使用新的公开观察并重新检查时效，不执行原错误动作。统计时分别计算首答格式率、首答观察合法率、纠错恢复率、提交接收率及最终执行成功率，不能删除错误首答后把纠正结果统计为首答成功。以上为兼容的附加字段和诊断流，既有动作与观察格式不变。

## 公开观察与内部记录严格分开

公开观察含：局面编号与时间、阳光、卡片成本/冷却/可用性、格子占用、植物、实际可见的僵尸/子弹、小推车状态、已到达波次。

不提供：当前精确剩余血量、防具精确剩余血量、内部攻击倒计时、未来出怪、完全被遮挡/屏幕外敌人、内部目标引用。可见性依据实际绘制次序与不透明像素判断；自己的种植占用作为已知布局保留。

模型 `public_context()` 包含当前观察、此前五秒内每秒一份观察、已完成的公开动作和静态规则。参数覆盖是双方可查看的静态规则，不是运行中的隐藏血量。未来出怪表不进入模型输入。

云端配置可启用 `compact_context`：实际请求采用 `compact_public_v1`，以带列名的表格表达对象列表，并用最早历史观察及连续差异表达全部历史。可用 `daylab.cloud_context.expand_context()` 无损还原。模型请求文件保存实际发送内容，决策记录仍保留原始公开上下文；这不改变 observation 等持久化流版本。模型配置日志包含开关及请求间隔，比较时需同时检查它们。

兼容模式 `compact_context: false, history_encoding: "delta"`：当前观察保持原字段，历史编码标记为 `history_reverse_deltas_v1`。从当前观察依次应用由近到远的 `set/del` 路径操作，即可恢复各历史观察；`expand_delta_context()` 返回按原时间顺序排列的历史。规则移入固定 system 消息，未删除任何公开信息。

当前示例默认 `history_encoding: "board"`，请求 user.content 为 `text_board_v1` 文本，不再是可直接 json.loads 的对象。过去五秒内每秒一帧，按时间顺序排列，当前帧在最后。植物格与敌人表分开：敌人的 x/y 是精灵左上角像素位置，不是碰撞框或植物格编号；保留每只敌人，允许相同坐标及负坐标。未知植物用原类型名显示。当前帧有植物 ID/状态/外观、敌人可见状态、子弹、小推车和卡片费用/冷却/ready；省略可由冷却表达的进度小数。历史只呈现布局、敌人、资源、波次和小推车，不保存历史子弹、植物动画和历史卡片详情，因此无法无损逆变换。原始 context 仍在决策/观察记录，模型输入不含隐藏信息。

board/delta 与 compact_context=true 互斥。模型输出协议、原始观察协议和 parse_reply 的公开观察预检保持不变。不同输入编码是不同控制器配置，应分别评价模型效果；字节量变化不等同 Token 或缓存命中变化。

可选 `strategy_memory` 扩展模型回复外层为 action 与 strategy 两个必填字段，游戏 action 契约不变。strategy 只接受限长字符串；无效、过期、超时或提交拒绝的回复不更新备忘。启用 fact_memory 时仅从公开观察差异与已执行公开动作生成有界事实和整局计数，不能推断植物消失原因。请求前缀附 `episode_memory_v1` 数据，包括 facts/totals/strategy/strategy_sim_ms；原始请求和回复完整记录。`model_memory.jsonl` 记录已接收的策略更新，明确标记 intention_only，实际执行仍以 actions 为准。新 episode 清空记忆。离线同局面元数据 memory_policy 明确独立样本，不在样本间传播策略。

终局尚未采用的请求记录 `ABANDONED_AT_END`、`server_cancel_confirmed: false`、`usage_known: false`；旧 `CANCELLED_AT_END` 仍可读取。两者都不代表服务端退款或停止计费。报告按请求 ID 汇总，单独显示未知用量、预算耗尽、首答/纠错/提交/执行，不把超时中间记录重复计算为另一次请求。离线同局面报告的 `decision_policy: single_attempt_fixed_observation` 表示只评价首答，`repair_enabled_effective: false` 独立于实时配置开关。

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
