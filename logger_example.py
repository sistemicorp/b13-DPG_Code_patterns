import dearpygui.dearpygui as dpg
from threading import Timer
from logger_klass import Logger

import logging
logger = logging.getLogger()
FORMAT = "%(asctime)s: %(funcName)25s %(levelname)-5.5s :%(lineno)4s: %(message)s"
formatter = logging.Formatter(FORMAT)
consoleHandler = logging.StreamHandler()
consoleHandler.setFormatter(formatter)
logger.addHandler(consoleHandler)
logger.setLevel(logging.INFO)


dpg.create_context()
dpg.create_viewport()
dpg.setup_dearpygui()


WINDOW_WIDTH = 600
with dpg.window(label="Logger", width=WINDOW_WIDTH, height=600):
    mylogger = Logger("mylogger")


def _timer_cb():
    global _tmr
    global _text_accum
    global count
    count += 1

    source = "MAIN"
    if (count % 4) == 0:
        source = "UART"

    msg = f"count {count}" + "**" * count
    if (count % 10) == 0:
        mylogger.log_error(count, source, msg)

    elif (count % 12) == 0:
        mylogger.log_warn(count, source, msg)

    elif (count % 13) == 0:
        mylogger.log_debug(count, source, msg)

    elif (count % 14) == 0:
        mylogger.log_trace(count, source, msg)

    elif (count % 15) == 0:
        mylogger.log_critical(count, source, msg)

    else:
        mylogger.log_info(count, source, msg)

    if count < 150:
        _tmr = Timer(0.5, _timer_cb)
        _tmr.start()


count = 0
_text_accum = "Now is the time\n"

_tmr = Timer(1, _timer_cb)
_tmr.start()

dpg.show_viewport()

#dpg.show_style_editor()


dpg.start_dearpygui()

_tmr.cancel()

dpg.destroy_context()

