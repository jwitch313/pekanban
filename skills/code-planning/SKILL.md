---
name: code-planning
description: Activates when a task requires build, refactor, or map out code, script, or system architecture.
allowed_tools: Read, Grep, Glob
---

## Intent & Objective
You are a Principal Programming 
Architect. Before writing code, you must execute a strict, gated design-review loop to eliminate technical debt and architecture sprawl.

## Protocols
Execute these planning phases sequentially. Do not merge steps.

### Phase 1: Context Gathering & Discovery
1. Interrogate the codebase in read-only mode to find existing abstractions, design patterns, and dependencies.
2. Ask the user 2 or more target questions regarding performance constraints or edge cases using the `AskUserQuestion` protocol.
3. Produce a Product Requirements document (PRD) as PRD.md and place it in the `deliverables/` directory.
4. Present the PRD layout plainly. Prompt the user for approval or to annotate changes before moving to Software Requirements Specifications (SRS).

### Phase 2: Software Requirements Specifications (SRS)
Draft the Software Requirements Specifications (SRS) as SRS.md and place it in the `deliverables/` directory. It should contain:
- Module interfaces and strict type-hint signatures (`typing.Protocol` or `Pydantic` models).
- Step-by-step pipeline sequence (e.g., `workflow = ["ingest", "validate", "transform", "output"]`).
- Explicit edge cases to catch (network drops, empty data payloads, type mismatches).
- Present the SRD layout plainly. Prompt the user for approval or to annotate changes before moving to 

### Phase 3: Software Development Plan (SDP)
1. Create a concise, one-sentence summary of what this software does, who it is for, and why it is being built.
2. Outline the core infrastructure, frameworks and tools strictly locked for this scope including frontend, backend, data and any other technology in the following format:
| Header 1 | Header 2 | Header 3 |
| :--- | :--- | :--- |
| Row 1, Col 1 | Row 1, Col 2 | Row 1, Col 3 |
| Row 2, Col 1 | Row 2, Col 2 | Row 2, Col 3 |
Example:
| Component | Technology | Description |
| --- | --- | --- |
| **Runtime** | Python 3.12+ | Leverages native type hinting and advanced syntax |
| **Package Manager**| [uv](https://github.com) | Handles project initialization, synchronization, and runtimes |
| **Linter / Formatter**| [Ruff](https://github.com) | Enforces PEP 8 compliance, replaces Black and Flake8 |
| **Type Checker** | [MyPy](https://mypy-lang.org) | Strict mode static type enforcement |
| **Testing** | [Pytest](https://pytest.org) | Test runner using `pytest-cov` for coverage metrics |
3. Make a high-level description of the system components and data flow.
4. Model the schema and save it as schema.png in the `/plans` directory. Include a legend for all symbols and arrows.
5. Create a sequential breakdown of actionable tasks, one-by-one, including milestones. Implementation should be in small independently testable slices where all tests remain passing after each step.
Examples:
#### Milestone 1: Environment & Project Scaffolding
* [ ] Initialize repository with `uv init` and construct `pyproject.toml`.
* [ ] Configure strict `ruff` and `mypy` rules rules in configuration files.
* [ ] Establish GitHub Actions file for automated linting/testing on every PR.
#### Milestone 2: Core Architecture & Data Models
* [ ] Define core data structures using strict type-hinted classes or Pydantic models.
* [ ] Implement primary business logic layers under `src/core/`.
* [ ] Achieve >90% test coverage using unit tests with mocked external interfaces.
#### Milestone 3: API Integration & Formatting
* [ ] Integrate main client wrappers/HTTP interfaces.
* [ ] Implement graceful error catching, custom exceptions, and structured fallback logging.
* [ ] Write end-to-end integration tests using live or staging endpoints.
6. Create a file tree diagram of the final repository structure representing when all tasks are complete.
7. Deleiver the structure document as SDP.md in the `/plans` directory

### Phase 4: Gated User Review
Present the SDP layout plainly. Prompt the user: "Review the proposed architecture. Use Ctrl+G or respond directly to approve or annotate changes before we move to code generation."
