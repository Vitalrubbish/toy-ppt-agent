import json
import os
import shutil
import time
from pathlib import Path
from typing import List

import typer
from dotenv import load_dotenv

from agents.editor import EditorAgent
from agents.critic import CriticAgent
from utils.slidev_runner import SlidevRunner, RenderError


app = typer.Typer(add_completion=False)


def read_text_file(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def write_text_file(path: str, content: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def ensure_dir(path: str) -> None:
    Path(path).mkdir(parents=True, exist_ok=True)


def clear_dir(path: str) -> None:
    if Path(path).exists():
        shutil.rmtree(path)
    Path(path).mkdir(parents=True, exist_ok=True)


def strip_code_fence(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if len(lines) >= 2 and lines[0].startswith("```") and lines[-1].strip() == "```":
            return "\n".join(lines[1:-1]).strip() + "\n"
    return text

def is_approved(feedback: List[dict]) -> bool:
    return not feedback


@app.command()
def run(
    input_path: str = "data/paper_summary.txt",
    output_dir: str = "outputs",
    max_iterations: int = 5,
    model_name: str = "gpt-4o",
    mode: str = typer.Option("single", help="Mode: 'dual' (Editor+Critic) or 'single' (Editor self-review)"),
):
    """Run the PPT-Agent pipeline."""
    load_dotenv()
    start_time = time.time()

    raw_content = read_text_file(input_path)

    default_model = model_name or "gpt-4o"

    editor_provider = os.getenv("EDITOR_LLM_PROVIDER") or os.getenv("LLM_PROVIDER", "openai")
    critic_provider = os.getenv("CRITIC_LLM_PROVIDER") or os.getenv("LLM_PROVIDER", "openai")

    editor_model = os.getenv("EDITOR_LLM_MODEL") or os.getenv("LLM_MODEL") or default_model
    critic_model = os.getenv("CRITIC_LLM_MODEL") or os.getenv("LLM_MODEL") or default_model

    if os.getenv("EDITOR_LLM_MODEL") is None and os.getenv("LLM_MODEL") is None:
        if editor_provider == "openai":
            editor_model = "gpt-4o"
        else:
            print("模型未指定，供应商不是OpenAI")
            exit(1)

    if os.getenv("CRITIC_LLM_MODEL") is None and os.getenv("LLM_MODEL") is None:
        if critic_provider == "openai":
            critic_model = "gpt-4o"
        else:
            print("模型未指定，供应商不是OpenAI")
            exit(1)

    editor = EditorAgent(model_name=editor_model, provider=editor_provider)
    critic = None
    if mode == "dual":
        critic = CriticAgent(model_name=critic_model, provider=critic_provider)
    runner = SlidevRunner(work_dir=str(Path(__file__).resolve().parents[1]))

    if mode == "dual":
        output_dir = os.path.join(output_dir, "dual_output")
    else:
        output_dir = os.path.join(output_dir, "single_output")

    current_dir = os.path.join(output_dir, "current")
    history_dir = os.path.join(output_dir, "history")
    logs_dir = os.path.join(output_dir, "logs")
    images_dir = os.path.join(current_dir, "images")
    
    ensure_dir(current_dir)
    ensure_dir(history_dir)
    ensure_dir(logs_dir)

    feedback: List[dict] = []
    slides_md = ""
    outline_md = ""
    last_success_md = ""
    last_render_error: str | None = None
    need_fix = False

    run_stamp = time.strftime("%Y%m%d_%H%M%S")
    run_log_path = os.path.join(logs_dir, f"run_{run_stamp}.log")

    def append_run_log(message: str) -> None:
        line = f"[{time.strftime('%H:%M:%S')}] {message}\n"
        with open(run_log_path, "a", encoding="utf-8") as f:
            f.write(line)
        typer.echo(message)

    # Outline
    append_run_log("Editor: generating outline")
    outline_md = editor.generate_outline(raw_content)
    outline_log_path = os.path.join(logs_dir, f"outline_{run_stamp}.md")
    outline_path = os.path.join(current_dir, "outline.md")
    write_text_file(outline_log_path, outline_md)
    write_text_file(outline_path, outline_md)
    append_run_log(f"Outline saved to {outline_path}")

    if not typer.confirm("Outline generated. Start iteration?", default=True):
        append_run_log("User stopped after outline generation.")
        typer.echo(f"Outline saved at {outline_path}")
        return


    # Editor: Slides
    for iteration in range(1, max_iterations + 1):
        append_run_log(f"Iteration {iteration}/{max_iterations} started")

        # slides.md
        if iteration == 1:
            append_run_log("Editor: generating draft")
            slides_md = editor.generate_draft(raw_content, outline=outline_md)
        elif need_fix:
            append_run_log("Editor: fixing slides after render error")
            slides_md = editor.fix_slides(slides_md, last_render_error or "")
        else:
            append_run_log("Editor: refining slides")
            slides_md = editor.refine_slides(slides_md, feedback)

        slides_md = strip_code_fence(slides_md)

        editor_log_path = os.path.join(logs_dir, f"iter_{iteration}_editor.txt")
        editor_output = editor.last_response or slides_md
        write_text_file(editor_log_path, editor_output)
        append_run_log(f"Editor output saved to {editor_log_path}")

        # Render
        slides_path = os.path.join(current_dir, "slides.md")
        candidate_path = os.path.join(current_dir, "slides_candidate.md")
        write_text_file(candidate_path, slides_md)
        rendered_log_path = os.path.join(logs_dir, f"iter_{iteration}_rendered.md")
        write_text_file(rendered_log_path, slides_md)
        append_run_log(f"Rendered markdown saved to {rendered_log_path}")

        append_run_log("Rendering slides to images")
        clear_dir(images_dir)
        image_paths = []
        render_error = None
        try:
            image_paths = runner.render_slides(candidate_path, images_dir)
        except RenderError as e:
            render_error = str(e)
            append_run_log("Render failed. Sending error back to editor for fixes")

        if render_error:
            need_fix = True
            last_render_error = render_error
            feedback = [
                {
                    "issue": "Render Error",
                    "details": render_error,
                    "severity": "CRITICAL",
                }
            ]
            critic_log_path = os.path.join(logs_dir, f"iter_{iteration}_critic.txt")
            write_text_file(critic_log_path, json.dumps(feedback, ensure_ascii=False, indent=2))
            append_run_log(f"Render error logged to {critic_log_path}")
        else:
            need_fix = False
            last_render_error = None
            last_success_md = slides_md
            write_text_file(slides_path, slides_md)
            append_run_log(f"Rendered {len(image_paths)} slide images")

            if mode == "dual":
                append_run_log("Critic: reviewing slides")
                feedback = critic.review(image_paths, slides_md=slides_md)
                critic_log_path = os.path.join(logs_dir, f"iter_{iteration}_critic.txt")
                critic_output = critic.last_response or json.dumps(feedback, ensure_ascii=False, indent=2)
                write_text_file(critic_log_path, critic_output)
                append_run_log(f"Critic output saved to {critic_log_path}")
            else:
                append_run_log("Editor: self-reviewing slides")
                feedback = editor.self_review(image_paths, slides_md=slides_md)
                critic_log_path = os.path.join(logs_dir, f"iter_{iteration}_critic.txt")
                critic_output = editor.last_response or json.dumps(feedback, ensure_ascii=False, indent=2)
                write_text_file(critic_log_path, critic_output)
                append_run_log(f"Self-review output saved to {critic_log_path}")


        iter_dir = os.path.join(history_dir, f"iter_{iteration}")
        ensure_dir(iter_dir)
        source_slides_path = slides_path if Path(slides_path).exists() else candidate_path
        shutil.copy(source_slides_path, os.path.join(iter_dir, "slides.md"))
        if image_paths:
            images_history = os.path.join(iter_dir, "images")
            clear_dir(images_history)
            for img in image_paths:
                shutil.copy(img, images_history)

        critique_path = os.path.join(iter_dir, "critique.json")
        with open(critique_path, "w", encoding="utf-8") as f:
            json.dump(feedback, f, ensure_ascii=False, indent=2)

        if is_approved(feedback):
            append_run_log("Approved. Stopping iterations.")
            break
        append_run_log("Not approved. Continuing to next iteration.")

    if last_success_md:
        write_text_file(slides_path, last_success_md)
    else:
        write_text_file(slides_path, slides_md)
    elapsed = time.time() - start_time
    typer.echo(f"Done. Final slides at {current_dir}/slides.md")
    typer.echo(f"Elapsed: {elapsed:.2f}s")


if __name__ == "__main__":
    app()
