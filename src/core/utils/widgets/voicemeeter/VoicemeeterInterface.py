import inspect
import logging
import subprocess
import threading

import voicemeeterlib

from core.utils.widgets.microphone.service import _SharedVolumeCallback

global vm_direct_global
vm_direct_global = None
_lock = threading.Lock()


class VoicemeeterApiLoginController:
    @staticmethod
    def Vm_api_login():
        VoicemeeterApiLoginController._start_vm_direct_if_not_started()

    @staticmethod
    def Vm_api_logout():
        VoicemeeterApiLoginController._stop_vm_direct_if_not_stopped()

    @staticmethod
    def _start_vm_direct_if_not_started():
        global vm_direct_global
        try:
            if vm_direct_global is None:
                with _lock:
                    if vm_direct_global is None:
                        logging.debug(
                            f"{inspect.stack()[0][3]}(): was called!  id(vm_direct_global)  = {id(vm_direct_global)}"
                        )
                        # vm software has 3 versions: basic, banana, potato LOL
                        vm_direct_global = voicemeeterlib.api("banana", sync=True)
                        vm_direct_global.login()
                        logging.info(f"{inspect.stack()[0][3]}(): STARTED!")

        except Exception as e:
            logging.error(
                f"{inspect.stack()[0][3]}(): Failed to init voicemeeter direct communnicator obj. Details: {e}"
            )

    @staticmethod
    def _stop_vm_direct_if_not_stopped():
        global vm_direct_global
        try:
            if vm_direct_global is not None:
                with _lock:
                    if vm_direct_global is not None:
                        logging.debug(
                            f"{inspect.stack()[0][3]}(): was called! stopping... id(vm_direct_global) = {id(vm_direct_global)}"
                        )
                        # software has 3 versions: normal,banana,potato LOL
                        vm_direct_global.logout()
                        vm_direct_global = None
                        logging.info(f"{inspect.stack()[0][3]}(): STOPPED!")

        except Exception as e:
            logging.error(
                f"{inspect.stack()[0][3]}(): Failed to stop voicemeeter direct communnicator obj. Details: {e}"
            )


