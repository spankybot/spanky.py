Use these utilities to run the bot in a container.
The container only installs tools to run the bot, without the actual bot source code. When started, the container will use the source code present in the upper directory.

`./build.sh - build the container`

`./start.sh - start the container`

N.B.: Not all functionality is enabled in the container.

Known issues:
- PRAW does not pick up the config file - will be fixed
