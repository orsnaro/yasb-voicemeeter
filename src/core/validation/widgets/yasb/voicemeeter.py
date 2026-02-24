from pydantic import Field

from core.validation.widgets.base_model import (
    AnimationConfig,
    CallbacksConfig,
    CustomBaseModel,
    KeybindingConfig,
    PaddingConfig,
    ShadowConfig,
)


class AppIconsConfig(CustomBaseModel):
    toggle_down: str = "\uf078"
    toggle_up: str = "\uf077"


class AudioMenuConfig(CustomBaseModel):
    blur: bool = True
    round_corners: bool = True
    round_corners_type: str = "normal"
    border_color: str = "System"
    alignment: str = "right"
    direction: str = "down"
    distance: int = 6  # deprecated
    offset_top: int = 6
    offset_left: int = 0
    show_apps: bool = False
    show_app_labels: bool = False
    show_app_icons: bool = True
    show_apps_expanded: bool = False
    app_icons: AppIconsConfig = AppIconsConfig()


class ProgressBarConfig(CustomBaseModel):
    enabled: bool = False
    size: int = Field(default=18, ge=8, le=64)
    thickness: int = Field(default=3, ge=1, le=10)
    color: str | list[str] = "#00C800"
    background_color: str = "#3C3C3C"
    position: str = "left"
    animation: bool = True


class VoicemeeterCallbacksConfig(CallbacksConfig):
    on_left: str = "toggle_volume_menu"
    on_right: str = "toggle_mute"


class VoicemeeterConfig(CustomBaseModel):
    label: str = "{volume[percent]}%"
    label_alt: str = "{volume[percent]}%"
    class_name: str = ""
    vmcli_exe_path: str = (
        "c:\\Users\\OmarPc\\repo_My_configs_cmder\\cmder\\bin\\vmcli.exe"
    )
    main_output_bus: int = Field(default=0, ge=0, le=3)
    synced_outputs_count: int = Field(default=2, ge=1, le=4)
    mute_text: str = "mute"
    tooltip: bool = True
    scroll_step: int = Field(default=2, ge=1, le=100)
    slider_beep: bool = True
    volume_icons: list[str] = [
        "\ueee8",  # Icon for muted
        "\uf026",  # Icon for 0-10% volume
        "\uf027",  # Icon for 11-30% volume
        "\uf027",  # Icon for 31-60% volume
        "\uf028",  # Icon for 61-100% volume
    ]
    audio_menu: AudioMenuConfig = AudioMenuConfig()
    animation: AnimationConfig = AnimationConfig()
    container_padding: PaddingConfig = PaddingConfig()
    label_shadow: ShadowConfig = ShadowConfig()
    container_shadow: ShadowConfig = ShadowConfig()
    progress_bar: ProgressBarConfig = ProgressBarConfig()
    keybindings: list[KeybindingConfig] = []
    callbacks: VoicemeeterCallbacksConfig = VoicemeeterCallbacksConfig()


# DEFAULTS = {
#     "label": "{volume[percent]}%",
#     "label_alt": "{volume[percent]}%",
#     "class_name": "",
#     "vmcli_exe_path": "c:\\Users\\OmarPc\\repo_My_configs_cmder\\cmder\\bin\\vmcli.exe",
#     "main_output_bus": 0,
#     "synced_outputs_count": 2,
#     "mute_text": "mute",
#     "tooltip": True,
#     "scroll_step": 2,
#     "slider_beep": True,
#     "volume_icons": [
#         "\ueee8",  # Icon for muted
#         "\uf026",  # Icon for 0-10% volume
#         "\uf027",  # Icon for 11-30% volume
#         "\uf027",  # Icon for 31-60% volume
#         "\uf028",  # Icon for 61-100% volume
#     ],
#     "audio_menu": {
#         "blur": True,
#         "round_corners": True,
#         "round_corners_type": "normal",
#         "border_color": "System",
#         "alignment": "right",
#         "direction": "down",
#         "distance": 6,  # deprecated
#         "offset_top": 6,
#         "offset_left": 0,
#         "show_apps": False,
#         "show_app_labels": False,
#         "show_app_icons": True,
#         "show_apps_expanded": False,
#         "app_icons": {"toggle_down": "\uf078", "toggle_up": "\uf077"},
#     },
#     "animation": {"enabled": True, "type": "fadeInOut", "duration": 200},
#     "container_padding": {"top": 0, "left": 0, "bottom": 0, "right": 0},
#     "callbacks": {
#         "on_left": "toggle_volume_menu",
#         "on_middle": "do_nothing",
#         "on_right": "toggle_mute",
#     },
# }

