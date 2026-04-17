$ErrorActionPreference = "Stop"

$outputPath = Join-Path (Resolve-Path ".").Path "software-project-practicum\长篇实训报告评分研究设计完整总结.docx"
$outputDir = Split-Path -Parent $outputPath
if (-not (Test-Path $outputDir)) {
    New-Item -ItemType Directory -Path $outputDir | Out-Null
}

$content = @'
#TITLE 长篇实训报告评分研究设计完整总结
#SUBTITLE 围绕 Rubric 条件证据子图恢复与稳定可审计评分的阶段性总结文档

#H1 一、研究问题的最终收敛
最初的研究问题是：长文档被切片后，如何尽量减少跨片语义关系损失，并保持评分一致性。这个问题本身真实且重要，因为长篇学生实训报告通常包含需求规格说明、概要设计说明、详细设计说明等多个文档部分，而这些内容之间存在跨章节、跨页、跨片段的强依赖关系。一旦直接按固定窗口切片，原本完整的追踪链就可能被切断，导致模型只能看到局部信息，从而引发证据缺失、语义断裂和评分漂移。
但如果把“切片”本身直接当成论文主线，研究会过于工程化。因此，后续经过多轮压缩，我们将真正的论文主问题收敛为：在文档切片条件下，针对给定的 rubric item，如何恢复与该评分项相关的跨片证据子图，并基于该子图实现稳定、可审计的 item-level 自动评分。
因此，切片不再是论文的主角，而是问题设定；跨片语义保持不再停留在抽象口号，而被具体化为 evidence subgraph recovery；评分一致性不再是独立平行问题，而是证据子图恢复的下游验证任务。

#H1 二、论文主问题、主任务、子任务与应用目标
#H2 2.1 论文主问题
本文最终研究的问题可以表述为：在长篇实训报告因上下文限制被切分为多个文档片段的条件下，如何针对给定的评分项 rubric item，从局部可见证据中恢复其相关的跨片证据子图，并基于该子图实现稳定、可审计的 item-level 判分。
#H2 2.2 主任务
主任务为：Rubric-conditioned evidence subgraph recovery under document slicing。其含义是：在切片条件下，不恢复整篇文档的全局语义图，而是恢复与当前评分项直接相关、足以支撑该评分项判定的局部证据子图。
#H2 2.3 两个子任务
第一个子任务是 Trace recovery，即从切片后局部可见证据中恢复 item 相关的跨片追踪子图。第二个子任务是 Stability-aware scoring，即基于恢复出的证据子图进行 item-level 稳定评分。
#H2 2.4 应用目标
应用目标是面向长篇实训报告自动评分的可审计判分。系统不仅要给出评分结论，还要给出证据 span、跨片追踪路径、局部判断与全局仲裁依据，从而保证评分结果可回溯、可解释、可核查。

#H1 三、研究对象、最小研究单元与关系范围
#H2 3.1 最小研究单元
最小研究单元最终不定义为单个需求点，也不定义为单个评分项本身，而定义为：一个 rubric item 约束下的一条跨片追踪链。可形式化理解为 <rubric_item, requirement_node, design_node(s), implementation_node(s), evidence_spans, confidence>。换句话说，真正被研究的对象不是零散节点，而是与某个评分项判定直接相关的证据链结构。
#H2 3.2 核心关系类型
为了支撑 trace-intensive rubric item，论文核心关系类型应聚焦于需求、设计、实现和测试之间的追踪边。例如：requirement -> module、requirement -> page、requirement -> interface、requirement -> table、requirement -> class_or_method、requirement -> test_case、module -> page、module -> interface、module -> table、module -> class_or_method，以及 design_component -> implementation_artifact。
这些边足以支撑以“需求覆盖完整性”“设计与需求一致性”“实现落地完整性”“需求与测试对应性”为代表的评分项。反之，诸如语言表达、文档规范性、排版完整性等维度并不是当前方法的主战场，不宜在论文前期纳入主任务。
#H2 3.3 关系保持的任务性质
本文主任务不是潜在关系预测，而是已有关系恢复。也就是说，需求、设计与实现之间的关系原本就以文本、章节、对象名、图表标题、流程说明等形式存在于完整文档中，只是切片后被割裂。论文要解决的是如何在切片条件下将其恢复出来，而不是去猜测作者未写出的潜在联系。

