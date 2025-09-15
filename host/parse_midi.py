import logging
from dataclasses import dataclass
from typing import List, Tuple

from mido import MidiFile

# Maximum duration in ms that can be represented in 2 bytes
DURATION_MAX = (1 << 16) - 1


@dataclass
class MidiConfig:
    """Configuration class for MIDI parsing"""

    rest_symbol: int = 255
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

    # Extract events from each track
    for track in mid.tracks:
        abs_time = 0  # Current time in absolute ticks
        last_note_time = 0  # Last time a note was released
        current_track_events = []  # Store events for the current track

        for msg in track:
            abs_time += msg.time

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
        if len(current_track_events) > 0:
            event_list.append(current_track_events)

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


if __name__ == "__main__":
    config = MidiConfig()
    event_list = parse_midi_to_events("music/overworld.mid", config)
    print(len(event_list[1]))
    print(events_to_binary(event_list[1]).hex())
