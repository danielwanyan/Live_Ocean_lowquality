# IPP任一匹配优先 — 已获用户实施授权

用户已评审200直播间GT诊断及节点级方案，并要求通过OpenCLI/Test Chrome修改。保留33个事实、20分类、Start/Output字段及10节点11边，GT原件不改。

1. 以现有271项通过的测试为基线，先增加行为回归：任一有效匹配、拍卖证据、非卖货、全货盘覆盖、非法引用、8→20不可复活。
2. 在Judge既有boundary_checks里加入ipp_alignment；Finalizer校验结构及来源，落实匹配/拍卖豁免，无审计不能命中IPP。同步规则、fallback、版本、Judge模板及Gate schema。
3. 用真实源病例验证代码行为；保持旧GT与串珠复核建议分离，不能把注入匹配审计的离线回放叫作新版模型结果。
4. 更新wiki镜像/registry契约、代码和提示词摘要，提交源规则到独立分支，HTTP固定到明确commit，不改已发布main。
5. 预检、官方unbind、tab-discover/bind-exact/canvas-audit；逐节点node-apply并即时回读，完整重载和全部契约审计。
6. 单Run有界验证关键误伤、拍卖及已授权正例。runtime/structural gate实际通过后workflow-publish；完成OCL-15。旧租约managed_resource_conflict期间停止所有浏览器写操作，用户完整退出后再恢复。
