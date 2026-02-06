import json
import re
from groq import Groq
from config import settings

client = Groq(api_key=settings.GROQ_API_KEY)
# client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def call_groq(prompt, temperature=0.2, max_tokens=300):
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",  # ✅ current supported fast model
            messages=[
                {
                    "role": "system",
                    "content": "You are a strict, professional HR interviewer."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=temperature,
            max_tokens=max_tokens
        )

        content = response.choices[0].message.content.strip()

        # Try JSON parse (important for decisions)
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return {"text": content}

    except Exception as e:
        print("❌ Groq error:", e)
        return {}
    
def should_end_interview(conversation):
    candidate_answers = [
        m["text"].lower()
        for m in conversation
        if m["role"] == "candidate"
    ]

    # ---- HARD STOP RULES ----
    refusal_count = sum(
        1 for a in candidate_answers
        if any(p in a for p in [
            "i don't know",
            "no idea",
            "skip",
            "not sure",
            "cannot answer",
            "can't handle"
        ])
    )

    if refusal_count >= 2:
        return True, "Too many unanswered questions"

    very_short = sum(1 for a in candidate_answers if len(a.split()) <= 3)
    if very_short >= 3:
        return True, "Insufficient detail in responses"

    if len(candidate_answers) >= 6:
        return True, "Interview length reached"


    prompt = f"""
You are a senior HR interviewer.

Conversation:
{conversation}

Question:
Have you gathered enough information to evaluate this candidate?

Answer strictly as JSON:
{{
  "end": true/false,
  "reason": "short reason"
}}
"""

    ai = call_groq(prompt)   # you already have this
    return ai.get("end", False), ai.get("reason", "")



def generate_ai_turn(conversation):
    end, reason = should_end_interview(conversation)

    if end:
        return {
            "action": "end_interview",
            "reason": reason
        }

    prompt = f"""
You are a professional HR interviewer on a phone call.

Rules:
- Ask ONE clear question
- Adapt based on candidate's last answer
- If candidate is junior, simplify
- If experienced, go deeper
- Do NOT repeat questions
- Be natural and concise

Conversation so far:
{conversation}

Respond ONLY in JSON:
{{
  "action": "ask",
  "intent": "intro|technical|problem|communication",
  "text": "question to ask"
}}
"""

    return call_groq(prompt)


def local_invalid_check(answer: str) -> dict:
    if not answer or not answer.strip():
        return {"valid": False, "reason": "Empty answer"}

    cleaned = answer.strip().lower()

    REFUSAL_PATTERNS = [
        r"\b(i am|i'm)\s+(not able|unable)\s+to\b",
        r"\b(i|we)\s+(cannot|can't)\s+(answer|tell|explain|handle)\b",

        r"\b(i\s*(do not|don't)\s*know)\b",
        r"\b(no\s*idea)\b",
        r"\b(not\s*sure)\b",

        r"\b(skip|skip this|pass this)\b",
        r"\b(nothing\s+to\s+say)\b",

        r"\b(not\s+able\s+to\s+handle)\b",
        r"\b(can't\s+handle)\b",
    ]


    for pattern in REFUSAL_PATTERNS:
        if re.match(pattern, cleaned):
            return {"valid": False, "reason": "Explicitly declined to answer"}

    if len(cleaned.split()) < 5:
        return {"valid": True, "reason": "Very short answer"}

    return {"valid": True, "reason": ""}

#  ----------------------------------------------------------------------

def extract_answers_from_conversation(conversation):
    """
    Groups candidate answers based on last AI intent.
    """
    grouped = {
        "INTRO": [],
        "TECHNICAL": [],
        "PROBLEM": [],
        "COMMUNICATION": []
    }

    last_intent = None

    INTENT_MAP = {
        "intro": "INTRO",
        "technical": "TECHNICAL",
        "skills": "TECHNICAL",
        "project": "TECHNICAL",
        "problem": "PROBLEM",
        "problem_solving": "PROBLEM",
        "challenge": "PROBLEM",
        "communication": "COMMUNICATION",
        "team": "COMMUNICATION"
    }

    for turn in conversation:
        if turn["role"] == "ai":
            last_intent = INTENT_MAP.get(turn.get("intent"), last_intent)


        elif turn["role"] == "candidate" and last_intent:
            grouped[last_intent].append(turn["text"])
            
    intent_coverage = {k: len(v) for k, v in grouped.items()}

    # Merge multiple answers into one per category
    return {
        "answers": {
            k: " ".join(v).strip()
            for k, v in grouped.items() if v
        },
        "coverage": intent_coverage
    }


def build_hr_summary(final_score, decision, red_flags, per_question_notes):
    strengths = []
    weaknesses = []
    risk_patterns = []

    avg_comm = 0
    avg_just = 0

    for note in per_question_notes:
        avg_comm += note["communication"]
        avg_just += note["justification"]

        if note["communication"] >= 7 and note["justification"] >= 6:
            strengths.append(note["question"])
        elif note["justification"] <= 3:
            weaknesses.append(note["question"])

        reasoning = note.get("reasoning", "").lower()
        if "vague" in reasoning or "unclear" in reasoning:
            risk_patterns.append("lack of clarity in explanations")
        if "no examples" in reasoning or "lacked examples" in reasoning:
            risk_patterns.append("insufficient practical examples")

    count = max(len(per_question_notes), 1)
    avg_comm /= count
    avg_just /= count

    summary = []

    if avg_comm >= 6:
        summary.append("The candidate communicated ideas clearly and was generally understandable.")
    else:
        summary.append("The candidate struggled to clearly communicate ideas during the interview.")

    if avg_just >= 6:
        summary.append("Responses demonstrated reasonable technical understanding and practical awareness.")
    elif avg_just >= 4:
        summary.append("Technical explanations were basic and lacked consistent depth.")
    else:
        summary.append("Technical and problem-solving explanations were weak and lacked clarity.")

    if strengths:
        summary.append(
            "Stronger responses were observed in: " + ", ".join(strengths) + "."
        )

    if weaknesses:
        summary.append(
            "Weaker or unclear responses were noted in: " + ", ".join(weaknesses) + "."
        )

    if risk_patterns:
        summary.append(
            "Common concerns included " + ", ".join(set(risk_patterns)) + "."
        )

    if red_flags:
        summary.append(
            "Additional concerns were identified due to " + "; ".join(red_flags) + "."
        )

    if decision == "STRONG HIRE":
        summary.append(
            "Based on consistent communication skills and acceptable technical reasoning, the candidate is considered a strong fit."
        )
    elif decision == "CONSIDER":
        summary.append(
            "The candidate shows potential but would benefit from stronger technical depth and clearer explanations."
        )
    else:
        summary.append(
            "Due to weak technical justification and inconsistent responses, the candidate is not recommended at this stage."
        )

    summary.append(
        f"The final interview score was {final_score}/100, leading to a decision of {decision}."
    )

    return " ".join(summary)

def apply_experience_bonus(item, comm, just):
    answer = item["answer"].lower()

    senior_signals = [
        "years of experience",
        "production",
        "owned",
        "maintained",
        "deployment",
        "services",
        "architecture",
        "clients",
        "real users"
    ]

    signal_count = sum(1 for s in senior_signals if s in answer)

    if signal_count >= 2:
        just = min(just + 1.6, 10)
        comm = min(comm + 1.0, 10)

    return comm, just

def enforce_real_world_floors(answer: str, comm: float, just: float):
    """
    Enforces minimum justification scores based on real-world signals.
    This runs AFTER Groq scoring and BEFORE weighting.
    """

    if not answer:
        return comm, just

    text = answer.lower()

    # ---- real tool / tech signals ----
    tool_signals = [
        "django", "flask", "fastapi", "spring", "node",
        "aws", "gcp", "azure", "docker", "kubernetes",
        "postgres", "mysql", "mongodb", "redis",
        "react", "angular", "vue",
        "api", "microservice", "service", "backend",
        "ci/cd", "deployment", "production"
    ]

    # ---- real problem + action signals ----
    problem_signals = [
        "issue", "problem", "bug", "error", "failure",
        "latency", "performance", "scaling", "downtime",
        "timeout", "crash", "bottleneck"
    ]

    action_signals = [
        "fixed", "solved", "implemented", "designed",
        "optimized", "refactored", "debugged",
        "improved", "migrated", "handled"
    ]

    has_tools = any(t in text for t in tool_signals)
    has_problem = any(p in text for p in problem_signals)
    has_action = any(a in text for a in action_signals)

    # ---- enforce floors ----
    if has_tools:
        just = max(just, 5.0)

    if has_problem and has_action:
        just = max(just, 6.0)

    # Slight communication bump if explanation is concrete
    if has_problem and has_action and comm < 6:
        comm = max(comm, 5.5)

    return comm, just

def safe_json_extract(text):
    try:
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            return json.loads(match.group())
    except Exception:
        pass
    return None


def groq_score_full_interview(questions_with_answers):

    formatted_qa = ""
    for i, qa in enumerate(questions_with_answers, start=1):
        formatted_qa += f"""
Q{i}: {qa['question']}
Answer:
{qa['answer']}
"""

    prompt = f"""
ROLE:
You are a professional HR evaluator assessing real-world software engineers.
Score answers based on the candidate’s stated experience and practical exposure.

CONTEXT:
- Answers are generated from speech-to-text (STT)
- Ignore grammar mistakes, repetition, filler words, and accent issues
- Do NOT penalize informal or spoken phrasing
- Focus ONLY on professional meaning and substance

EVALUATION PRINCIPLES (NON-NEGOTIABLE):
- Evaluate EACH question independently
- Do NOT compare answers across questions
- Do NOT infer unstated skills or experience
- Concise but real answers are VALID
- Missing or explicit refusal answers MUST score 0

REAL-WORLD CREDIT RULES (CRITICAL):
- Mentioning real tools, frameworks, projects, clients, or years of experience
  MUST receive meaningful credit
- Listing multiple real technologies implies hands-on exposure
- Naming a real problem + constraint + action counts as valid problem-solving
- Do NOT penalize answers for lack of storytelling or structure (spoken interview)

INTRO QUESTION RULE:
- Mentioning years of experience + role + tools is sufficient
- Intro answers do NOT require metrics or achievements

EXPERIENCE-AWARE EVALUATION:
- Detect experience ONLY from the answer itself
- Adjust expectations accordingly:

Junior signals:
- learning-focused language
- academic or small projects
→ require more explanation for high scores

Mid-level signals:
- real projects
- backend ownership
- client or integration work
→ moderate explanation is sufficient

Senior signals:
- production systems
- architecture, deployments, integrations
- cross-team collaboration
→ concise answers are acceptable and should score higher

SCORING RUBRIC:

Communication (0–10):
0–2: refusal, incoherent, irrelevant  
3–4: basic clarity  
5–7: understandable, spoken clarity  
7–8: clear, structured, professional  
9–10: exceptionally precise and confident  

Justification (0–10):
0–2: no substance or refusal  
3–4: vague but real exposure  
5–7: real tools, projects, or responsibilities  
7–8: problem-solving or ownership  
9–10: strong impact, decisions, or trade-offs  

IMPORTANT FLOOR RULES:
- If an answer mentions real tools or projects, justification MUST NOT be below 5
- If an answer describes a real problem and action, justification MUST NOT be below 6

SOFT FLAGS (DO NOT REDUCE SCORES):
- scripted_sounding
- confidence_without_content (only TRUE if communication ≥7 and justification ≤3)

QUESTIONS & ANSWERS:
{formatted_qa}

OUTPUT RULES:
- VALID JSON ONLY
- No markdown or extra text
- One result per question
- Use EXACT question text
- Reasoning must reference the actual answer
- Do NOT normalize or cap scores

RETURN JSON ONLY:
{{
  "results": [
    {{
      "question": "<exact question text>",
      "communication": <integer 0-10>,
      "justification": <integer 0-10>,
      "confidence_without_content": <true|false>,
      "scripted_sounding": <true|false>,
      "reasoning": "<short factual explanation>"
    }}
  ]
}}

IMPORTANT:
- End the response immediately after end of json
- Do NOT add explanations
- Do NOT add trailing text
"""


    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": "You are an HR evaluation engine."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.1,
        max_tokens=1500
    )

    content = response.choices[0].message.content.strip()

    parsed = safe_json_extract(content)

    if not parsed:
        print("❌ Groq JSON parse failed. Raw output:\n", content)
        return {"results": []}

    return parsed


