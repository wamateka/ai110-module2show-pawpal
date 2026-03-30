# PawPal+ Project Reflection

## 1. System Design
user actions
- add pet: user will should be able to add a pet using it's name, age, breed, etc,
- set goals: user will be able to set goals for his pet care and set up a daily routine for his pet
- log activities: user will log activities like, walking a dog, feeding, grooming etc.
- view a dashboar of logged and activites and accomplished goals so far
**a. Initial design**

- Briefly describe your initial UML design.
- What classes did you include, and what responsibilities did you assign to each?

-> the initial design will consist of 5 main classes. 
 -user: It will contain information about the user such as the name, email, id
 -pets: it will contain informaiton about the pet such name, breed, age. it will be connected to owner through a foreign key of the user.
 -careTarget: this will contain the targets(daily goals) for each pet. there will be 4 main categories initially ie: feeding, exercise, grooming and vet
 daily__meals, daily_calories, daily_walk_min, daily_walk_km, grooming_interval_days, vet_checkc_interval_days
 - activity
  it log an ativitivy by adding an activity obejct in with for examplee
  type, details: {"meals":"", calories: "" }
 - careScore:  the care score for each pet.
  calculates each logged value in the activity log for a particular target and determines the percentage. eg daily_meals_score = num_meal/ daily_meal *100

**b. Design changes**

- Did your design change during implementation? no really
- If yes, describe at least one change and why you made it.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?
- How did you decide which constraints mattered most?

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.
- Why is that tradeoff reasonable for this scenario?

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
