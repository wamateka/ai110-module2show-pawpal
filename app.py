import streamlit as st
from datetime import date
import pawpal_system as ps

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

# ---------------------------------------------------------------------------
# Service initialisation — stored in session_state so they (and their
# class-level data dicts) survive across Streamlit reruns.
# ---------------------------------------------------------------------------
if "user_service" not in st.session_state:
    st.session_state.user_service = ps.UserService()
if "pet_service" not in st.session_state:
    st.session_state.pet_service = ps.PetService()
if "care_target_service" not in st.session_state:
    st.session_state.care_target_service = ps.CareTargetService()
if "activity_service" not in st.session_state:
    st.session_state.activity_service = ps.ActivityService()
if "care_score_service" not in st.session_state:
    st.session_state.care_score_service = ps.CareScoreService(
        st.session_state.activity_service,
        st.session_state.care_target_service,
    )
if "current_user" not in st.session_state:
    st.session_state.current_user = None
if "selected_pet_id" not in st.session_state:
    st.session_state.selected_pet_id = None

us   = st.session_state.user_service
ps_  = st.session_state.pet_service
cts  = st.session_state.care_target_service
acts = st.session_state.activity_service
css  = st.session_state.care_score_service

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.title("🐾 PawPal+")

# ---------------------------------------------------------------------------
# Auth — shown when no user is logged in
# ---------------------------------------------------------------------------
if st.session_state.current_user is None:
    tab_login, tab_register = st.tabs(["Login", "Register"])

    with tab_register:
        st.subheader("Create Account")
        reg_name     = st.text_input("Name",     key="reg_name")
        reg_email    = st.text_input("Email",    key="reg_email")
        reg_password = st.text_input("Password", key="reg_password", type="password")
        if st.button("Register"):
            if not reg_name or not reg_email or not reg_password:
                st.error("All fields are required.")
            else:
                try:
                    user = us.register(reg_name, reg_email, reg_password)
                    st.session_state.current_user = user
                    st.success(f"Welcome, {user.name}!")
                    st.rerun()
                except ValueError as e:
                    st.error(str(e))

    with tab_login:
        st.subheader("Login")
        login_email    = st.text_input("Email",    key="login_email")
        login_password = st.text_input("Password", key="login_password", type="password")
        if st.button("Login"):
            try:
                user = us.login(login_email, login_password)
                st.session_state.current_user = user
                st.success(f"Welcome back, {user.name}!")
                st.rerun()
            except ValueError as e:
                st.error(str(e))

    st.stop()

# ---------------------------------------------------------------------------
# Logged-in header
# ---------------------------------------------------------------------------
user = st.session_state.current_user
col_user, col_logout = st.columns([5, 1])
with col_user:
    st.markdown(f"**{user.name}** &nbsp;·&nbsp; {user.email}")
with col_logout:
    if st.button("Logout"):
        st.session_state.current_user   = None
        st.session_state.selected_pet_id = None
        st.rerun()

st.divider()

# ---------------------------------------------------------------------------
# Pet list + add
# ---------------------------------------------------------------------------
st.subheader("My Pets")

pets = us.get_pets(user.id)

if pets:
    pet_names = {p.name: p.id for p in pets}
    chosen_name = st.selectbox("Select a pet", list(pet_names.keys()), key="pet_selector")
    st.session_state.selected_pet_id = pet_names[chosen_name]
else:
    st.info("No pets yet — add one below.")

with st.expander("➕ Add New Pet"):
    np_name    = st.text_input("Pet name",       key="np_name")
    np_species = st.selectbox("Species", ["dog", "cat", "other"], key="np_species")
    np_breed   = st.text_input("Breed (optional)",      key="np_breed")
    np_weight  = st.number_input("Weight (kg)",  min_value=0.0, step=0.1, key="np_weight")
    np_age     = st.number_input("Age (years)",  min_value=0,   step=1,   key="np_age")
    if st.button("Add Pet"):
        if not np_name:
            st.error("Pet name is required.")
        else:
            pet = ps_.create(
                user_id=user.id,
                name=np_name,
                species=np_species,
                breed=np_breed   or None,
                weight_kg=np_weight if np_weight > 0 else None,
                age_years=int(np_age) if np_age > 0 else None,
            )
            st.session_state.selected_pet_id = pet.id
            st.success(f"Added **{pet.name}**!")
            st.rerun()

