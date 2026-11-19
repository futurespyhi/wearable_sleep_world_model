# 固定 38 夜的四阶段预测对照

| 项目 | 约定 |
| --- | --- |
| 状态 | 用户选定的下一轮设计，供 HPG Codex 实现、复审和运行。扩展结果待回传 |
| 任务分支 | `research/20261119-stage-expanded` |
| 代码起点 | `b97be6ca54c0a061377a319bf71a31952c595a46`，首轮实现和报告所在提交 |
| 既有协议 | [四阶段首轮 spec](2026-11-18_wearable_sleep_world_model.md)，[固定 38 夜采样协议](../experiments/g3/expanded_protocol.json) |
| 运行证据 | [首轮报告](../reports/20261119-first-round/report.md) 和 [audit provenance](../reports/20261119-first-round/provenance.json)，run `20261119-first-round` |

## 1. 要验证的问题

**主问题**是在相同腕部历史和相同 rollout 结构下，最近一个已完成 epoch 的腕动放进第一步转移，是否比放进初始状态更有预测价值。主比较为 `explicit − fusion` 的 **+30 min 四阶段 macro-F1**，使用相同验证原点配对。

复核首轮结果后保留此方向。两种 rollout 共享输入、历史上下文和转移骨架，各有 18,709 个参数。六夜 smoke 中，显式腕动在 +5、+15、+30 min 的 F1 均低于融合。+30 min 的 `explicit − fusion` 为 −0.0121，`explicit − direct` 为 +0.0146。显式仅命中 37 个 REM 目标中的 1 个，全时距 NLL 也高于两个对照。学得的 persistence 在三个时距的 F1 均最高。两位验证受试者和单个 seed 提供流程诊断，固定 38 夜用于下一轮比较。依据见 [首轮分数和配对差](../reports/20261119-first-round/seed-0.json) 及[模型实现](../experiments/stage_forecast/stage_forecast/models.py)。

