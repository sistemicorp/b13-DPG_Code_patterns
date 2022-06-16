# -*- coding: utf-8 -*-
"""
Martin Guthrie

This code pattern demonstrates how to move GUI callback events to
their own thread via a class.

"""
import dearpygui.dearpygui as dpg
from threading import Thread, Lock, Event, Timer
import queue
import time
import traceback
from pubsub import pub
from dataclasses import dataclass
import logging
logger = logging.getLogger()
FORMAT = "%(asctime)s: %(filename)22s %(funcName)25s %(levelname)-5.5s :%(lineno)4s: %(message)s"
formatter = logging.Formatter(FORMAT)
consoleHandler = logging.StreamHandler()
consoleHandler.setFormatter(formatter)
logger.addHandler(consoleHandler)
logger.setLevel(logging.INFO)


@dataclass(frozen=True)
class PUB:

    SHUTDOWN = "SHUTDOWN"


class Worker(Thread):

    EVENT_SHUTDOWN = "EVENT_SHUTDOWN"
    EVENT_CB_BUTTON1 = "EVENT_CB_BUTTON1"

    def __init__(self, name="Worker"):
        super(Worker, self).__init__()

        self._lock = Lock()
        self._q = queue.Queue()
        self._stop_event = Event()

        pub.subscribe(self.onPubSHUTDOWN, PUB.SHUTDOWN)

        self.name = name
        self.start()

    def __q(self, item_dict: dict):
        logger.debug(item_dict)
        self._q.put(item_dict)

    def onPubSHUTDOWN(self, item_dict, topic=pub.AUTO_TOPIC):
        logger.info(f"{topic.getName()} - {item_dict}")
        self.shutdown()

    def shutdown(self):
        item_dict = {"type": self.EVENT_SHUTDOWN, "from": "shutdown"}
        self.__q(item_dict)

    def stopped(self):
        return self._stop_event.is_set()

    def _event_shutdown(self):
        self._stop_event.set()
        pub.unsubscribe(self.onPubSHUTDOWN,        PUB.SHUTDOWN)
        logger.info(f"{self.name} shutdown")

    # ------------- Your specific code goes here --------------------
    # For any GUI event, do the work on this class's thread, leaving
    # the DPG thread to run as fast as possible

    def _event_button1(self, item: dict):
        # this is now running on its own thread
        logger.info(item)

    def cb_button1(self, sender, app_data, user_data):
        logger.info(f"sender: {sender} {app_data} {user_data}")
        item_dict = {"type": self.EVENT_CB_BUTTON1,
                     "cb": dict(s=sender, a=app_data, u=user_data),
                     "from": "cb_button1"}
        self.__q(item_dict)

    def run(self):
        logger.info(f"{self.name} run thread started")
        while not self.stopped():

            try:
                item = self._q.get(block=True)
                logger.debug(item)

                with self._lock:
                    if item["type"] == self.EVENT_SHUTDOWN:
                        self._event_shutdown()

                    # ------------- Your specific code goes here --------------------

                    elif item["type"] == self.EVENT_CB_BUTTON1:
                        self._event_button1(item)

                    else:
                        logger.error("Unknown event: {}".format(item["type"]))

            except queue.Empty:
                pass
            except Exception as e:
                logger.error("Error processing event {}, {}".format(e, item["type"]))
                traceback.print_exc()

            time.sleep(0)  # allow other threads to run if any, in the case that the queue is full

        logger.info(f"{self.name} run thread stopped")


dpg.create_context()
dpg.create_viewport(height=200, width=200)
dpg.setup_dearpygui()

worker = Worker()

with dpg.window(label="Example", height=100, width=100):
    dpg.add_text("Hello world")
    dpg.add_button(tag="b1", label="Button1", callback=worker.cb_button1)

dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()
pub.sendMessage(PUB.SHUTDOWN, item_dict={"from": "main"})

