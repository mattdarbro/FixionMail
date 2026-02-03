"""
Beat templates for different genres and story lengths.

Each template defines the structure for a complete standalone story.
"""

from typing import List, Dict, Any
import copy


class BeatTemplate:
    """A beat template defines the structure for a story."""

    def __init__(
        self,
        name: str,
        genre: str,
        total_words: int,
        beats: List[Dict[str, Any]],
        description: str = ""
    ):
        self.name = name
        self.genre = genre
        self.total_words = total_words
        self.beats = beats
        self.description = description

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "genre": self.genre,
            "total_words": self.total_words,
            "beats": self.beats,
            "description": self.description
        }


# ===== PACING STYLES =====
# These adjust how word counts are distributed across beats, particularly
# affecting the climax and resolution to create varied story rhythms.

PACING_STYLES = {
    "auto": {
        "id": "auto",
        "name": "Auto (AI Decides)",
        "description": "Let the Structure Agent choose the best pacing for this specific story.",
        "resolution_multiplier": 1.0,  # Not used - SSBA sets word targets directly
        "climax_multiplier": 1.0,
        "setup_multiplier": 1.0,
        "ending_guidance": "",  # SSBA generates its own
        "beat_guidance": {},
        "ai_controlled": True  # Flag indicating SSBA controls pacing
    },
    "hard_cut": {
        "id": "hard_cut",
        "name": "Hard Cut",
        "description": "End on or near the climax. Minimal wrap-up, maximum impact.",
        "resolution_multiplier": 0.4,  # Resolution gets 40% of normal words
        "climax_multiplier": 1.2,      # Climax gets 20% more words
        "setup_multiplier": 1.0,       # Setup unchanged
        "ending_guidance": """END ABRUPTLY after the climax. The story should feel like a hard cut to black.
- Resolution is 2-3 sentences MAX
- No epilogue, no "where are they now"
- End on action, dialogue, or a striking image
- Let the reader's imagination fill the silence
- Think: final frame of a Coen Brothers film""",
        "beat_guidance": {
            "resolution": "Minimal. One powerful final moment or image. No wrapping up loose ends.",
            "finale": "This IS the ending. Don't write past the climactic moment.",
            "new_equilibrium": "A single sentence showing the new state. Nothing more.",
            "return": "Brief. The journey ends mid-step, not at the doorstep."
        }
    },
    "classic": {
        "id": "classic",
        "name": "Classic",
        "description": "Balanced pacing with proper resolution. The default storytelling rhythm.",
        "resolution_multiplier": 1.0,
        "climax_multiplier": 1.0,
        "setup_multiplier": 1.0,
        "ending_guidance": """Provide satisfying closure with proper denouement.
- Resolve the main story question
- Show the emotional aftermath
- Brief glimpse of the new normal
- Classic three-act structure pacing""",
        "beat_guidance": {}
    },
    "lingering": {
        "id": "lingering",
        "name": "Lingering",
        "description": "Extended denouement. Savor the aftermath and emotional resonance.",
        "resolution_multiplier": 1.6,  # Resolution gets 60% more words
        "climax_multiplier": 0.9,      # Slightly shorter climax
        "setup_multiplier": 0.95,      # Slightly compressed setup
        "ending_guidance": """Let the ending BREATHE. Linger in the aftermath.
- Explore the emotional resonance of what happened
- Show characters processing, reflecting
- Small details that reveal the new normal
- Quiet moments after the storm
- Think: the last 20 minutes of a Terrence Malick film""",
        "beat_guidance": {
            "resolution": "Expanded. Take time with the aftermath. Small moments matter.",
            "finale": "Don't rush. Let characters and readers sit with what happened.",
            "new_equilibrium": "Explore the changed world. Multiple scenes showing the new balance.",
            "return": "The journey home is its own story. Savor the return."
        }
    },
    "twist_ending": {
        "id": "twist_ending",
        "name": "Twist Ending",
        "description": "Short resolution with a final revelation that recontextualizes everything.",
        "resolution_multiplier": 0.7,
        "climax_multiplier": 1.0,
        "setup_multiplier": 1.05,      # Slightly more setup to plant seeds
        "ending_guidance": """End with a TWIST that reframes the entire story.
- Resolution should be brief but contain a revelation
- The twist should feel inevitable in hindsight
- Plant subtle seeds earlier that pay off at the end
- The final line should land like a punch
- Think: O. Henry, Twilight Zone, "I see dead people" """,
        "beat_guidance": {
            "resolution": "Brief setup for the twist, then the revelation. End immediately after.",
            "finale": "The twist IS the finale. Everything pivots on the final reveal.",
            "new_equilibrium": "The 'new equilibrium' is the reader's shifted understanding."
        }
    },
    "open_ending": {
        "id": "open_ending",
        "name": "Open Ending",
        "description": "Ambiguous conclusion. Questions linger, reader fills the gaps.",
        "resolution_multiplier": 0.5,
        "climax_multiplier": 1.1,
        "setup_multiplier": 1.0,
        "ending_guidance": """Leave the ending OPEN and ambiguous.
- Don't resolve everything
- End on a question, choice, or threshold moment
- Multiple interpretations should be valid
- Trust the reader to find their own meaning
- Think: Inception's spinning top, The Sopranos finale""",
        "beat_guidance": {
            "resolution": "Deliberately incomplete. The story ends, but the question remains.",
            "finale": "End at a crossroads, not at the destination.",
            "new_equilibrium": "Suggest multiple possible equilibriums. Don't choose one."
        }
    },
    "circular": {
        "id": "circular",
        "name": "Circular",
        "description": "End where you began, but transformed. Echo the opening.",
        "resolution_multiplier": 0.8,
        "climax_multiplier": 1.0,
        "setup_multiplier": 1.1,       # More setup to establish the circle
        "ending_guidance": """Create a CIRCULAR structure that echoes the opening.
- Final scene mirrors the opening scene
- Same location, action, or dialogue—but transformed
- Show how everything has changed (or stayed the same)
- The echo should feel meaningful, not gimmicky
- Think: "The Great Gatsby" returning to the green light""",
        "beat_guidance": {
            "resolution": "Return to the opening scene/moment with new eyes.",
            "finale": "Echo the beginning. Same but different.",
            "new_equilibrium": "The circle closes. We're back where we started, transformed."
        }
    }
}


def get_pacing_style(style_id: str) -> Dict[str, Any]:
    """Get a pacing style by ID. Returns 'classic' if not found."""
    return PACING_STYLES.get(style_id, PACING_STYLES["classic"])


def list_pacing_styles() -> List[Dict[str, str]]:
    """List all available pacing styles for UI selection."""
    return [
        {
            "id": style["id"],
            "name": style["name"],
            "description": style["description"]
        }
        for style in PACING_STYLES.values()
    ]


def apply_pacing_to_template(
    template: BeatTemplate,
    pacing_style: str = "classic"
) -> BeatTemplate:
    """
    Apply a pacing style to a beat template, adjusting word targets.

    Args:
        template: The original beat template
        pacing_style: ID of the pacing style to apply

    Returns:
        A new BeatTemplate with adjusted word targets
    """
    style = get_pacing_style(pacing_style)

    if pacing_style == "classic":
        return template  # No adjustment needed

    # Deep copy to avoid modifying original
    new_beats = copy.deepcopy(template.beats)

    # Identify beat types by name patterns
    resolution_patterns = ["resolution", "finale", "return", "new_equilibrium", "final_image", "return_with_elixir"]
    climax_patterns = ["crisis", "ordeal", "battle", "climax", "all_is_lost", "revelation", "self_revelation"]
    setup_patterns = ["opening", "setup", "ordinary_world", "weakness", "hook", "incident"]

    total_adjustment = 0

    for beat in new_beats:
        beat_name = beat.get("beat_name", "").lower()
        original_words = beat.get("word_target", 0)

        # Determine beat type and apply multiplier
        if any(pattern in beat_name for pattern in resolution_patterns):
            multiplier = style["resolution_multiplier"]
            # Add specific beat guidance if available
            for pattern in resolution_patterns:
                if pattern in beat_name and pattern in style.get("beat_guidance", {}):
                    beat["pacing_guidance"] = style["beat_guidance"][pattern]
                    break
        elif any(pattern in beat_name for pattern in climax_patterns):
            multiplier = style["climax_multiplier"]
        elif any(pattern in beat_name for pattern in setup_patterns):
            multiplier = style["setup_multiplier"]
        else:
            multiplier = 1.0

        new_words = int(original_words * multiplier)
        adjustment = new_words - original_words
        total_adjustment += adjustment
        beat["word_target"] = new_words

    # Redistribute any word count changes to maintain total
    # (borrow from/give to middle beats)
    if total_adjustment != 0:
        middle_beats = [b for b in new_beats if not any(
            pattern in b.get("beat_name", "").lower()
            for pattern in resolution_patterns + setup_patterns
        )]
        if middle_beats:
            adjustment_per_beat = -total_adjustment // len(middle_beats)
            for beat in middle_beats:
                beat["word_target"] = max(100, beat["word_target"] + adjustment_per_beat)

    # Create new template with adjusted beats
    return BeatTemplate(
        name=f"{template.name}_{pacing_style}",
        genre=template.genre,
        total_words=template.total_words,
        beats=new_beats,
        description=f"{template.description} (Pacing: {style['name']})"
    )


def get_pacing_guidance(pacing_style: str) -> str:
    """Get the ending guidance text for a pacing style."""
    style = get_pacing_style(pacing_style)
    return style.get("ending_guidance", "")


# ===== FREE TIER TEMPLATES (1500 words) =====

FREE_SCIFI_TEMPLATE = BeatTemplate(
    name="scifi_short",
    genre="sci-fi",
    total_words=1800,
    description="Concise sci-fi story with discovery and resolution",
    beats=[
        {
            "beat_number": 1,
            "beat_name": "opening_hook",
            "word_target": 400,
            "description": "Establish setting and protagonist, introduce intriguing element",
            "guidance": "Ground reader in sci-fi world. Present protagonist's normal. Hint at mystery/problem."
        },
        {
            "beat_number": 2,
            "beat_name": "discovery",
            "word_target": 450,
            "description": "Protagonist discovers or encounters the core mystery/problem",
            "guidance": "Raise stakes. Show protagonist's reaction. Complicate the situation."
        },
        {
            "beat_number": 3,
            "beat_name": "crisis",
            "word_target": 400,
            "description": "Problem intensifies, protagonist must make a choice",
            "guidance": "Peak tension. Protagonist faces decision or realization."
        },
        {
            "beat_number": 4,
            "beat_name": "resolution",
            "word_target": 250,
            "description": "Resolution of immediate problem, with emotional or thematic closure",
            "guidance": "Satisfy story question. Emotional landing. Hint at larger world continuing."
        }
    ]
)

FREE_MYSTERY_TEMPLATE = BeatTemplate(
    name="mystery_short",
    genre="mystery",
    total_words=1800,
    description="Quick mystery with clue discovery and solution",
    beats=[
        {
            "beat_number": 1,
            "beat_name": "incident",
            "word_target": 350,
            "description": "Present the mystery or crime",
            "guidance": "Establish what's wrong. Introduce detective/protagonist."
        },
        {
            "beat_number": 2,
            "beat_name": "investigation",
            "word_target": 500,
            "description": "Gather clues, interview, discover leads",
            "guidance": "Show protagonist's method. Plant clues for reader. Red herring optional."
        },
        {
            "beat_number": 3,
            "beat_name": "revelation",
            "word_target": 400,
            "description": "Key insight or breakthrough",
            "guidance": "Protagonist connects the dots. Aha moment."
        },
        {
            "beat_number": 4,
            "beat_name": "solution",
            "word_target": 250,
            "description": "Mystery solved, explanation",
            "guidance": "Reveal answer. Show protagonist's satisfaction or reflection."
        }
    ]
)

FREE_ROMANCE_TEMPLATE = BeatTemplate(
    name="romance_short",
    genre="romance",
    total_words=1800,
    description="Sweet romantic moment or connection",
    beats=[
        {
            "beat_number": 1,
            "beat_name": "setup",
            "word_target": 400,
            "description": "Introduce characters and situation",
            "guidance": "Show protagonist's emotional state. Set up meeting or interaction."
        },
        {
            "beat_number": 2,
            "beat_name": "connection",
            "word_target": 450,
            "description": "Romantic interaction or deepening bond",
            "guidance": "Chemistry, vulnerability, or shared moment. Show attraction/connection."
        },
        {
            "beat_number": 3,
            "beat_name": "complication",
            "word_target": 400,
            "description": "Obstacle or misunderstanding",
            "guidance": "Something threatens the connection. Internal or external conflict."
        },
        {
            "beat_number": 4,
            "beat_name": "resolution",
            "word_target": 250,
            "description": "Overcome obstacle, emotional payoff",
            "guidance": "Vulnerability wins. Sweet or hopeful ending. Connection strengthened."
        }
    ]
)

FREE_FANTASY_TEMPLATE = BeatTemplate(
    name="fantasy_short",
    genre="fantasy",
    total_words=1800,
    description="Magical adventure with wonder and resolution",
    beats=[
        {
            "beat_number": 1,
            "beat_name": "ordinary_world",
            "word_target": 400,
            "description": "Establish fantasy world and protagonist",
            "guidance": "Show the magic system or fantastical elements. Protagonist's daily life."
        },
        {
            "beat_number": 2,
            "beat_name": "magical_disruption",
            "word_target": 450,
            "description": "Magical problem or quest emerges",
            "guidance": "Something goes wrong with magic, or a quest appears. Stakes established."
        },
        {
            "beat_number": 3,
            "beat_name": "trials",
            "word_target": 400,
            "description": "Face challenges, use magic or skills",
            "guidance": "Protagonist must overcome obstacles. Show their growth or cleverness."
        },
        {
            "beat_number": 4,
            "beat_name": "triumph",
            "word_target": 250,
            "description": "Quest complete, magic restored",
            "guidance": "Victory and wonder. Show what was gained or learned."
        }
    ]
)

