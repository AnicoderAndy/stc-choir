#include "STC15F2K60S2.H"
#include "types.h"

/**
 * @brief Initialize I2C (IIC) communication.
 */
void IIC_init();

/**
 * @brief Write a byte `dt` to the NVM at address `addr`.
 * 
 * @param addr The address to write to.
 * @param dt The data byte to write.
 */
void nvm_write(uint8 addr, uint8 dt);

/**
 * @brief Get a byte from the NVM at address `addr`.
 * 
 * @param addr The address to read from.
 * @return uint8 The data byte read from the NVM.
 */
uint8 nvm_read(uint8 addr);