import position_json_receiver
#import motorcontrol
import json
import math
import RPi.GPIO as GPIO
from time import sleep
GPIO.setmode(GPIO.BCM)


#written for ENME441 by Gurshaan Mann
class Targeter():



    def __init__(self, host, team, number_of_teams, laser_height, yaw_motor, pitch_motor, laser):
        self.position_receiver = position_json_receiver.PositionReceiver(host)
        self.target_data = self.position_receiver.get_json_data()
        self.team = team
        self.number_of_teams = number_of_teams
        self.my_z = laser_height
        self.yaw_motor = yaw_motor
        self.pitch_motor = pitch_motor
        self.laserpin = laser
        self.stop = False
        self.number_of_teams = len(self.target_data["turrets"])
        self.g_z = 10 #placeholder
        self.pitch = 0
        #GPIO.setup(self.laserpin,GPIO.OUT)
        GPIO.output(self.laserpin,GPIO.LOW)

    def locate_self_rad(self):
        self.mypos = self.target_data["turrets"][str(self.team)]
        return self.mypos

    def pick_target(self, n):
        self.target = n

    def locate_target_rad(self):
        self.tpos = self.target_data["turrets"][str(self.target)]
        return self.tpos
        
    def cycle_targets_rad(self):
        for i in range(self.number_of_teams):
            n = i+1
            if n != self.team:
                self.pick_target(n)
                target_loc = self.locate_target_rad()
                print(f'Target {n} is at location: {target_loc}')
    def stop_targeting(self):
        self.stop = True

    def start_again(self):
        self.stop = False

    class TMath():
        @staticmethod
        def rad2deg(ang):
            return ang*180/math.pi
        @staticmethod
        def which_quad(ang):
            ang %= 360
            if 0 <= ang < 90:
                return 1
            elif 90 <= ang < 180:
                return 2
            elif 180 <= ang < 270:
                return 3
            else:
                return 4

        
        


    


    def locate_self(self):
        self.my_r = self.target_data["turrets"][str(self.team)]['r']
        self.my_ang = self.target_data["turrets"][str(self.team)]['theta']
        self.my_ang = Targeter.TMath.rad2deg(self.my_ang)

        print(f'My team number is {self.team} and my position is (r: {self.my_r}, theta: {self.my_ang} degrees, z:{self.my_z})')

        return (self.my_r, self.my_ang, self.my_z)

    def locate_target(self):
        self.t_r = self.target_data["turrets"][str(self.target)]['r']
        self.t_ang = self.target_data["turrets"][str(self.target)]['theta']
        self.t_ang = Targeter.TMath.rad2deg(self.t_ang)
        self.g_z = 10 # placeholder
        return (self.t_r, self.t_ang)

    def cycle_targets(self):
        for i in range(self.number_of_teams):
            n = i+1
            if n != self.team:
                self.pick_target(n)
                target_loc = self.locate_target()
                print(f'Target {n} is at location: {target_loc}')

    def aim_at_target(self):
        #self.locate_self()
        self.locate_target()
        self.heading = self.rel_ang(self.my_ang,self.t_ang)
        self.yaw_motor.goAngle(self.heading)
        print (f"I'm at {self.my_ang} and my target is at {self.t_ang}")

        # self.fire()
        sleep(0.1)
        return self.heading

    def rel_ang(self,m,t): #assumes all turrets are equidistant from center 
        arc = abs(t-m)
        arc = min(arc,360-arc)
        absrel = (180-arc)/2 #180 degrees of a triangle minus the arc between target and me, divided by two because one angle is the angle at me, the other is the target.
        if(t != m): sgn = (t-m)/abs(t-m)
        
        quad = self.TMath.which_quad(t-m)
        sgn = (quad-2.5)/abs(quad-2.5)


        rel = absrel*sgn
        return rel

    def find_pitch(self):
        dist = 2*self.my_r *math.sin(math.radians(abs(self.g_ang-self.my_ang))/2)
        if dist == 0:
            return 90
        height_diff = self.g_z - self.my_z
        return -1 * math.degrees(math.atan(height_diff/dist)) # motor direction is flipped for some weird reason


    def aim_down_list(self):    
        for i in range(self.number_of_teams):
            if self.stop:
                print("Aborting")
                break
            n = i+1
            if n != self.team:
                self.pick_target(n)
                # self.locate_target()
                self.aim_at_target()
                print(f'Target {n} is being aimed at with this heading: {self.heading}')
                self.fire(3.0)
        
        self.globe_data = self.target_data['globes']
        for g in range(len(self.globe_data)):
            g
            if self.stop:
                print("Aborting")
                break

            try:
                self.pick_globe(self.globe_data[g])
                self.aim_at_globe(g)

                print(f'Globe {g+1} is being aimed at with this heading: {self.heading} and this pitch: {self.pitch}')
                self.fire(3.0)
            except:
                print("Globe not found")


    def pick_globe(self, g):
        self.globe = g

    def locate_globe(self,g):
        self.g_r = self.target_data["globes"][g]['r']
        self.g_ang = self.target_data["globes"][g]['theta']
        self.g_ang = Targeter.TMath.rad2deg(self.g_ang)
        self.g_z = self.target_data["globes"][g]['z']
        return (self.g_r, self.g_ang, self.g_z)
    
    def aim_at_globe(self,g):
        #self.locate_self()
        self.locate_globe(g)
        self.heading = self.rel_ang(self.my_ang,self.g_ang)
        self.pitch = self.find_pitch()
        self.fire(3)

        self.yaw_motor.goAngle(self.heading)
        sleep(0.1)
        self.yaw_motor.lock.acquire()

        try: # wait for yaw to finish
            self.pitch_motor.goAngle(self.pitch)
        finally:
            self.yaw_motor.lock.release()

        sleep(0.1)
        return (self.heading, self.pitch)
                
                

    def guess_hit(self):
        if self.heading == 0:
            return self.heading
        sgn = self.heading/abs(self.heading)
        arc = 180-abs(self.heading)*2
        arc = arc*sgn
        return (self.my_ang-arc)%360

    def aim_down_list_test(self):
        self.locate_self()
        hits = 0
        
        for i in range(self.number_of_teams):
            if self.stop:
                print("Aborting")
                break
            n = i+1
            if n != self.team:
                self.pick_target(n)
                self.locate_target()
                self.heading = self.aim_at_target()
                print(f'Target {n} is being aimed at with this heading: {self.heading}')
                hit_guess = self.guess_hit()
                print(f'I think my hit for target {n} was at theta {hit_guess} instead of {self.t_ang}')
                rel_guess = (hit_guess-self.my_ang)%360
                rel_tar = (self.t_ang-self.my_ang)%360
                print(f'Relative to me that is: {rel_guess} instead of {rel_tar}')
                print(f'Relative Quadrant is: {self.TMath.which_quad(rel_tar)}')
                #print(f'Absolute Quadrant is: {self.TMath.which_quad(self.t_ang)}')
                if abs(hit_guess-self.t_ang)<1:
                    hits += 1
                    print()
                elif abs(180-rel_tar) == abs(180-rel_guess):
                    print('FLIPPED')
                    
                else:
                    print('MISS\n')

        self.globe_data = self.target_data['globes']
        globes_hit = 0
        for g in range(len(self.globe_data)):
            if self.stop:
                print("Aborting")
                break
            self.pick_globe(g)
            self.aim_at_globe(g)
            hit_guess = self.guess_hit()
            print(f'I think my hit for globe {g} was at theta {hit_guess} instead of {self.g_ang}')
            
            rel_guess = (hit_guess-self.my_ang)%360
            rel_globe = (self.g_ang-self.my_ang)%360
            if abs(hit_guess-self.g_ang)<1:
                globes_hit += 1
                print()
            elif abs(180-rel_globe) == abs(180-rel_guess):
                print('FLIPPED')
                
            else:
                print('MISS\n')
            print(f'Relative to me that is: {rel_guess} instead of {rel_globe}')
            print(f'Relative Quadrant is: {self.TMath.which_quad(rel_globe)}')
        print(f'I made {hits} hits out of {self.number_of_teams-1} enemy turrets.')
        print(f'I made {globes_hit} hits out of {len(self.globe_data)} globes')
        self.locate_self()
     
    def fire(self, t):
        self.yaw_motor.lock.acquire()
        self.pitch_motor.lock.acquire()

        try:
            self.laser = True
            GPIO.output(self.laserpin,GPIO.HIGH)
            sleep(t)
            self.laser = False
            GPIO.output(self.laserpin,GPIO.LOW)
        finally:
            self.yaw_motor.lock.release()
            self.pitch_motor.lock.release()


    


if __name__ == "__main__":
    #in class
    host = "http://192.168.1.254:8000/positions.json"
    team = 21
    number_of_teams = 22

    #values for local testing
    #host = "http://127.0.0.254:8000/positions.json"
    
    laser_height = 5 

    self = Targeter(host, team, number_of_teams, laser_height)
    #We only need to instantiate a Targeter in the main file in a thread, run the aim_down_list function at the start. 
    #teampos = self.locate_self_rad()
    #All of below is for testing
    print(f'Json host is: {self.position_receiver.host}')
    #print(f'My team number is {team} and my position is {teampos}')
    

    #self.cycle_targets_rad()

    #print(Targeter.TMath.rad2deg(math.pi/3))

    team_r, team_ang, team_z = self.locate_self()
    #print(f'My team number is {team} and my position is (r: {team_r}, theta: {team_ang} degrees, z:{team_z})')

    self.cycle_targets()
    print()
    #self.aim_down_list()
    print()
    self.aim_down_list_test()
    print('DONE TESTS FOR TURRETS')

