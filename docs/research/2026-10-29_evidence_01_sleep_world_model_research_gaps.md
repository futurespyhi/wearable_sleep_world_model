# 表一：从已有论文出发的 wearable sleep world model 小研究缺口

- 检索与核查日期：2026-10-29，America/New_York；供当日 14:00 组会讨论。
- 目标：先识别有具体证据边界的小问题，再据此筛数据；不预设新架构、因果干预或某个现有项目必须成为答案。
- 阅读深度：**M** = 本次读到相关正文方法/结果；**A** = 作者摘要或出版社摘要；**P** = 作者/机构/厂商页面；**R** = 综述，仅供追踪原始引用。
- M 不表示复现成功、全部代码审计或完整补充材料审计；本轮没有下载权重、训练、访问新的受限数据或联系作者。
- 表内 **作者证据** 指来源明确报告的设计或结果；**我们的判断** 指由这些证据提出的解释或候选问题。
- 所有“尚未确认”都限定于注明的阅读范围，不能改写为该工作没有做过、无效或整个领域没有人研究。

## 1. 当前最值得讨论的结论

**“睡眠 world model”“未来睡眠预测”“latent rollout”“个体化 adaptation”已有直接先例；值得推进的是它们在一个明确部署协议下是否解决了一个小而可测的问题。**

文献侧的一个候选是：新用户仅逐日积累可用历史时，模型能否预测下一晚相对个人习惯的变化，且增益超过同信息的历史统计和直接预测器。
它允许以现有模型、简单状态空间模型或校准方法开展工作；无须先承诺一个新 world-model 架构。
该问题的候选新意在“在线可用历史下的个体内预测增益”，不是首次 personalization；是否已有等价研究仍需沿近邻引用继续查重。

另两条候选分别针对部署时钟变化，以及未来状态轨迹对睡眠结局是否有增量；它们是备选主问题，不应同时堆成一个大系统。
只有拿到真实计划/分配日志后，才增加行动条件版本；观察性睡眠预测本身可独立成立。

结合数据初筛后的讨论顺序见 [综合判断](2026-10-29_research_gap_to_data_synthesis.md)：G3 作为组会暂定主问题，G1 为备选。本文保留各候选的文献依据，不将排序当作实验结论。

## 2. NormWear-2：任务与方法的核查表

版本固定为 Luo et al., *Toward World Modeling of Physiological Signals with Chaos-Theoretic Balancing and Latent Dynamics*，arXiv:2605.15465v1，2026-05-14。[原文及版本][N1]
本次读了 §3.1–3.6、§4.1–4.4、§5、附录 A/B/C/D/G/H；附录 K 仅核表 11 与相关说明；图 3/6 的判断依据正文和图注。
因此下表的定位均为 M，资源页面另记 P；未完成代码级数据流追踪。

