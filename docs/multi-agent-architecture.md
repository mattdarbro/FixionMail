# Multi-Agent Story Generation Architecture

## Overview

This document describes the redesigned story generation system using a multi-agent architecture with RAG-based consistency checking.

**Key Insight:** Two-level beat system - story structure beats (novel-level) + chapter beats (chapter-level)

---

## Agent Definitions

### 1. Story Structure Beat Agent (SSBA)
**Purpose:** Maintains overall story arc across all 30 chapters using Save the Cat structure

**When it runs:**
- **Chapter 1:** Full story planning (creates complete story arc)
- **Chapters 2-30:** Lightweight check-in (monitors progression, provides context)

**Input (Chapter 1):**
- World template
- Genre
- Story bible (initial)
- Total chapters (default: 30)

**Output (Chapter 1):**
```json
{
  "story_structure": {
    "act_1": {
      "opening_image": {"chapters": [1], "description": "Establish ordinary world on space station"},
      "theme_stated": {"chapters": [1-2], "description": "Hint at isolation vs connection"},
      "setup": {"chapters": [1-3], "description": "Introduce characters, relationships, station life"},
      "catalyst": {"chapters": [3-4], "description": "Mysterious signal detected"},
      "debate": {"chapters": [4-5], "description": "Should they investigate or report?"}
    },
    "act_2a": {
      "break_into_2": {"chapters": [6], "description": "Decision to investigate secretly"},
      "b_story": {"chapters": [6-8], "description": "Romance subplot develops"},
      "fun_and_games": {"chapters": [7-12], "description": "Explore signal source, discoveries"},
      "midpoint": {"chapters": [13-14], "description": "False victory: decrypt signal, reveal danger"}
    },
    "act_2b": {
      "bad_guys_close_in": {"chapters": [15-20], "description": "Station command suspicious, external threat"},
      "all_is_lost": {"chapters": [21-22], "description": "Discovery exposed, consequences"},
      "dark_night_of_soul": {"chapters": [23], "description": "Protagonist questions everything"}
    },
    "act_3": {
      "break_into_3": {"chapters": [24], "description": "New plan formulated"},
      "finale": {"chapters": [25-29], "description": "Confrontation and resolution"},
      "final_image": {"chapters": [30], "description": "New normal established"}
    }
  },
  "key_arcs": {
    "protagonist_arc": "Isolated engineer → Community leader",
    "romance_arc": "Mutual distrust → Deep partnership",
    "station_arc": "Safe haven → Dangerous frontier"
  }
}
```

**Input (Chapters 2-30):**
- Current chapter number
- Story structure (from Chapter 1)
- Story bible (updated)
- Previous chapter summaries (last 3)

**Output (Chapters 2-30):**
```json
{
  "current_story_beat": "fun_and_games",
  "act": "2a",
  "progress_percentage": 35.5,
  "guidance_for_cba": "We're in Act 2A - exploration phase. Create chapter beats that reveal discoveries and deepen relationships. Tone: wonder with underlying tension.",
  "upcoming_milestone": "Approaching midpoint (chapter 13-14) - start building toward false victory",
  "character_arcs_status": {
    "protagonist": "Learning to trust others, 40% through arc",
    "love_interest": "Opening up about past, 35% through arc"
  }
}
```

---

### 2. Chapter Beat Agent (CBA)
**Purpose:** Creates 6-beat structure for the current chapter

**When it runs:** Every chapter (1-30)

**Input (Chapter 1):**
- SSBA story structure
- Story bible
- World template

**Input (Chapters 2-30):**
- SSBA check-in output
- Story bible
- Player's last choice
- Last 6 chapter summaries

**Output:**
```json
{
  "chapter_beats": [
    {
      "beat_number": 1,
      "beat_name": "Opening Hook",
      "scene": "Charlie wheels through empty corridor, notices oxygen readings fluctuating",
      "key_actions": [
        "Charlie checks tablet while navigating to control room",
        "Passes crew quarters - everyone asleep",
        "Hears unusual hum from ventilation system"
      ],
      "characters_present": ["Charlie"],
      "location": "Level 3 corridor, near control room",
      "emotional_tone": "Uneasy calm, growing concern",
      "time_estimate": "Late night, 0300 hours",
      "story_beat_alignment": "fun_and_games - discovery phase"
    },
    {
      "beat_number": 2,
      "beat_name": "Rising Action",
      "scene": "Charlie investigates control panel, discovers anomaly pattern",
      "key_actions": [
        "Accesses main control terminal",
        "Runs diagnostic on life support systems",
        "Discovers pattern matches signal frequency from Chapter 7"
      ],
      "characters_present": ["Charlie", "Station AI (voice only)"],
      "location": "Main control room",
      "emotional_tone": "Focused tension, intellectual excitement",
      "time_estimate": "15 minutes later",
      "story_beat_alignment": "fun_and_games - connecting clues"
    }
    // ... beats 3-6
  ],
  "chapter_goal": "Charlie discovers connection between station anomalies and the mysterious signal",
  "chapter_tension": "Will Charlie investigate alone or wake the crew?",
  "setup_for_next": "Decision point about whether to bring others into investigation"
}
```

