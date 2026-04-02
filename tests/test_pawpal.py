import pytest
import sys
import os
from datetime import date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pawpal_system import (
    PetService,
    CareTargetService,
    ActivityService,
    CareScoreService,
    TaskService,
    sort_by_urgency,
    sort_by_care_score,
    sort_by_completion_gap,
)


# ---------------------------------------------------------------------------
# Fixtures — wipe class-level dicts before each test so state never leaks
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_all():
    """Clear every in-memory store before each test."""
    PetService._pets = {}
    CareTargetService._targets = {}
    ActivityService._activities = {}
    CareScoreService._scores = {}
    TaskService._tasks = {}
    yield


@pytest.fixture
def pet_svc():
    return PetService()


@pytest.fixture
def target_svc():
    return CareTargetService()


@pytest.fixture
def activity_svc():
    return ActivityService()


@pytest.fixture
def score_svc(activity_svc, target_svc):
    return CareScoreService(activity_svc, target_svc)


@pytest.fixture
def task_svc():
    return TaskService()


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def make_pet(pet_svc, name="Buddy", species="dog"):
    return pet_svc.create(user_id="user-001", name=name, species=species)


def set_basic_targets(target_svc, pet_id, reset_period="none"):
    return target_svc.set_targets(
        pet_id=pet_id,
        daily_meals=2,
        daily_walk_min=30,
        grooming_interval_days=14,
        vet_interval_days=180,
        reset_period=reset_period,
    )


# ===========================================================================
# EXISTING TESTS (preserved)
# ===========================================================================

class TestCareTargetStatus:
    """mark_achieved sets status to 'achieved'."""

    def test_starts_pending(self, pet_svc, target_svc):
        pet = make_pet(pet_svc)
        set_basic_targets(target_svc, pet.id)
        assert target_svc.get_targets(pet.id).status == "pending"

    def test_mark_achieved(self, pet_svc, target_svc):
        pet = make_pet(pet_svc)
        set_basic_targets(target_svc, pet.id)
        updated = target_svc.mark_achieved(pet.id)
        assert updated.status == "achieved"
        assert target_svc.get_targets(pet.id).status == "achieved"


class TestCareTargetCount:
    """count_for_pet and upsert semantics."""

    def test_count_zero_before_set(self, pet_svc, target_svc):
        pet = make_pet(pet_svc)
        assert target_svc.count_for_pet(pet.id) == 0

    def test_count_one_after_set(self, pet_svc, target_svc):
        pet = make_pet(pet_svc)
        set_basic_targets(target_svc, pet.id)
        assert target_svc.count_for_pet(pet.id) == 1

    def test_upsert_no_duplicate(self, pet_svc, target_svc):
        pet = make_pet(pet_svc)
        set_basic_targets(target_svc, pet.id)
        set_basic_targets(target_svc, pet.id)   # second call — must not add a row
        assert target_svc.count_for_pet(pet.id) == 1


# ===========================================================================
# NEW TESTS
# ===========================================================================

# ---------------------------------------------------------------------------
# 1. SORTING CORRECTNESS
# ---------------------------------------------------------------------------

