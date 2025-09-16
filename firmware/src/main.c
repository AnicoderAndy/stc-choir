#include "core.h"

uint16 pos = 0;
uint8 nodeid = 0;

void main() {
    sysInit();

    nodeid = nvm_read(0);
    if (nodeid > 0x0f) {
        nodeid = 0;
    }

PREPARE:
    while (1) {
        // Display node ID on digital tube
        bit is_nodeid_changed = 0;
        ledSel = 0;
        P2 = 0;
        P0 = dtDecode[nodeid];

        // Change node ID with keys
        if (key1 == 0) {
            delay(10);
            if (key1 == 0) {
                nodeid++;
                if (nodeid == 0x10)
                    nodeid = 0;
                while (key1 == 0);
                is_nodeid_changed = 1;
            }
        }
        if (key2 == 0) {
            delay(10);
            if (key2 == 0) {
                nodeid--;
                if (nodeid == 0xff)
                    nodeid = 0x0f;
                while (key2 == 0);
                is_nodeid_changed = 1;
            }
        }

        if (isMusicPlaying) {
            break;
        }

        if (is_nodeid_changed) {
            nvm_write(0, nodeid);
        }

        // Check if we need to send response from interrupt
        if (sendResponse) {
            sendData(responseData);
            sendResponse = 0;
        }
    }

    ledSel = 1;
    while (isMusicPlaying) {
        play_music_note();
    }
    goto PREPARE;
}
