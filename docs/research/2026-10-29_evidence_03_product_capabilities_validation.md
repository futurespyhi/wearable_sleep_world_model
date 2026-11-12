# 证据表三：睡眠产品的能力与对应验证

- 核查截止与访问日期：**2026-10-29，America/New_York**；用于当日 14:00 EDT 组会。
- 固定对象：Samsung Bedtime Guidance、WHOOP Sleep Planner、Garmin Sleep Coach、Eight Sleep Autopilot。
- 依据：[三表计划 §5](2026-10-29_meeting_three_evidence_tables_plan.md)；[前轮综述 §5、§9](2026-10-28_wearable_sleep_prediction_academic_industry_review.md)仅作为检索入口。
- 阅读等级：**P** = 官方功能原文；**M** = 原始论文相关方法、结果与披露；**A** = 原始会议摘要；各来源的实际范围见 §7。
- “本轮未找到对应验证”限定于下列来源与定向检索，**不表示研究不存在，更不表示厂商内部没有模型**。

## 1. 可用于汇报的判断

**产品已经包含模型化建议与实际控制；需要检验的是某个明确功能的预测或干预价值。**
Samsung 的研究来源比单独一条宣传文案更完整：KAIST 确认算法进入 Galaxy Watch，相关团队已有 SleepWake 原型及前瞻研究。
但研究原型、零售版 Bedtime Guidance、睡眠分期算法仍须分别记录，不能互相替代验证。[S1]、[S2]、[S3]、[S4]

| 产品及固定功能 | 已确认的输入、更新与输出 | 建议/实际行动 | 与该功能相连的证据 | 当前可以说到哪一层 |
|---|---|---|---|---|
| **Samsung Bedtime Guidance** | 至少 3 天睡眠分析；双过程框架表征睡眠压力与昼夜节律；输出建议就寝窗口。[S1] | 用户执行就寝建议；本功能本身没有强制执行睡眠的装置 | KAIST 产品转化声明；2023 数学原型、2025 SleepWake 的建议遵从与警觉性研究。[S2]、[S3]、[S4] | 模型化推荐及相关原型的人体证据已存在；研究原型与零售算法的参数/版本同一性未核实 |
| **WHOOP Sleep Planner** | 基线需求、Strain、睡眠债、午睡、近 28 天睡眠习惯与生活节律；给出需求及 bed/wake 目标。[W1] | 提醒/计划；触觉闹钟可以实际振动唤醒 | WHOOP 4.0 的 PSG 测量比较，以及佩戴频率的观察研究；均未隔离 Planner 的作用。[V1]、[W3] | 确有个体化需求与计划；不能把目标时长称为实际将睡时长的已验证 forecast |
| **Garmin Sleep Coach** | 年龄、活动、睡眠史、午睡、HRV；早晨估计下一晚需求，日间随活动和午睡更新；新机型资料加入昼夜节律。[G1]、[G2] | 建议睡眠需求；实际入睡由用户决定 | 本轮核到旧硬件 Vivosmart 4 的测量比较；未找到与所查 Coach 版本对应的需求/建议效果试验。[V1] | 需求估计已实现；跨硬件、跨年份的数值规则及验证不能直接通用 |
| **Eight Sleep Autopilot** | 床上传感、用户偏好、睡眠阶段及环境等信息驱动床温调整；当前网页为 Autopilot 4.0。[E1] | **实际加热/降温**；具备执行通道 | 2024 固定 OFF/ON/OFF 研究；2025 分期温控摘要；另有 2025 随机交叉研究，各验证不同配置。[E2]、[E3]、[E5] | 控制与人体研究均已存在；不能据此宣布每个候选温度下的个体结果预测已验证 |

这里“识别”指从已观测信号估计已发生的睡眠；“需求”是应达到的目标；“forecast”是决策后实际结果的预测。
“建议”还要经过用户接收与执行；设备控制则可直接改变环境。它们是不同评价对象，不是统一的产品成熟度排名。
品牌整体提供分期，并不意味着其 coach 的效果已由分期准确率证明。

