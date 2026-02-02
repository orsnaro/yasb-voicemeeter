import subprocess

from core.config import get_config


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

    def __init__(self):
        self.synced_outputs_count = int(get_config().get("synced_outputs_count"))
        self.main_output_bus = int(get_config().get("main_output_bus"))
        self._level_all_to_main()

    def GetMasterVolumeLevelScalar(self) -> float:
        level_dB = self._get_master_volume()
        level_scaled = self._converte_to_normal_scale(level_dB)
        return level_scaled

    def SetMasterVolumeLevelScalar(self, level: float, _=None):
        level_dB = self._converte_to_voicemeter_scale(level)
        self._set_master_volume(level_dB)

    def GetMute(self) -> bool:
        is_muted = self._get_mute_state_master_volume()
        return bool(is_muted)

    def SetMute(self, state: bool, _=None):
        self._set_mute_state_master_volume(does_want_to_mute=state)

    def _increase_master_volume(self, inc_amount: int): ...
    def _decrease_master_volume(self, dec_amount: int): ...

    def _master_volume_toggle_mute(self):
        self._toggle_mute_volume(bus=int(self.main_output_bus))

    def _get_mute_state_master_volume(self) -> int:
        # if any is unmuted the master state is then unmuted
        is_master_muted = 1  # 1 means true

        for i in range(self.synced_outputs_count):
            is_muted = self._get_mute_state_volume(bus=int(self.main_output_bus))
            if is_muted == 0:
                is_master_muted = 0
                return

        return is_master_muted

    def _set_mute_state_master_volume(self, does_want_to_mute: bool):
        for i in range(self.synced_outputs_count):
            self._set_mute_state_volume(bus=i, does_want_to_mute=does_want_to_mute)

    def _get_master_volume(self) -> int:
        volume_dB = self._get_volume(bus=int(self.main_output_bus))
        return volume_dB

    def _set_master_volume(self, volume: int):
        for i in range(self.synced_outputs_count):
            self._set_volume(bus=i, volume=volume)

    def _get_volume(self, bus: int) -> int:
        volume_dB = self._vmcli_cmd(f"Strip[{bus}].Gain")
        return volume_dB

    def _set_volume(self, bus: int, volume: int):
        self._vmcli_cmd(f"Strip[{bus}].Gain={volume}")

    def _increase_volume(self, bus: int, inc_amount: int):
        self._vmcli_cmd(f"Strip[{bus}].Gain+={inc_amount}")

    def _decrease_volume(self, bus: int, dec_amount: int):
        self._vmcli_cmd(f"Strip[{bus}].Gain-={dec_amount}")

    def _toggle_mute_volume(self, bus: int):
        self._vmcli_cmd(f"!Strip[{bus}].Mute")

    def _get_mute_state_volume(self, bus: int) -> int:
        state = self._vmcli_cmd(f"Strip[{bus}].Mute")
        return state

    def _set_mute_state_volume(self, bus: int, does_want_to_mute: bool):
        self._vmcli_cmd(f"Strip[{bus}].Mute={int(does_want_to_mute)}")

    def _level_all_to_main(self):
        main_output_bus = self.main_output_bus
        volume_dB = self._get_volume(bus=main_output_bus)

        for i in range(int(self.synced_outputs_count)):
            self._set_volume(bus=i, volume=volume_dB)

    def _converte_to_voicemeter_scale(level: float) -> int:
        # NOTE: volume comes in range from 0.0 to 1.0
        # search linear transformation

        shift_from_zero = 60.0  # voicemeeter ranges from -60 to 12
        vsteps = 72.0

        converted_level = int((level * vsteps) - shift_from_zero)

        return converted_level

    def _converte_to_normal_scale(level: int) -> float:
        # NOTE: volume comes in range from 0.0 to 1.0
        # search linear transformation

        shift_from_zero = 60.0  # voicemeeter range -60 to 12
        vsteps = 72.0

        converted_level = (float(level) + shift_from_zero) / vsteps

        return converted_level

    def _vmcli_cmd(self, command: str, **kwargs):
        vmcli_exe_path = get_config().get("vmcli_exe_path")
        # TESTING
        print("TESTING:" + vmcli_exe_path)
        # TESTING

        val = None
        try:
            val = subprocess.run(vmcli_exe_path + " " + command)
        except:
            pass

        return val
