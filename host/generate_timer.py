"""
This script generates timer values for MIDI notes.
If you want to change the firmware frequency or other
related stuff, edit and run this script for convenience.
"""

F_TIMER = 11059200  # System clock frequency, in the unit of Hz
TIMER_CYCLE = 12  # Ticks per timer count, 12 for 8051 timer
REST_TH = 0xFF  # If frequency is unavailable, use rest value
REST_TL = 0xFF

th0_list = []
tl0_list = []

for midi in range(128):
    # Calculate frequency from MIDI note number
    freq = 440.0 * (2 ** ((midi - 69) / 12))

    # Calculate timer value
    y = int(F_TIMER / (2 * TIMER_CYCLE * freq))

    # Handle out of range values
    if y <= 0 or y >= 65536:
        th0 = REST_TH
        tl0 = REST_TL
    else:
        val = 65536 - y
        th0 = val // 256
        tl0 = val % 256

    th0_list.append(th0)
    tl0_list.append(tl0)

# Print the results in C array format
print("unsigned char code th0_table[128] = {")
for i, val in enumerate(th0_list):
    print(f"  {val},", end="\n" if (i + 1) % 12 == 0 else " ")
print("};\n")

print("unsigned char code tl0_table[128] = {")
for i, val in enumerate(tl0_list):
    print(f"  {val},", end="\n" if (i + 1) % 12 == 0 else " ")
print("};")
