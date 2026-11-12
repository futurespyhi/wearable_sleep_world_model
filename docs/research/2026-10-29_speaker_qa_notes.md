# 10 月 29 日组会：讲稿 Q&A 备用 notes

- 用途：三位教授提问时的讲稿备查，不是 slides 正文。
- PSG 相关解释只保留在此处；四页 slides 不单独介绍术语。
- 以下为备用答法，按实际提问选用；不需要在主讲中逐条念。

## Q1. PSG 指什么？

PSG 是 polysomnography，即多导睡眠监测。它同步记录脑电、眼动、肌电、心率、呼吸和血氧等多种信号，提供比单一腕部设备更丰富的睡眠信息。

英文简答：

> PSG stands for polysomnography, an overnight recording of multiple physiological signals used to assess sleep. In a wearable prediction study, PSG-based scoring can provide the reference labels while the model receives only wearable measurements.

来源：[NIH/NHLBI Sleep Studies](https://www.nhlbi.nih.gov/health/sleep-studies)。

## Q2. 使用 PSG 标签，是否就等于模型使用了 PSG？

不等于。要分别说明输入和参考标签。腕表模型可以只接收腕部运动、心率等信息，以 PSG 的专业评分检验输出；直接接收脑电、呼吸等 PSG 通道的模型则是另一种信息条件。

英文简答：

> The input modality and the reference label are separate. A model evaluated against PSG labels does not necessarily have access to PSG signals at inference.

需要进一步说明时：标签是未来结果的监督，并不因为来自预测时刻之后就构成输入泄漏；问题在于模型或特征处理是否读到了当时不可获得的未来观测。数据划分和模型选择仍需独立处理。

## Q3. 多夜 EEG 头带标签可以直接写成完整 PSG 真值吗？

不能。应报告具体设备、自动标注和专家复核方式。例如 BIDSleep 的参考标签来自 Dreem 2 EEG，并含单一专家检查；其官方说明明确指出它不等同完整 PSG，也未进行多评分者裁决。这影响我们能声称的验证范围。

英文简答：

> We would report the reference measurement explicitly. EEG-headband labels and full PSG labels are different evidence sources, even when both use the same sleep-stage names.

来源：[BIDSleep v1.0.1，Methods / Reference Labels / Usage Notes](https://physionet.org/content/bidsleep-dataset/1.0.1/)。本轮只核查官方说明，尚未检查逐夜原始文件。

## Q4. 不同行为或模型的曲线不同，能说明干预有效吗？

仅靠曲线变化不能。模型在改变条件输入后产生另一条轨迹，首先说明它对条件敏感。要将其解释为某个行动的效果，还需要适当的数据设计、识别条件和验证。没有合格行动日志时，应把问题限定为事实预测或 past-only forecasting。

这与用户确认的研究原则一致：根据可核实事实决定任务和声明；不把记录到的行为换名为干预，也不为保持 world model 的称呼而放大证据。

## 后续并入正式讲稿

- PSG 解释和输入/标签区别放入备用 notes。
- 文献证据、候选研究问题和数据选择的主要结论放在正常讲稿中。
- slides 中保留必要的模态和标签名称即可，不新增 PSG 定义页或解释卡片。
