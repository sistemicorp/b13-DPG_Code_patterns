import dearpygui.dearpygui as dpg
from threading import Lock, Thread


class Logger:

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
    TABLE_COL_MSG_WIDTH = 20
    TABLE_FIXED_WIDTH = TABLE_COL_TIMESTAMP_WIDTH + TABLE_COL_SOURCE_WIDTH + TABLE_COL_LOGLEVEL_WIDTH

    TABLE_FONT_HEIGHT = 10

    def __init__(self, label="Logger", tag_root="logger", export_filename="log.txt", loggerIn=None):

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
        self._table_rows = 0
        self._scrolling = True
        self._log_level = self.LOG_LEVEL_INFO
        self._lock = Lock()
        self._sources = {}

        self._rows = []

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
                           row_background=True,
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
        listbox_sources = []
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

        return self._sources[source]["show"]

    def _add_table_row(self, timestamp, source, log_level, msg):
        with self._lock:
            r = [timestamp, source, log_level, msg]
            self._rows.append(r)

            show_row = self._show_source(source)
            if log_level < self._log_level:
                show_row = False

            def _set_table_width(row_items):
                # causes horizontal scroll bar to appear if necessary
                w = (self.TABLE_FIXED_WIDTH + len(row_items[self.ROW_IDX_MSG])) * self.TABLE_FONT_WIDTH
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

            self._table_rows += 1

            dpg.pop_container_stack()
            if self._scrolling:
                dpg.set_y_scroll(self.__tag("child_window"), -1.0)  # needed to keep scroll at bottom

            _set_table_width(r)

    def _cb_table_row(self, sender, app_data, user_data):
        self.logger.info(f"{sender} {app_data} {user_data}")

    def _cb_combo_sources(self, sender, app_data, user_data):
        self.logger.info(f"{sender} {app_data} {user_data}")
        source = app_data.split(" ")[0]
        self._sources[source]["show"] = not self._sources[source]["show"]
        self.__update_show_rows()
        listbox_sources = self._create_listbox_sources_items()
        dpg.configure_item(self.__tag("combo_sources"), items=listbox_sources)
        dpg.set_value(self.__tag("combo_sources"), "Sources")

    def _cb_button_scroll(self, sender, app_data, user_data):
        self.logger.info(f"{sender} {app_data} {user_data}")
        self._scrolling = not self._scrolling

    def _cb_button_export(self, sender, app_data, user_data):
        self.logger.info(f"{sender} {app_data} {user_data}")

        def _thread_export():
            try:
                with open(self._export_filename, "w") as f:
                    with self._lock:
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

        thrd = Thread(None, _thread_export)
        thrd.start()

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

    def log_trace(self, timestamp, source, message):
        self._add_table_row(timestamp, source, self.LOG_LEVEL_TRACE, message)

    def log_debug(self, timestamp, source, message):
        self._add_table_row(timestamp, source, self.LOG_LEVEL_DEBUG, message)

    def log_info(self, timestamp, source, message):
        self._add_table_row(timestamp, source, self.LOG_LEVEL_INFO, message)

    def log_warn(self, timestamp, source, message):
        self._add_table_row(timestamp, source, self.LOG_LEVEL_WARN, message)

    def log_error(self, timestamp, source, message):
        self._add_table_row(timestamp, source, self.LOG_LEVEL_ERROR, message)

    def log_critical(self, timestamp, source, message):
        self._add_table_row(timestamp, source, self.LOG_LEVEL_CRITICAL, message)

    def log(self, timestamp, source, message, level=LOG_LEVEL_INFO):
        self._add_table_row(timestamp, source, level, message)

