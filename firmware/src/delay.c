#include "delay.h"

void delay(uint16 t) {
    unsigned int j;
    for (; t > 0; t--)
        for (j = 800; j > 0; j--);
}

void delay_4us() {
    ;
    ;
}