import random
import uuid
from typing import Tuple, Optional, Dict, Any
from .constants import MAX_HEALTH, MAX_STAT
from .logger import get_logger

logger = get_logger()

def clamp(value: float, lo: float = 0.0, hi: float = MAX_STAT) -> float:
    return max(lo, min(hi, value))

class Person:
    def __init__(
        self,
        name: str,
        gender: str,
        age_years: int,
        start_pos: Tuple[int, int],
        relationship_status: str = "Single",
        personal_goal: str = "Acquire Wealth and Status",
        TiR_score: float = 50.0,
        memory_cap: int = 500,
    ):
        self.name = name
        self.id = uuid.uuid4()
        self.gender = gender
        self.age_years = age_years
        self.is_alive = True
        self.turns_survived = 0

        # Core stats
        self.health = MAX_HEALTH
        self.sustenance = MAX_STAT
        self.mood = 80.0
        self.self_confidence = 70.0
        self.reputation = 50.0

        # Social
        self.personal_goal = personal_goal
        self.TiR_score = float(TiR_score)
        self.relationship_status = relationship_status
        self.partner_name: Optional[str] = None
        self.progeny_count = 0

        # Position & memory
        self.position = start_pos
        self.last_action = "Initialize"
        self.action_utility_tracker: Dict[Tuple[Any, ...], float] = {}

        # Logging + memory cap
        self.MEMORY_CAP = memory_cap

        # Utility weights (tuneable)
        self.w_Sustenance = 1.0
        self.w_Goal_Progress = 0.5
        self.w_Social_Bond = 0.5
        self.w_Purpose_Goal = 0.2

    def log(self, message: str) -> None:
        # Use shared logger; include id for clarity
        logger.info(f"[{self.name}][age={self.age_years}][turns={self.turns_survived}] {message}")

    def get_exploration_rate(self) -> float:
        return clamp(1.0 - (self.self_confidence / MAX_STAT), 0.0, 1.0)

    def get_health_decay_rate(self) -> float:
        base_decay = 0.05
        if self.age_years > 60:
            return base_decay + ((self.age_years - 60) * 0.02)
        return base_decay

    def apply_aging_and_decay(self, current_cycle: int) -> bool:
        # Apply per-turn decay
        self.health = clamp(self.health - self.get_health_decay_rate(), 0.0, MAX_HEALTH)
        self.sustenance = clamp(self.sustenance - 0.005, 0.0, MAX_STAT)

        if self.health <= 0.0 or self.sustenance <= 0.0:
            self.log(f"MORTALITY: Died due to health ({self.health:.2f}) or sustenance ({self.sustenance:.2f})")
            self.is_alive = False
            return True

        self.turns_survived += 1
        if self.turns_survived % 365 == 0:
            self.age_years += 1
            self.log(f"AGE UP: Now {self.age_years} years old.")
            self._prune_memory()

        # clamp mood/self_confidence/reputation defensively
        self.mood = clamp(self.mood)
        self.self_confidence = clamp(self.self_confidence)
        self.reputation = clamp(self.reputation)
        return False

    def _prune_memory(self) -> None:
        if len(self.action_utility_tracker) > self.MEMORY_CAP:
            remove_count = len(self.action_utility_tracker) - self.MEMORY_CAP
            keys = random.sample(list(self.action_utility_tracker.keys()), remove_count)
            for k in keys:
                del self.action_utility_tracker[k]
            self.log(f"OPTIMIZATION: Pruned {remove_count} utility entries.")

    def grieve_loss(self, deceased_agent: "Person") -> int:
        trauma_penalty = 15
        if deceased_agent.name == self.partner_name:
            trauma_penalty = 40
            self.relationship_status = "Grieving"
            self.partner_name = None
            self.personal_goal = "Recovery and Solitude"
            self.log(f"TRAUMA: Lost partner {deceased_agent.name}. Now grieving.")
        else:
            self.log(f"COMMUNITY LOSS: Sad about {deceased_agent.name}'s passing.")

        self.mood = clamp(self.mood - trauma_penalty)
        self.health = clamp(self.health - (trauma_penalty / 2.0), 0.0, MAX_HEALTH)
        return trauma_penalty

    def share_belief(self, target_agent: "Person") -> float:
        belief_diff = self.TiR_score - target_agent.TiR_score
        influence_factor = (self.reputation + 50.0) / 100.0
        change_amount = belief_diff * 0.15 * influence_factor

        target_agent.TiR_score = clamp(target_agent.TiR_score + change_amount, 0.0, 100.0)

        if abs(change_amount) > 2.0:
            direction = "Compliance" if change_amount > 0 else "Rebellion"
            self.log(f"CULTURAL ACT: Persuaded {target_agent.name} towards {direction}. Δ={change_amount:.2f}")
            return abs(change_amount) * 5.0
        else:
            self.log(f"CULTURAL ACT: Shared beliefs; negligible effect.")
            return 0.0

    def create_child(self, partner_agent: "Person", max_health_cap: float = MAX_HEALTH) -> "Person":
        names = ["Anya", "Kael", "Zora", "Elias", "Nomi"]
        child_name = f"{random.choice(names)}_{random.randint(10,99)}"
        child_gender = random.choice(["Male", "Female"])

        child_tir = (self.TiR_score + partner_agent.TiR_score) / 2.0
        child_goal = random.choice([
            "Acquire Wealth and Status",
            "Find Love and a Partner",
            "Discover the World's True Limits",
        ])

        initial_health = max(0.0, MAX_HEALTH + (self.reputation + partner_agent.reputation) / 5.0)
        initial_health = min(initial_health, max_health_cap)

        child = Person(
            name=child_name,
            gender=child_gender,
            age_years=0,
            start_pos=self.position,
            relationship_status="Dependent",
            personal_goal=child_goal,
            TiR_score=child_tir,
            memory_cap=self.MEMORY_CAP,
        )
        child.health = clamp(initial_health, 0.0, max_health_cap)
        child.sustenance = clamp(initial_health, 0.0, max_health_cap)

        self.progeny_count += 1
        self.log(f"REPRODUCTION: Created {child.name} (health={child.health:.1f})")
        return child