| 核查项 | 作者证据与精确位置 | 我们的判断 / 使用边界 |
|---|---|---|
| 问题定义 | §3.1：未来分布条件含 `x_<=t` 和 `u_<=t+H`。[N1] | 属于允许未来条件的任务定义；逐任务须区分计划、控制量和事后记录。 |
| 数据类型 | §3.2、表 1：VitalDB、PMData、CGMacros、Shanghai Diabetes、KidneyDialysis。[N1] | 五类不同场景，不能统一称为腕戴睡眠数据。 |
| 是否涉及 sleep | §3.2、附录 A 明写 PMData 包含 sleep；表 1 的预测信号栏列 HR、steps、distance、calories。[N1] | “原始数据含 sleep”成立；“主表已验证 sleep outcome forecast”尚未确认。 |
| 预训练 | §3.3–3.4、附录 H：动态特征平衡取样、逐通道 masking/reconstruction；MSE 训练。[N1] | “平衡预训练 + 生理 latent dynamics”已被覆盖。 |
| 两种推理任务 | §3.4：forecasting 与按已给通道补齐未观察通道的 simulation。[N1] | 通道补齐与真正预先可用的未来预测需要分别报告。 |
| Latent adaptation | §3.5：从 observed context 编码、聚类，估计相邻 patch 的状态转移并采样；无参数更新的 context adaptation。[N1] | 不能说 NormWear-2 只用冻结通用 encoder、没有个体适应。 |
| 行动条件机制 | §3.5、式 2：state-action 联合表示的邻域检索约束转移。[N1] | 已有明确的条件 dynamics；是否适合某个睡眠行动仍取决于字段和支持域。 |
| 归一化边界 | §3.6：预测目标使用 observed context 的均值/标准差。[N1] | 这处明确满足历史归一化；不能泛指它以整段未来统计量归一化。 |
| 指标 | §3.6、式 3：MAE、Soft-DTW、频谱与 latent 距离/相似度的组合。[N1] | 组合排名不能替代一个选定睡眠结局的预测误差或概率校准。 |
| 主结果 | §4.2、表 2：作者报告综合排名优势，同时说明没有单个方法在每项指标都最佳。[N1] | 评价指标的权衡已被作者讨论；“发现多指标不一致”本身不是新缺口。 |
| Action-awareness | §4.3、图 3D、附录 D/图 6：观察到的临床行动条件预测及定性案例。[N1] | 不等同于已检验个人未选行动的真实效果；这不是判定其预测结果无效。 |
| Personalization | §4.4、图 3C.2：历史量增加时的预测改善；表 3 检验替代 backbone。[N1] | “更多个人历史是否有帮助”已被覆盖；新问题须有更具体目标和在线协议。 |
| 规划范围 | §5 明列一般 RL/reward optimization 为未来方向。[N1] | 无须把补一个 planner 设为本项目必需贡献。 |
| 资源状态 | 官方模型卡有推理示例、demo 链接，同时注明 full codebase 正在内部 review。[N2] | 可加载资源与可复现论文全部流程是两个状态；未下载或运行验证。 |

### 2.1 五个主评估数据集是否能直接支撑 sleep 问题

以下单位按论文附录 A 表 4，history 的最大值不等于该数据集总随访长度。[N1]

| 数据集 | 主表目标 / 条件 | History -> forecast | 对 sleep 与未来条件可知性的判断 |
|---|---|---|---|
| VitalDB | ECG/PPG/EEG/respiration；麻醉/呼吸机参数 | 7.6–31.3 s -> 31.8 s | 围术期 EEG 不等于自然睡眠；设备设置可预先设定，也可能按新状态临时调整。 |
| PMData | HR/steps/distance/calories；运动类型 | 0.5–2 d -> 0.5 d | 原始数据有睡眠；运动记录是否在预测前已计划并留痕，正文未证明。 |
| CGMacros | glucose/HR/motion；营养成分 | 0.5–2 d -> 0.5 d | 膳食安排可能有控制，但逐餐实际时间/摄入不自动等于预测时可知。 |
| Shanghai Diabetes | glucose/HR；insulin/agents | 1–2 d -> 2 d | 用药记录与未来已知处方计划需分开；不是睡眠评估。 |
| KidneyDialysis | HR/BP/temperature；透析控制参数 | 5–20 sessions -> 4 sessions | §4.3 说参数可能因不耐受症状调整；不能默认四次未来 session 的实际控制轨迹已知。 |

上述未来可知性判断是我们的部署解释，并非作者报告存在数据泄漏。
条件预测可以把给定计划当作输入，也可以评估事后记录条件下的重建能力；需要给二者不同任务名称和指标。
对 PMData，作者数据页确列 `sleep.json`、`sleep_score.csv`，另有 `wellness.csv` 的主观睡眠质量/时长。[D1]（Fitbit/PMSys 段，P）
因此最准确表述是：**NormWear-2 使用含睡眠记录的生活数据，但本次检查的主表和下游任务表未给出明确睡眠结局评估。**

