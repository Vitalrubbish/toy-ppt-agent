# Editor Agent Specification (Proposer)

## 职责
负责 PPT 内容的生成和 Slidev 代码的编写与修改。

## 继承
继承自 `BaseAgent`。

## 核心方法

### `generate_draft(self, raw_content: str) -> str`
*   **输入**: 原始长文本（论文摘要、文章等）。
*   **输出**: 完整的 `slides.md` 内容。
*   **Prompt 策略**:
    *   提供 Slidev 基础语法的 Few-Shot 示例。
    *   要求逻辑分片：Title Page -> Outline -> Content Pages -> Conclusion -> Ref/Thanks。
    *   强制使用 `---` 分隔符。

### `refine_slides(self, current_code: str, feedback: List[Dict]) -> str`
*   **输入**: 当前的 `slides.md` 代码，以及 Critic 的反馈列表。
*   **输出**: 修改后的 `slides.md` 代码。
*   **逻辑**:
    *   **Chain-of-Thought**: 先思考如何根据反馈修改代码，再执行修改。
    *   **Input Context**: "这是当前的代码：\n...\n 这是收到的反馈：\n..."
    *   **Response**: 只返回修改后的完整代码（或 Diff，视 Context 长度而定，推荐初期返回完整代码以降低复杂度）。

## Prompt Design (System Prompt)
> You are an expert Slidev Developer and Presentation Designer.
> Your task is to transform raw text into beautiful, structured Slidev markdown slides.
>
> Rules:
> 1. Use `---` to separate slides.
> 2. Use Frontmatter for layout (e.g., `layout: two-cols`).
> 3. Keep text concise. Use bullet points.
> 4. Ensure code syntax is correct Slidev markdown.
> 5. Always add a dedicated Title Slide as a standalone slide (first slide) for title, subtitle, author/affiliation, date.
> 6. Do NOT assume the frontmatter will render as a title page. If a title page is required, create an explicit slide after the frontmatter.
> 7. `layout` only works inside a slide’s frontmatter block. Place it immediately after `---`.
> 8. Do not mix multiple layout declarations in a single slide; create a new slide instead.
> 9. For two-column layouts, use `layout: 2-cols` and `::right::` blocks correctly.
>
> When receiving feedback, strictly follow the suggestions to fix visual issues (e.g., reducing word count, splitting slides).

## 状态管理
*   Editor 在 `refine` 阶段不仅需要知道"要改什么"，还需要"原来的代码是什么"。
*   为了防止 Context 污染，建议每次 Refine 构建一个新的 Prompt，包含 `Current Code` + `Critique Instructions`，而不是在一个持续的 Conversation 中追加。
