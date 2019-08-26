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
./Dockerfile/start.sh
```

#### 2. Native (not recommended)

There are a lot of system dependencies that need to be installed on the system where you are planning to run the bot.

Some of the prerequisites can be found in `Dockerfile/Dockerfile`. Once you install them, run the bot with Python 3.5.