### 2.2 Split 与复现仍需追问的具体项

| 项目 | 本次确认 | 尚不确定，已检查范围 |
|---|---|---|
| VitalDB | 附录 A：20% 手术病例，即 1,278/6,388，留作评估，其余保留给 SFT。[N1] | 病例 ID 列表及窗口采样程序未审计。 |
| KidneyDialysis | 附录 A/表 5：291 人评估、1,161 人 SFT。[N1] | 逐人/逐 session 样本构造和模型选择流程未审计。 |
| PMData / CGMacros / Shanghai | 表 4 给测试窗口数量，附录 A 介绍来源。[N1] | §3.2、§4、附录 A/H 中未找到等价的逐人留出比例与窗口清单；不能据此断言分割错误。 |
| 预训练与评估隔离 | 附录 A.1 声明 pretrain collections disjoint。[N1] | 没有逐源逐参与者 manifest 审计；也不能反过来假设重叠。 |
| 推理时历史 | §3.5 明确 observed context；§4.4 增加历史长度。[N1] | 是否逐预测起点重建统计、跨窗口缓存如何更新，需要 demo/full pipeline 核查。 |
| 计数一致性 | 表 1 Shanghai 为 125；附录 A 引用原始集合 12+100 人。[N1] | 纳入集合或版本差异未解释清楚；复现前核样本清单即可，不外推为整项研究无效。 |

## 3. 睡眠领域近邻：已有覆盖与真实边界

### 3.1 三篇核心正文对照

| 原始工作、日期、深度 | 已覆盖的问题与定位 | 我们可提出的更窄问题 |
|---|---|---|
| **Sakal et al.，SLEEP，2025-04-28，M** | UK Biobank 80,811 人，入睡前 4/8 h 预测最后一晚低 SE；Methods: Study design / Data preprocessing；图 1/4。[S1] | 已有 pre-sleep forecast；部署触发时刻能否不依赖事后实际入睡时间，需要独立验证。 |
| **Wang et al.，arXiv v2，2026-02-19，M**；v1 为 2025-08-28 | 16 名女性、Garmin 每日特征/设备分数；3–11 d 输入、1–9 d 预测；按人训练/验证/测试及 TTA。§III-A–G、§IV-B/E、Algorithm 1、表 II。[S2] | 多日预测、跨人适应已经覆盖；更窄的是仅使用当日已到达数据的在线 adaptation，对“偏离个人习惯”的额外价值。 |
| **Gao，arXiv v1，2026-10-14，M** | EEG RSSM、dwell prior、transition calibration、生成轨迹；SHHS 200 人，160/20/20；Sleep-EDF 检验约束层/在线调度。§3、§4.1/4.5–4.7、表 4–6。[S3] | sleep latent world model 与 duration constraint 已覆盖；腕部输入下的未来条件预测和实际睡眠结局并未由这些指标直接证明。 |

Sakal 的标签来自 accelerometry 的 HMM，Methods 明确不是该夜独立 PSG；作者的同队列重复交叉验证不等于外部队列验证。[S1]（Methods；M）
其预测输入确实排除了预测点之后的 activity；“起点依赖目标夜 onset”与“读入未来传感信号”是不同问题。
因此我们应评估时钟可部署性，而不能把它概括成没有做真正预测。

Wang 的 Algorithm 1 先在 `D_test` 上适应，再对 `D_test` 最终推理；§III-D 说各 split 分别 MinMaxScaler，§III-C 包含平滑与插补。[S2]（M）
这些文本尚未证明逐 origin 的在线限制；批量无标签适应本身可以是合法 transductive 协议。
我们的待核项是：若改为只见当前历史前缀，性能是否保持；不能把无标签 TTA 一概称为标签泄漏。
§III-F 定义误差使用 normalized sleep value，§III-D 又提到 denormalization；比较数值前应核实现尺度，本文不横排其 RMSE。[S2]（M）

