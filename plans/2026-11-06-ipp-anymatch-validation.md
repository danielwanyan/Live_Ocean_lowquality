# IPP v5实施与验证

用户基于2026-11-06人审校准批准任一挂品匹配、拍卖豁免、先确认卖货对象，再通过OpenCLI修改。

版本：2026-11-06-v5-ipp-any-match。33facts、20分类、所有节点I/O和10节点11边保持。

新增ipp_alignment为Judge内部JSON审计，Finalizer验证来源与索引、完整目录覆盖及身份材料，任一有效匹配/有证据的拍卖阻断IPP和8→20重判。未知身份或稀疏Segment编号不被误判。Validator独立检查审计结构、类别与来源语法，精确来源权限仍由可信Normalize清单下的Finalizer核验。

拍卖证据需kind为auction_sign、bidding_rules、active_bidding或auction_settlement，带来源和具体详情；不能因偶然出现auction一词豁免。新增信息依然是模型提供的可检查记录，不是人工GT，也不证明视觉理解正确。

源码285项测试通过，含18项新行为/契约回归；先执行失败，再实现。独立审查发现的缺失身份、无效图列表、拍卖词误判、Validator空根/类型/覆盖及稀疏Segment兼容性已补回归。

线上读回确认当前模型平台内置-GPT5.4、缓存true、两路Array<Image>，保留。运行和发布以当前structural/runtime gate为准；本文件记录本地验证，不声明新模型准确率。
