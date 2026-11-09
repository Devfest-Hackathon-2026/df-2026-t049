"""Hand-verifiable fixture and seeded public event scenarios."""
import random
import hashlib

PUBLIC_SEEDS = (11, 22, 33)


def hourly_scenario(hour):
    """A versioned UTC-hour seed with a connected, varied six-shelter network."""
    if type(hour) is not int or not 0 <= hour < 10000000:
        raise ValueError('Invalid UTC hour')
    seed = int.from_bytes(hashlib.sha256(f'league-v1:{hour}'.encode()).digest()[:4], 'big')
    rng = random.Random(seed)
    scenario = fixed_scenario()
    scenario.update(scenario_version='1.0-hourly', seed=seed, total_turns=48,
                    efficiency_budget=240, league_hour=hour)
    scenario['depot']['stock'] = 160
    scenario['vehicles'] = [dict(scenario['vehicles'][0], id=f'V{i}', capacity=rng.choice((8, 10, 12)))
                            for i in range(1, 6)]
    scenario['shelters'] = [
        {'id': f'S{i}', 'node_id': f'N{i}', 'priority': rng.randint(1, 3),
         'batches': [{'id': f'B{i}', 'amount': rng.randint(2, 4) * 10,
                      'created_turn': 0, 'due_turn': rng.randint(10, 25),
                      'received': 0, 'on_time': 0}]}
        for i in range(1, 7)]
    # A ring remains connected after any single edge closure; random chords
    # vary shortest paths. No invented real-world geography is implied.
    edges = {(i, i + 1) for i in range(6)} | {(0, 6)}
    chords = [(a, b) for a in range(7) for b in range(a + 1, 7) if (a, b) not in edges]
    edges.update(rng.sample(chords, 4))
    scenario['roads'] = [
        {'id': f'R{i}', 'from': f'N{a}', 'to': f'N{b}',
         'travel_turns': rng.randint(1, 4), 'is_open': True}
        for i, (a, b) in enumerate(sorted(edges), 1)]
    plan = []
    for index, turn in enumerate((4, 18, 32)):
        plan.append({'id': f'C{index}', 'turn': turn, 'end_turn': turn + 6,
                     'type': 'road_closed', 'payload': {'road_id': rng.choice(scenario['roads'])['id']}})
        plan.append({'id': f'J{index}', 'turn': turn + 1, 'end_turn': turn + 8,
                     'type': 'road_congested',
                     'payload': {'road_id': rng.choice(scenario['roads'])['id'], 'multiplier': '2'}})
        plan.append({'id': f'D{index}', 'turn': turn + 3, 'type': 'demand_spike',
                     'payload': {'shelter_id': rng.choice(scenario['shelters'])['id'],
                                 'amount': 10, 'due_turn': turn + 11}})
    scenario['event_plan'] = plan
    return scenario


def fixed_scenario():
    return {
        "scenario_version": "0.2-fixture", "seed": 0, "total_turns": 24,
        "efficiency_budget": 72,
        "depot": {"id": "D1", "node_id": "N0", "stock": 60},
        "vehicles": [
            {"id": f"V{i}", "capacity": 10, "status": "idle",
             "node_id": "N0", "cargo": 0, "target": None,
             "leg": None, "edge": None}
            for i in range(1, 4)
        ],
        "shelters": [
            {"id": f"S{i}", "node_id": f"N{i}", "priority": 1,
             "batches": [{"id": f"B{i}", "amount": 20,
                          "created_turn": 0, "due_turn": 6,
                          "received": 0, "on_time": 0}]}
            for i in range(1, 4)
        ],
        "roads": [
            {"id": f"R{i}", "from": "N0", "to": f"N{i}",
             "travel_turns": i, "is_open": True}
            for i in range(1, 4)
        ],
    }


def event_scenario(seed):
    """Generate the complete plan before any Bot runs; no global RNG use."""
    if type(seed) is not int:
        raise ValueError("Seed must be an integer")
    rng = random.Random(seed)
    scenario = fixed_scenario()
    scenario.update(scenario_version="0.2-events", seed=seed)
    scenario["depot"]["stock"] = 70
    for i, shelter in enumerate(scenario["shelters"]):
        shelter["priority"] = i + 1
        shelter["batches"][0]["due_turn"] = (12, 7, 4)[i]
    # Alternative links make rerouting observable without a large map.
    scenario["roads"].extend([
        {"id": "R4", "from": "N1", "to": "N2", "travel_turns": 2, "is_open": True},
        {"id": "R5", "from": "N2", "to": "N3", "travel_turns": 2, "is_open": True},
    ])
    closed_turn = rng.randint(2, 4)
    congested_turn = rng.randint(1, 3)
    spike_turn = rng.randint(6, 9)
    scenario["event_plan"] = [
        {"id": "E1", "turn": closed_turn, "end_turn": closed_turn + 4,
         "type": "road_closed", "payload": {"road_id": rng.choice(["R1", "R2", "R3"])}},
        {"id": "E2", "turn": congested_turn, "end_turn": congested_turn + 5,
         "type": "road_congested", "payload": {"road_id": rng.choice(["R2", "R3"]),
                                                   "multiplier": rng.choice(["3/2", "2"])}},
        {"id": "E3", "turn": spike_turn, "type": "demand_spike",
         "payload": {"shelter_id": rng.choice(["S1", "S2", "S3"]), "amount": 20,
                     "due_turn": spike_turn + 4}},
    ]
    return scenario
