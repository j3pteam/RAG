"""Two written reports built from items.score() output.

- build_self_report(name, scores): what the person who took the assessment
  receives. Developmental and strengths-first. It shows where they sit
  between two poles rather than a number, because these scores are raw
  scale positions from two or three items, not percentiles against a norm
  group, and a number invites more precision than the data has.
- build_coach_report(name, scores): for whoever works with them (coach,
  admin, program lead). Shows the numbers and bands, how to work with the
  person, what pressure may look like, patterns worth exploring, and
  questions to open conversations.

Both are plain data (dicts and lists of strings) so templates only lay
them out. Neither is ever given to the AI; build_persona_block() in
persona.py is the only thing that reaches the advisor's system prompt.

Wording is original. Not validated; developmental use only.
"""
from .items import DERAILERS, TRAITS

# Pole labels for the self report's spectrum, low pole first.
TRAIT_POLES = {
    "openness": ("Prefers the proven", "Seeks the new"),
    "conscientiousness": ("Flexible and spontaneous", "Planned and structured"),
    "extraversion": ("Reserved and reflective", "Outgoing and expressive"),
    "agreeableness": ("Candid and challenging", "Warm and accommodating"),
    "neuroticism": ("Steady under pressure", "Feels pressure keenly"),
}

# Adjective phrases (low, high) for sentences in the coach report.
TRAIT_ADJ = {
    "openness": ("practical and grounded", "curious and open to new ideas"),
    "conscientiousness": ("flexible and spontaneous", "organized and dependable"),
    "extraversion": ("reserved and reflective", "outgoing and expressive"),
    "agreeableness": ("candid and direct", "warm and collaborative"),
    "neuroticism": ("calm under pressure", "sensitive to pressure"),
}

