# /new-sdk-app

Scaffold a new application powered by the Claude Agent SDK with interactive setup.

## Usage

```
/new-sdk-app [PROJECT_NAME]
```

## Arguments

- `PROJECT_NAME` (optional): Name for the new project. If omitted, the command will prompt for it.

## Workflow

### Step 1: Interactive project configuration

Ask the user the following questions one at a time. Wait for each answer before proceeding.

#### Q1: Language

> Which language would you like to use?
> 1. **Python** -- uses the `claude-agent-sdk` PyPI package
> 2. **TypeScript** -- uses the `@anthropic-ai/agent-sdk` npm package

Default to Python if the user does not specify.

#### Q2: Project name

If `PROJECT_NAME` was not provided as an argument:

> What should the project be called? (lowercase, hyphens allowed, e.g., `my-agent-app`)

Validate the name: lowercase alphanumeric characters and hyphens only, must start with a letter, 2-50 characters.

#### Q3: Features

> Which features would you like to include? (comma-separated numbers, or "all")
> 1. **Tool use** -- define custom tools the agent can call
> 2. **Multi-turn conversation** -- maintain conversation history across turns
> 3. **Streaming** -- stream agent responses token-by-token
> 4. **Sub-agents** -- spawn child agents for parallel or specialized tasks
> 5. **Human-in-the-loop** -- pause execution to ask the user for input or approval
> 6. **MCP integration** -- connect to Model Context Protocol servers for external tools
> 7. **Guardrails** -- add input/output validation and safety checks

Default to features 1, 2, 3 if the user does not specify.

#### Q4: Description

> Briefly describe what your agent will do (one sentence):

This will be used in the README and package metadata.

### Step 2: Scaffold the project (Python)

If the user chose Python, create the following structure:

```
<project-name>/
  pyproject.toml
  README.md
  src/
    <package_name>/
      __init__.py
      agent.py
      tools.py          # if "Tool use" selected
      config.py
  tests/
    __init__.py
    test_agent.py
  .env.example
  .gitignore
  CLAUDE.md
```

#### pyproject.toml

```toml
[project]
name = "<project-name>"
version = "0.1.0"
description = "<user description>"
requires-python = ">=3.10"
dependencies = [
    "claude-agent-sdk>=0.1.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "ruff>=0.4",
]

[tool.ruff]
line-length = 100
target-version = "py310"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
```

#### src/<package_name>/agent.py

Generate a working agent file that:
- Imports `Agent`, `Tool`, and relevant classes from `claude_agent_sdk`
- Creates an agent with the user's description as the system prompt
- Registers any selected tools
- Implements streaming if selected
- Sets up sub-agent spawning if selected
- Adds human-in-the-loop hooks if selected
- Configures MCP servers if selected
- Applies guardrails if selected
- Includes a `main()` function that runs the agent in a conversation loop
- Has proper type hints and docstrings

#### src/<package_name>/tools.py (if Tool use selected)

Generate a tools file with:
- 2-3 example tool definitions using the `@tool` decorator
- Proper parameter type annotations
- Docstrings that serve as tool descriptions
- One simple tool (e.g., `get_current_time`) and one that demonstrates structured input/output

#### src/<package_name>/config.py

Generate a config file that:
- Loads settings from environment variables with sensible defaults
- Defines a `Config` dataclass with fields for: `model` (default `claude-sonnet-4-20250514`), `max_tokens`, `api_key` (from `ANTHROPIC_API_KEY`), and any feature-specific settings
- Validates required configuration at startup

#### tests/test_agent.py

Generate a test file with:
- A test that verifies the agent can be instantiated
- A test for each selected tool (mocked)
- Basic conversation flow test with mocked API responses

#### .env.example

```
ANTHROPIC_API_KEY=your-api-key-here
```

#### .gitignore

Standard Python `.gitignore` including `.env`, `__pycache__`, `.venv`, `dist/`, `.ruff_cache/`.

