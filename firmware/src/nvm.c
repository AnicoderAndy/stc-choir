#include "nvm.h"
#include "delay.h"

void IIC_init() {
    SCL = 1;
    delay_4us();
    SDA = 1;
    delay_4us();
}

void IIC_start() {
    SDA = 1;
    delay_4us();
    SCL = 1;
    delay_4us();
    SDA = 0;
    delay_4us();
}

void IIC_stop() {
    SDA = 0;
    delay_4us();
    SCL = 1;
    delay_4us();
    SDA = 1;
    delay_4us();
}

void IIC_response() {
    uint8 i = 0;
    SCL = 1;
    delay_4us();
    // If no response received from IIC, regard as success
    while (SDA == 1 && (i < 255)) i++;
    SCL = 0;
    delay_4us();
}

void IIC_write(uint8 dt) {
    uint8 i, temp;
    temp = dt;
    for (i = 0; i < 8; i++) {
        temp = temp << 1;
        SCL = 0;
        delay_4us();
        SDA = CY;
        delay_4us();
        SCL = 1;
        delay_4us();
    }
    SCL = 0;
    delay_4us();
    SDA = 1;
    delay_4us();
}

uint8 IIC_read() {
    uint8 i, k;
    SCL = 0;
    delay_4us();
    SDA = 1;
    delay_4us();
    for (i = 0; i < 8; i++) {
        SCL = 1;
        delay_4us();
        k = (k << 1) | SDA;
        delay_4us();
        SCL = 0;
        delay_4us();
    }
    delay_4us();
    return k;
}

void nvm_write(uint8 addr, uint8 dt) {
    IIC_start();
    IIC_write(0xa0);
    IIC_response();
    IIC_write(addr);
    IIC_response();
    IIC_write(dt);
    IIC_response();
    IIC_stop();
}

uint8 nvm_read(uint8 addr) {
    uint8 dt;
    IIC_start();
    IIC_write(0xa0);
    IIC_response();
    IIC_write(addr);
    IIC_response();

    IIC_start();
    IIC_write(0xa1);
    IIC_response();
    dt = IIC_read();
    IIC_stop();
    return dt;
}