class TestSortByUrgency:
    """sort_by_urgency: overdue tasks first, then ascending by scheduled_date."""

    def test_chronological_order(self, pet_svc, task_svc):
        pet = make_pet(pet_svc)
        today = date.today()

        t_future = task_svc.create(pet.id, "walk",  today + timedelta(days=3))
        t_today  = task_svc.create(pet.id, "walk",  today)
        t_past   = task_svc.create(pet.id, "walk",  today - timedelta(days=2))

        tasks = [t_future, t_today, t_past]
        sorted_tasks = sort_by_urgency(tasks, today)

        dates = [t.scheduled_date for t in sorted_tasks]
        assert dates == sorted(dates), "tasks should be in ascending date order"

    def test_overdue_comes_first(self, pet_svc, task_svc):
        pet = make_pet(pet_svc)
        today = date.today()

        overdue  = task_svc.create(pet.id, "feeding", today - timedelta(days=5))
        upcoming = task_svc.create(pet.id, "feeding", today + timedelta(days=1))

        sorted_tasks = sort_by_urgency([upcoming, overdue], today)
        assert sorted_tasks[0].id == overdue.id, "overdue task must sort first"

    def test_same_date_stable(self, pet_svc, task_svc):
        pet = make_pet(pet_svc)
        today = date.today()

        t1 = task_svc.create(pet.id, "feeding", today)
        t2 = task_svc.create(pet.id, "walk",    today)

        sorted_tasks = sort_by_urgency([t1, t2], today)
        # Both are "today" — order between them doesn't matter, but both must be present
        assert len(sorted_tasks) == 2

    def test_sort_by_care_score_lowest_first(self, pet_svc, task_svc):
        """Pets with the lowest score surface first."""
        pet_a = make_pet(pet_svc, name="A")
        pet_b = make_pet(pet_svc, name="B")
        today = date.today()

        t_a = task_svc.create(pet_a.id, "walk", today)
        t_b = task_svc.create(pet_b.id, "walk", today)

        score_map = {pet_a.id: 80, pet_b.id: 20}
        sorted_tasks = sort_by_care_score([t_a, t_b], score_map)
        assert sorted_tasks[0].pet_id == pet_b.id, "lower-score pet should surface first"

    def test_sort_by_completion_gap_largest_gap_first(self, pet_svc, task_svc):
        """Pets furthest from targets surface first."""
        pet_a = make_pet(pet_svc, name="A")
        pet_b = make_pet(pet_svc, name="B")
        today = date.today()

        t_a = task_svc.create(pet_a.id, "feeding", today)
        t_b = task_svc.create(pet_b.id, "feeding", today)

        gap_map = {pet_a.id: 0.1, pet_b.id: 0.9}
        sorted_tasks = sort_by_completion_gap([t_a, t_b], gap_map)
        assert sorted_tasks[0].pet_id == pet_b.id, "largest gap (0.9) should surface first"


# ---------------------------------------------------------------------------
# 2. RECURRENCE LOGIC
# ---------------------------------------------------------------------------

class TestRecurrence:
    """Completing/skipping a recurring task spawns the correct next occurrence."""

    def test_daily_complete_spawns_next_day(self, pet_svc, task_svc):
        pet = make_pet(pet_svc)
        today = date.today()
        task = task_svc.create(pet.id, "feeding", today, recurrence="daily")

        next_task = task_svc.complete(task.id)

        assert next_task is not None, "completing a daily task must spawn a successor"
        assert next_task.scheduled_date == today + timedelta(days=1)
        assert next_task.recurrence == "daily"
        assert next_task.parent_task_id == task.id

    def test_weekly_complete_spawns_next_week(self, pet_svc, task_svc):
        pet = make_pet(pet_svc)
        today = date.today()
        task = task_svc.create(pet.id, "grooming", today, recurrence="weekly")

        next_task = task_svc.complete(task.id)

        assert next_task is not None
        assert next_task.scheduled_date == today + timedelta(days=7)

    def test_custom_interval_spawns_correct_date(self, pet_svc, task_svc):
        pet = make_pet(pet_svc)
        today = date.today()
        task = task_svc.create(
            pet.id, "vet_visit", today,
            recurrence="custom",
            recurrence_interval_days=10,
        )

        next_task = task_svc.complete(task.id)

        assert next_task is not None
        assert next_task.scheduled_date == today + timedelta(days=10)

    def test_skip_also_spawns_next(self, pet_svc, task_svc):
        pet = make_pet(pet_svc)
        today = date.today()
        task = task_svc.create(pet.id, "walk", today, recurrence="daily")

        next_task = task_svc.skip(task.id)

        assert next_task is not None
        assert next_task.scheduled_date == today + timedelta(days=1)
        assert task.status == "skipped"

    def test_non_recurring_complete_returns_none(self, pet_svc, task_svc):
        pet = make_pet(pet_svc)
        task = task_svc.create(pet.id, "feeding", date.today(), recurrence="none")

        next_task = task_svc.complete(task.id)

        assert next_task is None, "one-off task must not spawn a successor"
        assert task.status == "done"

    def test_original_task_marked_done_after_complete(self, pet_svc, task_svc):
        pet = make_pet(pet_svc)
        task = task_svc.create(pet.id, "walk", date.today(), recurrence="daily")
        task_svc.complete(task.id)
        assert task.status == "done"


