def decide(request):
    state = request['observation']
    actions = []
    stock = state['depot']['stock']
    for vehicle in state['vehicles']:
        if vehicle['status'] != 'idle':
            continue
        target = None
        largest = 0
        for shelter in state['shelters']:
            pending = shelter['outstanding']
            for other in state['vehicles']:
                if other['leg'] == 'delivering' and other['target'] == shelter['id']:
                    pending = pending - other['cargo']
            for action in actions:
                if action['target_shelter_id'] == shelter['id']:
                    pending = pending - action['quantity']
            if pending > largest:
                largest = pending
                target = shelter['id']
        quantity = min(stock, vehicle['capacity'], largest)
        if target != None and quantity > 0:
            actions = append(actions, {'vehicle_id': vehicle['id'], 'type': 'dispatch',
                                      'target_shelter_id': target, 'quantity': quantity})
            stock = stock - quantity
    return {'protocol_version': '0.1', 'turn': request['turn'], 'actions': actions}