## 2. Samsung：追到研究原型，但保留产品版本边界

**官方功能定位。** 2025-09-10 Samsung 官方说明将 Bedtime Guidance 明确连接到 Two-Process Model of Sleep Regulation。
发布对象为 2025 年 7 月的 Galaxy Watch8 系列；该澳洲材料脚注要求 Android 11+、Samsung Health 6.30.2+，并写明基于 3 天分析。
这些是该地区/日期的条件，不扩写为所有国家和后续机型的统一要求。[S1，Leading the Charge in Sleep Health、脚注 3]

**产品转化连接。** KAIST 2025-07-28 原文确认 Kim 团队算法通过与 Samsung 合作进入 Galaxy Watch，包括 Watch8。[S2]
同团队 2023/2025 论文提供机制与人体研究链条；本轮未找到零售版构建号与论文实现逐项对应的说明。
因此把它们记为“有来源支持的相关研究原型”，不写成“Watch8 Bedtime Guidance 已完成下面这项临床试验”。

| 原始证据 | 设计、样本与标签 | 对照/结果与边界 |
|---|---|---|
| **Song et al., SLEEP 2023，zsad179**，M | 71 名女性轮班护士，13–21 天；腕部活动记录、睡眠日记与班前/班后 KSS 主观嗜睡评分 | 模型模拟压力/节律，比较静态节律模型与另一生理模型；另模拟主睡眠加小睡方案。本文的建议方案不是已完成随机干预；不把其警觉性拟合误差称为零售产品未来睡眠误差。[S3，Methods、Fig.2–4、Discussion] |
| **Song et al., SLEEP 2025，zsaf160**，M | 71 人旧数据回顾分析；另有 19 名男性急救人员前瞻试点，约 6 天隐藏建议、约 20 天开放建议；16 人 Galaxy Watch、3 人 Apple Watch，亦允许手填 | 按遵从程度变化事后分为 10/9 人；比较相同班次。高遵从组自评警觉性 4.67→5.64，p=.012；无随机分组。标签是每日 1–10 分警觉性及 1–5 分睡眠质量，不是 PSG/PVT。[S4，Methods、Fig.3] |

2025 研究使用历史睡眠与预先填写的可就寝时间、工作窗口来给出计划；这与单纯显示历史分数不同。
其建议遵从指标依赖实际睡眠与推荐窗口的重叠；事后按重叠变化分组会混入执行能力、日程与其他行为差异。
故现有证据支持进一步试验，尚不提供随机化建议效应；不能把 TST 的 p=.058 解释为排除了时长贡献。[S4，Fig.3、Discussion]

披露：2023/2025 均有 IBS 与 Samsung Medical Center 资助；2023 声明无利益冲突，2025 披露作者开发 SleepWake 及相关专利申请。
2025 还说明无法区分所有睡眠记录的传感器、手填或自动估计来源；这直接影响遵从分析。原文未给出零售 Bedtime Guidance 固件版本。[S3]、[S4]

**小结论：** “双过程状态 + 个体睡眠计划 + 警觉性评价”已有真实近邻。
仍可测的问题是，在明确发送时刻、实际执行记录与独立结局下，模型能否预测建议实施后的实际结果，而不只解释事后遵从者表现。

## 3. WHOOP：需求、计划、测量与使用关联分开

2026-02-12 官方说明允许以 100%/85%/70% 需求为计划目标，并据习惯与指定起床时间安排睡眠窗口。
Wake Alarm 的确执行振动，可按固定时间、达到目标或 Recovery 条件触发；它不等于自动执行整晚的睡眠计划。[W1，personal sleep need、bed/wake time]