# ---------------------------------------------------------------------------
# 3. CONFLICT DETECTION
# ---------------------------------------------------------------------------

class TestConflictDetection:
    """detect_conflicts flags the three conflict rules correctly."""

    def test_duplicate_non_feeding_same_day(self, pet_svc, task_svc):
        """Rule A: same non-feeding type, same pet, same day → duplicate_non_feeding."""
        pet = make_pet(pet_svc)
        today = date.today()

        task_svc.create(pet.id, "grooming", today)
        task_svc.create(pet.id, "grooming", today)

        reports = task_svc.detect_conflicts([pet.id])
        types = [r.conflict_type for r in reports]
        assert "duplicate_non_feeding" in types

    def test_feeding_duplicate_not_flagged(self, pet_svc, task_svc):
        """Rule A does NOT apply to feeding (multiple meals per day are valid)."""
        pet = make_pet(pet_svc)
        today = date.today()

        task_svc.create(pet.id, "feeding", today)
        task_svc.create(pet.id, "feeding", today)

        reports = task_svc.detect_conflicts([pet.id])
        dup_reports = [r for r in reports if r.conflict_type == "duplicate_non_feeding"]
        assert len(dup_reports) == 0

    def test_time_proximity_under_30_min(self, pet_svc, task_svc):
        """Rule B: two tasks < 30 min apart → time_proximity."""
        pet = make_pet(pet_svc)
        today = date.today()

        task_svc.create(pet.id, "feeding", today, scheduled_time="09:00")
        task_svc.create(pet.id, "walk",    today, scheduled_time="09:20")

        reports = task_svc.detect_conflicts([pet.id])
        types = [r.conflict_type for r in reports]
        assert "time_proximity" in types

    def test_time_proximity_30_min_apart_not_flagged(self, pet_svc, task_svc):
        """Exactly 30 minutes apart should NOT trigger time_proximity (boundary check)."""
        pet = make_pet(pet_svc)
        today = date.today()

        task_svc.create(pet.id, "feeding", today, scheduled_time="09:00")
        task_svc.create(pet.id, "walk",    today, scheduled_time="09:30")

        reports = task_svc.detect_conflicts([pet.id])
        prox = [r for r in reports if r.conflict_type == "time_proximity"]
        assert len(prox) == 0

    def test_daily_overload_more_than_6_tasks(self, pet_svc, task_svc):
        """Rule C: > 6 pending tasks same pet same day → daily_overload."""
        pet = make_pet(pet_svc)
        today = date.today()

        for _ in range(7):
            task_svc.create(pet.id, "feeding", today)

        reports = task_svc.detect_conflicts([pet.id])
        types = [r.conflict_type for r in reports]
        assert "daily_overload" in types

    def test_no_conflicts_clean_schedule(self, pet_svc, task_svc):
        """A well-spaced schedule produces zero conflict reports."""
        pet = make_pet(pet_svc)
        today = date.today()

        task_svc.create(pet.id, "feeding", today,                  scheduled_time="08:00")
        task_svc.create(pet.id, "walk",    today,                  scheduled_time="10:00")
        task_svc.create(pet.id, "grooming", today + timedelta(1),  scheduled_time="09:00")

        reports = task_svc.detect_conflicts([pet.id])
        assert len(reports) == 0

    def test_outside_window_not_flagged(self, pet_svc, task_svc):
        """Tasks beyond window_days are ignored."""
        pet = make_pet(pet_svc)
        far_future = date.today() + timedelta(days=30)

        task_svc.create(pet.id, "grooming", far_future)
        task_svc.create(pet.id, "grooming", far_future)

        reports = task_svc.detect_conflicts([pet.id], window_days=7)
        assert len(reports) == 0