---

### 3. Context Editor Agent (CEA)
**Purpose:** RAG-based consistency checking - validates CBA output against established story facts

**When it runs:** Chapters 2-30 only (Chapter 1 has no context to check)

**Input:**
- CBA chapter beats (unvalidated)
- RAG vector store (all previous chapters as paragraph chunks)
- Story bible

**Process:**
1. Extract entities from CBA beats: characters, locations, objects, facts
2. For each entity, query RAG store for relevant past mentions
3. Identify contradictions or inconsistencies
4. Revise beat plan to maintain continuity

**Output:**
```json
{
  "revised_chapter_beats": [ /* same structure as CBA, but corrected */ ],
  "consistency_checks": [
    {
      "beat_number": 1,
      "entity": "Charlie",
      "issue": "Original beat said 'Charlie walks through corridor'",
      "rag_finding": "Chapter 3, paragraph 12: 'The explosion left Charlie dependent on his wheelchair'",
      "correction": "Changed to 'Charlie wheels through corridor'",
      "confidence": 0.95
    },
    {
      "beat_number": 2,
      "entity": "Dr. Sarah Chen",
      "issue": "Original beat included Dr. Chen in control room",
      "rag_finding": "Chapter 11, paragraph 45: 'Dr. Chen departed for Earth on supply shuttle'",
      "correction": "Replaced Dr. Chen with Lieutenant Torres",
      "confidence": 0.88
    },
    {
      "beat_number": 2,
      "entity": "signal frequency",
      "issue": "Beat mentions 'signal frequency from Chapter 7'",
      "rag_finding": "Chapter 7, paragraph 23: 'The signal pulsed at 2.4 GHz, matching old radio astronomy band'",
      "correction": "Added detail: 'matches the 2.4 GHz pattern'",
      "confidence": 0.92
    }
  ],
  "rag_queries_performed": 15,
  "contradictions_found": 3,
  "auto_corrections_made": 3
}
```

**RAG Implementation Details:**
- **Vector Store:** Chroma (local, free)
- **Chunk Size:** Paragraph-level (each paragraph is a separate embedding)
- **Embedding Model:** OpenAI text-embedding-3-small (cheap, fast) or Anthropic's if available
- **Retrieval:** Top 5 most relevant chunks per entity query
- **Metadata stored with chunks:**
  ```json
  {
    "chapter_number": 7,
    "paragraph_number": 23,
    "characters_mentioned": ["Charlie", "Torres"],
    "locations_mentioned": ["control room"],
    "themes": ["mystery", "discovery"],
    "beat": "fun_and_games"
  }
  ```

---

### 4. Prose Agent (PA)
**Purpose:** Write 2500-word narrative prose from beat plan

**Input (Chapter 1):**
- CBA chapter beats (no CEA validation)
- Story bible
- World template

**Input (Chapters 2-30):**
- CEA revised chapter beats
- Story bible
- Player's last choice (continuation text)
- Last 3 chapter summaries

**Output:**
```json
{
  "narrative": "The emergency klaxons screamed through the corridors...",  // ~2500 words
  "choices": [
    {"id": 1, "text": "She decided to...", "tone": "bold"},
    {"id": 2, "text": "She carefully...", "tone": "cautious"},
    {"id": 3, "text": "She paused to...", "tone": "thoughtful"}
  ],
  "image_prompt": "Space station control room, dramatic lighting, holographic displays",
  "story_bible_update": {
    "key_events": ["Charlie discovered oxygen anomaly pattern"],
    "locations": {
      "level_3_corridor": "Dimly lit hallway between crew quarters and control room"
    }
  },
  "beat_progress": 1.0
}
```