FREE_HORROR_TEMPLATE = BeatTemplate(
    name="horror_short",
    genre="horror",
    total_words=1800,
    description="Suspenseful horror with mounting dread",
    beats=[
        {
            "beat_number": 1,
            "beat_name": "unease",
            "word_target": 400,
            "description": "Normal situation with subtle wrongness",
            "guidance": "Something feels off. Build atmosphere. Protagonist notices small details."
        },
        {
            "beat_number": 2,
            "beat_name": "escalation",
            "word_target": 450,
            "description": "Threat becomes clear, fear intensifies",
            "guidance": "The horror reveals itself. Tension rises. Protagonist reacts."
        },
        {
            "beat_number": 3,
            "beat_name": "confrontation",
            "word_target": 400,
            "description": "Face the horror directly",
            "guidance": "Peak terror. Protagonist must act or flee. Visceral details."
        },
        {
            "beat_number": 4,
            "beat_name": "aftermath",
            "word_target": 250,
            "description": "Escape or resolution, lingering unease",
            "guidance": "Survive but changed. Optional twist ending. Lasting dread."
        }
    ]
)

FREE_DRAMA_TEMPLATE = BeatTemplate(
    name="drama_short",
    genre="drama",
    total_words=1800,
    description="Character-focused emotional journey",
    beats=[
        {
            "beat_number": 1,
            "beat_name": "status_quo",
            "word_target": 400,
            "description": "Establish character's life and inner conflict",
            "guidance": "Show their world, relationships, and emotional state."
        },
        {
            "beat_number": 2,
            "beat_name": "catalyst",
            "word_target": 450,
            "description": "Event that forces choice or change",
            "guidance": "External event triggers internal crisis. Stakes are personal."
        },
        {
            "beat_number": 3,
            "beat_name": "struggle",
            "word_target": 400,
            "description": "Character grapples with decision",
            "guidance": "Internal conflict. Relationships tested. Difficult choices."
        },
        {
            "beat_number": 4,
            "beat_name": "resolution",
            "word_target": 250,
            "description": "Character makes choice, finds clarity",
            "guidance": "Emotional truth revealed. Growth or acceptance. Bittersweet okay."
        }
    ]
)

FREE_WESTERN_TEMPLATE = BeatTemplate(
    name="western_short",
    genre="western",
    total_words=1800,
    description="Frontier justice and moral choices",
    beats=[
        {
            "beat_number": 1,
            "beat_name": "frontier_life",
            "word_target": 400,
            "description": "Establish western setting and protagonist",
            "guidance": "Show the harsh frontier. Protagonist's skills and code."
        },
        {
            "beat_number": 2,
            "beat_name": "trouble_arrives",
            "word_target": 450,
            "description": "Outlaws, conflict, or moral dilemma",
            "guidance": "Challenge to peace or justice. Stakes for community."
        },
        {
            "beat_number": 3,
            "beat_name": "showdown",
            "word_target": 400,
            "description": "Confrontation or decisive action",
            "guidance": "Protagonist faces the threat. Action and tension."
        },
        {
            "beat_number": 4,
            "beat_name": "new_dawn",
            "word_target": 250,
            "description": "Justice served, order restored",
            "guidance": "Resolution but frontier continues. Moral clarity."
        }
    ]
)

FREE_HISTORICAL_TEMPLATE = BeatTemplate(
    name="historical_short",
    genre="historical",
    total_words=1800,
    description="Historical moment with personal stakes",
    beats=[
        {
            "beat_number": 1,
            "beat_name": "period_setting",
            "word_target": 400,
            "description": "Establish time period and protagonist's world",
            "guidance": "Rich historical detail. Social context. Character's place in history."
        },
        {
            "beat_number": 2,
            "beat_name": "historical_event",
            "word_target": 450,
            "description": "Major event impacts protagonist",
            "guidance": "Historical moment meets personal story. Stakes become real."
        },
        {
            "beat_number": 3,
            "beat_name": "personal_crisis",
            "word_target": 400,
            "description": "Character must navigate historical challenges",
            "guidance": "Personal and historical stakes converge. Difficult choices."
        },
        {
            "beat_number": 4,
            "beat_name": "legacy",
            "word_target": 250,
            "description": "Resolution with historical significance",
            "guidance": "Personal story resolves. Hint at historical impact."
        }
    ]
)


# ===== PREMIUM TIER TEMPLATES (4500 words) =====

PREMIUM_SCIFI_ADVENTURE = BeatTemplate(
    name="scifi_adventure_full",
    genre="sci-fi",
    total_words=4500,
    description="Full sci-fi adventure with world-building and action",
    beats=[
        {
            "beat_number": 1,
            "beat_name": "opening_hook",
            "word_target": 500,
            "description": "Establish world, protagonist, and normal",
            "guidance": "Rich world-building. Show protagonist's skills/personality. Hint at adventure to come."
        },
        {
            "beat_number": 2,
            "beat_name": "inciting_incident",
            "word_target": 500,
            "description": "Call to adventure or problem emerges",
            "guidance": "Disrupt the normal. Present the challenge. Show stakes."
        },
        {
            "beat_number": 3,
            "beat_name": "rising_action",
            "word_target": 500,
            "description": "Protagonist engages, complications arise",
            "guidance": "Active protagonist. Obstacles emerge. World expands."
        },
        {
            "beat_number": 4,
            "beat_name": "first_revelation",
            "word_target": 500,
            "description": "Discovery or twist that changes understanding",
            "guidance": "New information. Paradigm shift. Stakes raise."
        },
        {
            "beat_number": 5,
            "beat_name": "midpoint_crisis",
            "word_target": 600,
            "description": "Major setback or challenge",
            "guidance": "All seems lost OR false victory. Emotional low or high."
        },
        {
            "beat_number": 6,
            "beat_name": "renewed_push",
            "word_target": 600,
            "description": "Protagonist adapts, new approach",
            "guidance": "Character growth. New strategy. Building to climax."
        },
        {
            "beat_number": 7,
            "beat_name": "climax",
            "word_target": 500,
            "description": "Confrontation or final challenge",
            "guidance": "Peak action/tension. Protagonist uses what they've learned."
        },
        {
            "beat_number": 8,
            "beat_name": "resolution",
            "word_target": 500,
            "description": "Immediate aftermath and victory/outcome",
            "guidance": "Show results. Emotional payoff. Consequences."
        },
        {
            "beat_number": 9,
            "beat_name": "denouement",
            "word_target": 300,
            "description": "Return to new normal, reflection",
            "guidance": "Show growth. Thematic closure. World continues."
        }
    ]
)

PREMIUM_MYSTERY_NOIR = BeatTemplate(
    name="mystery_noir_full",
    genre="mystery",
    total_words=4500,
    description="Full noir mystery with investigation and twists",
    beats=[
        {
            "beat_number": 1,
            "beat_name": "setup",
            "word_target": 500,
            "description": "Introduce detective and world",
            "guidance": "Noir atmosphere. Show detective's life/personality."
        },
        {
            "beat_number": 2,
            "beat_name": "case_arrives",
            "word_target": 500,
            "description": "Crime or mystery presented",
            "guidance": "The hook. Why this case matters. Initial details."
        },
        {
            "beat_number": 3,
            "beat_name": "first_clues",
            "word_target": 500,
            "description": "Investigation begins, gather evidence",
            "guidance": "Detective method. Plant clues. Introduce suspects."
        },
        {
            "beat_number": 4,
            "beat_name": "red_herring",
            "word_target": 500,
            "description": "False lead or misdirection",
            "guidance": "Seems promising but wrong. Keep reader guessing."
        },
        {
            "beat_number": 5,
            "beat_name": "complication",
            "word_target": 600,
            "description": "New crime, threat, or setback",
            "guidance": "Stakes raise. Detective in danger or case gets personal."
        },
        {
            "beat_number": 6,
            "beat_name": "breakthrough",
            "word_target": 600,
            "description": "Key insight or evidence found",
            "guidance": "Pieces come together. Detective sees the pattern."
        },
        {
            "beat_number": 7,
            "beat_name": "confrontation",
            "word_target": 500,
            "description": "Confront culprit or reveal truth",
            "guidance": "Tension peaks. Truth comes out. Danger."
        },
        {
            "beat_number": 8,
            "beat_name": "resolution",
            "word_target": 500,
            "description": "Case closed, justice or consequence",
            "guidance": "Wrap up loose ends. Show outcome."
        },
        {
            "beat_number": 9,
            "beat_name": "reflection",
            "word_target": 300,
            "description": "Detective reflects, returns to life",
            "guidance": "Noir wisdom. Thematic landing. Bitter or sweet."
        }
    ]
)

PREMIUM_ROMANCE_FULL = BeatTemplate(
    name="romance_full",
    genre="romance",
    total_words=4500,
    description="Complete romantic arc with emotional depth",
    beats=[
        {
            "beat_number": 1,
            "beat_name": "introduction",
            "word_target": 500,
            "description": "Introduce protagonist and their world",
            "guidance": "Show protagonist's life, emotional state, desires."
        },
        {
            "beat_number": 2,
            "beat_name": "meet_cute",
            "word_target": 500,
            "description": "First meeting or meaningful interaction",
            "guidance": "Chemistry. Spark. Interesting dynamic."
        },
        {
            "beat_number": 3,
            "beat_name": "growing_connection",
            "word_target": 500,
            "description": "Spend time together, bond deepens",
            "guidance": "Vulnerability. Shared moments. Attraction builds."
        },
        {
            "beat_number": 4,
            "beat_name": "first_barrier",
            "word_target": 500,
            "description": "Internal resistance or external obstacle",
            "guidance": "Fear, past hurt, circumstances. Tension."
        },
        {
            "beat_number": 5,
            "beat_name": "turning_point",
            "word_target": 600,
            "description": "Breakthrough moment or confession",
            "guidance": "Emotional honesty. Risk taken. Relationship shifts."
        },
        {
            "beat_number": 6,
            "beat_name": "complication",
            "word_target": 600,
            "description": "Misunderstanding or serious obstacle",
            "guidance": "Something threatens to tear them apart. Dark night."
        },
        {
            "beat_number": 7,
            "beat_name": "realization",
            "word_target": 500,
            "description": "Character growth, understanding what matters",
            "guidance": "Internal change. Clarity about feelings."
        },
        {
            "beat_number": 8,
            "beat_name": "grand_gesture",
            "word_target": 500,
            "description": "One or both take decisive action",
            "guidance": "Vulnerability. Risk. Putting it all on the line."
        },
        {
            "beat_number": 9,
            "beat_name": "resolution",
            "word_target": 300,
            "description": "Together, emotional payoff",
            "guidance": "Satisfying ending. Hope or happiness. New beginning."
        }
    ]
)

PREMIUM_SITCOM_STYLE = BeatTemplate(
    name="sitcom_full",
    genre="sitcom",
    total_words=4500,
    description="Comedy with escalating chaos and warm resolution",
    beats=[
        {
            "beat_number": 1,
            "beat_name": "normal_day",
            "word_target": 500,
            "description": "Establish characters and normal situation",
            "guidance": "Show relationships. Light humor. Set baseline."
        },
        {
            "beat_number": 2,
            "beat_name": "disruption",
            "word_target": 500,
            "description": "Something goes wrong or unusual happens",
            "guidance": "Comic premise. Small problem that will escalate."
        },
        {
            "beat_number": 3,
            "beat_name": "attempted_fix",
            "word_target": 500,
            "description": "Try to solve it, makes it worse",
            "guidance": "Character flaws cause problems. Escalation."
        },
        {
            "beat_number": 4,
            "beat_name": "escalation",
            "word_target": 500,
            "description": "Problem grows, more chaos",
            "guidance": "Snowball effect. Multiple characters involved."
        },
        {
            "beat_number": 5,
            "beat_name": "peak_chaos",
            "word_target": 600,
            "description": "Everything falls apart hilariously",
            "guidance": "Maximum comedy. Multiple threads colliding."
        },
        {
            "beat_number": 6,
            "beat_name": "moment_of_truth",
            "word_target": 600,
            "description": "Honest moment amidst the chaos",
            "guidance": "Heart. Character insight. Why we care."
        },
        {
            "beat_number": 7,
            "beat_name": "resolution",
            "word_target": 500,
            "description": "Problem solved or accepted",
            "guidance": "Fix it together. Teamwork or acceptance."
        },
        {
            "beat_number": 8,
            "beat_name": "new_normal",
            "word_target": 500,
            "description": "Return to normalish, lessons learned",
            "guidance": "Back to baseline but slightly changed."
        },
        {
            "beat_number": 9,
            "beat_name": "tag",
            "word_target": 300,
            "description": "Callback joke or sweet moment",
            "guidance": "Button on the episode. Warm ending."
        }
    ]
)

