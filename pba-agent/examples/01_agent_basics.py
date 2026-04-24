"""Step 1: Agent Basics + YAML Specs.

Demonstrates:
- Creating an Agent in Python with instructions and model_settings
- Running an agent with run_sync()
- Loading an agent from a YAML Agent Spec via Agent.from_file()
"""

from __future__ import annotations

from pathlib import Path

from pydantic_ai import Agent

SPECS_DIR = Path(__file__).resolve().parent.parent / "specs"


def demo_inline_agent() -> None:
    """Create an agent entirely in Python and run it."""
    agent = Agent(
        "openai:gpt-4.1-mini",
        instructions="You are a concise, helpful assistant. Lead with the answer.",
        model_settings={"temperature": 0.3, "max_tokens": 256},
    )
    result = agent.run_sync("What is the capital of Japan?")
    print(f"[inline agent] {result.output}\n")


def demo_yaml_agent() -> None:
    """Load an agent from a YAML spec and run it."""
    spec_path = SPECS_DIR / "hello-agent.yaml"
    agent = Agent.from_file(spec_path)
    result = agent.run_sync("Explain what an LLM agent is in two sentences.")
    print(f"[yaml agent] {result.output}\n")


def demo_instructions_matter() -> None:
    """Show that instructions change agent behavior."""
    formal = Agent(
        "openai:gpt-4.1-mini",
        instructions="You are an 18th-century British diplomat. Respond formally.",
        model_settings={"temperature": 0.7, "max_tokens": 256},
    )
    casual = Agent(
        "openai:gpt-4.1-mini",
        instructions="You are a surfer from California. Respond casually.",
        model_settings={"temperature": 0.7, "max_tokens": 256},
    )

    prompt = "What do you think about rainy weather?"
    print(f"[formal] {formal.run_sync(prompt).output}\n")
    print(f"[casual] {casual.run_sync(prompt).output}\n")


if __name__ == "__main__":
    print("=== Demo 1: Inline Agent ===")
    demo_inline_agent()

    print("=== Demo 2: YAML Agent Spec ===")
    demo_yaml_agent()

    print("=== Demo 3: Instructions Shape Behavior ===")
    demo_instructions_matter()
