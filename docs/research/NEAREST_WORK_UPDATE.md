# G3 近邻补充核查：已有覆盖与可保留的问题

- 核查日期：2026-10-29，America/New_York；用于当日下午三位教授的研究进度讨论。
- 对照材料：原研究综合计划与 `2026-10-29_evidence_01_sleep_world_model_research_gaps.md`。本补充不修改原证据表。
- 范围：Waqar & Ghani Khan 2024、SSF-SET、Gao duration-aware sleep world model；公开原文、作者稿及代码可访问性。本轮未训练、未访问受限数据、未取得可运行的作者代码。
- 结论边界：这是窄范围近邻核查，不是全领域系统综述，也不能证明尚无人研究等价任务。

## 1. 对 G3 的直接判断

**未来睡眠阶段预测、腕部历史建模、自由 rollout、持续时间约束，以及同一输出的无/软/硬后处理比较，都已有相关先例。**

当前应保留为待验证问题的是：在相同受试者划分、相同预测起点、仅过去 30 分钟腕部 HR/ACC 的信息条件下，持续时间先验能否改善未来 30 分钟参考 Wake 总分钟预测，以及这种改善是否伴随短 Wake 事件漏报增加。

30 分钟不是单独的新颖性依据。主要价值需要来自同信息的结局增益和事件误差分析；当前数据覆盖扩展与简单基线诊断仍应优先。

## 2. Waqar & Ghani Khan，2024