#H1 四、输入输出形式化与图模型
#H2 4.1 输入定义
设原始长文档为 D，经切片后得到片段集合 C = {c1, c2, ..., cn}。每个切片 ci 不仅包含文本，还包含文档角色标签、章节层级、原文位置索引、主题标签等结构化元信息。设评分标准集合为 R = {r1, r2, ..., rm}，其中某个评分项记为 r。则系统在单个 item 下的输入可形式化为 x = (C, r, M)，其中 M 为全局辅助信息，包括术语表、别名映射、结构先验、合法边类型集合和节点类型约束等。
#H2 4.2 输出定义
对每个评分项 r，系统输出 y_r = (G_r, S_r, A_r)。其中 G_r 为与评分项相关的证据子图，S_r 为该 item 的评分结果，A_r 为审计对象。进一步可写为：G_r = (V_r, E_r)，S_r = (level_r, conf_graph_r, conf_level_r)，A_r 包含 evidence spans、recovered paths、local judgments、arbitration notes 等信息。最终系统还输出全局总分 S_final。
#H2 4.3 图模型定义
全局节点集合 V 由多类节点组成，包括需求节点、模块节点、页面节点、接口节点、数据库表节点、类/方法节点、测试用例节点等。每个节点包含唯一标识、类型、规范名、别名、所属文档角色、章节位置、原文 span 和属性信息。
边集合 E 由节点对、边类型、权重和证据集合构成。每条边表示一种跨片关系，如 requirement_to_module、requirement_to_interface、module_to_table 等。对于某一评分项 r，系统关注的不是全图，而是 item-conditioned 的证据子图 G_r。

#H1 五、候选图构建与关系恢复方法
论文的方法起点不是直接评分，而是先构建候选图。候选图构建采用混合式策略：首先进行节点抽取，识别需求、模块、页面、接口、表、类/方法、测试用例等语义节点；然后基于类型约束、结构先验和主题邻近性生成候选边；再结合词汇匹配、语义相似度、结构位置、角色信息和模型置信度对候选边进行综合评分；最后得到面向评分项的候选关系图。
因此，本文不采用“直接让大模型抽整图”的粗放思路，而是采用 rule + schema-guided extraction + constrained graph construction 的混合方法。这样做的目的在于保证节点与边的类型合法性、减少无效候选、提高可审计性，并为后续的最小充分证据子图解码提供干净的候选空间。

#H1 六、研究对象的收缩：只做 trace-intensive rubric items
论文前期不应追求覆盖全部 10 到 12 个 rubric item，否则会导致约束模板、标注方案和实验设计全部发散。当前方法明显更适合那些依赖跨片追踪链的维度，也就是 trace-intensive items。典型代表包括：需求覆盖完整性、设计与需求一致性、实现落地完整性、需求与测试用例对应性。
因此，一个合理的研究收缩策略是：先只选择 4 到 6 个核心追踪型 rubric item，并为每个 item 定义 item-specific 的约束模板和最小充分证据子图。这样既能突出研究重点，也有利于让方法从一开始就具备 trait-specific / rubric-specific 的特点，而不是试图用一个统一黑箱去吞掉所有评分维度。

#H1 七、“充分”的正式定义与最小充分证据子图
#H2 7.1 充分的正式定义
“充分”最终不定义为全局统一的槽位覆盖式，也不定义为全局统一的路径闭环式，而定义为 item-specific constraint-satisfaction sufficiency。也就是说，对于给定 rubric item，其最小充分证据子图必须满足该 item 对应的一组显式约束。不同 item 的充分性判定规则可以不同，这正是 rubric-conditioned 的真正含义。
#H2 7.2 解码目标
证据子图的正式解码目标定义为：带路径完整性约束的最小充分证据子图。它不是最大置信度子图，不是尽可能大的高相似子图，也不是简单的“召回后贪心裁剪”作为理论目标。真正的目标是：在候选关系图中，找到一个足以支撑该评分项判分、关键路径不断裂、整体规模尽量小且置信度尽量高的子图。

#H1 八、从约束类别到约束系统
仅仅说“有槽位约束、路径约束、冲突约束、证据约束”还不够，这只是约束类别，不是约束系统。真正的方法必须明确：哪些是硬约束，哪些是软约束；哪些决定档位上限，哪些只影响置信度；缺哪个约束会导致直接封顶，冲突出现后又如何影响最终档位。
因此，论文需要构建 item-specific constrained evidence decoding system。这个系统可以分成四层：第一层是 Structural hard constraints，用于判定子图是否合法；第二层是 Sufficiency hard constraints，用于决定档位上限；第三层是 Consistency soft constraints，用于在可达档位内进行细化和惩罚；第四层是 Evidence reliability constraints，用于估计证据可靠性并主要影响置信度。
这样，约束就不再是若干 if-else 规则的堆砌，而成为一个有明确逻辑层次的判定框架：先判断结构合法性，再判断充分性上限，再处理一致性惩罚，最后估计证据可靠性。

