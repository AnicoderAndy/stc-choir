#include "core.h"
#include "nvm.h"
#define MAX_NOTES 600
// UART1 related
bit uartBusy = 1;       // UART busy flag
bit dataReady = 0;      // Flag indicating data is ready to be processed
bit isMusicPlaying = 0; // Flag indicating music is playing
bit sendResponse = 0;   // Flag to send response in main loop
uint8 responseData = 0; // Response data to send
uint8 event = 0;
uint8 param = 0;
uint16 uartDtSz = 0;    // Size of data to be received from UART
uint16 uartPos = 0;     // Position in the UART buffer
uint8 uartCheckSum = 0; // XOR checksum for data integrity
uint16 notePos = 0;     // Position in the note array
bit uartDtSzH = 0;      // High byte of data size flag
bit uartDtSzL = 0;      // Low byte of data size flag

// Music related
uint8 xdata note[MAX_NOTES];
uint16 xdata duration[MAX_NOTES];

uint8 code dtDecode[17] = {0x3F, 0x06, 0x5B, 0x4F, 0x66, 0x6D, 0x7D, 0x07, 0x7F,
                           0x6F, 0x77, 0x7C, 0x39, 0x5E, 0x79, 0x71, 0x00};

uint8 code th0_table[128] = {
    35,  48,  59,  70,  81,  91,  100, 109, 117, 125, 132, 139, 145, 152, 157, 163, 168, 173, 178,
    182, 186, 190, 194, 197, 200, 204, 206, 209, 212, 214, 217, 219, 221, 223, 225, 226, 228, 230,
    231, 232, 234, 235, 236, 237, 238, 239, 240, 241, 242, 243, 243, 244, 245, 245, 246, 246, 247,
    247, 248, 248, 249, 249, 249, 250, 250, 250, 251, 251, 251, 251, 252, 252, 252, 252, 252, 253,
    253, 253, 253, 253, 253, 253, 254, 254, 254, 254, 254, 254, 254, 254, 254, 254, 254, 254, 255,
    255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255,
    255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255,
};

uint8 code tl0_table[128] = {
    215, 50,  220, 222, 66,  17,  83,  16,  79,  24,  113, 96,  236, 25,  238, 111, 161, 137, 42,
    136, 168, 140, 57,  176, 246, 13,  247, 184, 81,  197, 21,  68,  84,  70,  29,  216, 123, 7,
    124, 220, 41,  99,  139, 162, 170, 163, 143, 108, 62,  4,   190, 110, 21,  178, 70,  209, 85,
    210, 72,  182, 31,  130, 223, 55,  139, 217, 35,  105, 171, 233, 36,  91,  144, 193, 240, 28,
    70,  109, 146, 181, 214, 245, 18,  46,  72,  97,  120, 142, 163, 183, 201, 219, 235, 251, 9,
    23,  36,  49,  60,  71,  82,  92,  101, 110, 118, 126, 133, 140, 146, 153, 158, 164, 169, 174,
    179, 183, 187, 191, 195, 198, 201, 205, 207, 210, 213, 215, 218, 220,
};

// Function prototypes
void event1(uint8 dt);

void sysInit() {
    // Display init.
    P0M0 = 0xff; // Set push-pull mode
    P0M1 = 0x00;
    P2M0 = 0x08;
    P2M1 = 0x00;
    P3M0 = 0x10;
    P3M1 = 0x00;
    ledSel = 1;
    P0 = 0;
    P_SW2 |= 0x01;
    m485TRn = 0; // Ready to receive

    beepInit();
    uartInit();
    interruptInit();
    IIC_init();
}

void beepInit() {
    AUXR &= 0x7F; // Timer clock is 12T mode
    TMOD &= 0xF0; // Set timer work mode
    TF0 = 0;      // Clear TF0 flag
    TR0 = 0;      // Do not start timer 0
    beep = 0;
}

void uartInit() {
    // 115200bps@11.0592MHz
    S2CON = 0x50; // 8 bits and variable baudrate
    AUXR |= 0x04; // Timer clock is 1T mode
    T2L = 0xE8;   // Initial timer value
    T2H = 0xFF;   // Initial timer value
    AUXR |= 0x10; // Timer2 start run
}