# ---------------------------------------------------------------------------
# Pet detail — only shown when a pet is selected
# ---------------------------------------------------------------------------
if not st.session_state.selected_pet_id:
    st.stop()

pet_id = st.session_state.selected_pet_id
try:
    pet = ps_.get_profile(pet_id)
except ValueError:
    st.session_state.selected_pet_id = None
    st.rerun()

st.divider()
st.subheader(f"🐾 {pet.name}")

tab_profile, tab_targets, tab_activities, tab_score = st.tabs(
    ["Profile", "Care Targets", "Log Activity", "Care Score"]
)

# ── Profile ────────────────────────────────────────────────────────────────
with tab_profile:
    st.markdown(
        f"**Species:** {pet.species} &nbsp;|&nbsp; "
        f"**Breed:** {pet.breed or '—'} &nbsp;|&nbsp; "
        f"**Weight:** {f'{pet.weight_kg} kg' if pet.weight_kg else '—'} &nbsp;|&nbsp; "
        f"**Age:** {f'{pet.age_years} yr' if pet.age_years else '—'}"
    )

    with st.expander("Edit Profile"):
        species_opts = ["dog", "cat", "other"]
        upd_name    = st.text_input("Name",    value=pet.name,                                    key="upd_name")
        upd_species = st.selectbox("Species",  species_opts,
                                   index=species_opts.index(pet.species) if pet.species in species_opts else 2,
                                   key="upd_species")
        upd_breed   = st.text_input("Breed",   value=pet.breed   or "",                           key="upd_breed")
        upd_weight  = st.number_input("Weight (kg)",  min_value=0.0, step=0.1,
                                      value=float(pet.weight_kg or 0.0),                          key="upd_weight")
        upd_age     = st.number_input("Age (years)",  min_value=0,   step=1,
                                      value=int(pet.age_years or 0),                              key="upd_age")
        if st.button("Save Changes"):
            ps_.update(
                pet_id,
                name=upd_name,
                species=upd_species,
                breed=upd_breed  or None,
                weight_kg=upd_weight if upd_weight > 0 else None,
                age_years=int(upd_age) if upd_age > 0 else None,
            )
            st.success("Profile updated!")
            st.rerun()

    st.markdown("---")
    if st.button("🗑 Delete this pet", type="secondary"):
        ps_.delete(pet_id)
        st.session_state.selected_pet_id = None
        st.success(f"{pet.name} deleted.")
        st.rerun()

# ── Care Targets ───────────────────────────────────────────────────────────
with tab_targets:
    try:
        targets = cts.get_targets(pet_id)
        st.markdown(
            f"**Current targets** &nbsp;·&nbsp; Status: `{targets.status}`  \n"
            f"Meals/day: **{targets.daily_meals}** &nbsp;|&nbsp; "
            f"Walk: **{targets.daily_walk_min} min/day** &nbsp;|&nbsp; "
            f"Grooming every **{targets.grooming_interval_days} days** &nbsp;|&nbsp; "
            f"Vet every **{targets.vet_interval_days} days**"
        )
        if targets.status != "achieved":
            if st.button("Mark as Achieved"):
                cts.mark_achieved(pet_id)
                st.success("Targets marked as achieved!")
                st.rerun()
    except ValueError:
        targets = None
        st.info("No care targets set yet.")

    st.markdown("#### Set / Update Targets")
    tgt_meals  = st.number_input("Daily meals",               min_value=1, step=1,
                                  value=targets.daily_meals               if targets else 2, key="tgt_meals")
    tgt_walk   = st.number_input("Daily walk (minutes)",      min_value=0, step=5,
                                  value=targets.daily_walk_min            if targets else 30, key="tgt_walk")
    tgt_groom  = st.number_input("Grooming interval (days)",  min_value=1, step=1,
                                  value=targets.grooming_interval_days    if targets else 14, key="tgt_groom")
    tgt_vet    = st.number_input("Vet visit interval (days)", min_value=1, step=1,
                                  value=targets.vet_interval_days         if targets else 180, key="tgt_vet")
    if st.button("Save Targets"):
        cts.set_targets(pet_id, int(tgt_meals), int(tgt_walk), int(tgt_groom), int(tgt_vet))
        st.success("Care targets saved!")
        st.rerun()

