"""
LangGraph workflow for interactive storytelling.

This module defines the complete state machine that orchestrates
the storytelling process from user input to final response.
"""

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from backend.models.state import StoryState
from backend.storyteller.nodes import (
    generate_narrative_node,
    parse_output_node,
    generate_summary_node,
    generate_image_node,
    generate_audio_node,
    check_beat_complete_node,
    deduct_credits_node,
    should_generate_media,
    is_beat_complete,
    has_error
)
from backend.config import config


def create_storyteller_graph(checkpointer: MemorySaver | None = None):
    """
    Build the complete storytelling state machine.

    The workflow follows this pattern:
    1. Generate narrative with LLM (using world template + generated story bible)
    2. Parse JSON output and extract story bible updates
    3. Generate summary
    4. Conditionally generate media (image/audio)
    5. Check if beat is complete and advance if needed
    6. Deduct credits
    7. End

    Args:
        checkpointer: Optional MemorySaver for session persistence

    Returns:
        Compiled LangGraph workflow
    """
    # Create state graph
    workflow = StateGraph(StoryState)

    # ===== Add Nodes =====

    workflow.add_node("generate_narrative", generate_narrative_node)
    workflow.add_node("parse_output", parse_output_node)
    workflow.add_node("generate_summary", generate_summary_node)
    workflow.add_node("generate_image", generate_image_node)
    workflow.add_node("generate_audio", generate_audio_node)
    workflow.add_node("check_beat_complete", check_beat_complete_node)
    workflow.add_node("deduct_credits", deduct_credits_node)

    # Error handling node
    workflow.add_node("handle_error", lambda state: {
        "narrative_text": "Something went wrong...",
        "choices": [{"id": 1, "text": "She tried again, taking a deep breath as...", "tone": "cautious"}],
        "error": None  # Clear error after handling
    })

    # ===== Define Edges =====

    # Entry point - start with narrative generation (no RAG needed)
    workflow.set_entry_point("generate_narrative")

    # Linear flow through core generation
    workflow.add_edge("generate_narrative", "parse_output")
    workflow.add_edge("parse_output", "generate_summary")

    # Conditional: Generate media or skip?
    workflow.add_conditional_edges(
        "generate_summary",
        should_generate_media,
        {
            "generate_media": "generate_image",
            "skip_media": "check_beat_complete"
        }
    )

    # If generating media, do image then audio
    workflow.add_edge("generate_image", "generate_audio")
    workflow.add_edge("generate_audio", "check_beat_complete")

    # After beat check, always deduct credits
    workflow.add_edge("check_beat_complete", "deduct_credits")

    # Final edge to END
    workflow.add_edge("deduct_credits", END)

    # Error handling (currently not wired - can be added later)
    workflow.add_edge("handle_error", END)

    # ===== Compile =====

    if checkpointer:
        return workflow.compile(checkpointer=checkpointer)
    else:
        return workflow.compile()


def create_persistent_graph(db_path: str = "story_checkpoints.db"):
    """
    Create a graph with async SQLite persistence.

    Args:
        db_path: Path to SQLite database file for checkpointing

    Returns:
        Compiled graph with async checkpointing enabled
    """
    from pathlib import Path

    try:
        # Ensure database directory exists
        db_file = Path(db_path)
        db_file.parent.mkdir(parents=True, exist_ok=True)

        print(f"📝 Creating async SQLite checkpoint database at: {db_path}")
        print(f"📁 Parent directory: {db_file.parent} (exists: {db_file.parent.exists()})")
        print(f"📁 Parent writable: {db_file.parent.exists() and db_file.parent.stat().st_mode & 0o200}")

        # Create AsyncSqliteSaver by passing the database path as a URI
        # AsyncSqliteSaver will manage the aiosqlite connection internally
        checkpointer = AsyncSqliteSaver.from_conn_string(f"sqlite:///{db_file}")

        print(f"✓ Using async SQLite checkpointer: {db_path}")
        return create_storyteller_graph(checkpointer=checkpointer)

    except Exception as e:
        print(f"❌ Failed to create async SQLite checkpoint database: {e}")
        import traceback
        traceback.print_exc()
        raise RuntimeError(f"Could not initialize checkpoint database at {db_path}: {e}") from e


# ===== Helper Functions =====

async def run_story_turn(
    graph,
    user_input: str,
    session_id: str,
    current_state: StoryState | None = None
) -> tuple[StoryState, dict]:
    """
    Execute one turn of the story (user input → AI response).

    Args:
        graph: Compiled LangGraph workflow
        user_input: Player's choice or input
        session_id: Session identifier for checkpointing
        current_state: Current state (if None, loads from checkpoint)

    Returns:
        Tuple of (final_state, outputs)
    """
    from langchain_core.messages import HumanMessage

    # Prepare input
    if current_state:
        # Add user message to state
        messages = current_state.get("messages", []).copy()
        messages.append(HumanMessage(content=user_input))
        input_state = {**current_state, "messages": messages}
    else:
        # Starting fresh (should load from checkpoint)
        input_state = {"messages": [HumanMessage(content=user_input)]}

    # Configuration for checkpointing
    graph_config = {"configurable": {"thread_id": session_id}}

    # Run graph
    final_state = await graph.ainvoke(input_state, config=graph_config)

    # Extract outputs for response
    outputs = {
        "narrative": final_state.get("narrative_text", ""),
        "choices": final_state.get("choices", []),
        "image_url": final_state.get("image_url"),
        "audio_url": final_state.get("audio_url"),
        "current_beat": final_state.get("current_beat", 1),
        "beat_complete": final_state.get("beat_progress", {}).get(final_state.get("current_beat", 1), False),
        "credits_remaining": final_state.get("credits_remaining", 0),
        "error": final_state.get("error")
    }

    return final_state, outputs


def visualize_graph(output_path: str = "storyteller_graph.png"):
    """
    Generate a visual representation of the graph.

    Args:
        output_path: Path to save the visualization

    Note:
        Requires graphviz installed: `brew install graphviz`
    """
    try:
        graph = create_storyteller_graph()
        graph_image = graph.get_graph().draw_mermaid_png()

        with open(output_path, "wb") as f:
            f.write(graph_image)

        print(f"✓ Graph visualization saved to {output_path}")

    except Exception as e:
        print(f"Error generating graph visualization: {e}")
        print("Try: brew install graphviz")


if __name__ == "__main__":
    # Test: visualize the graph
    print("Creating storyteller graph visualization...")
    visualize_graph()
