#include "core.h"

uint16 pos = 0;
uint8 nodeid = 0;

void playmusic() {
    uint8 current_note = note[pos];
    P0 = (pos & 0xff);
    if (current_note == 254) {
        pos = 0;
        isMusicPlaying = 0;
        return;
    } else if (current_note == 255) {
        delay(duration[pos]);
        pos++;
        return;
    } else {
        TH0 = th0_table[current_note];
        TL0 = tl0_table[current_note];
    }
    TR0 = 1;
    delay(duration[pos]);
    TR0 = 0;
    beep = 0;
    pos++;
}

void main() {
    sysInit();
    beepInit();
    uartInit();
    interruptInit();

PREPARE:
    while (1) {
        ledSel = 0;
        P2 = 0;
        P0 = dtDecode[nodeid];
        if (key1 == 0) {
            delay(10);
            if (key1 == 0) {
                nodeid++;
                if (nodeid == 0x10)
                    nodeid = 0;
                while (key1 == 0);
            }
        }
        if (key2 == 0) {
            delay(10);
            if (key2 == 0) {
                nodeid--;
                if (nodeid == 0xff)
                    nodeid = 0x0f;
                while (key2 == 0);
            }
        }

        if (isMusicPlaying) {
            break;
        }

        // Check if we need to send response from interrupt
        if (sendResponse) {
            sendData(responseData);
            sendResponse = 0;
        }
    }

    ledSel = 1;
    while (isMusicPlaying) {
        playmusic();
    }
    goto PREPARE;
}
