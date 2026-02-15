import inspect
import logging
import threading
from typing import override

from pycaw.constants import DEVICE_STATE
from pycaw.pycaw import AudioUtilities, EDataFlow

from core.utils.utilities import is_process_running
from core.utils.widgets.voicemeeter.VoicemeeterInterface import VoicemeeterApiLoginController, VoicemeeterInterface
from core.utils.widgets.volume.service import AudioOutputService


# NOTE: if this inherited calss doesnt work doesn't work just try pasting AudioOutputService(QObject) as it is here
# or using AudioOutputService(QObject) in volume/service.py directly
class VoicemeeterService(AudioOutputService):
    def __init__(self, **kwargs):
        self.vmcli_exe_path = kwargs["vmcli_exe_path"]  # backward compatibility
        self.main_output_bus = kwargs["main_output_bus"]
        self.synced_outputs_count = kwargs["synced_outputs_count"]
        VoicemeeterApiLoginController.Vm_api_login()
        super().__init__()

    # OVERRIDE
    @override
    def _initialize_audio(self):
        """Fetch speakers, devices and sessions in background thread."""
        if self._initializing:
            return
        self._initializing = True

        def fetch():
            try:
                if self._cached_speakers is None:
                    speakers = AudioUtilities.GetSpeakers()
                    self._cached_speakers = speakers
                    if speakers or self._volume_interface is None:
                        self._volume_interface = self.get_volume_interface()
                        logging.info(f"{inspect.stack()[0][3]}(): initing audio with voicemeeterInterface!")

                with self._cache_lock:
                    if self._cached_devices is None:
                        devices = AudioUtilities.GetAllDevices(
                            data_flow=EDataFlow.eRender.value, device_state=DEVICE_STATE.ACTIVE.value
                        )
                        self._cached_devices = [(d.id, d.FriendlyName) for d in devices]

                with self._cache_lock:
                    if self._cached_sessions is None:
                        self._cached_sessions = AudioUtilities.GetAllSessions()

            except Exception as e:
                logging.warning(f"from {inspect.stack()[0][3]}(): failed to fetch volume service details: {e}")
                self._volume_interface = None
            finally:
                self._initializing = False

        threading.Thread(target=fetch, daemon=True).start()

    # OVERRIDE
    @override
    def __del__(self):
        if self._volume_interface is not None and isinstance(self._volume_interface, VoicemeeterInterface):
            self._volume_interface.stop_vm_api()

    # OVERRIDE
    @override
    def get_volume_interface(self):
        """Get volume control interface."""

        try:
            if is_process_running("voicemeeterpro.exe"):
                logging.warning(
                    "'voicemeeterpro.exe' was not running before yasb starts. This MAY cause issues specially if using legacy vmcli.exe! -> launching voicemeeter via an internal command"
                )

            # maybe voicemeeterpro.exe init process includes a device change that triggers _on_device_change() in yasb
            # if so it will call get_volume_interface() just in right time lazely when its ready!
            self._volume_interface = VoicemeeterInterface(
                vmcli_exe_path=self.vmcli_exe_path,
                main_output_bus=self.main_output_bus,
                synced_outputs_count=self.synced_outputs_count,
            )

        except Exception as e:
            logging.warning(
                f"from {inspect.stack()[0][3]}(): failed to use VoicemeeterInterface as the volume interface. Fallingback to default OS and yasb volume interface. err details: {e}"
            )

            # fallback to default OS and yasb volume interface
            speakers = self.get_speakers()
            if speakers:
                try:
                    self._volume_interface = speakers.EndpointVolume
                except:
                    pass

        return self._volume_interface