# Per trait and band: what the person reads (self) and what their coach reads.
TRAIT_TEXT = {
    "openness": {
        "high": {
            "headline": "You're energized by new ideas and different ways of doing things.",
            "best": "You spot possibilities others miss, reframe stuck problems, and help people see past how it has always been done.",
            "watch": "Chasing the next idea before the current one lands, or losing people who need a concrete plan.",
            "try": "When you bring a new idea, pair it with one concrete first step and a date.",
            "coach_see": "Enjoys exploring ideas and alternatives; may open several threads in one conversation.",
            "coach_work": "Use frameworks, analogies, and 'what if' questions. Help them narrow down: 'Of these, which one will you act on this month?'",
        },
        "moderate": {
            "headline": "You balance openness to new approaches with respect for what already works.",
            "best": "You can champion change without discarding proven practice, which makes your ideas easier for others to adopt.",
            "watch": "Defaulting to the middle when a situation calls for a bolder or a more conservative call.",
            "try": "Before deciding, ask yourself whether this situation needs a new approach or a proven one, and commit to that.",
            "coach_see": "Pragmatic about change; neither a strong innovator nor a strong traditionalist.",
            "coach_work": "Offer both a proven option and a novel one, and let them choose.",
        },
        "low": {
            "headline": "You value what's proven and practical.",
            "best": "You bring grounded judgment, keep teams focused on what works, and protect against change for its own sake.",
            "watch": "Dismissing unfamiliar approaches before they're tested, or being seen as resistant to change.",
            "try": "When a new idea comes up, ask one curious question about it before evaluating it.",
            "coach_see": "Prefers concrete, practical discussion; may be skeptical of abstract models.",
            "coach_work": "Lead with real examples and evidence. Introduce new approaches as small, low-risk experiments.",
        },
    },
    "conscientiousness": {
        "high": {
            "headline": "You're organized, dependable, and follow through.",
            "best": "People trust you to deliver. You plan ahead, keep commitments, and bring order to messy work.",
            "watch": "Over-planning, rigidity when plans change, or holding others to your pace and standards.",
            "try": "Identify one area where 'good enough, on time' beats 'perfect, late', and practice letting it go.",
            "coach_see": "Arrives prepared and follows through on commitments; likes structure and clear next steps.",
            "coach_work": "Agree on clear goals, actions, and timelines. Written follow-ups land well. Watch that sessions don't become status updates.",
        },
        "moderate": {
            "headline": "You bring structure when it matters and flex when it doesn't.",
            "best": "You can plan and deliver while staying adaptable when priorities shift.",
            "watch": "Letting details slip during busy stretches without noticing.",
            "try": "During heavy weeks, pick the two commitments that matter most and protect those.",
            "coach_see": "Reasonably organized; follow-through may vary with workload.",
            "coach_work": "Keep action items few and specific, and check in on them.",
        },
        "low": {
            "headline": "You're flexible, adaptable, and comfortable with ambiguity.",
            "best": "You adjust quickly, handle surprises well, and don't get stuck on process.",
            "watch": "Commitments or details slipping, which can erode others' trust even when your intentions are good.",
            "try": "Write down every commitment you make in one place, and review it at the end of each day.",
            "coach_see": "Spontaneous and adaptable; action items may not get done between sessions.",
            "coach_work": "Keep structure light but explicit: one or two commitments per session, written down together. Explore what support makes follow-through easier.",
        },
    },
    "extraversion": {
        "high": {
            "headline": "You draw energy from people and speak up readily.",
            "best": "You build connection quickly, bring energy to groups, and make your views known.",
            "watch": "Filling the silence, talking before others have spoken, or overcommitting in the moment.",
            "try": "In your next meeting, ask a question and wait until at least two others have answered before giving your view.",
            "coach_see": "Talkative and energetic; thinks out loud and engages readily.",
            "coach_work": "Let them talk it through, then help them land on a point. Use pauses so reflection happens.",
        },
        "moderate": {
            "headline": "You can engage a room or work quietly, depending on what's needed.",
            "best": "You read when to step forward and when to step back.",
            "watch": "Holding back in settings where your view is needed.",
            "try": "Before important meetings, decide whether you're there mainly to contribute or to listen.",
            "coach_see": "Comfortable in groups and alone; adjusts to the setting.",
            "coach_work": "Mix discussion with time to think; ask what pace works for them.",
        },
        "low": {
            "headline": "You're reflective and measured, and you think before you speak.",
            "best": "You listen well, bring considered views, and stay calm and focused.",
            "watch": "Your ideas going unheard, or being read as disengaged when you're actually thinking.",
            "try": "Share one idea early in your next meeting, even if it isn't fully formed.",
            "coach_see": "Quieter and reflective; may need time before answering and may say less than they think.",
            "coach_work": "Send questions ahead of time, allow silence, and don't mistake few words for low engagement. Written reflection can help.",
        },
    },
    "agreeableness": {
        "high": {
            "headline": "You're supportive and collaborative, and you look for the good in people.",
            "best": "You build trust, help colleagues, and create teams where people feel safe.",
            "watch": "Avoiding hard conversations, over-accommodating, or being taken advantage of.",
            "try": "Pick one piece of difficult feedback you've been holding and deliver it clearly this week.",
            "coach_see": "Warm and cooperative; may agree readily in the session, so agreement isn't always commitment.",
            "coach_work": "Build rapport, then invite challenge directly: 'What would you push back on here?' Help them rehearse difficult conversations.",
        },
        "moderate": {
            "headline": "You can be supportive or direct, as the situation calls for.",
            "best": "You balance care for people with candor about problems.",
            "watch": "Choosing comfort when directness would serve better, or the reverse.",
            "try": "Before a hard conversation, decide what you most need the other person to hear.",
            "coach_see": "Balances warmth with candor.",
            "coach_work": "Be straightforward; they can take direct feedback delivered with respect.",
        },
        "low": {
            "headline": "You're candid and direct, and you're willing to challenge.",
            "best": "You name problems others avoid, push for high standards, and aren't swayed by politics.",
            "watch": "Bluntness landing as harshness, or people withholding information to avoid friction with you.",
            "try": "Before challenging an idea, name one thing about it that is useful.",
            "coach_see": "Direct and skeptical; may challenge the coach or the process.",
            "coach_work": "Be direct back; they respect candor. Don't over-soften. Explore how their impact lands with others.",
        },
    },
    "neuroticism": {
        "high": {
            "headline": "You feel pressure keenly and pay close attention to what could go wrong.",
            "best": "You anticipate risks, take problems seriously, and empathize with others under stress.",
            "watch": "Worry crowding out action, or stress showing up in your tone with others.",
            "try": "When you notice worry building, write down the one thing you can control and do it.",
            "coach_see": "Sensitive to stress and risk; may bring worry or frustration into sessions.",
            "coach_work": "Acknowledge the pressure before problem-solving. Help separate what's controllable from what isn't. Watch for overload.",
        },
        "moderate": {
            "headline": "You generally handle pressure well, with some tough stretches.",
            "best": "You take problems seriously without being thrown by them.",
            "watch": "Stress building up during long, high-stakes stretches.",
            "try": "Notice your early signs of strain (sleep, patience, focus) and plan recovery before you need it.",
            "coach_see": "Generally steady; stress may show during sustained pressure.",
            "coach_work": "Check in on workload and recovery during intense periods.",
        },
        "low": {
            "headline": "You stay calm and steady under pressure.",
            "best": "You're a stabilizing presence in a crisis and help others keep perspective.",
            "watch": "Underestimating risk, or missing how stressed others around you are.",
            "try": "In your next tense situation, ask others how it's landing for them before moving on.",
            "coach_see": "Calm and even-keeled; may understate problems or their own stress.",
            "coach_work": "Ask directly about risks and about the stress of people around them.",
        },
    },
}