#H1 九、四档体系的唯一固定版本
为保证后续模板、封顶条件和置信度能够落地，论文最终固定采用唯一的四档体系：
第一档 D0：缺失。表示几乎没有形成有效追踪关系，或关键槽位缺失，无法支撑该 item 判分。
第二档 D1：弱覆盖。表示存在局部对应或局部证据，但没有形成稳定追踪链，证据薄弱或存在重大缺口。
第三档 D2：基本覆盖。表示已经形成主要追踪链，关键槽位基本齐全，可以支撑该 item 的基本成立，但仍存在证据不足、单视角支撑或局部冲突。
第四档 D3：完整覆盖。表示形成高置信、低冲突、可回溯的完整追踪结构，关键槽位齐全，证据充分，能够稳定支撑该 item 判分。
后续所有 item-specific 模板、冲突封顶条件和置信度定义都统一围绕这四档展开。

#H1 十、两个典型 trace-intensive item 的正式模板
#H2 10.1 Item A：需求与概要/详细设计一致性
槽位：
R：requirement 节点。
H：高层设计节点，如 module、page、high-level interface。
L：低层设计节点，如 detailed interface、table、class_or_method。
A：alignment evidence，表示 R 与 H/L 在功能、对象、流程、约束上的对应证据。
硬约束：
必须存在 R；必须存在至少一个有效 R -> H；若档位大于等于 D2，则必须存在 A；若档位为 D3，则必须同时存在 R -> H 且 H -> L 或 R -> L；若 requirement 仅与标题级节点对应、无正文支撑，则最高只能到 D1。
软约束：
多视角一致性优于单视角；流程一致性支撑优于仅名称一致；约束一致性支撑优于仅功能名一致；跨文档角色支撑优于同一局部片段自我重复；多条独立路径优于单一路径。
冲突封顶条件：
semantic_drift 封顶 D1；constraint_violation 封顶 D1；path_conflict 封顶 D2；over_design_major 封顶 D2；entity_mismatch_major 封顶 D1。
四档可达条件：
D0：无 R 或无有效 R -> H。
D1：有 R、有局部 R -> H，但无稳定 A，或触发重大语义冲突。
D2：存在稳定对齐关系，且至少具备 R + H + (A 或 L)，但只有单视角支撑、低层落地不足或存在中等冲突。
D3：R/H/L/A 全部满足，至少存在一条高置信一致性路径，无重大冲突，证据充分且跨片可回溯。
#H2 10.2 Item B：需求与实现落地完整性
槽位：
R：requirement 节点。
D：设计承接节点，如 module、page、interface design。
I：实现导向节点，如 concrete interface、table、class_or_method、testcase。
E：execution evidence，表示需求已落到可实现对象上的证据。
硬约束：
必须存在 R；必须存在至少一个有效 R -> D；若档位大于等于 D2，则必须存在至少一个有效闭环 R -> D -> I 或强支撑的 R -> I；若档位为 D3，则必须同时满足 R、D、I、E 全部存在；若仅有设计描述、无实现导向节点，则最高只能到 D1。
软约束：
多个实现导向节点共同支撑优于单一实现节点支撑；闭环路径数量越多越好；不同实现视角一致支撑更优；证据 span 越具体越好；关键边平均权重越高越好。
冲突封顶条件：
missing_implementation 封顶 D1；semantic_drift 封顶 D1；broken_closure 封顶 D1；implementation_conflict 封顶 D2；evidence_thin_major 封顶 D1。
四档可达条件：
D0：无 R 或无有效 R -> D。
D1：有 R -> D，但无有效 R -> D -> I，或触发 missing_implementation、broken_closure、证据极薄等重大问题。
D2：存在至少一条有效 R -> D -> I，且 R/D/I 基本齐全，但 E 不足、支撑视角单一或存在中等冲突。
D3：R/D/I/E 全部满足，至少一条高置信闭环路径，最好有多实现视角支撑，无重大冲突，证据充分，可稳定支撑“已落地”的判断。

