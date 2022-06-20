import dearpygui.dearpygui as dpg

dpg.create_context()
dpg.create_viewport(height=400, width=600)
dpg.setup_dearpygui()


with dpg.window(label="Example", height=100, width=400):
    dpg.add_text("Hello world")


class Table:
    """ (Another) Smart Table class
    - meant to be sub-classed
    - automatically creates tags for each cell
    - cells can be address by row, col, or by a name provided at creation

    """
    w = None
    h = None
    t = [[]]
    tags = None

    def __init__(self, name="t", **kwargs):

        self._tag_root = f"{name}"
        self._kwargs = kwargs

    def table(self, t):
        self.t = t

    def tags(self, tags):
        self.tags = tags

    def create(self):
        with dpg.table(**self._kwargs, tag=self._tag_root):

            if self._kwargs.get("header_row", False) and self.h:
                if self.w:
                    width = sum(self.w) + len(self.w) * 10
                    dpg.configure_item(self._tag_root, width=width)
                    for h, w in zip(self.h, self.w):
                        dpg.add_table_column(label=h, width_fixed=True, init_width_or_weight=w)
                else:
                    for h in self.h:
                        dpg.add_table_column(label=h)

            else:
                dpg.add_table_column()

            r, c = 0, 0
            for row in self.t:
                with dpg.table_row():
                    c = 0
                    for i in row:
                        tag = self.__tag(r, c)
                        if isinstance(i, str):
                            dpg.add_text(i, tag=tag)
                        elif isinstance(i, int):
                            dpg.add_input_int(default_value=i, width=-1, step=0, tag=tag)
                        elif isinstance(i, float):
                            dpg.add_input_float(default_value=i, width=-1, step=0, tag=tag)
                        elif i is None:
                            dpg.add_text("", tag=tag)

                        c += 1
                r += 1

    def __tag(self, r, c):
        if self.tags is None or self.tags[r][c] is None:
            return f"{self._tag_root}_{r}_{c}"
        return f"{self._tag_root}_{self.tags[r][c]}"

    def __get_rc_from_name(self, name):
        r, c = 0, 0
        for row in self.tags:
            c = 0
            for item in row:
                if item == name:
                    return r, c
                c += 1
            r += 1
        return -1, -1

    def set_cell_value(self, row, col, value):
        tag = self.__tag(row, col)
        dpg.set_value(tag, value)

    def set_cell_value_by_name(self, name, value):
        tag = f"{self._tag_root}_{name}"
        dpg.set_value(tag, value)

    def set_cell_values_by_name(self, n_v_list: list):
        for (name, value) in n_v_list:
            tag = f"{self._tag_root}_{name}"
            dpg.set_value(tag, value)

    def get_cell_value(self, row, col):
        tag = self.__tag(row, col)
        return dpg.get_value(tag)

    def get_cell_value_by_name(self, name):
        tag = f"{self._tag_root}_{name}"
        return dpg.get_value(tag)

    def highlight_cell_by_name(self, name, color=(0, 0, 255, 100)):
        r, c = self.__get_rc_from_name(name)
        if r == -1 or c == -1:
            raise ValueError(f"{name} not valid tag")
        dpg.highlight_table_cell(self._tag_root, r, c, color=color)


class Stats(Table):

    # widths
    w = [60, 80, 80, 80, 60]

    # header
    h = ["Item", "   Min", "   AVG", "   Max", " Units"]     # header

    # Labels and default values of the table
    t = [
        ["Current",    "{:10,.3f}".format(0.0),   "{:10,.3f}".format(0.0),   "{:10,.3f}".format(0.0),   "  mA"],
        ["Coulombs",    None,   "{:10,.3f}".format(0.0),    None,   "  mC"],
    ]

    # a list of tag alias names, to address a cell by its functional name
    # for more readable code
    # - does not include the header row
    # - use None for no alias(es)
    tags = [
        [None,  "cur_min",   "cur_avg",   "cur_max",   None],
        [None,       None,   "clb_avg",        None,   None],
    ]
    # tags = None

    def __init__(self, name="t", **kwargs):
        super().__init__(name, **kwargs)


with dpg.window(label="Plotted Stats", pos=(100, 120),
                height=130, width=400, collapsed=True, no_close=True):

    plotted_stats_table = Stats("tbl_plotted_stats",
                                header_row=True,
                                row_background=True,
                                borders_innerH=True,
                                borders_outerH=True,
                                borders_innerV=True,
                                borders_outerV=True)
    plotted_stats_table.create()


plotted_stats_table.set_cell_value(0, 1, 123.4)
plotted_stats_table.set_cell_value_by_name("clb_avg", 123.4)

dpg.highlight_table_cell("tbl_plotted_stats", 1, 2, [0, 0, 255, 100])
plotted_stats_table.highlight_cell_by_name("cur_avg", [255, 0, 0, 100])

dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()