# Pressure tendencies. "self_name" is the neutral name the person sees;
# the coach report uses the scale name from items.DERAILERS.
DERAILER_TEXT = {
    "volatile": {
        "notice": "your jaw or tone tightens when a plan slips, or you feel impatient with someone before they've finished explaining.",
        "self_name": "Intensity when things stall",
        "looks": "When progress stalls or people disappoint you, frustration can show quickly, and enthusiasm can cool abruptly.",
        "strength": "It comes from real passion and investment in results.",
        "try": "When you feel frustration rising, pause before responding and name the issue, not the person.",
        "coach_see": "Frustration may surface quickly in sessions, and enthusiasm for people or plans may swing.",
        "coach_respond": "Stay steady and don't match the intensity. Help them identify triggers and early warning signs.",
        "question": "When a project stalls, what do the people around you see from you in the first ten minutes?",
    },
    "mistrustful": {
        "notice": "you find yourself building a case about someone's motives instead of asking them.",
        "self_name": "Guardedness",
        "looks": "Under pressure you may question others' motives or keep score of who has let you down.",
        "strength": "It comes from alertness to politics and a wish to protect yourself and your team.",
        "try": "Before concluding someone has a hidden agenda, ask them one open question about their intent.",
        "coach_see": "May be slow to trust, skeptical of feedback sources, or quick to see bad intent.",
        "coach_respond": "Be transparent and consistent. Test assumptions about others' intentions gently.",
        "question": "Think of someone you don't fully trust at work. What else could explain what they did?",
    },
    "risk_averse": {
        "notice": "you ask for one more piece of data on a decision that's already clear enough.",
        "self_name": "Caution",
        "looks": "Under pressure you may delay decisions until you're sure you won't be criticized.",
        "strength": "It comes from care about getting things right and avoiding avoidable mistakes.",
        "try": "For your next pending decision, set a deadline and decide with the information you have by then.",
        "coach_see": "May hedge, defer decisions, or seek more data than the decision needs.",
        "coach_respond": "Make the cost of not deciding explicit. Encourage small, reversible decisions.",
        "question": "What decision are you delaying right now, and what is waiting costing you?",
    },
    "detached": {
        "notice": "you've stopped replying to messages or skipped check-ins during a busy week.",
        "self_name": "Pulling back",
        "looks": "Under pressure you may withdraw, go quiet, or focus on the task over people's reactions.",
        "strength": "It comes from independence and the ability to stay objective.",
        "try": "During stressful stretches, schedule brief check-ins with your key people so they don't read silence as distance.",
        "coach_see": "May become less communicative or harder to read when stressed, and may discount others' feelings.",
        "coach_respond": "Name the withdrawal when you see it. Explore the impact of silence on their team.",
        "question": "When you go quiet under pressure, what do you think your team assumes?",
    },
    "passive_resistant": {
        "notice": "you hear yourself say yes while thinking 'I'll get to it when I get to it.'",
        "self_name": "Quiet resistance",
        "looks": "You may agree to things you privately disagree with, then act on your own timeline.",
        "strength": "It comes from wanting to keep the peace while protecting your own priorities.",
        "try": "When you're asked for something you disagree with, say so at the time and propose an alternative.",
        "coach_see": "May say yes in the session but not follow through; agreement may mask disagreement.",
        "coach_respond": "Invite disagreement explicitly and check real commitment: 'On a scale of 1–10, how likely are you to do this?'",
        "question": "What have you agreed to recently that you don't intend to do?",
    },
    "arrogant": {
        "notice": "you've decided the answer before anyone else has spoken.",
        "self_name": "Self-assurance",
        "looks": "Under pressure your confidence can tip into dismissing others' input or feedback.",
        "strength": "It comes from real capability and conviction.",
        "try": "In your next discussion, ask for input before offering your view, and act on part of what you hear.",
        "coach_see": "Confident and may discount feedback or see themselves as the exception.",
        "coach_respond": "Use data and specific examples. Frame feedback in terms of their goals and reputation.",
        "question": "What's a piece of feedback you dismissed that turned out to be right?",
    },
    "limit_testing": {
        "notice": "you catch yourself thinking 'it's easier to apologize later.'",
        "self_name": "Pushing boundaries",
        "looks": "You may bend rules or act first and ask permission later.",
        "strength": "It comes from boldness and a bias for action.",
        "try": "Before taking a shortcut, ask who else would be affected if it went wrong.",
        "coach_see": "May be comfortable with risk and push past agreed limits.",
        "coach_respond": "Be clear about boundaries. Explore consequences for trust and for others.",
        "question": "Where are you currently operating on 'ask forgiveness, not permission'? What's the downside if it goes wrong?",
    },
    "attention_seeking": {
        "notice": "you say yes in the moment because it sounds exciting, before checking your calendar.",
        "self_name": "Drawn to the spotlight",
        "looks": "You may enjoy center stage and take on more than you can deliver because it's exciting.",
        "strength": "It comes from energy, visibility, and enthusiasm.",
        "try": "Before saying yes to something new, check what you'd have to drop to deliver it.",
        "coach_see": "Enjoys visibility; may overcommit or bring dramatic energy to sessions.",
        "coach_respond": "Help them evaluate commitments before accepting. Celebrate the team's wins, not only theirs.",
        "question": "What's on your plate because it was exciting to say yes to?",
    },
    "eccentric": {
        "notice": "people nod but don't act on your idea, or ask you to explain it again.",
        "self_name": "Unconventional thinking",
        "looks": "Your ideas may be ahead of others or hard for them to follow.",
        "strength": "It comes from creativity and seeing connections others miss.",
        "try": "When sharing a big idea, start from the problem the audience cares about.",
        "coach_see": "Creative and original; ideas may be hard for others to follow or act on.",
        "coach_respond": "Help translate ideas into practical steps and check how they land with others.",
        "question": "Which of your ideas has had trouble getting traction, and what would make it easier for others to adopt?",
    },
    "perfectionistic": {
        "notice": "you're redoing something a colleague already finished, or a deadline passes while you polish.",
        "self_name": "High standards",
        "looks": "You may find it hard to delegate or keep reworking past a deadline.",
        "strength": "It comes from real commitment to quality.",
        "try": "Delegate one task this week with a clear standard of done, and don't redo it.",
        "coach_see": "Holds high standards; may be a bottleneck or struggle to delegate.",
        "coach_respond": "Explore the cost of the standard to them and their team. Define 'good enough' together.",
        "question": "What are you holding onto that someone else could do at 80% as well as you?",
    },
    "deferential": {
        "notice": "you soften or drop your view as soon as someone senior speaks.",
        "self_name": "Deference to authority",
        "looks": "You may hold back disagreement with senior leaders or seek their approval before acting.",
        "strength": "It comes from loyalty and respect for the chain of command.",
        "try": "In your next meeting with a senior leader, share one view that differs from theirs, with your reasons.",
        "coach_see": "May defer to authority, including the coach, and seek approval rather than take a position.",
        "coach_respond": "Ask for their view before sharing yours. Rehearse disagreeing with a senior leader.",
        "question": "When did you last disagree openly with someone senior to you? What happened?",
    },
}

