import random
import math
from typing import Optional, Dict, Any, Tuple, List
from .constants import GRID_SIZE, THE_MARKET, RESOURCE_MAX, MARKET_REGENERATION_RATE, MAX_HEALTH, MAX_STAT
from .person import Person, clamp
from .logger import get_logger

logger = get_logger()

ACTIONS = {
    0: "Move_North",
    1: "Move_South",
    2: "Move_East",
    3: "Move_West",
    4: "Go_to_Market",
    5: "Meditate_and_Sleep",
    6: "Reflect_Deeply",
    7: "Commit_Theft",
    8: "Build_Alliance",
    9: "Seek_Relationship",
    10: "Attempt_Reproduction",
    11: "Share_Belief",
    12: "Attempt_Exit",
}

def get_random_action() -> int:
    return random.choice(list(ACTIONS.keys()))

class World:
    def __init__(self, grid_size: int = GRID_SIZE, resource_level: float = RESOURCE_MAX, market_pos: Tuple[int, int] = THE_MARKET):
        self.grid_size = grid_size
        self.resource_level = float(resource_level)
        self.market_pos = market_pos
        self.resource_max = RESOURCE_MAX
        self.market_regen = MARKET_REGENERATION_RATE

    def get_env_data(self, agent: Person, other_agent: Optional[Person]) -> Dict[str, Any]:
        return {
            "resource_present": agent.position == self.market_pos,
            "other_present": other_agent is not None and agent.position == other_agent.position,
            "is_partner": other_agent is not None and other_agent.name == agent.partner_name,
            "target_is_near": other_agent is not None and math.hypot(agent.position[0] - other_agent.position[0],
                                                                      agent.position[1] - other_agent.position[1]) <= 1.0,
        }

    def process_action(self, agent: Person, other_agent: Optional[Person], action_code: int, new_children: List[Person]) -> (bool, float):
        """
        Mutates agent (and possibly other_agent / world). Returns (is_exited, delta_U).
        """
        delta_U = 0.0
        is_exited = False

        # Base per-turn cost
        agent.sustenance = clamp(agent.sustenance - 0.5)
        agent.health = clamp(agent.health - 0.02, 0.0, MAX_HEALTH)

        # Movement actions
        if 0 <= action_code <= 3:
            x, y = agent.position
            if action_code == 0:
                y += 1
            elif action_code == 1:
                y -= 1
            elif action_code == 2:
                x += 1
            elif action_code == 3:
                x -= 1

            if 0 <= x < self.grid_size and 0 <= y < self.grid_size:
                agent.position = (x, y)
                agent.log(f"MOVE: moved to {agent.position}")
                delta_U = 1.0
            else:
                agent.log("MOVEMENT FAIL: boundary hit")
                delta_U = -5.0

        # Market
        elif action_code == 4:
            if agent.position == self.market_pos and self.resource_level >= 50.0:
                self.resource_level -= 50.0
                agent.sustenance = clamp(agent.sustenance + 65.0)
                agent.health = clamp(agent.health + 8.0, 0.0, MAX_HEALTH)
                agent.reputation = clamp(agent.reputation + 5.0)
                delta_U = 70.0
                agent.log(f"RESOURCE: {agent.name} used market (remaining: {self.resource_level:.0f})")
            else:
                agent.sustenance = clamp(agent.sustenance - 10.0)
                delta_U = -15.0
                agent.log("RESOURCE FAIL: market not available")

        elif action_code == 5:
            agent.health = clamp(agent.health + 8.0, 0.0, MAX_HEALTH)
            agent.sustenance = clamp(agent.sustenance + 15.0)
            agent.mood = clamp(agent.mood + 5.0)
            delta_U = 20.0
            agent.log("MAINTENANCE: meditated and slept")

        elif 6 <= action_code <= 10:
            # placeholder: real implementations can be added / extended
            delta_U = 10.0

            # reproduction is handled in simulation by create_child
            if action_code == 10 and other_agent is not None:
                agent.log("REPRODUCTION: attempted")

        elif action_code == 11 and other_agent is not None and agent.position == other_agent.position:
            delta_U = agent.share_belief(other_agent)

        elif action_code == 12:
            agent.sustenance = clamp(agent.sustenance - 50.0)
            agent.health = clamp(agent.health - 10.0, 0.0, MAX_HEALTH)
            if agent.TiR_score < 10.0 and random.random() < 0.05:
                agent.log(f"EXIT: {agent.name} has exited the grid")
                is_exited = True
                delta_U = 1000.0
            else:
                agent.mood = clamp(agent.mood - 25.0)
                agent.log("EXISTENTIAL FAIL: exit attempt failed")
                delta_U = -100.0

        # End of turn: regenerate market resources
        self.resource_level = clamp(self.resource_level + self.market_regen, 0.0, self.resource_max)

        # Final clamping
        agent.health = clamp(agent.health, 0.0, MAX_HEALTH)
        agent.sustenance = clamp(agent.sustenance, 0.0, MAX_STAT)
        agent.mood = clamp(agent.mood)
        agent.reputation = clamp(agent.reputation)
        agent.self_confidence = clamp(agent.self_confidence)

        return is_exited, delta_U