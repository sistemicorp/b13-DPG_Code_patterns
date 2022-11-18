# -*- coding: utf-8 -*-
"""
Martin Guthrie

This code pattern demonstrates how to move GUI callback events to
their own thread via a class.

"""
import dearpygui.dearpygui as dpg
from threading import Thread, Lock, Event
import queue
import time
import traceback
import logging
logger = logging.getLogger()
FORMAT = "%(asctime)s: %(threadName)10s %(filename)22s %(funcName)25s %(levelname)-5.5s :%(lineno)4s: %(message)s"
formatter = logging.Formatter(FORMAT)
consoleHandler = logging.StreamHandler()
consoleHandler.setFormatter(formatter)
logger.addHandler(consoleHandler)
logger.setLevel(logging.INFO)


# Put this in a separate file
class WorkerBase(Thread):

    EVENT_SHUTDOWN = "EVENT_SHUTDOWN"

    def __init__(self, name="Worker"):
        super().__init__()

        self._lock = Lock()
        self._q = queue.Queue()
        self._stop_event = Event()

        # Note: you can create your dpg widgets here, create the widgets
        #       and put the callbacks in the same class

        self.name = name
        self.start()

    def enqueue(self, item_dict: dict):
        logger.debug(item_dict)
        self._q.put(item_dict)

    def shutdown(self):
        item_dict = {"type": self.EVENT_SHUTDOWN, "from": "shutdown"}
        self.enqueue(item_dict)
        self.join()

    def is_stopped(self):
        return self._stop_event.is_set()

    def _event_shutdown(self):
        self._stop_event.set()
        logger.info(f"{self.name} shutdown")

    def subc_events(self, item):
        return False

    def run(self):
        logger.info(f"{self.name} run thread started")
        while not self.is_stopped():

            try:
                item = self._q.get(block=True)
                logger.debug(item)

                with self._lock:
                    if item["type"] == self.EVENT_SHUTDOWN:
                        self._event_shutdown()

                    elif self.subc_events(item):
                        pass

                    else:
                        logger.error("Unknown event: {}".format(item["type"]))

            except queue.Empty:
                pass
            except Exception as e:
                logger.error("Error processing event {}, {}".format(e, item["type"]))
                traceback.print_exc()

            time.sleep(0)  # allow other threads to run if any, in the case that the queue is full

        logger.info(f"{self.name} run thread stopped")


class Worker(WorkerBase):

    EVENT_CB_BUTTON1 = "EVENT_CB_BUTTON1"

    def __init__(self, name="Worker"):
        super().__init__()

        # Note: you can create your dpg widgets here, create the widgets
        #       and put the callbacks in the same class

    # ------------- Your specific code goes here --------------------
    # For any GUI event, do the work on this class's thread, leaving
    # the DPG thread to run as fast as possible

    def _event_button1(self, item: dict):
        # this is now running on its own thread
        # this call is also protected by a lock
        logger.info(item)

    def cb_button1(self, sender, app_data, user_data):
        # this is called on the client thread, in this case the DPG thread
        logger.info(f"sender: {sender} {app_data} {user_data}")
        item_dict = {"type": self.EVENT_CB_BUTTON1,
                     "cb": dict(s=sender, a=app_data, u=user_data),
                     "from": "cb_button1"}
        self.enqueue(item_dict)

    def subc_event_handler(self, item):
        if item["type"] == self.EVENT_CB_BUTTON1:
            self._event_button1(item)
            return True

        # elif item["type"] == self.EVENT_something:
        #     ... code ...
        #     return True

        else:
            return False


dpg.create_context()
dpg.create_viewport(height=200, width=200)
dpg.setup_dearpygui()

worker = Worker()

with dpg.window(label="Example", height=100, width=100):
    dpg.add_text("Hello world")

    # NOTE: the callback happens on the worker thread
    dpg.add_button(tag="b1", label="Button1", callback=worker.cb_button1)

dpg.show_viewport()
dpg.start_dearpygui()

# shut thread down properly
worker.shutdown()

dpg.destroy_context()