**Key difference from current system:** PA now follows a structured beat plan instead of generating everything from scratch. This should:
- Reduce hallucinations
- Improve consistency
- Maintain quality prose
- Actually be FASTER (less creative load)

---

## Data Structures

### Story State Updates

**New fields to add:**

```python
class StoryState(TypedDict):
    # ... existing fields ...

    # SSBA outputs
    story_structure: dict  # Full story arc (set in chapter 1)
    current_story_beat: str  # Current Save the Cat beat (updated each chapter)
    story_progress_pct: float  # Overall story completion %

    # CBA outputs
    chapter_beat_plan: dict  # Current chapter's 6-beat plan

    # CEA outputs
    consistency_report: dict  # Last consistency check results

    # RAG metadata
    rag_chunks_indexed: int  # Total paragraph chunks in vector store
    last_rag_update: str  # Timestamp of last vector store update
```

### Vector Store Schema

**Collection name:** `west_haven_story_{session_id}`

**Document structure:**
```python
{
    "id": "ch7_p23",
    "text": "The signal pulsed at 2.4 GHz, matching the old radio astronomy band. Charlie's eyes widened as he recognized the pattern.",
    "metadata": {
        "chapter_number": 7,
        "paragraph_number": 23,
        "characters": ["Charlie"],
        "locations": ["control room"],
        "entities": ["signal", "2.4 GHz", "radio astronomy"],
        "themes": ["mystery", "discovery"],
        "story_beat": "fun_and_games",
        "emotional_tone": "excitement"
    }
}
```

---

## Workflow Comparison

### Current System
```
User chooses option
  ↓
generate_narrative_node (100-120s)
  ↓
parse_output_node
  ↓
generate_summary_node (5s)
  ↓
generate_audio_node (10s)
  ↓
generate_image_node (15s)
  ↓
Return to user

Total: ~130-150s per chapter
Consistency: Relies on prompt + story bible + summaries
```

### New Multi-Agent System

**Chapter 1 Flow:**
```
User starts story
  ↓
SSBA: Create story structure (20-30s)
  ↓
CBA: Create chapter 1 beats (15-20s)
  ↓
PA: Write prose from beats (60-80s)
  ↓
parse_output_node
  ↓
generate_summary_node (5s)
  ↓
extract_entities_node (NEW - 5s)
  ↓
index_to_rag_node (NEW - 3s)
  ↓
generate_audio_node (10s)
  ↓
generate_image_node (15s)
  ↓
Return to user

Total: ~130-170s (similar to current)
```

**Chapters 2-30 Flow:**
```
User chooses option
  ↓
SSBA: Check-in (5-10s - lightweight)
  ↓
CBA: Create chapter beats (15-20s)
  ↓
CEA: RAG consistency check + revise (20-30s)
  ↓
PA: Write prose from revised beats (60-80s)
  ↓
parse_output_node
  ↓
generate_summary_node (5s)
  ↓
extract_entities_node (5s)
  ↓
index_to_rag_node (3s)
  ↓
generate_audio_node (10s)
  ↓
generate_image_node (15s)
  ↓
Return to user

Total: ~140-180s (10-30s longer, but MUCH more consistent)
```

---

## Implementation Phases

### Phase 1: RAG Infrastructure (3-4 hours)
**Goal:** Set up vector store and entity extraction

**Tasks:**
- [ ] Install Chroma: `pip install chromadb`
- [ ] Create `backend/rag/vector_store.py` - wrapper for Chroma operations
- [ ] Create `backend/rag/entity_extractor.py` - extract entities from text
- [ ] Create new node: `extract_entities_node` - parse narrative for entities
- [ ] Create new node: `index_to_rag_node` - add paragraph chunks to vector store
- [ ] Add RAG fields to StoryState
- [ ] Test: Index sample chapters, query for entities

**Files to create:**
- `backend/rag/__init__.py`
- `backend/rag/vector_store.py`
- `backend/rag/entity_extractor.py`

**Files to modify:**
- `backend/models/state.py` - add RAG fields
- `backend/storyteller/nodes.py` - add new nodes
- `backend/storyteller/graph.py` - wire new nodes into graph

---

### Phase 2: Story Structure Beat Agent (2-3 hours)
**Goal:** Create SSBA for novel-level story planning

**Tasks:**
- [ ] Create prompt template: `prompts_v2.py::create_story_structure_prompt()`
- [ ] Create node: `story_structure_beat_node` (runs chapter 1 only)
- [ ] Create node: `story_beat_checkin_node` (runs chapters 2-30)
- [ ] Add conditional edge: route to different node based on chapter number
- [ ] Test: Generate story structure for Chapter 1
- [ ] Test: Check-in output for Chapter 15

