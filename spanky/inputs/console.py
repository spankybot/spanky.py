
class EventPeriodic:
    def __init__(self):
        pass
    
class EventMessage:
    def __init__(self, event_type, message):
        self.type = event_type
        
        self.msg = Message(message)
        self.channel = Channel(message.channel)
        self.nick = Author(message.author)
        self.text = message.text
        
        self.source = self.channel
        
        self._message = message
        
    def message(self, text, target=None):
        if target == None:
            target = self.source
            
        print("Send to %s: %s" % (target.name, text))

class Message():
    def __init__(self, object):
        self.text = object.text
        
class Author():
    def __init__(self, name):
        self.name = name

class Channel():
    def __init__(self, name):
        self.name = name
    
class Server():
    def __init__(self, name):
        self.name = name