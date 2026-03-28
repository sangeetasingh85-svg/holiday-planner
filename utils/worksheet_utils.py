import json
import random
from pathlib import Path

WORKSHEETS_PATH = Path(__file__).parent.parent / "data" / "worksheets.json"

TOPIC_LABELS = {
    "pronouns": "Pronouns",
    "contractions": "Contractions",
    "homophones": "Homophones",
    "interjections": "Interjections",
    "suffix_prefix": "Suffix & Prefix",
    "vocabulary": "Vocabulary",
    "research_writing": "Reading & Writing",
    "division_equal_groups": "Division – Equal Groups",
    "division_repeated_subtraction": "Division – Repeated Subtraction",
    "division_number_line": "Division – Number Line",
    "division_fact_families": "Division – Fact Families",
    "division_word_problems": "Division – Word Problems",
    "measurement_length": "Measurement – Length",
    "measurement_mass": "Measurement – Mass",
    "measurement_capacity": "Measurement – Capacity",
}

LITERACY_TOPICS = ["pronouns", "contractions", "homophones", "interjections", "suffix_prefix", "vocabulary", "research_writing"]
NUMERACY_TOPICS = ["division_equal_groups", "division_repeated_subtraction", "division_number_line",
                   "division_fact_families", "division_word_problems", "measurement_length",
                   "measurement_mass", "measurement_capacity"]


def load_worksheets():
    with open(WORKSHEETS_PATH) as f:
        return json.load(f)


def get_all_worksheets_flat(selected_topics=None):
    data = load_worksheets()
    flat = {}
    for subject in ["literacy", "numeracy"]:
        for topic, sheets in data[subject].items():
            if selected_topics is None or topic in selected_topics:
                flat[topic] = sheets
    return flat


def get_worksheets_for_topic(topic, exclude_ids=None):
    data = load_worksheets()
    subject = "literacy" if topic in LITERACY_TOPICS else "numeracy"
    sheets = data[subject].get(topic, [])
    if exclude_ids:
        sheets = [s for s in sheets if s["id"] not in exclude_ids]
    return sheets


def get_alternates_for_topic(topic, exclude_ids=None):
    return get_worksheets_for_topic(topic, exclude_ids=exclude_ids)


def build_day_plan(day_num, lit_topics_queue, num_topics_queue, used_ids, num_lit=3, num_num=2):
    worksheets = []
    used_this_plan = set(used_ids)

    # Assign literacy worksheets
    lit_assigned = 0
    lit_attempts = 0
    while lit_assigned < num_lit and lit_attempts < len(lit_topics_queue) * 2:
        topic = lit_topics_queue[lit_attempts % len(lit_topics_queue)]
        available = get_worksheets_for_topic(topic, exclude_ids=used_this_plan)
        if available:
            sheet = available[0]
            worksheets.append({
                "id": sheet["id"],
                "title": sheet["title"],
                "url": sheet["url"],
                "source": sheet["source"],
                "description": sheet["description"],
                "topic": topic,
                "topic_label": TOPIC_LABELS.get(topic, topic),
                "subject": "literacy",
                "is_speed_math": False
            })
            used_this_plan.add(sheet["id"])
            lit_assigned += 1
        lit_attempts += 1

    # Assign numeracy worksheets
    num_assigned = 0
    num_attempts = 0
    while num_assigned < num_num and num_attempts < len(num_topics_queue) * 2:
        topic = num_topics_queue[num_attempts % len(num_topics_queue)]
        available = get_worksheets_for_topic(topic, exclude_ids=used_this_plan)
        if available:
            sheet = available[0]
            worksheets.append({
                "id": sheet["id"],
                "title": sheet["title"],
                "url": sheet["url"],
                "source": sheet["source"],
                "description": sheet["description"],
                "topic": topic,
                "topic_label": TOPIC_LABELS.get(topic, topic),
                "subject": "numeracy",
                "is_speed_math": False
            })
            used_this_plan.add(sheet["id"])
            num_assigned += 1
        num_attempts += 1

    # Always add speed math sheet
    worksheets.append({
        "id": f"speed_math_day_{day_num}",
        "title": "Speed Math – Addition & Subtraction",
        "url": None,
        "source": "Generated",
        "description": "20 single-digit addition and subtraction problems (no negative answers)",
        "topic": "speed_math",
        "topic_label": "Speed Math",
        "subject": "numeracy",
        "is_speed_math": True
    })

    return worksheets, used_this_plan


def generate_plan(num_days, selected_lit_topics=None, selected_num_topics=None, global_used_ids=None):
    if selected_lit_topics is None:
        selected_lit_topics = LITERACY_TOPICS[:]
    if selected_num_topics is None:
        selected_num_topics = NUMERACY_TOPICS[:]
    if global_used_ids is None:
        global_used_ids = set()

    used_ids = set(global_used_ids)
    days = []

    # Rotate topics across days so each topic appears roughly evenly
    lit_queue = selected_lit_topics * ((num_days * 3 // len(selected_lit_topics)) + 2)
    num_queue = selected_num_topics * ((num_days * 2 // len(selected_num_topics)) + 2)

    # Shuffle to avoid always starting with the same topic
    random.shuffle(lit_queue)
    random.shuffle(num_queue)

    lit_idx = 0
    num_idx = 0

    for day_num in range(1, num_days + 1):
        day_lit = []
        day_num_topics = []

        # Pick 3 unique literacy topics for the day
        seen_lit = set()
        for i in range(lit_idx, lit_idx + len(lit_queue)):
            t = lit_queue[i % len(lit_queue)]
            if t not in seen_lit:
                day_lit.append(t)
                seen_lit.add(t)
            if len(day_lit) == 3:
                break
        lit_idx = (lit_idx + 3) % len(lit_queue)

        # Pick 2 unique numeracy topics for the day
        seen_num = set()
        for i in range(num_idx, num_idx + len(num_queue)):
            t = num_queue[i % len(num_queue)]
            if t not in seen_num:
                day_num_topics.append(t)
                seen_num.add(t)
            if len(day_num_topics) == 2:
                break
        num_idx = (num_idx + 2) % len(num_queue)

        worksheets, used_ids = build_day_plan(day_num, day_lit, day_num_topics, used_ids)
        days.append({
            "day": day_num,
            "worksheets": worksheets
        })

    return {"days": days}


def get_topic_summary(plan_data):
    topic_counts = {}
    for day in plan_data["days"]:
        for ws in day["worksheets"]:
            label = ws["topic_label"]
            topic_counts[label] = topic_counts.get(label, 0) + 1
    return topic_counts