| 证据对象 | 样本、对照与标签 | 对 Planner 的支持范围 |
|---|---|---|
| **WHOOP 4.0 测量比较，2025**，M | 62 人单夜 PSG 总队列；WHOOP 有效 40 人、缺失 5 人；同夜人工 PSG 评分 | 四态一致性 kappa 0.37±0.16；验证睡眠测量，没有随机发送计划、需求真值或建议效果结局。[V1，Methods、Tables 2、7] |
| **佩戴频率观察研究，2025**，M | 11,914 名 2024 年新 WHOOP 4.0 用户，907,249 个日/夜记录，12 周；比较不同佩戴频率及个体内周变化 | 结局由 WHOOP 产生；佩戴更多与更长/规律睡眠等相关。暴露是佩戴频率，没有隔离 Planner 或随机对照；作者披露 WHOOP 雇佣关系。[W3，§2、§3、COI] |

官方 2026 准确性页也明确其引用的 CQU 研究测试 WHOOP 3.0，并提醒硬件/算法后来已改变。[W2]
本表的 4.0 比较来自另一个原始研究，不能把两篇论文的样本、数字和代际拼在一起。

**本轮未找到的对应验证：** 所查 Planner 文档、官方验证索引、上述原始论文及定向文献检索中，没有定位到隔离 Sleep Planner 的随机建议效果试验或 sleep-need 个体真值验证。
这不能推出“WHOOP 没有行为干预研究”；也不能用“实际睡眠与需求之差”来验证需求本身，否则目标被当成了真值。
需求研究应先定义充足睡眠的外部结局，例如固定时间警觉性/表现；实际睡眠 forecast 则评价后续实际时长或效率。

## 4. Garmin：功能与版本必须一起记录

2024-11-18 博客描述五类输入、10 分钟步长、7–9 小时建议范围，并列举 Venu 3、fenix 8 等兼容设备。[G1]
**这些数值只归属于该日期的说明。** Forerunner 170 手册 v2（2026-09）明确把 circadian rhythm 加入 Coach 输入，但没有在该节重申同一数值范围。[G2]
因此可以确认后续资料包含节律，不能从旧博客推断所有 2026 机型的范围与规则。

| 证据对象 | 设计、标签及结果 | 不能外推到哪里 |
|---|---|---|
| **Vivosmart 4 测量比较，2025**，M | 与 WHOOP 上述研究同源；有效 25 人、缺失 18 人；单夜同人 PSG 对照；四态 kappa 0.21±0.13。[V1] | 测试的是旧硬件的睡眠识别，未评价 Sleep Coach；既不能证明新版 Coach 有效，也不能用旧分期误差否定其建议效果 |
| **所查 Coach 功能文档**，P | 描述输入与输出，无试验 N、对照组、需求参考标签或干预结局 | 本轮未找到直接对应所查版本的需求估计/建议效果验证；机制权重与个体需求真值保持未决 |

V1 的资助为 VLAIO，作者声明无财务及非财务利益冲突；WHOOP/Garmin 有效人数不同，不能把总队列 62 人当成两台设备各自的验证人数。
相关硬件/软件代际不一致是适用范围问题，不是“有论文就有效”或“旧硬件测得差就无效”的二选一。[V1，Funding、Disclosure]

**小结论：** 加入活动、HRV、午睡、历史或节律本身不足以建立研究区别。
若研究目标是睡眠需求，需要先确定需求的操作性定义与外部评价；若目标是实际睡眠，则将产品需求值作为一个可用输入/基线，另建实际结局预测任务。

## 5. Eight Sleep：三项研究分别回答不同问题

当前官方 Autopilot 页面写明实时调节温度，标注 Autopilot 4.0；床体升降还依赖相应硬件。[E1]
2025-06-12 官方说明进一步给出阶段偏移机制：在用户温度上按睡眠阶段加偏移，且会参考前夜分期比例调整偏移幅度。[E4]
这足以确认控制行为和部分规则，不能从“AI”措辞推导其训练目标、动作搜索方式或候选温度结果的校准性能。