PREMIUM_FANTASY_EPIC = BeatTemplate(
    name="fantasy_epic",
    genre="fantasy",
    total_words=4500,
    description="Epic fantasy quest with magic and wonder",
    beats=[
        {
            "beat_number": 1,
            "beat_name": "magical_world",
            "word_target": 500,
            "description": "Rich fantasy world-building, establish protagonist",
            "guidance": "Show magic system, cultures, and wonder. Protagonist's place in this world."
        },
        {
            "beat_number": 2,
            "beat_name": "call_to_adventure",
            "word_target": 500,
            "description": "Quest or magical threat emerges",
            "guidance": "Ancient prophecy, dark magic rising, or quest appears. Stakes for the realm."
        },
        {
            "beat_number": 3,
            "beat_name": "journey_begins",
            "word_target": 500,
            "description": "Set out, gather allies or items",
            "guidance": "World expands. Meet companions. Early challenges."
        },
        {
            "beat_number": 4,
            "beat_name": "trials",
            "word_target": 500,
            "description": "Face magical obstacles or enemies",
            "guidance": "Test protagonist's courage and abilities. Use magic creatively."
        },
        {
            "beat_number": 5,
            "beat_name": "dark_moment",
            "word_target": 600,
            "description": "Major setback or betrayal",
            "guidance": "All seems lost. Dark magic prevails or ally falls. Emotional low."
        },
        {
            "beat_number": 6,
            "beat_name": "inner_magic",
            "word_target": 600,
            "description": "Discover inner strength or true magic",
            "guidance": "Protagonist finds deeper power or understanding. Character growth."
        },
        {
            "beat_number": 7,
            "beat_name": "final_battle",
            "word_target": 500,
            "description": "Confront dark force or complete quest",
            "guidance": "Epic magical confrontation. Use all they've learned."
        },
        {
            "beat_number": 8,
            "beat_name": "victory",
            "word_target": 500,
            "description": "Quest complete, magic restored",
            "guidance": "Triumph and cost. Show what was saved."
        },
        {
            "beat_number": 9,
            "beat_name": "new_age",
            "word_target": 300,
            "description": "Return changed, new era begins",
            "guidance": "Hero's transformation. Magic world continues. Hopeful ending."
        }
    ]
)

PREMIUM_HORROR_DESCENT = BeatTemplate(
    name="horror_descent",
    genre="horror",
    total_words=4500,
    description="Slow-burn horror with psychological depth",
    beats=[
        {
            "beat_number": 1,
            "beat_name": "normalcy",
            "word_target": 500,
            "description": "Establish normal life, subtle unease",
            "guidance": "Grounded reality. Small details that feel wrong. Build atmosphere."
        },
        {
            "beat_number": 2,
            "beat_name": "first_signs",
            "word_target": 500,
            "description": "Unexplained events, growing dread",
            "guidance": "Things that can't be explained away. Protagonist's concern."
        },
        {
            "beat_number": 3,
            "beat_name": "investigation",
            "word_target": 500,
            "description": "Protagonist seeks answers",
            "guidance": "Research, ask questions. Uncover dark history. Tension builds."
        },
        {
            "beat_number": 4,
            "beat_name": "revelation",
            "word_target": 500,
            "description": "True nature of horror revealed",
            "guidance": "Understanding makes it worse. Cannot be denied now."
        },
        {
            "beat_number": 5,
            "beat_name": "escalation",
            "word_target": 600,
            "description": "Horror becomes aggressive, personal",
            "guidance": "Direct threats. Isolation. Fear peaks. Visceral details."
        },
        {
            "beat_number": 6,
            "beat_name": "breaking_point",
            "word_target": 600,
            "description": "Protagonist's reality fractures",
            "guidance": "Can't trust perceptions. Psychological terror. Desperation."
        },
        {
            "beat_number": 7,
            "beat_name": "confrontation",
            "word_target": 500,
            "description": "Face the horror directly",
            "guidance": "No escape but through. Survival instinct. Peak terror."
        },
        {
            "beat_number": 8,
            "beat_name": "aftermath",
            "word_target": 500,
            "description": "Survive but forever changed",
            "guidance": "Escaped but scarred. Ambiguous victory."
        },
        {
            "beat_number": 9,
            "beat_name": "lingering_dread",
            "word_target": 300,
            "description": "Return to life, but horror lingers",
            "guidance": "Never truly over. Subtle hint it continues. Lasting unease."
        }
    ]
)

PREMIUM_DRAMA_DEEP = BeatTemplate(
    name="drama_deep",
    genre="drama",
    total_words=4500,
    description="Rich character drama with emotional complexity",
    beats=[
        {
            "beat_number": 1,
            "beat_name": "life_portrait",
            "word_target": 500,
            "description": "Deep dive into character's world",
            "guidance": "Relationships, work, dreams, conflicts. Rich detail."
        },
        {
            "beat_number": 2,
            "beat_name": "inciting_incident",
            "word_target": 500,
            "description": "Event disrupts equilibrium",
            "guidance": "Death, diagnosis, revelation, opportunity. Stakes are personal."
        },
        {
            "beat_number": 3,
            "beat_name": "denial_resistance",
            "word_target": 500,
            "description": "Character resists change",
            "guidance": "Old patterns. Fear of change. Conflict with others."
        },
        {
            "beat_number": 4,
            "beat_name": "forced_engagement",
            "word_target": 500,
            "description": "Can't avoid the issue anymore",
            "guidance": "Must face it. Complications arise. Relationships strain."
        },
        {
            "beat_number": 5,
            "beat_name": "crisis_point",
            "word_target": 600,
            "description": "Everything comes to a head",
            "guidance": "Emotional explosion. Truth revealed. Relationships break or deepen."
        },
        {
            "beat_number": 6,
            "beat_name": "dark_night",
            "word_target": 600,
            "description": "Lowest point, facing self",
            "guidance": "Alone with truth. Internal reckoning. Vulnerability."
        },
        {
            "beat_number": 7,
            "beat_name": "choice",
            "word_target": 500,
            "description": "Character makes defining decision",
            "guidance": "Active choice. Growth or acceptance. Not easy."
        },
        {
            "beat_number": 8,
            "beat_name": "reconciliation",
            "word_target": 500,
            "description": "Repair relationships or find peace",
            "guidance": "Honest conversations. Forgiveness or letting go."
        },
        {
            "beat_number": 9,
            "beat_name": "new_understanding",
            "word_target": 300,
            "description": "Character in new equilibrium",
            "guidance": "Changed but authentic. Bittersweet okay. Earned wisdom."
        }
    ]
)

PREMIUM_WESTERN_EPIC = BeatTemplate(
    name="western_epic",
    genre="western",
    total_words=4500,
    description="Sweeping western with moral complexity",
    beats=[
        {
            "beat_number": 1,
            "beat_name": "frontier_world",
            "word_target": 500,
            "description": "Establish harsh frontier reality",
            "guidance": "Landscape, settlements, danger. Protagonist's reputation and code."
        },
        {
            "beat_number": 2,
            "beat_name": "trouble_brewing",
            "word_target": 500,
            "description": "Outlaws, land dispute, or injustice",
            "guidance": "Threat to peace. Stakes for community. Moral dimensions."
        },
        {
            "beat_number": 3,
            "beat_name": "investigation",
            "word_target": 500,
            "description": "Uncover the truth, track the threat",
            "guidance": "Protagonist's skills shine. Meet allies and enemies."
        },
        {
            "beat_number": 4,
            "beat_name": "complications",
            "word_target": 500,
            "description": "Moral gray areas, conflicting loyalties",
            "guidance": "Not simple good vs evil. Personal stakes rise."
        },
        {
            "beat_number": 5,
            "beat_name": "rising_violence",
            "word_target": 600,
            "description": "Conflict escalates, blood spilled",
            "guidance": "Action sequence. Cost of violence shown. Tension peaks."
        },
        {
            "beat_number": 6,
            "beat_name": "moral_reckoning",
            "word_target": 600,
            "description": "Protagonist faces what justice means",
            "guidance": "Internal conflict. What's right vs what's legal. Character depth."
        },
        {
            "beat_number": 7,
            "beat_name": "showdown",
            "word_target": 500,
            "description": "Final confrontation",
            "guidance": "Climactic gunfight or standoff. Skills and resolve tested."
        },
        {
            "beat_number": 8,
            "beat_name": "aftermath",
            "word_target": 500,
            "description": "Justice served, order restored",
            "guidance": "Resolution. Show cost. Community changed."
        },
        {
            "beat_number": 9,
            "beat_name": "riding_on",
            "word_target": 300,
            "description": "Protagonist moves forward",
            "guidance": "Frontier continues. Protagonist's code tested but intact. Sunset ride."
        }
    ]
)

PREMIUM_HISTORICAL_SAGA = BeatTemplate(
    name="historical_saga",
    genre="historical",
    total_words=4500,
    description="Rich historical epic with personal and political stakes",
    beats=[
        {
            "beat_number": 1,
            "beat_name": "period_immersion",
            "word_target": 500,
            "description": "Deep historical world-building",
            "guidance": "Social structures, customs, tensions. Character's place in history."
        },
        {
            "beat_number": 2,
            "beat_name": "historical_forces",
            "word_target": 500,
            "description": "Major historical events begin",
            "guidance": "War, revolution, social change. Personal life intersects with history."
        },
        {
            "beat_number": 3,
            "beat_name": "personal_impact",
            "word_target": 500,
            "description": "History affects protagonist directly",
            "guidance": "Can't stay neutral. Family, livelihood, beliefs at stake."
        },
        {
            "beat_number": 4,
            "beat_name": "difficult_choices",
            "word_target": 500,
            "description": "Navigate historical and moral complexity",
            "guidance": "Period-appropriate dilemmas. Loyalty vs conscience."
        },
        {
            "beat_number": 5,
            "beat_name": "historical_climax",
            "word_target": 600,
            "description": "Major historical event peaks",
            "guidance": "Battle, uprising, trial. Protagonist in the thick of it."
        },
        {
            "beat_number": 6,
            "beat_name": "personal_crisis",
            "word_target": 600,
            "description": "Character faces defining moment",
            "guidance": "Individual choice matters. Risk everything. Courage or sacrifice."
        },
        {
            "beat_number": 7,
            "beat_name": "resolution",
            "word_target": 500,
            "description": "Historical and personal arcs conclude",
            "guidance": "Outcome shown. Individual role in larger history."
        },
        {
            "beat_number": 8,
            "beat_name": "aftermath",
            "word_target": 500,
            "description": "New historical reality, personal cost",
            "guidance": "World changed. Show what was gained and lost."
        },
        {
            "beat_number": 9,
            "beat_name": "legacy",
            "word_target": 300,
            "description": "Long view of impact",
            "guidance": "Historical significance. Personal story's place in larger narrative."
        }
    ]
)


# ===== STORY STRUCTURE TEMPLATES =====
# These are meta-templates based on famous storytelling frameworks

# Save the Cat! Beat Sheet (Blake Snyder) - Adapted for short stories
SAVE_THE_CAT_SHORT = BeatTemplate(
    name="save_the_cat_short",
    genre="universal",
    total_words=1800,
    description="Blake Snyder's Save the Cat structure adapted for short fiction",
    beats=[
        {
            "beat_number": 1,
            "beat_name": "opening_image_and_setup",
            "word_target": 300,
            "description": "Opening Image + Set-up: Show protagonist's world before change",
            "guidance": "Establish 'before' snapshot. Show protagonist's flaw or want. Include a 'save the cat' moment that makes us root for them."
        },
        {
            "beat_number": 2,
            "beat_name": "catalyst_and_debate",
            "word_target": 350,
            "description": "Catalyst + Debate: Life-changing moment and hesitation",
            "guidance": "Something disrupts their world. Protagonist resists or debates the call. Stakes become clear."
        },
        {
            "beat_number": 3,
            "beat_name": "break_into_two",
            "word_target": 350,
            "description": "Break Into Two + Fun and Games: Enter new world, explore premise",
            "guidance": "Protagonist commits and enters Act 2. Promise of the premise - give readers what they came for."
        },
        {
            "beat_number": 4,
            "beat_name": "midpoint_to_all_is_lost",
            "word_target": 300,
            "description": "Midpoint + All Is Lost: False victory/defeat leads to dark moment",
            "guidance": "Stakes raise at midpoint. Then everything falls apart. Dark Night of the Soul."
        },
        {
            "beat_number": 5,
            "beat_name": "finale",
            "word_target": 200,
            "description": "Break Into Three + Final Image: Apply lesson, show transformation",
            "guidance": "Protagonist uses what they learned. New solution. Final image mirrors opening but shows change."
        }
    ]
)

