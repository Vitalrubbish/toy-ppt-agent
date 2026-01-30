import glob
import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List


class RenderError(RuntimeError):
    pass


@dataclass
class SlidevRunner:
    work_dir: str

    def _get_chromium_headless_revision(self) -> str | None:
        browsers_json = Path(self.work_dir) / "node_modules" / "playwright-core" / "browsers.json"
        if not browsers_json.exists():
            return None
        try:
            data = json.loads(browsers_json.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None
        for browser in data.get("browsers", []):
            if browser.get("name") == "chromium-headless-shell":
                return browser.get("revision")
        return None

    def install_dependencies(self) -> None:
        subprocess.run(
            ["npm", "install"],
            cwd=self.work_dir,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

    def render_slides(self, md_file_path: str, output_dir: str) -> List[str]:
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        env = os.environ.copy()
        env.setdefault("PLAYWRIGHT_DISABLE_SANDBOX", "1")
        env.setdefault("PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS", "1")

        chromium_path = (
            shutil.which("chromium")
            or shutil.which("chromium-browser")
            or shutil.which("google-chrome")
            or shutil.which("google-chrome-stable")
            or shutil.which("chrome")
            or shutil.which("brave-browser")
        )
        if chromium_path and "PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH" not in env:
            env["PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH"] = chromium_path
            revision = self._get_chromium_headless_revision()
            if revision:
                stub_root = os.path.join(self.work_dir, ".playwright-browsers")
                stub_dir = os.path.join(
                    stub_root,
                    f"chromium_headless_shell-{revision}",
                    "chrome-headless-shell-linux64",
                )
                stub_path = os.path.join(stub_dir, "chrome-headless-shell")
                os.makedirs(stub_dir, exist_ok=True)
                if not os.path.exists(stub_path) or not os.access(stub_path, os.X_OK):
                    with open(stub_path, "w", encoding="utf-8") as stub_file:
                        stub_file.write("#!/usr/bin/env bash\n")
                        stub_file.write(f"exec {chromium_path} \"$@\"\n")
                    os.chmod(stub_path, 0o755)
                env["PLAYWRIGHT_BROWSERS_PATH"] = stub_root

        base_cmd = [
            "npx",
            "slidev",
            "export",
            md_file_path,
            "--output",
            output_dir,
            "--format",
            "png",
        ]
        if chromium_path:
            base_cmd.extend(["--executable-path", chromium_path])

        attempts = [
            {"timeout": "180000", "wait": "2000", "per_slide": False},
            {"timeout": "300000", "wait": "8000", "per_slide": True},
        ]

        last_error = ""
        for attempt in attempts:
            cmd = base_cmd + ["--timeout", attempt["timeout"], "--wait", attempt["wait"]]
            if attempt["per_slide"]:
                cmd.append("--per-slide")
            result = subprocess.run(
                cmd,
                cwd=self.work_dir,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            if result.returncode == 0:
                last_error = ""
                break
            last_error = result.stderr.strip() or result.stdout.strip()
            if "locator.waitFor" not in last_error and "Timeout" not in last_error:
                break

        if last_error:
            raise RenderError(last_error)

        patterns = ["*.png", "*.PNG"]
        files: List[str] = []
        for pattern in patterns:
            files.extend(glob.glob(os.path.join(output_dir, pattern)))
        files.sort()
        return files

    @staticmethod
    def check_syntax(code: str) -> bool:
        if not code.strip():
            return False
        if "---" not in code:
            return False
        return True