| 原始研究及具体功能 | 设计、N、参考测量 | 主要结果、限制与版本 |
|---|---|---|
| **Moyen et al., Bioengineering 2024，11(4):352**，M | 75 人招募、69 人完成、54 人纳入；固定 7 夜 OFF→7 夜 ON→2 夜 OFF。前 5 夜尚无 Pod cover；睡眠用 8 夜 Zmachine 单通道 EEG 自动分期，HR/HRV 用 Fitbit Versa 2 | 用户自选三阶段温度，不是随机试验或新版分期 Autopilot 的独立测试。报告 HR 约 −2%、HRV 约 +7%，部分性别/温度/阶段结果改善；整体 TST/SE 未显著改善。[E2，§2、Fig.1、§4.3、§4.5] |
| **Ediger et al., SLEEP 2025 摘要 0462，A202**，A | **另一个 34 人样本**，10 女/24 男，43±11 岁；至少 7 夜无 Pod 基线和至少 7 夜 Pod + Sleep Stage Autopilot；用 **Oura Ring** 测结果 | HR −2.3 bpm、HRV +4.9 ms、深睡 +4.7 min，均 p<.05；前后配对，摘要未报告随机次序或恒温/旧控制器对照。Pod/Oura 型号、软件版本和完整 CI 未披露。[E3，Methods、Results] |
| **Stevenson et al., Clocks & Sleep 2025，7:55**，M | **第三项研究，也为 34 人**，20 女/14 男；Pod 3，≥3 夜适应后随机、平衡交叉 ON/OFF 各 7 夜；睡眠用腕部 actigraphy，心血管用 Pod；记录室温/湿度 | 主观睡眠质量改善（d=0.92）；客观睡眠及生物指标未见显著条件效应。用户可手动调节，不能隔离阶段响应算法；不是前一项 Oura 研究。[E5，§2、§3.5、§4、Fig.2] |

2024 研究的 Zmachine 是独立设备的自动单通道 EEG 分期，不能简称为“全部 16 夜人工 PSG”。
固定顺序、温度自选及未测室温意味着时间/环境混杂仍在；“未选择温度会怎样”也没有个体反事实真值。[E2，§2.2–2.4、§4.6]

2025 阶段温控摘要使用第三方 Oura 算法，降低同一 Pod 同时干预与测结局的直接依赖，但 **Oura 不是 PSG**。
无 Pod→Pod+Autopilot 同时改变床上硬件和控制模式，不能单独识别“阶段响应”相对恒温的增益。[E3]

利益关系：E2 由 Eight Sleep 资助，多位作者是员工/持股者，另有顾问或前员工；数据/代码因专有原因不公开。
E3 作者机构均为 Eight Sleep，摘要没有完整独立 COI 文本；E5 由 La Trobe University 内部基金资助，作者声明无利益冲突。[E2，p.22–23]、[E3]、[E5，p.18]

**小结论：** 已有闭环执行与人体干预证据；效果依赖研究对象、控制配置和结局。
不能概括为“只有营销、没有控制研究”，也不能把不同研究的有利指标组合成一个已验证的 Autopilot 4.0 效果包。

## 6. 数据条件满足后的行动分支候选

**行动分支候选：在固定晚间决策时刻，给定发送或不发送同一条个体化就寝提醒，能否预测次晨固定时刻的警觉性，并解释实际执行的差异？**
这是由产品证据引出的条件分支，不是本轮已经选定的主问题或关于整个行业“从未做过”的结论；需要进一步核对可用行动日志后冻结。三表合并后的主问题与数据优先级见 [综合判断](2026-10-29_research_gap_to_data_synthesis.md)。
Samsung/SleepWake 提供生理模型基线；WHOOP/Garmin 提醒我们应区分需求与实际结果；Eight Sleep 说明直接设备控制是另一种行动接口。