SAVE_THE_CAT_PREMIUM = BeatTemplate(
    name="save_the_cat_premium",
    genre="universal",
    total_words=4500,
    description="Full Blake Snyder Save the Cat beat sheet",
    beats=[
        {
            "beat_number": 1,
            "beat_name": "opening_image",
            "word_target": 300,
            "description": "Opening Image: Visual 'before' snapshot of protagonist's world",
            "guidance": "Tone-setting image. Show the world before transformation. Hint at theme."
        },
        {
            "beat_number": 2,
            "beat_name": "setup",
            "word_target": 400,
            "description": "Set-Up: Establish protagonist's world and what's missing",
            "guidance": "Introduce protagonist and supporting cast. Show their want vs need. Plant story elements."
        },
        {
            "beat_number": 3,
            "beat_name": "theme_stated",
            "word_target": 200,
            "description": "Theme Stated: Someone hints at the story's moral",
            "guidance": "Often dialogue where someone tells protagonist what they need to learn. Protagonist doesn't get it yet."
        },
        {
            "beat_number": 4,
            "beat_name": "catalyst",
            "word_target": 400,
            "description": "Catalyst: The moment that changes everything",
            "guidance": "Life-altering event. Can't go back to normal after this. Clear inciting incident."
        },
        {
            "beat_number": 5,
            "beat_name": "debate",
            "word_target": 400,
            "description": "Debate: Protagonist questions whether to act",
            "guidance": "Should I go? What should I do? Last chance to remain in comfort zone. Building pressure."
        },
        {
            "beat_number": 6,
            "beat_name": "break_into_two",
            "word_target": 350,
            "description": "Break Into Two: Protagonist commits to action",
            "guidance": "Decisive action. Leaves old world behind. Enters Act 2 upside-down world."
        },
        {
            "beat_number": 7,
            "beat_name": "b_story",
            "word_target": 300,
            "description": "B Story: Secondary relationship that carries theme",
            "guidance": "New character or relationship. Often love interest or mentor. Discusses theme differently."
        },
        {
            "beat_number": 8,
            "beat_name": "fun_and_games",
            "word_target": 600,
            "description": "Fun and Games: The promise of the premise",
            "guidance": "What the audience came for. Genre-specific fun. Protagonist exploring new world. Successes."
        },
        {
            "beat_number": 9,
            "beat_name": "midpoint",
            "word_target": 400,
            "description": "Midpoint: False victory or false defeat",
            "guidance": "Stakes raise. Party's over or seeming success. Connect A and B stories. Time clock starts."
        },
        {
            "beat_number": 10,
            "beat_name": "bad_guys_close_in",
            "word_target": 500,
            "description": "Bad Guys Close In: Forces regroup, internal doubts surface",
            "guidance": "External pressure mounts. Team fractures. Self-doubt. Everything falls apart."
        },
        {
            "beat_number": 11,
            "beat_name": "all_is_lost",
            "word_target": 300,
            "description": "All Is Lost: The opposite of the Midpoint",
            "guidance": "False defeat (if midpoint was victory). Whiff of death - something dies. Lowest point."
        },
        {
            "beat_number": 12,
            "beat_name": "dark_night_soul",
            "word_target": 250,
            "description": "Dark Night of the Soul: Despair before the breakthrough",
            "guidance": "Wallowing in hopelessness. Then... the 'aha' moment. Realizes what was missing."
        },
        {
            "beat_number": 13,
            "beat_name": "break_into_three",
            "word_target": 300,
            "description": "Break Into Three: Solution using A and B story lessons",
            "guidance": "Combines what learned in both stories. New idea. Ready to finish this."
        },
        {
            "beat_number": 14,
            "beat_name": "finale",
            "word_target": 400,
            "description": "Finale: Execute new plan, face antagonist, transform",
            "guidance": "Storm the castle. Use new knowledge. High point. Transformation complete."
        },
        {
            "beat_number": 15,
            "beat_name": "final_image",
            "word_target": 200,
            "description": "Final Image: Proof that change has occurred",
            "guidance": "Mirror opening image but different. Show transformation. New world/status quo."
        }
    ]
)

# Hero's Journey (Joseph Campbell / Christopher Vogler)
HEROS_JOURNEY_SHORT = BeatTemplate(
    name="heros_journey_short",
    genre="universal",
    total_words=1800,
    description="Joseph Campbell's Hero's Journey condensed for short fiction",
    beats=[
        {
            "beat_number": 1,
            "beat_name": "ordinary_world",
            "word_target": 300,
            "description": "Ordinary World: Hero in their comfort zone",
            "guidance": "Show hero's normal life. Establish what they'll leave behind. Hint at inner need."
        },
        {
            "beat_number": 2,
            "beat_name": "call_and_crossing",
            "word_target": 350,
            "description": "Call to Adventure + Crossing the Threshold",
            "guidance": "Hero receives call, may refuse briefly, then commits. Enters Special World."
        },
        {
            "beat_number": 3,
            "beat_name": "tests_and_allies",
            "word_target": 400,
            "description": "Tests, Allies, Enemies: Learning the new world's rules",
            "guidance": "Hero faces challenges, meets helpers, identifies enemies. Training/growth."
        },
        {
            "beat_number": 4,
            "beat_name": "ordeal",
            "word_target": 300,
            "description": "The Ordeal: Face death/greatest fear, seize the reward",
            "guidance": "Central crisis. Near-death experience. Hero emerges transformed with prize."
        },
        {
            "beat_number": 5,
            "beat_name": "return",
            "word_target": 150,
            "description": "The Road Back + Return: Bring elixir home changed",
            "guidance": "Hero returns transformed. Applies wisdom. Master of two worlds."
        }
    ]
)

HEROS_JOURNEY_PREMIUM = BeatTemplate(
    name="heros_journey_premium",
    genre="universal",
    total_words=4500,
    description="Full Hero's Journey with all twelve stages",
    beats=[
        {
            "beat_number": 1,
            "beat_name": "ordinary_world",
            "word_target": 400,
            "description": "The Ordinary World: Hero's limited awareness",
            "guidance": "Hero in comfortable but unfulfilling world. Show their flaw. Establish sympathy."
        },
        {
            "beat_number": 2,
            "beat_name": "call_to_adventure",
            "word_target": 350,
            "description": "Call to Adventure: Something disrupts ordinary",
            "guidance": "Herald brings news. Problem presents itself. Adventure beckons."
        },
        {
            "beat_number": 3,
            "beat_name": "refusal_of_call",
            "word_target": 300,
            "description": "Refusal of the Call: Hero hesitates",
            "guidance": "Fear, obligation, or inadequacy. What's at stake if they go? If they don't?"
        },
        {
            "beat_number": 4,
            "beat_name": "meeting_mentor",
            "word_target": 350,
            "description": "Meeting with the Mentor: Guidance and gifts",
            "guidance": "Wise figure provides advice, training, or magical aid. Gives confidence to proceed."
        },
        {
            "beat_number": 5,
            "beat_name": "crossing_threshold",
            "word_target": 350,
            "description": "Crossing the First Threshold: Commit to adventure",
            "guidance": "Hero fully enters Special World. No turning back. Threshold guardian may appear."
        },
        {
            "beat_number": 6,
            "beat_name": "tests_allies_enemies",
            "word_target": 500,
            "description": "Tests, Allies, Enemies: Navigate Special World",
            "guidance": "Learn rules of new world. Gain allies, identify foes. Skills tested and developed."
        },
        {
            "beat_number": 7,
            "beat_name": "approach_inmost_cave",
            "word_target": 400,
            "description": "Approach to the Inmost Cave: Prepare for ordeal",
            "guidance": "Approach to the most dangerous place. Team reorganizes. Final preparations."
        },
        {
            "beat_number": 8,
            "beat_name": "ordeal",
            "word_target": 500,
            "description": "The Ordeal: Death and rebirth",
            "guidance": "Hero's greatest fear. Death experience (literal or symbolic). Transformation moment."
        },
        {
            "beat_number": 9,
            "beat_name": "reward",
            "word_target": 350,
            "description": "Reward (Seizing the Sword): Claim the prize",
            "guidance": "Hero takes treasure, knowledge, or reconciliation. Celebration. But not over yet."
        },
        {
            "beat_number": 10,
            "beat_name": "road_back",
            "word_target": 400,
            "description": "The Road Back: Chase or flight",
            "guidance": "Consequences of taking reward. Pursued. Must return to Ordinary World."
        },
        {
            "beat_number": 11,
            "beat_name": "resurrection",
            "word_target": 400,
            "description": "Resurrection: Final test, full transformation",
            "guidance": "Climactic battle. Hero fully transformed. Death and rebirth at higher level."
        },
        {
            "beat_number": 12,
            "beat_name": "return_with_elixir",
            "word_target": 200,
            "description": "Return with the Elixir: Share the gift",
            "guidance": "Hero returns changed. Brings boon to community. Master of two worlds."
        }
    ]
)

# Truby's 22 Building Blocks (John Truby) - Adapted
TRUBY_BEATS_SHORT = BeatTemplate(
    name="truby_beats_short",
    genre="universal",
    total_words=1800,
    description="John Truby's story anatomy condensed for short fiction",
    beats=[
        {
            "beat_number": 1,
            "beat_name": "weakness_and_need",
            "word_target": 300,
            "description": "Weakness/Need + Ghost: Hero's psychological and moral flaw",
            "guidance": "Establish hero's weakness (psychological) and need (moral). The ghost event that caused it."
        },
        {
            "beat_number": 2,
            "beat_name": "desire_and_opponent",
            "word_target": 350,
            "description": "Desire + Opponent: What hero wants and who blocks them",
            "guidance": "Clear external goal. Introduce opponent who wants same thing. Conflict established."
        },
        {
            "beat_number": 3,
            "beat_name": "plan_and_battle",
            "word_target": 400,
            "description": "Plan + Battle: Strategy and conflict escalation",
            "guidance": "Hero's plan to achieve desire. Series of attacks and counterattacks with opponent."
        },
        {
            "beat_number": 4,
            "beat_name": "self_revelation",
            "word_target": 300,
            "description": "Self-Revelation: Hero sees their flaw clearly",
            "guidance": "Psychological revelation - hero learns truth about themselves. Moral revelation - learns right action."
        },
        {
            "beat_number": 5,
            "beat_name": "new_equilibrium",
            "word_target": 150,
            "description": "New Equilibrium: Changed life based on revelation",
            "guidance": "Hero at higher or lower level than start. Show moral ramifications. New balance."
        }
    ]
)

TRUBY_BEATS_PREMIUM = BeatTemplate(
    name="truby_beats_premium",
    genre="universal",
    total_words=4500,
    description="John Truby's comprehensive story anatomy",
    beats=[
        {
            "beat_number": 1,
            "beat_name": "weakness_and_need",
            "word_target": 350,
            "description": "Weakness and Need: Hero's core flaw",
            "guidance": "Psychological weakness: hurts self. Moral need: hurts others. Both must be addressed."
        },
        {
            "beat_number": 2,
            "beat_name": "ghost_and_world",
            "word_target": 300,
            "description": "Ghost + Story World: Past trauma and arena",
            "guidance": "Event from past that created weakness. Establish story world as expression of hero's inner state."
        },
        {
            "beat_number": 3,
            "beat_name": "desire",
            "word_target": 350,
            "description": "Desire: Hero's concrete goal",
            "guidance": "Specific, external goal. What hero WANTS (vs what they NEED). Clear finish line."
        },
        {
            "beat_number": 4,
            "beat_name": "opponent",
            "word_target": 400,
            "description": "Opponent: The necessary antagonist",
            "guidance": "Opponent wants same goal. Is best at attacking hero's weakness. Forces hero to change."
        },
        {
            "beat_number": 5,
            "beat_name": "plan",
            "word_target": 350,
            "description": "Plan: Hero's strategy to win",
            "guidance": "Guidelines and tactics to reach goal. Will need to adjust. Shows character."
        },
        {
            "beat_number": 6,
            "beat_name": "battle",
            "word_target": 600,
            "description": "Battle: Escalating conflict",
            "guidance": "Series of attacks and counterattacks. Each side adjusts. Stakes rise. Multiple reversals."
        },
        {
            "beat_number": 7,
            "beat_name": "apparent_defeat",
            "word_target": 400,
            "description": "Apparent Defeat: Hero seems to lose",
            "guidance": "All seems lost. Hero at lowest point. Must dig deep. Question everything."
        },
        {
            "beat_number": 8,
            "beat_name": "obsessive_drive",
            "word_target": 350,
            "description": "Obsessive Drive: Hero pushes through",
            "guidance": "Desperate push toward goal. May make moral compromises. Tension peaks."
        },
        {
            "beat_number": 9,
            "beat_name": "self_revelation",
            "word_target": 400,
            "description": "Self-Revelation: Hero sees truth",
            "guidance": "Psychological: learns truth about self. Moral: learns right way to treat others. Transformative moment."
        },
        {
            "beat_number": 10,
            "beat_name": "moral_decision",
            "word_target": 350,
            "description": "Moral Decision: Prove the change",
            "guidance": "Hero acts on revelation. Makes choice that proves transformation. Action based on new self."
        },
        {
            "beat_number": 11,
            "beat_name": "new_equilibrium",
            "word_target": 250,
            "description": "New Equilibrium: Changed status quo",
            "guidance": "New balance higher or lower than start. Show moral ramifications for world. Resolution."
        }
    ]
)


# Bond Beats (Static Protagonist Structure)
# Unlike Hero's Journey, the protagonist DOES NOT change - the world changes around them
BOND_BEATS_SHORT = BeatTemplate(
    name="bond_beats_short",
    genre="universal",
    total_words=1800,
    description="Static protagonist structure - hero influences and changes the world while remaining unchanged",
    beats=[
        {
            "beat_number": 1,
            "beat_name": "charismatic_opener",
            "word_target": 250,
            "description": "Charismatic Opener: Showcase defining trait in bold standalone action",
            "guidance": "Start in the middle of action. No context needed. Show protagonist's signature skills - charm, cunning, competence. Exotic location, beautiful things, tension. Hook the reader immediately. The protagonist is STATIC - they will not change."
        },
        {
            "beat_number": 2,
            "beat_name": "world_and_challenge",
            "word_target": 300,
            "description": "World Introduction + Challenge: Establish world and introduce the threat",
            "guidance": "Mix introductions with action (double scene technique). Show allies and reputation. Introduce villain's power and dastardly nature. Use exposition through action, not info dumps. Stakes become clear."
        },
        {
            "beat_number": 3,
            "beat_name": "first_influence",
            "word_target": 350,
            "description": "First Influence: Protagonist begins reshaping their world",
            "guidance": "Show relationships with allies. Introduce key tools or allies that will matter later. Meet the secondary character who WILL change (the 'Bond Girl' archetype). Tension and temptation mixed. Protagonist is controlled by external forces but remains unchanged internally."
        },
        {
            "beat_number": 4,
            "beat_name": "escalating_stakes",
            "word_target": 400,
            "description": "Escalating Stakes + Midpoint Spectacle: Back-and-forth victories and defeats",
            "guidance": "Protagonist watches villain secretly. Not all is revealed. Up and down tension. Use tech or skills but not everything works. Major set piece that showcases protagonist's dominance. Villain's exotic threat revealed. Multiple scenes doing 2-3 things at once."
        },
        {
            "beat_number": 5,
            "beat_name": "charm_and_pushback",
            "word_target": 300,
            "description": "Charm Offensive + Antagonist's Pushback: Protagonist uses charm, then gets trapped",
            "guidance": "Protagonist sweet-talks their way through setbacks. The secondary character begins to change due to protagonist's influence. Then villain outmaneuvers and traps protagonist. Things look impossible. Short-lived wins followed by lows."
        },
        {
            "beat_number": 6,
            "beat_name": "climax_and_world_changed",
            "word_target": 200,
            "description": "Rally, Climax, World Changed: Escape, defeat villain, world is transformed",
            "guidance": "Protagonist escapes using core traits. Rally allies. Fight the #2 villain (not the mastermind) first. High stakes showdown. Villain's world unravels. Protagonist UNCHANGED but world/allies transformed. End with signature flourish."
        }
    ]
)

