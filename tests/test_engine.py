import copy
import unittest

from reliefroute.bots import nearest_first
from reliefroute.engine import Engine, canonical, shortest_path
from reliefroute.scenario import fixed_scenario


def envelope(turn=0, actions=None):
    return {"protocol_version": "0.1", "turn": turn, "actions": actions or []}


def action(vehicle="V1", target="S1", quantity=10):
    return {"vehicle_id": vehicle, "type": "dispatch", "target_shelter_id": target, "quantity": quantity}


def wait(request):
    return envelope(request["turn"])


class EngineTests(unittest.TestCase):
    def test_hand_calculated_fixture(self):
        result = Engine(fixed_scenario()).run(nearest_first)
        self.assertEqual(result["summary"], {"turns": 24, "delivered": 60,
                         "depot_stock": 0, "cargo_remaining": 0, "travel_turns": 24})
        deliveries = [(row["turn"], d["vehicle_id"], d["shelter_id"], d["quantity"])
                      for row in result["log"] for d in row["deliveries"]]
        self.assertEqual(deliveries, [(1, "V1", "S1", 10), (1, "V2", "S1", 10),
                         (2, "V3", "S2", 10), (4, "V1", "S2", 10),
                         (5, "V2", "S3", 10), (7, "V3", "S3", 10)])
        final = result["log"][-1]["state"]
        self.assertTrue(all(v["status"] == "idle" for v in final["vehicles"]))
        self.assertEqual([s["batches"][0]["on_time"] for s in final["shelters"]], [20, 20, 10])

    def test_three_runs_are_identical_and_input_unchanged(self):
        scenario = fixed_scenario()
        original = copy.deepcopy(scenario)
        results = [canonical(Engine(scenario).run(nearest_first)) for _ in range(3)]
        self.assertEqual(results[0], results[1])
        self.assertEqual(results[0], results[2])
        self.assertEqual(scenario, original)

    def test_conservation_each_turn(self):
        result = Engine(fixed_scenario()).run(nearest_first)
        for row in result["log"]:
            state = row["state"]
            received = sum(b["received"] for s in state["shelters"] for b in s["batches"])
            self.assertEqual(state["depot"]["stock"] + sum(v["cargo"] for v in state["vehicles"]) + received, 60)
            self.assertGreaterEqual(state["depot"]["stock"], 0)
            for v in state["vehicles"]:
                self.assertTrue(0 <= v["cargo"] <= v["capacity"])

    def test_invalid_responses_do_not_mutate_state(self):
        invalid = [None, [], "bad JSON", {}, envelope(1), envelope(True),
                   {**envelope(), "score": 100}, {**envelope(), "actions": {}},
                   envelope(actions=[action()] * 4)]
        for value in [-1, 0, True, "1", 1.5, 11, None, []]:
            invalid.append(envelope(actions=[action(quantity=value)]))
        invalid += [envelope(actions=[action(vehicle="missing")]),
                    envelope(actions=[action(target="missing")]),
                    envelope(actions=[{**action(), "stock": 100}]),
                    envelope(actions=[action(vehicle=[])]), envelope(actions=[None])]
        for response in invalid:
            with self.subTest(response=response):
                engine = Engine(fixed_scenario())
                before = copy.deepcopy(engine.state)
                self.assertFalse(engine.dispatch(response)[0]["accepted"])
                self.assertEqual(engine.state, before)

    def test_duplicate_busy_vehicle_and_shared_stock(self):
        scenario = fixed_scenario()
        scenario["depot"]["stock"] = 15
        engine = Engine(scenario)
        results = engine.dispatch(envelope(actions=[action(), action(), action(vehicle="V2")]))
        self.assertEqual([r["reason"] for r in results], [None, "duplicate_vehicle", "insufficient_stock"])
        self.assertEqual(engine.dispatch(envelope(actions=[action()]))[0]["reason"], "vehicle_not_idle")
        self.assertEqual(engine.state["depot"]["stock"], 5)

    def test_dispatch_moves_next_turn_and_return_can_redispatch(self):
        engine = Engine(fixed_scenario())
        engine.step(nearest_first)
        self.assertEqual(engine.vehicles["V1"]["node_id"], "N0")
        engine.step(nearest_first)
        self.assertEqual(engine.vehicles["V1"]["node_id"], "N1")
        engine.step(nearest_first)
        self.assertEqual(engine.vehicles["V1"]["node_id"], "N0")
        self.assertEqual(engine.vehicles["V1"]["status"], "delivering")

    def test_excess_cargo_returns_and_future_demand_hidden(self):
        scenario = fixed_scenario()
        scenario["shelters"][0]["batches"][0]["amount"] = 3
        scenario["shelters"][0]["batches"].append({"id": "future", "amount": 100,
                  "created_turn": 10, "due_turn": 12, "received": 0, "on_time": 0})
        engine = Engine(scenario)
        self.assertEqual(len(engine.observe()["observation"]["shelters"][0]["batches"]), 1)
        engine.step(lambda req: envelope(req["turn"], [action()]))
        engine.step(wait)
        self.assertEqual(engine.vehicles["V1"]["cargo"], 7)
        self.assertEqual(engine.shelters["S1"]["batches"][1]["received"], 0)
        engine.step(wait)
        self.assertEqual(engine.state["depot"]["stock"], 57)
        self.assertEqual(engine.vehicles["V1"]["cargo"], 0)

    def test_final_turn_cargo_is_not_delivery(self):
        engine = Engine(fixed_scenario())
        result = engine.run(lambda req: envelope(req["turn"], [action()] if req["turn"] == 23 else []))
        self.assertEqual(result["summary"]["delivered"], 0)
        self.assertEqual(result["summary"]["cargo_remaining"], 10)
        with self.assertRaises(ValueError):
            engine.step(wait)

    def test_observation_isolation_and_bot_failure(self):
        engine = Engine(fixed_scenario())
        def broken(request):
            request["observation"]["depot"]["stock"] = 999
            raise RuntimeError("unstable details should not enter deterministic logs")
        result = engine.run(broken)
        self.assertEqual(result["summary"]["depot_stock"], 60)
        self.assertEqual(result["log"][0]["observation"]["observation"]["depot"]["stock"], 60)
        self.assertEqual(result["log"][0]["actions"][0]["reason"], "bot_error")

    def test_closed_road_and_blocked_return(self):
        engine = Engine(fixed_scenario())
        engine.roads["R1"]["is_open"] = False
        self.assertEqual(engine.dispatch(envelope(actions=[action()]))[0]["reason"], "unreachable")
        engine.roads["R1"]["is_open"] = True
        engine.step(lambda req: envelope(req["turn"], [action(target="S2")]))
        engine.step(wait)  # on the two-turn road
        engine.roads["R2"]["is_open"] = False
        engine.step(wait)  # existing traversal completes
        self.assertEqual(engine.shelters["S2"]["batches"][0]["received"], 10)
        engine.step(wait)
        self.assertEqual(engine.vehicles["V1"]["status"], "blocked")
        engine.roads["R2"]["is_open"] = True
        engine.step(wait)
        engine.step(wait)
        self.assertEqual(engine.vehicles["V1"]["status"], "idle")

    def test_path_tie_and_multi_edge_timing(self):
        roads = [{"id": rid, "from": a, "to": b, "travel_turns": 1, "is_open": True}
                 for rid, a, b in [("a", "N0", "A"), ("b", "A", "N1"),
                                    ("c", "N0", "B"), ("d", "B", "N1")]]
        self.assertEqual(shortest_path(roads, "N0", "N1"), (2, ("a", "b")))
        self.assertEqual(shortest_path(list(reversed(roads)), "N0", "N1"), (2, ("a", "b")))
        scenario = fixed_scenario()
        scenario["roads"] = roads
        engine = Engine(scenario)
        engine.step(lambda req: envelope(req["turn"], [action()]))
        engine.step(wait)
        self.assertEqual(engine.vehicles["V1"]["node_id"], "A")
        self.assertEqual(engine.shelters["S1"]["batches"][0]["received"], 0)
        engine.step(wait)
        self.assertEqual(engine.shelters["S1"]["batches"][0]["received"], 10)


if __name__ == "__main__":
    unittest.main()
