# spanky.py

Chat-bot overlay framework that can run on top of any python-based bot and call plugins on multiple types of events.

### High level schematic:


\=====================================
| Backend that communicates with    |
| Discord, Slack, IRC servers, etc. |
\=====================================
                  ||
                  ||
        events are decapsulated and 
          sent to the framework
                  ||                                                              -------------------
                  ||                                                         | -> | moderator tools |
                  \/                                                         |    -------------------
            =============                                                    |    -----------
            | Framework | ---> bot framework triggers events            ---> | -> | logging |
            =============     that are specified in the plugins folders      |    -----------
                                                                             |    ---------------------
                                                                             | -> | periodic events   |
                                                                                  | for announcements |
                                                                                  ---------------------

