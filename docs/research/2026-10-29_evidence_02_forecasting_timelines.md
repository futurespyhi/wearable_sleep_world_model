# 证据表二：睡眠 prediction 的输入截止与目标时间线

- 资料截止：2026-10-29，America/New_York；用于当日 14:00 EDT 组会。
- 范围：四项指定工作的原文、可取得补充材料及必要公开代码，只读核查。
- 本文记录已确认事实、依据材料作出的解释，以及仍未解决的问题；没有复跑论文结果。
- 统一记号：`t` 为出结果时点，`s` 为目标夜入睡时刻，`u` 为该夜结束，`W` 为一周。
- “当时已知”同时要求观测已经发生、处理结果已经可用；时间戳早于 `t` 不自动保证处理过程在线。

四项工作的任务不同：Sakal 是入睡前的整夜结局预测，Roberts causal 是当前 epoch 识别，Apple 是周级状态估计，Corda 提出下一夜自报质量预测但日特征截止仍不完整。
这些区别决定比较对象，也决定何种新增实验能够回答一个尚未解决的小问题。

## 1. 固定七列证据表

| 工作/版本 | history 与 input cutoff | 决策时点/触发 | 目标窗口/horizon/标签 | 预处理与切分 | 任务归类 | 来源定位/未决项 |
|---|---|---|---|---|---|---|
| **Sakal et al., SLEEP 2025**；48(8), zsaf113；DOI 10.1093/sleep/zsaf113 | 目标入睡前 5 天 accelerometry，排除 cutoff 至入睡之间的 4/8 h；CNN-LSTM 用 5 秒平均加速度；CatBoost 用此前 4 夜睡眠、此前活动及当天醒后至 cutoff 的统计量 | `t=s-4h` 或 `s-8h`；离线用目标夜实际入睡时刻定位；未给部署时无需已知 `s` 的触发器 | 每人最后一夜为唯一 target night；预测 HMM-derived `SE<0.85`；4/8 h 是距入睡的提前量，整夜标签在 `u` 后才完整 | UKB 校准、non-wear 处理/插补；至少 5 天活动及此前 4 个有效夜；80,811 人；10 次重复 10-fold CV；公开代码按 eid 分折；特征选择与调参的外层隔离见下文 | 真正面向尚未发生目标夜的预测；事件相对起点、设备算法标签；无干预效果证明 | [S1] Methods: Study design / Data preprocessing / Model evaluation，Fig. 1/3；[S2] Fig. S1/S8；[S3]、[S4]、[S5] 公开脚本。输入截断构造、插补实时性与在线触发尚未完整复现 |
| **Roberts et al., Sleep Health 2023 causal 版本**；9(5):596–610；PMC11005467 | ActiWatch activity counts，30 秒 epoch；送入约 24 h 记录，causal TCN 每一输出仅依赖当前及过去 epoch；实际有效 history 由 kernel/dilation 决定 | 每个当前 epoch 观测完成后可推断其状态；无需预知卧床区间；没有正提前量的触发任务 | 当前 `y_t∈{sleep,wake}`；PSG 分期合并为二分类，部分 PSG 外时段用直接观察的 wake；`h=0` | 按人、按研究分层 5-fold：训练/调参/测试隔离；训练折最大 count 缩放；缺失填 0 并遮蔽 loss；记录级对齐/脱腕判定含离线步骤；MESA 仅补充外测 | 模型层面 causal 的当前状态识别；论文评价管线不能直接等同完整在线系统 | [R1] §§3b–3d、§4b；[R2] README；[R3] `padding='causal'`；[R4]、[R5] 对齐/脱腕。补充 DOCX 本轮未成功解析，不能借主模型感受野当 causal 数值 |
| **Erturk et al., Beyond Sensor Data**；arXiv:2507.00191v1，2025-06-30；仅 weekly sleep tasks | 每周 168 小时、27 个 HealthKit 派生量及 missingness mask；包含夜间行为/生理数据；一周汇成 embedding，未把睡眠阶段标签作为预训练输入 | 论文采用周样本，没有入睡前在线报警触发；完整周 embedding 要等该周数据齐备 | 周平均 total/deep/REM sleep duration、sleep efficiency；Apple Watch accelerometer 算法派生；35.2K 人、671.6K participant-weeks；每周至少 5 夜 | 周一起始；训练观测 z-score、异常值裁剪、缺失用训练全局均值及 mask；预训练按人 80/10/10；下游合并 val/test 为 80/20，内部 CV 选 ridge penalty | 同周睡眠指标估计/动态健康状态检测，非已验证的 next-week forecast；该归类由周构造和正文解释共同支持 | [A1] §4.1/5.1/5.2/6；[A2] A.1.3、A.2.1、A.6.1，PDF pp.13/21。跨午夜睡眠归周细则及逐样本 join 代码未知；作者未发布代码/权重 |
| **Corda, Massa, Riboni, Future Internet 2024**；16(2):46；DOI 10.3390/fi16020046 | 手机 activity/audio/lock/light/conversation/GPS；一天切成 12 个 2 h 槽，加入前夜时长、分时段路程；夜间路程为 20:00–07:00 | 按日生成下一夜质量预测/建议；未明确每日推断时刻；示例含 22:00–24:00 特征，跨夜窗口所属日不清 | 宣称下一夜主观睡眠质量；EMA 1–4 级回归再取整；§3.4 与 §4.2 的量表好坏方向相反，编码待核 | 清洗/异常检测、插补、低通、light/sound 归一化；StudentLife 48 人、10 周；leave-one-person-out；未给插值方向及统计量拟合边界 | 作者定义为 next-night forecasting + LLM 建议；严格 pre-bed 可用性尚不能从公开定义完全确认 | [C1] §§3.1–3.4 pp.5–7，§3.7 p.10，§4.2 p.12；检查到整日/跨夜特征，未取得公开 feature-label 配对实现；10 人可用性研究不能证明睡眠改善 |

