from threading import Thread
from time import sleep
from typing import Callable, Any
from sensors import SensorsState


class AutoLifecycle:
    def __init__(
            self,
            get_state: Callable[[], SensorsState],
            get_settings: callable,
            handler: Callable[[Any, SensorsState], None],
    ):
        self.__get_state = get_state
        self.__get_settings = get_settings

        self.__handler = handler
        self.active = False

    def set_active(self, active: bool):
        if active:
            print("Running in auto mode...")
        else:
            print("Quit auto mode...")

        self.active = active

    def start(self, interval: int = 1):
        print("Start waiting auto mode...\n")
        Thread(
            target=self.__get_listener(interval),
            daemon=True
        ).start()

    def __get_listener(self, interval: int) -> callable:
        def listener():
            while True:
                sleep(interval)
                if not self.active: continue

                state = self.__get_state()
                settings = self.__get_settings()

                self.__handler(settings, state)

        return listener
