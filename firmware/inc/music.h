#ifndef MUSIC_H
#define MUSIC_H
#include "globals.h"
#include "STC15F2K60S2.h"

/**
 * @brief Essential function to play a music note.
 * When music is playing, this function should be called in a loop.
 * It will play a note, delay for rest duration, or stop music if the end is reached.
 */
void play_music_note();

#endif // MUSIC_H