#H1 十一、子图解码与档位判分的连接方式
对于“子图解码和档位判分如何连接”这一问题，论文明确选择第一条路线：先解码最小充分子图，再按约束映射到档位。也就是说，系统不会直接基于候选图做多档分类并隐式完成子图选择，而是先恢复 item 对应的最小充分证据子图，再检查约束系统，从而得到档位可达性判断。
这一选择有三个理由。第一，它更符合主任务“evidence subgraph recovery”的上游核心地位。第二，它更符合可审计目标，因为评分结果可以明确回溯到具体子图和约束检查过程。第三，它更符合约束系统的逻辑，因为档位本身应当由结构合法性、充分性上限、冲突情况和证据可靠性共同决定，而不是由一个黑箱分类器直接给出。

#H1 十二、置信度定义：双层置信度
conf_r 最终不采用单一置信度，而采用双层置信度：
第一层为子图恢复置信度 conf_graph_r，用于衡量恢复出的最小充分证据子图是否可靠。它受关键节点和边的平均置信度、路径完整性、证据 span 充分性、关键槽位是否由独立证据支撑以及重大冲突等因素影响。
第二层为档位判分置信度 conf_level_r，用于衡量在给定证据子图的前提下，当前四档判分是否稳定。它受档位边界裕量、约束满足程度、软约束惩罚是否逼近阈值、切片扰动下档位是否稳定、多次运行下档位是否一致等因素影响。
采用双层置信度的原因在于，子图恢复和档位判分是两个不同阶段。一个 item 可能出现“图恢复较可靠，但档位边界不清晰”的情况，也可能出现“图恢复不可靠，因此档位不应自信”的情况。若把两者混成一个数，会丢失非常重要的审计信息。

#H1 十三、精品标注集与数据方案
精品标注集不能只标节点和边，否则只能评估信息抽取，无法真正支持 item-level 判分任务。较合理的精品集标注粒度应包括四层：节点层、边层、子图层和解释层。
节点层标需求、模块、页面、接口、表、类/方法等节点及其原文 span；边层标节点之间的关系类型与支撑证据；子图层标每个核心 rubric item 的最小充分证据子图；解释层标 item-level 分数、判分理由、缺失类型和冲突类型。
其中最关键的 gold 对象不是零散节点和边，而是“item 对应的最小充分证据子图”。因为这才是论文主任务真正要恢复的对象。
数据规模方面，比较现实的硕士论文配置是：180 份实训报告，每份包含需求、概要、详细设计三类文档；其中 50 份构成精品集，做 item-level 证据子图和判分解释标注；其余 130 份可作为弱标注集，仅保留 item-level 教师评分。若资源紧张，可压缩为 120 份总报告、30 份精品集、90 份弱标注集。

#H1 十四、评价指标与实验设计
论文评价将围绕三个层面展开。第一层是子图恢复质量，包括节点抽取 F1、边恢复 Precision、Recall、F1，以及路径恢复率 PathRecall。第二层是评分性能，包括 item-level 的 MAE、Spearman、QWK，以及总分 MAE。第三层是稳定性，包括不同切片策略下 item-level 分数方差、同配置多次运行的方差，以及 PathRecall 与评分误差之间的相关性。
除了常规方差实验，论文还应加入切片扰动鲁棒性实验。具体做法是：固定文档与评分项，人为制造切片边界平移、overlap 大小变化、章节拆碎或合并等扰动，观察证据子图恢复和 item score 是否保持稳定。这样才能说明方法不是只在某一种切片策略上表现好，而是对切片扰动本身更鲁棒。
在消融实验中，还必须证明改进来自跨片关系建模，而不只是“多喂了更多上下文”。为此，应比较：仅结构切片、结构切片加更多 overlap、结构切片加显式关系边、结构切片加关系边但无全局仲裁、完整方法等多种配置，并尽量控制总 token 预算一致。

#H1 十五、当前毕业论文的总方法框架
基于以上讨论，论文的总方法框架已经比较稳定，可以概括为以下五步：
第一步，候选图构建。
第二步，item-specific 约束模板实例化。
第三步，最小充分证据子图解码。
第四步，约束检查与档位可达性判断。
第五步，置信度估计与审计输出。
如果按论文化的层级划分，这个框架又可以分为三层。第一层是任务建模层，包括问题定义、输入输出形式化和候选图表示；第二层是核心方法层，包括约束模板、证据子图解码和档位可达性判断；第三层是评分与解释层，包括双层置信度、审计输出以及稳定性实验。
这说明当前研究已经不再只是“做一个批改系统”，而是形成了一个以证据子图恢复为核心、以稳定评分为下游验证、以可审计判分为应用目标的任务型方法论文框架。