## 2. Sakal：预测整夜效率，起点相对实际入睡

```text
s-5d        此前4夜及活动        t=s-8h 或 s-4h       s             u
|------------已保留输入-------------|  不作预测输入    |--目标夜-----|
                              输出低SE风险                    HMM整夜SE标签
```

**已确认。** [S1] 将每人最后一个有 accelerometer 睡眠估计的夜晚定义为 target night。
因此分析单位是一个人对应一个目标夜，不能把 80,811 人解释为连续多夜逐日预测评估。
模型读到此前的 4 夜睡眠指标是合法历史输入；原文明确当天活动只累计到 forecasting time。
4/8 h 衡量 cutoff 到入睡的间隔，不是 cutoff 到完整 SE 结局可得的间隔。

**当时已知。** 原始历史活动、已经结束夜晚的睡眠估计，以及醒来到 `t` 的活动理论上可用。
这个陈述仍以历史睡眠算法、non-wear 处理和数据上传在 `t` 前完成为条件。
**未来才知道。** 目标夜真实 `s`、结束 `u` 和完整 SE；部署者不能事先直接调用真实 `s`。
离线围绕 `s` 构造起点是已知协议选择，不能仅凭该选择断言目标夜信号被喂给了预测器。

**预处理与选择边界。** UKB 先处理校准和 non-wear，论文随后构造睡眠/活动特征。[S1]
原文明确预测输入排除了最后 4/8 h；论文中的 pre-bed 活动关联分析另有完整 4/8 h 暴露窗口。
后一组关联分析不能被混写为 forecasting 模型的额外输入，也不能证明改变运动量会改善睡眠。
补充 Fig. S1 确认为 CNN blocks → LSTM → MLP；Fig. S8 是全候选特征选择结果。[S2]

**代码进一步确认的内容。** [S3] 读取 `df-final-8hrs.csv` 全表拟合初始模型并计算 SHAP 排序。
[S4] 在固定 feature list 上用 10-fold 平均 AUC 调参；[S5] 读取固定参数/特征和 eid 列表评估 100 折。
这些脚本没有展示每个最终外层测试折重新筛选特征/调参的嵌套流程；不能将其描述为已确认的 nested CV。
这与“目标夜观测是否进入特征”是不同的问题；本轮没有运行结果来量化选择过程对 AUC 的影响。