# Combinations worth exploring in the coach report:
# (trait, trait band, derailer, text). Shown when the trait is in that band
# and the derailer is elevated.
PATTERNS = [
    ("agreeableness", "high", "deferential",
     "Warmth plus deference: may avoid conflict with senior leaders, so agreement may not mean buy-in."),
    ("agreeableness", "high", "passive_resistant",
     "Warmth plus quiet resistance: may say yes to keep the peace and then not follow through."),
    ("extraversion", "high", "attention_seeking",
     "Outgoing plus spotlight-seeking: at risk of overcommitting in the moment, and of taking up the space others need."),
    ("conscientiousness", "high", "perfectionistic",
     "Structured plus perfectionistic: may become a delivery bottleneck and struggle to delegate."),
    ("agreeableness", "low", "arrogant",
     "Candor plus self-assurance: may dismiss input and discourage people from raising concerns."),
    ("agreeableness", "low", "mistrustful",
     "Candor plus guardedness: can come across as suspicious or combative; trust will take time."),
    ("neuroticism", "high", "volatile",
     "Pressure-sensitive plus intensity: stress may escalate quickly into visible frustration."),
    ("neuroticism", "high", "risk_averse",
     "Pressure-sensitive plus caution: at risk of decision paralysis under high stakes."),
    ("openness", "high", "eccentric",
     "Idea-driven plus unconventional: ideas may outpace others' ability to follow or execute."),
    ("conscientiousness", "low", "limit_testing",
     "Flexible plus boundary-pushing: follow-through and compliance risks worth discussing openly."),
    ("extraversion", "low", "detached",
     "Reserved plus pulling back: withdrawal under stress may be hard for others to detect."),
    ("neuroticism", "low", "detached",
     "Steady plus pulling back: may miss or discount stress in others."),
]

