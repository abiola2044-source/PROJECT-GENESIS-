import argparse
import random
import csv
from typing import List, Optional
from .person import Person
from .world import World, get_random_action, ACTIONS
from .constants import CYCLES_PER_YEAR, CYCLES_PER_DEPENDENT_YEAR
from .logger import get_logger
from pathlib import Path
import matplotlib.pyplot as plt

logger = get_logger()

def _state_key(agent: Person, action_code: int):
    return (agent.position, agent.sustenance > 50.0, agent.reputation > 50.0, action_code)

def decide_action(agent: Person, population: List[Person]):
    target = None
    others = [a for a in population if a is not agent and a.relationship_status != "Dependent"]
    if others:
        target = random.choice(others)

    if random.random() < agent.get_exploration_rate():
        action = get_random_action()
        agent.log(f"DECISION: exploring with {ACTIONS[action]}")
        return action, target

    sample_actions = random.sample(list(ACTIONS.keys()), k=min(len(ACTIONS), 5))
    best = None
    best_u = -float("inf")
    for act in sample_actions:
        key = _state_key(agent, act)
        Q = agent.action_utility_tracker.get(key, 10.0)
        survival_modifier = (100.0 - agent.sustenance) * agent.w_Sustenance
        purpose = 0.0
        if agent.personal_goal == "Discover the World's True Limits" and act == 12:
            purpose = agent.w_Purpose_Goal * 100.0
        utility = Q + survival_modifier + purpose
        if utility > best_u:
            best_u = utility
            best = act
    return best if best is not None else get_random_action(), target

class Simulation:
    def __init__(self, turns: int = 10000, seed: Optional[int] = None, out_dir: str = "."):
        self.turns = turns
        self.seed = seed
        self.out_dir = Path(out_dir)
        self.world = World()
        self.global_clock = 0
        self.exit_log = []
        self.out_dir.mkdir(parents=True, exist_ok=True)
        if seed is not None:
            random.seed(seed)

        # initial population
        self.agents: List[Person] = [
            Person("Leo", "Male", 25, (1, 1), personal_goal="Acquire Wealth and Status", TiR_score=85),
            Person("Clara", "Female", 22, (9, 9), personal_goal="Find Love and a Partner", TiR_score=60),
            Person("Elara", "Female", 30, (5, 5), personal_goal="Discover the World's True Limits", TiR_score=5),
        ]

        # metrics
        self.metrics = []

    def step(self):
        self.global_clock += 1
        agents_to_remove = []
        new_children = []

        for agent in list(self.agents):
            if agent.relationship_status == "Dependent":
                agent.turns_survived += 1
                if agent.turns_survived >= CYCLES_PER_DEPENDENT_YEAR:
                    agent.relationship_status = "Single"
                    agent.age_years = 10
                    agent.log(f"MILESTONE: {agent.name} matured")
                continue

            if agent.apply_aging_and_decay(self.global_clock):
                agents_to_remove.append(agent)
                continue

            action, target = decide_action(agent, self.agents)
            key = _state_key(agent, action)
            env = self.world.get_env_data(agent, target)
            is_exited, delta_U = self.world.process_action(agent, target, action, new_children)

            # Q update
            alpha = 0.5
            cur_Q = agent.action_utility_tracker.get(key, 10.0)
            new_Q = cur_Q + alpha * (delta_U - cur_Q)
            agent.action_utility_tracker[key] = new_Q

            if is_exited:
                self.exit_log.append(agent)
                agents_to_remove.append(agent)
                for s in [a for a in self.agents if a is not agent]:
                    if s.TiR_score < 50.0:
                        s.self_confidence = 100.0
                        s.TiR_score = max(0.0, s.TiR_score - 20.0)
                        s.log(f"IDEOLOGY: {agent.name}'s exit changed TiR and confidence")

            if action == 10 and target is not None:
                child = agent.create_child(target)
                new_children.append(child)

        # grief + remove
        for deceased in agents_to_remove:
            for survivor in [a for a in self.agents if a is not deceased and a not in agents_to_remove]:
                survivor.grieve_loss(deceased)
            if deceased in self.agents:
                self.agents.remove(deceased)
                logger.info(f"COMMUNITY EVENT: {deceased.name} removed")

        self.agents.extend(new_children)

        # periodic outputs and metrics
        if self.global_clock % CYCLES_PER_YEAR == 0:
            compliant = sum(1 for a in self.agents if a.TiR_score > 60.0)
            rebel = sum(1 for a in self.agents if a.TiR_score < 40.0)
            avg_age = sum(a.age_years for a in self.agents) / len(self.agents) if self.agents else 0.0
            logger.info(f"YEAR {self.global_clock // CYCLES_PER_YEAR} | Pop {len(self.agents)} | AvgAge {avg_age:.1f} | C={compliant} R={rebel}")

        # flush metrics every step (lightweight)
        self.metrics.append({
            "tick": self.global_clock,
            "population": len(self.agents),
            "exited": len(self.exit_log),
            "resource_level": self.world.resource_level,
            "avg_TiR": (sum(a.TiR_score for a in self.agents) / len(self.agents)) if self.agents else 0.0
        })

    def run(self):
        logger.info("Simulation start")
        for _ in range(self.turns):
            self.step()

        logger.info("Simulation finished")
        self._write_metrics()
        self._plot_metrics()

    def _write_metrics(self):
        out_csv = self.out_dir / "metrics.csv"
        with open(out_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(self.metrics[0].keys()))
            writer.writeheader()
            for row in self.metrics:
                writer.writerow(row)
        logger.info(f"Wrote metrics to {out_csv}")

    def _plot_metrics(self):
        ticks = [m["tick"] for m in self.metrics]
        pop = [m["population"] for m in self.metrics]
        tir = [m["avg_TiR"] for m in self.metrics]
        res = [m["resource_level"] for m in self.metrics]

        plt.figure(figsize=(10,6))
        plt.plot(ticks, pop, label="Population")
        plt.plot(ticks, tir, label="Avg TiR")
        plt.plot(ticks, res, label="Resource Level")
        plt.xlabel("Tick")
        plt.legend()
        out_png = self.out_dir / "metrics.png"
        plt.savefig(out_png)
        logger.info(f"Wrote plot to {out_png}")

def main():
    parser = argparse.ArgumentParser(description="Run Project Genesis simulation")
    parser.add_argument("--turns", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--out", type=str, default="out")
    args = parser.parse_args()

    sim = Simulation(turns=args.turns, seed=args.seed, out_dir=args.out)
    sim.run()

if __name__ == "__main__":
    main()