**仍未知。** 已查正文、补充、官方目录与三个 CatBoost 脚本，但目录中未见原始加速度到 cutoff 输入的完整构造代码。
因此不能完整证明插补/历史 HMM 参数计算的时间局部性，也未核实 CNN 输入缩放的全部细节。
尚无原文支持一个无需真实入睡时刻、按固定钟点执行的等价线上成绩。
可保留结论：它已建立强的 pre-sleep forecasting 先例；固定时钟触发的影响仍是可测问题。

## 3. Roberts causal：当前状态输出与离线准备流程分开

```text
历史 counts ................ 当前30秒epoch结束 t ............未来 epochs
|---------------- causal TCN 可见 -------------|               不可见
                                              -> y_t (当前sleep/wake)
```

**已确认。** 正文 §3d 的 Model Structure 明确区分 symmetric 主模型与 supplemental causal 版本。[R1]
官方 `Train_Activity_Count_Classifier.py` 设置 `padding='causal'`、`return_sequences=True`，逐 epoch sigmoid 输出。[R3]
它与同索引的 sleep/wake 标签计算 loss，没有将标签平移到 `t+h`。
因此 causal 指输入方向，不能把这里的 `h=0` 分类称为未来睡眠预测。

**history 的准确含义。** 约 24 h 是记录/评价覆盖范围，不代表每一输出均能读取完整 24 h 历史。
正文报告的 757 epoch 感受野及前后各约 3 h 9 min 属于 symmetric 主模型；不移植给 causal 行。
本轮代码确认 causal 候选 kernel/dilation，但未逐个读取冻结模型配置来断定每折有效 history 长度。

**当时已知。** 当前已结束 epoch 与其历史 count、固定训练参数、训练折得到的缩放系数。
**未来或参考端才可知。** 后续 counts、参考 PSG 序列及利用整段记录修正的时钟误差。
[R3] 按训练折非缺失最大 activity count 缩放，不是逐测试夜利用整夜最大值归一化。
模型输入 mask 用于不计缺失点 loss；这不等于部署时必须知道当前 PSG 标签。

**实际离线步骤。** [R4]、[R5] 用 PSG sleep/wake 片段寻找 actigraphy 的整段对齐 lag。
代码还将至少 120 min 连续零活动区间识别为 off-wrist，然后将整段标记并遮蔽。
前者是参考对齐程序，后者的区间起点可能要观察到后续零活动才能最终确认。
这说明论文准备好的输入/掩码不全是实时原样可用；没有证据表明 causal 卷积本身读了未来 epoch。
若研究在线系统，需用已知设备同步、实时缺失判定或明确延迟，单独评估该差异。

**切分。** 四项研究按参与者分层进入 5 折，每折单独调参并保留测试参与者；同人记录不跨当折训练/测试。[R1]
MESA 用于补充外测，不参与训练和调参；这一外测评价的是识别泛化。
**仍未知。** PMC 的补充 DOCX 链接返回下载中间页，正文和官方 README/训练/预处理代码已读。
本轮未运行固定前缀重放测试，也未读取全部模型配置；不声称完整端到端在线复现。

## 4. Apple weekly sleep：周数据与周结局的配对证据

```text
W周一00:00                W内日间与夜间                     W结束
|-------------------- 168小时行为/生理输入 -------------------|
|-------------------- 至少5夜睡眠汇总标签 --------------------|
                                                          周embedding -> 周指标
```

**时间构造已查到的事实。** A.1.3 将输入周对齐至周一午夜；A.2.1 用 `T` 表示该周所有观测。[A2]
A.6.1 “Sleep metrics” 以 participant-week 构造睡眠标签，并要求该周同时有足够 HealthKit 与至少一段 PPG。
§5.1 使用 per-week 读出；§5.2 将睡眠表现解释为整周、包括夜间的静止和心率等信息具有辨识力。[A1]
§6 又明确说明 WBM 没有被设计为根据个人历史预测未来健康状态。
因此本表将 weekly sleep 归为同周状态估计；该判断结合了正面的窗口/配对证据，不只依赖未出现 next-week 字样。

