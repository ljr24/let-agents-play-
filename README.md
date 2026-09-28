# pypvz 白天实验室 V3

《植物大战僵尸》人机策略实验环境：十档僵尸难度 × 三套8卡方案，共30种关卡条件，提供统一操作、云端决策、完整记录与回放。

## 启动

Windows首次下载：安装Python 3.12（包含Python Launcher），解压整个仓库，双击 setup_day_lab.cmd 创建独立环境，再双击 start_day_lab.cmd。
本机已有安装目录为 E:\AI_game_test，继续使用其中的 .venv。

入口选择关卡01—10、方案A/B/C、真人／规则AI／云端AI和种子。全部直接开放，八张卡同时显示，数字键1—8选卡。

## 文档

- [使用、关卡与云端设置](README_DAY_LAB.md)
- [架构和开发接口](docs/DEVELOPMENT.md)
- [记录结构和比较口径](docs/DATA_FORMAT.md)
- [上游来源与作者声明](docs/UPSTREAM.md)

## 云端与数据

DeepSeek示例是 cloud.deepseek.example.json，使用思考暂停、回复后推进1秒。密钥从本机 PVZ_API_KEY 环境变量读取。
prompts/cloud_framework.md 是提示词框架，prompts/play_style.json 是可编辑风格；新局加载快照。
每次决策最多两次请求，连续三次失败后暂停，可重试或结束保存。输入、实际Token、回复错误和动作执行分别记录。

正常记录保存为 experiments/关卡xx/方案xx/时间_控制者_seed种子_短编号。入口支持筛选、比较和回放。

game/ 负责战斗，daylab/ 负责实验和控制，configs/ 负责条件，prompts/ 负责提示词，resources/ 保留完整原素材。原版主游戏入口已经退役。