Gao 的准确率主要衡量当前 EEG 的 staging；dream quality 衡量 pooled dwell statistics；在线调度衡量切换次数与 dwell。[S3]（§4.3–4.7；M）
本次未见“给定某夜历史后，对该夜真实未来路径按 horizon 评分”的独立表；这不同于已经验证个体未来轨迹 forecast。
Sleep-EDF 的跨数据集证据针对约束层，不应写成整个 SHHS RSSM 零样本迁移成功。
以上是任务边界判断，承认论文已经实现 sleep world model；它没有要求我们的研究必须做 EEG 或 neuromodulation。

### 3.2 新近论文与业界：必须保留的查重线索

| 工作 | 日期 / 深度 / 来源位置 | 对新颖性判断的约束 |
|---|---|---|
| **SSF-SET，Kweon et al.** | IEEE JBHI 2026-08；PubMed 作者摘要，A；DOI 10.1109/JBHI.2026.3662787。[S4] | 明确仅用历史 EEG 预测未来阶段，SleepEDF20/78 按人验证；不能将 future stage forecast 或 token latent dynamics 称为无人研究。具体 horizon、预处理与代码待全文。 |
| **NeuroLingua-RT** | I2MTC 2026-05-25–28；IEEE 收录 2026-09-25；出版社摘要索引，A；DOI 10.1109/I2MTC66907.2026.11694657。[S5] | 当前分段分类与 next-segment forecast 双头、3 s 更新、Raspberry Pi 原型与 relay actuation 已有；不能仅以实时系统/闭环原型立新意。未核干预临床效果。 |
| **Corda et al.** | Future Internet 2024-01-30；本次读摘要、§4.1–4.3、§5 局部，M。[S6] | StudentLife、LOPO、次夜主观质量预测与 LLM 建议已有；用户信任评价与改善睡眠是不同结局。 |
| **HealthFormer** | arXiv v1 2026-04-30，作者摘要，A。[S7] | 通用 physiology world model 包含 sleep physiology；需全文确认哪些 sleep outcomes 被独立验证，不能直接忽略这一相邻方向。 |
| **The Impact of Domain Shift on Predicting Perceived Sleep Quality from Wearables** | Abdalazim et al., Sensors 2025-06-27；作者摘要与出版社索引，A；DOI 10.3390/s25134012。[S8] | population/personalized 模型的跨域退化及无监督 cluster-based adaptation 已研究；作者将任务称为 sleep quality recognition。泛称 domain shift、无标签适应或个体化不能构成空白。输入/结局时间线待正文。 |
| **Fullpower / Sleeptracker-AI** | 厂商公告 2026-04-25，P，“Predictive Capabilities”“Sense-and-Respond”段。[P1] | 厂商明确使用 world model、未来 wake timing 与床体调整反馈等表述；这是已公开能力声明，当前页面没有给对应预测 benchmark。 |
| **Sleep World Models: From Staging the Night to Simulating It** | Preprints.org v1，提交 2026-10-21、公开 2026-10-22；摘要、§1–2，R。[R1] | 是未同行评审综述、无新数据；用于追踪 mechanistic/learned 近邻。其“未见”仅在作者选文范围，不能充当本项目 novelty 的独立证明。 |

R1 对 sleep world model 使用更严格的 input-driven 定义，并提出 mechanistic prior 等研究任务。
这个定义和路线图不是必须接受的任务门槛；本项目可以先做 action-free latent forecasting，或研究既有模型的适应/评价协议。
厂商未披露完整架构、split 或预测指标，只说明公开验证边界；不能据此断言其产品没有相关能力。[P1]（我们的判断）

## 4. 三个小缺口候选：从问题到最小实验

下表全部是**我们的待验证假设**；出处说明为什么值得问，不代表出处已经证明整个领域存在空白。

