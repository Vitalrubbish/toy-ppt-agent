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
    Create a `.env` file in the root directory. Example:
    ```
    LLM_PROVIDER=openai
    LLM_MODEL=gpt-4o

    OPENAI_API_KEY=sk-your-openai-key
    OPENAI_BASE_URL=https://api.openai.com/v1

    EDITOR_LLM_PROVIDER=openai
    EDITOR_LLM_MODEL=gpt-4o

    CRITIC_LLM_PROVIDER=openai
    CRITIC_LLM_MODEL=gpt-4o

    PLAYWRIGHT_BROWSERS_PATH="PATH_TO_PLAYWRIGHT_BROWSERS"
    PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH="PATH_TO_PLAYWRIGHT_CHROMIUM_EXECUTABLE"
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
*   `outputs`: Generated slides and history.