| 必需数据/设计 | 最小字段与用途 |
|---|---|
| 决策前历史 | 截止 t0 的睡眠、活动、HRV、光照等可取得记录；记录测量时刻与同步时刻，防止事后补齐输入 |
| 行动分配 | t0、提醒内容/目标窗口、可发送状态、随机化概率、分配、实际发送与送达；“建议早点睡”须成为可编码行动 |
| 接收与执行 | 打开/确认时间、实际关灯/就寝/入睡时间、午睡与日程变化；发送、看到、按时就寝分别存储 |
| 固定主要结局 | 次晨预先约定时刻的 PVT 或 KSS；同时记录距起床时间，避免睡眠惰性与不同测量时点混淆 |
| 睡眠次要结局 | 当晚实际 TST/SE 或独立设备/PSG 子样本；保存标签设备/版本及缺失原因，不用 sleep need 代替实际睡眠 |
| 同信息对照 | 双过程模型及简单遵从模型、直接统计/时序预测器；若加入 latent transition，必须让所有方法看到相同历史和行动 |
| 评估边界 | 跨人/向前时间测试、预测误差与校准；干预效果按分配分析，事后遵从分析另标，保留不执行与缺失情况 |

最小可否定假设：加入执行概率与实际睡眠中介的建模后，行动条件预测能在独立参与者上改善次晨警觉性的误差/校准。
若简单直接模型或双过程基线同样有效，则没有证据支持更复杂状态转移结构的价值。
若只有历史观测而没有行动分配/送达日志，先做 past-only forecast；不能把实际睡眠时间回填成预先已知的行动。

温控作为替代路线需要额外的设定温度、实际床面/水温、每次更改时刻、环境温湿度、人工覆盖及控制器版本。
优先比较明确的恒温与预定温度偏移；只有能安全随机分配且记录实际执行后，才评价某个温控策略的效果。
仅凭 ON/OFF 平均改善无法判断模型是否正确预测了每个人的温度响应。

### 范围外重要查重线索

Fullpower 官方在 **2026-04-25** 已将 Sleeptracker-AI 称为 world model，声明融合压电和环境观测、预测未来状态及干预结果，并可抬高床头后继续观测。[X1]
这是**厂商功能/架构声明**；该页未提供动作条件预测误差、校准、随机干预设计或完整模型验证。
本轮不扩成第五行产品审查，但后续不能再用“业界没人称自己 world model”或“只有识别”作为区别；应比较可测试功能与对应证据。

## 7. 来源定位、日期与阅读范围

所有来源访问日期为 2026-10-29。HTML 以章节名定位，PDF 页码按论文印刷页；未读取的补充材料不计入精读。

| ID | 一手来源及版本日期 | 实际阅读范围/定位 |
|---|---|---|
| S1 | [Samsung World Sleep 2025][S1]，2025-09-10 | P：Leading the Charge in Sleep Health、脚注 3；核模型名称、Watch8、3 天分析与平台要求 |
| S2 | [KAIST 产品转化说明][S2]，2025-07-28 | P：正文算法介绍、与 Samsung 合作段；证明技术来源连接，不提供版本逐项对照 |
| S3 | [Song et al., zsad179][S3]，SLEEP 46(9)，2023 | M：Methods、Fig.2–4、Table 2、Discussion、Funding/Disclosure；补充方程与代码未复核 |
| S4 | [Song et al., zsaf160][S4]，2025-06-09 在线、2025-08-23 排版 | M：Materials and Methods、Fig.1–5、Discussion、Funding/Disclosure；前瞻设计和事后分组已核，补充材料未读 |
| W1 | [WHOOP Sleep Planner][W1]，2026-02-12 | P：personal sleep need、best time to go to bed/wake up；本轮页面重定向至 nz/en 同题文章 |
| W2 | [WHOOP 睡眠准确性说明][W2]，2026-01-23 | P：accuracy、wearing more frequently；用于定位原始研究与代际边界 |
| W3 | [佩戴频率原始研究][W3]，Sensors，2025-04 | M：§2.1–2.3、结果/限制、COI；核 4.0、12 周、样本与观察性暴露 |
| G1 | [Garmin 五因素博客][G1]，2024-11-18 | P：How Garmin estimates your sleep need 与五因素；仅支持该日期规则 |
| G2 | [Forerunner 170 手册][G2]，v2，2026-09 | P：Sleep Tracking、Setting Your Sleep Schedule；核节律输入与手册版本 |
| V1 | [Schyvens et al., zpaf021][V1]，2025-03-22 在线 | M：Methods、Tables 2、7、Funding/Disclosure；单夜、型号有效人数和缺失均已核 |
| E1 | [Autopilot 官方页][E1]，访问时标注 4.0 | P：From night one、All night every night、输入/执行说明；动态网页没有固定发布日期 |
| E2 | [Moyen et al. DOI][E2]；[出版社 PDF][E2P]，2024-04-03 | M：PDF p.2–8 方法、Fig.1、p.19–22 讨论/限制、p.22–23 数据/COI；补充表未单独读取 |
| E3 | [Ediger et al. 摘要 0462][E3]，2025-05-19 | A：SLEEP 48(S1):A202，Introduction/Methods/Results；已读出版社索引返回的原始完整摘要，直接页面重定向报错 |
| E4 | [Eight Sleep 对阶段温控研究的说明][E4]，2025-06-12 | P：How does Autopilot work、How researchers tested；只补产品规则，不当作第二个独立研究 |
| E5 | [Stevenson et al. DOI][E5]；[原文 PDF 镜像][E5P]，2025-10-01 | M：PDF p.1、3–9 结果、p.12–18 限制/方法/披露；出版社限流后读取同版原文镜像 |
| X1 | [Fullpower world model 声明][X1]，2026-04-25 | P：What makes...、Sense-and-Respond；范围外线索，未检索其完整验证文献 |

