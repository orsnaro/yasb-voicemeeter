from core.utils.widgets.volume.service import AudioOutputService
from core.utils.utilities import is_process_running

from VoicemeeterInterface import VoicemeeterInterface


# NOTE: if this inherited calss doesnt work doesn't work just try pasting AudioOutputService(QObject) as it is here
# or using AudioOutputService(QObject) in volume/service.py directly
class VoicemeeterService(AudioOutputService):
    def __init__():
        super().__init__()

    # OVERRIDE
    def get_volume_interface(self):
        """Get volume control interface."""
        if is_process_running("voicemeeterpro.exe"):
            # NOTE: sometimes yasb will init before voicemeeterpro.exe does... what to do then??? other than manually refresh yasb?
            # maybe voicemeeterpro.exe init process includes a device change that triggers _on_devicce_change() in yasb
            # if so it will call get_volume_interface() just in right time lazely when its ready!

            try:
                self._volume_interface = VoicemeeterInterface
            except:
                pass
        else:
            # fallback to default OS and yasb volume interface
            speakers = self.get_speakers()
            if speakers:
                try:
                    self._volume_interface = speakers.EndpointVolume
                except:
                    pass

        return self._volume_interface