BOND_BEATS_PREMIUM = BeatTemplate(
    name="bond_beats_premium",
    genre="universal",
    total_words=4500,
    description="Full static protagonist structure - hero influences and changes the world while remaining unchanged",
    beats=[
        {
            "beat_number": 1,
            "beat_name": "charismatic_opener",
            "word_target": 350,
            "description": "Charismatic Opener (0-5%): Showcase defining trait in bold standalone action",
            "guidance": "Start in the middle of a mission, no context. Highlight protagonist's skills and personality through action. Exotic places, beautiful things, and tension mixed together. Good guy vs bad guy is obvious without explanation. Somewhat brutal to show stakes. The protagonist is STATIC and will never change throughout the story."
        },
        {
            "beat_number": 2,
            "beat_name": "world_introduction",
            "word_target": 350,
            "description": "World Introduction (5-10%): Establish world, allies, and villain",
            "guidance": "Mix introductions and exposition in a fun environment. Use double scene technique - action + exposition + character simultaneously. Show villain's devilish nature and protagonist's cunning. Establish the authority figures who control the protagonist. Early hints of betrayal add mystery."
        },
        {
            "beat_number": 3,
            "beat_name": "challenge_emerges",
            "word_target": 350,
            "description": "Challenge Emerges (10-15%): The threat becomes clear",
            "guidance": "Introduce a second threat or henchman who initially bests or challenges the protagonist. Focus on the villain's dastardly deeds. Multiple plot threads can interweave - moral dilemma, mission stakes, media/public pressure. External stakes the protagonist will address."
        },
        {
            "beat_number": 4,
            "beat_name": "first_influence",
            "word_target": 500,
            "description": "First Influence (15-25%): Protagonist reshapes their world",
            "guidance": "Show protagonist's relationships - authority figures, allies, tech quartermaster. Introduce tools that will save lives later. Meet the secondary character who changes (the transforming ally). Tension and temptation, good and bad mixed. Protagonist remains static even in danger. Exotic places and opulence keep it fun."
        },
        {
            "beat_number": 5,
            "beat_name": "escalating_stakes",
            "word_target": 500,
            "description": "Escalating Stakes (25-35%): Back-and-forth victories and defeats",
            "guidance": "Protagonist watches villain secretly. Slow reveal of the plot as protagonist figures it out. Tech works but not perfectly - ups and downs. Unexpected dangers. Secondary character's backstory and why they might change. Multiple use scenes - 2-3 things happening at once. Stakes raise continuously."
        },
        {
            "beat_number": 6,
            "beat_name": "midpoint_spectacle",
            "word_target": 600,
            "description": "Midpoint Spectacle (35-50%): Major set piece showcasing dominance",
            "guidance": "Peak moment of influence. Exotic threat setup by villain. Neither protagonist nor villain is swayed - the tension builds. Multiple secondary characters in play. Meet more allies. Keep interesting places and things. Could reveal the villain's grand plan. Tense and slow at times, then bursts of action."
        },
        {
            "beat_number": 7,
            "beat_name": "secondary_impact",
            "word_target": 450,
            "description": "Secondary Impact (50-60%): Allies change, complications arise",
            "guidance": "Backstory for secondary character and why they're changing. Villain demonstrates supreme power but protagonist finds a way out. Setbacks and victories back and forth. Secondary character is comforted or influenced by protagonist. The point is to highlight the unchanging nature of protagonist against a changing world."
        },
        {
            "beat_number": 8,
            "beat_name": "charm_offensive",
            "word_target": 400,
            "description": "Charm Offensive (60-70%): Protagonist uses charm to navigate setbacks",
            "guidance": "Protagonist overhears more of villain's power. Stakes raised again. Secondary character swayed to protagonist's side. Protagonist doesn't change but secondary character does. Charm and wit win the day in key moments."
        },
        {
            "beat_number": 9,
            "beat_name": "antagonist_pushback",
            "word_target": 400,
            "description": "Antagonist's Pushback (70-80%): Villain traps or outmaneuvers protagonist",
            "guidance": "Villain appears to be winning but protagonist is still in the game. Slow reveal of villain's full plan. Love/truth moment possible. Betrayal. From highs to lows in rapid succession. Short-lived wins. Villain's own people may turn on each other."
        },
        {
            "beat_number": 10,
            "beat_name": "protagonist_rally",
            "word_target": 350,
            "description": "Protagonist's Rally (80-90%): Escape and counterattack",
            "guidance": "Protagonist sways final ally to their side. Uses core traits to escape. Small action set in motion earlier pays off. The impossibility of winning becomes more apparent - they make it seem impossible. Things are not what they seem. Rally the troops."
        },
        {
            "beat_number": 11,
            "beat_name": "climactic_impact",
            "word_target": 400,
            "description": "Climactic Impact (90-95%): High-stakes showdown",
            "guidance": "Villain's world unravels. Fight the #2 henchman, not the mastermind directly. Countdown tension (literal or metaphorical). Protagonist must use all skills. Evil of villains starts to destroy themselves. Multiple threads resolve. Pure skill wins in the end."
        },
        {
            "beat_number": 12,
            "beat_name": "world_changed",
            "word_target": 350,
            "description": "World Changed (95-100%): Resolution with protagonist unchanged",
            "guidance": "Protagonist reflects on unchanged nature while world shows lasting change. Secondary character is transformed. Protagonist goes on to another adventure. End with signature flourish or witty line. Affirm the static nature - they were always this skilled, this charming, this unflappable."
        }
    ]
)


# ===== TRUBY GENRE-SPECIFIC BEATS =====
# From John Truby's "The Anatomy of Genres" - each genre has its own philosophy and beat structure

# HORROR - The Philosophy of Death
# Key: Hero is VICTIM, monster as "Other", NO positive self-revelation, double ending
TRUBY_HORROR_SHORT = BeatTemplate(
    name="truby_horror_short",
    genre="horror",
    total_words=1800,
    description="Horror as philosophy of death - hero as victim confronting the monster/Other",
    beats=[
        {
            "beat_number": 1,
            "beat_name": "ghost_and_world",
            "word_target": 300,
            "description": "Ghost & Haunted World: Sins of the past in a trapped society",
            "guidance": "Establish the GHOST - sins of the past that haunt this place. The story world is a 'haunted house' or closed society where characters CANNOT escape. Introduce the hero's weakness: slavery of the mind, shame, guilt, the monster within. The hero starts as potential VICTIM."
        },
        {
            "beat_number": 2,
            "beat_name": "monster_attacks",
            "word_target": 350,
            "description": "The Monster Attacks: The Other emerges",
            "guidance": "The MONSTER attacks - this is the extreme 'Other', something fundamentally alien and threatening. The hero's desire crystallizes: defeat the monster, defeat death itself. Introduce the ALLY - usually a rational skeptic who will likely die or be proven wrong. Hero crosses into the forbidden world."
        },
        {
            "beat_number": 3,
            "beat_name": "reactive_drive",
            "word_target": 400,
            "description": "Reactive Drive: Survival mode escalates",
            "guidance": "The hero's plan is purely REACTIVE - just trying to survive. The monster's attacks escalate. Each attack reveals more about the monster and the hero's past sins. The rational ally's skepticism is challenged. The 'safe haven' begins to feel compromised."
        },
        {
            "beat_number": 4,
            "beat_name": "haven_compromised",
            "word_target": 350,
            "description": "Battle in Compromised Haven: The final confrontation",
            "guidance": "The battle takes place in a 'safe haven' that has been completely compromised - nowhere is safe. The hero faces the monster but there is NO POSITIVE SELF-REVELATION. The hero survives but is often broken, damaged, changed for the worse."
        },
        {
            "beat_number": 5,
            "beat_name": "double_ending",
            "word_target": 200,
            "description": "Double Ending: The monster returns",
            "guidance": "The DOUBLE ENDING - hint or show that the monster returns or was never truly defeated. Horror is about ETERNAL RECURRENCE. The evil is not defeated, only delayed. Leave the reader with dread, not comfort. The horror continues or will continue."
        }
    ]
)

TRUBY_HORROR_PREMIUM = BeatTemplate(
    name="truby_horror_premium",
    genre="horror",
    total_words=4500,
    description="Full horror structure - philosophy of death with victim hero and eternal monster",
    beats=[
        {
            "beat_number": 1,
            "beat_name": "ghost",
            "word_target": 350,
            "description": "The Ghost: Sins of the past",
            "guidance": "Establish the GHOST - the specific sin or trauma from the past that haunts this place or these characters. This could be a literal ghost, a family secret, a buried crime. The ghost creates the conditions for the horror to come."
        },
        {
            "beat_number": 2,
            "beat_name": "haunted_world",
            "word_target": 350,
            "description": "The Haunted World: Trapped society",
            "guidance": "The story world is a 'haunted house' - a CLOSED or TRAPPED society where characters cannot easily escape. Could be an actual house, a small town, a ship, an island. Establish why leaving is impossible or unthinkable."
        },
        {
            "beat_number": 3,
            "beat_name": "hero_as_victim",
            "word_target": 350,
            "description": "Hero as Victim: Weakness and shame",
            "guidance": "The hero is fundamentally a VICTIM - passive, trapped, often complicit in past sins. Establish their weakness: slavery of the mind, shame, guilt. They may have 'the monster within' - a darkness that makes them vulnerable or connected to the evil."
        },
        {
            "beat_number": 4,
            "beat_name": "monster_emerges",
            "word_target": 400,
            "description": "The Monster Attacks: The Other appears",
            "guidance": "The MONSTER attacks - this is the extreme 'Other', something fundamentally alien and threatening to our humanity. The monster represents what we fear most about death, the unknown, or ourselves. First attack establishes the monster's power and the stakes."
        },
        {
            "beat_number": 5,
            "beat_name": "rational_ally",
            "word_target": 350,
            "description": "The Ally: The rational skeptic",
            "guidance": "Introduce the ALLY - typically a rational skeptic who doesn't believe in the supernatural or underestimates the threat. This character often dies or is proven catastrophically wrong. Their rationality cannot save them."
        },
        {
            "beat_number": 6,
            "beat_name": "crossing_barrier",
            "word_target": 400,
            "description": "Crossing the Barrier: Into the forbidden",
            "guidance": "The hero crosses into the FORBIDDEN WORLD - the place where the monster rules, where normal rules don't apply. This could be physical (basement, forest) or psychological (madness, obsession). There's no going back."
        },
        {
            "beat_number": 7,
            "beat_name": "reactive_survival",
            "word_target": 450,
            "description": "Reactive Drive: Pure survival",
            "guidance": "The hero's plan is purely REACTIVE - just trying to survive. No clever strategy, just desperate response to escalating attacks. The monster's attacks grow worse. Each reveals more about the ghost/sin and the hero's connection to it."
        },
        {
            "beat_number": 8,
            "beat_name": "escalation",
            "word_target": 450,
            "description": "Monster Escalation: The attacks worsen",
            "guidance": "The monster demonstrates its full power. Other characters die or are taken. The ally's skepticism crumbles too late. The hero realizes the depth of their own guilt or connection to the evil. The safe spaces shrink."
        },
        {
            "beat_number": 9,
            "beat_name": "haven_battle",
            "word_target": 500,
            "description": "Battle in Compromised Haven: Final confrontation",
            "guidance": "The battle takes place in a 'SAFE HAVEN' that has been COMPROMISED - the last refuge is breached. The hero faces the monster directly. This is not a triumph but a desperate last stand. The hero may defeat the monster but at terrible cost."
        },
        {
            "beat_number": 10,
            "beat_name": "no_revelation",
            "word_target": 300,
            "description": "No Self-Revelation: Broken, not grown",
            "guidance": "Unlike other genres, there is NO POSITIVE SELF-REVELATION. The hero survives but is broken, traumatized, or morally damaged. They do not 'grow' in a positive sense. They may realize the horror is eternal, or become part of it."
        },
        {
            "beat_number": 11,
            "beat_name": "double_ending",
            "word_target": 300,
            "description": "The Double Ending: Eternal recurrence",
            "guidance": "The DOUBLE ENDING - the monster returns or was never truly defeated. A final scare, a lingering dread, a sign that the evil continues. Horror is about ETERNAL RECURRENCE - death and evil cannot be permanently conquered. End with unease, not comfort."
        }
    ]
)

