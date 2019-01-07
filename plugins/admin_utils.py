from spanky.plugin import hook, permissions
from spanky.plugin.permissions import Permission

@hook.command(permissions=Permission.admin, format="user")
def kick(user_id_to_object, str_to_id, text):
    """
    <user> - Kick someone
    """
    user = user_id_to_object(str_to_id(text))
    user.kick()
    return "Okay."

@hook.command(permissions=Permission.admin, format="user")
def ban(user_id_to_object, str_to_id, text):
    """
    <user> - Ban someone
    """
    user = user_id_to_object(str_to_id(text))
    user.ban()
    return "Okay."

@hook.command(permissions=Permission.admin)
def add_join_event(storage, text):
    """
    <'type' 'option'> - Add action to be triggered on user join.
    Possible actions: 
        - message #channel blahblah -> send blahblah to #channel
        - role @role -> set @role on join).
    The scripted message can contain special words that are replaced when the event is triggered:
    - {AGE} - Account age
    - {USER} - User that just joined
    - {USER_ID} - User ID
    
    e.g. 'message #general {USER} / {USER_ID} just joined!' will send 'John / 12345678910 just joined!'
    """
    text = text.split()
    
    if text[0] == "message":
        if storage["on_join_message"] == None:
            storage["on_join_message"] = []
            
        storage["on_join_message"].append(" ".join(text[1:]))
        storage.sync()
    elif text[0] == "role":
        if storage["on_join_role"] == None:
            storage["on_join_role"] = []
            
        storage["on_join_role"].append(" ".join(text[1:]))
        storage.sync()
    else:
        return "Invalid type."
    return "Done."

@hook.command(permissions=Permission.admin)
def list_join_events(storage):
    msg = ""
    
    if storage["on_join_message"]:
        msg += "\nMessages: " + "; ".join(i for i in storage["on_join_message"])
    
    if storage["on_join_role"]:
        msg += "\nRoles: " + "; ".join(i for i in storage["on_join_role"])
    
    return msg

@hook.command(permissions=Permission.admin)
def del_join_event(storage, text):
    if storage["on_join_message"] and text in storage["on_join_message"]:
        del storage["on_join_message"][text]
        storage.sync()
        return "Done."
    elif storage["on_join_role"] and text in storage["on_join_role"]:
        del storage["on_join_role"][text]
        storage.sync()
        return "Done."
    
    return "Couldn't find it."