from .bpio_base import BPIOBase

class BPIOUART(BPIOBase):
    """UART wrapper for Bus Pirate BPIO2"""

    def __init__(self, client):
        super().__init__(client)

    def configure(self, speed=115200, data_bits=8, parity=False, stop_bits=1,
                  flow_control=False, signal_inversion=False, **kwargs):
        """Configure UART mode

        Args:
            speed: Baud rate (default: 115200)
            data_bits: Data bits (default: 8)
            parity: Parity enable (default: False for no parity)
            stop_bits: Stop bits (default: 1)
            flow_control: Flow control enable (default: False)
            signal_inversion: Signal inversion (default: False)
            **kwargs: Additional configuration (psu_enable, pullup_enable, etc.)
        """
        kwargs['mode'] = 'UART'

        # Get existing mode_configuration or create new one
        mode_configuration = kwargs.get('mode_configuration', {})

        # Set UART-specific parameters
        mode_configuration['speed'] = speed
        mode_configuration['data_bits'] = data_bits
        mode_configuration['parity'] = parity
        mode_configuration['stop_bits'] = stop_bits
        mode_configuration['flow_control'] = flow_control
        mode_configuration['signal_inversion'] = signal_inversion

        # Replace mode_configuration in kwargs
        kwargs['mode_configuration'] = mode_configuration

        success = self.client.configuration_request(**kwargs)
        self.configured = success
        return success

    def write(self, data):
        """Write data to UART

        Args:
            data: Bytes to write

        Returns:
            Result of data_request
        """
        if not self.config_check():
            return None

        return self.client.data_request(
            data_write=data,
        )

    def read(self, num_bytes):
        """Read bytes from UART

        Args:
            num_bytes: Number of bytes to read

        Returns:
            Bytes read from UART
        """
        if not self.config_check():
            return None

        return self.client.data_request(
            bytes_read=num_bytes,
        )