**结论的边界。** 公开文本未展示每条睡眠事件跨午夜时归到哪一周，也没有逐行 label join 代码。
这使细粒度时间对齐仍待确认，但没有把整个 weekly sleep 任务解释成下一周预测的依据。
此结论只对应表中的 sleep 下游任务；不把论文全部疾病、感染或伤病标签一概归为同一时间关系。

**当时已知。** 若决策放在 `W` 结束，完整 `W` 输入已发生，输出用于总结/检测该周状态。
**未来才知道。** 若决策放在 `W` 开始，则该周夜间行为和结局均未发生，原任务不能直接提供这项预测能力。
预训练没有使用 sleep 标签，不意味着它的 HealthKit 输入排除了目标睡眠发生期间的观测。

**切分与处理。** 预训练和下游按参与者隔离；下游把原验证/测试参与者合成 20% 评价集合，ridge penalty 在训练侧内部 CV 选择。[A1]
训练集观测决定 z-score，缺失用全局平均值并保留 mask；这不是跨周外推的时间留出方案。[A2]
作者说明因知情同意约束不公开模型权重和代码，本轮不能补做样本级构造验证。[A1] §4.3
可保留结论：行为表征对周级睡眠指标有信息；转为未来周预测需重新定义输入/标签和基线。

## 5. Corda：下一夜意图明确，逐日可用性尚未闭合

```text
前夜睡眠       日d手机观测，含2小时槽及22:00–24:00      宣称的下一夜      EMA
    |------------------ daily feature vector ----------------?|---------|
夜间路程另含20:00–07:00：其归属日和与target night的相对关系未说明
```

**已确认。** 原文 §3、§4.2 都将目标描述为 next/following night 的质量。[C1]
标签来自 EMA 的感知质量，手机活动/音频/锁屏/光照/对话/GPS 提供上下文。
虽然数据集介绍泛称 smartphone/wearable，本文实际特征接口不能当作独立腕部 PSG 分期输入。
48 人、10 周数据使用 leave-one-person-out：每次整个人留作测试，其余人训练。

**当时已知。** 已完成时段的手机事件、已结束且已填写的前夜时长和质量。
**未来才知道。** 当前尚未结束时段总量、目标夜结束后的质量自报，以及跨到次日的路程总量。
§3.3 的 12×2 h 槽和 20:00–07:00 路程加上 Fig. 2 的 22:00–24:00 示例，使截止时点不能省略。
如果这些都属于已经结束的前一日，则可形成未来预测；如果包含被预测夜，则任务会发生改变。
原文没有给足日偏移、每日触发钟点和 EMA 关联规则，本轮不能在两种解释间强作断定。

**可定位的不一致。** §3.4 p.6 写 level 1=very good、4=very bad；§4.2 p.12 写 1=very bad、4=very good。
这是原文内部量表方向冲突；在取得标签映射实现之前，只能确认四级主观质量，不能确认高分好坏方向。
§3.2 说明插补和低通，却没有规定仅向过去插补、滤波时延及归一化统计量的拟合范围。
LOPO 解决参与者重叠，不能单独解决每天特征是否含 cutoff 后信息。

**建议与效果。** LLM 根据树的 decision path 生成解释/建议；预测相关性不等于建议导致改善。
10 人用户研究测信任和理解等主观可用性，作者也要求更长研究才能量化睡眠改善。[C1] §§4.3/5
**仍未知。** 已查出版社 PDF 方法、示例、实验和数据说明；其引用公开 StudentLife，未给可核验的配对实现链接。
数据站本轮访问超时；没有下载原始人类数据，因此不声称核实实际 EMA 日期映射。

## 6. 不能直接比较的内容

1. **Sakal vs Roberts causal：** 一个预测数小时后的整夜设备 SE，另一个识别当前 30 秒 PSG sleep/wake；AUC/accuracy 的标签、单位、起点均不同。
2. **Sakal vs Apple weekly sleep：** 每人一个未来目标夜与同周多夜汇总不同；周级 `R²` 不能与低 SE 分类 AUC 排名，周中夜间观测也不是 pre-sleep 可用信息。
3. **Sakal vs Corda：** HMM 效率和主观满意程度测量不同结局，人群与传感器不同；两个任务都叫 sleep quality 不构成共享 benchmark。
4. **Roberts 主模型 vs causal：** symmetric 输入包含未来上下文；若比较在线任务，须统一可见数据和实际预处理延迟，不能把主文最好数字直接移作 causal baseline。

