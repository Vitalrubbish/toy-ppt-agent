# PPT-Agent 优化方案与路线图

本文档记录了基于当前 PPT-Agent 原型的高优先级优化方向，旨在提升生成的稳定性、逻辑质量以及视觉一致性。

## 1. 优化工作流：引入 "思维链 (Chain of Thought)" 与 "大纲先行"

**问题描述**:
当前 Editor Agent 直接从长文本生成完整的 `slides.md` 代码，容易导致幻灯片逻辑混乱、分页不合理、或者关键内容遗漏。一次性生成过多代码也增加了 LLM 幻觉的风险。

**优化思路**:
将生成过程分解为多阶段任务，采用 "大纲 -> 内容 -> 代码" 的渐进式生成策略。

**实施计划**:
1.  **拆分 Editor 职责**:
    *   **Phase 1 (Outline)**: 接受长文本，输出 JSON 格式的幻灯片大纲（包含 `title`, `key_points`, `suggested_layout`）。
    *   **Phase 2 (User/Critic Review)**: 允许用户或 Critic 对大纲进行确认或调整（可选）。
    *   **Phase 3 (Generation)**: 根据确认的大纲，逐页或批量生成 Slidev Markdown 代码。
2.  **Prompt 调整**:
    *   为 Editor 增加 `generate_outline` 和 `generate_slides_from_outline` 方法。

## 2. 增强稳定性：增加 "语法预检 (Syntax Linter)" 环节

**问题描述**:
`slidev export` 对 Markdown 文件的语法错误非常敏感（例如未闭合的 HTML 标签、错误的 Frontmatter 格式、代码块围栏缺失）。渲染失败会导致整个迭代流程中断，浪费 Token 和时间。

**优化思路**:
在调用 Slidev 渲染器之前，引入一个中间层进行代码质量检查。

**实施计划**:
1.  **开发 `src/utils/linter.py`**:
    *   实现基于规则的检查逻辑（Python 脚本）。
    *   **检查项**:
        *   分页符 `---` 是否存在。
        *   代码块 ` ``` ` 是否成对闭合。
        *   HTML 标签（如 `<div>`）是否平衡。
        *   Frontmatter 格式是否合法。
2.  **集成到 `main.py`**:
    *   在 `editor.generate` 或 `refine` 之后，立即运行 Linter。
    *   如果发现 Critic 级别的语法错误，**不进行渲染**，直接自动构建 Feedback 发回给 Editor 要求修正（Self-Correction）。

## 3. 提升修改精度：从 "全文重写" 转向 "增量修补 (Local Refinement)"

**问题描述**:
目前的 `refine_slides` 方法要求 LLM 在每一轮迭代中返回完整的全文。随着 PPT 页数增加：
1.  Context Window 压力增大。
2.  LLM 容易在重写过程中丢失之前已经优化完美的细节（"灾难性遗忘"）。
3.  修改响应速度变慢。

**优化思路**:
实现基于页面的局部更新机制。

**实施计划**:
1.  **解析与分割**:
    *   编写工具函数，能够将 `slides.md` 解析为 `List[SlidePage]` 对象。
2.  **定位修改**:
    *   利用 Critic 返回的 `page_index` 定位到具体的 Slide Chunk。
3.  **局部重写**:
    *   Editor 新增 `refine_page(slide_content, issue)` 方法，只针对单页代码进行修复。
4.  **重新组装**:
    *   将修复后的片段拼回全文。

## 4. 视觉优化：构建 "设计规范系统 (Design System)"

**问题描述**:
Editor 和 Critic 目前缺乏统一的视觉标准。Editor 容易生成杂乱的内联样式，Critic 的反馈往往过于主观（"不好看"），缺乏可执行的标准。

**优化思路**:
利用 Slidev 的 UnoCSS 特性，建立一套标准的设计规范，并将其注入到 Agent 的 Context 中。

**实施计划**:
1.  **定义样式库**:
    *   在 `assets/` 或 System Prompt 中定义推荐的 CSS/UnoCSS 类组合。
    *   例如：
        *   `Heading`: `text-4xl font-bold text-primary`
        *   `Highlight`: `bg-yellow-200 dark:bg-yellow-800 px-1 rounded`
2.  **Prompt 增强**:
    *   在 Editor 的 System Prompt 中强制约束其使用预定义的 Class 类名，禁止使用 Raw CSS (`style="..."`)。
    *   在 Critic 的 System Prompt 中加入具体的视觉检查清单（例如：是否使用了规定的标题尺寸？颜色对比度是否符合规范？）。

## 5. 多媒体资源集成：支持用户自定义图片与动画

**问题描述**:
目前 Editor 仅能处理文本，生成的幻灯片虽然结构清晰但视觉单调。无法有效利用用户拥有的高质量素材（如产品演示视频、架构图、Logo），限制了 PPT 的表现力。

**优化思路**:
建立"资源感知 (Asset-Aware)" 机制，让 Editor Agent 知晓本地可用的媒体资源及其语义含义，并在生成 Slidev 代码时自动引用。

**实施计划**:
1.  **资源库建设**:
    *   在 `assets/user_uploads/` 下集中管理用户文件。
    *   要求用户（或通过脚本）提供 `manifest.json`，描述资源内容。
        *   Example: `{"demo_v1.mp4": "产品核心功能演示动画", "arch_diagram.png": "系统整体架构图"}`
2.  **Context 注入**:
    *   在 Editor 的 System Prompt 中动态插入"可用资源列表"（Available Assets）。
    *   Prompt 示例: "You have access to the following assets: 'demo_v1.mp4' (Description: Product Demo). Use them where appropriate."
3.  **代码生成适配**:
    *   指导 Editor 使用 Slidev 的标准语法引用资源：
        *   图片: `![Architecture Diagram](/user_uploads/arch_diagram.png)`
        *   视频: `<Video src="/user_uploads/demo_v1.mp4" controls />`
    *   确保公共路径配置正确（Slidev 可能需要配置 `public` 目录映射）。
