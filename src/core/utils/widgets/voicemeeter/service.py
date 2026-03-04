import inspect
import logging
import threading
from typing import override

from pycaw.constants import DEVICE_STATE
from pycaw.pycaw import AudioDevice, AudioUtilities, EDataFlow

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
        """Get volume control appropriate interface (either win api volume endpoints or voicemeeter interface)"""
        if self._volume_interface is None:
            self._volume_interface = self.try_get_volume_interfaces()

        return self._volume_interface

    def try_get_volume_interfaces(self):
        "Try to  get the right interface for the default speakers (start with testing voicemeeter interface)"
        speakers = self.get_speakers()
        if speakers:
            if self.is_voicemeeter_device(speakers):
                self._volume_interface = self.try_voicemeeter_interface(speakers)
            else:  # so the current speakers is not voicemeeter vritual device
                self._volume_interface = self.try_win_api_volume_endpoint(speakers)

        return self._volume_interface

    def is_voicemeeter_device(self, audio_output_device: AudioDevice):
        """Check if default audio output device is a voicemeeter interface compatible device"""
        target = "voicemeeter"
        # nieve: check if the name has voicemeeter in it -> target in device.FriendlyName.lower()  ?
        # Bullet proof check!: check all props if have 'voicemeeter' keyword in it (props dict is not big -> 71 entries approx)
        is_voicemeeter_device_used = False
        device_properties_container = audio_output_device.properties
        if device_properties_container is not None and isinstance(device_properties_container, dict):
            for _, value in device_properties_container.items():
                if isinstance(value, str) and target in value.lower():
                    is_voicemeeter_device_used = True
                    break

        return is_voicemeeter_device_used

    def try_voicemeeter_interface(self, voicemeeter_device: AudioDevice):
        """Try using the voicemeeter interface class as the volume interface"""
        try:
            self._volume_interface = VoicemeeterInterface(
                vmcli_exe_path=self.vmcli_exe_path,
                main_output_bus=self.main_output_bus,
                synced_outputs_count=self.synced_outputs_count,
                virtual_speakers_obj=voicemeeter_device,
            )

        except Exception as e:
            logging.warning(
                f"from {inspect.stack()[0][3]}(): failed to use VoicemeeterInterface as the volume interface. Fallingback to default OS and yasb volume interface. err details: {e}"
            )

        return self._volume_interface

    def try_win_api_volume_endpoint(self, speakers: AudioDevice):
        """Try using the win api volume endpoint as the volume interface"""
        try:
            self._volume_interface = speakers.EndpointVolume
        except Exception as e:
            logging.warning(f"from {inspect.stack()[0][3]}(): failed to use Win API Volume Endpoint. Details: {e}")

        return self._volume_interface
