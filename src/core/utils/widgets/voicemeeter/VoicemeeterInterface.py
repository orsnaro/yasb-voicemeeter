import inspect
import logging
import subprocess
import threading

import voicemeeterlib

from core.utils.widgets.microphone.service import _SharedVolumeCallback

global vm_direct_global
vm_direct_global = None


class VoicemeeterInterface:
    """_summary_
    class communicates with vmcli tool  that communicates with voicemeeter tool to control in/op sound in OS

    ### Interface need those method names:

    GetMasterVolumeLevelScalar

    SetMasterVolumeLevelScalar

    GetMute

    SetMute

    ---
    voicemeeter output sliders has total of 72 steps -60:0% ->  12:100% (gain is in dB)
    """

    _lock = threading.Lock()
    watcher_loop_th: threading.Thread = None

    def __init__(
        self,
        vmcli_exe_path: str,
        main_output_bus: str,
        synced_outputs_count: str,
    ):
        self.sync_vm_widgets = False
        self.synced_outputs_count = synced_outputs_count
        self.main_output_bus = main_output_bus
        self.vmcli_exe_path = vmcli_exe_path
        self.__class__._start_vm_direct_if_not_started()
        # VoicemeeterInterface._start_vm_direct_if_not_started() #same as above line
        self.vm_direct = vm_direct_global
        self.vm_direct.observer.add(self)
        with self.__class__._lock:
            if self.__class__.watcher_loop_th is not None and not self.__class__.watcher_loop_th.is_alive():
                self.__class__.watcher_loop_th = threading.Thread(target=self.__class__._watcher_loop, daemon=True)
                self.__class__.watcher_loop_th.start()
        self._level_all_to_main()

    @classmethod
    def on_update(cls, new_volume=None, new_mute=None, event_context=None, channels=None, channel_volumes=None):
        # alias for on_notify() in _SharedVolumeCallback cuz voicemeeter api looks for on_update() to call
        pass

    @classmethod
    def _watcher_loop(cls):
        try:
            global vm_direct_global
            vm = vm_direct_global
            while True:
                if vm.pdirty() or vm.ldirty() or vm.mdirty():
                    cls.on_update(None, None, None, None, None)
        except Exception as e:
            logging.error(f"{inspect.stack()[0][3]}(): issue while starting Voicemeeter watcher_loop Details: {e}")

    @classmethod
    def _start_vm_direct_if_not_started(cls):
        global vm_direct_global
        try:
            if vm_direct_global is None:
                with cls._lock:
                    if vm_direct_global is None:
                        logging.info(
                            f"{inspect.stack()[0][3]}(): was called!  id(vm_direct_global) = {id(vm_direct_global)}"
                        )
                        # software has 3 versions: normal,banana,potato LOL
                        vm_direct_global = voicemeeterlib.api(
                            "banana",
                            sync=True,
                            subs={"ldirty": True, "pdirty": True, "mdirty": True},
                        )
                        vm_direct_global.event.ldirty = True  # get updates from voicemeeter for audio levels changes
                        vm_direct_global.event.pdirty = True  # get updates from voicemeeter for params values changes
                        vm_direct_global.event.mdirty = True  # get updates from voicemeeter for macro values changes

                        vm_direct_global.login()
        except Exception as e:
            logging.error(
                f"{inspect.stack()[0][3]}(): Failed to init voicemeeter direct communnication obj. Details: {e}"
            )

    def GetMasterVolumeLevelScalar(self) -> float:
        level_dB = self._get_master_volume()
        level_scaled = self._converte_to_normal_scale(level_dB)
        return level_scaled

    def SetMasterVolumeLevelScalar(self, level: float, _=None):
        if self.sync_vm_widgets:
            self.__class__.on_update(None, None, None, None, None)  # updates all other widges but a bit laggy
        level_dB = self._converte_to_voicemeter_scale(level)
        self._set_master_volume(level_dB)

    def GetMute(self) -> int:
        is_muted = self._get_mute_state_master_volume()
        return is_muted

    def SetMute(self, state: bool, _=None):
        if self.sync_vm_widgets:
            self.__class__.on_update(None, None, None, None, None)  # updates all other widges but a bit laggy
        self._set_mute_state_master_volume(does_want_to_mute=state)

    def RegisterControlChangeNotify(self, callback: _SharedVolumeCallback):
        logging.debug(f"{inspect.stack()[0][3]}(): registiring!")
        # NOTE: will need this cuz
        # keyboard macros that changes gain/mute in voicemeeter is not reflected to voicemeeter widget slider or label
        self.__class__.on_update = callback.on_notify  # voicemeeter api searched for on_update() to call on any changes

    def UnregisterControlChangeNotify(self, callback):
        logging.debug(f"{inspect.stack()[0][3]}(): UN-registiring!")
        # NOTE: will need this cuz
        # keyboard macros that changes gain/mute in voicemeeter is not reflected to voicemeeter widget slider or label
        self.__class__.on_update = None

    def _increase_master_volume(self, inc_amount: int): ...
    def _decrease_master_volume(self, dec_amount: int): ...

    def _master_volume_toggle_mute(self):
        self._toggle_mute_volume(bus=int(self.main_output_bus))

    def _get_mute_state_master_volume(self) -> int:
        # if any is unmuted the master state is then unmuted
        is_master_muted = 1  # 1 means true

        for i in range(self.synced_outputs_count):
            is_muted = self._get_mute_state_volume(bus=i)
            if not is_muted:
                is_master_muted = 0
                break

        return is_master_muted

    def _set_mute_state_master_volume(self, does_want_to_mute: bool):
        if self.vm_direct == None:
            cmd_bulk = ""
            for i in range(self.synced_outputs_count):
                cmd_bulk += f"Bus[{i}].Mute={int(does_want_to_mute)} "
            threading.Thread(target=self._vmcli_cmd, args=(cmd_bulk,), daemon=True).start()

        else:
            cmd_bulk = {}
            for i in range(self.synced_outputs_count):
                cmd_bulk[f"bus-{i}"] = {"mute": does_want_to_mute}
            try:
                # threading.Thread(target=self.vm_direct.apply, args=(cmd_bulk,), daemon=True).start()
                self.vm_direct.apply(cmd_bulk)
            except Exception as e:
                logging.error(f"{inspect.stack()[0][3]}(): failed to change master mute state! err details: {e}")

    def _get_master_volume(self) -> int:
        volume_dB = self._get_volume(bus=int(self.main_output_bus))
        return volume_dB

    def _set_master_volume(self, volume: int):
        if self.vm_direct == None:
            cmd_bulk = ""
            for i in range(self.synced_outputs_count):
                cmd_bulk += f"Bus[{i}].Gain={volume} "
            threading.Thread(target=self._vmcli_cmd, args=(cmd_bulk,), daemon=True).start()
        else:
            cmd_bulk = {}
            for i in range(self.synced_outputs_count):
                cmd_bulk[f"bus-{i}"] = {"gain": volume}
            try:
                # threading.Thread(target=self.vm_direct.apply, args=(cmd_bulk,), daemon=True).start()
                self.vm_direct.apply(cmd_bulk)
            except Exception as e:
                logging.error(f"{inspect.stack()[0][3]}(): failed to get master volume! err details: {e}")

    def _get_volume(self, bus: int) -> int:
        if self.vm_direct == None:
            volume_dB: subprocess.CompletedProcess = self._vmcli_cmd(f"Bus[{bus}].Gain")
            # volume_dB = volume_dB.stdout.split("=")[1].replace("\n", "")  # e.g.(o/p before split 'Bus[1].Gain=0.000')
            volume_dB = volume_dB.stdout[12:16]  # e.g.(o/p before slice 'Bus[1].Gain=0.000')
            volume_dB = int(float(volume_dB))
        else:
            try:
                volume_dB = self.vm_direct.bus[bus].gain
            except Exception as e:
                logging.error(f"{inspect.stack()[0][3]}(): failed to get bus{bus} volume! err details: {e}")

        return volume_dB

    def _set_volume(self, bus: int, volume: int):
        if self.vm_direct == None:
            cmd = f"Bus[{bus}].Gain={volume}"
            threading.Thread(target=self._vmcli_cmd, args=(cmd,), daemon=True).start()
        else:
            try:
                self.vm_direct.bus[bus].gain = volume
            except Exception as e:
                logging.error(f"{inspect.stack()[0][3]}(): failed to set bus{bus} volume! err details: {e}")

        # slower?
        # self._vmcli_cmd(cmd)

    def _increase_volume(self, bus: int, inc_amount: int):
        if self.vm_direct == None:
            cmd = f"Bus[{bus}].Gain+={inc_amount}"
            threading.Thread(target=self._vmcli_cmd, args=(cmd,), daemon=True).start()
        else:
            try:
                self.vm_direct.bus[bus].gain += inc_amount
            except Exception as e:
                logging.error(f"{inspect.stack()[0][3]}(): failed to increase bus{bus} volume! err details: {e}")

        # slower?
        # self._vmcli_cmd(cmd)

    def _decrease_volume(self, bus: int, dec_amount: int):
        if self.vm_direct == None:
            cmd = f"Bus[{bus}].Gain-={dec_amount}"
            threading.Thread(target=self._vmcli_cmd, args=(cmd,), daemon=True).start()
        else:
            try:
                self.vm_direct.bus[bus].gain -= dec_amount
            except Exception as e:
                logging.error(f"{inspect.stack()[0][3]}(): failed to decrease bus{bus} volume! err details: {e}")

        # slower?
        # self._vmcli_cmd(cmd)

    def _toggle_mute_volume(self, bus: int):
        if self.vm_direct == None:
            cmd = f"!Bus[{bus}].Mute"
            threading.Thread(target=self._vmcli_cmd, args=(cmd,), daemon=True).start()
        else:
            try:
                self.vm_direct.bus[bus].mute = not self.vm_direct.bus[bus].mute
            except Exception as e:
                logging.error(f"{inspect.stack()[0][3]}(): failed to toggle bus{bus} mute state! err details: {e}")

        # slower?
        # self._vmcli_cmd(cmd)

    def _get_mute_state_volume(self, bus: int) -> int:
        if self.vm_direct == None:
            state: subprocess.CompletedProcess = self._vmcli_cmd(f"Bus[{bus}].Mute")
            # state = state.stdout.split("=")[1].replace("\n", "")  # e.g.(o/p before split 'Bus[1].Gain=0.000')
            state = state.stdout[12:16]  # e.g.(o/p before slice 'Bus[1].Gain=-60.000')
            state = int(float(state))
        else:
            try:
                state = self.vm_direct.bus[bus].mute
            except Exception as e:
                logging.error(f"{inspect.stack()[0][3]}(): failed to get bus{bus} mute state! err details: {e}")
        return state

    def _set_mute_state_volume(self, bus: int, does_want_to_mute: bool):
        if self.vm_direct == None:
            cmd = f"Bus[{bus}].Mute={int(does_want_to_mute)}"
            threading.Thread(target=self._vmcli_cmd, args=(cmd,), daemon=True).start()
        else:
            try:
                self.vm_direct.bus[bus].mute = does_want_to_mute
            except Exception as e:
                logging.error(f"{inspect.stack()[0][3]}(): failed to set bus{bus} mute state! err details: {e}")

        # slower?
        # self._vmcli_cmd(cmd)

    def _level_all_to_main(self):
        main_output_bus = self.main_output_bus
        volume_dB = self._get_volume(bus=main_output_bus)

        for i in range(int(self.synced_outputs_count)):
            self._set_volume(bus=i, volume=volume_dB)

    def _converte_to_voicemeter_scale(self, level: float) -> int:
        # NOTE: volume comes in range from 0.0 to 1.0
        # search linear transformation

        mx_v = 12
        mn_v = -60
        shift_from_zero = 60.0  # voicemeeter ranges from -60 to 12
        vsteps = 72.0
        delta = 0
        converted_level = int((level * vsteps) - shift_from_zero)

        if converted_level - delta <= mn_v:
            converted_level = mn_v

        if converted_level + delta >= mx_v:
            converted_level = mx_v

        return converted_level

    def _converte_to_normal_scale(self, level: int) -> float:
        # NOTE: volume comes in range from 0.0 to 1.0
        # search linear transformation

        mx = 1.0
        mn = 0.0
        shift_from_zero = 60.0  # voicemeeter range -60 to 12
        vsteps = 72.0
        delta = 0.0
        converted_level = (float(level) + shift_from_zero) / vsteps

        if converted_level - delta <= mn:
            converted_level = mn

        if converted_level + delta >= mx:
            converted_level = mx

        return converted_level

    def _vmcli_cmd(self, command: str, **kwargs):
        _vmcli_exe_path = self.vmcli_exe_path
        val = None
        try:
            val = subprocess.run(_vmcli_exe_path + " " + command, capture_output=True, text=True, close_fds=False)
        except Exception as e:
            logging.error(f"{inspect.stack()[0][3]}(): failed to execute vmcli.exe! err details: {e}")

        return val
