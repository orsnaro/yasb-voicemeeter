import ctypes
import logging
import re
import subprocess

import psutil
from PIL import Image
from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, QRect, Qt
from PyQt6.QtGui import QImage, QPixmap, QWheelEvent
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QSlider, QVBoxLayout, QWidget

from core.utils.tooltip import CustomToolTip, set_tooltip
from core.utils.utilities import (
    PopupWidget,
    add_shadow,
    build_progress_widget,
    build_widget_label,
    is_valid_qobject,
    refresh_widget_style,
)

from core.validation.widgets.yasb.volume import VolumeWidget
from core.utils.widgets.animation_manager import AnimationManager
from core.utils.widgets.voicemeeter.service import VoicemeeterService
from core.utils.win32.app_icons import get_process_icon
from core.utils.win32.utilities import get_app_name_from_pid
from core.validation.widgets.yasb.voicemeeter import VALIDATION_SCHEMA
from core.widgets.base import BaseWidget


class Voicemeeter(VolumeWidget):
    def __init__(self):
        super.__init__(class_name="voicemeeter", service=VoicemeeterService)

    def _reinitialize_audio(self):  # OVERRIDE
        """Update volume interface reference after device change."""
        # Service already reinitialized, just update our reference
        self.volume = self._service.get_volume_interface()

        # Close dialog if open (device change means menu data is stale)
        if hasattr(self, "dialog") and is_valid_qobject(self.dialog):
            self.dialog.hide()
            # Only reopen menu if we still have a valid device and speakers available
            if self.volume is not None:
                try:
                    speakers = self._service.get_speakers()
                    if speakers:
                        self.show_volume_menu()
                except Exception as e:
                    logging.debug(f"Cannot show volume menu after device change: {e}")

        self._update_label()
