"""Integer-time engine. No network access or execution of uploaded code."""
import copy
import hashlib
import heapq
import json

from .events import EventSchedule
from .scoring import SCORING_VERSION, score_record
from .program_bot import ProgramError


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def shortest_path(roads, start, end):
    """Undirected positive-weight graph; ties use lexicographic node paths."""
    graph = {}
    for road in roads:
        if road["is_open"]:
            a, b, cost = road["from"], road["to"], road["travel_turns"]
            graph.setdefault(a, []).append((b, cost, road["id"]))
            graph.setdefault(b, []).append((a, cost, road["id"]))
    queue = [(0, (start,), ())]
    seen = set()
    while queue:
        cost, nodes, edges = heapq.heappop(queue)
        node = nodes[-1]
        if node in seen:
            continue
        seen.add(node)
        if node == end:
            return cost, edges
        for target, weight, road_id in sorted(graph.get(node, [])):
            if target not in seen:
                heapq.heappush(queue, (cost + weight, nodes + (target,), edges + (road_id,)))
    return None


class Engine:
    def __init__(self, scenario):
        # Scenarios are trusted fixtures; Bot observations/actions are untrusted.
        self.state = copy.deepcopy(scenario)
        self.turn = 0
        self.log = []
        self.travel_turns = 0
        self.roads = {r["id"]: r for r in self.state["roads"]}
        self.shelters = {s["id"]: s for s in self.state["shelters"]}
        self.vehicles = {v["id"]: v for v in self.state["vehicles"]}
        self.schedule = EventSchedule(self.state.pop("event_plan", []), self.roads)

    def observe(self):
        public = copy.deepcopy({k: self.state[k] for k in ("depot", "vehicles", "roads", "shelters")})
        for shelter in public["shelters"]:
            shelter["batches"] = [b for b in shelter["batches"] if b["created_turn"] <= self.turn]
            shelter["outstanding"] = sum(b["amount"] - b["received"] for b in shelter["batches"])
        public["events"] = copy.deepcopy(self.schedule.history)
        return {"protocol_version": "0.1", "match_id": "local-match",
                "scenario_version": self.state["scenario_version"], "turn": self.turn,
                "total_turns": self.state["total_turns"], "observation": public}

    def _enter_edge(self, vehicle):
        destination = (self.shelters[vehicle["target"]]["node_id"]
                       if vehicle["leg"] == "delivering" else self.state["depot"]["node_id"])
        route = shortest_path(self.state["roads"], vehicle["node_id"], destination)
        if route is None:
            vehicle["status"] = "blocked"
            return False
        vehicle["status"] = vehicle["leg"]
        road = self.roads[route[1][0]]
        target = road["to"] if road["from"] == vehicle["node_id"] else road["from"]
        vehicle["edge"] = {"road_id": road["id"], "to": target, "remaining": road["travel_turns"]}
        return True

    def _advance(self):
        deliveries = []
        for vehicle in self.state["vehicles"]:
            if vehicle["status"] == "idle":
                continue
            if vehicle["edge"] is None and not self._enter_edge(vehicle):
                continue
            edge = vehicle["edge"]
            edge["remaining"] -= 1
            self.travel_turns += 1
            if edge["remaining"]:
                continue
            vehicle["node_id"] = edge["to"]
            vehicle["edge"] = None
            if vehicle["leg"] == "delivering":
                shelter = self.shelters[vehicle["target"]]
                if vehicle["node_id"] != shelter["node_id"]:
                    continue
                delivered = 0
                for batch in sorted(shelter["batches"], key=lambda b: (b["due_turn"], b["id"])):
                    if batch["created_turn"] > self.turn:
                        continue
                    amount = min(vehicle["cargo"], batch["amount"] - batch["received"])
                    batch["received"] += amount
                    if self.turn <= batch["due_turn"]:
                        batch["on_time"] += amount
                    vehicle["cargo"] -= amount
                    delivered += amount
                deliveries.append({"vehicle_id": vehicle["id"], "shelter_id": shelter["id"], "quantity": delivered})
                vehicle["leg"] = vehicle["status"] = "returning"
            elif vehicle["node_id"] == self.state["depot"]["node_id"]:
                self.state["depot"]["stock"] += vehicle["cargo"]
                vehicle.update(status="idle", cargo=0, target=None, leg=None)
        return deliveries

    def dispatch(self, response):
        if (not isinstance(response, dict) or set(response) != {"protocol_version", "turn", "actions"}
                or response["protocol_version"] != "0.1"
                or type(response["turn"]) is not int or response["turn"] != self.turn
                or not isinstance(response["actions"], list)
                or len(response["actions"]) > len(self.vehicles)):
            return [{"accepted": False, "reason": "invalid_envelope"}]
        results, seen = [], set()
        for action in response["actions"]:
            reason = None
            expected = {"vehicle_id", "type", "target_shelter_id", "quantity"}
            if (not isinstance(action, dict) or set(action) != expected
                    or not all(isinstance(action[k], str) for k in ("vehicle_id", "type", "target_shelter_id"))
                    or type(action["quantity"]) is not int or action["quantity"] <= 0
                    or action["type"] != "dispatch"):
                results.append({"accepted": False, "reason": "invalid_action"})
                continue
            vid, target, quantity = action["vehicle_id"], action["target_shelter_id"], action["quantity"]
            vehicle, shelter = self.vehicles.get(vid), self.shelters.get(target)
            if vid in seen:
                reason = "duplicate_vehicle"
            elif vehicle is None:
                reason = "unknown_vehicle"
            elif shelter is None:
                reason = "unknown_shelter"
            elif vehicle["status"] != "idle" or vehicle["node_id"] != self.state["depot"]["node_id"]:
                reason = "vehicle_not_idle"
            elif quantity > vehicle["capacity"]:
                reason = "over_capacity"
            elif quantity > self.state["depot"]["stock"]:
                reason = "insufficient_stock"
            elif shortest_path(self.state["roads"], vehicle["node_id"], shelter["node_id"]) is None:
                reason = "unreachable"
            seen.add(vid)
            if reason is None:
                self.state["depot"]["stock"] -= quantity
                vehicle.update(status="delivering", leg="delivering", cargo=quantity, target=target)
            results.append({"action": copy.deepcopy(action), "accepted": reason is None, "reason": reason})
        return results

    def step(self, bot):
        if self.turn >= self.state["total_turns"]:
            raise ValueError("Match already finished")
        events = self.schedule.apply(self.turn, self.roads, self.shelters)
        before_cost = self.travel_turns
        deliveries = self._advance()
        observation = self.observe()
        try:
            response = bot(copy.deepcopy(observation))
        except ProgramError as exc:
            results = [{"accepted": False, "reason": "bot_error", "detail": str(exc)[:240]}]
        except Exception:
            results = [{"accepted": False, "reason": "bot_error"}]
        else:
            results = self.dispatch(response)
        snapshot = copy.deepcopy(self.state)
        self.log.append({"turn": self.turn, "observation": observation, "actions": results,
                         "deliveries": deliveries, "events": events, "state": snapshot,
                         "movement_cost": self.travel_turns - before_cost,
                         "state_hash": hashlib.sha256(canonical(snapshot).encode()).hexdigest()})
        self.turn += 1

    def run(self, bot):
        while self.turn < self.state["total_turns"]:
            self.step(bot)
        received = sum(b["received"] for s in self.state["shelters"] for b in s["batches"])
        record = {"scenario_version": self.state["scenario_version"], "seed": self.state["seed"],
                "scoring_version": SCORING_VERSION,
                "simulated": True, "summary": {"turns": self.turn, "delivered": received,
                "depot_stock": self.state["depot"]["stock"],
                "cargo_remaining": sum(v["cargo"] for v in self.state["vehicles"]),
                "travel_turns": self.travel_turns}, "log": self.log}

        record["score"] = score_record(record)
        return record