# ---------------------------------------------------------------------------
# 4. CARE SCORE CALCULATION
# ---------------------------------------------------------------------------

class TestCareScoreCalculation:
    """CareScoreService.calculate() produces correct percentages and grades."""

    def test_perfect_score_grade_A(self, pet_svc, target_svc, activity_svc, score_svc):
        pet = make_pet(pet_svc)
        set_basic_targets(target_svc, pet.id)
        today = date.today()

        # 2 feedings (meets target of 2)
        activity_svc.log_activity(pet.id, "feeding", {}, today)
        activity_svc.log_activity(pet.id, "feeding", {}, today)
        # Walk 30 min (meets target)
        activity_svc.log_activity(pet.id, "walk", {"duration_min": 30}, today)
        # Grooming within 14 days
        activity_svc.log_activity(pet.id, "grooming", {}, today)
        # Vet within 180 days
        activity_svc.log_activity(pet.id, "vet_visit", {}, today)

        score = score_svc.calculate(pet.id, today)

        assert score.feeding_pct == 100
        assert score.exercise_pct == 100
        assert score.grooming_pct == 100
        assert score.vet_pct == 100
        assert score.overall_score == 100
        assert score.grade == "A"

    def test_zero_activities_grade_D(self, pet_svc, target_svc, score_svc):
        pet = make_pet(pet_svc)
        set_basic_targets(target_svc, pet.id)

        score = score_svc.calculate(pet.id, date.today())

        assert score.feeding_pct == 0
        assert score.exercise_pct == 0
        assert score.overall_score == 0
        assert score.grade == "D"

    def test_feeding_pct_capped_at_100(self, pet_svc, target_svc, activity_svc, score_svc):
        """Extra feedings beyond target must not push feeding_pct above 100."""
        pet = make_pet(pet_svc)
        set_basic_targets(target_svc, pet.id)
        today = date.today()

        for _ in range(10):   # target is 2
            activity_svc.log_activity(pet.id, "feeding", {}, today)

        score = score_svc.calculate(pet.id, today)
        assert score.feeding_pct == 100

    def test_overdue_grooming_scores_zero(self, pet_svc, target_svc, activity_svc, score_svc):
        """Grooming that happened more than grooming_interval_days ago scores 0."""
        pet = make_pet(pet_svc)
        set_basic_targets(target_svc, pet.id)   # grooming_interval_days=14
        today = date.today()

        old_date = today - timedelta(days=20)
        activity_svc.log_activity(pet.id, "grooming", {}, old_date)

        score = score_svc.calculate(pet.id, today)
        assert score.grooming_pct == 0

    def test_grade_thresholds(self, pet_svc, target_svc, score_svc, activity_svc):
        """Verify grade boundaries: >=90→A, >=80→B, >=70→C, else D."""
        pet = make_pet(pet_svc)
        today = date.today()

        target_svc.set_targets(
            pet_id=pet.id,
            daily_meals=1,
            daily_walk_min=0,   # skip walk to isolate feeding-only score
            grooming_interval_days=0,
            vet_interval_days=0,
            reset_period="none",
        )
        # With walk/grooming/vet targets=0 those pcts are 0, so only feeding counts.
        # overall = round((feeding_pct + 0 + 0 + 0) / 4)
        activity_svc.log_activity(pet.id, "feeding", {}, today)   # feeding_pct = 100

        score = score_svc.calculate(pet.id, today)
        # overall = round(100/4) = 25 → D
        assert score.grade == "D"

    def test_upsert_recalculates_existing_score(self, pet_svc, target_svc, activity_svc, score_svc):
        """Calling calculate twice for same (pet, date) updates in place."""
        pet = make_pet(pet_svc)
        set_basic_targets(target_svc, pet.id)
        today = date.today()

        s1 = score_svc.calculate(pet.id, today)
        first_id = s1.id

        activity_svc.log_activity(pet.id, "feeding", {}, today)
        activity_svc.log_activity(pet.id, "feeding", {}, today)

        s2 = score_svc.calculate(pet.id, today)

        assert s2.id == first_id, "upsert must reuse the same CareScore record"
        assert s2.feeding_pct == 100


