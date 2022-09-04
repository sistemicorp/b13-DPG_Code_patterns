import dearpygui.dearpygui as dpg
from logger_klass import Logger

import logging
logging.basicConfig(level=logging.INFO)

dpg.create_context()
dpg.create_viewport()
dpg.setup_dearpygui()


WINDOW_WIDTH = 600
with dpg.window(label="Logger", width=WINDOW_WIDTH, height=600):
    mylogger = Logger("mylogger", loggerIn=logging)


count = 0
source = ["MAIN", "AAA", "BBB", "CCC", "DDD", "EEE", "FFF", "GGG", "HHH", "III",
          "JJJ", "KKK", "LLL", "MMM"]
msg = "Now is the time"
for s in source:
    mylogger.log_trace(count, s, msg)
    mylogger.log_debug(count, s, msg)
    mylogger.log_info(count, s, msg)
    mylogger.log_warn(count, s, msg)
    mylogger.log_error(count, s, msg)
    mylogger.log_critical(count, s, msg)


dpg.show_viewport()
dpg.start_dearpygui()

mylogger.shutdown()

dpg.destroy_context()

