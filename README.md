# PPT-Agent: AI-Powered Slide Generator

This project implements an AI agent system capable of generating high-quality presentations using the Proposer-Reviewer (Editor-Critic) paradigm. It utilizes **Slidev** as the rendering engine and **Vision LLMs** for visual quality assessment.

## Prerequisites

*   Python 3.10+
*   Node.js 18+
*   API Key for your chosen LLM provider (DeepSeek, Moonshot, or OpenAI)

## Setup

1.  Current directory:
    ```bash
    cd "PATH_TO_THE_ROOT_OF_THE_PROJECT"
    ```

2.  Install Python dependencies:
    ```bash
    pip install -r requirements.txt
    ```

3.  Install Node.js dependencies:
    ```bash
    npm install
    # or
    yarn
    ```

4.  Set up environment variables:
    Create a `.env` file in the root directory. Example (Editor=DeepSeek, Critic=Moonshot):
    ```
    EDITOR_LLM_PROVIDER=deepseek
    EDITOR_LLM_MODEL=deepseek-chat
    DEEPSEEK_API_KEY=sk-your-deepseek-key
    DEEPSEEK_BASE_URL=https://api.deepseek.com

    CRITIC_LLM_PROVIDER=moonshot
    CRITIC_LLM_MODEL=moonshot-v1-8k
    MOONSHOT_API_KEY=sk-your-moonshot-key
    MOONSHOT_BASE_URL=https://api.moonshot.cn/v1
    ```

    Optional:
    ```
    # Global defaults (used if EDITOR_/CRITIC_ not set)
    # LLM_PROVIDER=openai
    # LLM_MODEL=gpt-4o
    # OPENAI_API_KEY=sk-your-openai-key

    # Force vision on/off for providers that support it
    # LLM_SUPPORTS_VISION=true
    ```

## Usage

1.  Prepare your input text in `data/paper_summary.txt`.
2.  Run the main script:
    ```bash
    python -m src.main
    ```

## Structure

*   `src/agents`: Editor and Critic agent implementations.
*   `src/utils`: Utilities for LLM communication and Slidev execution.
*   `output`: Generated slides and history.