GENERAL_REFLECTIONS = [
    "Which of these descriptions feels most like you? Which feels least like you?",
    "Who at work would recognize these patterns in you, and what would they add?",
    "What is one small change you could try in the next two weeks?",
]


def _join(items):
    """'a', 'a and b', 'a, b, and c' — the phrases themselves contain 'and'."""
    if len(items) <= 2:
        return " and ".join(items)
    return ", ".join(items[:-1]) + ", and " + items[-1]


def _trait_name(k):
    return TRAITS[k][0]


def _derailer_name(k):
    return DERAILERS[k][0]


def _sorted_derailers(scores, bands):
    ds = scores.get("derailers") or {}
    return sorted((k for k, v in ds.items() if v["band"] in bands),
                  key=lambda k: -ds[k]["score"])


def _focus_areas(scores, limit=3):
    """Up to `limit` development areas: elevated pressure tendencies first
    (highest first), then the flip side of the strongest non-moderate traits."""
    out = []
    for k in _sorted_derailers(scores, ("elevated",)):
        t = DERAILER_TEXT[k]
        out.append({"kind": "pressure", "key": k, "title": t["self_name"],
                    "coach_title": _derailer_name(k), "why": t["looks"],
                    "notice": t["notice"],
                    "try": t["try"], "coach_how": t["coach_respond"]})
    traits = scores.get("traits") or {}
    extremes = sorted((k for k, v in traits.items() if v["band"] != "moderate"),
                      key=lambda k: -abs(traits[k]["score"] - 50))
    for k in extremes:
        t = TRAIT_TEXT[k][traits[k]["band"]]
        adj = TRAIT_ADJ[k][1 if traits[k]["band"] == "high" else 0]
        out.append({"kind": "trait", "key": k, "title": f"The flip side of being {adj}",
                    "coach_title": f"{_trait_name(k)} ({traits[k]['band']})",
                    "why": t["watch"], "notice": "", "try": t["try"], "coach_how": t["coach_work"]})
    return out[:limit]


