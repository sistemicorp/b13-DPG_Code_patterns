# -*- coding: utf-8 -*-
"""
Martin Guthrie

This code pattern demonstrates a toggle button with theme

"""
import os
import dearpygui.dearpygui as dpg
import logging
logger = logging.getLogger()
FORMAT = "%(asctime)s: %(filename)22s %(funcName)25s %(levelname)-5.5s :%(lineno)4s: %(message)s"
formatter = logging.Formatter(FORMAT)
consoleHandler = logging.StreamHandler()
consoleHandler.setFormatter(formatter)
logger.addHandler(consoleHandler)
logger.setLevel(logging.INFO)


dpg.create_context()
dpg.create_viewport(height=200, width=200)
dpg.setup_dearpygui()


class ID:
    """  All DPG IDs are created here
    """

    ID = {

        # other IDs would be listed here

        "button": {
            "run": dpg.generate_uuid(),  # actually a ToggleButton
        },
        "theme": {
            "togglebutton_run_enabled": dpg.generate_uuid(),
            "togglebutton_run_active": dpg.generate_uuid(),
            "togglebutton_run_disabled": dpg.generate_uuid(),
        },
        "obj_ToggleButton": {
            # dynamically added
        }
    }

    def add_object(self, obj, key, value):
        if obj not in self.ID:
            raise ValueError(f"{obj} not in ID")

        self.ID[obj][key] = value

    def name(self, id):
        for key in self.ID:
            for kkey in self.ID[key]:
                if self.ID[key][kkey] == id:
                    return f"{key}.{kkey}"

        return f"not.found_{id}"

    def show_all(self):
        for key in self.ID:
            for kkey in self.ID[key]:
                logger.info(f"{key}.{kkey} {self.ID[key][kkey]}")


id = ID()


class Fonts(object):

    # fancy path stuff supports Nuitka builds
    f = os.path.join(os.path.dirname(__file__), "assets/UbuntuMono-BI.ttf")

    with dpg.font_registry():
        default_big = dpg.add_font(f, 30)
        default = dpg.add_font(f, 15)
        default_small = dpg.add_font(f, 12)

        run = dpg.add_font(f, 24)


class ThemeToggleRun(object):
    """ Theme for Toggle Buttons
    - used by Run, Single, and Connect

    """

    name = "run"

    with dpg.theme(tag=id.ID["theme"][f"togglebutton_{name}_enabled"]):  # not active
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button, (66, 245, 126))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (160, 240, 144))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (160, 240, 144))
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 15)
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 9, 9)
            dpg.add_theme_color(dpg.mvThemeCol_Text, (34, 27, 227))

    with dpg.theme(tag=id.ID["theme"][f"togglebutton_{name}_active"]):  # shows STOP, and red for stop
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button, (245, 159, 159))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (245, 159, 159))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (245, 159, 159))
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 15)
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 9, 9)

    with dpg.theme(tag=id.ID["theme"][f"togglebutton_{name}_disabled"]):
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button, (161, 168, 160))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (161, 168, 160))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (161, 168, 160))
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 15)
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 9, 9)

    font_enabled = Fonts.run
    font_disabled = Fonts.run
    font_active = Fonts.run


class ToggleButton(object):

    STATE_ENABLED = "STATE_ENABLED"
    STATE_DISABLED = "STATE_DISABLED"
    STATE_ACTIVE = "STATE_ACTIVE"

    def __init__(self, name, themeKlass, **kwargs):

        if name not in id.ID["button"]:
            raise ValueError("{} not in ids".format(name))

        kwargs["tag"] = self._tag = id.ID["button"][name]

        self._state = kwargs.get("state", self.STATE_ENABLED)
        self._cb = kwargs.get("callback", None)

        self._attrb = {
            self.STATE_ENABLED: {
                "theme": id.ID["theme"]["togglebutton_{}_enabled".format(themeKlass.name)],
                "font": themeKlass.font_enabled
            },
            self.STATE_DISABLED: {
                "theme": id.ID["theme"]["togglebutton_{}_disabled".format(themeKlass.name)],
                "font": themeKlass.font_disabled
            },
            self.STATE_ACTIVE: {
                "theme": id.ID["theme"]["togglebutton_{}_active".format(themeKlass.name)],
                "font": themeKlass.font_active
            },
        }

        if isinstance(kwargs["label"], str):
            self._attrb[self.STATE_ENABLED]["label"] = kwargs["label"]
            self._attrb[self.STATE_ACTIVE]["label"] = kwargs["label"]
            self._attrb[self.STATE_DISABLED]["label"] = kwargs["label"]
        elif isinstance(kwargs["label"], list):
            self._attrb[self.STATE_ENABLED]["label"] = kwargs["label"][0]
            self._attrb[self.STATE_ACTIVE]["label"] = kwargs["label"][1]
            self._attrb[self.STATE_DISABLED]["label"] = kwargs["label"][2]

        kwargs["callback"] = lambda s, u, a: self.__cb(s, u, a)
        kwargs["user_data"] = self

        dpg.add_button(**kwargs)
        self.set_state()

    def __cb(self, sender, app_data, user_data):
        if self._state == self.STATE_ENABLED:
            self.set_state(self.STATE_ACTIVE)
        elif self._state == self.STATE_ACTIVE:
            self.set_state(self.STATE_ENABLED)
        elif self._state == self.STATE_DISABLED:
            # could return here and not call the widget's callback, because
            # the button is disabled, however, lets do it for most flexibility
            pass
        else:
            logger.error("ERROR")

        if self._cb:
            self._cb(sender, app_data, user_data)

    def trigger_callback(self):
        self.__cb(self._tag, None, None)

    def set_state(self, state=STATE_ENABLED):
        self._state = state
        self.set_label(self._attrb[self._state]["label"])
        dpg.bind_item_theme(self._tag, self._attrb[self._state]["theme"])
        dpg.bind_item_font(self._tag, self._attrb[self._state]["font"])

    def set_label(self, label):
        dpg.set_item_label(self._tag, label)

    def get_state(self):
        return self._state

    def get_item(self):
        return self._tag


def cb_button1(sender, app_data, user_data):
    logger.info(f"B1 sender: {sender} {app_data} {user_data}")
    logger.info(f"   state : {user_data.get_state()}")


with dpg.window(label="Example", height=100, width=150):
    dpg.add_text("Hello world")

    _run = ToggleButton(name="run",
                        themeKlass=ThemeToggleRun,
                        label=["RUN", "STOP", "RUN"],
                        width=100,
                        callback=cb_button1)

dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()


