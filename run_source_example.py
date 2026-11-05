# runs the original Mesa Boltzmann Wealth example saved in src/boltzmann_wealth_model/:
import importlib.util
import json
from pathlib import Path
import sys


def run_source(steps=10):
    root = Path(__file__).resolve().parent / "src" / "boltzmann_wealth_model"
    # the original model imports agents from this Mesa path, so need point it to our saved agents.py:
    agent_name = "mesa.examples.basic.boltzmann_wealth_model.agents"
    spec = importlib.util.spec_from_file_location(agent_name, root / "agents.py")
    agents = importlib.util.module_from_spec(spec)
    sys.modules[agent_name] = agents
    spec.loader.exec_module(agents)
    spec = importlib.util.spec_from_file_location("preserved_boltzmann", root / "model.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    model = module.BoltzmannWealth(n=50, width=10, height=10, seed=4461)
    for _ in range(steps):
        model.step()
    wealth = [a.wealth for a in model.agents]
    assert sum(wealth) == 50 and min(wealth) >= 0
    assert all(type(a).__module__ == agent_name for a in model.agents)
    return {"source": "local copy of the original Mesa model.py and agents.py",
            "steps": steps, "agents": len(wealth), "total_wealth": sum(wealth),
            "gini": model.compute_gini()}

if __name__ == "__main__":
    print(json.dumps(run_source(), indent=2))

