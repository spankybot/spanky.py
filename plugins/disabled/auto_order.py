# from spanky.plugin import hook, permissions
# from spanky.plugin.permissions import Permission
# from spanky.utils import time_utils
# from plugins.log import get_msg_cnt_for_channel_after

# #
# # Auto channel ordering
# #
# @hook.command(permissions=Permission.admin, format="chan")
# def add_chan_to_auto_order(text, str_to_id, storage, send_message, server):
#     """
#     <channel> -
#     """
#     channel_id = str_to_id(text)

#     found = False
#     for chan in server.get_channels():
#         if chan.id == channel_id:
#             found = True
#             break

#     if not found:
#         return "No channel named: " + text

#     if "auto_order" not in storage:
#         storage["auto_order"] = []

#     if channel_id in storage["auto_order"]:
#         return "Channel already added"

#     storage["auto_order"].append(channel_id)
#     storage.sync()
#     send_message("Done")


# @hook.command(permissions=Permission.admin)
# def list_auto_order_chans(storage, id_to_chan):
#     """
#     Lists channels that are auto ordered
#     """
#     if "auto_order" not in storage:
#         return "No channels set"

#     chans = storage["auto_order"]

#     return ", ".join("<#%s>" % i for i in chans)


# @hook.command(permissions=Permission.admin)
# def del_chan_from_auto_order(text, storage, send_message, str_to_id):
#     """
#     <channel> -
#     """
#     if "auto_order" not in storage:
#         return "No channels set"

#     channel_id = str_to_id(text)
#     if channel_id in storage["auto_order"]:
#         storage["auto_order"].remove(channel_id)

#     storage.sync()
#     send_message("Done")


# def do_auto_order(server, chanlist):
#     lower_limit = int(time_utils.tnow()) - time_utils.SEC_IN_MIN * 60
#     server_chans = server.get_channels()
#     to_order = []
#     msgs_to_chan = {}

#     # Get channels to sort
#     for chan_id in chanlist:
#         for srvchan in server_chans:
#             if srvchan.id == chan_id:
#                 to_order.append(srvchan)

#     # Get number of messages for each channel
#     for channel in to_order:
#         cnt = get_msg_cnt_for_channel_after(channel.id, lower_limit)

#         if cnt not in msgs_to_chan:
#             msgs_to_chan[cnt] = []

#         # Store it in a map in case there are multiple channels with the same number
#         # of messages
#         msgs_to_chan[cnt].append(channel)

#     # Create an array containing the old positions
#     old_positions = sorted([i.position for i in to_order])
#     # Each most active channel will be positioned to the topmost position
#     for nb_messages in reversed(sorted(msgs_to_chan.keys())):
#         crt_elem = msgs_to_chan[nb_messages]

#         for chan in crt_elem:
#             # Only change the order if it's different
#             if chan.position != old_positions[0]:
#                 print(chan.name + " -> " + str(old_positions[0]))
#                 chan.move_channel(old_positions[0])
#             del old_positions[0]


# @hook.periodic(5)
# def order_chans(bot, storage_getter):
#     for server in bot.backend.get_servers():
#         stor = storage_getter(server.id)
#         if "auto_order" in stor:
#             do_auto_order(server, stor["auto_order"])
