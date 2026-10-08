// This file is part of www.nand2tetris.org
// and the book "The Elements of Computing Systems"
// by Nisan and Schocken, MIT Press.
// File name: projects/4/Fill.asm

// Runs an infinite loop that listens to the keyboard input. 
// When a key is pressed (any key), the program blackens the screen,
// i.e. writes "black" in every pixel. When no key is pressed, 
// the screen should be cleared.

//// Replace this comment with your code.
  // 外層無窮迴圈：負責監聽鍵盤
(LOOP)
    @KBD
    D=M
    @BLACK
    D;JGT       // 如果有按鍵 (值大於 0)，跳到 BLACK

(WHITE)
    D=0         // 沒按鍵，準備 0 (全白)
    @FILL_START
    0;JMP

(BLACK)
    D=-1        // 有按鍵，準備 -1 (全黑)

(FILL_START)
    // 儲存顏色
    @COLOR
    M=D

    // 1. 設定 pointer 的起點為 SCREEN
    @SCREEN     
    D=A
    @pointer
    M=D

    // 2. 設定螢幕像素總數 8192 作為倒數計數器
    @8192       
    D=A
    @count
    M=D

(DRAW_LOOP)
    // 檢查 count 是否歸零
    @count
    D=M
    @LOOP
    D;JEQ       // 若歸零代表畫完了，跳回 LOOP 繼續監聽鍵盤

    // 把顏色畫到目前的 pointer 位置
    @COLOR
    D=M
    @pointer
    A=M
    M=D

    // pointer 往前進一格
    @pointer
    M=M+1       

    // count 減 1
    @count
    M=M-1       

    // 跳回 DRAW_LOOP 繼續畫下一個區塊
    @DRAW_LOOP
    0;JMP