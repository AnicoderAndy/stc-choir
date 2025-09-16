#ifndef GLOBALS_H
#define GLOBALS_H
#ifndef __VSCODE_C51__
#define INTERRUPT(x) interrupt x
#define USING(x) using x
#else
#define INTERRUPT(x)
#define USING(x)
#endif
#include "STC15F2K60S2.h"
#define uint8 unsigned char
#define int8 char
#define uint16 unsigned int
#define int16 int
#define uint32 unsigned long
#define int32 long

// Define the bit-addressable variables
sbit beep = P3 ^ 4;    // Buzzer
sbit key1 = P3 ^ 2;    // Key 1
sbit key2 = P3 ^ 3;    // Key 2
sbit ledSel = P2 ^ 3;  // LED selection
sbit m485TRn = P3 ^ 7; // MAX485 Transmit/Receive control
sbit SDA = P4 ^ 0;     // I2C Data
sbit SCL = P5 ^ 5;     // I2C Clock

// UART2 related
// Use bit mask instead of sbit, because these registers are not bit-addressable
#define ES2_BIT 0x01   // Bit 0 of IE2
#define PS2_BIT 0x01   // Bit 0 of IP2
#define S2RI_BIT 0x01  // Bit 0 of S2CON
#define S2TI_BIT 0x02  // Bit 1 of S2CON
#define S2REN_BIT 0x10 // Bit 4 of S2CON

// UART related
extern bit uartBusy;       // UART busy flag
extern bit dataReady;      // Flag indicating data is ready to be processed
extern bit sendResponse;   // Flag to send response in main loop
extern uint8 responseData; // Response data to send
extern uint16 uartDtSz;    // Size of data to be received from UART
extern uint16 uartPos;     // Position in the UART buffer
extern bit uartDtSzH;      // High byte of data size flag
extern bit uartDtSzL;      // Low byte of data size flag
extern uint8 nodeid;       // Node ID for data transmission
// Music related
extern uint8 xdata note[];
extern uint16 xdata duration[];
// Playback related
extern bit isMusicPlaying;   // Flag indicating music is playing
extern bit isWaitingForSync; // Flag for waiting for sync signal
extern uint16 pos;           // Current position in music playback

/// @brief Digital tube decode table.
extern uint8 code dtDecode[];
/// @brief MIDI note number to TH0 conversion table.
extern uint8 code th0_table[];
/// @brief MIDI note number to TL0 conversion table.
extern uint8 code tl0_table[128];

#endif // GLOBALS_H