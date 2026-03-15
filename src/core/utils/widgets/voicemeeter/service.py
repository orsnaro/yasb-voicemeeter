import logging
import threading
from typing import override

import psutil
from pycaw.callbacks import AudioEndpointVolumeCallback, MMNotificationClient
from pycaw.constants import DEVICE_STATE
from pycaw.pycaw import AudioDevice, AudioUtilities, EDataFlow, ERole

from core.utils.widgets.voicemeeter.VoicemeeterInterface import VoicemeeterApiLoginController, VoicemeeterInterface
from core.utils.widgets.volume.service import AudioOutputService


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
                        logging.info("fetch(): initing audio with voicemeeterInterface!")

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
                logging.warning(f"from fetch(): failed to fetch volume service details: {e}")
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
    def handle_device_restart(self):
        logging.info("Attempting Handle audio device add/remove/change/restart")
        try:
            self._on_device_change()
        except Exception as e:
            logging.warning(
                f"handle_device_restart(): An Issue Happend While Attempting Handling audio device add/remove/change/restart! Issue Details: {e}"
            )

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
                vm_service_handle_device_restart=self.handle_device_restart,
            )

        except Exception as e:
            logging.warning(
                f"from try_voicemeeter_interface(): failed to use VoicemeeterInterface as the volume interface. Fallingback to default OS and yasb volume interface. err details: {e}"
            )

        return self._volume_interface

    def try_win_api_volume_endpoint(self, speakers: AudioDevice):
        """Try using the win api volume endpoint as the volume interface"""
        try:
            # kill voicemeeter GUI process IF running to stop it's keyboard media keys hook
            voicmeeter_names = ("voicemeeterpro_x64.exe", "voicemeeterpro.exe")
            self.kill_process_by_name(voicmeeter_names)
            self._volume_interface = speakers.EndpointVolume
        except Exception as e:
            logging.warning(f"from try_win_api_volume_endpoint(): failed to use Win API Volume Endpoint. Details: {e}")
        finally:
            self._volume_interface = speakers.EndpointVolume

        return self._volume_interface

    def kill_process_by_name(self, process_names: tuple[str, str]):
        found_and_killed = False

        for proc in psutil.process_iter(["pid", "name"]):
            try:
                # check if the process name matches (case-insensitive)
                if proc.info["name"]:
                    proc_name_lower = proc.info["name"].lower()
                    if any(target.lower() in proc_name_lower for target in process_names):
                        proc.kill()  # forcefully terminates the matched process
                        found_and_killed = True

            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as e:
                logging.warning(f"Failed to kill {proc.info['name']} (PID: {proc.info['pid']}) - Error: {e}")

        if not found_and_killed:
            logging.warning(f"No running task found matching: '{process_names}'")


class _SharedVolumeCallback(AudioEndpointVolumeCallback):
    """Forwards volume changes to the service."""

    def __init__(self, service):
        super().__init__()
        self.service = service

    def on_notify(self, new_volume, new_mute, event_context, channels, channel_volumes):
        self.service.volume_change_requested.emit()


class _SharedDeviceCallback(MMNotificationClient):
    """Forwards device changes to the service."""

    def __init__(self, service):
        super().__init__()
        self.service = service
        self._last_device_id = None
        self._last_state_changes = {}

    def on_default_device_changed(self, flow, flow_id, role, role_id, default_device_id):
        if flow_id != EDataFlow.eRender.value or role_id != ERole.eConsole.value:
            return
        if default_device_id == self._last_device_id:
            return
        self._last_device_id = default_device_id
        self.service.device_change_requested.emit()

    def on_device_state_changed(self, device_id, new_state, new_state_id):
        if new_state_id not in (DEVICE_STATE.DISABLED.value, DEVICE_STATE.ACTIVE.value, DEVICE_STATE.UNPLUGGED.value):
            return
        if self._last_state_changes.get(device_id) == new_state_id:
            return
        self._last_state_changes[device_id] = new_state_id
        self.service.device_change_requested.emit()
