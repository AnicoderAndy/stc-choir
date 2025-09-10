import logging

import serial
import serial.tools.list_ports

BAUDRATE = 115200


def send_command(port: str, data: bytes):
    """Send data to the specified serial port."""
    ser = None
    try:
        # Open the serial port
        ser = serial.Serial(
            port=port,
            baudrate=BAUDRATE,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=2.0,
        )

        logging.debug(f"Port {port} opened successfully, sending data...")

        ser.write(data)
        ser.flush()

        logging.info(f"Command 0x{data.hex()} sent successfully to port {port}")
    except serial.SerialException as e:
        logging.error(f"Serial port error: {e}")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
    finally:
        if ser and ser.is_open:
            ser.close()
            logging.debug(f"Port {port} closed.")


def send_music_data(
    port: str, byte_list: list[bytes], track_assignments: dict[int, str]
) -> int:
    """Send music data to the specified serial port.

    Args:
        port (str): Serial port name.
        byte_list (list[bytes]): List of byte data for each track.
        track_assignments (dict[int, str]): Mapping of track index to node ID.

    Returns:
        int: Number of successfully transmitted tracks
    """
    ser = None
    try:
        ser = serial.Serial(
            port=port,
            baudrate=BAUDRATE,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=2.0,
        )

        logging.debug(f"Port {port} opened successfully, sending music data...")

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

            if _send_track_data(ser, node_id_int, track_data):
                success_count += 1
                logging.debug(f"Track {track_index} transmitted successfully.")
            else:
                logging.error(f"Track {track_index} transmission failed.")

    except Exception as e:
        logging.error(f"Unexpected error: {e}")
    finally:
        if ser and ser.is_open:
            ser.close()
            logging.debug(f"Port {port} closed.")

    return success_count


def _send_track_data(ser, node_id, track_data):
    """Send a single track data packet to the specified node."""
    try:
        # track_data already includes header, size, data, checksum
        # only need to modify the header byte
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