来源：[Sleep stage prediction using multimodal body network and circadian rhythm，PMC 正文](https://pmc.ncbi.nlm.nih.gov/articles/PMC11057653/)，PeerJ Computer Science，2024-04-22，DOI [10.7717/peerj-cs.1988](https://doi.org/10.7717/peerj-cs.1988)。

| 核查点 | 正文证据与边界 |
|---|---|
| 输入与阶段来源 | *Sequence generation*、*Memory efficient models* 和 *Visualization* 使用历史窗口，完整序列含 `circadian, cosine, steps, hr, time, stage`。推理历史 stage 究竟来自参考标签还是模型预测，正文未明确。 |
| 时间线与 rollout | LSTM 描述为下一步预测，检查 1–39 个历史采样步；Fig.10 展示预测睡眠模式。本轮没有确认它从单一 cutoff 自由生成完整未来窗口。 |
| Past-only 预处理 | *Feature preparation* 包含睡眠时段均值归一化及 Gaussian 滤波。其在线边界需要实现检查，不能直接认定满足严格历史前缀协议。 |
| 结局与事件 | *Results* 主要报告阶段分类指标及 RMSE；未确认未来固定窗口 Wake 总分钟误差或按短事件匹配的漏报评价。 |

**判断：** 已是腕部历史与 sleep-pattern prediction 的直接近邻；stage 可用性和自由 rollout 仍未核实。不能直接当作纯 HR/ACC 等价任务，也不能由上述不明确处指控标签泄漏。

**代码访问记录：** *Data Availability / Supplemental Information 1* 列出 [38.4 KB ZIP 补充代码](https://pmc.ncbi.nlm.nih.gov/articles/instance/11057653/bin/peerj-cs-10-1988-s001.zip)，[补充材料 DOI](https://doi.org/10.7717/peerj-cs.1988/supp-1)。本轮 PMC 返回下载验证 HTML，未取得有效 ZIP；PeerJ 返回 HTTP 403。没有执行代码，因此 stage 输入与 rollout 的代码级核查仍待完成。

## 3. SSF-SET：阅读深度已超过原证据表的摘要级别

来源：[PubMed PMID 41662557](https://pubmed.ncbi.nlm.nih.gov/41662557/)，DOI [10.1109/JBHI.2026.3662787](https://doi.org/10.1109/JBHI.2026.3662787)；[Korea University 官方记录](https://pure.korea.ac.kr/en/publications/ssf-set-a-discrete-eeg-token-based-framework-for-sleep-stage-fore/) 标记 2026-08-01 正式发表。方法核查使用 [公开可读的作者稿正文](https://www.researchgate.net/publication/400606202_SSF-SET_A_Discrete_EEG_Token-Based_Framework_for_Sleep_Stage_Forecasting)。

| 核查点 | 作者稿定位与证据 |
|---|---|
| 输入与自由生成 | §III-A、§III-D、Fig.1：过去 EEG 编码为 token；训练采用 teacher forcing，推理自回归生成未来阶段，不读取相应未来 EEG。 |
| Stage 基线 | §IV-C / Fig.3：SSF-PSS 使用预测阶段；推理时使用自身先前输出。不能说它在测试时靠真实未来 PSG 阶段滚动。 |
| History 与 horizon | §IV-B：序列长度 25 epochs，SSF context length 为 125 tokens，不能把两者混称为统一 history。§V-D / Fig.5 明确 horizon 为 25–100 epochs，即 12.5–50 分钟。 |
| 结局与事件 | §IV-A、§V-C / Table IV：阶段 ACC、κ、macro-F1、各类 F1；本轮未发现 Wake 总分钟误差或短 Wake 事件匹配评价。 |

**判断：** 过去信息驱动的未来阶段生成、直接预测比较及覆盖 30 分钟附近的 horizon 均已有先例。G3 的候选区别应落实到腕部信息条件、未来清醒总时长和短事件误报/漏报的联合评价。

**版本与复现限制：** 可读正文自述为尚未最终编辑的作者稿，页眉保留占位年份；正式发表信息以上述 PubMed 和大学记录为准。本轮未逐页核对最终出版社版本；DOI 入口未能直开，PDF 链接返回 403，但作者稿正文可读。未定位公开作者代码。原证据表对 SSF-SET 的 A 级摘要阅读说明属于先前状态，本补充仅将已核方法和结果提升为作者稿正文证据，不表示完成代码审计。

## 4. Gao：同输出 raw/soft/hard 比较已有先例

来源：[Duration-Aware World Models for Sleep Staging with Dwell-Time Constraints，arXiv:2610.33033v1 正文](https://arxiv.org/html/2610.33033v1)；[版本记录](https://arxiv.org/abs/2610.33033v1) 为 2026-10-14。它是预印本，不能写成已完成同行评审。

| 核查点 | 正文定位与证据 |
|---|---|
| 潜在阶段与真实标签 | §3.3 中 `s_t` 由模型 continue/switch 更新；§3.4–3.5 的 dwell/transition prior 由训练标签拟合。不能把 `s_t` 记号直接解释为推理时输入真实 PSG stage。 |
| 已有约束对照 | §3.6、§4.6 / Table 5 已比较基础输出的 raw argmax、HSMM Viterbi、hard run merging；无/软/硬比较本身不是 G3 新意。 |
| Horizon 的区别 | §4.5 的 dreaming 无新观测，汇总 20 人 × 80 epochs 的 dwell 分布。`Dmax=60 epochs=30 min` 是 dwell 统计截断，不是 30 分钟 forecasting horizon；80 epochs 相当于 40 分钟。 |
| 结局与短片段 | §4.6 评价 staging accuracy 与低于应用最小时长的 run 比例；Fig.4 承认专家标签本身有两个低于阈值的片段。本轮未见逐夜条件未来 Wake 总分钟或短 Wake 真事件召回。 |

**判断：** 应承认 duration-aware world model 和同输出后处理对照先例。其应用最小时长不能自动视为参考睡眠标签必须满足的生理规律；去掉低于阈值的 run 与保留真实短 Wake 事件是不同评价问题。

**实现限制：** Algorithm 1 给出初始潜在状态，但本轮未核得与 G3 相同的 30 分钟历史初始化和逐夜未来评分协议。§4.6 与 Fig.4 对基础模型的命名分别为 discriminative baseline 与 RSSM，需代码厘清；本轮仅确认文中比较设计。原文仍称代码与权重将发布，未定位可审计实现。

## 5. 会议中可用的表述

> We ask whether duration priors improve next-30-minute Wake-burden prediction from the same past wrist information, and whether any gain comes at the cost of missing short reference Wake events.

这句话是研究问题，不是已实现的贡献。外推前至少需要：

1. 固定 history、cutoff、窗口、参与者划分及可用输入；所有变体都不得获得真实当前或未来参考 stage。
2. 同一预测器的无/软/硬约束之外，保留直接结局预测和强简单基线，并检查一般概率收缩是否解释主要增益。
3. 预先确定短事件长度、匹配、预测阈值、边界截断及未知标签处理；同时报告误报、漏报与独立事件数量。
4. 分别解释总分钟误差、概率校准和事件命中；总分钟变准不能独自证明保留事件，轨迹平滑也不能独自证明生理有效。

目前不能使用“首次 future-stage forecasting”“首次腕部历史建模”“首次自由 rollout”“首次无/软/硬持续时间比较”或“尚无人做过等价任务”等表述。

## 6. 对现有会议材料的只读核查

已读 `MEETING_BRIEF.md` 与 `MEETING_SPEAKER_NOTES.md`。在本轮核查的三篇范围内，没有发现改变会议主结论的文献夸大；材料已明确新颖性未证明，并保留了 Waqar 的不确定性。

- `MEETING_BRIEF.md` Slide 2 的 `Future EEG-stage forecasting` 建议改成 `Future sleep-stage forecasting from past EEG`，避免被理解为预测 EEG 波形。
- `MEETING_SPEAKER_NOTES.md` Slide 2 已准确写出 SSF-SET 的 12.5–50 分钟与 Gao 的同输出后处理先例；建议引用本补充及作者稿，说明并非仅从旧证据表的摘要读取得出。
- 既有证据表仍把 SSF-SET horizon 标为待全文确认；不要把旧表与新讲稿的阅读深度差异误认为事实矛盾。本补充记录了新增阅读范围。
- 本次只读审阅没有重新审核 NormWear-2、Samsung、Eight Sleep 或本地实验数值，不能将上述判断扩大为对全部材料的独立复核。
