#include "core.h"

// UART1 related
bit uartBusy = 0;       // UART busy flag
bit dataReady = 0;      // Flag indicating data is ready to be processed
bit isMusicPlaying = 0; // Flag indicating music is playing
uint8 event = 0;
uint8 param = 0;
uint16 uartDtSz = 0;    // Size of data to be received from UART
uint16 uartPos = 0;     // Position in the UART buffer
uint8 uartCheckSum = 0; // XOR checksum for data integrity
uint16 notePos = 0;     // Position in the note array
bit uartDtSzH = 0;      // High byte of data size flag
bit uartDtSzL = 0;      // Low byte of data size flag

// Music related
uint8 xdata note[682];
uint16 xdata duration[682];

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

uint8 dtData[8] = {10, 10, 10, 10, 10, 10, 10, 10};
uint8 ledData = 0;

// Function prototypes
void event1(uint8 dt);

void sysInit() {
    // Display init.
    P0M0 = 0xff; // 设置推挽模式
    P0M1 = 0x00;
    P2M0 = 0x08;
    P2M1 = 0x00;
    P3M0 = 0x10;
    P3M1 = 0x00;
    ledSel = 1;
    P0 = 0;
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
    SCON = 0x50;  // 8 bits and variable baudrate
    AUXR |= 0x01; // UART 1 use Timer2 as baudrate generator
    AUXR |= 0x04; // Timer clock is 1T mode
    T2L = 0xE8;   // Initial timer value
    T2H = 0xFF;   // Initial timer value
    AUXR |= 0x10; // Timer2 start run
}

void interruptInit() {
    ET0 = 1; // Enable Timer 0 interrupt
    ES = 1;  // Enable UART interrupt
    EA = 1;  // Enable global interrupts
    PT0 = 1; // Set Timer 0 interrupt priority to high
    PS = 1;  // Set UART interrupt priority to high
}

void delay(uint16 t) {
    unsigned int j;
    for (; t > 0; t--)
        for (j = 800; j > 0; j--);
}

void display() {
    uint8 i;
    // Digital tube
    ledSel = 0;
    for (i = 0; i < 8; i++) {
        P0 = 0;
        P2 = i;
        P0 = dtDecode[dtData[i]];
        delay(1);
    }
    // LED
    ledSel = 1;
    P0 = ledData;
}

void sendData(uint8 dt) {
    while (uartBusy);
    uartBusy = 1;
    SBUF = dt;
}

void fetchData() {
    uint8 dt = SBUF;
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
            uartCheckSum = 0;  // 重置校验和
            dataReady = 0;
            break;
        case 2:
            // TODO: Toggle node display
            event = 0;
            param = 0;
            break;
        case 3:
            pos = 0;  // 重置音乐播放位置
            isMusicPlaying = 1;
            event = 0;
            param = 0;
            break;
        case 4:
            isMusicPlaying = 0;
            event = 0;
            param = 0;
            break;
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
        // Store the received data in note and duration arrays
        if (uartPos < uartDtSz) {
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
            RI = 0;
            if (dt == uartCheckSum) {
                sendData(0xe0);
                dataReady = 1;
            } else {
                sendData(0xf0);
                dataReady = 0;  // Invalid data
            }
            uartPos++;
        }
        if (uartPos > uartDtSz) {
            event = 0;
            param = 0;
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

void uartInterruptHandler() INTERRUPT(4) USING(1) {
    if (RI) {
        // Data received
        fetchData();
        RI = 0;
    }
    if (TI) {
        // Data transmitted
        TI = 0;
        uartBusy = 0;
    }
}