| 优先级 / 候选问题 | 与近邻的具体距离 | 最小比较与可证伪条件 | 先需要什么数据 |
|---|---|---|---|
| **G1：在线个人历史是否真正帮助预测次夜偏离习惯的变化？** | N1 已做 history scaling，S2/S8 已做 adaptation；尚需查重的是严格历史前缀下，个体内变化预测超过个人统计基线的证据。 | 固定每日出结果时刻；同一输入比较滚动个人均值/上一夜、直接预测器、现有 latent transition；按 3/7/14/28 d 可用历史画增益。若只改善人群均值差异、个体内 skill 不增，则不支持。 | 多人多周连续 wearable、每日睡眠结局、设备与上报时间戳；不要求 intervention。 |
| **G2：从事后对齐的 onset 时钟改为可部署时钟，预测价值还剩多少？** | S1 的起点按目标夜实际 onset 回溯；其 pre-sleep 任务已成立。我们问同一数据/模型换触发规则造成的差异。 | 固定本地时刻或仅用历史预测的 bedtime；同样 history 截断；按 lead time、作息不规则程度报告误差/校准。若结果一致，说明时钟选择不是主要限制。 | 时间戳、时区、连续活动和多夜 sleep timing；目标夜 onset 只能用于事后分层/评价。 |
| **G3：只读腕部历史时，动态约束能否改善未来清醒时长，并保留真实短觉醒？** | N1 重信号/频谱/latent，S3 重 dwell，S4 已做 EEG stage forecast；候选区别是 wrist 输入下的未来清醒负荷与短事件保留，不是首次 rollout。 | 预先规定 t0，只读 wrist 到 t0；预测未来 30 min 清醒总时长。比较直接多步状态预测、状态转移、Markov/HSMM，并设 direct outcome 基线；总时长均评分，短事件漏报仅比较有轨迹输出的模型。若只是平滑或抹掉真实事件，不支持增益。 | 同步 wrist 和逐 epoch 参考标签；t0 不能依赖未来参考标签；跨人留出，外部设备另测。 |

### 4.1 G1 建议怎样收窄

先选一个连续结局，例如次夜 device-derived total sleep time；目标是预测，不将设备标签叫作真实生理睡眠质量。
候选出结果时刻可定为每日 18:00；仅以此前已到达记录构造特征，不能读事后生成的当天完整日摘要。具体时刻由数据覆盖决定。
研究量为 `y_(d+1) - mean(y_<d+1, recent history)`；baseline 的个人均值也只能用预测点以前的有效夜晚。
模型还要报告原始单位误差，避免只在中心化目标上表现好却偏移绝对值。
每人等权汇总误差和 skill，分别给个体内差异、冷启动天数、有效历史天数；bootstrap 以参与者为单位。
Adaptation 可以更新简单均值、读出头或转移统计，不必都更新 backbone；将计算开销作为附属证据。
随机划分时间窗口不回答这个问题；训练/调参按人隔离，测试用户按时间推进，所有插补/归一化只用允许信息。
若低复杂度个人历史模型已解决问题，应据实保留结果，并重新判断是否值得增加 latent dynamics。
若只在一批 16 人数据上成立，定位为可行性证据；跨队列复现后才能扩大可迁移性主张。

G3 的另一条具体动机来自 S3 §4.6/图 4：展示案例的专家标签本身有两个低于设定 dwell 阈值的片段。
因此应用设定的最小时长不是所有真实睡眠阶段都应满足的生理规律；压短片段可能改善控制稳定性，也可能改变清醒负荷。[S3]（我们的推断）
这条候选应与 S4/S5 的未来阶段预测直接对照，先确认新增的 wrist/目标/误差分解是否具有研究价值。

### 4.2 条件输入作为后续分支

若研究数据只有已完成运动、已摄入餐食或当夜环境记录，先做纯预测或记录条件预测。
若另有预测前留下的计划，才比较 history-only、history+planned、history+realized 三种信息条件。
各条件内部再比较 direct 与 rollout，从而区分额外信息、计划误差与模型结构的贡献。
只有当研究目标变为行动效应/政策价值时，再要求相应试验或识别设计；不把因果条件强加给 G1/G2/G3。