**Files to modify:**
- `backend/storyteller/prompts_v2.py` - add SSBA prompts
- `backend/storyteller/nodes.py` - add SSBA nodes
- `backend/storyteller/graph.py` - add SSBA to workflow

---

### Phase 3: Chapter Beat Agent (2-3 hours)
**Goal:** Create CBA for chapter-level beat planning

**Tasks:**
- [ ] Create prompt template: `prompts_v2.py::create_chapter_beat_prompt()`
- [ ] Create node: `chapter_beat_agent_node`
- [ ] Modify existing beat system to work with CBA output
- [ ] Test: Generate chapter beats with SSBA guidance
- [ ] Validate: 6 beats generated, proper structure

**Files to modify:**
- `backend/storyteller/prompts_v2.py` - add CBA prompts
- `backend/storyteller/nodes.py` - add CBA node
- `backend/storyteller/graph.py` - add CBA to workflow

---

### Phase 4: Context Editor Agent (4-5 hours)
**Goal:** Create CEA for RAG-based consistency checking

**Tasks:**
- [ ] Create `backend/rag/consistency_checker.py` - RAG query logic
- [ ] Create prompt template: `prompts_v2.py::create_consistency_check_prompt()`
- [ ] Create node: `context_editor_agent_node`
- [ ] Implement entity extraction from beat plan
- [ ] Implement RAG queries for each entity
- [ ] Implement beat plan revision based on findings
- [ ] Add conditional edge: skip CEA for Chapter 1
- [ ] Test: Intentionally create contradiction, verify CEA catches it

**Files to create:**
- `backend/rag/consistency_checker.py`

**Files to modify:**
- `backend/storyteller/prompts_v2.py` - add CEA prompts
- `backend/storyteller/nodes.py` - add CEA node
- `backend/storyteller/graph.py` - add CEA to workflow, conditional routing

---

### Phase 5: Prose Agent Modification (2-3 hours)
**Goal:** Modify existing narrative generation to follow beat plans

**Tasks:**
- [ ] Modify `generate_narrative_node` to accept beat plan input
- [ ] Update narrative prompt to follow beat structure
- [ ] Remove old beat marker system (replaced by structured beats)
- [ ] Test: Compare prose quality with/without structured beats
- [ ] Verify: 2500-word target still met

**Files to modify:**
- `backend/storyteller/nodes.py` - modify `generate_narrative_node`
- `backend/storyteller/prompts_v2.py` - update narrative prompt

---

### Phase 6: Integration & Testing (3-4 hours)
**Goal:** Wire everything together and test end-to-end

**Tasks:**
- [ ] Update graph.py with full workflow
- [ ] Test Chapter 1 generation (SSBA → CBA → PA)
- [ ] Test Chapter 2 generation (SSBA check-in → CBA → CEA → PA)
- [ ] Create test story with known contradictions
- [ ] Verify CEA catches contradictions
- [ ] Performance testing: measure latency of each agent
- [ ] Tune timeouts for new nodes
- [ ] Update frontend if needed (e.g., show agent progress)

**Files to modify:**
- `backend/storyteller/graph.py` - complete workflow
- `backend/api/routes.py` - any API changes needed
- `frontend/src/components/GenerationLog.tsx` - show new agents

---

### Phase 7: Monitoring & Refinement (2-3 hours)
**Goal:** Add observability and tune parameters

**Tasks:**
- [ ] Add detailed logging for each agent
- [ ] Add timing metrics for each phase
- [ ] Add consistency report to API response (for debugging)
- [ ] Create admin endpoint to view RAG store contents
- [ ] Tune RAG parameters (chunk size, retrieval count, similarity threshold)
- [ ] Tune consistency check strictness
- [ ] Document configuration options

**Files to modify:**
- `backend/storyteller/nodes.py` - add logging
- `backend/api/routes.py` - add consistency report to response
- `backend/config.py` - add RAG configuration options

---

## Configuration Options

**Add to `backend/config.py`:**