# VALIDATION_SCHEMA = {
#     "label": {"type": "string", "default": DEFAULTS["label"]},
#     "label_alt": {"type": "string", "default": DEFAULTS["label_alt"]},
#     "class_name": {
#         "type": "string",
#         "required": False,
#         "default": DEFAULTS["class_name"],
#     },
#     "vmcli_exe_path": {
#         "type": "string",
#         "required": True,
#         "default": DEFAULTS["class_name"],
#     },
#     "main_output_bus": {
#         "type": "integer",
#         "required": True,
#         "default": DEFAULTS["main_output_bus"],
#     },
#     "synced_outputs_count": {
#         "type": "integer",
#         "required": True,
#         "default": DEFAULTS["synced_outputs_count"],
#     },
#     "mute_text": {
#         "type": "string",
#         "required": False,
#         "default": DEFAULTS["mute_text"],
#     },
#     "tooltip": {"type": "boolean", "required": False, "default": DEFAULTS["tooltip"]},
#     "scroll_step": {
#         "type": "integer",
#         "required": False,
#         "default": DEFAULTS["scroll_step"],
#         "min": 1,
#         "max": 100,
#     },
#     "slider_beep": {
#         "type": "boolean",
#         "required": False,
#         "default": DEFAULTS["slider_beep"],
#     },
#     "volume_icons": {
#         "type": "list",
#         "default": DEFAULTS["volume_icons"],
#         "schema": {"type": "string", "required": False},
#     },
#     "audio_menu": {
#         "type": "dict",
#         "required": False,
#         "schema": {
#             "blur": {"type": "boolean", "default": DEFAULTS["audio_menu"]["blur"]},
#             "round_corners": {
#                 "type": "boolean",
#                 "default": DEFAULTS["audio_menu"]["round_corners"],
#             },
#             "round_corners_type": {
#                 "type": "string",
#                 "default": DEFAULTS["audio_menu"]["round_corners_type"],
#             },
#             "border_color": {
#                 "type": "string",
#                 "default": DEFAULTS["audio_menu"]["border_color"],
#             },
#             "alignment": {
#                 "type": "string",
#                 "default": DEFAULTS["audio_menu"]["alignment"],
#             },
#             "direction": {
#                 "type": "string",
#                 "default": DEFAULTS["audio_menu"]["direction"],
#             },
#             "distance": {
#                 "type": "integer",
#                 "default": DEFAULTS["audio_menu"]["distance"],
#             },
#             "offset_top": {
#                 "type": "integer",
#                 "default": DEFAULTS["audio_menu"]["offset_top"],
#             },
#             "offset_left": {
#                 "type": "integer",
#                 "default": DEFAULTS["audio_menu"]["offset_left"],
#             },
#             "show_apps": {
#                 "type": "boolean",
#                 "default": DEFAULTS["audio_menu"]["show_apps"],
#             },
#             "show_app_labels": {
#                 "type": "boolean",
#                 "default": DEFAULTS["audio_menu"]["show_app_labels"],
#             },
#             "show_app_icons": {
#                 "type": "boolean",
#                 "default": DEFAULTS["audio_menu"]["show_app_icons"],
#             },
#             "show_apps_expanded": {
#                 "type": "boolean",
#                 "default": DEFAULTS["audio_menu"]["show_apps_expanded"],
#             },
#             "app_icons": {
#                 "type": "dict",
#                 "schema": {
#                     "toggle_down": {
#                         "type": "string",
#                         "default": DEFAULTS["audio_menu"]["app_icons"]["toggle_down"],
#                     },
#                     "toggle_up": {
#                         "type": "string",
#                         "default": DEFAULTS["audio_menu"]["app_icons"]["toggle_up"],
#                     },
#                 },
#                 "default": DEFAULTS["audio_menu"]["app_icons"],
#             },
#         },
#         "default": DEFAULTS["audio_menu"],
#     },
#     "animation": {
#         "type": "dict",
#         "required": False,
#         "schema": {
#             "enabled": {"type": "boolean", "default": DEFAULTS["animation"]["enabled"]},
#             "type": {"type": "string", "default": DEFAULTS["animation"]["type"]},
#             "duration": {
#                 "type": "integer",
#                 "default": DEFAULTS["animation"]["duration"],
#             },
#         },
#         "default": DEFAULTS["animation"],
#     },
#     "container_padding": {
#         "type": "dict",
#         "required": False,
#         "schema": {
#             "top": {"type": "integer", "default": DEFAULTS["container_padding"]["top"]},
#             "left": {
#                 "type": "integer",
#                 "default": DEFAULTS["container_padding"]["left"],
#             },
#             "bottom": {
#                 "type": "integer",
#                 "default": DEFAULTS["container_padding"]["bottom"],
#             },
#             "right": {
#                 "type": "integer",
#                 "default": DEFAULTS["container_padding"]["right"],
#             },
#         },
#         "default": DEFAULTS["container_padding"],
#     },
#     "label_shadow": {
#         "type": "dict",
#         "required": False,
#         "schema": {
#             "enabled": {"type": "boolean", "default": False},
#             "color": {"type": "string", "default": "black"},
#             "offset": {"type": "list", "default": [1, 1]},
#             "radius": {"type": "integer", "default": 3},
#         },
#         "default": {"enabled": False, "color": "black", "offset": [1, 1], "radius": 3},
#     },
#     "container_shadow": {
#         "type": "dict",
#         "required": False,
#         "schema": {
#             "enabled": {"type": "boolean", "default": False},
#             "color": {"type": "string", "default": "black"},
#             "offset": {"type": "list", "default": [1, 1]},
#             "radius": {"type": "integer", "default": 3},
#         },
#         "default": {"enabled": False, "color": "black", "offset": [1, 1], "radius": 3},
#     },
#     "progress_bar": {
#         "type": "dict",
#         "default": {"enabled": False},
#         "required": False,
#         "schema": {
#             "enabled": {"type": "boolean", "default": False},
#             "size": {"type": "integer", "default": 18, "min": 8, "max": 64},
#             "thickness": {"type": "integer", "default": 3, "min": 1, "max": 10},
#             "color": {
#                 "anyof": [
#                     {"type": "string"},
#                     {"type": "list", "schema": {"type": "string"}},
#                 ],
#                 "default": "#00C800",
#             },
#             "background_color": {"type": "string", "default": "#3C3C3C"},
#             "position": {
#                 "type": "string",
#                 "allowed": ["left", "right"],
#                 "default": "left",
#             },
#             "animation": {
#                 "type": "boolean",
#                 "default": True,
#             },
#         },
#     },
#     "callbacks": {
#         "type": "dict",
#         "schema": {
#             "on_left": {
#                 "type": "string",
#                 "default": DEFAULTS["callbacks"]["on_left"],
#             },
#             "on_middle": {
#                 "type": "string",
#                 "default": DEFAULTS["callbacks"]["on_middle"],
#             },
#             "on_right": {
#                 "type": "string",
#                 "default": DEFAULTS["callbacks"]["on_right"],
#             },
#         },
#         "default": DEFAULTS["callbacks"],
#     },
# }
