import enum
import os


# Kept for legacy purposes
# This should be eventually removed


# DEPRECATED
@enum.unique
class Permission(enum.Enum):
    admin = "admin"  # Can be used by anyone with admin rights in a server
    bot_owner = "bot_owner"  # Bot big boss
