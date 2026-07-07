# REFLECTION

本项目选择 Coding Agent Harness，是因为它能最直接地回答课程反复强调的问题：当 LLM 已经可以给出相当多代码建议时，工程师的价值具体落在哪里。我的结论是，价值主要落在把不稳定的模型输出包进一个可验证、可治理、可分发的系统里。Aegis Code Harness 的实现规模不大，但它刻意把主循环、动作解析、工具分发、护栏、反馈、记忆、配置、凭据与分发都写成普通代码，并且用 mock LLM 测试这些机制。

Superpowers 方法论中最有价值的部分是 brainstorming 和 test-driven-development。brainstorming 的作用不是替我决定题目，而是迫使我把“harness 到底是什么”拆开：动作是什么、危险动作是什么、反馈信号是什么、记忆如何进入上下文、哪些规则必须是代码。最重要的问题是：移除真实 LLM 以后，这个机制还能否被单测验证？这个问题直接改变了项目形态。如果只在 system prompt 中写安全要求和自检要求，那几乎没有工程含量。于是我把危险动作识别写成 `GuardrailEngine.check()`，把反馈写成 `FeedbackSensor.collect()`，把主循环写成 `AgentLoop.run()`。这些都可以直接构造对象测试，不需要真实 API，也不依赖模型是否听话。

TDD 在这个项目中是放大器。编码智能体很容易先给出一个看似完整的实现，再补一些没有约束力的测试。这里我反过来从可验证机制出发：先写 parser、guardrail、memory、credential、agent loop 的测试，再补实现。尤其是反馈闭环测试，它要求 mock LLM 第一次写出坏的 `hello.py`，`py_compile` 失败后，第二次写出修复版本，最后 finish。这个测试让“反馈回灌”从一个口号变成了可观察行为。TDD 的阻碍主要是前期速度变慢，但它减少了后面解释不清的风险。

subagent-driven 工作流对 task 粒度有要求。最合适的 task 是“一个机制 + 一组测试 + 明确文件路径”，例如 guardrail、feedback、credentials。过大的 task 会让智能体混在一起改很多文件，评审困难；过小的 task 只是在机械搬运代码。PLAN 中把 parser、guardrail、tool/feedback、agent loop、memory/config、credentials、WebUI/CI 分开，是比较适合的颗粒度。实际开发中，如果继续严格执行 worktree，每个 task 可以对应一个短 PR，评审时先看 spec 合规，再看代码质量。

SPEC / PLAN 的质量直接影响实现质量。一个具体例子是“人工审批”。最初只写“危险动作暂停等待人工审批”，冷启动阅读时会产生歧义：到底要实现完整的交互式审批服务器，还是返回一个停止状态即可？如果不写清楚，subagent 很可能实现一个复杂但不必要的状态机，甚至把审批绕回 prompt。修订后，SPEC 明确 v0.1 的行为是返回 `approval_required`，机制演示中确定性复现暂停；完整审批 UI 作为未来扩展。这个修改让实现范围更稳定。

最有效的 prompt/context 策略是把模型要做的事限定到“下一步 JSON action”，其余由 harness 执行。Aegis 的 system prompt 很短，只规定 action 格式。安全、反馈、记忆都不靠 prompt 保证。这样做的好处是模型响应更容易解析，错误也更容易变成 observation 反馈。另一条有效策略是只给模型相关 memory，而不是把全量历史塞进上下文。当前实现用 lexical search，很朴素，但可预测、可测试。

凭据与分发要求迫使我考虑“别人如何在新机器上运行”。如果只做课堂 demo，很容易把 key 放进环境变量甚至代码里。这里实现了带主密码的加密文件作为便携 fallback，并在 README 说明 `.env` 和环境变量的明文风险。分发方面，Dockerfile 使 WebUI 可以用一条命令启动，CI 同时跑单元测试和容器构建。虽然这个容器不是强安全沙箱，但它提供了可复现实验环境。

如果重做，我会把治理维度继续做深：增加结构化 approval queue、命令能力白名单、容器隔离、审计日志签名，以及 per-tool policy。反馈维度也可以增强为失败分类器，例如把 syntax error、test failure、timeout、permission error 分开，并用不同模板回灌给模型。记忆可以增加确定性索引和可解释检索结果。WebUI 当前只是机制演示入口，未来可以做成真正的任务控制台。

对 Superpowers 的批判是，它假设开发者愿意并且有能力持续做审查。对于简单项目，这套流程显得重；但对于 agentic SE，它的保守性是必要的。LLM 可以生成很多内容，但它不会天然知道哪些行为应该被禁止、哪些结果才算客观正确、哪些凭据不能泄露、哪些部署方式能在别人机器上复现。这个项目的体验说明，可靠的软件工程仍然来自清晰规约、可执行计划、可重复测试、明确边界和审查纪律。AI 可以加速实现，但不能替代这些判断。