# ACTION - The Philosophy of Success
# Key: Warrior's moral code, will to greatness, collecting allies, game plan, vortex battle
TRUBY_ACTION_SHORT = BeatTemplate(
    name="truby_action_short",
    genre="action",
    total_words=1800,
    description="Action as philosophy of success - warrior's code, will, and physical triumph",
    beats=[
        {
            "beat_number": 1,
            "beat_name": "defining_crisis",
            "word_target": 300,
            "description": "Hero's Defining Crisis: Enslaved world, warrior emerges",
            "guidance": "The hero faces a DEFINING CRISIS that showcases their core trait. The world is one of enslavement or physical danger. Establish the WARRIOR'S MORAL CODE - courage, honor, the will to greatness. The hero's weakness is shame or a failure of will."
        },
        {
            "beat_number": 2,
            "beat_name": "collect_allies",
            "word_target": 350,
            "description": "Collecting the Allies: Building the team",
            "guidance": "The hero's DESIRE is success, glory, personal freedom. They must COLLECT ALLIES - build the team needed to face the opposition. Each ally brings specific skills. The OPPONENT represents external bondage - a master villain who must be overcome."
        },
        {
            "beat_number": 3,
            "beat_name": "game_plan",
            "word_target": 400,
            "description": "Game Plan & Drive: Strategic attack, cat and mouse",
            "guidance": "The hero develops a GAME PLAN - a strategic attack on the opponent. The DRIVE is cat and mouse, rapid pacing, action set pieces. Revelations lead to new decisions. The MORAL ARGUMENT emerges: the 'Great' (excellence) vs the 'Good' (morality)."
        },
        {
            "beat_number": 4,
            "beat_name": "vortex_battle",
            "word_target": 450,
            "description": "Vortex Point: The violent final battle",
            "guidance": "The VORTEX POINT - the violent final battle where all forces converge. This is pure physical action, the ultimate test of the warrior's code. The hero must prove their worth through courage and skill. Maximum stakes, maximum action."
        },
        {
            "beat_number": 5,
            "beat_name": "revelation_communion",
            "word_target": 200,
            "description": "Self-Revelation & Communion: Victory and belonging",
            "guidance": "SELF-REVELATION - the hero proves their worth and learns what truly matters. FAREWELL or COMMUNION - the hero either leaves as a lone warrior or joins the community they saved. Victory brings freedom, glory, or both."
        }
    ]
)

TRUBY_ACTION_PREMIUM = BeatTemplate(
    name="truby_action_premium",
    genre="action",
    total_words=4500,
    description="Full action structure - warrior's code, team building, and triumphant battle",
    beats=[
        {
            "beat_number": 1,
            "beat_name": "defining_crisis",
            "word_target": 400,
            "description": "Hero's Defining Crisis: The warrior is tested",
            "guidance": "Open with a DEFINING CRISIS that showcases the hero's core warrior trait - their courage, skill, or determination. This is not the main conflict but a preview of who the hero is under pressure."
        },
        {
            "beat_number": 2,
            "beat_name": "enslaved_world",
            "word_target": 350,
            "description": "The Enslaved World: Physical danger and oppression",
            "guidance": "Establish the story world as one of ENSLAVEMENT or physical danger. People are oppressed, threatened, or trapped. The hero sees this injustice and their DESIRE crystallizes: success, glory, personal freedom, or the freedom of others."
        },
        {
            "beat_number": 3,
            "beat_name": "warriors_code",
            "word_target": 350,
            "description": "Warrior's Moral Code: Courage and will",
            "guidance": "Establish the hero's WARRIOR'S MORAL CODE - the values they live by. Courage, honor, loyalty, the will to greatness. Their WEAKNESS is shame or a past failure of will - a time they didn't live up to their code."
        },
        {
            "beat_number": 4,
            "beat_name": "opposition",
            "word_target": 400,
            "description": "The Opposition: Master villain and bondage",
            "guidance": "The OPPONENT represents external bondage - a master villain, an oppressive system, a powerful enemy. Show their strength and cruelty. The hero cannot defeat them alone. The opposition seems overwhelming."
        },
        {
            "beat_number": 5,
            "beat_name": "collecting_allies",
            "word_target": 450,
            "description": "Collecting the Allies: Building the team",
            "guidance": "The hero must COLLECT ALLIES - recruiting the team needed to face the opposition. Each ally brings specific skills and personality. There may be reluctance, negotiation, proving worthiness. The team dynamic adds texture and humor."
        },
        {
            "beat_number": 6,
            "beat_name": "game_plan",
            "word_target": 400,
            "description": "The Game Plan: Strategic attack",
            "guidance": "The hero develops the GAME PLAN - the strategic approach to defeating the opponent. This involves preparation, training, gathering resources. The plan should be clever but have potential weaknesses the reader can see."
        },
        {
            "beat_number": 7,
            "beat_name": "cat_and_mouse",
            "word_target": 450,
            "description": "Drive - Cat and Mouse: Rapid action pacing",
            "guidance": "The DRIVE phase - cat and mouse, rapid pacing. Initial clashes with the opposition. Wins and losses. Revelations that lead to new decisions. The MORAL ARGUMENT begins: the 'Great' (excellence, winning) vs the 'Good' (morality, sacrifice)."
        },
        {
            "beat_number": 8,
            "beat_name": "setback",
            "word_target": 400,
            "description": "Major Setback: The plan fails",
            "guidance": "A major SETBACK - the game plan fails or a key ally is lost. The hero's weakness resurfaces. They must dig deeper, recommit to their warrior's code. The team's bonds are tested."
        },
        {
            "beat_number": 9,
            "beat_name": "vortex_point",
            "word_target": 500,
            "description": "Vortex Point: The violent final battle",
            "guidance": "The VORTEX POINT - the violent final battle where all forces converge. This is the ultimate test of the warrior's code. Pure physical action at maximum intensity. The hero must prove their worth through courage and skill."
        },
        {
            "beat_number": 10,
            "beat_name": "self_revelation",
            "word_target": 300,
            "description": "Self-Revelation: The hero proves their worth",
            "guidance": "SELF-REVELATION - through victory, the hero learns what truly matters. They may choose the 'Good' over the 'Great' or prove they can be both. Their shame is redeemed, their failure of will corrected."
        },
        {
            "beat_number": 11,
            "beat_name": "farewell_communion",
            "word_target": 300,
            "description": "Farewell or Communion: Victory's aftermath",
            "guidance": "FAREWELL or COMMUNION - the hero either leaves as a lone warrior (farewell) or joins the community they saved (communion). Success brings freedom, glory, and possibly love. The world is changed by the hero's will."
        }
    ]
)

# LOVE STORY - The Philosophy of Happiness
# Key: TWO protagonists, the gaze/meeting, the scam, steps of intimacy, apparent defeat
TRUBY_LOVE_SHORT = BeatTemplate(
    name="truby_love_short",
    genre="romance",
    total_words=1800,
    description="Love story as philosophy of happiness - two protagonists learning to love",
    beats=[
        {
            "beat_number": 1,
            "beat_name": "two_protagonists",
            "word_target": 300,
            "description": "Two Protagonists: Emotional armor and fear",
            "guidance": "Establish TWO EQUAL PROTAGONISTS - both have depth and agency. Each has a GHOST - a cycle of fear regarding intimacy. Their WEAKNESS is inability to love, emotional armor. They are fundamentally incomplete without each other but don't know it yet."
        },
        {
            "beat_number": 2,
            "beat_name": "the_gaze",
            "word_target": 350,
            "description": "The Gaze: Meeting and longing",
            "guidance": "THE GAZE - the meeting, the first look. DESIRE awakens - they want this person but fear being vulnerable. Each sees something in the other that both attracts and threatens. Love ALLIES appear (friends giving advice, good and bad). The other person is also the OPPONENT - the one blocking their desire."
        },
        {
            "beat_number": 3,
            "beat_name": "the_scam",
            "word_target": 400,
            "description": "The Scam & Intimacy: Trying to love safely",
            "guidance": "THE SCAM - each tries to get the other without being vulnerable themselves. Games, pretenses, protection of the heart. STEPS OF INTIMACY begin: Talking → Touching → (perhaps) Sex. Each step deeper increases both desire and fear."
        },
        {
            "beat_number": 4,
            "beat_name": "apparent_victory_defeat",
            "word_target": 350,
            "description": "Victory then Defeat: Perfect moment, then breakup",
            "guidance": "APPARENT VICTORY - the perfect love moment, intimacy seems achieved. Then APPARENT DEFEAT - the breakup. The scam is exposed, fear wins, they push each other away. Both are devastated, forced to confront their inability to love."
        },
        {
            "beat_number": 5,
            "beat_name": "revelation_union",
            "word_target": 200,
            "description": "Self-Revelation & Union: Admitting need",
            "guidance": "SELF-REVELATION - both admit their need for the other, their fear, their weakness. NEW EQUILIBRIUM - Union (romantic ending) or tragic separation (they've grown but can't be together). The key is vulnerability and authentic connection."
        }
    ]
)

TRUBY_LOVE_PREMIUM = BeatTemplate(
    name="truby_love_premium",
    genre="romance",
    total_words=4500,
    description="Full love story structure - two protagonists on parallel journeys to vulnerability",
    beats=[
        {
            "beat_number": 1,
            "beat_name": "protagonist_one",
            "word_target": 350,
            "description": "First Protagonist: Their ghost and armor",
            "guidance": "Establish PROTAGONIST ONE - their life, their GHOST (past pain regarding intimacy), their emotional armor. They cannot love fully due to fear. Show their WEAKNESS - the specific way they push people away or protect themselves."
        },
        {
            "beat_number": 2,
            "beat_name": "protagonist_two",
            "word_target": 350,
            "description": "Second Protagonist: Their ghost and armor",
            "guidance": "Establish PROTAGONIST TWO - equally developed with their own GHOST and armor. Their weakness should complement or clash with protagonist one. Both are incomplete without knowing it."
        },
        {
            "beat_number": 3,
            "beat_name": "the_gaze",
            "word_target": 350,
            "description": "The Gaze: The meeting",
            "guidance": "THE GAZE - the first meeting, the look that changes everything. Something sparks between them. DESIRE awakens in both - they want this person. But wanting means risking vulnerability, which triggers their armor."
        },
        {
            "beat_number": 4,
            "beat_name": "desire_opponent",
            "word_target": 400,
            "description": "Desire & Opposition: They want and block each other",
            "guidance": "The other person is both the DESIRE and the OPPONENT. They want each other but each blocks the other's emotional progress. Love ALLIES appear - friends giving advice (some good, some bad). External obstacles may also interfere."
        },
        {
            "beat_number": 5,
            "beat_name": "the_scam",
            "word_target": 400,
            "description": "The Scam: Trying to love without vulnerability",
            "guidance": "THE SCAM - each tries to get the other without being truly vulnerable. Games, pretenses, half-truths, protection of the heart. They're falling in love but pretending they're not, or pretending it's casual."
        },
        {
            "beat_number": 6,
            "beat_name": "intimacy_steps",
            "word_target": 450,
            "description": "Steps of Intimacy: Getting closer",
            "guidance": "STEPS OF INTIMACY - Talking → Touching → deeper connection. Each step increases both desire and fear. Moments of genuine connection break through the armor. The first dance, first kiss, first real conversation."
        },
        {
            "beat_number": 7,
            "beat_name": "apparent_victory",
            "word_target": 400,
            "description": "Apparent Victory: The perfect moment",
            "guidance": "APPARENT VICTORY - the perfect love moment. They seem to have achieved intimacy and happiness. The armor seems down. This is the 'happily ever after' moment that comes too early - because the real work hasn't been done."
        },
        {
            "beat_number": 8,
            "beat_name": "apparent_defeat",
            "word_target": 450,
            "description": "Apparent Defeat: The breakup",
            "guidance": "APPARENT DEFEAT - the breakup. The scam is exposed, the armor snaps back, fear wins. They push each other away, often saying hurtful things. External obstacles may combine with internal ones. Both are devastated."
        },
        {
            "beat_number": 9,
            "beat_name": "dark_night",
            "word_target": 350,
            "description": "Dark Night: Confronting inability to love",
            "guidance": "The dark night of the soul - both protagonists must confront their GHOST and their inability to love. They see how their armor has hurt them and the other. The choice: remain safe and alone, or risk everything."
        },
        {
            "beat_number": 10,
            "beat_name": "self_revelation",
            "word_target": 350,
            "description": "Self-Revelation: Admitting the need",
            "guidance": "SELF-REVELATION - one or both admit their need for the other, their fear, their weakness. This requires true vulnerability - saying 'I love you' or 'I was wrong' without knowing if it will be returned."
        },
        {
            "beat_number": 11,
            "beat_name": "new_equilibrium",
            "word_target": 350,
            "description": "New Equilibrium: Union or tragic separation",
            "guidance": "NEW EQUILIBRIUM - Union (romantic ending, they're together having both grown) or tragic separation (they've grown but circumstances keep them apart). Either way, both are changed. Love has taught them to be vulnerable."
        }
    ]
)