核查仍未覆盖：零售算法与论文的代码/构建号绑定、各厂商未公开研究、四品牌所有历史硬件，以及全部后续算法升级。
本表不据这些未决项推断内部能力，也不把论文标题或厂商所用模型名称当作性能证据。

[S1]: https://news.samsung.com/au/samsung-showcases-next-generation-health-innovations-at-world-sleep-2025
[S2]: https://news.kaist.ac.kr/newsen/html/news/?mode=V&mng_no=49710
[S3]: https://academic.oup.com/sleep/article/46/9/zsad179/7221723
[S4]: https://academic.oup.com/sleep/article/48/11/zsaf160/8158652
[W1]: https://www.whoop.com/us/en/thelocker/how-much-sleep-do-i-need/
[W2]: https://www.whoop.com/us/en/thelocker/how-well-whoop-measures-sleep/
[W3]: https://pmc.ncbi.nlm.nih.gov/articles/PMC12030945/
[G1]: https://www.garmin.com/en-AU/blog/five-factors-garmin-sleep-coach-uses-to-find-your-sleep-needs/
[G2]: https://www8.garmin.com/manuals/webhelp/GUID-4A2FC8FE-7025-4AEC-946E-097B31131B45/EN-US/GUID-70D41BFB-2BB2-4933-BF95-47FF63140112.html
[V1]: https://academic.oup.com/sleepadvances/article/6/2/zpaf021/8090472
[E1]: https://www.eightsleep.com/autopilot/
[E2]: https://doi.org/10.3390/bioengineering11040352
[E2P]: https://mdpi-res.com/d_attachment/bioengineering/bioengineering-11-00352/article_deploy/bioengineering-11-00352.pdf
[E3]: https://academic.oup.com/sleep/article/48/Supplement_1/A202/8135278
[E4]: https://www.eightsleep.com/blog/research-finds-the-pod-can-boost-sleep-and-cardiovascular-metrics-with-real-time-temperature-adjustments-based-on-your-sleep-stages/
[E5]: https://doi.org/10.3390/clockssleep7040055
[E5P]: https://pdfs.semanticscholar.org/e72b/fb35cfa5aeb7671d58cf6d6cc483ebc42b79.pdf
[X1]: https://fullpower.com/news/2026/fullpower-ai-deploys-an-ai-world-model-for-human-biological-and-environmental-systems
