"""Item bank and scoring. Original items (not Hogan/HDS content). Developmental use only."""

LIKERT = ["Strongly disagree", "Disagree", "Neutral", "Agree", "Strongly agree"]

# (text, reverse_scored)
TRAITS = {
    "openness": ("Openness to experience", [
        ("I enjoy exploring ideas that challenge how things are usually done.", False),
        ("I'm drawn to new approaches even when the current one works.", False),
        ("I prefer familiar routines over experimenting.", True)]),
    "conscientiousness": ("Conscientiousness", [
        ("I follow through on commitments without reminders.", False),
        ("I plan my work well ahead of deadlines.", False),
        ("My schedule and workspace tend to be disorganized.", True)]),
    "extraversion": ("Extraversion", [
        ("I gain energy from being around groups of people.", False),
        ("I readily speak up in meetings.", False),
        ("I prefer to stay in the background at social events.", True)]),
    "agreeableness": ("Agreeableness", [
        ("I go out of my way to help colleagues.", False),
        ("I assume good intentions in others.", False),
        ("I can be blunt even when it hurts feelings.", True)]),
    "neuroticism": ("Emotional reactivity", [
        ("I worry about things that might go wrong.", False),
        ("I get stressed easily under pressure.", False),
        ("I stay calm in tense situations.", True)]),
}

DERAILERS = {
    "volatile": ("Volatile", [
        "When projects stall, my frustration shows quickly.",
        "My enthusiasm for people or ideas can fade abruptly when they disappoint me."]),
    "mistrustful": ("Mistrustful", [
        "I often suspect others have hidden agendas.",
        "I keep track of who has let me down."]),
    "risk_averse": ("Risk-averse", [
        "I delay decisions until I'm sure I won't be criticized.",
        "I'd rather miss an opportunity than risk a visible mistake."]),
    "detached": ("Detached", [
        "Under pressure, I withdraw and keep to myself.",
        "Other people's emotional reactions to my decisions are mostly their problem."]),
    "passive_resistant": ("Passive-resistant", [
        "I agree to requests I privately resent, then do them on my own timeline.",
        "I get annoyed when others interrupt my priorities, even if I don't say so."]),
    "arrogant": ("Arrogant", [
        "I'm usually the most capable person in the room.",
        "Rules and feedback apply less to me than to most people."]),
    "limit_testing": ("Limit-testing", [
        "I enjoy testing limits to see what I can get away with.",
        "I'd rather act and apologize later than ask permission."]),
    "attention_seeking": ("Attention-seeking", [
        "I like being the center of attention.",
        "I sometimes take on more than I can deliver because it's exciting."]),
    "eccentric": ("Eccentric", [
        "People often don't follow my ideas because I'm ahead of them.",
        "I see connections others miss, even when they call them unusual."]),
    "perfectionistic": ("Perfectionistic", [
        "I find it hard to delegate because others won't do it right.",
        "I'll keep reworking something until it meets my standard, even past the deadline."]),
    "deferential": ("Overly deferential", [
        "I rarely push back on my boss, even when I disagree.",
        "I seek approval from senior leaders before acting."]),
}

def _interleave(items, group_size):
    """Mix items so the same scale isn't answered back to back."""
    groups = [items[i:i + group_size] for i in range(0, len(items), group_size)]
    return [g[j] for j in range(group_size) for g in groups if j < len(g)]


# One onboarding step ("Personality assessment") with two parts.
# The existing Self behavioral assessment is separate and untouched.
PARTS = [
    {"key": "traits", "title": "Part 1: Everyday style",
     "intro": "How you tend to show up day to day. Answer based on how you usually are, not how you'd like to be.",
     "items": _interleave([(f"{k}_{i}", t) for k, (_, its) in TRAITS.items() for i, (t, _) in enumerate(its)], 3)},
    {"key": "derailers", "title": "Part 2: Under pressure",
     "intro": "Think about stressful stretches, high stakes, or when you're tired or not being watched.",
     "items": _interleave([(f"{k}_{i}", t) for k, (_, its) in DERAILERS.items() for i, t in enumerate(its)], 2)},
]
ALL_ITEM_IDS = [i for part in PARTS for i, _ in part["items"]]


def _pct(total, lo, hi):
    return round((total - lo) / (hi - lo) * 100)


def trait_band(p):
    return "high" if p >= 65 else "low" if p <= 35 else "moderate"


def derailer_band(p):
    return "elevated" if p >= 70 else "moderate" if p >= 40 else "low"


def score(answers):
    """answers: {item_id: 1..5} for all 37 items.
    Returns {"traits": {scale: {"score","band"}}, "derailers": {...}}. Raises ValueError if incomplete."""
    missing = [i for i in ALL_ITEM_IDS if i not in answers]
    if missing:
        raise ValueError(f"{len(missing)} statements unanswered")
    vals = {i: int(answers[i]) for i in ALL_ITEM_IDS}
    if any(v < 1 or v > 5 for v in vals.values()):
        raise ValueError("answers must be 1-5")

    traits = {}
    for k, (_, its) in TRAITS.items():
        s = sum((6 - vals[f"{k}_{i}"]) if rev else vals[f"{k}_{i}"] for i, (_, rev) in enumerate(its))
        p = _pct(s, 3, 15)
        traits[k] = {"score": p, "band": trait_band(p)}
    derailers = {}
    for k in DERAILERS:
        p = _pct(vals[f"{k}_0"] + vals[f"{k}_1"], 2, 10)
        derailers[k] = {"score": p, "band": derailer_band(p)}
    return {"traits": traits, "derailers": derailers}
