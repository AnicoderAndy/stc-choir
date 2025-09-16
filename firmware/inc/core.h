#ifndef CORE_H
#define CORE_H
#include "STC15F2K60S2.h"
#include "intrins.h"
#include "globals.h"
#include "nvm.h"
#include "music.h"
#include "delay.h"

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

#endif // CORE_H