class VoicemeeterInterface:
    """_summary_
    class communicates with (vmcli tool or vm api directly)  that communicates with voicemeeter tool to control in/op sound in OS

    ### Interface needss to implement the following:

    GetMasterVolumeLevelScalar

    SetMasterVolumeLevelScalar

    GetMute

    SetMute

    RegisterControlChangeNotify

    UnRegisterControlChangeNotify

    ---
    voicemeeter output sliders has total of 72 steps -60:0% ->  12:100% (vm gain is in dB)
    """

    _instances_count = 0
    _id_gen = 0
    _watched_instances = {}
    _update_threads = set()
    _VmApiUpdatesThreadName = "VmApiUpdatesTh"

    def __new__(cls, **kwargs):
        cls._instances_count += 1
        cls._id_gen += 1
        return super().__new__(cls)

    def __init__(self, **kwargs):

        logging.debug(
            f"{self.__class__.__name__} {inspect.stack()[0][3]}(): was called!  id(VoicemeeterInterface) = {id(self)}"
        )
        self.id = self.__class__._id_gen

        self.synced_outputs_count = kwargs["synced_outputs_count"]
        self.main_output_bus = kwargs["main_output_bus"]
        self.vmcli_exe_path = kwargs["vmcli_exe_path"]  # backward compatibility
        self.virtual_speakers_obj = kwargs.get("virtual_speakers_obj", None)

        self._shared_volume_callback = None
        VoicemeeterApiLoginController.Vm_api_login()
        self.vm_direct = vm_direct_global
        self._level_all_to_main()

    def __del__(self):
        self.__class__._instances_count -= 1

    def GetMasterVolumeLevelScalar(self) -> float:
        level_dB = self._get_master_volume()
        level_scaled = self._converte_to_normal_scale(level_dB)
        return level_scaled

    def SetMasterVolumeLevelScalar(self, level: float, _=None):
        level_dB = self._converte_to_voicemeter_scale(level)
        self._set_master_volume(level_dB)

    def GetMute(self) -> int:
        is_muted = self._get_mute_state_master_volume()
        return is_muted

    def SetMute(self, state: bool, _=None):
        self._set_mute_state_master_volume(does_want_to_mute=state)

    def RegisterControlChangeNotify(self, callback: _SharedVolumeCallback):
        logging.debug(f"{inspect.stack()[0][3]}(): Registiring! {callback.on_notify.__name__}")
        # NOTE: will need this cuz without it
        # keyboard macros that changes gain/mute in voicemeeter is not reflected to voicemeeter widget slider or label

        self.vm_direct.clear_dirty()
        try:
            if self.vm_direct.stopped():
                # update_th = threading.Thread(target=self.vm_direct.init_thread, daemon=False)
                # update_th.start()
                # self.__class__._update_threads.add(update_th)
                self.vm_direct.init_thread()  # start vm updates watcher thread

        except Exception as e:
            logging.error(f"{inspect.stack()[0][3]}():could not start vm api updates thread. Details: {e}")

        self._shared_volume_callback = callback
        self.vm_direct.event.add(["pdirty"])
        self.vm_direct.observer.add(self)  # looks for on_update() method automatically inside passed class
        self.__class__._watched_instances[id(self)] = self

    def UnregisterControlChangeNotify(self, callback: _SharedVolumeCallback):
        logging.debug(f"{inspect.stack()[0][3]}(): UN-Registiring!")
        # NOTE: DONT call logout() here! this method is triggered multiple times during yasb app lifetime
        # NOTE: will need this cuz without it
        # keyboard macros that changes gain/mute in voicemeeter is not reflected to voicemeeter widget slider or label

        # for th in list(self.__class__._update_threads):
        #     th.join()
        #     self.__class__._update_threads.remove(th)

        self.vm_direct.end_thread()

        self.vm_direct.event.remove(["pdirty"])
        self._shared_volume_callback = None

        instance_id = id(self)
        if instance_id in self.__class__._watched_instances:
            self.vm_direct.observer.remove(self)
            self.__class__._watched_instances.pop(instance_id)
        else:
            logging.warning(
                f"{inspect.stack()[0][3]}(): this instance id: {instance_id} is not in watched instances {self.__class__._watched_instances}"
            )

    def on_update(self, event):  # vm lib docs: can use on_{event}() e.g.(on_pdirty())
        try:
            self._shared_volume_callback.on_notify(0, 0, event, 0, 0)
        except Exception as e:
            logging.error(f"{inspect.stack()[0][3]}(): Failed to use on_notify() ! event {event} Details: {e}")

    def stop_vm_api(self):  # CHECK: must be called once in entire yasb app lifetime
        try:
            logging.info(f"{inspect.stack()[0][3]}(): stopping vm api...")
            # for k, v in list(self.__class__._watched_instances.items()):
            #     v.UnregisterControlChangeNotify(0)
            #     self.__class__._watched_instances.pop(k)

            if self.__class__._instances_count <= 1:  # only this instance
                VoicemeeterApiLoginController.Vm_api_logout()
                self.vm_direct.end_thread()
            else:  # _instances_count > 1
                raise Exception(
                    "Can't logout or stop VM API now (there is other instances of VM interface that still alive)"
                )
        except Exception as e:
            logging.error(f"{inspect.stack()[0][3]}(): {e}")

    def _increase_master_volume(self, inc_amount: int): ...  # nope! over-engineering
    def _decrease_master_volume(self, dec_amount: int): ...  # nope! over-engneering

    def _master_volume_toggle_mute(self):
        self._toggle_mute_volume(bus=int(self.main_output_bus))

    def _get_mute_state_master_volume(self) -> int:
        # if any is unmuted the master state is then -> unmuted
        is_master_muted = 1  # 1 means true

        for i in range(self.synced_outputs_count):
            is_muted = self._get_mute_state_volume(bus=i)
            if not is_muted:
                is_master_muted = 0
                break

        return is_master_muted

    def _set_mute_state_master_volume(self, does_want_to_mute: bool):
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
        cmd_bulk = {}
        for i in range(self.synced_outputs_count):
            cmd_bulk[f"bus-{i}"] = {"gain": volume}
        try:
            # threading.Thread(target=self.vm_direct.apply, args=(cmd_bulk,), daemon=True).start()
            self.vm_direct.apply(cmd_bulk)
        except Exception as e:
            logging.error(f"{inspect.stack()[0][3]}(): failed to get master volume! err details: {e}")

    def _get_volume(self, bus: int) -> int:
        try:
            volume_dB = self.vm_direct.bus[bus].gain
        except Exception as e:
            logging.error(f"{inspect.stack()[0][3]}(): failed to get bus{bus} volume! err details: {e}")

        return volume_dB

    def _set_volume(self, bus: int, volume: int):
        try:
            self.vm_direct.bus[bus].gain = volume
        except Exception as e:
            logging.error(f"{inspect.stack()[0][3]}(): failed to set bus{bus} volume! err details: {e}")

    def _increase_volume(self, bus: int, inc_amount: int):
        try:
            self.vm_direct.bus[bus].gain += inc_amount
        except Exception as e:
            logging.error(f"{inspect.stack()[0][3]}(): failed to increase bus{bus} volume! err details: {e}")

    def _decrease_volume(self, bus: int, dec_amount: int):
        try:
            self.vm_direct.bus[bus].gain -= dec_amount
        except Exception as e:
            logging.error(f"{inspect.stack()[0][3]}(): failed to decrease bus{bus} volume! err details: {e}")

    def _toggle_mute_volume(self, bus: int):
        try:
            self.vm_direct.bus[bus].mute = not self.vm_direct.bus[bus].mute
        except Exception as e:
            logging.error(f"{inspect.stack()[0][3]}(): failed to toggle bus{bus} mute state! err details: {e}")

    def _get_mute_state_volume(self, bus: int) -> int:
        try:
            state = self.vm_direct.bus[bus].mute
        except Exception as e:
            logging.error(f"{inspect.stack()[0][3]}(): failed to get bus{bus} mute state! err details: {e}")
        return state

    def _set_mute_state_volume(self, bus: int, does_want_to_mute: bool):
        try:
            self.vm_direct.bus[bus].mute = does_want_to_mute
        except Exception as e:
            logging.error(f"{inspect.stack()[0][3]}(): failed to set bus{bus} mute state! err details: {e}")

    def _level_all_to_main(self):
        main_output_bus = self.main_output_bus
        volume_dB = self._get_volume(bus=main_output_bus)

        for i in range(int(self.synced_outputs_count)):
            self._set_volume(bus=i, volume=volume_dB)

        logging.debug(f"{inspect.stack()[0][3]}(): leveled all buses to main bus{self.main_output_bus} level")

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

    # legacy
    def _vmcli_cmd(self, command: str, **kwargs):
        _vmcli_exe_path = self.vmcli_exe_path
        val = None
        try:
            val = subprocess.run(_vmcli_exe_path + " " + command, capture_output=True, text=True, close_fds=False)
        except Exception as e:
            logging.error(f"{inspect.stack()[0][3]}(): failed to execute vmcli.exe! err details: {e}")

        return val
