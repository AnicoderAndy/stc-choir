import logging

import serial
import serial.tools.list_ports

BAUDRATE = 115200


def get_serial_ports() -> tuple[list[str], list[str]]:
    """Get a list of available serial ports and their descriptions.

    Returns:
        tuple[list[str], list[str]]: A tuple containing two lists:
            - List of available serial port names.
            - List of port descriptions (including name and description).
    """
    ports = serial.tools.list_ports.comports()
    available_ports = [port.device for port in ports]

    port_descriptions: list[str] = []
    for port in ports:
        # Display port name and description
        if port.description and port.description != "n/a":
            port_descriptions.append(f"{port.device} - {port.description}")
        else:
            port_descriptions.append(port.device)

    return (available_ports, port_descriptions)


def open_serial_port(port: str, *, timeout: None | float = 2.0) -> serial.Serial:
    """Open the specified serial port with predefined settings.

    Args:
        port (str): Serial port name.

    Returns:
        serial.Serial: Opened serial port object.
    """
    ser = serial.Serial(
        port=port,
        baudrate=BAUDRATE,
        bytesize=serial.EIGHTBITS,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        timeout=timeout,
    )
    logging.debug(f"Port {port} opened successfully.")
    return ser


def send_command(ser: serial.Serial, data: bytes):
    """Send data to the specified serial port."""
    ser.write(data)
    ser.flush()

    logging.info(f"Command 0x{data.hex()} sent successfully to port {ser.name}")


def send_music_data(
    ser: serial.Serial, byte_list: list[bytes], track_assignments: dict[int, str]
) -> int:
    """Send music data to the specified serial port.

    Args:
        ser (serial.Serial): Serial port name.
        byte_list (list[bytes]): List of byte data for each track.
        track_assignments (dict[int, str]): Mapping of track index to node ID.

    Returns:
        int: Number of successfully transmitted tracks
    """
    success_count = 0
    processed_tracks = 0

    for track_index, track_data in enumerate(byte_list):
        # Get node ID from assignments, default to hex of track index
        node_id = track_assignments.get(track_index, hex(track_index).upper()[2:])

        # Skip unassigned tracks
        if node_id == "不分配":
            logging.debug(f"Skip {track_index} (unassigned)")
            continue

        processed_tracks += 1
        node_id_int = int(node_id, 16)

        logging.info(f"Start transmitting track {track_index} to node {node_id}...")

        if send_track_data(ser, node_id_int, track_data):
            success_count += 1
            logging.debug(f"Track {track_index} transmitted successfully.")
        else:
            logging.error(f"Track {track_index} transmission failed.")

    return success_count


def preview_track(ser: serial.Serial, node_id: int, track_data: bytes) -> bool:
    """Preview a single track on the specified node.

    Args:
        ser (serial.Serial): Serial port object.
        node_id (int): The node ID to send data to.
        track_data (bytes): The track data to be previewed.

    Raises:
        RuntimeError: If sending the track fails.

    Returns:
        bool: =True if preview command is sent successfully.
    """
    result = send_track_data(ser, node_id, track_data)
    if result:
        logging.info(f"Track successfully sent to node {node_id}.")
        cmd = 0x50 | (node_id & 0x0F)
        send_command(ser, bytes([cmd]))
        return True
    else:
        raise RuntimeError(f"Failed to send track to node {node_id}.")


def send_track_data(ser: serial.Serial, node_id: int, track_data: bytes) -> bool:
    """Send a single track data packet to the specified node.


    Args:
        ser (str): Serial port object.
        node_id (int): The node ID to send data to.
        track_data (byte): The complete track data packet.
            (NOTE: You don't have to modify the header by yourself, this function
            will do it for you. But you need to make sure other data is correct,
            including size and checksum.)

    Returns:
        bool: True if transmission is successful, False otherwise.
    """
    try:
        # track_data already includes header, size, data, checksum
        # only need to modify the header byte
        ser.read_all()  # Clear input buffer
        if len(track_data) == 0:
            logging.warning(f"Track data for node {node_id} is empty. Skipping.")
            return False

        # Create a mutable bytearray from the original track data
        packet = bytearray(track_data)
        new_header = 0x10 | (node_id & 0x0F)
        packet[0] = new_header

        # Send the packet
        logging.debug(f"Sending data ({len(packet)} bytes) to node {node_id}")
        ser.write(packet)
        ser.flush()

        # Wait for response
        response = ser.read(1)
        if len(response) == 1:
            response_byte = response[0]
            logging.debug(f"Response received: {hex(response_byte)}")

            if response_byte == 0xE0:  # Success
                return True
            elif response_byte == 0xF0:  # Fail
                logging.warning(f"Firmware reported failure for node {node_id}")
                return False
            elif response_byte == 0xF1:  # Size error
                logging.warning(f"Size error reported by node {node_id}")
                return False
            else:
                logging.warning(
                    f"Unknown response from node {node_id}: {hex(response_byte)}"
                )
                return False
        else:
            logging.warning(f"No response received from node {node_id}")
            return False

    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return False
