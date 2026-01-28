# PPT-Agent Optimization Plan

## 1. Current Problems

### 1.1. Syntax Compliance & Rendering Failures
- **Issue**: The Editor agent often generates Markdown that violates Slidev syntax rules.
    - Common errors: Invalid Frontmatter (YAML), missing `---` separators, wrapping the entire file in Markdown code blocks (```` ```markdown ... ``` ````), or using undefined layouts.
- **Consequence**: The `SlidevRunner` throws a `RenderError`.
- **Critical Flaw**: `src/main.py` **does not catch** `RenderError`. If the Editor generates invalid code, the entire pipeline crashes immediately without giving the agent a chance to fix it.

### 1.2. Low Presentation Quality
- **Issue**: The generated slides often have generic layouts (mostly default bullet points).
- **Cause**:
    - The `EditorAgent` system prompt is too generic ("transform raw text into beautiful... slides") without specific design directives or examples.
    - It lacks knowledge of advanced Slidev features (UnoCSS/Tailwind classes, specific components, complex layouts like `two-cols-header`).
- **Feedback Loop**: The `CriticAgent` reviews *rendered images*. If the slide looks "okay" but is boring, the Critic might pass it. If it fails to render, the Critic never sees it.

### 1.3. Weak Context & Feedback Utilization
- **Issue**: The Critic's feedback is sometimes too high-level ("Text overflow") without telling the Editor *how* to fix it technically (e.g., "Change layout to `two-cols`" or "Add `class: tex-sm`").
- **Issue**: The simple chat history mechanism might lose context or get confused if the feedback is vague.

### 1.4. Syntax Error Message Not Actionable to Editor
- **Issue**: When Slidev reports a syntax error (e.g., invalid frontmatter YAML, malformed separators), the agent doesn't reliably transform the raw error message into concrete edit instructions, so the Editor cannot use the error details to fix the Markdown.
- **Consequence**: The same error can recur across iterations, wasting cycles and preventing recovery.

## 2. Optimization Directions

### 2.1. Architecture: Robust Error Recovery (Priority High)
**Goal**: Prevent pipeline crashes due to syntax errors.
- **Action**: Modify `src/main.py` to wrap `runner.render_slides()` in a `try...except RenderError` block.
- **Logic**:
    1. If rendering fails, capture the error message (stderr).
    2. Skip the `CriticAgent` visual review.
    3. Treat the error message as "Critical Feedback".
    4. Feed this error back to the `EditorAgent` in the `refine_slides` step, explicitly asking it to fix the syntax error.