# THRILLER - Mix of Horror, Action, and Crime
# Key: Hero under suspicion, being hunted, attack focus, must clear name
TRUBY_THRILLER_SHORT = BeatTemplate(
    name="truby_thriller_short",
    genre="thriller",
    total_words=1800,
    description="Thriller combining horror dread, action pace, and crime investigation",
    beats=[
        {
            "beat_number": 1,
            "beat_name": "ordinary_shattered",
            "word_target": 300,
            "description": "Ordinary World Shattered: The attack comes",
            "guidance": "The hero's ordinary world is SHATTERED by an attack or threat. They may be UNDER SUSPICION - wrongly accused or framed. From HORROR: the dread, the sense of being hunted. From CRIME: the mystery of who's behind it. The hero must clear their name while being hunted."
        },
        {
            "beat_number": 2,
            "beat_name": "hunted",
            "word_target": 400,
            "description": "The Hunted: Running and investigating",
            "guidance": "The hero is HUNTED - by the villain, by authorities, by both. From ACTION: rapid pacing, physical danger. They must investigate while on the run. Every ally is suspect. Trust becomes impossible. The clock is ticking toward some deadline."
        },
        {
            "beat_number": 3,
            "beat_name": "revelations_attacks",
            "word_target": 450,
            "description": "Revelations & Attacks: Truth emerges through danger",
            "guidance": "Truth emerges through ATTACKS and narrow escapes. Each revelation raises the stakes. From HORROR: the villain's plan is monstrous. From CRIME: the conspiracy goes deeper than imagined. The hero discovers their own connection to the threat."
        },
        {
            "beat_number": 4,
            "beat_name": "final_trap",
            "word_target": 350,
            "description": "Final Trap & Counterattack: Turn the tables",
            "guidance": "The hero is trapped but TURNS THE TABLES. Using everything they've learned, they set their own trap. From ACTION: the hero becomes the hunter. The villain's identity and full plan are exposed. Confrontation is inevitable."
        },
        {
            "beat_number": 5,
            "beat_name": "climax_clearance",
            "word_target": 200,
            "description": "Climax & Clearance: Vindication or pyrrhic victory",
            "guidance": "Climactic confrontation with the villain. The hero is CLEARED of suspicion and defeats the threat. But from HORROR: victory may be incomplete or costly. The world is saved but the hero is changed, possibly damaged."
        }
    ]
)

TRUBY_THRILLER_PREMIUM = BeatTemplate(
    name="truby_thriller_premium",
    genre="thriller",
    total_words=4500,
    description="Full thriller structure - hunted hero combining horror, action, and crime elements",
    beats=[
        {
            "beat_number": 1,
            "beat_name": "ordinary_world",
            "word_target": 350,
            "description": "Ordinary World: Before the storm",
            "guidance": "Establish the hero's ordinary world - their job, relationships, routine. They have a specific WEAKNESS or vulnerability that the coming events will exploit. Subtle hints of the threat to come."
        },
        {
            "beat_number": 2,
            "beat_name": "the_attack",
            "word_target": 400,
            "description": "The Attack: World shattered",
            "guidance": "The ATTACK - the hero's world is violently disrupted. Someone close to them is killed, they witness something they shouldn't, or they're framed for a crime. From HORROR: the dread, the sense of malevolent force. Life will never be the same."
        },
        {
            "beat_number": 3,
            "beat_name": "under_suspicion",
            "word_target": 350,
            "description": "Under Suspicion: Hunted from all sides",
            "guidance": "The hero is UNDER SUSPICION - the evidence points to them, or they're the only witness. Authorities pursue them. They can't trust the system. From CRIME: they must solve the mystery to clear their name. The clock starts ticking."
        },
        {
            "beat_number": 4,
            "beat_name": "running_investigating",
            "word_target": 400,
            "description": "Running & Investigating: Dual pressure",
            "guidance": "The hero must RUN and INVESTIGATE simultaneously. From ACTION: rapid pacing, physical danger, narrow escapes. Every potential ally is suspect. The hero pieces together clues while evading capture."
        },
        {
            "beat_number": 5,
            "beat_name": "conspiracy_deepens",
            "word_target": 400,
            "description": "Conspiracy Deepens: It's bigger than imagined",
            "guidance": "The CONSPIRACY is bigger than imagined. Powerful people are involved. The villain's plan has larger stakes - political, corporate, or existential. From CRIME: following the money or power trail. The hero is in over their head."
        },
        {
            "beat_number": 6,
            "beat_name": "attacks_escalate",
            "word_target": 450,
            "description": "Attacks Escalate: The villain strikes back",
            "guidance": "The villain realizes the hero is getting close and ATTACKS escalate. From HORROR: the attacks become more personal, more brutal. Someone the hero cares about is threatened or killed. The hero's connection to the threat is revealed."
        },
        {
            "beat_number": 7,
            "beat_name": "all_seems_lost",
            "word_target": 400,
            "description": "All Seems Lost: Trapped and alone",
            "guidance": "The hero is TRAPPED - captured, cornered, or out of options. Their evidence is destroyed or discredited. No one believes them. From HORROR: they face the villain's true monstrous nature. Death seems certain."
        },
        {
            "beat_number": 8,
            "beat_name": "turn_tables",
            "word_target": 400,
            "description": "Turn the Tables: The hunter becomes hunted",
            "guidance": "The hero TURNS THE TABLES. Using everything they've learned, their hidden strength, or an overlooked clue, they escape and set their own trap. From ACTION: the hero becomes the hunter. They know the villain's plan."
        },
        {
            "beat_number": 9,
            "beat_name": "expose_villain",
            "word_target": 350,
            "description": "Expose the Villain: The truth comes out",
            "guidance": "The hero works to EXPOSE the villain - gather proof that will clear their name and reveal the conspiracy. Race against the deadline. The villain tries to silence them one last time."
        },
        {
            "beat_number": 10,
            "beat_name": "climactic_confrontation",
            "word_target": 400,
            "description": "Climactic Confrontation: Face to face",
            "guidance": "CLIMACTIC CONFRONTATION with the villain. This is physical (from ACTION), psychological (from HORROR), and revelatory (from CRIME). The hero defeats the villain through wit, will, and courage."
        },
        {
            "beat_number": 11,
            "beat_name": "clearance",
            "word_target": 300,
            "description": "Clearance: Vindicated but changed",
            "guidance": "The hero is CLEARED - the truth is known, the conspiracy exposed. But from HORROR: victory is costly. The hero is changed, possibly damaged. The world is safer but trust is harder. Some mysteries may remain."
        }
    ]
)

# DETECTIVE - The Hunt for Truth
# Key: The crime, investigation, interviews, the reveal, bringing to justice
TRUBY_DETECTIVE_SHORT = BeatTemplate(
    name="truby_detective_short",
    genre="mystery",
    total_words=1800,
    description="Detective story as hunt for truth - investigation, interviews, revelation",
    beats=[
        {
            "beat_number": 1,
            "beat_name": "the_crime",
            "word_target": 300,
            "description": "The Crime: A mystery demands solving",
            "guidance": "THE CRIME - a murder, theft, or mystery that demands solving. The detective is drawn in by duty, curiosity, or personal connection. Establish the detective's method and moral code. The crime scene holds the first clues."
        },
        {
            "beat_number": 2,
            "beat_name": "investigation_begins",
            "word_target": 400,
            "description": "Investigation & Interviews: Gathering suspects",
            "guidance": "THE INVESTIGATION begins - examining evidence, questioning witnesses. INTERVIEWS reveal suspects, each with motive and opportunity. The detective pieces together the victim's world. Red herrings emerge. The truth is buried under lies."
        },
        {
            "beat_number": 3,
            "beat_name": "hunt_deepens",
            "word_target": 450,
            "description": "The Hunt Deepens: Following the trail",
            "guidance": "The HUNT FOR TRUTH deepens. Following leads, connecting dots. The detective may face obstruction - from authority, from the guilty, from unexpected quarters. Second crime or complication raises stakes. The detective's personal code is tested."
        },
        {
            "beat_number": 4,
            "beat_name": "revelation",
            "word_target": 350,
            "description": "The Revelation: Truth uncovered",
            "guidance": "THE REVELATION - the detective realizes the truth. Often through a detail that suddenly makes everything clear. The 'why' matters as much as the 'who.' The solution reveals something about human nature - greed, jealousy, desperation."
        },
        {
            "beat_number": 5,
            "beat_name": "justice",
            "word_target": 200,
            "description": "Bringing to Justice: The confrontation",
            "guidance": "Confrontation with the guilty party. The detective explains how they solved it. JUSTICE - the guilty are exposed and face consequences. But justice may be imperfect or bittersweet. Truth has a cost."
        }
    ]
)

TRUBY_DETECTIVE_PREMIUM = BeatTemplate(
    name="truby_detective_premium",
    genre="mystery",
    total_words=4500,
    description="Full detective structure - methodical investigation leading to revelation",
    beats=[
        {
            "beat_number": 1,
            "beat_name": "the_crime",
            "word_target": 400,
            "description": "The Crime: The mystery presented",
            "guidance": "THE CRIME - presented in full disturbing detail. A murder, disappearance, or mystery that demands solving. The crime scene tells a story but not the whole story. First clues are gathered but don't yet make sense."
        },
        {
            "beat_number": 2,
            "beat_name": "detective_called",
            "word_target": 350,
            "description": "Detective Called: Duty or obsession",
            "guidance": "The DETECTIVE is drawn into the case - by duty, by curiosity, or by personal connection to the victim. Establish their METHOD and moral code. Their weakness may be obsession with truth, or personal demons. They see what others miss."
        },
        {
            "beat_number": 3,
            "beat_name": "victims_world",
            "word_target": 350,
            "description": "The Victim's World: Who they were",
            "guidance": "Exploring THE VICTIM'S WORLD - who they were, who they knew, what secrets they held. The victim was not who they appeared. Multiple lives touched, multiple potential motives. The detective maps the relationships."
        },
        {
            "beat_number": 4,
            "beat_name": "interviews_suspects",
            "word_target": 450,
            "description": "Interviews & Suspects: Everyone lies",
            "guidance": "INTERVIEWS with suspects - each has motive, means, and opportunity. Everyone lies about something. The detective must separate relevant lies from irrelevant ones. Red herrings emerge. First theory forms but it's wrong."
        },
        {
            "beat_number": 5,
            "beat_name": "following_leads",
            "word_target": 400,
            "description": "Following Leads: The hunt for truth",
            "guidance": "FOLLOWING LEADS - the detective pursues promising threads. Some pan out, some don't. The truth is buried under layers of deception. Physical evidence must be matched with testimony. The detective's skill is tested."
        },
        {
            "beat_number": 6,
            "beat_name": "obstruction",
            "word_target": 400,
            "description": "Obstruction: Someone doesn't want truth found",
            "guidance": "OBSTRUCTION - someone is actively preventing the truth from emerging. Could be the guilty party, someone protecting them, or someone with a different secret to hide. Evidence disappears. Witnesses recant. The detective is warned off."
        },
        {
            "beat_number": 7,
            "beat_name": "second_crime",
            "word_target": 350,
            "description": "Second Crime or Complication: Stakes rise",
            "guidance": "A SECOND CRIME or major complication - another murder, the detective is framed, or a key witness dies. Stakes rise. The detective is getting close enough to threaten the guilty. Time pressure increases."
        },
        {
            "beat_number": 8,
            "beat_name": "code_tested",
            "word_target": 350,
            "description": "Code Tested: Temptation to compromise",
            "guidance": "The detective's moral CODE is tested - they're tempted to bend rules, hide evidence, or pursue personal justice. The right thing and the easy thing diverge. They must choose who they are."
        },
        {
            "beat_number": 9,
            "beat_name": "revelation",
            "word_target": 400,
            "description": "The Revelation: Everything clicks",
            "guidance": "THE REVELATION - often through a small detail that suddenly makes everything clear. The detective sees the pattern they've been missing. Not just 'who' but 'why' - the psychological truth behind the crime."
        },
        {
            "beat_number": 10,
            "beat_name": "confrontation",
            "word_target": 400,
            "description": "Confrontation: Accusing the guilty",
            "guidance": "CONFRONTATION with the guilty party. The detective explains the chain of reasoning, the evidence, the motive. The guilty may confess, deny, or try to escape. The truth is spoken aloud."
        },
        {
            "beat_number": 11,
            "beat_name": "justice",
            "word_target": 350,
            "description": "Justice: Truth and consequences",
            "guidance": "JUSTICE - but justice is complex. The guilty face legal consequences. But the truth has costs - relationships destroyed, innocence lost, lives changed. The detective solves the crime but may not feel victorious. Order is restored, but imperfectly."
        }
    ]
)


# ===== BEAT STRUCTURE REGISTRY =====
# These are the selectable story structures

