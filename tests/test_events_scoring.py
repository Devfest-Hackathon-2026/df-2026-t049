import copy
import json
import random
import unittest

from reliefroute.bots import nearest_first, urgency_first
from reliefroute.engine import Engine, canonical
from reliefroute.scenario import PUBLIC_SEEDS, event_scenario, fixed_scenario
from reliefroute.scoring import score_record


def wait(request):
    return {"protocol_version": "0.1", "turn": request["turn"], "actions": []}


def dispatch(request, target="S2"):
    return {"protocol_version": "0.1", "turn": request["turn"], "actions": [
        {"vehicle_id": "V1", "type": "dispatch", "target_shelter_id": target, "quantity": 10}]}


def road_event(kind, start, end, road="R2", identifier="E", multiplier="3/2"):
    payload = {"road_id": road}
    if kind == "road_congested":
        payload["multiplier"] = multiplier
    return {"id": identifier, "turn": start, "end_turn": end, "type": kind, "payload": payload}


class EventTests(unittest.TestCase):
    def test_closure_applies_before_movement_and_recovers(self):
        scenario = fixed_scenario()
        scenario["event_plan"] = [road_event("road_closed", 1, 3)]
        engine = Engine(scenario)
        engine.step(dispatch)
        engine.step(wait)
        self.assertEqual(engine.vehicles["V1"]["status"], "blocked")
        self.assertEqual(engine.log[1]["movement_cost"], 0)
        engine.step(wait)
        engine.step(wait)
        self.assertEqual(engine.vehicles["V1"]["edge"]["remaining"], 1)
        engine.step(wait)
        self.assertEqual(engine.shelters["S2"]["batches"][0]["received"], 10)
        self.assertEqual([(r["turn"], e["phase"]) for r in engine.log for e in r["events"]], [(1, "started"), (3, "ended")])

    def test_entered_edge_finishes_despite_closure(self):
        scenario = fixed_scenario()
        scenario["event_plan"] = [road_event("road_closed", 2, 6)]
        engine = Engine(scenario)
        engine.step(dispatch)
        engine.step(wait)
        engine.step(wait)
        self.assertEqual(engine.shelters["S2"]["batches"][0]["received"], 10)
        engine.step(wait)
        self.assertEqual(engine.vehicles["V1"]["status"], "blocked")

    def test_congestion_ceil_no_compounding_and_entered_edge_unchanged(self):
        scenario = fixed_scenario()
        scenario["event_plan"] = [road_event("road_congested", 1, 4, "R3")]
        engine = Engine(scenario)
        engine.step(lambda req: dispatch(req, "S3"))
        engine.step(wait)
        self.assertEqual(engine.roads["R3"]["travel_turns"], 5)
        self.assertEqual(engine.vehicles["V1"]["edge"]["remaining"], 4)
        engine.step(wait)
        self.assertEqual(engine.roads["R3"]["travel_turns"], 5)
        engine.step(wait)
        engine.step(wait)  # expiration changes new routes, not the current traversal
        self.assertEqual(engine.roads["R3"]["travel_turns"], 3)
        self.assertEqual(engine.vehicles["V1"]["edge"]["remaining"], 1)
        engine.step(wait)
        self.assertEqual(engine.shelters["S3"]["batches"][0]["received"], 10)

    def test_overlapping_intervals_restore_base_independent_of_order(self):
        scenario = fixed_scenario()
        scenario["event_plan"] = [
            road_event("road_closed", 1, 3, identifier="a"),
            road_event("road_closed", 2, 4, identifier="b"),
            road_event("road_congested", 1, 3, identifier="c"),
            road_event("road_congested", 2, 4, identifier="d"),
        ]
        first = Engine(scenario).run(wait)
        scenario["event_plan"].reverse()
        second = Engine(scenario).run(wait)
        self.assertEqual(first, second)
        roads = [next(r for r in row["state"]["roads"] if r["id"] == "R2") for row in first["log"]]
        self.assertEqual([r["travel_turns"] for r in roads[:5]], [2, 3, 5, 3, 2])
        self.assertEqual([r["is_open"] for r in roads[:5]], [True, False, False, False, True])

    def test_spike_visible_only_when_applied_before_arrival(self):
        scenario = fixed_scenario()
        scenario["shelters"][0]["batches"][0]["amount"] = 0
        scenario["event_plan"] = [{"id": "secret-new-demand", "turn": 1, "type": "demand_spike",
            "payload": {"shelter_id": "S1", "amount": 10, "due_turn": 1}}]
        engine = Engine(scenario)
        self.assertNotIn("secret-new-demand", canonical(engine.observe()))
        engine.step(lambda req: dispatch(req, "S1"))
        self.assertNotIn("secret-new-demand", canonical(engine.log[0]))
        engine.step(wait)
        batch = engine.shelters["S1"]["batches"][1]
        self.assertEqual((batch["received"], batch["on_time"]), (10, 10))
        self.assertEqual(engine.log[1]["events"][0]["id"], "secret-new-demand")
        self.assertNotIn("event_plan", engine.observe()["observation"])
        self.assertNotIn("end_turn", canonical(engine.observe()))

    def test_closure_reroutes_via_available_links(self):
        scenario = event_scenario(11)
        scenario["event_plan"] = [road_event("road_closed", 1, 20)]
        engine = Engine(scenario)
        engine.step(dispatch)
        engine.step(wait)
        self.assertEqual(engine.vehicles["V1"]["node_id"], "N1")
        engine.step(wait)
        engine.step(wait)
        self.assertEqual(engine.shelters["S2"]["batches"][0]["received"], 10)

    def test_initial_observation_does_not_identify_private_seed(self):
        observations = [Engine(event_scenario(seed)).observe() for seed in PUBLIC_SEEDS]
        self.assertEqual(observations[0], observations[1])
        self.assertEqual(observations[1], observations[2])
        self.assertNotIn("seed", observations[0])
        self.assertEqual(observations[0]["match_id"], "local-match")

    def test_rng_isolation_and_identical_events_for_both_policies(self):
        rng_state = random.getstate()
        scenario = event_scenario(11)
        self.assertEqual(random.getstate(), rng_state)
        def noisy(request):
            for _ in range(30):
                random.random()
            return nearest_first(request)
        try:
            ordinary = Engine(scenario).run(nearest_first)
            consumed = Engine(event_scenario(11)).run(noisy)
            urgent = Engine(event_scenario(11)).run(urgency_first)
            self.assertEqual(ordinary, consumed)
            self.assertEqual([r["events"] for r in ordinary["log"]], [r["events"] for r in urgent["log"]])
        finally:
            random.setstate(rng_state)

    def test_public_seeds_reproduce_and_conserve_resources(self):
        scenarios = [canonical(event_scenario(seed)) for seed in PUBLIC_SEEDS]
        self.assertEqual(len(set(scenarios)), 3)
        for seed in PUBLIC_SEEDS:
            for bot in (nearest_first, urgency_first):
                runs = [Engine(event_scenario(seed)).run(bot) for _ in range(3)]
                self.assertEqual(runs[0], runs[1])
                self.assertEqual(runs[1], runs[2])
                for row in runs[0]["log"]:
                    state = row["state"]
                    delivered = sum(b["received"] for s in state["shelters"] for b in s["batches"])
                    self.assertEqual(state["depot"]["stock"] + sum(v["cargo"] for v in state["vehicles"]) + delivered, 70)
                    for shelter in state["shelters"]:
                        for batch in shelter["batches"]:
                            self.assertTrue(0 <= batch["on_time"] <= batch["received"] <= batch["amount"])


