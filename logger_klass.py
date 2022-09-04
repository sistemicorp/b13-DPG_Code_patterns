import dearpygui.dearpygui as dpg
from threading import Lock, Thread, Event
import queue
import traceback
import time


class Logger(Thread):
    """
    Creates a Window to display log lines.
    - log lines have
      - timestamp, could be anything really, an integer, or epoch, must be string
      - source, a string representing the source library or module, could always be "main"
      - log level, see LOG_LEVEL_*
      - message, a string to display

    """

    LOG_LEVEL_TRACE = 0
    LOG_LEVEL_DEBUG = 1
    LOG_LEVEL_INFO = 2
    LOG_LEVEL_WARN = 3
    LOG_LEVEL_ERROR = 4
    LOG_LEVEL_CRITICAL = 5
    LOG_LEVEL_COMBO_DEFAULT = "INFO"

    ROW_IDX_TIMESTAMP = 0
    ROW_IDX_SOURCE = 1
    ROW_IDX_LOGLEVEL = 2
    ROW_IDX_MSG = 3

    TABLE_FONT_WIDTH = 8
    TABLE_COL_TIMESTAMP_WIDTH = 6  # num characters
    TABLE_COL_SOURCE_WIDTH = 5
    TABLE_COL_LOGLEVEL_WIDTH = 7
    TABLE_COL_MSG_WIDTH = 80
    TABLE_FIXED_WIDTH = TABLE_COL_TIMESTAMP_WIDTH + TABLE_COL_SOURCE_WIDTH + TABLE_COL_LOGLEVEL_WIDTH

    TABLE_FONT_HEIGHT = 8

    EVENT_SHUTDOWN = "EVENT_SHUTDOWN"
    EVENT_LOG = "EVENT_LOG"
    EVENT_EXPORT = "EVENT_EXPORT"
    EVENT_CLEAR = "EVENT_CLEAR"

    # colors found by trial and error from: https://rgbacolorpicker.com/
    SOURCE_ROW_COLORBG = [
        (27, 76, 136, 80), (52, 63, 77, 80), (145, 116, 70, 80), (246, 250, 197, 80),
        (133, 144, 0, 80), (121, 44, 80, 80), (243, 129, 182, 60), (3, 137, 130, 80),
        (136, 248, 167, 80), (79, 150, 146, 80), (5, 172, 52, 80), (175, 31, 31, 80)
    ]

    def __init__(self, label="Logger", tag_root="logger", export_filename="log.txt", loggerIn=None):
        super(Logger, self).__init__()

        class StubLogger(object):
            """ stubb out logger if none is provided"""
            def info(self, *args, **kwargs): pass
            def error(self, *args, **kwargs): pass
            def debug(self, *args, **kwargs): pass
            def warning(self, *args, **kwargs): pass
            def critical(self, *args, **kwargs): pass

        if loggerIn: self.logger = loggerIn
        else: self.logger = StubLogger()

        self._tag_root = tag_root
        self._tags = []
        self._export_filename = export_filename
        self._table_width = 0  # tracks and creates horizontal scrollbar
        self._scrolling = True
        self._table_rows = 0
        self._log_level = self.LOG_LEVEL_INFO
        self._lock = Lock()
        self._q = queue.Queue()
        self._stop_event = Event()
        self._sources = {}  # keys are from SOURCE
                            # {"show": True, "theme": <obj>}

        self._rows = []

        self.name = tag_root
        self.start()

        self.LOG_LEVEL_MAP = {
            self.LOG_LEVEL_TRACE:    {"str": "TRACE", "color": (0, 255, 0, 255)},
            self.LOG_LEVEL_DEBUG:    {"str": "DEBUG", "color": (64, 128, 255, 255)},
            self.LOG_LEVEL_INFO:     {"str": "INFO",  "color": (255, 255, 255, 255)},
            self.LOG_LEVEL_WARN:     {"str": "WARN",  "color": (255, 255, 0, 255)},
            self.LOG_LEVEL_ERROR:    {"str": "ERROR", "color": (255, 0, 0, 255)},
            self.LOG_LEVEL_CRITICAL: {"str": "CRTCL", "color": (255, 0, 0, 255)},
        }

        for k, v in self.LOG_LEVEL_MAP.items():
            with dpg.theme() as theme:
                with dpg.theme_component(0):
                    dpg.add_theme_color(dpg.mvThemeCol_Text, v["color"])

            self.LOG_LEVEL_MAP[k]["theme"] = theme

        with dpg.group(horizontal=True):

            dpg.add_button(label="Clear",
                           callback=lambda s, u, a: self._cb_button_clear(s, u, a),
                           tag=self.__tag("button_clear"))

            dpg.add_button(label="Export",
                           callback=lambda s, u, a: self._cb_button_export(s, u, a),
                           tag=self.__tag("button_export"))

            dpg.add_button(label="Scroll",
                           callback=lambda s, u, a: self._cb_button_scroll(s, u, a),
                           tag=self.__tag("button_scroll"))

            log_levels = [v["str"] for k, v in self.LOG_LEVEL_MAP.items()]
            dpg.add_combo(log_levels,
                          label="",
                          width=80,
                          tag=self.__tag("combo_level"),
                          default_value=self.LOG_LEVEL_COMBO_DEFAULT,
                          height_mode=dpg.mvComboHeight_Largest,
                          callback=lambda s, u, a: self._cb_combo_level(s, u, a))

            dpg.add_combo(items=[],
                          width=80,
                          default_value="Sources",
                          tag=self.__tag("combo_sources"),
                          callback=lambda s, u, a: self._cb_combo_sources(s, u, a))

        with dpg.child_window(label=label,
                              tag=self.__tag("child_window"),
                              horizontal_scrollbar=True,
                              width=-1,
                              height=-1,
                              tracked=True,
                              track_offset=-1.0):

            with dpg.table(header_row=False,
                           tag=self.__tag("table")):

                dpg.add_table_column(width=self.TABLE_COL_TIMESTAMP_WIDTH * self.TABLE_FONT_WIDTH,
                                     width_fixed=True, no_resize=True,
                                     tag=self.__tag("col_timestamp"))  # timestamp
                dpg.add_table_column(width=self.TABLE_COL_SOURCE_WIDTH * self.TABLE_FONT_WIDTH,
                                     width_fixed=True, no_resize=True,
                                     tag=self.__tag("col_source"))  # source
                dpg.add_table_column(width=self.TABLE_COL_LOGLEVEL_WIDTH * self.TABLE_FONT_WIDTH,
                                     width_fixed=True, no_resize=True,
                                     tag=self.__tag("col_loglevel"))  # log level
                dpg.add_table_column(width=self.TABLE_COL_MSG_WIDTH * self.TABLE_FONT_WIDTH,
                                     tag=self.__tag("col_msg"))  # message string

    def __q(self, item_dict: dict):
        self.logger.debug(item_dict)
        self._q.put(item_dict)

    def __tag(self, item):
        """
        create a tag, append to list of known, and return it
        :param item:
        :return:
        """
        tag = f"""{self._tag_root}_{item}"""
        if tag not in self._tags:
            self._tags.append(tag)
        return tag

    def _create_listbox_sources_items(self):
        listbox_sources = ["ALL_ON", "ALL_OFF"]
        for k, v in self._sources.items():
            if v["show"]:
                item_string = f"{k} ON"
            else:
                item_string = f"{k} OFF"

            listbox_sources.append(item_string)

        return listbox_sources

    def _show_source(self, source):
        if source not in self._sources:
            self._sources[source] = {"show": True}
            # update the listbox
            listbox_sources = self._create_listbox_sources_items()
            dpg.configure_item(self.__tag("combo_sources"), items=listbox_sources)
            idx = (len(self._sources) - 1) % len(self.SOURCE_ROW_COLORBG)  # recycle colors if too many
            self._sources[source]["color"] = self.SOURCE_ROW_COLORBG[idx]

        return self._sources[source]["show"]

    def _add_table_row(self, timestamp, source, log_level, msg):
        if not isinstance(timestamp, str):
            timestamp = str(timestamp)

        r = [timestamp, source, log_level, msg]
        self._rows.append(r)

        show_row = self._show_source(source)
        if log_level < self._log_level:
            show_row = False

        def _set_table_width(row_items):
            # causes horizontal scroll bar to appear if necessary
            w1 = (self.TABLE_FIXED_WIDTH + len(row_items[self.ROW_IDX_MSG])) * self.TABLE_FONT_WIDTH
            w2 = (self.TABLE_FIXED_WIDTH + self.TABLE_COL_MSG_WIDTH) * self.TABLE_FONT_WIDTH
            w = max(w1, w2)
            if w > self._table_width:
                self._table_width = w
                dpg.configure_item(self.__tag("table"), width=w)

        theme = self.LOG_LEVEL_MAP[log_level]["theme"]

        dpg.push_container_stack(self.__tag("table"))
        with dpg.table_row(height=self.TABLE_FONT_HEIGHT,
                           user_data=(log_level, source),
                           show=show_row,
                           tag=self.__tag(f"row_{self._table_rows}")):

            # NOTE: tried to set the column widths on selectable, but it breaks the
            #       span all coulmns when mouse is selecting... choice between correct
            #       selection or initial column widths.  As it is now, the columns will
            #       expand as required.

            sel = dpg.add_selectable(label=timestamp,
                                     span_columns=True,
                                     callback=lambda s, u, a: self._cb_table_row(s, u, a),
                                     user_data=(self.ROW_IDX_TIMESTAMP, self._table_rows))
            dpg.bind_item_theme(sel, theme)

            sel = dpg.add_selectable(label=source,
                                     span_columns=True,
                                     callback=lambda s, u, a: self._cb_table_row(s, u, a),
                                     user_data=(self.ROW_IDX_SOURCE, self._table_rows))
            dpg.bind_item_theme(sel, theme)

            lvl = self.LOG_LEVEL_MAP[log_level]["str"]
            sel = dpg.add_selectable(label=f"[{lvl:5s}]",
                                     span_columns=True,
                                     callback=lambda s, u, a: self._cb_table_row(s, u, a),
                                     user_data=(self.ROW_IDX_LOGLEVEL, self._table_rows))
            dpg.bind_item_theme(sel, theme)

            sel = dpg.add_selectable(label=msg,
                                     span_columns=True,
                                     callback=lambda s, u, a: self._cb_table_row(s, u, a),
                                     user_data=(self.ROW_IDX_MSG, self._table_rows))
            dpg.bind_item_theme(sel, theme)

        dpg.highlight_table_row(self.__tag("table"), self._table_rows, self._sources[source]["color"])

        self._table_rows += 1

        dpg.pop_container_stack()
        if self._scrolling:
            dpg.set_y_scroll(self.__tag("child_window"), -1.0)  # needed to keep scroll at bottom

        _set_table_width(r)

    def _cb_table_row(self, sender, app_data, user_data):
        self.logger.info(f"{sender} {app_data} {user_data}")

    def _cb_combo_sources(self, sender, app_data, user_data):
        self.logger.info(f"{sender} {app_data} {user_data}")

        if app_data == "ALL_ON":
            for k, v in self._sources.items():
                v["show"] = True

        elif app_data == "ALL_OFF":
            for k, v in self._sources.items():
                v["show"] = False

        else:
            source = app_data.split(" ")[0]
            self._sources[source]["show"] = not self._sources[source]["show"]

        self.__update_show_rows()
        listbox_sources = self._create_listbox_sources_items()
        dpg.configure_item(self.__tag("combo_sources"), items=listbox_sources)
        dpg.set_value(self.__tag("combo_sources"), "Sources")

    def _cb_button_scroll(self, sender, app_data, user_data):
        self.logger.info(f"{sender} {app_data} {user_data}")
        self._scrolling = not self._scrolling

    def _clear_logger(self, clear_sources):
        if clear_sources:
            self._sources = {}
            listbox_sources = self._create_listbox_sources_items()
            dpg.configure_item(self.__tag("combo_sources"), items=listbox_sources)
            dpg.set_value(self.__tag("combo_sources"), "Sources")

        for i in range(self._table_rows):
            tag = self.__tag(f"row_{i}")
            dpg.delete_item(tag)

        self._table_rows = 0
        self._rows = []

    def _event_clear(self, item):
        self._clear_logger(clear_sources=True)

    def _cb_button_clear(self, sender, app_data, user_data):
        self.logger.info(f"{sender} {app_data} {user_data}")
        item_dict = {"type": self.EVENT_CLEAR}
        self.__q(item_dict)

    def _cb_button_export(self, sender, app_data, user_data):
        self.logger.info(f"{sender} {app_data} {user_data}")
        item_dict = {"type": self.EVENT_EXPORT}
        self.__q(item_dict)

    def _event_export(self, item):
        try:
            with open(self._export_filename, "w") as f:
                for i in range(self._table_rows):
                    row_tag = self.__tag(f"row_{i}")
                    r = self._rows[i]
                    if self._is_row_showing(row_tag):
                        line = f"{r[self.ROW_IDX_TIMESTAMP]},{r[self.ROW_IDX_SOURCE]},{r[self.ROW_IDX_LOGLEVEL]},{r[self.ROW_IDX_MSG]}"
                        print(line, file=f)

        except Exception as e:
            self.logger.error(e)
            return

        with dpg.window(label="Log Exported",
                        width=200,
                        height=50,
                        modal=True,
                        pos=(100, 100),
                        no_collapse=True,
                        no_move=True,
                        no_resize=True):

            dpg.add_text(default_value=self._export_filename)

    def _is_row_showing(self, row_tag):
        row_level, row_source = dpg.get_item_user_data(row_tag)
        source_show = self._sources[row_source]["show"]
        if row_level < self._log_level or not source_show:
            return False

        return True

    def __update_show_rows(self):
        with self._lock:
            for i in range(self._table_rows):
                row_tag = self.__tag(f"row_{i}")
                if self._is_row_showing(row_tag):
                    dpg.show_item(row_tag)
                else:
                    dpg.hide_item(row_tag)

    def _cb_combo_level(self, sender, app_data, user_data):
        self.logger.info(f"{sender} {app_data} {user_data}")
        for k, v in self.LOG_LEVEL_MAP.items():
            if v["str"] == app_data:
                self._log_level = k
                break

        self.__update_show_rows()

    def set_export_filename(self, filename):
        self._export_filename = filename

    def get_tags(self):
        """
        Get all the tags created in this logger
        :return:
        """
        return self._tags

    def set_log_level(self, level=LOG_LEVEL_INFO):
        self._log_level = level
        self.__update_show_rows()

    def clear(self, clear_sources=False):
        """ Clear all the log lines

        :param clear_sources: [True|False], when set clears all known sources
        :return: None
        """
        self._clear_logger(clear_sources)

    def _event_log(self, item):
        self._add_table_row(item["timestamp"],
                            item["source"],
                            item["level"],
                            item["message"])

    def log_trace(self, timestamp, source, message):
        item_dict = {"type": self.EVENT_LOG,
                     "timestamp": timestamp,
                     "level": self.LOG_LEVEL_TRACE,
                     "source": source,
                     "message": message}
        self.__q(item_dict)

    def log_debug(self, timestamp, source, message):
        item_dict = {"type": self.EVENT_LOG,
                     "timestamp": timestamp,
                     "level": self.LOG_LEVEL_DEBUG,
                     "source": source,
                     "message": message}
        self.__q(item_dict)

    def log_info(self, timestamp, source, message):
        """ Log at Info level

        :param timestamp: string, or something that is convertible to string
        :param source: string
        :param message: string
        :return: None
        """
        item_dict = {"type": self.EVENT_LOG,
                     "timestamp": timestamp,
                     "level": self.LOG_LEVEL_INFO,
                     "source": source,
                     "message": message}
        self.__q(item_dict)

    def log_warn(self, timestamp, source, message):
        item_dict = {"type": self.EVENT_LOG,
                     "timestamp": timestamp,
                     "level": self.LOG_LEVEL_WARN,
                     "source": source,
                     "message": message}
        self.__q(item_dict)

    def log_error(self, timestamp, source, message):
        item_dict = {"type": self.EVENT_LOG,
                     "timestamp": timestamp,
                     "level": self.LOG_LEVEL_ERROR,
                     "source": source,
                     "message": message}
        self.__q(item_dict)

    def log_critical(self, timestamp, source, message):
        item_dict = {"type": self.EVENT_LOG,
                     "timestamp": timestamp,
                     "level": self.LOG_LEVEL_CRITICAL,
                     "source": source,
                     "message": message}
        self.__q(item_dict)

    def log(self, timestamp, source, message, level=LOG_LEVEL_INFO):
        item_dict = {"type": self.EVENT_LOG,
                     "timestamp": timestamp,
                     "level": level,
                     "source": source,
                     "message": message}
        self.__q(item_dict)

    def stopped(self):
        return self._stop_event.is_set()

    def shutdown(self):
        item_dict = {"type": self.EVENT_SHUTDOWN}
        self.__q(item_dict)

    def _event_shutdown(self):
        self._stop_event.set()

    def run(self):
        self.logger.info(f"{self._tag_root} run thread started")
        while not self.stopped():

            try:
                item = self._q.get(block=True)
                self.logger.debug(item)

                with self._lock:
                    if item["type"] == self.EVENT_LOG:
                        self._event_log(item)

                    elif item["type"] == self.EVENT_CLEAR:
                        self._event_clear(item)

                    elif item["type"] == self.EVENT_EXPORT:
                        self._event_export(item)

                    elif item["type"] == self.EVENT_SHUTDOWN:
                        self._event_shutdown()

                    else:
                        self.logger.error("Unknown event: {}".format(item["type"]))

            except queue.Empty:
                pass
            except Exception as e:
                self.logger.error("Error processing event {}, {}".format(e, item["type"]))
                traceback.print_exc()

            time.sleep(0)  # allow other threads to run if any, in the case that the queue is full

        self.logger.info(f"{self._tag_root} run thread stopped")
