"""
Beat templates for different genres and story lengths.

Each template defines the structure for a complete standalone story.
"""

from typing import List, Dict, Any


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


# ===== FREE TIER TEMPLATES (1500 words) =====

FREE_SCIFI_TEMPLATE = BeatTemplate(
    name="scifi_short",
    genre="sci-fi",
    total_words=1500,
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
    total_words=1500,
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
    total_words=1500,
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
    total_words=1500,
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
    total_words=1500,
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
    total_words=1500,
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
    total_words=1500,
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
    total_words=1500,
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
    total_words=1500,
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
    total_words=1500,
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
    total_words=1500,
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
        "author": "FictionMail",
        "description": "Genre-optimized beats tailored for each story type (sci-fi, mystery, romance, etc.)",
        "best_for": ["All genres", "Genre-specific conventions", "Reader expectations"],
        "short_template": None,  # Uses genre-specific templates
        "premium_template": None  # Uses genre-specific templates
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