#H1 十六、自由文本评分规则到 YAML 的辅助模块说明
为提升系统对不同学科、不同作业类型的适应性，本文在系统实现中设计了一个自由文本评分规则到标准 YAML rubric 的转换模块。教师可通过自然语言自由描述评分要求，系统再结合强约束 schema、分阶段解析与自动校验机制生成结构化 rubric 文件。这样做的目的不是改变本文的核心研究问题，而是降低教师配置评分规则的门槛，增强系统在真实教学场景中的可用性。
从系统分层角度看，该模块属于 Rubric 输入层辅助模块，位于评分执行层之前。它主要负责把教师自由撰写的评分规则转换为统一的结构化配置，使后续的 item-specific 约束模板实例化、证据子图解码和档位判分模块能够在标准化 rubric 输入上工作。
需要明确的是，该模块不作为本文的核心研究问题，也不纳入核心算法实验评价。本文真正的主任务仍然是在给定结构化 rubric 的前提下，研究文档切片条件中的证据子图恢复与稳定、可审计的 item-level 判分。因此，自由文本到 YAML 的模块应被理解为提升系统可部署性和跨学科适应性的辅助能力，而不是替代核心评分方法的研究主线。

#H1 十七、最终总体判断
综合全部讨论，当前这条研究路线已经具备硕士论文所需的几个关键特征：研究问题明确，方法主线清晰，任务分解合理，实验目标可执行，应用场景真实，且具有一定的新颖性。真正值得坚持的总路线可以概括为：
围绕少量 trace-intensive rubric item，定义 item-specific 约束模板；在文档切片条件下，从候选关系图中解码带路径完整性约束的最小充分证据子图；再通过约束检查、档位可达性判断和双层置信度估计，实现稳定、可审计的 item-level 自动评分。
从这个意义上说，当前研究框架已经从“工程流程描述”收缩为“可写论文的问题定义与方法设计”。如果后续继续围绕约束模板实例化、子图解码算法、档位许可机制、双层置信度估计和鲁棒性实验展开，这条路线完全有可能支撑一篇结构完整、问题聚焦、实验扎实的计算机专业硕士学位论文。
'@

$lines = $content -split "`r?`n"
$word = $null
$document = $null

try {
    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    $document = $word.Documents.Add()
    $selection = $word.Selection

    foreach ($line in $lines) {
        $trimmed = $line.Trim()
        if (-not $trimmed) {
            $selection.TypeParagraph()
            continue
        }

        if ($trimmed.StartsWith("#TITLE ")) {
            $selection.Style = "标题 1"
            $selection.ParagraphFormat.Alignment = 1
            $selection.TypeText($trimmed.Substring(7))
            $selection.TypeParagraph()
            continue
        }

        if ($trimmed.StartsWith("#SUBTITLE ")) {
            $selection.Style = "正文"
            $selection.Font.Size = 11
            $selection.ParagraphFormat.Alignment = 1
            $selection.TypeText($trimmed.Substring(10))
            $selection.TypeParagraph()
            $selection.TypeParagraph()
            continue
        }

        if ($trimmed.StartsWith("#H1 ")) {
            $selection.Style = "标题 1"
            $selection.ParagraphFormat.Alignment = 0
            $selection.TypeText($trimmed.Substring(4))
            $selection.TypeParagraph()
            continue
        }

        if ($trimmed.StartsWith("#H2 ")) {
            $selection.Style = "标题 2"
            $selection.ParagraphFormat.Alignment = 0
            $selection.TypeText($trimmed.Substring(4))
            $selection.TypeParagraph()
            continue
        }

        if ($trimmed.StartsWith("- ")) {
            $selection.Style = "正文"
            $selection.ParagraphFormat.Alignment = 0
            $selection.TypeText("• " + $trimmed.Substring(2))
            $selection.TypeParagraph()
            continue
        }

        $selection.Style = "正文"
        $selection.ParagraphFormat.Alignment = 0
        $selection.ParagraphFormat.CharacterUnitFirstLineIndent = 2
        $selection.TypeText($trimmed)
        $selection.TypeParagraph()
    }

    if (Test-Path $outputPath) {
        Remove-Item -LiteralPath $outputPath -Force
    }

    $wdFormatXMLDocument = 12
    $document.SaveAs([string]$outputPath, $wdFormatXMLDocument)
    Write-Output $outputPath
}
finally {
    if ($document -ne $null) {
        $document.Close()
    }
    if ($word -ne $null) {
        $word.Quit()
    }
    [System.GC]::Collect()
    [System.GC]::WaitForPendingFinalizers()
}
