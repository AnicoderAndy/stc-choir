#ifndef DELAY_H
#define DELAY_H
#include "globals.h"

/**
 * @brief Delay function.
 *
 * @param t Time to delay in the unit of milliseconds.
 */
void delay(uint16 t);

/**
 * @brief Delay for approximately 4 us.
 */
void delay_4us();

#endif // DELAY_H