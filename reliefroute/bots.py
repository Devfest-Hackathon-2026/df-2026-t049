"""Reference policies share the same public observation/action interface."""
from fractions import Fraction

from .engine import shortest_path


CONFIG_OPTIONS = {
    "priority_rule": ("urgency", "nearest", "fair"),
    "load_rule": ("full", "half"),
    "dispatch_rule": ("any", "full_load"),
}
DEFAULT_CONFIG = {key: values[0] for key, values in CONFIG_OPTIONS.items()}


def validate_config(config):
    if (not isinstance(config, dict) or set(config) != set(CONFIG_OPTIONS)
            or any(not isinstance(config[key], str) or config[key] not in values
                   for key, values in CONFIG_OPTIONS.items())):
        raise ValueError("Invalid strategy configuration")
    return dict(config)


def configured_bot(config):
    frozen = validate_config(config)
    return lambda request: _decide(request, frozen["priority_rule"] == "urgency", frozen)


def _decide(request, urgent, config=None):
    state = request["observation"]
    # Reserve incoming cargo against earliest-due demand, without hidden state.
    batches = {s["id"]: [[b["due_turn"], b["amount"] - b["received"]]
                        for b in sorted(s["batches"], key=lambda b: (b["due_turn"], b["id"]))]
               for s in state["shelters"]}

    def reserve(target, quantity):
        for batch in batches[target]:
            amount = min(quantity, batch[1])
            batch[1] -= amount
            quantity -= amount

    for vehicle in state["vehicles"]:
        if vehicle["leg"] == "delivering":
            reserve(vehicle["target"], vehicle["cargo"])
    stock, actions = state["depot"]["stock"], []
    for vehicle in sorted(state["vehicles"], key=lambda v: v["id"]):
        if vehicle["status"] != "idle" or stock <= 0:
            continue
        load_limit = vehicle["capacity"]
        if config and config["load_rule"] == "half":
            load_limit = max(1, load_limit // 2)
        candidates = []
        for shelter in state["shelters"]:
            outstanding = [b for b in batches[shelter["id"]] if b[1] > 0]
            route = shortest_path(state["roads"], vehicle["node_id"], shelter["node_id"])
            if outstanding and route is not None:
                distance = route[0]
                key = ((outstanding[0][0] - request["turn"] - distance,
                        -shelter["priority"], distance, shelter["id"])
                       if urgent else (distance, shelter["id"]))
                if config and config["priority_rule"] == "fair":
                    demand = sum(b["amount"] for b in shelter["batches"])
                    reserved_coverage = demand - sum(b[1] for b in batches[shelter["id"]])
                    key = (Fraction(reserved_coverage, demand), distance, shelter["id"])
                if config and config["dispatch_rule"] == "full_load" and min(stock, sum(b[1] for b in outstanding)) < load_limit:
                    continue
                candidates.append((key, shelter["id"]))
        if candidates:
            _, target = min(candidates)
            quantity = min(stock, load_limit, sum(b[1] for b in batches[target]))
            actions.append({"vehicle_id": vehicle["id"], "type": "dispatch",
                            "target_shelter_id": target, "quantity": quantity})
            stock -= quantity
            reserve(target, quantity)
    return {"protocol_version": "0.1", "turn": request["turn"], "actions": actions}


def nearest_first(request):
    return _decide(request, urgent=False)


def urgency_first(request):
    return _decide(request, urgent=True)


BOTS = {"nearest": nearest_first, "urgency": urgency_first}
