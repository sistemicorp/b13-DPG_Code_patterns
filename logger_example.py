import dearpygui.dearpygui as dpg
from threading import Timer
from logger_klass import Logger

dpg.create_context()
dpg.create_viewport()
dpg.setup_dearpygui()


WINDOW_WIDTH = 600
with dpg.window(label="Logger", width=WINDOW_WIDTH, height=600):
    mylogger = Logger("mylogger")


def _timer_cb():
    """ This timer simulates log lines being sent
    - diffent sources and log levels are used
    :return:
    """
    global _tmr
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

    if count < 100:  # stops the simulation
        _tmr = Timer(0.2, _timer_cb)
        _tmr.start()

    else:
        mylogger.log("NOW", "MAIN", "This is the end of the logging", mylogger.LOG_LEVEL_INFO)


count = 0
_tmr = Timer(1, _timer_cb)
_tmr.start()

dpg.show_viewport()
dpg.start_dearpygui()
_tmr.cancel()
dpg.destroy_context()

