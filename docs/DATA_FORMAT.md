# V3 实验记录与数据接口

## 版本和身份

app_version=3.1.0，schema_version=4，基准benchmark_version=day_benchmark_v1。
stream_versions：observation=3、action=1、event=2、checkpoint=2、model=3、result=1。
读取器仍接受旧版1—3清单；旧记录未提供的新字段保持未知，不补猜。跨代码版本回放仍受版本指纹校验约束。
应用版本、规则配置和数据协议独立。路径为experiments/关卡{level_id}/方案{scheme_id}/时间_控制者_seed种子_短编号。
manifest.run_identity是真实身份，完整episode_id与配置、出怪表另存；自定义卡组使用摘要编号，不冒充A/B/C。

## 文件

|文件|内容|
|---|---|
|manifest.json|身份、配置、种子、出怪表、版本／素材／依赖指纹、执行模式|
|result.json|终局、时长、flags、finalized、正式比较资格|
|submissions.jsonl|所有提交与回执，含拒绝和重复|
|decisions.jsonl|提交前公开输入及动作标签，标签不送模型|
|actions.jsonl|实际执行结果、原因与植物ID|
|events.jsonl|资源、实体、伤害、消耗、唤醒、地形、终局|
|observations.jsonl|每100ms及终局公开观察|
|checkpoints.jsonl|初始、每秒、暂停／终局及关闭校验状态|
|raw_input.jsonl、wait_samples.jsonl|原始输入及独立等待样本|
|model_config.jsonl|控制器参数、提示词与风格快照|
|model_requests.jsonl|真正发出的payload、输入诊断、追加尝试关系|
|model_results.jsonl|回复、解析、错误阶段、usage、耗时、结束原因和脱敏服务详情|
|model_submissions.jsonl、model_memory.jsonl|云端提交回执及策略意图|
|model_state.jsonl|暂停、恢复、旧回复丢弃、输入超限|
|decision_timing.jsonl、timing.jsonl、errors.jsonl|推进量、现实滞后、技术异常|

未发生行为的流可以不存在。普通流event_seq是当时最近的游戏事件序号，events.seq才是各事件自身序号。模拟日志带tick与sim_ms。

## 动作和观察

动作保持PLACE_PLANT(plant_type,row,col)、REMOVE_PLANT(plant_id)、WAIT。行列从0开始。
咖啡使用PLACE_PLANT投放到休眠蘑菇格；队列绑定源观察中的目标ID。目标更换返回TARGET_CHANGED，不休眠NOT_SLEEPING，正在唤醒ALREADY_WAKING，弹坑BLOCKED_TERRAIN；失败不扣费。
grid仅放主植物ID；plants增加sleeping/waking，地雷有armed；overlays放咖啡及target_id；terrain为grass/crater矩阵。不能铲咖啡覆盖物或弹坑。
可见敌人增加shield/jumping/jumped/paper_broken，不提供精确血量、防具数值、攻击倒计时或未来波次。
观察新增total_waves（总波数）、time_limit_ms（时限）、remaining_time_ms（剩余时间，最低0），均由本局配置和模拟时间计算，不含未来出怪安排。
text_board_v2最后一帧为CURRENT，显示当前／总波数、时限和剩余时间；棋盘标注睡／唤醒中／醒、退缩、地雷准备／就绪。旧记录缺字段显示问号，不推断睡眠状态。历史仍为摘要；必要时删减旧帧和旧事实，删减量在diagnostics中。本地公开日志保留原始信息。内部events/checkpoints不能直接送模型。

## 事件与归属

plant_awakened记录蘑菇和咖啡ID，plant_loss区分consumed/eaten/shovel/target_lost，terrain_changed记录弹坑出现或消失。
bullet_transformed记录旧新弹丸、发射植物及火炬；damage附owner_id、modifier_ids、base_damage和projectile_damage。
报告按实际生命和防具减少量排除过量伤害，火炬增伤按弹丸伤害比例单列；这是归属口径，不是反事实因果估计。支出与部署分前75秒／75秒起展示，唤醒、损失、击杀与布局单列。

## 云端与回放

diagnostics含字节、估算输入Token、估算方法、实体数、历史帧数、裁剪数、输出上限和上下文配置。
服务usage是真实返回用量，缺失表示未知，预算另做保守预留。截断不同于JSON格式错误；HTTP详情脱敏。repair_of关联唯一追加尝试，包含网络重试。
同一请求可能先写超时通知再写最终结果，统计按request_id合并。ABANDONED_AT_END不代表取消计费。
pause_think/realtime/offline分别记录，技术暂停与人工恢复标记到flags。

environment_id为环境条件，condition_id包括植物方案；同方案比较使用完整条件，跨方案保持环境和控制器一致，均检查版本、时间模式与干预。
回放使用保存的实际配置、出怪表、提交时刻及全部动作，从开局推进且不调用模型。verified要求版本、状态及提交覆盖一致；state_match只表示状态一致。非有限生命值用hp:null与invulnerable:true。
旧清单可读取，但跨版本不保证规则重放；--migration-check不能冒充同版本verified。
