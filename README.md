# Wearable Sleep World Model

本仓库是网页端 ChatGPT / Claude 与 HPG 上 Codex 的研究交接入口：保存研究目标、可执行任务、实现、实验事实和写作依据。

当前主问题：只使用过去 30 分钟腕部 HR/ACC，持续时间建模能否改善未来 30 分钟参考 Wake 总分钟预测，同时不增加短 Wake 漏报？目前是诊断阶段，尚未证明新颖性或机制增益。

## 每次会话先读

1. [当前状态](CURRENT_STATUS.md)：已完成什么、卡在哪里、最新实验入口。
2. [研究目标](docs/PROJECT_BRIEF.md)：问题、时间边界、证据与未决事项。
3. [协作流程](docs/AI_COLLABORATION.md)：从研究方案到实现，再回到证据审阅。
4. [实验报告索引](reports/README.md)及所讨论的具体报告。
5. [研究决策](docs/DECISIONS.md)，然后读取对应 `specs/` 或 GitHub issue。

开始回答时说明读取的 branch / commit 和报告 run_id；GitHub 文件已经更新，不代表旧聊天自动获得了更新。

## 目录

| 路径 | 用途 |
|---|---|
| `experiments/g3/` | 从扩展实现导入的当前代码、测试与两份协议 |
| `archive/pilot_20261029/` | 原 pilot 代码快照，供历史追溯 |
| `specs/` | 具体研究/实现任务，明确状态与完成标准 |
| `reports/` | 可直接供网页 AI 阅读的实验事实、汇总指标与失败记录 |
| `docs/research/` | 10/29 文献与产品调研历史文档，保留其当时证据边界 |
| `docs/SOURCE_IMPORT.json` | 导入文件的来源与 SHA256；导入不代表重新实验 |
| `templates/` | 实验交接模板 |
| `.github/ISSUE_TEMPLATE/` | 网页 AI 或研究者提交任务的结构化入口 |

## HPG 实现入口

环境与外部数据位置见 [ENVIRONMENT](docs/ENVIRONMENT.md)。在计算节点的 Slurm allocation 内，通过 `scripts/run_g3.sh` 使用此仓库中的代码。例如已准备好新的工作目录后，audit 的形式为：

```bash
# 在仓库根执行。G3_WORK_ROOT 必须指向待审核的具体工作目录。
bash scripts/run_g3.sh -m sleep_g3 audit \
  --root "$G3_WORK_ROOT" \
  --protocol "$PWD/experiments/g3/expanded_protocol.json"
```

这是命令形式说明，不是要求现在重跑。现有扩展 audit 有已知时间戳异常，应先按诊断任务定位。运行新实验使用新的 artifact/run 目录，保留历史记录。

`experiments/g3/protocol.json` 仍是原 4/2/1 协议；12/7/2 扩展必须显式使用 `expanded_protocol.json`。没有运行参数扫描、自动提交 Slurm 作业或自动发布结果的后台服务。

## 数据与远端状态

原始数据、逐人预测、缓存、模型权重、环境目录及完整运行日志保存在 HPG。GitHub 交接使用代码、协议、汇总结果、图表和 artifact 位置，不把整个 Orange 目录作为 Git 内容。

2026-11-12：本地仓库已准备；目标 GitHub URL 尚未提供，尚未配置 remote 或推送。建议建立私有研究仓库。现有 `IoT_medical/paper/` 是独立的旧 AD 论文 Overleaf 仓库，不属于本次导入。

网页应用连接、Canva 和 Overleaf 的分工见 [INTEGRATIONS](docs/INTEGRATIONS.md)。
