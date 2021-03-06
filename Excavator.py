from AMSpi import AMSpi
import time


class Excavator:
    LEFT_CHAIN_MOTOR = AMSpi.DC_Motor_1
    RIGHT_CHAIN_MOTOR = AMSpi.DC_Motor_2
    BODY_MOTOR = AMSpi.DC_Motor_3
    SHOWEL_MOTOR = AMSpi.DC_Motor_4

    def __init__(self):
        self.motors = AMSpi()
        # Set PINs for controlling shift register (GPIO numbering)
        self.motors.set_74HC595_pins(21, 20, 16)
        # Set PINs for controlling all 4 motors (GPIO numbering)
        self.motors.set_L293D_pins(5, 6, 13, 19)

        self.motors_memo = []

        self.body_angle = 0
        self.showel_angle = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.motors.clean_up()

    def execute(self, run_time=1):
        time.sleep(run_time)
        for motor in self.motors_memo:
            self.motors.stop_dc_motor(motor)
        self.motors_memo = []
        time.sleep(1)

    def forward_left_chain(self, speed=100):
        self.motors_memo.append(self.LEFT_CHAIN_MOTOR)
        self.motors.run_dc_motor(self.LEFT_CHAIN_MOTOR,
                                 clockwise=True,
                                 speed=speed)

    def backward_left_chain(self, speed=100):
        self.motors_memo.append(self.LEFT_CHAIN_MOTOR)
        self.motors.run_dc_motor(self.LEFT_CHAIN_MOTOR,
                                 clockwise=False,
                                 speed=speed)

    def forward_right_chain(self, speed=100):
        self.motors_memo.append(self.RIGHT_CHAIN_MOTOR)
        self.motors.run_dc_motor(self.RIGHT_CHAIN_MOTOR,
                                 clockwise=True,
                                 speed=speed)

    def backward_right_chain(self, speed=100):
        self.motors_memo.append(self.RIGHT_CHAIN_MOTOR)
        self.motors.run_dc_motor(self.RIGHT_CHAIN_MOTOR,
                                 clockwise=False,
                                 speed=speed)

    def turn_left_body(self, speed=100):
        self.motors_memo.append(self.BODY_MOTOR)
        self.motors.run_dc_motor(self.BODY_MOTOR, clockwise=True, speed=speed)

    def turn_right_body(self, speed=100):
        self.motors_memo.append(self.BODY_MOTOR)
        self.motors.run_dc_motor(self.BODY_MOTOR, clockwise=False, speed=speed)

    def move_up_showel(self, speed=100):
        self.motors_memo.append(self.SHOWEL_MOTOR)
        self.motors.run_dc_motor(self.SHOWEL_MOTOR,
                                 clockwise=True,
                                 speed=speed)

    def move_down_showel(self, speed=100):
        self.motors_memo.append(self.SHOWEL_MOTOR)
        self.motors.run_dc_motor(self.SHOWEL_MOTOR,
                                 clockwise=False,
                                 speed=speed)

    def test_move(self):
        self.forward_left_chain()
        self.forward_right_chain()
        self.execute(3)
        self.backward_left_chain()
        self.backward_right_chain()
        self.execute(3)
        self.turn_left_body()
        self.execute(3)
        self.turn_right_body()
        self.execute(3)
        self.move_down_showel()
        self.execute(5)
        self.move_up_showel()
        self.execute(5)
