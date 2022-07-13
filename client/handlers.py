import weakref
from cbor2 import loads

from . import messages

def handle_update(client, message, specifier):
    """Update a delegate in the current state

    Args:
        client (Client): 
            client to be updated
        message (Message): 
            message containing updates
        specifier (str): 
            which part of state to update
    """

    current_state = client.state[specifier][message.id[0]]
    ensure_gen_match(current_state.info.id, message.id)
    for attribute, value in message.as_dict().items():
        setattr(current_state, attribute, value)


def ensure_gen_match(id1: list, id2: list):
    """Ensure id's match

    Args:
       id1 (list) : id to be checked
       id2 (list) : id to be checked

    Raises:
        Exception: Generation Mismatch
    """
    if id1 != id2:
        raise Exception(f"Generation Mismatch {id1} - {id2}")


# Put this inside core class?
# Split each section into helper function?
def handle(client, encoded_message):
    """handle message from server

    'Handle' uses the ID attached to message to get handling info, and uses this info 
    to take proper course of action with message. The function has 5 main sections 
    handling create, delete, and update messages along with signalinvocation and reply
    messages. For now all other communication messages are simply printed.

    'Handle' is also responsible for managing the client's state and working with the
    delegates in a couple of key ways. This function creates, deletes, and updates
    delegates as well as invoking methods on the delegates using signals.

    Args:
        client (Client): client receiving the message
        encoded_message (CBOR array): array with id and message as dictionary
    """

    # Decode message
    raw_message = loads(encoded_message)
    
    # Process message using ID from dict
    handle_info = client.server_message_map[raw_message[0]]
    action = handle_info.action
    specifier = handle_info.specifier
    message_obj = messages.Message.from_dict(raw_message[1])

    #print(f"\n  {action} - {specifier}\n{message_obj}")
    
    # Update state based on map info
    if action == "create":

        # Create instance of delegate
        specifier = specifier
        reference = weakref.ref(client)
        reference_obj = reference()
        delegate = client.delegates[specifier](reference_obj, message_obj, specifier)

        # Update state and pass message info to the delegate's handler
        client.state[specifier][message_obj.id[0]] = delegate
        delegate.on_new(message_obj)
    
    elif action == "delete":

        state_delegate = client.state[specifier][message_obj.id[0]]

        # Ensure generations match and update state / delegate
        ensure_gen_match(message_obj.id, state_delegate.info.id)
        state_delegate.on_remove(message_obj)
        del state_delegate

    elif action == "update":

        if specifier != "document":
            # Ensure generations match and update state
            ensure_gen_match(message_obj.id, client.state[specifier][message_obj.id[0]].info.id)
            handle_update(client, message_obj, specifier)
            
        # Inform delegate
        client.state[specifier][message_obj.id[0]].on_update(message_obj)

    elif action == "reply":

        # Handle callback functions
        if hasattr(message_obj, "method_exception"):
            raise Exception(f"Method call ({message_obj}) resulted in exception from server")
        else:
            callback = client.callback_map.pop(message_obj.invoke_id)
            callback(message_obj.result)

    elif action == "invoke":

        # Handle invoke message from server
        print("Handling Signal from the server...")
        id = message_obj.id
        signal_data = message_obj.signal_data
        signal = client.state["signals"][id[0]]
        ensure_gen_match(id, signal.info.id)

        # Determine the delegate the signal is being invoked on
        context = getattr(message_obj, "context", False)
        if not context:
            target_delegate = client.state["document"]
        elif hasattr(context, "table"):
            target_delegate = client.state["tables"][context.table[0]]
            ensure_gen_match(target_delegate.info.id, context.table)
        elif hasattr(context, "entity"):
            target_delegate = client.state["entities"][context.entity[0]]
            ensure_gen_match(target_delegate.info.id, context.entity)
        elif hasattr(context, "plot"):
            target_delegate = client.state["plots"][context.plot[0]]
            ensure_gen_match(target_delegate.info.id, context.plot)
        else:
            raise Exception("Couldn't handle signal from server")

        # Invoke signal attached to target delegate
        target_delegate.signals[signal.info.name](*signal_data)

    else:
        # Communication messages or document messages
        # For right now just print these, could add handlers for "invoke", "reset" actions
        print(message_obj)


    