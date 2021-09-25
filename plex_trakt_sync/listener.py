from time import sleep

from plexapi.server import PlexServer

from plex_trakt_sync.events import EventFactory
from plex_trakt_sync.logging import logging

PLAYING = "playing"


class EventDispatcher:
    def __init__(self):
        self.event_listeners = list()
        self.event_factory = EventFactory()
        self.logger = logging.getLogger("PlexTraktSync.EventDispatcher")

    def on(self, event_type, listener, **kwargs):
        self.event_listeners.append({
            "listener": listener,
            "event_type": event_type,
            "filters": kwargs,
        })
        return self

    def event_handler(self, data):
        self.logger.debug(data)
        events = self.event_factory.get_events(data)
        for event in events:
            self.dispatch(event)

    def dispatch(self, event):
        for listener in self.event_listeners:
            if not self.match_event(listener, event):
                continue

            listener["listener"](event)

    @staticmethod
    def match_filter(event, name, value):
        # test event property
        if hasattr(event, name) and getattr(event, name) == value:
            return True
        # test event dictionary items
        if name not in event:
            return False
        if event[name] not in value:
            return False
        return True

    def match_event(self, listener, event):
        if not isinstance(event, listener["event_type"]):
            return False

        if listener["filters"]:
            for name, value in listener["filters"].items():
                if not self.match_filter(event, name, value):
                    return False

        return True


class WebSocketListener:
    def __init__(self, plex: PlexServer, interval=1):
        self.plex = plex
        self.interval = interval
        self.dispatcher = EventDispatcher()
        self.logger = logging.getLogger("PlexTraktSync.WebSocketListener")

    def on(self, event_type, listener, **kwargs):
        self.dispatcher.on(event_type, listener, **kwargs)

    def listen(self):
        while True:
            notifier = self.plex.startAlertListener(callback=self.dispatcher.event_handler)
            while notifier.is_alive():
                sleep(self.interval)

            self.logger.debug(f"Listener finished. Restarting in {self.interval}")
            sleep(self.interval)