#### CLAUDE.md

Generate a `CLAUDE.md` with:
- Project description
- How to set up and run the project
- Coding conventions (use ruff, type hints required, docstrings on public functions)
- Testing instructions

### Step 3: Scaffold the project (TypeScript)

If the user chose TypeScript, create the following structure:

```
<project-name>/
  package.json
  tsconfig.json
  README.md
  src/
    index.ts
    agent.ts
    tools.ts            # if "Tool use" selected
    config.ts
  tests/
    agent.test.ts
  .env.example
  .gitignore
  CLAUDE.md
```

#### package.json

```json
{
  "name": "<project-name>",
  "version": "0.1.0",
  "description": "<user description>",
  "type": "module",
  "main": "dist/index.js",
  "scripts": {
    "build": "tsc",
    "start": "tsx src/index.ts",
    "dev": "tsx watch src/index.ts",
    "test": "vitest run",
    "test:watch": "vitest",
    "lint": "biome check src/",
    "format": "biome format --write src/"
  },
  "dependencies": {
    "@anthropic-ai/agent-sdk": "^0.1.0"
  },
  "devDependencies": {
    "@biomejs/biome": "^1.8.0",
    "tsx": "^4.0.0",
    "typescript": "^5.5.0",
    "vitest": "^2.0.0"
  }
}
```

#### tsconfig.json

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "outDir": "dist",
    "rootDir": "src",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "declaration": true,
    "sourceMap": true
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist", "tests"]
}
```

#### src/agent.ts

Generate a working agent file that:
- Imports `Agent`, `Tool`, and relevant classes from `@anthropic-ai/agent-sdk`
- Creates an agent class with the user's description as the system prompt
- Registers any selected tools
- Implements streaming if selected
- Sets up sub-agent spawning if selected
- Adds human-in-the-loop callbacks if selected
- Configures MCP integration if selected
- Applies guardrails if selected
- Exports the agent for use by `index.ts`
- Has proper TypeScript types and JSDoc comments

#### src/tools.ts (if Tool use selected)

Generate a tools file with:
- 2-3 example tool definitions using Zod schemas for parameter validation
- Proper TypeScript types
- JSDoc comments that serve as tool descriptions
- One simple tool and one demonstrating structured input/output

#### src/config.ts

Generate a config file that:
- Loads settings from `process.env` with sensible defaults
- Defines a `Config` interface and a `loadConfig()` function
- Validates required configuration at startup and throws clear errors for missing values

#### src/index.ts

Entry point that:
- Loads configuration
- Creates the agent
- Runs the conversation loop
- Handles graceful shutdown on SIGINT/SIGTERM

#### tests/agent.test.ts

Generate a test file with:
- A test that verifies agent instantiation
- A test for each selected tool (mocked)
- Basic conversation flow test with mocked API responses

#### .env.example, .gitignore, CLAUDE.md

Similar to the Python versions but adapted for the TypeScript toolchain (biome, vitest, tsx).

### Step 4: Post-scaffold actions

After creating all files:

1. Print a summary of created files and directories.
2. Display the next steps:
   ```
   ## Next Steps

   1. cd <project-name>
   2. Copy .env.example to .env and add your ANTHROPIC_API_KEY
   3. Install dependencies:
      - Python: pip install -e ".[dev]"
      - TypeScript: npm install
   4. Run the agent:
      - Python: python -m <package_name>
      - TypeScript: npm start
   5. Run tests:
      - Python: pytest
      - TypeScript: npm test
   ```
3. Ask if the user wants to install dependencies now.
4. Ask if the user wants to initialize a git repository.

### Step 5: Verify with the appropriate agent

After scaffolding, run the appropriate verification agent:
- For Python: use the `agent-sdk-verifier-py` agent to verify the project structure and implementation.
- For TypeScript: use the `agent-sdk-verifier-ts` agent to verify the project structure and implementation.

Report any issues found and offer to fix them automatically.
