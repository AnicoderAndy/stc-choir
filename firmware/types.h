#ifndef TYPES_H
#define TYPES_H
#ifndef __VSCODE_C51__
#define INTERRUPT(x) interrupt x
#define USING(x) using x
#else
#define INTERRUPT(x)
#define USING(x)
#endif
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
sbit SDA = P4 ^ 0;
sbit SCL = P5 ^ 5;

// UART2 相关位定义 - 使用位操作而不是sbit，因为这些寄存器不是位可寻址的
#define ES2_BIT 0x01   // IE2的第0位
#define PS2_BIT 0x01   // IP2的第0位
#define S2RI_BIT 0x01  // S2CON的第0位
#define S2TI_BIT 0x02  // S2CON的第1位
#define S2REN_BIT 0x10 // S2CON的第4位

#endif // TYPES_H