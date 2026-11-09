"""Private, pre-generated event schedule; only occurred events become public."""
import copy
from fractions import Fraction


class EventSchedule:
    def __init__(self, plan, roads):
        self.plan = sorted(copy.deepcopy(plan), key=lambda e: (e["turn"], e["id"]))
        self.base_roads = copy.deepcopy(roads)
        self.history = []

    def apply(self, turn, roads, shelters):
        occurred = []
        for event in self.plan:
            phase = "started" if event["turn"] == turn else None
            if event.get("end_turn") == turn:
                phase = "ended"
            if phase is None:
                continue
            public = {"id": event["id"], "turn": turn, "type": event["type"],
                      "phase": phase, "payload": copy.deepcopy(event["payload"])}
            occurred.append(public)
            if event["type"] == "demand_spike":
                payload = event["payload"]
                shelters[payload["shelter_id"]]["batches"].append({
                    "id": event["id"], "amount": payload["amount"],
                    "created_turn": turn, "due_turn": payload["due_turn"],
                    "received": 0, "on_time": 0})
        # Derive from base weights, never compound the previous turn's value.
        affected = {e["payload"]["road_id"] for e in self.plan if e["type"] != "demand_spike"}
        for road_id in sorted(affected):
            base = self.base_roads[road_id]
            active = [e for e in self.plan if e["type"] != "demand_spike"
                      and e["payload"]["road_id"] == road_id
                      and e["turn"] <= turn < e["end_turn"]]
            roads[road_id]["is_open"] = base["is_open"] and not any(e["type"] == "road_closed" for e in active)
            multiplier = Fraction(1)
            for event in active:
                if event["type"] == "road_congested":
                    multiplier *= Fraction(event["payload"]["multiplier"])
            cost = base["travel_turns"] * multiplier
            roads[road_id]["travel_turns"] = (cost.numerator + cost.denominator - 1) // cost.denominator
        self.history.extend(copy.deepcopy(occurred))
        return occurred
