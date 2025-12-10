import position_json_receiver
import json
import math

class Targeter():



    def __init__(self, host, team, number_of_teams, laser_height):
        self.position_receiver = position_json_receiver.PositionReceiver(host)
        self.target_data = self.position_receiver.get_json_data()
        self.team = team
        self.number_of_teams = number_of_teams
        self.my_z = laser_height

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
                enme441_targeter.pick_target(n)
                target_loc = enme441_targeter.locate_target_rad()
                print(f'Target {n} is at location: {target_loc}')

    class TMath():

        def rad2deg(ang):
            return ang*180/math.pi

        def rel_ang(m,t): #assumes all turrets are equidistant from center 
            arc = abs(t-m)
            arc = min(arc,360-arc)
            absrel = (180-arc)/2 #180 degrees of a triangle minus the arc between target and me, divided by two because one angle is the angle at me, the other is the target.

        
            if t<85 or t>265: #left side of diameter through me  
                sgn = -1 #ccw turn
            else:# right side of diameter
                sgn = 1 #cw turn

            rel = absrel*sgn
            return rel


    


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
        return (self.t_r, self.t_ang)

    def cycle_targets(self):
        for i in range(self.number_of_teams):
            n = i+1
            if n != self.team:
                enme441_targeter.pick_target(n)
                target_loc = enme441_targeter.locate_target()
                print(f'Target {n} is at location: {target_loc}')

    def aim_at_target(self):
        self.heading = self.TMath.rel_ang(self.my_ang,self.t_ang)
        return self.heading

    def aim_down_list(self):
        for i in range(self.number_of_teams):
            n = i+1
            if n != self.team:
                enme441_targeter.pick_target(n)
                self.locate_target()
                self.aim_heading = enme441_targeter.aim_at_target()
                print(f'Target {n} is being aimed at with this heading: {self.aim_heading}')
                
                

    def guess_hit(self):
        sgn = self.aim_heading/abs(self.aim_heading)
        arc = self.aim_heading*2-180
        return (self.my_ang-arc)%360

    def aim_down_list_test(self):
        hits = 0
        for i in range(self.number_of_teams):
            n = i+1
            if n != self.team:
                enme441_targeter.pick_target(n)
                self.locate_target()
                self.aim_heading = enme441_targeter.aim_at_target()
                print(f'Target {n} is being aimed at with this heading: {self.aim_heading}')
                hit_guess = self.guess_hit()
                print(f'I think my hit for target {n} was at theta {hit_guess} instead of {self.t_ang}')
                if abs(hit_guess-self.t_ang)<1:
                    hits += 1
                else:
                    print('MISS')
        print(f'I made {hits} hits out of {self.number_of_teams-1} turrets.')

    def fire(self):
        self.laser = True
    


if __name__ == "__main__":
    #in class
    host = "http://192.168.1.254:8000/positions.json"
    team = 21
    number_of_teams = 22

    #values for local testing
    host = "http://127.0.0.254:8000/positions.json"
    team = 13
    number_of_teams = 20 
    laser_height = 0 

    enme441_targeter = Targeter(host, team, number_of_teams, laser_height)#We only need to instantiate a Targeter in the main file in a thread, run the aim_down_list function at the start. 
    #teampos = enme441_targeter.locate_self_rad()
    #All of below is for testing
    print(f'Json host is: {enme441_targeter.position_receiver.host}')
    #print(f'My team number is {team} and my position is {teampos}')
    

    #enme441_targeter.cycle_targets_rad()

    #print(Targeter.TMath.rad2deg(math.pi/3))

    team_r, team_ang, team_z = enme441_targeter.locate_self()
    #print(f'My team number is {team} and my position is (r: {team_r}, theta: {team_ang} degrees, z:{team_z})')

    enme441_targeter.cycle_targets()
    print()
    enme441_targeter.aim_down_list()
    print()
    enme441_targeter.aim_down_list_test()
    print('DONE TESTS FOR TURRETS')

