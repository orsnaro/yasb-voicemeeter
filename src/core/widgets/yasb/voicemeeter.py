import logging

from core.utils.utilities import is_valid_qobject
from core.utils.widgets.voicemeeter.service import VoicemeeterService
from core.validation.widgets.yasb.volume import VolumeWidget


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