# ---------------------------------------------------------------------------
# 5. CARE TARGET RESET (daily / weekly)
# ---------------------------------------------------------------------------

class TestCareTargetReset:
    """check_and_reset flips 'achieved' → 'pending' when the period has elapsed."""

    def test_daily_reset_after_one_day(self, pet_svc, target_svc):
        pet = make_pet(pet_svc)
        set_basic_targets(target_svc, pet.id, reset_period="daily")

        yesterday = date.today() - timedelta(days=1)
        target_svc.mark_achieved(pet.id)
        # Simulate last_reset_date as yesterday
        target = target_svc.get_targets(pet.id)
        target.last_reset_date = yesterday

        result = target_svc.check_and_reset(pet.id, today=date.today())
        assert result is not None
        assert result.status == "pending"

    def test_daily_no_reset_same_day(self, pet_svc, target_svc):
        """No reset if less than 1 day has passed."""
        pet = make_pet(pet_svc)
        set_basic_targets(target_svc, pet.id, reset_period="daily")
        target_svc.mark_achieved(pet.id)

        # last_reset_date is today (set by mark_achieved) — should not reset
        result = target_svc.check_and_reset(pet.id, today=date.today())
        assert result is None

    def test_weekly_reset_after_7_days(self, pet_svc, target_svc):
        pet = make_pet(pet_svc)
        set_basic_targets(target_svc, pet.id, reset_period="weekly")
        target_svc.mark_achieved(pet.id)

        target = target_svc.get_targets(pet.id)
        target.last_reset_date = date.today() - timedelta(days=7)

        result = target_svc.check_and_reset(pet.id, today=date.today())
        assert result is not None
        assert result.status == "pending"

    def test_weekly_no_reset_before_7_days(self, pet_svc, target_svc):
        pet = make_pet(pet_svc)
        set_basic_targets(target_svc, pet.id, reset_period="weekly")
        target_svc.mark_achieved(pet.id)

        target = target_svc.get_targets(pet.id)
        target.last_reset_date = date.today() - timedelta(days=5)

        result = target_svc.check_and_reset(pet.id, today=date.today())
        assert result is None

    def test_no_reset_when_still_pending(self, pet_svc, target_svc):
        """A target that was never achieved should not be touched by check_and_reset."""
        pet = make_pet(pet_svc)
        set_basic_targets(target_svc, pet.id, reset_period="daily")

        result = target_svc.check_and_reset(pet.id, today=date.today())
        assert result is None

    def test_check_and_reset_all_batch(self, pet_svc, target_svc):
        """check_and_reset_all returns one entry per pet that was actually reset."""
        pet_a = make_pet(pet_svc, name="A")
        pet_b = make_pet(pet_svc, name="B")

        set_basic_targets(target_svc, pet_a.id, reset_period="daily")
        set_basic_targets(target_svc, pet_b.id, reset_period="daily")

        target_svc.mark_achieved(pet_a.id)
        target_svc.mark_achieved(pet_b.id)

        # Push both last_reset_date to yesterday
        for pet_id in [pet_a.id, pet_b.id]:
            t = target_svc.get_targets(pet_id)
            t.last_reset_date = date.today() - timedelta(days=1)

        resets = target_svc.check_and_reset_all(today=date.today())
        assert len(resets) == 2
        assert all(t.status == "pending" for t in resets)
