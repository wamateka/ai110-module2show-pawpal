from pawpal_system import (
    UserService,
    PetService,
    CareTargetService,
)

# --- Setup services ---
user_service = UserService()
pet_service = PetService()
target_service = CareTargetService()


def print_targets(pet_name: str, pet_id: str) -> None:
    """Fetch and pretty-print care targets for a single pet."""
    t = target_service.get_targets(pet_id)
    print(f"  Pet       : {pet_name}")
    print(f"  Feeding   : {t.daily_meals} meal(s) per day")
    print(f"  Exercise  : {t.daily_walk_min} min of walking per day")
    print(f"  Grooming  : every {t.grooming_interval_days} day(s)")
    print(f"  Vet Visit : every {t.vet_interval_days} day(s)")
    print()


def main() -> None:
    # --- Create owner ---
    owner = user_service.register(
        name="Alex Rivera",
        email="alex@pawpal.com",
        password="securepassword123",
    )
    print("=" * 45)
    print(f"  Owner registered: {owner.name} ({owner.email})")
    print("=" * 45)
    print()

    # --- Create pets ---
    # Pet 1: a large active dog
    max = pet_service.create(
        user_id=owner.id,
        name="Max",
        species="dog",
        breed="Golden Retriever",
        weight_kg=32.0,
        age_years=3,
    )

    # Pet 2: an indoor cat
    luna = pet_service.create(
        user_id=owner.id,
        name="Luna",
        species="cat",
        breed="Siamese",
        weight_kg=4.2,
        age_years=5,
    )

    # Pet 3: a small senior rabbit
    biscuit = pet_service.create(
        user_id=owner.id,
        name="Biscuit",
        species="rabbit",
        breed="Holland Lop",
        weight_kg=1.8,
        age_years=7,
    )

    # Pet 4: a young energetic puppy
    pepper = pet_service.create(
        user_id=owner.id,
        name="Pepper",
        species="dog",
        breed="Border Collie",
        weight_kg=10.5,
        age_years=1,
    )

    pets = [max, luna, biscuit, pepper]
    print(f"  {len(pets)} pets created for {owner.name}:")
    for p in pets:
        print(f"    - {p.name} ({p.breed}, {p.age_years}yr, {p.weight_kg}kg)")
    print()

    # --- Set care targets ---
    # Max: active dog — 3 meals, 90 min walks, groom every 7 days, vet every 180 days
    target_service.set_targets(
        pet_id=max.id,
        daily_meals=3,
        daily_walk_min=90,
        grooming_interval_days=7,
        vet_interval_days=180,
    )

    # Luna: indoor cat — 2 meals, 0 walk min, groom every 14 days, vet every 365 days
    target_service.set_targets(
        pet_id=luna.id,
        daily_meals=2,
        daily_walk_min=0,
        grooming_interval_days=14,
        vet_interval_days=365,
    )

    # Biscuit: senior rabbit — 2 meals, 20 min exercise, groom every 10 days, vet every 90 days
    target_service.set_targets(
        pet_id=biscuit.id,
        daily_meals=2,
        daily_walk_min=20,
        grooming_interval_days=10,
        vet_interval_days=90,
    )

    # Pepper: energetic puppy — 4 meals, 120 min walks, groom every 5 days, vet every 90 days
    target_service.set_targets(
        pet_id=pepper.id,
        daily_meals=4,
        daily_walk_min=120,
        grooming_interval_days=5,
        vet_interval_days=90,
    )

    # --- Print targets ---
    print("=" * 45)
    print("  Care Targets")
    print("=" * 45)
    print()
    for pet in pets:
        print_targets(pet.name, pet.id)

    # --- Verify update upsert (set_targets called twice for Max) ---
    print("  [Testing upsert] Updating Max's vet interval to 120 days...")
    target_service.set_targets(
        pet_id=max.id,
        daily_meals=3,
        daily_walk_min=90,
        grooming_interval_days=7,
        vet_interval_days=120,
    )
    print()
    print("  Max's targets after update:")
    print_targets(max.name, max.id)


if __name__ == "__main__":
    main()