class ScoringTests(unittest.TestCase):
    def test_original_hand_fixture_score(self):
        result = Engine(fixed_scenario()).run(nearest_first)
        self.assertEqual(result["score"]["metrics"], {"C": 1.0, "T": 0.833333, "F": 1.0, "E": 0.666667})
        self.assertEqual(result["score"]["total"], 95.0)
        self.assertEqual(result["score"]["movement_cost"], 24)

    def test_idle_is_zero_and_full_on_time_is_not_automatically_100(self):
        self.assertEqual(Engine(fixed_scenario()).run(wait)["score"]["total"], 0)
        scenario = fixed_scenario()
        for shelter in scenario["shelters"]:
            shelter["batches"][0]["due_turn"] = 23
        score = Engine(scenario).run(nearest_first)["score"]
        self.assertEqual([score["metrics"][k] for k in ("C", "T", "F")], [1, 1, 1])
        self.assertEqual(score["total"], 98.333333)

    def test_weighted_metrics_and_empty_shelter_excluded(self):
        record = Engine(fixed_scenario()).run(wait)
        shelters = record["log"][-1]["state"]["shelters"]
        for shelter, priority, amount, received, on_time in zip(
                shelters, [1, 3, 1], [20, 10, 0], [10, 10, 0], [5, 10, 0]):
            shelter["priority"] = priority
            shelter["batches"][0].update(amount=amount, received=received, on_time=on_time)
        score = score_record(record)
        self.assertEqual(score["metrics"], {"C": .8, "T": .7, "F": .5, "E": .8})
        self.assertEqual(score["total"], 73.5)

    def test_saved_record_rescore_ignores_cached_summary_and_score(self):
        record = json.loads(json.dumps(Engine(event_scenario(11)).run(urgency_first)))
        expected = copy.deepcopy(record["score"])
        record["score"] = {"total": 999}
        record["summary"] = {"travel_turns": 0, "delivered": 999}
        self.assertEqual(score_record(record), expected)

    def test_cost_clamp_future_demand_and_invalid_records(self):
        record = Engine(fixed_scenario()).run(nearest_first)
        record["log"][-1]["state"]["shelters"][0]["batches"].append(
            {"id": "future", "created_turn": 24, "due_turn": 25, "amount": 1000, "received": 0, "on_time": 0})
        self.assertEqual(score_record(record), record["score"])
        record["log"][0]["movement_cost"] = 1000
        self.assertEqual(score_record(record)["metrics"]["E"], 0)
        for bad in ( {**record, "scoring_version": "unknown"}, {**record, "log": []},
                     {**record, "log": record["log"][:-1]} ):
            with self.assertRaises(ValueError):
                score_record(bad)
        for budget in (0, -1, True):
            record["log"][-1]["state"]["efficiency_budget"] = budget
            with self.assertRaises(ValueError):
                score_record(record)
        scenario = fixed_scenario()
        for shelter in scenario["shelters"]:
            shelter["batches"] = []
        with self.assertRaises(ValueError):
            Engine(scenario).run(wait)

    def test_strategy_difference_and_public_score_baseline(self):
        expected = {11: (73.506944, 78.009259), 22: (73.564815, 78.618827), 33: (73.449074, 78.422068)}
        for seed, scores in expected.items():
            results = [Engine(event_scenario(seed)).run(bot) for bot in (nearest_first, urgency_first)]
            self.assertEqual(tuple(r["score"]["total"] for r in results), scores)
            self.assertEqual(results[0]["log"][0]["actions"][0]["action"]["target_shelter_id"], "S1")
            self.assertEqual(results[1]["log"][0]["actions"][0]["action"]["target_shelter_id"], "S3")
            for result in results:
                self.assertTrue(0 <= result["score"]["total"] <= 100)
                self.assertTrue(all(0 <= v <= 1 for v in result["score"]["metrics"].values()))


if __name__ == "__main__":
    unittest.main()
