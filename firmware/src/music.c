#include "music.h"
#include "core.h"
#include "delay.h"

bit isWaitingForSync = 0;

void play_music_note() {
    uint8 current_note = note[pos];
    P0 = (pos & 0xff);
    if (current_note <= 127) {
        TH0 = th0_table[current_note];
        TL0 = tl0_table[current_note];
        TR0 = 1;
        delay(duration[pos]);
        TR0 = 0;
        beep = 0;
        pos++;
    } else if (current_note == 255) {
        delay(duration[pos]);
        pos++;
    } else if (current_note == 254) {
        pos = 0;
        isMusicPlaying = 0;
        isWaitingForSync = 0;
        if (nodeid == 0)
            sendData(0x20);
    } else if (current_note == 253) {
        // Sync signal
        if (nodeid == 0)
            sendData(0x70);
        isWaitingForSync = 1;
        pos++;
    }
}
