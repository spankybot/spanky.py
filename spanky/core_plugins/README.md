# `core_plugins`


`core_plugins` is a set of essential plugins that add various functionalities to the bot. For example, this is where the `permissions` attribute is checked, channel groups are checked, PMs are handled properly, and more features coming soon, as needed.

Here is a list with the order in which these middleware are executed:
- `setup_perm_ctx` (p=0)
- `check_server_id` (p=1)
- `check_format` (legacy) (p=4)
- `handle_pm` (p=5)
- `perm_admin` (p=10)
- `perm_bot_owner` (p=10)
- `check_chgroups` (p=15)
- `finalize_perm_filter` (p=1000000) (this should be the last)
