import os
import json

class CalendarTgBot:
    def __init__(self):
        self.path_events = "events.json"
        self.events = self.load_events()

    def load_events(self):
        if os.path.isfile(self.path_events):
            with open(self.path_events, "r") as f:
                return json.load(f)
        return {}

    def save_events(self):
        with open(self.path_events, "w") as f:
            json.dump(self.events, f)

    def create_event(self, name, date, time, details):
        event_id = len(self.events) + 1
        event = {
            "id": event_id,
            "name": name,
            "date": date,
            "time": time,
            "details": details
        }
        self.events[event_id] = event
        self.save_events()
        return event_id
    
    def get_event(self, event_id):
        return self.events.get(event_id, None)
    
    def delete_event(self, event_id):
        if event_id in self.events:
            del self.events[event_id]
            return True
        return False
    
    def list_events(self):
        return list(self.events.values())
    
    def update_event(self, event_id, name=None, date=None, time=None, details=None):
        if event_id in self.events:
            if name:
                self.events[event_id]["name"] = name
            if date:
                self.events[event_id]["date"] = date
            if time:
                self.events[event_id]["time"] = time
            if details:
                self.events[event_id]["details"] = details
            return True
        return False
    