同源 BIDSleep 研究已报告睡眠中间的 Wake 很难识别，因此报告 Wake recall 与实际支持数。SSF-SET 提供从过去 EEG 比较递归与直接预测的先例。PatientWM 在每步递归时接收外部记录动作，这里的腕动只观测到 cutoff。腕动入口的价值由同输入的 `explicit` 和 `fusion` 判定。参见 [Song et al.](https://pmc.ncbi.nlm.nih.gov/articles/PMC12931632/)、[SSF-SET](https://pubmed.ncbi.nlm.nih.gov/41662557/) 和 [PatientWM §3.4](https://arxiv.org/pdf/2610.17059v1)。

## 2. 固定数据与时序边界

- 复用 BIDSleep 1.0.1 的 `expanded_seed40_12t7v2n` acquisition receipt 和原始文件。使用 seed 40 的既有按人划分，选定 12 位训练人与 7 位验证人，每人两夜，合计 24 训练夜与 14 验证夜。7 位封存测试受试者保持封存。
- 每 epoch 30 秒，60 个历史 epoch 预测 60 个未来 epoch。原点从第 60 个 epoch 的结束边界开始，步幅 10 个 epoch。最低覆盖为 60 个历史 epoch 中至少 48 个同时有 HR 和 ACC。六组方法与三个 seed 共用按 `(participant, night, origin)` 识别的验证原点及目标有效性 mask。
- 用 `recStart` 和标签向量长度确定对齐区间 `[start, end)`，执行分箱和质量规则时使用时间戳。输入只用严格早于原点的 HR 和 ACC。`expert_label` 映射为 Wake、Light（N1/N2）、Deep（N3）、REM，unknown 和记录末端之外的目标均标为 `-1`。标准化基于训练历史。未来阶段和 HR 用于监督或评分。

## 3. 复审中的时间戳规则

原来的 [G3 聚合器](../experiments/g3/sleep_g3/data.py) 在裁切标注区间前检查整份文件顺序和冲突重复。首轮 33/38 夜通过，另外五夜的异常都已在 checksum 相符的源 CSV 中定位。以下规则固定在看扩展分数前，作为四阶段扩展审核的显式选项。

| 划分与文件 | 物理行号，1-based | 已核对的现象 | 特征处理 |
| --- | --- | --- | --- |
| Train `Bidslab36/1/motion.csv` | 54622、54623 | 回跳 0.183314 s，两端在 epoch 32（0-based） | 掩码 epoch 32 的 ACC |
| Validation `Bidslab35/1/motion.csv` | 36713、36714 | 回跳 0.162618 s，两端在 epoch 25（0-based） | 掩码 epoch 25 的 ACC |
| Train `Bidslab44/1/hr.csv` | 6681、6682 | 等时戳测量冲突，两端在标注结束后 | 审计记载，按区间过滤 |
| Validation `Bidslab68/1/hr.csv` | 5047、5048 | 等时戳测量冲突，两端在标注结束后 | 审计记载，按区间过滤 |
| Validation `Bidslab49/2/motion.csv` | 2466112、2466113 | 回跳 0.2552967 s，两端在标注结束后 | 审计记载，按区间过滤 |

1. **复查两路传感器的整份源文件。** 对 38 夜的 `hr.csv` 和 `motion.csv` 核对 acquisition checksum，再按原行序流式检查，跨读取块保留前一行。首轮每夜停在首个失败传感器，本轮收齐两路的异常及区间归属。复用向量化检查，疑似回跳或冲突用 [CSV 原值诊断](../experiments/stage_forecast/stage_forecast/timestamps.py) 确认。审计记录行号、回跳量、重复类型和影响范围，原始文件以只读方式使用。
2. **按事件时间取区间。** 取 `start <= timestamp < end` 的原行序观测用于特征计算。两端均在区间同一侧的逆序或冲突重复记入审计，区间内有效流仍须通过顺序检查。即使先读到超过 `end` 的行，也继续扫描文件。跨边界的逆序、无法定位时戳的记录与新发现的区间内逆序或冲突重复进入失败报告，待定位后再处理。
3. **对两个已核对的区间内回跳按 epoch 掩码。** 用 acquisition receipt、两个源行与 epoch 边界核对事件身份。聚合前跳过该 epoch 的全部 ACC 样本，再校验剩余区间内样本。该 epoch 的 ACC 均值、标准差、相邻差 RMS 为缺失，`acc_count=0`。在覆盖筛选和拟合 scaler 前应用掩码，并保留 HR 和 `expert_label`。原字节和顺序留在源文件。相邻差 RMS 仍按 epoch 重置，相同值同时间戳的重复沿用既有去重规则。
4. **重新验证固定名单。** 这两个坏 epoch 都早于首个可预测边界，直接影响历史 ACC 和覆盖资格。按原 5 分钟步幅，分别至多进入该训练夜 4 个、该验证夜 3 个候选历史窗口。记录实际触及和因 80% 覆盖门槛淘汰的原点。对照原先通过的 33 夜，验证阶段标签、基于时间的原点与传感器特征等价，浮点差异需说明。原缓存缺失时，可对这 33 夜用严格模式重新生成参考。用原 38 夜的 acquisition receipt、逐夜特征缓存和完整 audit 做后续训练的输入。

### 实现与验收

- 在 stage audit 中提供可选 `--timestamp-policy PATH`，将上述规则作为版本化的 `experiments/stage_forecast/expanded_timestamp_policy.json`。记录 policy 路径和 SHA256、源文件身份、每个掩码与完整 audit status。默认走现有严格审核，以便复用原 G3 入口和诊断。修复后的 stage cache 写到新 `run_id`。
- 合成测试覆盖三种关键行为。区间外的已知类型可以记录并通过。epoch 内已登记的回跳只影响对应 ACC 及覆盖统计。未登记的区间内异常或跨边界异常仍触发失败。测试跨读取块的时间顺序和冲突重复、`end` 的半开边界，以及两个传感器都进行审计。确认改动固定预测原点之后的有效传感器值或标签时，历史张量与六种方法的 60 步预测一致。
- 完成现有 G3 和 stage 测试，以及原六夜 seed 0 的回归 smoke。审核完成条件为与固定 manifest 完全匹配的 **38/38 逐夜通过**，新缓存记录所选 policy 的 SHA256，`test_accessed=false`。若仍有例外，输出文件、行号、区间关系和影响，完整保留审计结果。正式训练由这个完整审核 gate 启动。

## 4. HPG 作业顺序

从任务分支另建实现分支或 worktree，读取 [AGENTS.md](../AGENTS.md)、[CURRENT_STATUS.md](../CURRENT_STATUS.md) 和 [ENVIRONMENT.md](../docs/ENVIRONMENT.md)。用已回传的 38 夜源数据路径，独立设置新 `$sleep_run_root`。按 [现有 Slurm 脚本](../scripts/stage_forecast.sbatch) 使用从实际 `code_commit` 提取的 Git archive，使在排队的 job 读固定代码。以本文件所在的实际提交为 `spec_commit`。在 `audit` mode 把 `STAGE_TIMESTAMP_POLICY` 透传给新增的 `--timestamp-policy`，`smoke` mode 走默认严格审核。

| 步骤 | `stage_forecast.sbatch` mode | 分配与依赖 |
| --- | --- | --- |
| 1 | `smoke` | CPU 2 核、8 GiB、30 min。现有测试加上述检查与六夜回归 |
| 2 | `audit` | CPU 2 核、8 GiB、2 h。通过步骤 1 后，应用上述 policy 审核和缓存固定 38 夜 |
| 3 | `benchmark` | CPU 2 核、8 GiB、30 min。审核通过后用现有 benchmark 测一个显式 rollout 训练 epoch |
| 4 | `expanded` | CPU 2 核、8 GiB，首个作业申请 2 h。使用同一完整缓存，跑 seeds `0 1 2` 和所有方法 |

这四个 mode 已存在，policy 参数支持由本任务实现。作业脚本参数顺序如下。`$sleep_snapshot` 为实际代码提交的源码快照，`$sleep_historical_root` 为 ENVIRONMENT 中含 `work/`、`deps/` 的目录，`$sleep_spec_commit` 与 `$sleep_code_commit` 为各自的完整 SHA。

```bash
# 在 HPG 登录节点提交，测试、审核和拟合由 Slurm 计算节点执行。
export STAGE_DEVICE=cpu
export STAGE_TIMESTAMP_POLICY="$sleep_snapshot/experiments/stage_forecast/expanded_timestamp_policy.json"
mkdir -p "$sleep_run_root"
sleep_script="$sleep_snapshot/scripts/stage_forecast.sbatch"
sleep_inputs=("$sleep_snapshot" "$sleep_run_root" "$sleep_historical_root" "$sleep_spec_commit" "$sleep_code_commit")
# sleep_account_args 是当前授权的 account、QOS 和 partition 选项。
sleep_cpu_args=("${sleep_account_args[@]}" --parsable --ntasks=1 --cpus-per-task=2 --mem=8G
    "--output=$sleep_run_root/slurm-%j.log")
sleep_smoke_job=$(sbatch "${sleep_cpu_args[@]}" --time=00:30:00 "$sleep_script" smoke "${sleep_inputs[@]}")
sleep_audit_job=$(sbatch "${sleep_cpu_args[@]}" --time=02:00:00 \
    --dependency="afterok:${sleep_smoke_job%%;*}" "$sleep_script" audit "${sleep_inputs[@]}")
# 等 audit 成功并检查 audit.json、manifest 和 policy 后运行 benchmark。
sleep_benchmark_job=$(sbatch "${sleep_cpu_args[@]}" --time=00:30:00 "$sleep_script" benchmark "${sleep_inputs[@]}")
# 等 benchmark 成功并检查 timing.json。若估算符合单作业预算，提交全量训练。
sleep_expanded_job=$(sbatch "${sleep_cpu_args[@]}" --time=02:00:00 "$sleep_script" expanded "${sleep_inputs[@]}")
```

将 job ID、提交命令和退出状态写进报告。CPU 分配复用首轮可用的 `hpg-dev` 投资 QoS 或当前授权的 CPU 队列。首轮六夜训练与评分约 9 s，本轮依据实测 expanded benchmark 决定是否按 seed 拆分。拆分或重试训练可在计算节点复用现有 `stage_forecast run` 入口，显式指向同一份完整 `--cache` 和新的 `--output`，最后按 seed 汇总。结束前核对退出状态、缓存身份和实际评分产物。

## 5. 对照与判断

| 方法 | 功能与用途 |
| --- | --- |
| `stage_prior` | 训练集各 lead 阶段先验，提供无传感器参照 |
| `persistence` | 从历史 HR/ACC 估计当前阶段并将概率沿用，保留 smoke 的最强 F1 参照 |
| `direct` | HR+ACC，同历史编码后一次输出 60 步 |
| `hr_only` | 相同 rollout 骨架，腕动槽全部掩码 |
| `fusion` | 最近腕动进入初始状态，转移使用未知 motion token |
| `explicit` | 同样的腕动和过去上下文。最近腕动进入第 1 步转移，其后使用未知 token |

按现有代码固定神经模型状态 32、动作嵌入 16、batch 64、Adam `1e-3`、15 epochs、masked cross-entropy 和 `0.1` 加权的 masked HR Huber。按 `0,1,2` 分别从头训练四个神经模型，报告参数量。先验与 persistence 只在训练人上拟合一次。各训练用同一版本的数据、目标、损失和超参。

- **主指标。** 用 [现有四阶段评分](../experiments/stage_forecast/stage_forecast/metrics.py) 对每位验证人构建有效原点的归一化混淆矩阵，等权平均再算四类 macro-F1。主量为 +30 min 的 `explicit − fusion`，逐 seed 计算配对差再汇总均值与范围。+5/+15/+30 分别取数组索引 `9/29/59`。每个 lead 给支持的类别、可评估人数、有效与 unknown 原点数、混淆矩阵及各类 F1。某类无参考支持时，对应四类宏分和配对差标为不可估计。
- **次要比较。** 同时报告 `explicit − direct`、`fusion − hr_only` 和 `fusion − direct`，以及与 `persistence` 的差距。第一对用于和直接预测比整体表现，第二对衡量加入完整腕动输入的价值，包括幅值、样本计数和 mask，第三对比较两种完整方法。直接预测的 readout 与参数量也有差异，报告这一点。可向现有 `score_seed(..., contrasts=...)` 增加两个配对臂，沿用原评分实现。
- **预测质量与覆盖。** 每个 lead 给出 Wake recall 和 Wake 标签数，另给各 lead 与全 60 步的 multiclass NLL、Brier。Wake 总分钟 MAE、独立短 Wake 事件召回、HR MAE 为辅助。保留 participant-level 汇总，三个 seed 共享同一组人，重叠窗口和 seed 波动按描述性证据理解。用已评分预测在排除历史触到掩码的验证原点后复算主配对差，附可用支持，检查结果是否由这几个窗口驱动。
- **下一轮取舍。** 优先继续显式腕动入口需要三个 seed 的 +30 min `explicit − fusion` 均为正、平均全时距 NLL 至少持平，且可评估的 +30 min Wake recall 至少持平。若两组 Wake recall 都为零，明确保留 Wake 识别困难。若 `fusion − hr_only` 有稳定收益而主配对差缺乏一致收益，优先保留融合方法。若 persistence 的 F1 仍较高，把 rollout 结论限定到实际优于的对照与时距。以上为验证集上的研究取舍标准。

## 6. 回传

将 `reports/<run_id>/report.md`、聚合指标、配对差及审核摘要推到实现分支，按 [报告模板](../templates/EXPERIMENT_REPORT.md) 记录基线、spec/code/协议/policy/cache SHA、固定数据名单、受影响 epoch 和共同原点计数、job ID、环境与耗时。更新 [CURRENT_STATUS.md](../CURRENT_STATUS.md) 和 [报告索引](../reports/README.md)。原始数据、逐人预测、模型权重与完整日志留在 HPG。如果完整审核或评分被阻塞，回传已经完成的阶段、阻塞的具体证据与 artifact 路径。
