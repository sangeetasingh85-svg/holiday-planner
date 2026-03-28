import streamlit as st
from datetime import datetime
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from utils.db_utils import (
    init_db, save_plan, get_all_plans, get_plan, delete_plan,
    update_plan_data, get_all_used_worksheet_ids,
    save_course_file, get_all_course_files, get_course_file, delete_course_file
)
from utils.worksheet_utils import (
    generate_plan, get_topic_summary, get_alternates_for_topic,
    TOPIC_LABELS, LITERACY_TOPICS, NUMERACY_TOPICS
)
try:
    from utils.pdf_utils import build_day_pdf
except Exception as _pdf_err:
    def build_day_pdf(*a, **kw):
        raise RuntimeError(f"PDF library not available: {_pdf_err}")

# pdf_parser imports pypdf — import lazily to avoid crashing whole app on startup
def _get_pdf_parser():
    from utils.pdf_parser import detect_topics, summarise_detected
    return detect_topics, summarise_detected

APP_VERSION = "v1.3"

# ── Init ──────────────────────────────────────────────────────────────────────
init_db()

st.set_page_config(
    page_title="🐱 Holiday Learning Planner",
    page_icon="🐱",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .block-container { padding-top: 1.5rem; }
    h1 { color: #FF6B35; }
    .tag-literacy {
        background:#E8F5E9; color:#2E7D32; padding:2px 10px;
        border-radius:20px; font-size:0.78rem; font-weight:600; margin-right:4px;
    }
    .tag-numeracy {
        background:#E3F2FD; color:#1565C0; padding:2px 10px;
        border-radius:20px; font-size:0.78rem; font-weight:600; margin-right:4px;
    }
    .tag-speed {
        background:#FFF3E0; color:#E65100; padding:2px 10px;
        border-radius:20px; font-size:0.78rem; font-weight:600; margin-right:4px;
    }
    .ws-card {
        background:#FFFDF8; border:1.5px solid #FFB347;
        border-radius:10px; padding:10px 14px; margin:6px 0;
    }
    .plan-card {
        background:#FFF8F0; border:2px solid #FF6B35;
        border-radius:12px; padding:14px 18px; margin:8px 0;
    }
    div[data-testid="stSidebarNav"] { display:none; }
</style>
""", unsafe_allow_html=True)

# ── Session State ─────────────────────────────────────────────────────────────
if "page" not in st.session_state:
    st.session_state.page = "home"
if "view_plan_id" not in st.session_state:
    st.session_state.view_plan_id = None
if "replace_ctx" not in st.session_state:
    st.session_state.replace_ctx = None

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🐱 Holiday Planner")
    st.markdown("---")
    if st.button("🏠  Home", use_container_width=True):
        st.session_state.page = "home"
        st.rerun()
    if st.button("✨  New Plan", use_container_width=True):
        st.session_state.page = "new_plan"
        st.rerun()
    if st.button("📚  My Plans", use_container_width=True):
        st.session_state.page = "my_plans"
        st.rerun()
    st.markdown("---")
    st.markdown("<small>Grade 2 · Unit 5<br>Trio World Academy</small>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: HOME
# ══════════════════════════════════════════════════════════════════════════════
def page_home():
    st.markdown(f"# 🐱 Holiday Learning Planner <small style='font-size:0.4em;color:#aaa'>{APP_VERSION}</small>", unsafe_allow_html=True)
    st.markdown("#### Personalised daily practice sheets for your Grade 2 star ⭐")
    st.markdown("---")

    plans = get_all_plans()
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Plans Created", len(plans))
    with col2:
        total_days = sum(p["num_days"] for p in plans)
        st.metric("Total Days Planned", total_days)
    with col3:
        st.metric("Worksheets Tracked", len(get_all_used_worksheet_ids()))

    st.markdown("---")
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("### 🐾 What this planner does")
        st.markdown("""
- Builds a day-by-day holiday practice plan
- **Half literacy, half numeracy** every day
- Finds printable Grade 2 worksheets automatically
- Generates a **speed math sheet** each day (20 problems)
- Downloads and stitches all sheets into **one PDF per day**
- Remembers worksheets used so nothing repeats
- Saves all plans so you can revisit them anytime
        """)
    with col_b:
        st.markdown("### 📚 Unit 5 Topics covered")
        st.markdown("**Literacy**")
        for t in LITERACY_TOPICS:
            st.markdown(f"  • {TOPIC_LABELS[t]}")
        st.markdown("**Numeracy**")
        for t in NUMERACY_TOPICS:
            st.markdown(f"  • {TOPIC_LABELS[t]}")

    st.markdown("---")
    if plans:
        st.markdown("### 🕐 Recent Plans")
        for p in plans[:3]:
            with st.container():
                c1, c2 = st.columns([4, 1])
                with c1:
                    st.markdown(f"**{p['name']}** — {p['holiday_name'] or 'Holiday'} · {p['num_days']} days")
                    st.caption(f"Created {p['created_at'][:10]}")
                with c2:
                    if st.button("View →", key=f"home_view_{p['id']}"):
                        st.session_state.view_plan_id = p["id"]
                        st.session_state.page = "view_plan"
                        st.rerun()
    else:
        st.info("No plans yet! Click **✨ New Plan** in the sidebar to get started.")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: NEW PLAN  (3-step flow)
# ══════════════════════════════════════════════════════════════════════════════
def page_new_plan():
    st.markdown("# ✨ Create a New Holiday Plan")
    st.markdown("---")

    # Step state
    if "np_step" not in st.session_state:
        st.session_state.np_step = 1
    if "np_course_file_id" not in st.session_state:
        st.session_state.np_course_file_id = None
    if "np_detected" not in st.session_state:
        st.session_state.np_detected = {}

    step = st.session_state.np_step

    # ── Step indicator ────────────────────────────────────────────────────────
    cols = st.columns(3)
    for i, label in enumerate(["1. Course File", "2. Topics", "3. Plan Details"], 1):
        with cols[i - 1]:
            if i == step:
                st.markdown(f"**🔵 {label}**")
            elif i < step:
                st.markdown(f"✅ {label}")
            else:
                st.markdown(f"⬜ {label}")
    st.markdown("---")

    # ══ STEP 1: Course File ═══════════════════════════════════════════════════
    if step == 1:
        st.markdown("### 📂 Step 1 – Choose a Course File")
        st.markdown("Upload your school's unit PDF so the app can detect topics, "
                    "or pick one you've uploaded before.")

        existing = get_all_course_files()
        tab_new, tab_existing = st.tabs(["⬆️ Upload new PDF", "📚 Use a previous file"])

        with tab_new:
            uploaded = st.file_uploader(
                "Upload course PDF (Literacy or Numeracy booklet)",
                type=["pdf"], key="course_upload"
            )
            file_label = st.text_input(
                "Give this file a name",
                placeholder="e.g. Unit 5 – Literacy (2025)",
                key="course_label"
            )
            if st.button("Analyse PDF →", disabled=uploaded is None, use_container_width=True):
                if not file_label:
                    st.error("Please give the file a name first.")
                else:
                    with st.spinner("🐾 Reading PDF and detecting topics…"):
                        pdf_bytes = uploaded.read()
                        detect_topics, _ = _get_pdf_parser()
                        detected, _ = detect_topics(pdf_bytes)
                        file_id = save_course_file(
                            file_label, uploaded.name, pdf_bytes, detected
                        )
                    st.session_state.np_course_file_id = file_id
                    st.session_state.np_detected = detected
                    st.session_state.np_step = 2
                    st.rerun()

        with tab_existing:
            if not existing:
                st.info("No course files uploaded yet. Upload one in the tab above.")
            else:
                for cf in existing:
                    c1, c2 = st.columns([4, 1])
                    with c1:
                        st.markdown(f"**{cf['name']}**")
                        st.caption(f"Uploaded {cf['uploaded_at'][:10]}  ·  {cf['filename']}")
                    with c2:
                        if st.button("Use →", key=f"use_cf_{cf['id']}"):
                            full = get_course_file(cf["id"])
                            st.session_state.np_course_file_id = cf["id"]
                            st.session_state.np_detected = full["detected_topics"]
                            st.session_state.np_step = 2
                            st.rerun()

    # ══ STEP 2: Topics ════════════════════════════════════════════════════════
    elif step == 2:
        st.markdown("### 📋 Step 2 – Confirm Topics")
        st.markdown("Topics detected from your PDF are pre-ticked. "
                    "Tick or untick to customise what's covered.")

        detected = st.session_state.np_detected
        _, summarise_detected = _get_pdf_parser()
        topic_list = summarise_detected(detected, TOPIC_LABELS)

        lit_topics = [(k, l, d) for k, l, d in topic_list if k in LITERACY_TOPICS]
        num_topics = [(k, l, d) for k, l, d in topic_list if k in NUMERACY_TOPICS]

        col_lit, col_num = st.columns(2)
        selected_lit, selected_num = [], []

        with col_lit:
            st.markdown("#### 📗 Literacy")
            for key, label, det in lit_topics:
                icon = "🟢" if det else "⚪"
                if st.checkbox(f"{icon} {label}", value=det, key=f"s2_lit_{key}"):
                    selected_lit.append(key)

        with col_num:
            st.markdown("#### 📘 Numeracy")
            for key, label, det in num_topics:
                icon = "🟢" if det else "⚪"
                if st.checkbox(f"{icon} {label}", value=det, key=f"s2_num_{key}"):
                    selected_num.append(key)

        st.info("⚡ **Speed Math** (20 single-digit addition & subtraction problems) "
                "is included every day automatically.")

        c1, c2 = st.columns(2)
        with c1:
            if st.button("← Back", use_container_width=True):
                st.session_state.np_step = 1
                st.rerun()
        with c2:
            if st.button("Next →", use_container_width=True):
                if not selected_lit:
                    st.error("Select at least one literacy topic.")
                elif not selected_num:
                    st.error("Select at least one numeracy topic.")
                else:
                    st.session_state.np_selected_lit = selected_lit
                    st.session_state.np_selected_num = selected_num
                    st.session_state.np_step = 3
                    st.rerun()

    # ══ STEP 3: Plan Details ══════════════════════════════════════════════════
    elif step == 3:
        st.markdown("### 📝 Step 3 – Plan Details")

        col1, col2 = st.columns(2)
        with col1:
            plan_name = st.text_input("Plan name", placeholder="e.g. Easter Break 2025")
            holiday_name = st.text_input("Holiday name (optional)", placeholder="e.g. Easter Holidays")
        with col2:
            num_days = st.number_input("Number of holiday days", min_value=1, max_value=30, value=5)
            avoid_repeats = st.checkbox(
                "Avoid worksheets used in previous plans", value=True,
                help="The planner won't reuse worksheets from your older holiday plans."
            )

        # Preview selected topics
        with st.expander("📋 Topics selected (from Step 2)"):
            sc1, sc2 = st.columns(2)
            with sc1:
                st.markdown("**Literacy**")
                for t in st.session_state.get("np_selected_lit", []):
                    st.markdown(f"  • {TOPIC_LABELS.get(t, t)}")
            with sc2:
                st.markdown("**Numeracy**")
                for t in st.session_state.get("np_selected_num", []):
                    st.markdown(f"  • {TOPIC_LABELS.get(t, t)}")

        c1, c2 = st.columns(2)
        with c1:
            if st.button("← Back", use_container_width=True):
                st.session_state.np_step = 2
                st.rerun()
        with c2:
            if st.button("🐱 Generate Plan", use_container_width=True, type="primary"):
                if not plan_name:
                    st.error("Please enter a plan name.")
                else:
                    selected_lit = st.session_state.get("np_selected_lit", [])
                    selected_num = st.session_state.get("np_selected_num", [])
                    with st.spinner("🐾 Building your plan… finding worksheets…"):
                        global_used = get_all_used_worksheet_ids() if avoid_repeats else set()
                        plan_data = generate_plan(num_days, selected_lit, selected_num, global_used)
                        plan_id = save_plan(
                            plan_name, holiday_name, num_days, plan_data,
                            course_file_id=st.session_state.np_course_file_id
                        )
                    # Reset step state
                    for k in ["np_step", "np_course_file_id", "np_detected",
                              "np_selected_lit", "np_selected_num"]:
                        st.session_state.pop(k, None)
                    st.success(f"✅ Plan '{plan_name}' created for {num_days} days!")
                    st.session_state.view_plan_id = plan_id
                    st.session_state.page = "view_plan"
                    st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: MY PLANS
# ══════════════════════════════════════════════════════════════════════════════
def page_my_plans():
    st.markdown("# 📚 My Plans & Course Files")
    st.markdown("---")

    tab_plans, tab_files = st.tabs(["📅 Holiday Plans", "📂 Course File Library"])

    with tab_plans:
        plans = get_all_plans()
        if not plans:
            st.info("No plans yet. Click **✨ New Plan** to create your first one!")
        else:
            for p in plans:
                with st.container():
                    st.markdown(f"""<div class="plan-card">
                        <b>{p['name']}</b> &nbsp;·&nbsp; {p['holiday_name'] or 'Holiday'} &nbsp;·&nbsp;
                        {p['num_days']} days &nbsp;·&nbsp; <i>Created {p['created_at'][:10]}</i>
                    </div>""", unsafe_allow_html=True)
                    c1, c2 = st.columns([1, 5])
                    with c1:
                        if st.button("View", key=f"view_{p['id']}"):
                            st.session_state.view_plan_id = p["id"]
                            st.session_state.page = "view_plan"
                            st.rerun()
                    with c2:
                        if st.button("🗑️ Delete", key=f"del_{p['id']}"):
                            delete_plan(p["id"])
                            st.success("Plan deleted.")
                            st.rerun()

    with tab_files:
        st.markdown("#### Uploaded course PDFs")
        st.markdown("These are available to reuse when creating future plans.")
        files = get_all_course_files()
        if not files:
            st.info("No course files uploaded yet. Upload one when creating a new plan.")
        else:
            for cf in files:
                with st.container():
                    c1, c2 = st.columns([5, 1])
                    with c1:
                        st.markdown(f"**{cf['name']}**")
                        st.caption(f"File: {cf['filename']}  ·  Uploaded {cf['uploaded_at'][:10]}")
                    with c2:
                        if st.button("🗑️", key=f"del_cf_{cf['id']}", help="Delete this file"):
                            delete_course_file(cf["id"])
                            st.success("File deleted.")
                            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: VIEW PLAN
# ══════════════════════════════════════════════════════════════════════════════
def page_view_plan():
    plan_id = st.session_state.view_plan_id
    plan = get_plan(plan_id)
    if not plan:
        st.error("Plan not found.")
        return

    plan_data = plan["plan_data"]

    st.markdown(f"# 🐱 {plan['name']}")
    course_label = ""
    if plan.get("course_file_id"):
        cf = get_course_file(plan["course_file_id"])
        if cf:
            course_label = f" · 📂 {cf['name']}"
    st.markdown(f"**{plan['holiday_name'] or 'Holiday'}** · {plan['num_days']} days · "
                f"Created {plan['created_at'][:10]}{course_label}")
    st.markdown("---")

    # ── Summary ───────────────────────────────────────────────────────────────
    with st.expander("📊 Topic Coverage Summary", expanded=True):
        topic_counts = get_topic_summary(plan_data)
        total = sum(topic_counts.values())
        cols = st.columns(3)
        for i, (topic, count) in enumerate(sorted(topic_counts.items())):
            with cols[i % 3]:
                st.markdown(f"**{topic}**")
                st.progress(count / max(topic_counts.values()))
                st.caption(f"{count} sheet{'s' if count > 1 else ''}")

        # Day-wise mini calendar
        st.markdown("#### 📅 Day-by-day at a glance")
        header = [""] + [f"Day {d['day']}" for d in plan_data["days"]]
        lit_row = ["📗 Literacy"]
        num_row = ["📘 Numeracy"]
        for day in plan_data["days"]:
            lit_topics = list({w["topic_label"] for w in day["worksheets"] if w["subject"] == "literacy"})
            num_topics = list({w["topic_label"] for w in day["worksheets"] if w["subject"] == "numeracy" and not w.get("is_speed_math")})
            lit_row.append("\n".join(lit_topics))
            num_row.append("\n".join(num_topics) + "\n⚡ Speed Math")

        import pandas as pd
        df = pd.DataFrame([lit_row, num_row], columns=header)
        st.dataframe(df, use_container_width=True, hide_index=True)

    st.markdown("---")

    # ── Day Tabs ──────────────────────────────────────────────────────────────
    tabs = st.tabs([f"Day {d['day']}" for d in plan_data["days"]])

    for tab, day in zip(tabs, plan_data["days"]):
        with tab:
            day_num = day["day"]
            worksheets = day["worksheets"]

            lit_ws = [w for w in worksheets if w["subject"] == "literacy"]
            num_ws = [w for w in worksheets if w["subject"] == "numeracy" and not w.get("is_speed_math")]
            speed_ws = [w for w in worksheets if w.get("is_speed_math")]

            col_left, col_right = st.columns(2)

            with col_left:
                st.markdown("#### 📗 Literacy")
                for ws in lit_ws:
                    render_worksheet_card(ws, plan_id, plan_data, day_num)

            with col_right:
                st.markdown("#### 📘 Numeracy")
                for ws in num_ws:
                    render_worksheet_card(ws, plan_id, plan_data, day_num)
                for ws in speed_ws:
                    st.markdown(f"""<div class="ws-card">
                        <span class="tag-speed">⚡ Speed Math</span><br>
                        <b>{ws['title']}</b><br>
                        <small style="color:#777">{ws['description']}</small><br>
                        <small style="color:#aaa">Generated automatically</small>
                    </div>""", unsafe_allow_html=True)

            st.markdown("---")

            # ── Download PDF ──────────────────────────────────────────────────
            if st.button(f"⬇️ Download Day {day_num} PDF", key=f"dl_{plan_id}_{day_num}", use_container_width=True):
                with st.spinner(f"🐾 Building Day {day_num} PDF… downloading worksheets…"):
                    pdf_buf, failed = build_day_pdf(day_num, worksheets)

                st.download_button(
                    label=f"📄 Click to save Day {day_num}.pdf",
                    data=pdf_buf,
                    file_name=f"{plan['name'].replace(' ', '_')}_Day_{day_num}.pdf",
                    mime="application/pdf",
                    key=f"save_{plan_id}_{day_num}"
                )
                if failed:
                    st.warning(
                        f"⚠️ {len(failed)} worksheet(s) could not be auto-downloaded and are included as link pages. "
                        "You can open those links manually in your browser."
                    )
                else:
                    st.success("✅ All worksheets downloaded and stitched successfully!")


def render_worksheet_card(ws, plan_id, plan_data, day_num):
    subj_class = "tag-literacy" if ws["subject"] == "literacy" else "tag-numeracy"
    subj_label = "📗 Literacy" if ws["subject"] == "literacy" else "📘 Numeracy"
    source = ws.get("source", "")
    url = ws.get("url", "")
    link_html = f'<a href="{url}" target="_blank" style="font-size:0.8rem;color:#FF6B35">🔗 Preview</a>' if url else ""

    st.markdown(f"""<div class="ws-card">
        <span class="{subj_class}">{ws['topic_label']}</span> {link_html}<br>
        <b style="font-size:0.95rem">{ws['title']}</b><br>
        <small style="color:#777">{ws['description']}</small><br>
        <small style="color:#bbb">Source: {source}</small>
    </div>""", unsafe_allow_html=True)

    if st.button("🔄 Replace this sheet", key=f"replace_{ws['id']}_{day_num}"):
        st.session_state.replace_ctx = {
            "plan_id": plan_id,
            "day_num": day_num,
            "worksheet_id": ws["id"],
            "topic": ws["topic"]
        }
        st.session_state.page = "replace_sheet"
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: REPLACE SHEET
# ══════════════════════════════════════════════════════════════════════════════
def page_replace_sheet():
    ctx = st.session_state.replace_ctx
    if not ctx:
        st.session_state.page = "view_plan"
        st.rerun()

    plan_id = ctx["plan_id"]
    day_num = ctx["day_num"]
    old_ws_id = ctx["worksheet_id"]
    topic = ctx["topic"]

    plan = get_plan(plan_id)
    plan_data = plan["plan_data"]

    # Collect all worksheet IDs used in this plan except the one being replaced
    all_used = {
        w["id"] for day in plan_data["days"]
        for w in day["worksheets"]
        if w.get("id") and w["id"] != old_ws_id
    }

    alternatives = get_alternates_for_topic(topic, exclude_ids=all_used)

    st.markdown(f"# 🔄 Replace Worksheet")
    st.markdown(f"**Plan:** {plan['name']} · **Day {day_num}** · Topic: {TOPIC_LABELS.get(topic, topic)}")
    st.markdown("---")

    if not alternatives:
        st.warning("No alternative worksheets available for this topic that haven't been used already.")
        if st.button("← Back"):
            st.session_state.page = "view_plan"
            st.rerun()
        return

    st.markdown("#### Choose a replacement:")
    for ws in alternatives:
        with st.container():
            c1, c2 = st.columns([4, 1])
            with c1:
                st.markdown(f"**{ws['title']}**")
                st.caption(f"{ws['description']} · Source: {ws['source']}")
                if ws.get("url"):
                    st.markdown(f"[🔗 Preview]({ws['url']})")
            with c2:
                if st.button("Use this", key=f"use_{ws['id']}"):
                    # Swap in plan_data
                    for day in plan_data["days"]:
                        if day["day"] == day_num:
                            for i, w in enumerate(day["worksheets"]):
                                if w.get("id") == old_ws_id:
                                    day["worksheets"][i] = {
                                        "id": ws["id"],
                                        "title": ws["title"],
                                        "url": ws["url"],
                                        "source": ws["source"],
                                        "description": ws["description"],
                                        "topic": topic,
                                        "topic_label": TOPIC_LABELS.get(topic, topic),
                                        "subject": "literacy" if topic in LITERACY_TOPICS else "numeracy",
                                        "is_speed_math": False
                                    }
                    update_plan_data(plan_id, plan_data)
                    st.session_state.replace_ctx = None
                    st.session_state.page = "view_plan"
                    st.success("Worksheet replaced!")
                    st.rerun()

    if st.button("← Cancel, go back"):
        st.session_state.replace_ctx = None
        st.session_state.page = "view_plan"
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# ROUTER
# ══════════════════════════════════════════════════════════════════════════════
page = st.session_state.page

if page == "home":
    page_home()
elif page == "new_plan":
    page_new_plan()
elif page == "my_plans":
    page_my_plans()
elif page == "view_plan":
    page_view_plan()
elif page == "replace_sheet":
    page_replace_sheet()