## 5. 从候选问题反推数据路线

| 数据线索 | 对本轮问题的作用 | 当前证据与门槛 |
|---|---|---|
| **PMData** | G1 的首个公开可行性检查；可能同时提供设备与自报睡眠结局 | D1 官方页描述 16 人/5 个月、wearable 与 wellness；缺失、时区、标签发布时间与可用参与者夜需实际字段审核。不能将固定小样本的成功当泛化定论。 |
| **UK Biobank actigraphy** | G2 较贴近 S1；可复核入睡时钟与固定时钟协议 | S1 Methods 描述 7 日佩戴与样本筛选；适合较大人群，不足以直接回答 28 d 个人适应。访问需既有授权。 |
| **Garmin 16 人队列** | 与 S2 的 adaptation 问题最直接相邻 | S2 §III-A 为大学安全研究环境内数据；本次未确认公开原始数据/可下载 split。作为复现线索，不当作已可用资源。 |
| **StudentLife** | 可补查主观质量预测与作息变化，帮助审计 G1/G2 的目标定义 | S6 §4.1–4.2 使用手机数据和 EMA；不能自动当作腕部生理数据，也不能把自报质量与设备时长混成同一标签。 |
| **同步 wrist + 逐 epoch 参考标签的数据** | 仅在选 G3 时优先筛选；多夜记录也可检验仅用过去夜晚的适应 | 需要实际腕部通道、同步参考与预测起点；完整 PSG 与头带自动/专家校正标签要分别标注。Sleep-EDF/SHHS 的 EEG 不能单独证明 wrist 部署有效。 |

数据优先级跟随主问题：若选 G1，长时间重复夜晚比单夜高密度 PSG 更关键；若选 G3，逐 epoch 同步参考标签更关键。
这不是将两个问题互斥，而是先用能检验主假设的数据，避免因为熟悉某个数据库而反推贡献。

## 6. 本轮还不能回答什么

- NormWear-2 在 PMData 上是否已有未列入正文的 sleep-target 配置：检查了 §3.2、表 1/2/4、附录 A/B/D、官方模型卡；未跑完整代码。
- NormWear-2 各任务的未来条件究竟取完整记录、既定计划还是只取历史：问题定义已明确含未来条件；逐任务输入清单未核实。
- S2 的 online-prefix adaptation 是否与 batch TTA 等价：已读 Algorithm 1、§III-C/D/G、§IV-B/E；未取得代码和原始样本。
- S3 的 generated trajectories 是否在个体未来路径上有独立 horizon 评分：已读 §3、§4、§5；看到的是 staging、dwell 和 scheduler 证据。
- S4/S5 的精确 forecasting horizon、输入 buffer 的末端及预处理边界：本轮只有摘要层证据，不能据此做复现参数表。
- S7 的睡眠结局是否进入 intervention evaluation：只读摘要；HTML 无可用版本，不能将其总体临床结果外推到 sleep。
- S8 是否存在与 G1 完全等价的前瞻协议：摘要称 recognition；出版社限流、PMC 本次返回验证页面，故只作为必要查重线索，不声称已排除重合。
- 综述 R1 的选文是否完整、mechanistic-prior 空白是否成立：本轮未逐条复核其 62 项映射，故不采用该负面结论。

## 7. 来源、版本与检索记录

以下 URL 均为原始作者、出版社、机构或厂商来源；访问日统一 2026-10-29。正文每个证据项的节/表定位即其阅读边界。