## 7. 由文献产生的可测量小 gap

**优先候选：实际可知的决策时点如何改变下一夜风险预测。** Sakal 已覆盖 pre-sleep forecasting，待补的是相对真实 onset 的起点与固定钟点部署之间的差别。
在可取得多夜数据时，预先指定一个钟点，例如当地 18:00；标签定义固定，所有输入和插补截止在该时点。
同一参与者切分下，比较历史 SE/个体均值、钟点/星期特征、CatBoost 与一个 direct sequence predictor；不预设新架构必要。
以 `s-4/8h` 作为单列的事件相对参考，报告真实提前量分布、可预测覆盖率、AUPRC、Brier score/校准及每人权重一致的不确定性。
若固定起点与该参考没有实质差别，或历史基线已足够，则“部署起点带来重要差异”的假设被削弱。

**次级候选：同周表征的关联信息有多少能跨周保留。** 在允许重定义任务的数据上，明确比较 `X_W→Y_W` 与 `X_W→Y_(W+1)`。
后一项加入上一周结局/个人历史均值基线并按人隔离；看未来周误差与校准，而非拿 Apple 同周 `R²` 当应达到的 forecast 数字。
这是假设检验方案，未证明新颖性，也不要求先把 MESA 填进比较；需先确认数据支持重复夜/周及标签时点。

## 8. 来源定位与本轮阅读范围

