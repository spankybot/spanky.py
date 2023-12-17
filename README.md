# spanky.py

Chat-bot overlay framework that can run on top of any python-based bot and call plugins on multiple types of events.

### High level schematic:

```
=====================================
| Backend that communicates with    |
| Discord, Slack, IRC servers, etc. |
=====================================
                  ||
                  ||
        events are decapsulated and 
          sent to the framework
                  ||                                                              -------------------
                  ||                                                         | -> | moderator tools |
                  \/                                                         |    -------------------
            =============                                                    |    -----------
            | Framework | ===> bot framework triggers events            ===> | -> | logging |
            =============      that are specified in the plugins folders     |    -----------
                                                                             |    ---------------------
                                                                             | -> | periodic events   |
                                                                                  | for announcements |
                                                                                  ---------------------
```

### Running the bot

#### 1. Using Docker (recommended)
The easiest way of stating up the bot is to use the tools provided in the `Dockerfile/` folder:

```
git clone https://github.com/gc-plp/spanky.py.git && \
  cd spanky.py

# Build container
./Dockerfile/build.sh

# Create bot_config.json
cp bot_config.json.sample bot_config.json

# Edit the config file
# vi bot_config.json

# Start the bot
./Dockerfile/start.sh <folder where home files are kept>
```

#### 2. Native (not recommended)

There are a lot of system dependencies that need to be installed on the system where you are planning to run the bot.

Some of the prerequisites can be found in `Dockerfile/Dockerfile`. Once you install them, run the bot with Python 3.5.


### Design notes

#### Plain commands

Plugins can be added in the `plugins/` folder and are dinamically loaded at startup.

A plugin can also be modified while the bot is running. A write event (i.e. saving the file) will trigger the bot
to reload the plugin.

Example:


```python
from spanky.hook2 import Hook
hook = Hook("example")

@hook.command()
def example1():
    return "example1 called"
```

##### Permissions

The bot has a built-in permission system that allows plugin authors to restrict who can use a command.

Currently there are two explicit permission levels set in `spanky/plugin/permissions.py`:

```python
@enum.unique
class Permission(enum.Enum):
    admin = "admin"  # Can be used by anyone with admin rights in a server
    bot_owner = "bot_owner"  # Bot big boss
```

Example:
```python
from spanky.hook2 import Hook
from spanky.plugin.permissions import Permission

hook = Hook("example")

@hook.command(permissions=Permission.admin)
def example2():
    return "example2 called"
```

This will make the `example2` command only be accessible by users having one of the rules set through
`admin_config admin_roles add @role` command.

Similarly, when using the `bot_owner` permission, commands will only be accessed by users specified in the
`bot_owner` field set in the `bot_config.json` file.

#### Slash commands

Slash commands are registered through the `hook` decorator, but are only added when the `slash_servers` parameter is
set in the decorator. Example:

```python
from spanky.hook2 import Hook
hook = Hook("example")

@hook.command(slash_servers=["123456"])
def example1():
    return "example1 called"

```

By default, the bot will add a `string` parameter to plugins that request the `text` parameter. Example:

```python
from spanky.hook2 import Hook
hook = Hook("example")

@hook.command(slash_servers=["123456"])
def example2(text):
    return "example2 called with " + str(text)

```

Explicit arguments can also be added to a slash command and can be accessed through `event.args`

```python
from spanky.hook2 import Hook
hook = Hook("example")

@hook.command(slash_servers=["123456"])
def example3(event):
    """
    :sarg example_arg [1, 2]: int = 1 | some arg
    """
    return "example3 called with " + str(event.args)
```