- **N1 / M**：Luo et al., arXiv:2605.15465v1，2026-05-14；§3.1–3.6、§4、§5、附录 A/B/C/D/G/H，K 表 11。HTML 可读；PDF 超出抓取大小限制，未将图形细节标作人工视觉核查。
- **N2 / P**：NormWear-2 官方 Hugging Face 模型卡，更新日期未标；读取 Introduction、Usage、Inference Example、full-codebase 说明，未下载或运行。
- **S1 / M**：Sakal et al., SLEEP 48(8):zsaf113；网络发表 2025-04-28；Methods、图 1/4、Results 和 Discussion 的时间/标签边界。
- **S2 / M**：Wang et al., arXiv:2509.06974v2，2026-02-19；§III、§IV-B/E、Algorithm 1、表 II、§VI；未复现数据和数值。
- **S3 / M**：Gao, arXiv:2610.33033v1，2026-10-14；§3–5、表 1–6；不采用作者的“first”表述。
- **S4 / A**：Kweon et al., IEEE JBHI 30(8):6579–6592，2026-08；PubMed 作者摘要及 DOI，仅摘要。
- **S5 / A**：NeuroLingua-RT, I2MTC 2026；IEEE 摘要/发表元数据的原站搜索索引；直接页面抓取失败，未读正文。
- **S6 / M**：Corda, Massa, Riboni, Future Internet 16(2):46，2024-01-30；出版社 PDF 摘要、§4.1–4.3、§5 局部；主站限流。
- **S7 / A**：Lutsker et al., HealthFormer, arXiv:2604.27899v1，2026-04-30；作者摘要，HTML 404。
- **S8 / A**：Abdalazim et al., Sensors 25(13):4012，2025-06-27；PubMed 作者摘要及出版社原站索引，未读正文，不能直接并入 next-night forecasting 数值比较。
- **D1 / P**：Simula PMData 官方数据页；原数据论文 2020，网页索引标最近更新 2026-10；读取搜索返回的官方完整字段段落，直接页面重复 timeout；未下载数据。
- **P1 / P**：Fullpower-AI/Sleeptracker-AI 公告，2026-04-25；完整公告。产品声明与论文验证分开。
- **R1 / R**：Zhang, Liu, Yao, *Sleep World Models: From Staging the Night to Simulating It*，2026-10-22，未同行评审 review；摘要、§1–2、版本元数据。

主要实际查询：`"sleep" "world model" wearable 2026`、`"sleep" "world models" forecasting`、`"NormWear-2" sleep forecasting`、`"sleep forecasting" "2026" wearable personalised`、`"Individualized and Interpretable Sleep Forecasting"`、`"SSF-SET"`、`"NeuroLingua-RT"`、`"Sleep World Models: From Staging the Night to Simulating It"`、`PMData sleep simula`。
方法摘要聚合站、新闻转载与非原始评测只用于发现题名，表中结论回到 primary；R1 明确作为综述入口。
这是定向查重和问题筛选，未达到系统综述覆盖；推荐提交组会的是 G1/G2/G3 的取舍，不是“全球首个”或 novelty 已锁定。

[N1]: https://arxiv.org/html/2605.15465v1
[N2]: https://huggingface.co/mosaic-laboratory/normwear2
[S1]: https://academic.oup.com/sleep/article/48/8/zsaf113/8121042
[S2]: https://arxiv.org/html/2509.06974v2
[S3]: https://arxiv.org/html/2610.33033v1
[S4]: https://pubmed.ncbi.nlm.nih.gov/41662557/
[S5]: https://ieeexplore.ieee.org/abstract/document/11694657/
[S6]: https://mdpi-res.com/d_attachment/futureinternet/futureinternet-16-00046/article_deploy/futureinternet-16-00046.pdf?version=1706606654
[S7]: https://arxiv.org/abs/2604.27899
[S8]: https://pubmed.ncbi.nlm.nih.gov/40648271/
[D1]: https://datasets.simula.no/pmdata/
[P1]: https://sleeptracker.com/news/2026/fullpower-ai-deploys-an-ai-world-model-for-human-biological-and-environmental-systems
[R1]: https://www.preprints.org/manuscript/202610.2267