```python
# RAG Configuration
ENABLE_RAG_CONSISTENCY = True  # Master switch for CEA
RAG_CHUNK_SIZE = "paragraph"  # "paragraph" or "sentence"
RAG_RETRIEVAL_COUNT = 5  # How many chunks to retrieve per query
RAG_SIMILARITY_THRESHOLD = 0.7  # Minimum similarity score to consider
RAG_EMBEDDING_MODEL = "openai/text-embedding-3-small"  # or "anthropic/voyage-2"

# Multi-Agent Configuration
ENABLE_MULTI_AGENT = True  # Master switch for new architecture
SSBA_TIMEOUT = 30.0  # Story structure beat agent timeout
CBA_TIMEOUT = 25.0  # Chapter beat agent timeout
CEA_TIMEOUT = 35.0  # Context editor agent timeout
PA_TIMEOUT = 120.0  # Prose agent timeout (same as current)

# Story Structure
STORY_STRUCTURE_TYPE = "save_the_cat"  # "save_the_cat", "heros_journey", "three_act"
TOTAL_CHAPTERS = 30  # Default story length
```

---

## Cost Estimate

**Per Chapter (Chapters 2-30):**

| Agent | Tokens In | Tokens Out | Cost (Sonnet 3.5) |
|-------|-----------|------------|-------------------|
| SSBA Check-in | ~2,000 | ~500 | $0.008 |
| CBA | ~4,000 | ~1,500 | $0.017 |
| RAG Embeddings | ~3,000 | - | $0.001 |
| CEA | ~5,000 | ~1,800 | $0.020 |
| PA | ~8,000 | ~3,500 | $0.035 |
| Summary | ~2,500 | ~100 | $0.008 |
| **Total** | **~24,500** | **~7,400** | **~$0.089** |

**Current System:** ~$0.16/chapter
**New System:** ~$0.09/chapter (actually CHEAPER due to smaller focused calls!)

**Chapter 1 is slightly more expensive** (~$0.12) due to SSBA full story planning, but still cheaper than current system.

---

## Success Metrics

**How do we know this is working?**

1. **Consistency Score**
   - Track contradictions found by CEA
   - Goal: <1 contradiction per 10 chapters after training period

2. **Generation Time**
   - Target: <180s per chapter (95th percentile)
   - Current: ~145s average, ~280s worst case

3. **User Reports**
   - Track user feedback on story consistency
   - Goal: 80% of users report "very consistent" story

4. **Automated Tests**
   - Create test cases with intentional contradictions
   - Verify CEA catches 90%+ of them

---

## Migration Strategy

**How do we transition without breaking existing stories?**

### Option 1: Feature Flag (Recommended)
- Add `use_multi_agent` flag to session config
- Old sessions continue with current system
- New sessions use multi-agent system
- Gradual rollout: 10% → 50% → 100%

### Option 2: Parallel Systems
- Run both systems side-by-side
- Compare outputs for same prompts
- Switch when multi-agent matches or exceeds quality

### Option 3: Hard Cutover
- Deploy multi-agent system
- All new sessions use it
- Old sessions complete with old system

**Recommendation:** Option 1 with 2-week rollout period

---

## Open Questions

1. **Should CEA have authority to reject beat plans?**
   - Auto-fix and proceed (faster, might introduce new issues)
   - Alert and ask PA to handle gracefully (safer)
   - Block generation and alert developer (strictest)

2. **How to handle irreconcilable contradictions?**
   - Example: User chose "Charlie walks away" but he's in wheelchair
   - Option A: Ignore user choice, maintain consistency
   - Option B: Respect choice, retcon previous chapters in story bible
   - Option C: Acknowledge gracefully in prose: "Despite his injury, Charlie pushed himself to stand..."

3. **Should SSBA be allowed to modify story structure mid-story?**
   - Rigid: Lock story structure after Chapter 1
   - Flexible: Allow SSBA to adapt based on player choices
   - Hybrid: Allow minor adjustments, lock major beats

4. **What's the minimum context for CEA to be useful?**
   - Currently: Skip Chapter 1
   - Could skip Chapters 1-2? 1-3?
   - Or run CEA even on Chapter 2 with limited context?

5. **How to surface consistency checks to users?**
   - Hidden: Just fix silently (current plan)
   - Transparent: Show "consistency maintained" badge
   - Educational: Show what was caught and fixed (might break immersion)

---

## Next Steps

Please review this architecture and let me know:

1. ✅ Does this match your vision?
2. ✅ Any changes to agent responsibilities?
3. ❓ Which open questions need decisions?
4. ❓ Should we start with Phase 1 (RAG infrastructure)?
5. ❓ Do you want to test current fixes before starting multi-agent work?

Once you approve, I can start implementing Phase 1!