void interruptInit() {
    ET0 = 1;        // Enable Timer 0 interrupt
    IE2 |= ES2_BIT; // Enable UART2 interrupt
    EA = 1;         // Enable global interrupts
    PT0 = 1;        // Set Timer 0 interrupt priority to high
    IP2 |= PS2_BIT; // Set UART2 interrupt priority to high
}

void sendData(uint8 dt) {
    m485TRn = 1;
    S2BUF = dt;
    while (uartBusy);
    uartBusy = 1;
    m485TRn = 0; // Switch to receive mode
}

void fetchData() {
    uint8 dt = S2BUF;
    if (!event) {
        event = (dt & 0xf0) >> 4;
        param = (dt & 0x0f);
        switch (event) {
        case 0:
            break;
        case 1:
            uartDtSzH = 0;
            uartDtSzL = 0;
            uartPos = 0;
            notePos = 0;
            uartCheckSum = 0;
            dataReady = 0;
            break;
        case 2:
            // For host, ignore it
            event = 0;
            param = 0;
            break;
        case 3:
            pos = 0; // Reset playback position
            isMusicPlaying = 1;
            isWaitingForSync = 0;
            event = 0;
            param = 0;
            break;
        case 4:
            isMusicPlaying = 0;
            isWaitingForSync = 0;
            event = 0;
            param = 0;
            break;
        case 5:
            if (param == nodeid) {
                pos = 0;
                isMusicPlaying = 1;
                isWaitingForSync = 0;
            }
            event = 0;
            param = 0;
            break;
        case 6:
            if (param == nodeid) {
                isMusicPlaying = 0;
                isWaitingForSync = 0;
            }
            event = 0;
            param = 0;
            break;
        case 7:
            // For host, ignore it
            event = 0;
            param = 0;
            break;
        case 8:
            // Sync signal received
            isWaitingForSync = 0;
            event = 0;
            param = 0;
        case 0xe:
        case 0xf:
        default:
            // Data is for HOST, ignore it
            event = 0;
            param = 0;
        }
    } else {
        if (event == 1) {
            event1(dt);
        }
    }
}

/**
 * @brief Handle event 1: Receive music data
 *
 * @param dt The received byte
 */
void event1(uint8 dt) {
    // Receive music data
    if (!uartDtSzH) {
        uartDtSz = (dt << 8);
        uartDtSzH = 1; // High byte received
    } else if (!uartDtSzL) {
        uartDtSz |= dt;
        uartDtSzL = 1; // Low byte received
    } else if (nodeid == param) {
        if (uartDtSz / 3 > MAX_NOTES) {
            // Data size exceeds maximum note capacity
            // Ignore all data
            uartPos++;
        } else if (uartPos < uartDtSz) {
            // Store the received data in note and duration arrays
            switch (uartPos % 3) {
            case 0:
                note[notePos] = dt; // Store note
                break;
            case 1:
                duration[notePos] = (dt << 8); // Store high byte of duration
                break;
            case 2:
                duration[notePos] |= dt; // Store low byte of duration
                notePos++;
                break;
            }
            uartPos++;
            uartCheckSum ^= dt;
        } else if (uartPos == uartDtSz) {
            // Check byte
            if (dt == uartCheckSum) {
                responseData = 0xe0;
                sendResponse = 1;
                dataReady = 1;
            } else {
                responseData = 0xf0;
                sendResponse = 1;
                dataReady = 0; // Invalid data
            }
            uartPos++;
        }
        if (uartPos > uartDtSz) {
            event = 0;
            param = 0;
            if (uartDtSz / 3 > MAX_NOTES) {
                responseData = 0xf1; // Data size error
                sendResponse = 1;
                dataReady = 0;
            }
        }
    } else {
        // Not for this node, ignore the data
        if (uartPos <= uartDtSz) {
            uartPos++;
        }
        if (uartPos > uartDtSz) {
            event = 0;
            param = 0;
        }
    }
}

void t0InterruptHandler() INTERRUPT(1) { beep = ~beep; }

void uartInterruptHandler() INTERRUPT(8) USING(1) {
    if (S2CON & S2RI_BIT) {
        // Data received
        fetchData();
        S2CON &= ~S2RI_BIT; // Clear S2RI flag
    }
    if (S2CON & S2TI_BIT) {
        // Data transmitted
        uartBusy = 0;
        S2CON &= ~S2TI_BIT; // Clear S2TI flag
    }
}
