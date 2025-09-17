import logging
from dataclasses import dataclass
from typing import List, Tuple

import mido
from mido import MidiFile

# Maximum duration in ms that can be represented in 2 bytes
DURATION_MAX = (1 << 16) - 1


@dataclass
class MidiConfig:
    """Configuration class for MIDI parsing"""

    enable_sync: bool = True
    rest_symbol: int = 255
    marker_symbol: int = 253
    default_tempo: int = 500000  # μs per beat
    min_rest_ms: int = 5  # rest under this will be ignored


def parse_midi_to_events(
    midi_file: str, config: MidiConfig
) -> List[List[Tuple[int, int, int]]]:
    """
    Parse MIDIFile and return event list

    Args:
        config: MIDI configuration object

    Returns:
        event_list: Event list for every track, in the format of [(start_time, note/rest_symbol, duration_ms), ...]
    """
    # Load Midi file
    mid = MidiFile(midi_file)
    ticks_per_beat = mid.ticks_per_beat
    tempo = config.default_tempo

    note_stack = {}
    event_list = []
    marker_list = []

    # Extract events from each track
    for track in mid.tracks:
        abs_time = 0  # Current time in absolute ticks
        last_note_time = 0  # Last time a note was released
        # Event for the current track: (start_time, note/rest_symbol, duration_ms)
        current_track_events: list[tuple[int, int, int]] = []
        marker_time = None

        for msg in track:
            abs_time += msg.time
            if marker_time and abs_time > marker_time:
                if config.enable_sync:
                    marker_list.append(marker_time)
                marker_time = None
            if msg.type == "set_tempo":
                tempo = msg.tempo
            elif msg.type == "note_on" and msg.velocity > 0:
                note_stack[msg.note] = abs_time
                rest_ticks = abs_time - last_note_time
                rest_ms = int((rest_ticks * tempo) / (ticks_per_beat * 1000))
                if rest_ms >= config.min_rest_ms:
                    if rest_ms >= DURATION_MAX:
                        rest_ms = DURATION_MAX
                        logging.warning(
                            f"Rest duration too long, clipped to {DURATION_MAX} ms"
                        )
                    current_track_events.append(
                        (last_note_time, config.rest_symbol, rest_ms)
                    )
            elif msg.type == "note_off" or (
                msg.type == "note_on" and msg.velocity == 0
            ):
                if msg.note in note_stack:
                    start_time = note_stack[msg.note]
                    duration_ticks = abs_time - start_time
                    duration_ms = int(
                        (duration_ticks * tempo) / (ticks_per_beat * 1000)
                    )
                    if duration_ms >= DURATION_MAX:
                        duration_ms = DURATION_MAX
                        logging.warning(
                            f"Note duration too long, clipped to {DURATION_MAX} ms"
                        )
                    current_track_events.append((start_time, msg.note, duration_ms))
                    del note_stack[msg.note]
                    last_note_time = abs_time
            elif msg.type == "marker":
                marker_time = abs_time

        if len(current_track_events) > 0:
            event_list.append(current_track_events)

    for track in event_list:
        for marker_time in marker_list:
            track.append((marker_time, config.marker_symbol, 0))
        track.sort(key=lambda event: (event[0], event[1] != config.marker_symbol))
    return event_list


def events_to_binary(track: List[Tuple[int, int, int]]) -> bytes:
    checksum = 0
    ret = bytearray(b"\x10\x00\x00")
    cnt = 0
    for event in track:
        _, note, duration = event
        ret += bytes([note, duration >> 8, duration & 0xFF])
        cnt += 1
        checksum ^= int(note)
        checksum ^= int(duration & 0xFF)
        checksum ^= int(duration >> 8)
    cnt += 1
    cnt *= 3
    checksum ^= 0xFE

    ret += bytes([0xFE, 0, 0, checksum])
    ret[1] = cnt >> 8
    ret[2] = cnt & 0xFF
    ret = bytes(ret)
    return ret


def midi_to_binary_list(midi_file: str, config: MidiConfig) -> list[bytes]:
    event_list = parse_midi_to_events(midi_file, config)
    binary_list = [events_to_binary(track) for track in event_list]
    return binary_list


def events_to_c_arrays(event_list: List[List[Tuple[int, int, int]]]) -> Tuple[str, str]:
    """
    Convert event list to C-style arrays for notes and durations

    Args:
        event_list: List of tracks, each track contains (start_time, note, duration_ms) tuples

    Returns:
        Tuple of (notes_array_string, durations_array_string)
    """
    notes_lines = []
    durations_lines = []

    for track_idx, track in enumerate(event_list):
        # Sort events by start time
        sorted_events = sorted(
            track, key=lambda x: (x[0], x[1] != 253)
        )  # 253 is marker_symbol

        track_notes = []
        track_durations = []

        for _, note, duration in sorted_events:
            track_notes.append(str(note))
            track_durations.append(str(duration))

        # Add end marker (note: 254, duration: 0) at the end of each track
        track_notes.append("254")
        track_durations.append("0")

        # Format track data with line wrapping for better readability
        notes_str = ", ".join(track_notes)
        durations_str = ", ".join(track_durations)

        # Wrap long lines at 80 characters
        def wrap_line(line, indent="        "):
            if len(line) <= 80:
                return line + ","

            wrapped_lines = []
            current_line = ""

            for item in line.split(", "):
                if len(current_line + item + ", ") > 80 and current_line:
                    wrapped_lines.append(current_line.rstrip(", ") + ",")
                    current_line = indent + item + ", "
                else:
                    current_line += item + ", "

            if current_line:
                wrapped_lines.append(current_line.rstrip(", ") + ",")

            return "\n".join(wrapped_lines)

        # Format track data
        notes_wrapped = wrap_line(notes_str, "        ")
        durations_wrapped = wrap_line(durations_str, "        ")

        notes_line = f"        // Track {track_idx + 1}\n        {{{notes_wrapped}}}"
        durations_line = (
            f"        // Track {track_idx + 1}\n        {{{durations_wrapped}}}"
        )

        notes_lines.append(notes_line)
        durations_lines.append(durations_line)

    # Join all tracks
    notes_array = ",\n".join(notes_lines)
    durations_array = ",\n".join(durations_lines)

    return notes_array, durations_array


if __name__ == "__main__":
    config = MidiConfig()
    event_list = parse_midi_to_events("music/overworld.mid", config)

    # Generate C-style arrays
    notes_array, durations_array = events_to_c_arrays(event_list)

    print("// Notes array (replace content after // SONG 1):")
    print("{")
    print(notes_array)
    print("}")
    print()
    print("// Durations array (replace content after // SONG 1):")
    print("{")
    print(durations_array)
    print("}")
