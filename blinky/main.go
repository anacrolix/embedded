package main

import (
	"fmt"
	"machine"
	"time"
)

func main() {
	led := machine.GP16
	led.Configure(machine.PinConfig{Mode: machine.PinOutput})
	count := 0
	for {
		led.Low()
		time.Sleep(time.Millisecond * 500)
		fmt.Println("count", count)
		count++
		led.High()
		time.Sleep(time.Millisecond * 500)
	}
}
