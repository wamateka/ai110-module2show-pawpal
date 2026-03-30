import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pawpal_system import PetService, CareTargetService


# Shared helpers — fresh service instances per test via fixtures so state
# never leaks between tests.

@pytest.fixture
def services():
    """Return isolated PetService and CareTargetService instances."""
    # Clear class-level dicts before each test
    PetService._pets = {}
    CareTargetService._targets = {}
    return PetService(), CareTargetService()


def make_pet(pet_service: PetService) -> str:
    """Create a throwaway pet and return its id."""
    pet = pet_service.create(
        user_id="user-001",
        name="Buddy",
        species="dog",
    )
    return pet.id


# --- Test 1: mark_achieved sets status to "achieved" ---

def test_care_target_status_set_to_achieved(services):
    """
    After calling mark_achieved, the CareTarget's status should be 'achieved'.
    Before the call it starts as 'pending'.
    """
    pet_svc, target_svc = services
    pet_id = make_pet(pet_svc)

    target_svc.set_targets(
        pet_id=pet_id,
        daily_meals=2,
        daily_walk_min=30,
        grooming_interval_days=14,
        vet_interval_days=180,
    )

    target = target_svc.get_targets(pet_id)
    assert target.status == "pending", "status should start as 'pending'"

    updated = target_svc.mark_achieved(pet_id)
    assert updated.status == "achieved", "status should be 'achieved' after mark_achieved"

    # get_targets should reflect the same change
    assert target_svc.get_targets(pet_id).status == "achieved"


# --- Test 2: adding a care target increases the count for that pet ---

def test_adding_care_target_increases_count(services):
    """
    count_for_pet returns 0 before any target is set and 1 after set_targets is called.
    """
    pet_svc, target_svc = services
    pet_id = make_pet(pet_svc)

    assert target_svc.count_for_pet(pet_id) == 0, "count should be 0 before any target is set"

    target_svc.set_targets(
        pet_id=pet_id,
        daily_meals=3,
        daily_walk_min=60,
        grooming_interval_days=7,
        vet_interval_days=365,
    )

    assert target_svc.count_for_pet(pet_id) == 1, "count should be 1 after set_targets"

    # Calling set_targets again (upsert) must NOT create a second row
    target_svc.set_targets(
        pet_id=pet_id,
        daily_meals=4,
        daily_walk_min=60,
        grooming_interval_days=7,
        vet_interval_days=365,
    )

    assert target_svc.count_for_pet(pet_id) == 1, "upsert must not add a duplicate row"
