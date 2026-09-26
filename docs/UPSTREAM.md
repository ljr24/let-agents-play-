# 来源、使用限制与保留内容

本页保留原项目的来源和使用限制，不是原版游戏的操作手册。当前实验版的操作见 [使用说明](../README_DAY_LAB.md)，代码结构见 [开发与交接](DEVELOPMENT.md)。

## 上游来源

- 直接上游：[wszqkzqk/pypvz](https://github.com/wszqkzqk/pypvz)。本地基础提交为 `c88a018209ca48457e24db124f6532aea350f60d`，并不代表上游当前最新版。
- 上游 README 声明基于 [marblexu/PythonPlantsVsZombies](https://github.com/marblexu/PythonPlantsVsZombies)，部分代码整合自 [callmebg/PythonPlantsVsZombies](https://github.com/callmebg/PythonPlantsVsZombies)。

## 原 README 的使用声明（原文）

> 本项目为个人python语言学习的练习项目，仅供个人学习和研究使用，不得用于其他用途。如果这个游戏侵犯了版权，请联系我删除

上述声明来自原作者，其中的“我”指原作者。本地整理没有重新授权上游代码或素材，也没有声称素材属于本项目原创。

## 当前代码与素材的关系

`game/entities` 保留原植物、僵尸、子弹和场地对象，按职责分类；`game/combat.py` 取自原 `source/state/level.py` 的战斗相关方法。普通通关、原选卡菜单、进度读写和旧打包流程已退出当前实验应用。旧文件与现模块的对应关系见 [开发文档的迁移说明](DEVELOPMENT.md#11-原项目到当前结构的对应关系)。

实验自己的自动产阳、固定时钟、射手初始时钟修正、事件跟踪和动作入口，分别在 `game/content.py`、`daylab` 与 `game/tracking.py` 中明确保留。素材目录 `resources` 完整保留，包含尚未启用内容，不代表所有内容都通过了实验验证。

原实体仍有一些带夜晚、水面或特殊机制的条件分支：它们作为原设计保留，不能通过实验配置任意启用未经验证的内容。这与删除无关应用流程并不冲突。

## 不再作为当前说明保留的内容

原 README 中的 `pypvz.py` 启动命令、普通通关存档、旧版打包指令、夜晚与泳池等功能列表、历史开发计划和旧问题列表不适用于当前实验版，未并入操作或开发说明。旧问题列表也不能当作当前版本的已验证缺陷清单。

原 README 文档副本已移到回收站；本文提取并保留了来源与使用声明。如需核查完整原文，可查阅本地 Git 基础提交中的 `README.md`，或在回收站尚未清空时恢复副本。