def build_self_report(name, scores):
    """The developmental report for the person who took the assessment."""
    traits = scores.get("traits") or {}
    style = []
    for k, v in traits.items():
        t = TRAIT_TEXT[k][v["band"]]
        low, high = TRAIT_POLES[k]
        style.append({"key": k, "name": _trait_name(k), "low": low, "high": high,
                      "position": v["score"], "headline": t["headline"],
                      "best": t["best"], "watch": t["watch"]})

    ds = scores.get("derailers") or {}
    watch = [{"key": k, "name": DERAILER_TEXT[k]["self_name"],
              "looks": DERAILER_TEXT[k]["looks"],
              "strength": DERAILER_TEXT[k]["strength"],
              "try": DERAILER_TEXT[k]["try"]}
             for k in _sorted_derailers(scores, ("elevated",))]
    # 50 is two "Neutral" answers, so only list moderates above the midpoint.
    occasional = [DERAILER_TEXT[k]["self_name"]
                  for k in _sorted_derailers(scores, ("moderate",))
                  if ds[k]["score"] >= 60][:3]

    strengths = [TRAIT_TEXT[k][v["band"]]["best"] for k, v in traits.items()
                 if v["band"] != "moderate"][:3]
    if not strengths:
        strengths = ["You adapt your style to the situation rather than relying on one approach."]

    focus = _focus_areas(scores)
    focus_keys = {f["key"] for f in focus}
    for w in watch:
        w["in_focus"] = w["key"] in focus_keys
    reflections = [f"When have you seen “{w['name'].lower()}” show up for you recently, and what set it off?"
                   for w in watch[:2]] + GENERAL_REFLECTIONS

    return {"name": name, "first_name": name.split()[0] if name else "",
            "strengths": strengths, "style": style, "watch": watch,
            "occasional": occasional, "focus": focus, "reflections": reflections}


def build_coach_report(name, scores):
    """The report for someone working with this person."""
    traits = scores.get("traits") or {}
    ds = scores.get("derailers") or {}
    first = name.split()[0] if name else "They"

    trait_rows = [{"key": k, "name": _trait_name(k), "score": v["score"], "band": v["band"],
                   "see": TRAIT_TEXT[k][v["band"]]["coach_see"],
                   "work": TRAIT_TEXT[k][v["band"]]["coach_work"]}
                  for k, v in traits.items()]
    derailer_rows = [{"key": k, "name": _derailer_name(k), "score": v["score"], "band": v["band"]}
                     for k, v in sorted(ds.items(), key=lambda kv: -kv[1]["score"])]

    elevated = _sorted_derailers(scores, ("elevated",))
    to_watch = [{"key": k, "name": _derailer_name(k), "score": ds[k]["score"],
                 "see": DERAILER_TEXT[k]["coach_see"],
                 "respond": DERAILER_TEXT[k]["coach_respond"],
                 "question": DERAILER_TEXT[k]["question"]} for k in elevated]
    keep_eye = [_derailer_name(k) for k in _sorted_derailers(scores, ("moderate",))
                if ds[k]["score"] >= 60]

    patterns = [text for t, band, d, text in PATTERNS
                if traits.get(t, {}).get("band") == band and ds.get(d, {}).get("band") == "elevated"]

    # Snapshot: strongest traits in words, then the pressure picture.
    extremes = sorted((k for k, v in traits.items() if v["band"] != "moderate"),
                      key=lambda k: -abs(traits[k]["score"] - 50))
    descr = [TRAIT_ADJ[k][1 if traits[k]["band"] == "high" else 0] for k in extremes[:3]]
    if descr:
        style_line = (f"{name}'s answers describe someone " +
                      _join(descr) + ".")
    else:
        style_line = f"{name}'s answers describe a balanced style, with no strong leaning on any trait."
    if elevated:
        names = [_derailer_name(k).lower() for k in elevated]
        n = len(names)
        count = ["One", "Two", "Three", "Four", "Five", "Six", "Seven",
                 "Eight", "Nine", "Ten", "Eleven"][n - 1]
        pressure_line = (f"{count} pressure tendenc{'y is' if n == 1 else 'ies are'} elevated: " +
                         _join(names) + ".")
    else:
        pressure_line = "No pressure tendencies are elevated."

    questions = [r["question"] for r in to_watch]
    for k in extremes[:2]:
        adj = TRAIT_ADJ[k][1 if traits[k]["band"] == "high" else 0]
        questions.append(f"You describe yourself as {adj}. Where does that help you most, and where does it get in your way?")
    questions.append("What would you most like to be different six months from now?")

    return {"name": name, "first_name": first, "snapshot": [style_line, pressure_line],
            "traits": trait_rows, "derailers": derailer_rows, "to_watch": to_watch,
            "keep_eye": keep_eye, "patterns": patterns, "questions": questions,
            "focus": _focus_areas(scores)}