### 2.2. Prompt Engineering: Editor Enhancement
**Goal**: Improve aesthetic quality and syntax adherence.
- **Action**: Update `EDITOR_SYSTEM_PROMPT` in `src/agents/editor.py`.
- **Details**:
    - **Few-Shot Prompting**: Include examples of high-quality Slidev slides (Frontmatter + Content).
    - **Negative Constraints**: Explicitly forbid wrapping output in code fences (though `main.py` has a helper for this, it's better if the model obeys).
    - **Design Guidelines**: Instruct the model to use specific layouts (`two-cols`, `image-right`) and Tailwind classes (e.g., `class: 'text-center'`, `text-sm`) to improve visual appeal.
    - **Chain of Thought**: Ask the editor to first plan the slide structure before writing the code (implicit or explicit step).

### 2.6. PPT Quality: Concrete Code-Level Upgrades
**Goal**: Improve content presentation and aesthetics with deterministic, code-driven rules.

1. **Introduce a Slide Layout Selector (rule-based)**
    - **Where**: `src/agents/editor.py` (prompt + helper functions)
    - **What**: Map content types to layouts: `overview -> title`, `compare -> two-cols`, `process -> flow`, `data -> chart`, `image -> image-right`.
    - **How**: Add a lightweight classifier (regex + keywords) before composing slides, then inject `layout:` and section structure accordingly.

2. **Enforce Typography & Density Constraints**
    - **Where**: `src/agents/editor.py` + new `src/utils/slide_rules.py`
    - **What**: Hard caps: title <= 40 chars, bullets <= 5 per slide, each bullet <= 16 words.
    - **How**: Add a post-generation validator that rewrites long bullets into multiple slides and adds `class: 'text-sm'` when near limits.

3. **Auto-Insert Visual Tokens (emphasis & hierarchy)**
    - **Where**: `src/utils/slide_rules.py` (new) + editor prompt
    - **What**: Highlight key terms with `**bold**` and add `class: 'text-primary'` to lead bullets.
    - **How**: Detect keywords from source summary; add emphasis rules for first occurrence in each slide.

4. **Theme & Color Contrast Guardrails**
    - **Where**: `src/utils/slide_rules.py` + `rules/rules.md`
    - **What**: Enforce contrast-friendly palettes and forbid low-contrast classes (e.g., `text-gray-400` on white).
    - **How**: Validate used classes against an allowlist; auto-replace disallowed classes with safe alternatives.

5. **Component Insertion for Repetitive Structures**
    - **Where**: `src/agents/editor.py`
    - **What**: Use Slidev blocks/components like `columns`, `card`, `grid` for lists > 3 items.
    - **How**: Template expansion: if bullet list length > 3, render as 2-column grid with short phrases.

6. **Image Quality & Positioning Rules**
    - **Where**: `src/utils/slide_rules.py`
    - **What**: Standardize image sizes and alignment; avoid stretched images.
    - **How**: Normalize `class: 'w-3/5 mx-auto'` or `image-right` layout based on aspect ratio metadata when available.

7. **Micro-animations & Reveal Strategy**
    - **Where**: `src/agents/editor.py` (prompt)
    - **What**: Add `v-click` to step through dense slides.
    - **How**: Only apply to slides with 4–6 bullets to maintain pacing; never on titles.

8. **Automatic Slide Splitting & Merging**
    - **Where**: `src/utils/slide_rules.py` + `src/main.py`
    - **What**: Split slides that exceed density thresholds; merge two low-density slides.
    - **How**: Add a preprocessing step after `editor.generate_slides` and before render.

### 2.7. Rich Colors & Mermaid Diagrams (Framework Touchpoints)
**Goal**: Make slides more colorful and auto-generate Mermaid visuals where appropriate.

1. **Color Palette Tokens (Theme-Level)**
    - **Where**: `rules/rules.md` + `src/agents/editor.py`
    - **What**: Define a small set of named palette tokens (e.g., `primary`, `accent`, `success`, `warning`) and enforce usage across slides.
    - **How**: Add explicit prompt rules for color usage, and add allowlist validation in `slide_rules.py` to replace ad-hoc classes with palette tokens.

2. **Slide-Level Color Variation**
    - **Where**: `src/utils/slide_rules.py`
    - **What**: Auto-assign background/heading color variants to avoid monochrome decks.
    - **How**: Add a deterministic color rotation (by slide index or topic) and inject `class: 'bg-... text-...'` while ensuring contrast constraints.

3. **Mermaid Generation Heuristics**
    - **Where**: `src/agents/editor.py` (prompt + helper), `src/utils/slide_rules.py`
    - **What**: Convert “process/flow/relationship/architecture” sections into Mermaid blocks.
    - **How**: Use keyword detection to decide between `flowchart`, `sequenceDiagram`, `mindmap`, `graph TD`.

4. **Mermaid Style Preset**
    - **Where**: `rules/rules.md` + prompt in `src/agents/editor.py`
    - **What**: Enforce a consistent Mermaid theme (`theme: base`) and custom theme variables (node color, edge color, font).
    - **How**: Inject a `%%{init: { ... }}%%` header to every Mermaid block; validate that the header exists in `slide_rules.py`.

5. **Mermaid Rendering Safety**
    - **Where**: `src/utils/validator.py` (new) + `src/main.py`
    - **What**: Pre-check Mermaid blocks for syntax errors and missing headers before Slidev render.
    - **How**: Add regex checks for `graph`/`flowchart` keywords and balanced brackets; if fail, return actionable fixes to `EditorAgent`.

6. **Fallback Path When Mermaid Fails**
    - **Where**: `src/main.py` + `src/agents/editor.py`
    - **What**: If Mermaid block fails validation, replace with a styled bullet diagram template.
    - **How**: Create a minimal fallback template in editor prompt, and apply it automatically on validator failure.

### 2.3. New Component: Linter / Validator
**Goal**: Catch errors before rendering.
- **Action**: Create a simple regex-based or logic-based validator in Python.
- **Checks**:
    - Ensure every slide starts with `---`.
    - Validate Frontmatter YAML syntax.
    - Check for valid layout names.
- **Usage**: Run this validator immediately after generation. If it fails, auto-reject and ask for regeneration without even trying to call `slidev export`.

### 2.4. Agent Specialization
- **Refinement**: Split `CriticAgent` into two roles or phases:
    1.  **Code Critic**: Checks the Markdown code for structure and content density (can run on text, cheaper/faster).
    2.  **Design Critic**: Checks the rendered images for visual issues (current implementation).

### 2.5. Error-Driven Fix Instructions
**Goal**: Make syntax error feedback directly actionable for the Editor.
- **Action**: Add an “Error Interpreter” step before `refine_slides` that parses Slidev/Markdown/YAML errors and converts them into concrete fixes (e.g., “Add missing `---` before slide 3”, “Frontmatter key `theme` must be quoted”, “Remove code fences around the whole file”).
- **Implementation Idea**:
    1. Create a lightweight mapper (regex + rules) that recognizes common Slidev error patterns.
    2. Attach a structured patch plan to the feedback, e.g. `[{"issue":"missing_separator","fix":"insert --- before line 42"}]`.
    3. In `EditorAgent`, require applying the fix plan before any content rework.

## 3. Specific Implementation Roadmap

### Phase 1: Stability (Fixing Crashes)
1.  **Modify `src/main.py`**:
    - Add `try-except` around `runner.render_slides`.
    - If caught, construct a synthetic `feedback` object: `{"issue": "Render Error", "details": str(e), "severity": "CRITICAL"}`.
    - Pass this back to `editor.refine_slides`.

### Phase 2: Quality (Better Prompting)
1.  **Update `src/agents/editor.py`**:
    - Inject a "Style Guide" into the system prompt.
    - Force use of diverse layouts (limit `default` layout usage).

### Phase 3: Advanced Features
1.  **Add `validator.py`**: Implement pre-render checks.
2.  **Enhance Critic**: Teach the critic to suggest specific CSS classes or Layout changes.