# ── Log Activity ───────────────────────────────────────────────────────────
with tab_activities:
    st.markdown("#### Log an Activity")
    act_type = st.selectbox("Activity type",
                             ["feeding", "walk", "grooming", "vet_visit"], key="act_type")
    act_date = st.date_input("Date", value=date.today(), key="act_date")

    details: dict = {}
    if act_type == "walk":
        dur = st.number_input("Duration (minutes)", min_value=1, step=5, value=30, key="walk_dur")
        details["duration_min"] = int(dur)
    elif act_type == "feeding":
        notes = st.text_input("Food / notes (optional)", key="feed_notes")
        if notes:
            details["notes"] = notes
    elif act_type == "grooming":
        notes = st.text_input("Groomer / notes (optional)", key="groom_notes")
        if notes:
            details["notes"] = notes
    elif act_type == "vet_visit":
        notes = st.text_input("Reason / notes (optional)", key="vet_notes")
        if notes:
            details["notes"] = notes

    if st.button("Log Activity"):
        acts.log_activity(pet_id, act_type, details, act_date)
        st.success(f"{act_type.replace('_', ' ').title()} logged for {act_date}!")
        st.rerun()

    st.markdown("#### Today's Activities")
    today_acts = acts.get_by_date(pet_id, date.today())
    if today_acts:
        rows = [
            {
                "Type":    a.type.replace("_", " ").title(),
                "Date":    str(a.date),
                "Details": ", ".join(f"{k}: {v}" for k, v in a.details.items()) if a.details else "—",
            }
            for a in today_acts
        ]
        st.table(rows)
    else:
        st.info("No activities logged today.")

# ── Care Score ─────────────────────────────────────────────────────────────
with tab_score:
    score_date = st.date_input("Score date", value=date.today(), key="score_date")
    if st.button("Calculate Score"):
        try:
            score = css.calculate(pet_id, score_date)
            grade_colour = {"A": "green", "B": "blue", "C": "orange", "D": "red"}.get(score.grade, "grey")
            st.markdown(
                f"### Overall: **{score.overall_score}/100** &nbsp; "
                f"<span style='color:{grade_colour};font-size:1.4rem'>Grade {score.grade}</span>",
                unsafe_allow_html=True,
            )
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Feeding",   f"{score.feeding_pct}%")
            c2.metric("Exercise",  f"{score.exercise_pct}%")
            c3.metric("Grooming",  f"{score.grooming_pct}%")
            c4.metric("Vet",       f"{score.vet_pct}%")
        except ValueError as e:
            st.error(f"{e} — set care targets first.")

    st.markdown("#### Score History (last 30 days)")
    history = css.get_history(pet_id, 30)
    if history:
        chart_data = {str(s.date): s.overall_score for s in history}
        st.line_chart(chart_data)
        rows = [
            {
                "Date":     str(s.date),
                "Overall":  s.overall_score,
                "Grade":    s.grade,
                "Feeding":  f"{s.feeding_pct}%",
                "Exercise": f"{s.exercise_pct}%",
                "Grooming": f"{s.grooming_pct}%",
                "Vet":      f"{s.vet_pct}%",
            }
            for s in reversed(history)
        ]
        st.dataframe(rows, use_container_width=True)
    else:
        st.info("No score history yet. Calculate a score above to start tracking.")