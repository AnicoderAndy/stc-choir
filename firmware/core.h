#ifndef CORE_H
#define CORE_H
#include "STC15F2K60S2.h"
#include "intrins.h"
#include "types.h"
#include "nvm.h"

// UART related
extern bit uartBusy;    // UART busy flag
extern bit dataReady;   // Flag indicating data is ready to be processed
extern bit sendResponse; // Flag to send response in main loop
extern uint8 responseData; // Response data to send
extern uint16 uartDtSz; // Size of data to be received from UART
extern uint16 uartPos;  // Position in the UART buffer
extern bit uartDtSzH;   // High byte of data size flag
extern bit uartDtSzL;   // Low byte of data size flag
extern uint8 nodeid;    // Node ID for data transmission
// Music related
extern uint8 xdata note[];
extern uint16 xdata duration[];
// Playback related
extern bit isMusicPlaying; // Flag indicating music is playing
extern uint16 pos;         // Current position in music playback

/// @brief Digital tube decode table.
extern uint8 code dtDecode[];
/// @brief MIDI note number to TH0 conversion table.
extern uint8 code th0_table[];
/// @brief MIDI note number to TL0 conversion table.
extern uint8 code tl0_table[128];
/// @brief Digital tube data to be displayed.
extern uint8 dtData[];
/// @brief LED data to be displayed.
extern uint8 ledData;

/**
 * @brief Initialize the system. Set up and initialize ports.
 */
void sysInit();

/**
 * @brief Initialize Timer 0 for square wave generation.
 */
void beepInit();

/**
 * @brief Initialization function for UART communication.
 *
 * In this project, the UART uses Timer 2 in 8-bit auto-reload mode
 * to achieve a baud rate of 115200 bps.
 */
void uartInit();

/**
 * @brief Initialize interrupts.
 */
void interruptInit();

/**
 * @brief Delay function.
 *
 * @param t Time to delay in the unit of milliseconds.
 */
void delay(uint16 t);

/**
 * @brief Function for displaying data on the digital tube and LED.
 *
 * - Place this function in the main loop to continuously update the display.
 *
 * - Not suggested to call this function when the music is playing.
 *
 */
void display();

/**
 * @brief Called by UART interrupt to fetch data.
 *
 * Data from UART will be processed here. Data protocol can be found in `README.md`.
 */
void fetchData();

/**
 * @brief Send a byte of data via UART.
 *
 * @param dt Data byte to be sent.
 */
void sendData(uint8 dt);

/**
 * @brief Timer 0 interrupt handler.
 * Flips the beep state to generate a square wave, driving the buzzer.
 */
void t0InterruptHandler();

/**
 * @brief Called when data is received or transmitted via UART.
 */
void uartInterruptHandler();

#endif
