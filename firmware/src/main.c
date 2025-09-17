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
    isWaitingForSync = 0;
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

        // Load from code
        if (loadFromCode) {
            uint16 i;
            for (i = 0; i < MAX_NOTES; i++) {
                note[i] = builtin_note[loadSongId][nodeid][i];
                duration[i] = builtin_duration[loadSongId][nodeid][i];
                if (note[i] == 254) break;
            }
            loadFromCode = 0;
            loadSongId = 0;
        }
    }

    ledSel = 1;

MUSIC_PLAYBACK:
    while (isMusicPlaying && !isWaitingForSync) {
        play_music_note();
    }
    if (isWaitingForSync)
        goto MUSIC_PLAYBACK;
    goto PREPARE;
}