def evaluate_full_interview_from_conversation(conversation):
    print("\n========== FULL CONVERSATION ==========")
    for turn in conversation:
        role = turn.get("role", "").upper()
        text = turn.get("text", "")
        print(f"{role}: {text}")
    print("=======================================\n")

    qa_pairs = []
    last_question = None

    for turn in conversation:
        if turn.get("role") == "ai" and turn.get("type") == "question":
            last_question = turn.get("text")

        elif (
            turn.get("role") == "candidate"
            and turn.get("type") == "answer"
            and last_question
        ):
            qa_pairs.append({
                "question": last_question,
                "answer": turn.get("text")
            })
            last_question = None

    if not qa_pairs:
        print("❌ No valid Q/A pairs found")
        return {
            "final_score": 0,
            "decision": "REJECT",
            "red_flags": ["No valid answers provided"],
            "hr_summary": "Candidate did not provide usable responses."
        }

    valid_items = []
    red_flags = []

    for idx, pair in enumerate(qa_pairs, start=1):
        check = local_invalid_check(pair["answer"])

        valid_items.append({
            "question": pair["question"],
            "answer": pair["answer"],
            "force_zero": not check["valid"]
        })

        if not check["valid"]:
            red_flags.append(
                f"Question {idx}: {check['reason']}"
            )

    groq_result = groq_score_full_interview(valid_items)
    results = groq_result.get("results", [])

    total_score = 0.0
    max_possible = 0.0
    per_question_notes = []

    for idx, item in enumerate(valid_items):
        if item["force_zero"]:
            comm, just = 0.0, 0.0

        elif idx >= len(results):
            # fallback: partial credit
            comm, just = 4.0, 4.0
            reasoning = "Scoring fallback due to incomplete model response"
        else:
            r = results[idx]
            comm = float(r.get("communication", 0))
            just = float(r.get("justification", 0))
            reasoning = r.get("reasoning", "")

            # Real-world sanity enforcement
            comm, just = enforce_real_world_floors(
                item["answer"], comm, just
            )

            # Optional: experience bonus
            comm, just = apply_experience_bonus(
                item, comm, just
            )

        per_question_notes.append({
            "question": item["question"],
            "answer": item["answer"],
            "communication": comm,
            "justification": just,
            "reasoning": reasoning
        })

        total_score += comm + just
        max_possible += 20  # 10 comm + 10 justification

    final_score = round((total_score / max(max_possible, 1)) * 100)

    decision = (
        "STRONG HIRE" if final_score >= 70 else
        "CONSIDER" if final_score >= 55 else
        "LESS CONSIDER" if final_score >= 40 else
        "REJECT"
    )

    hr_summary = build_hr_summary(
        final_score,
        decision,
        red_flags,
        per_question_notes
    )

    print(f"✅ FINAL SCORE: {final_score}")
    print(f"📌 DECISION: {decision}")

    return {
        "final_score": final_score,
        "decision": decision,
        "red_flags": red_flags,
        "hr_summary": hr_summary
    }