- **[S1]** [Sakal 正式原文](https://academic.oup.com/sleep/article/48/8/zsaf113/8121042)：Methods 的 Study design、Data preprocessing、Model development、Model evaluation；Fig. 1/3；已读相关正文。
- **[S2]** [Sakal 补充材料入口](https://academic.oup.com/sleep/article/48/8/zsaf113/8121042#supplementary-data)：已取得 `zsaf113_suppl_supplementary_figures_s1-s47_tables_s1-s3_materials_2.docx`，读取表/图标题与说明、查看 Fig. S1；Fig. S8 特征选择说明已读。
- **[S3]** [特征选择代码](https://github.com/CollinSakal/ukb-sleep-efficiency-forecasting/blob/8a16fe18597b1377ba7e923bdf9e1cc964c14027/scripts/main-analysis/catboost/catboost-feature-selection.py)：`df` 全表、`model.fit(pool, eval_set=pool)`、SHAP 排序和逐特征评估。
- **[S4]** [调参代码](https://github.com/CollinSakal/ukb-sleep-efficiency-forecasting/blob/8a16fe18597b1377ba7e923bdf9e1cc964c14027/scripts/main-analysis/catboost/catboost-training.py)：`objective_cat`、10-fold AUC、200 trials。
- **[S5]** [重复 CV 代码](https://github.com/CollinSakal/ukb-sleep-efficiency-forecasting/blob/8a16fe18597b1377ba7e923bdf9e1cc964c14027/scripts/main-analysis/catboost/catboost-repeat-cv.py)：固定 features/params、eid 划分；本轮查询提交 `8a16fe1`（2025-10-24），只读，未执行。
- **[R1]** [Roberts PMC 全文](https://pmc.ncbi.nlm.nih.gov/articles/PMC11005467/)：Methods 的 preprocessing、Data partitions、Model Structure；§4b 与 Discussion；主文感受野属于 symmetric 模型。
- **[R2]** [官方 README](https://github.com/DanielGartenberg/24Hour_Actigraphy_SleepWake/blob/58a22c0c680faae4ce62900bca9c8cf3c5795101/README.md)：明确区分 bidirectional 主文模型与 causal 补充模型。
- **[R3]** [causal 训练代码](https://github.com/DanielGartenberg/24Hour_Actigraphy_SleepWake/blob/58a22c0c680faae4ce62900bca9c8cf3c5795101/Train_Activity_Count_Classifier.py)：`ScaledHyperModel.build`、训练折 scale、同索引标签；提交 `58a22c0`（2024-02-28）。
- **[R4]** [记录预处理](https://github.com/DanielGartenberg/24Hour_Actigraphy_SleepWake/blob/58a22c0c680faae4ce62900bca9c8cf3c5795101/preprocess_data.py)：`OFF_WRIST_DETECTION_MINUTES=120`、对齐 lag、缺失排除。
- **[R5]** [预处理函数](https://github.com/DanielGartenberg/24Hour_Actigraphy_SleepWake/blob/58a22c0c680faae4ce62900bca9c8cf3c5795101/preprocessing.py)：`identify_off_wrist`、`identify_lag_threshold`；[补充 DOCX](https://pmc.ncbi.nlm.nih.gov/articles/instance/11005467/bin/NIHMS1924140-supplement-1.docx) 本轮返回中间页，未视为已读。
- **[A1]** [Apple 论文 v1 正文](https://arxiv.org/html/2507.00191v1)：§4.1/4.3/5.1/5.2/6；[PDF p.8](https://arxiv.org/pdf/2507.00191v1#page=8) 夜间输入解释、[p.9](https://arxiv.org/pdf/2507.00191v1#page=9) future-forecast 限制。
- **[A2]** [v1 PDF p.13](https://arxiv.org/pdf/2507.00191v1#page=13)：A.1.3 周起点与 A.2.1 缩放；[p.21](https://arxiv.org/pdf/2507.00191v1#page=21)：A.6.1 Sleep metrics 的标签/筛选；附录与正文均已读。
- **[C1]** [Corda 出版社 PDF](https://mdpi-res.com/d_attachment/futureinternet/futureinternet-16-00046/article_deploy/futureinternet-16-00046.pdf?version=1706606654)：pp.5–7 方法/特征/量表，p.12 LOPO 与相反量表方向，§§4.3/5 用户评价与限制；[DOI](https://doi.org/10.3390/fi16020046)。
- **[C2]** [StudentLife 官方数据说明](https://studentlife.cs.dartmouth.edu/dataset.html)：本文的数据入口线索，本轮访问超时，未据此补写 EMA 时间规则。

[S1]: https://academic.oup.com/sleep/article/48/8/zsaf113/8121042
[S2]: https://academic.oup.com/sleep/article/48/8/zsaf113/8121042#supplementary-data
[S3]: https://github.com/CollinSakal/ukb-sleep-efficiency-forecasting/blob/8a16fe18597b1377ba7e923bdf9e1cc964c14027/scripts/main-analysis/catboost/catboost-feature-selection.py
[S4]: https://github.com/CollinSakal/ukb-sleep-efficiency-forecasting/blob/8a16fe18597b1377ba7e923bdf9e1cc964c14027/scripts/main-analysis/catboost/catboost-training.py
[S5]: https://github.com/CollinSakal/ukb-sleep-efficiency-forecasting/blob/8a16fe18597b1377ba7e923bdf9e1cc964c14027/scripts/main-analysis/catboost/catboost-repeat-cv.py
[R1]: https://pmc.ncbi.nlm.nih.gov/articles/PMC11005467/
[R2]: https://github.com/DanielGartenberg/24Hour_Actigraphy_SleepWake/blob/58a22c0c680faae4ce62900bca9c8cf3c5795101/README.md
[R3]: https://github.com/DanielGartenberg/24Hour_Actigraphy_SleepWake/blob/58a22c0c680faae4ce62900bca9c8cf3c5795101/Train_Activity_Count_Classifier.py
[R4]: https://github.com/DanielGartenberg/24Hour_Actigraphy_SleepWake/blob/58a22c0c680faae4ce62900bca9c8cf3c5795101/preprocess_data.py
[R5]: https://github.com/DanielGartenberg/24Hour_Actigraphy_SleepWake/blob/58a22c0c680faae4ce62900bca9c8cf3c5795101/preprocessing.py
[A1]: https://arxiv.org/html/2507.00191v1
[A2]: https://arxiv.org/pdf/2507.00191v1
[C1]: https://mdpi-res.com/d_attachment/futureinternet/futureinternet-16-00046/article_deploy/futureinternet-16-00046.pdf?version=1706606654
[C2]: https://studentlife.cs.dartmouth.edu/dataset.html