BEAT_STRUCTURES = {
    "save_the_cat": {
        "id": "save_the_cat",
        "name": "Save the Cat!",
        "author": "Blake Snyder",
        "description": "Hollywood's go-to beat sheet. Focused on audience engagement and clear emotional beats.",
        "best_for": ["Commercial fiction", "Action", "Romance", "Comedy"],
        "short_template": SAVE_THE_CAT_SHORT,
        "premium_template": SAVE_THE_CAT_PREMIUM
    },
    "heros_journey": {
        "id": "heros_journey",
        "name": "Hero's Journey",
        "author": "Joseph Campbell / Christopher Vogler",
        "description": "The monomyth. Universal story pattern of departure, initiation, and return.",
        "best_for": ["Fantasy", "Adventure", "Sci-Fi", "Coming-of-age"],
        "short_template": HEROS_JOURNEY_SHORT,
        "premium_template": HEROS_JOURNEY_PREMIUM
    },
    "truby_beats": {
        "id": "truby_beats",
        "name": "Truby's Story Anatomy",
        "author": "John Truby",
        "description": "Character-driven structure based on weakness, desire, and moral transformation.",
        "best_for": ["Drama", "Character studies", "Literary fiction", "Psychological"],
        "short_template": TRUBY_BEATS_SHORT,
        "premium_template": TRUBY_BEATS_PREMIUM
    },
    "classic": {
        "id": "classic",
        "name": "Classic Genre Structure",
        "author": "FixionMail",
        "description": "Genre-optimized beats tailored for each story type (sci-fi, mystery, romance, etc.)",
        "best_for": ["All genres", "Genre-specific conventions", "Reader expectations"],
        "short_template": None,  # Uses genre-specific templates
        "premium_template": None  # Uses genre-specific templates
    },
    "bond_beats": {
        "id": "bond_beats",
        "name": "Bond Beats (Static Protagonist)",
        "author": "Matt Darbro / FixionMail",
        "description": "Static protagonist structure where the hero influences and changes the world while remaining unchanged themselves. Perfect for competent, unflappable protagonists.",
        "best_for": ["Spy", "Action", "Thriller", "Competence porn", "Heist"],
        "short_template": BOND_BEATS_SHORT,
        "premium_template": BOND_BEATS_PREMIUM
    },
    # Truby Genre-Specific Beats (from The Anatomy of Genres)
    "truby_horror": {
        "id": "truby_horror",
        "name": "Truby Horror (Philosophy of Death)",
        "author": "John Truby",
        "description": "Horror as confrontation with death. Hero is VICTIM, monster is the 'Other', NO positive self-revelation, double ending where evil returns.",
        "best_for": ["Horror", "Supernatural", "Gothic", "Psychological horror"],
        "short_template": TRUBY_HORROR_SHORT,
        "premium_template": TRUBY_HORROR_PREMIUM
    },
    "truby_action": {
        "id": "truby_action",
        "name": "Truby Action (Philosophy of Success)",
        "author": "John Truby",
        "description": "Action as philosophy of will and success. Warrior's moral code, collecting allies, game plan leading to vortex battle.",
        "best_for": ["Action", "Military", "Sports", "Underdog stories"],
        "short_template": TRUBY_ACTION_SHORT,
        "premium_template": TRUBY_ACTION_PREMIUM
    },
    "truby_love": {
        "id": "truby_love",
        "name": "Truby Love Story (Philosophy of Happiness)",
        "author": "John Truby",
        "description": "Love as dual-protagonist journey. TWO equal protagonists with emotional armor, the gaze, the scam, steps of intimacy, apparent defeat.",
        "best_for": ["Romance", "Romantic comedy", "Drama", "Literary fiction"],
        "short_template": TRUBY_LOVE_SHORT,
        "premium_template": TRUBY_LOVE_PREMIUM
    },
    "truby_thriller": {
        "id": "truby_thriller",
        "name": "Truby Thriller (Mixed Genre)",
        "author": "John Truby",
        "description": "Thriller combining Horror (dread), Action (pace), and Crime (investigation). Hero under suspicion, hunted while investigating.",
        "best_for": ["Thriller", "Suspense", "Conspiracy", "Political thriller"],
        "short_template": TRUBY_THRILLER_SHORT,
        "premium_template": TRUBY_THRILLER_PREMIUM
    },
    "truby_detective": {
        "id": "truby_detective",
        "name": "Truby Detective (Hunt for Truth)",
        "author": "John Truby",
        "description": "Detective story as methodical hunt for truth. The crime, investigation, interviews, revelation, and complex justice.",
        "best_for": ["Mystery", "Detective", "Crime", "Noir"],
        "short_template": TRUBY_DETECTIVE_SHORT,
        "premium_template": TRUBY_DETECTIVE_PREMIUM
    }
}


def list_beat_structures() -> list[dict]:
    """
    List all available beat structures for the dropdown.

    Returns:
        List of beat structure info dictionaries
    """
    return [
        {
            "id": structure["id"],
            "name": structure["name"],
            "author": structure["author"],
            "description": structure["description"],
            "best_for": structure["best_for"]
        }
        for structure in BEAT_STRUCTURES.values()
    ]


def get_beat_structure_info(structure_id: str) -> dict | None:
    """
    Get detailed info about a specific beat structure.

    Args:
        structure_id: ID of the beat structure

    Returns:
        Dictionary with structure info and beat details, or None if not found
    """
    structure = BEAT_STRUCTURES.get(structure_id)
    if not structure:
        return None

    result = {
        "id": structure["id"],
        "name": structure["name"],
        "author": structure["author"],
        "description": structure["description"],
        "best_for": structure["best_for"]
    }

    # Add beat details if not classic (which uses genre templates)
    if structure["short_template"]:
        result["short_beats"] = [
            {
                "beat_name": beat["beat_name"],
                "word_target": beat["word_target"],
                "description": beat["description"]
            }
            for beat in structure["short_template"].beats
        ]

    if structure["premium_template"]:
        result["premium_beats"] = [
            {
                "beat_name": beat["beat_name"],
                "word_target": beat["word_target"],
                "description": beat["description"]
            }
            for beat in structure["premium_template"].beats
        ]

    return result


def get_structure_template(structure_id: str, tier: str = "free") -> BeatTemplate | None:
    """
    Get the beat template for a specific structure and tier.

    Args:
        structure_id: ID of the beat structure
        tier: User tier (free or premium)

    Returns:
        BeatTemplate or None if structure uses genre-specific templates
    """
    structure = BEAT_STRUCTURES.get(structure_id)
    if not structure:
        return None

    if tier == "premium":
        return structure.get("premium_template")
    else:
        return structure.get("short_template")


# Genre to structure affinity mapping
# Higher weight = better fit for that genre
# Includes Truby genre-specific beats with highest affinity for their matching genres
GENRE_STRUCTURE_AFFINITY = {
    "sci-fi": {"heros_journey": 3, "save_the_cat": 2, "bond_beats": 2, "truby_beats": 1, "truby_action": 2},
    "scifi": {"heros_journey": 3, "save_the_cat": 2, "bond_beats": 2, "truby_beats": 1, "truby_action": 2},
    "fantasy": {"heros_journey": 4, "save_the_cat": 2, "truby_beats": 1, "bond_beats": 1},
    "mystery": {"truby_detective": 5, "truby_beats": 2, "save_the_cat": 2, "bond_beats": 1, "heros_journey": 1},
    "thriller": {"truby_thriller": 5, "bond_beats": 4, "save_the_cat": 2, "truby_beats": 1, "heros_journey": 1},
    "romance": {"truby_love": 5, "save_the_cat": 3, "truby_beats": 2, "heros_journey": 1, "bond_beats": 1},
    "horror": {"truby_horror": 5, "truby_beats": 2, "save_the_cat": 2, "heros_journey": 1, "bond_beats": 1},
    "drama": {"truby_beats": 4, "truby_love": 2, "save_the_cat": 2, "heros_journey": 1, "bond_beats": 1},
    "action": {"truby_action": 5, "bond_beats": 4, "save_the_cat": 3, "heros_journey": 2, "truby_beats": 1},
    "western": {"heros_journey": 3, "truby_beats": 2, "save_the_cat": 2, "bond_beats": 2, "truby_action": 2},
    "historical": {"truby_beats": 3, "heros_journey": 2, "save_the_cat": 2, "bond_beats": 1, "truby_love": 1},
    "sitcom": {"save_the_cat": 4, "truby_beats": 1, "bond_beats": 1, "heros_journey": 1},
    "comedy": {"save_the_cat": 4, "truby_beats": 1, "bond_beats": 1, "heros_journey": 1},
    "crime": {"truby_detective": 4, "truby_thriller": 3, "bond_beats": 2, "truby_beats": 1},
    "noir": {"truby_detective": 4, "truby_thriller": 3, "truby_beats": 2, "bond_beats": 1},
    "suspense": {"truby_thriller": 5, "bond_beats": 3, "save_the_cat": 2, "truby_detective": 2},
    "spy": {"bond_beats": 5, "truby_thriller": 3, "truby_action": 2, "save_the_cat": 1},
}


def select_varied_structure(
    genre: str,
    recent_structures: List[str] = None,
    exclude_classic: bool = True
) -> str:
    """
    Select a beat structure that provides variety.

    Avoids recently used structures and weights by genre affinity.

    Args:
        genre: Current story genre
        recent_structures: List of recently used structure IDs (most recent last)
        exclude_classic: If True, don't return "classic" (use genre-specific instead)

    Returns:
        Structure ID (e.g., "bond_beats", "heros_journey")
    """
    import random

    recent_structures = recent_structures or []

    # Get all available structures (excluding classic if requested)
    available = [sid for sid in BEAT_STRUCTURES.keys() if not (exclude_classic and sid == "classic")]

    # Remove structures used in the last 2 stories (to ensure variety)
    recently_used = set(recent_structures[-2:]) if recent_structures else set()
    candidates = [s for s in available if s not in recently_used]

    # If all structures were recently used, use all of them
    if not candidates:
        candidates = available

    # Get genre affinity weights
    genre_lower = genre.lower().replace("-", "").replace("_", "")
    affinity = GENRE_STRUCTURE_AFFINITY.get(genre_lower, {})

    # Build weighted list
    weighted_candidates = []
    for structure_id in candidates:
        weight = affinity.get(structure_id, 1)  # Default weight of 1
        weighted_candidates.extend([structure_id] * weight)

    # Random selection from weighted list
    if weighted_candidates:
        selected = random.choice(weighted_candidates)
    else:
        selected = random.choice(candidates) if candidates else "save_the_cat"

    return selected


def get_structure_for_story(
    story_bible: Dict[str, Any],
    tier: str = "free"
) -> tuple[str, BeatTemplate]:
    """
    Get the best beat structure for a story, considering variety.

    If user has set a specific beat_structure, use that.
    Otherwise, auto-select for variety based on recent history.

    Args:
        story_bible: User's story bible with history
        tier: User tier (free or premium)

    Returns:
        Tuple of (structure_id, BeatTemplate)
    """
    genre = story_bible.get("genre", "sci-fi")
    user_structure = story_bible.get("beat_structure")

    # If user explicitly set a structure (not "auto" or "classic"), use it
    if user_structure and user_structure not in ("auto", "classic", ""):
        template = get_structure_template(user_structure, tier)
        if template:
            return (user_structure, template)

    # Auto-select for variety
    story_history = story_bible.get("story_history", {})
    recent_structures = story_history.get("recent_beat_structures", [])

    selected_id = select_varied_structure(
        genre=genre,
        recent_structures=recent_structures,
        exclude_classic=True
    )

    template = get_structure_template(selected_id, tier)

    # Fall back to genre template if structure template not available
    if not template:
        template = get_template(genre, tier)
        return ("classic", template)

    return (selected_id, template)


# ===== TEMPLATE REGISTRY =====

TEMPLATES = {
    # Free tier (1500 words)
    "free_scifi": FREE_SCIFI_TEMPLATE,
    "free_mystery": FREE_MYSTERY_TEMPLATE,
    "free_romance": FREE_ROMANCE_TEMPLATE,
    "free_fantasy": FREE_FANTASY_TEMPLATE,
    "free_horror": FREE_HORROR_TEMPLATE,
    "free_drama": FREE_DRAMA_TEMPLATE,
    "free_western": FREE_WESTERN_TEMPLATE,
    "free_historical": FREE_HISTORICAL_TEMPLATE,

    # Premium tier (4500 words)
    "premium_scifi": PREMIUM_SCIFI_ADVENTURE,
    "premium_mystery": PREMIUM_MYSTERY_NOIR,
    "premium_romance": PREMIUM_ROMANCE_FULL,
    "premium_sitcom": PREMIUM_SITCOM_STYLE,
    "premium_fantasy": PREMIUM_FANTASY_EPIC,
    "premium_horror": PREMIUM_HORROR_DESCENT,
    "premium_drama": PREMIUM_DRAMA_DEEP,
    "premium_western": PREMIUM_WESTERN_EPIC,
    "premium_historical": PREMIUM_HISTORICAL_SAGA,
}


def get_template(genre: str, tier: str = "free") -> BeatTemplate:
    """
    Get the appropriate beat template based on genre and user tier.

    Args:
        genre: Genre of story (scifi, mystery, romance, sitcom, etc.)
        tier: User tier (free, premium)

    Returns:
        BeatTemplate for the story
    """
    # Normalize inputs
    genre = genre.lower().replace("-", "").replace("_", "")
    tier = tier.lower()

    # Map common variations
    genre_map = {
        "scifi": "scifi",
        "sciencefiction": "scifi",
        "sf": "scifi",
        "mystery": "mystery",
        "detective": "mystery",
        "noir": "mystery",
        "thriller": "mystery",
        "romance": "romance",
        "love": "romance",
        "romantic": "romance",
        "sitcom": "sitcom",
        "comedy": "sitcom",
        "funny": "sitcom",
        "fantasy": "fantasy",
        "magical": "fantasy",
        "epic": "fantasy",
        "horror": "horror",
        "scary": "horror",
        "suspense": "horror",
        "drama": "drama",
        "dramatic": "drama",
        "western": "western",
        "cowboy": "western",
        "frontier": "western",
        "historical": "historical",
        "history": "historical",
        "period": "historical",
    }

    normalized_genre = genre_map.get(genre, "scifi")

    # Build template key
    if tier == "premium":
        template_key = f"premium_{normalized_genre}"
    else:
        template_key = f"free_{normalized_genre}"

    # Get template or fall back to default
    template = TEMPLATES.get(template_key)

    if not template:
        # Fallback to free scifi if nothing matches
        template = TEMPLATES["free_scifi"]

    return template


def list_available_genres(tier: str = "free") -> List[str]:
    """
    List available genres for a given tier.

    Args:
        tier: User tier (free, premium)

    Returns:
        List of available genre names
    """
    if tier == "premium":
        return ["scifi", "mystery", "romance", "sitcom", "fantasy", "horror", "drama", "western", "historical"]
    else:
        return ["scifi", "mystery", "romance", "fantasy", "horror", "drama", "western", "historical"]
