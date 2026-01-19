"""
BPIO2 FlatBuffers Protocol Implementation for Bus Pirate 5/6.

This module provides high-level functions for building and parsing BPIO2 messages.
Messages are encoded as FlatBuffers and transmitted over serial using COBS encoding.

Reference: https://docs.buspirate.com/docs/binmode-reference/protocol-bpio2/
"""

import flatbuffers
from typing import Optional, List, Dict, Any
from cobs import cobs  # COBS encoding for framing

# Import generated FlatBuffers classes
from .bpio import (
    RequestPacket, RequestPacketContents,
    ResponsePacket, ResponsePacketContents,
    StatusRequest, StatusResponse, StatusRequestTypes,
    ConfigurationRequest, ConfigurationResponse,
    ModeConfiguration,
    DataRequest, DataResponse
)


class BPIO2Protocol:
    """Helper class for building and parsing BPIO2 FlatBuffers messages."""

    def __init__(self):
        self._sequence = 0

    def _next_sequence(self) -> int:
        """Get next sequence number."""
        seq = self._sequence
        self._sequence = (self._sequence + 1) & 0xFFFF
        return seq

    # --------------------------------------------------------------------------
    # Message Builders
    # --------------------------------------------------------------------------

    def build_status_request(self, query_types: Optional[List[int]] = None) -> bytes:
        """
        Build a StatusRequest message.

        Args:
            query_types: List of StatusRequestTypes (default: [All])

        Returns:
            Serialized FlatBuffers message (not yet COBS-encoded)
        """
        builder = flatbuffers.Builder(256)

        # Build query vector
        if query_types is None:
            query_types = [StatusRequestTypes.StatusRequestTypes.All]

        StatusRequest.StatusRequestStartQueryVector(builder, len(query_types))
        for qtype in reversed(query_types):
            builder.PrependInt8(qtype)
        query_vec = builder.EndVector()

        # Build StatusRequest
        StatusRequest.StatusRequestStart(builder)
        StatusRequest.StatusRequestAddQuery(builder, query_vec)
        status_req = StatusRequest.StatusRequestEnd(builder)

        # Build RequestPacket
        RequestPacket.RequestPacketStart(builder)
        RequestPacket.RequestPacketAddSequence(builder, self._next_sequence())
        RequestPacket.RequestPacketAddPacketType(builder, RequestPacketContents.RequestPacketContents.StatusRequest)
        RequestPacket.RequestPacketAddPacket(builder, status_req)
        request = RequestPacket.RequestPacketEnd(builder)

        builder.Finish(request)
        return bytes(builder.Output())

    def build_configuration_request(
        self,
        mode: Optional[str] = None,
        mode_config: Optional[Dict[str, Any]] = None,
        psu_enable: Optional[bool] = None,
        psu_voltage_mv: Optional[int] = None,
        psu_current_ma: Optional[int] = None,
        pullup_enable: Optional[bool] = None,
        **kwargs
    ) -> bytes:
        """
        Build a ConfigurationRequest message.

        Args:
            mode: Mode name to switch to ("SPI", "I2C", "UART", etc.)
            mode_config: Dict of mode-specific configuration
            psu_enable: Enable/disable power supply
            psu_voltage_mv: Set PSU voltage in millivolts
            psu_current_ma: Set PSU current limit in milliamps
            pullup_enable: Enable/disable pull-up resistors
            **kwargs: Additional configuration fields

        Returns:
            Serialized FlatBuffers message
        """
        builder = flatbuffers.Builder(512)

        # Build mode string
        mode_str = None
        if mode:
            mode_str = builder.CreateString(mode)

        # Build ModeConfiguration if provided
        mode_config_obj = None
        if mode_config:
            ModeConfiguration.ModeConfigurationStart(builder)
            if 'speed' in mode_config:
                ModeConfiguration.ModeConfigurationAddSpeed(builder, mode_config['speed'])
            if 'data_bits' in mode_config:
                ModeConfiguration.ModeConfigurationAddDataBits(builder, mode_config['data_bits'])
            if 'clock_polarity' in mode_config:
                ModeConfiguration.ModeConfigurationAddClockPolarity(builder, mode_config['clock_polarity'])
            if 'clock_phase' in mode_config:
                ModeConfiguration.ModeConfigurationAddClockPhase(builder, mode_config['clock_phase'])
            if 'chip_select_idle' in mode_config:
                ModeConfiguration.ModeConfigurationAddChipSelectIdle(builder, mode_config['chip_select_idle'])
            mode_config_obj = ModeConfiguration.ModeConfigurationEnd(builder)

        # Build ConfigurationRequest
        ConfigurationRequest.ConfigurationRequestStart(builder)

        if mode_str:
            ConfigurationRequest.ConfigurationRequestAddMode(builder, mode_str)
        if mode_config_obj:
            ConfigurationRequest.ConfigurationRequestAddModeConfiguration(builder, mode_config_obj)

        if psu_enable is not None:
            if psu_enable:
                ConfigurationRequest.ConfigurationRequestAddPsuEnable(builder, True)
            else:
                ConfigurationRequest.ConfigurationRequestAddPsuDisable(builder, True)

        if psu_voltage_mv is not None:
            ConfigurationRequest.ConfigurationRequestAddPsuSetMv(builder, psu_voltage_mv)
        if psu_current_ma is not None:
            ConfigurationRequest.ConfigurationRequestAddPsuSetMa(builder, psu_current_ma)

        if pullup_enable is not None:
            if pullup_enable:
                ConfigurationRequest.ConfigurationRequestAddPullupEnable(builder, True)
            else:
                ConfigurationRequest.ConfigurationRequestAddPullupDisable(builder, True)

        config_req = ConfigurationRequest.ConfigurationRequestEnd(builder)

        # Build RequestPacket
        RequestPacket.RequestPacketStart(builder)
        RequestPacket.RequestPacketAddSequence(builder, self._next_sequence())
        RequestPacket.RequestPacketAddPacketType(builder, RequestPacketContents.RequestPacketContents.ConfigurationRequest)
        RequestPacket.RequestPacketAddPacket(builder, config_req)
        request = RequestPacket.RequestPacketEnd(builder)

        builder.Finish(request)
        return bytes(builder.Output())

    def build_data_request(
        self,
        write_data: Optional[bytes] = None,
        read_len: int = 0,
        start: bool = False,
        stop: bool = False,
        start_alt: bool = False,
        stop_alt: bool = False
    ) -> bytes:
        """
        Build a DataRequest message for bus transactions.

        Args:
            write_data: Bytes to write to bus
            read_len: Number of bytes to read
            start: Assert START condition (I2C) or CS low (SPI)
            stop: De-assert STOP condition (I2C) or CS high (SPI)
            start_alt: Alt START
            stop_alt: Alt STOP

        Returns:
            Serialized FlatBuffers message
        """
        builder = flatbuffers.Builder(512)

        # Build write data vector
        write_vec = None
        if write_data:
            DataRequest.DataRequestStartDataWriteVector(builder, len(write_data))
            for byte in reversed(write_data):
                builder.PrependUint8(byte)
            write_vec = builder.EndVector()

        # Build DataRequest
        DataRequest.DataRequestStart(builder)

        if start:
            DataRequest.DataRequestAddStartMain(builder, True)
        if stop:
            DataRequest.DataRequestAddStopMain(builder, True)
        if start_alt:
            DataRequest.DataRequestAddStartAlt(builder, True)
        if stop_alt:
            DataRequest.DataRequestAddStopAlt(builder, True)

        if write_vec:
            DataRequest.DataRequestAddDataWrite(builder, write_vec)

        if read_len > 0:
            DataRequest.DataRequestAddBytesRead(builder, read_len)

        data_req = DataRequest.DataRequestEnd(builder)

        # Build RequestPacket
        RequestPacket.RequestPacketStart(builder)
        RequestPacket.RequestPacketAddSequence(builder, self._next_sequence())
        RequestPacket.RequestPacketAddPacketType(builder, RequestPacketContents.RequestPacketContents.DataRequest)
        RequestPacket.RequestPacketAddPacket(builder, data_req)
        request = RequestPacket.RequestPacketEnd(builder)

        builder.Finish(request)
        return bytes(builder.Output())

    # --------------------------------------------------------------------------
    # Message Parsers
    # --------------------------------------------------------------------------

    def parse_response(self, data: bytes) -> Optional[Dict[str, Any]]:
        """
        Parse a ResponsePacket.

        Args:
            data: Raw FlatBuffers data (after COBS decoding)

        Returns:
            Dictionary with response data or None on error
        """
        try:
            response = ResponsePacket.ResponsePacket.GetRootAs(data, 0)

            result = {
                'sequence': response.Sequence(),
                'type': response.PacketType(),
            }

            # Parse based on response type
            if response.PacketType() == ResponsePacketContents.ResponsePacketContents.StatusResponse:
                status = StatusResponse.StatusResponse()
                status.Init(response.Packet().Bytes, response.Packet().Pos)
                result['data'] = self._parse_status_response(status)

            elif response.PacketType() == ResponsePacketContents.ResponsePacketContents.ConfigurationResponse:
                config = ConfigurationResponse.ConfigurationResponse()
                config.Init(response.Packet().Bytes, response.Packet().Pos)
                result['data'] = self._parse_configuration_response(config)

            elif response.PacketType() == ResponsePacketContents.ResponsePacketContents.DataResponse:
                data_resp = DataResponse.DataResponse()
                data_resp.Init(response.Packet().Bytes, response.Packet().Pos)
                result['data'] = self._parse_data_response(data_resp)

            return result

        except Exception as e:
            print(f"[BPIO2] Parse error: {e}")
            return None

    def _parse_status_response(self, status: StatusResponse.StatusResponse) -> Dict[str, Any]:
        """Parse StatusResponse fields."""
        data = {}

        if status.Error():
            data['error'] = status.Error().decode('utf-8')

        data['version'] = {
            'flatbuffers_major': status.VersionFlatbuffersMajor(),
            'flatbuffers_minor': status.VersionFlatbuffersMinor(),
            'hardware_major': status.VersionHardwareMajor(),
            'hardware_minor': status.VersionHardwareMinor(),
            'firmware_major': status.VersionFirmwareMajor(),
            'firmware_minor': status.VersionFirmwareMinor(),
        }

        if status.VersionFirmwareGitHash():
            data['version']['git_hash'] = status.VersionFirmwareGitHash().decode('utf-8')
        if status.VersionFirmwareDate():
            data['version']['date'] = status.VersionFirmwareDate().decode('utf-8')

        # Mode info
        if status.ModeCurrent():
            data['mode'] = status.ModeCurrent().decode('utf-8')

        # Modes available
        if status.ModesAvailableLength() > 0:
            data['modes_available'] = [
                status.ModesAvailable(i).decode('utf-8')
                for i in range(status.ModesAvailableLength())
            ]

        # PSU status
        data['psu'] = {
            'enabled': status.PsuEnabled(),
            'set_mv': status.PsuSetMv(),
            'set_ma': status.PsuSetMa(),
            'measured_mv': status.PsuMeasuredMv(),
            'measured_ma': status.PsuMeasuredMa(),
            'current_error': status.PsuCurrentError(),
        }

        # Pull-up status
        data['pullup_enabled'] = status.PullupEnabled()

        # ADC readings
        if status.AdcMvLength() > 0:
            data['adc_mv'] = [status.AdcMv(i) for i in range(status.AdcMvLength())]

        # IO status
        data['io'] = {
            'direction': status.IoDirection(),
            'value': status.IoValue(),
        }

        return data

    def _parse_configuration_response(self, config: ConfigurationResponse.ConfigurationResponse) -> Dict[str, Any]:
        """Parse ConfigurationResponse fields."""
        data = {}
        if config.Error():
            data['error'] = config.Error().decode('utf-8')
        return data

    def _parse_data_response(self, data_resp: DataResponse.DataResponse) -> Dict[str, Any]:
        """Parse DataResponse fields."""
        data = {}

        if data_resp.Error():
            data['error'] = data_resp.Error().decode('utf-8')

        if data_resp.DataReadLength() > 0:
            data['data_read'] = bytes([
                data_resp.DataRead(i)
                for i in range(data_resp.DataReadLength())
            ])

        return data

    # --------------------------------------------------------------------------
    # COBS Encoding/Decoding
    # --------------------------------------------------------------------------

    @staticmethod
    def encode_message(flatbuffer_data: bytes) -> bytes:
        """
        Encode FlatBuffer message with COBS framing.

        Args:
            flatbuffer_data: Raw FlatBuffers serialized data

        Returns:
            COBS-encoded message with 0x00 terminator
        """
        encoded = cobs.encode(flatbuffer_data)
        return encoded + b'\x00'  # Add frame terminator

    @staticmethod
    def decode_message(cobs_data: bytes) -> bytes:
        """
        Decode COBS-encoded message.

        Args:
            cobs_data: COBS-encoded data (without terminator)

        Returns:
            Decoded FlatBuffers data
        """
        return cobs.decode(cobs_data)
