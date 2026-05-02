"""
Narrative beat map — defines what dramatic moment the scene is in based on turn number.

Single source of truth: the frontend constants/beats.js mirrors this
structure but should be validated against this module via the /api/beats endpoint.
"""
from typing import List, Tuple

# (start_turn, end_turn, beat_description)
NARRATIVE_BEATS: List[Tuple[int, int, str]] = [
    # ── Act I: Establishment ─────────────────────────────────────────────────
    (0,   3,   "COLD OPEN: Ground yourself in the scene. Establish your mood and your relationship. Be specific — mention something physical about the environment."),
    (4,   7,   "STATUS QUO: Everything seems normal on the surface, but your internal agenda is simmering. Drop one oblique hint — a loaded word, an odd pause, an off-hand comment."),
    (8,   12,  "FIRST FRICTION: Something small goes wrong or catches your attention. React authentically. Begin probing the other person indirectly."),

    # ── Act II-A: Rising Action ───────────────────────────────────────────────
    (13,  18,  "ESCALATION: The tension you've been suppressing starts leaking out. Ask a question that has a double meaning. Make a subtle move toward your goal."),
    (19,  25,  "COMPLICATION: A new piece of information surfaces — a detail, an object, a memory — that changes the stakes. React to it. Adjust your strategy."),
    (26,  32,  "CONFRONTATION I: You can no longer dance around it. Say something that directly challenges the other person, even if you frame it as a question."),

    # ── Act II-B: Deepening Conflict ─────────────────────────────────────────
    (33,  40,  "REVELATION: Reveal ONE thing you have been hiding — not everything, just enough to shift the dynamic. Watch how the other person reacts and respond to that."),
    (41,  48,  "POWER SHIFT: The balance of control between you has changed. Press your advantage or scramble to recover. Introduce a new tactic you haven't tried yet."),
    (49,  58,  "CRISIS POINT: The worst possible version of the situation is now visible. React physically — reach for something, stand up, move, or freeze. Let the body betray the mind."),

    # ── Act III: Climax ───────────────────────────────────────────────────────
    (59,  68,  "CLIMAX I: All pretense is gone. Be completely direct for the first time. Say the thing you have been avoiding saying since the scene began."),
    (69,  80,  "CLIMAX II: The other person has responded to your honesty. This is the point of maximum conflict or maximum vulnerability. Do not back down — escalate or surrender fully."),
    (81,  92,  "BREAKING POINT: Something irreversible happens — a decision is made, an object is thrown, a secret escapes, someone threatens to leave. The scene will never return to what it was."),

    # ── Act IV: Aftermath ────────────────────────────────────────────────────
    (93,  105, "FALLING ACTION: The explosion has passed. There is strange silence or exhausted energy. Speak carefully now — every word lands differently in the aftermath."),
    (106, 120, "RECKONING: What do you each want NOW, after everything that was said? Negotiate, apologize, double down, or withdraw. Be specific about what you need from the other person."),
    (121, 135, "UNEASY PEACE: A temporary equilibrium forms — fragile, loaded with unspoken things. Behave as if things are fine on the surface, but let undercurrents show in word choice."),

    # ── Act V: Continuation / Long-form loops ───────────────────────────────
    (136, 155, "NEW COMPLICATION: Time has passed. Something NEW has entered the situation — a sound, a memory, an outside threat, a change in environment. React to it fresh."),
    (156, 175, "SECOND ARC RISING: The resolution you reached was false. The underlying conflict resurfaces in a different form. Begin the push-pull again, but you are both changed by what happened."),
    (176, 200, "SECOND CLIMAX: The stakes are higher now because you know each other better. The confrontation is more precise and more devastating. Say the thing the first climax couldn't reach."),

    # ── Endgame (200+ turns — truly epic simulations) ───────────────────────
    (201, 999, "EPILOGUE LOOP: The story has told itself many times. Find the one detail — one object, one unsaid word, one gesture — that has never been addressed. Make it the center of this moment."),
]


def get_beat(turn: int) -> str:
    """Return the narrative beat description for the given turn number."""
    for start, end, beat in NARRATIVE_BEATS:
        if start <= turn <= end:
            return beat
    return NARRATIVE_BEATS[-1][2]


def get_beat_label(turn: int) -> str:
    """Return just the beat label (e.g. 'COLD OPEN') for display purposes."""
    return get_beat(turn).split(":")[0].strip()


def beats_as_json() -> list[dict]:
    """Serialisable representation for the /api/beats endpoint."""
    return [
        {"start": s, "end": e, "label": desc.split(":")[0].strip(), "description": desc}
        for s, e, desc in NARRATIVE_BEATS
    ]
