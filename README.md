# blackcore

> Intelligence processing and automation system for Project Nassau

`blackcore` is a Python-based system designed for intelligent processing and automation. It leverages AI models from Anthropic and OpenAI, interacts with services like Notion, and uses a Redis cache.

## Features

*   **AI Integration:** Core logic powered by Anthropic and OpenAI models.
*   **Notion Connectivity:** Seamlessly interacts with Notion databases and pages.
*   **Data Caching:** Uses Redis for efficient data caching and persistence.
*   **Structured Data:** Employs Pydantic for robust data modeling and validation.
*   **Modern Tooling:** Formatted and linted with Ruff, tested with Pytest.

## Getting Started

### Prerequisites

- Python 3.11 or higher
- `uv` or `pip` for package management

### Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd blackcore
    ```

2.  **Create a virtual environment:**
    ```bash
    python -m venv .venv
    source .venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    For development, also install the development dependencies:
    ```bash
    pip install -r requirements-dev.txt
    ```

## Configuration

The system requires environment variables for configuration.

1.  Copy the example environment file:
    ```bash
    cp .env.example .env
    ```

2.  Fill in the required values in the `.env` file. This will include API keys for services like Notion, Anthropic, and OpenAI.

## Usage

To run the application, execute the main script:

```bash
# Example: python -m blackcore.main (assuming main.py is the entry point)
# Further usage instructions needed.
```

## Testing

The project uses `pytest` for testing. Tests are located in the `testing/` directory and within module-specific test folders.

To run the test suite:

```bash
pytest
```
