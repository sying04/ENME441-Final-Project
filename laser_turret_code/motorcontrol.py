import time
import multiprocessing
from shifter import Shifter   # our custom Shifter class

class Stepper:

    # Class attributes:
    num_steppers = 0      # track number of Steppers instantiated
    shifter_outputs = 0   # track shift register outputs for all motors
    seq = [0b0001,0b0011,0b0010,0b0110,0b0100,0b1100,0b1000,0b1001] # CCW sequence
    delay = 800          # delay between motor steps [us]
    steps_per_degree = 4096/360    # 4096 steps/rev * 1/360 rev/deg

    def __init__(self, shifter, lock):
        self.s = shifter           # shift register
        self.angle = multiprocessing.Value('f')             # current output shaft angle
        self.step_state = 0        # track position in sequence
        self.shifter_bit_start = 4*Stepper.num_steppers  # starting bit position
        self.lock = lock           # multiprocessing lock

        Stepper.num_steppers += 1   # increment the instance count

    # Signum function:
    def __sgn(self, x):
        if x == 0: return(0)
        else: return(int(abs(x)/x))

    # Move a single +/-1 step in the motor sequence:
    def __step(self, dir):
        self.step_state += dir    # increment/decrement the step
        self.step_state %= 8      # ensure result stays in [0,7]
        mask = 0b1111<<self.shifter_bit_start
        Stepper.shifter_outputs = (mask & Stepper.seq[self.step_state]<<self.shifter_bit_start) | (Stepper.shifter_outputs & ~mask)
        self.s.shiftByte(Stepper.shifter_outputs)
        self.angle.value += dir/Stepper.steps_per_degree
        self.angle.value %= 360         # limit to [0,359.9+] range

    # Move relative angle from current position:
    def __rotate(self, delta, angle):
        with self.lock:                 # wait until the lock is available
            numSteps = int(Stepper.steps_per_degree * abs(delta))    # find the right # of steps
            dir = self.__sgn(delta)        # find the direction (+/-1)
            for s in range(numSteps):      # take the steps
                self.__step(dir)
                time.sleep(Stepper.delay/1e6)


    # Move relative angle from current position:
    def rotate(self, delta):
        time.sleep(0.1)
        p = multiprocessing.Process(target=self.__rotate, args=(delta, self.angle))
        p.start()

    # Move to an absolute angle taking the shortest possible path:
    def goAngle(self, angle):
        diff = angle - self.angle.value
        if diff > 180.0:
            diff = diff - 360.0
        self.rotate(diff)

    # Set the motor zero point
    def zero(self):
        self.angle.value = 0

    # helper function to get the motor's current angle
    def getAngle(self):
        return self.angle.value