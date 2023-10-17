import ctypes

import time #lets you get current time
from datetime import datetime #lets you get a different current time (easier to access month, day, year, hour, minute, and second)

#memory only read, never written
from ReadWriteMemory import ReadWriteMemory
from process_interface import ProcessInterface 
from ctypes import *
import pymem

import cv2
import numpy as np
import pyautogui
import mss

from pynput import keyboard
import threading
import subprocess

from moviepy.editor import * #lets you edit videos

if(not os.path.exists("hsConfig.txt")):
    print("hsConfig.txt not found. Creating file.")
    config = open("hsConfig.txt", "w")
    config.writelines(["(True to use one key to toggle recording or False to have one for start one for stop) RecordingToggle=True\n",
                       "(Key to begin or toggle recording) Start/ToggleRecordingKey=g\n",
                       "(Key to stop recording) StopRecordingKey=h\n",
                       "(True to not slow down fastmo in clips or False to slow them) KeepFastMo=True\n"])
    config.close()
    
input("Press Enter in this window once you have configured hsConfig.txt how you want it.")

print("\n")

config = open("hsConfig.txt", "r")
lines = config.readlines()

recordToggle = lines[0][-6].upper() != "F" #True if you only want one key to toggle recording; False if you want separate record and stop record buttons
recordKey1 = keyboard.KeyCode.from_char(lines[1][-2].lower()) #record button or toggle
recordKey2 = keyboard.KeyCode.from_char(lines[2][-2].lower()) #stop record button
#   *example keybinds: keyboard.KeyCode.from_char('a'), keyboard.Key.space, keyboard.Key.alt_l, keyboard.Key.ctrl_r
keepFastMo = lines[3][-6].upper() != "F" #when True, doesn't slow down fast mo (if false, those segments go down to 5 fps)
###################################

generalOffset = 0 #how much earlier to set timestamps to account for delay in fetching timescale variable
pauseOffset = .05 #how much earlier to start pause to make sure its frames aren't included
unpauseOffset = .05 #how much later to end unpause to make sure its frames aren't included

######################################################################################################################
#adapted from the following with author's permission:
#https://youtu.be/x4WE3mSJoRA
#https://youtu.be/OEgvqDbdfQI
#https://youtu.be/Pv0wx4uHRfM

sleep = False

if(not pymem.process.process_from_name("Heat_Signature.exe")):
    sleep = True
    print("GAME NOT OPEN")

while(not pymem.process.process_from_name("Heat_Signature.exe")):
    pass

if (sleep):
    time.sleep(6)

base_address = pymem.Pymem(process_name="Heat_Signature.exe").base_address
static_address_offset = 0x0453D610
pointer_static_address = base_address + static_address_offset
offsets = [0x60, 0x10, 0x3C4, 0x1B0]

rwm = ReadWriteMemory()
process = rwm.get_process_by_name("Heat_Signature.exe")
process.open()
my_pointer = process.get_pointer(pointer_static_address, offsets=offsets)

process2 = ProcessInterface()
process2.open("Heat_Signature.exe")  

######################################################################################################################
    
if(recordToggle):
    print("Press " + recordKey1.char + " to start/stop recording.")
else:
    print("Press " + recordKey1.char + " to start recording. \nPress " + recordKey2.char + " to stop recording.")

######################################################################################################################

def record(key): #handle record presses
    global recordToggle, recording
    
    if(recordToggle): #if set to toggle
        if(key == recordKey1): #if record toggle pressed
            recording = not recording
            if(recording):
                print("RECORDING")
            else:
                print("NOT RECORDING")
    else: #if not toggling
        if(key == recordKey1): #if record key pressed
            recording = True
            print("RECORDING")
        elif(key == recordKey2): #if stop record key pressed
            recording = False
            print("NOT RECORDING")


recording = False 
listener = keyboard.Listener(on_press=record) #set up keyboard listener
listener.start() #starts keyboard listener
recorder = mss.mss() #screenshot taker set up

def main():
    global recording
    
    recording = False

    while(True): #while code runs
        #reset/set values
        readyToEdit = False #if raw footage is ready to put together and edit
        baseTime = time.time() #time recording began
        currFrame = 0 #current frame
        shots = [] #list of shots from recorder
        prevSpeed = -1 #last recorded speed
        currSpeed = c_double.from_buffer(process2.read_memory(my_pointer, buffer_size=8)).value #current speed; also adapted from the 3 youtube videos
        times = [] #entries consisting of [timescale change start time, new timescale]
        
        state = 0 #0-Paused, 1-Slow, 2-Normal, 3-Fast
        if(currSpeed == 0): #if starting paused
            state = 0
            times.append([time.time()-baseTime, 0])
        elif(currSpeed < .6): #if starting slow
            state = 1
            times.append([time.time()-baseTime, .2])
        elif(currSpeed >= .6 and (currSpeed <= 1 or keepFastMo)): #if starting normal (or fast, but ignoring it)
            state = 2
            times.append([time.time()-baseTime, 1])
        else: #if starting fast (and not ignoring it)
            state = 3
            times.append([time.time()-baseTime, 6])
        
        while(recording):
            if(time.time() - baseTime >= currFrame/30): #if ready for next screenshot (1/30 of a second has passed since last one)
                prevSpeed = currSpeed #last current speed is new previous speed
                currSpeed = c_double.from_buffer(process2.read_memory(my_pointer, buffer_size=8)).value #new current speed accessed; also adapted from the 3 youtube videos
                if(currSpeed != prevSpeed): #if speed has changed
                    if(currSpeed == 0 and state != 0): #if now paused but not yet considered paused
                        state = 0
                        times.append([time.time()-baseTime+generalOffset, 0])
                    elif(currSpeed < .6 and state != 1): #if now slow but not yet considered slow
                        state = 1
                        times.append([time.time()-baseTime+generalOffset, .2])
                    elif(currSpeed >= .6 and currSpeed <= 1 and state != 2): #if now normal but not yet considered normal
                        state = 2
                        times.append([time.time()-baseTime+generalOffset, 1])
                    elif(currSpeed > 1 and state != 3 and not keepFastMo): #if now fast but not yet considered fast (and not ignoring fast)
                        state = 3
                        times.append([time.time()-baseTime+generalOffset, 6])
                        
                shots.append(pyautogui.screenshot()) #take a screenshot and store it
                currFrame += 1 #increment current frame
            readyToEdit = True
            
        if(readyToEdit): #if raw footage ready to put together and edit
            print("Processing Footage. A progress bar will appear (may take a while)...")
            editTimer = threading.Timer(0, edit, args=[times, shots]) #set up edit
            editTimer.start() #start edit
            
            

def edit(times, shots): #create and edit raw footage from speed change timestamps and screenshots
    now = datetime.now() #current time
    timeStr = str(now.month) + "-" + str(now.day) + "-" + str(now.year) + "_" + str(now.hour) + "," + str(now.minute) + "," + str(now.second) #file identifier
    
    t = time.time()
    
    #from https://www.thepythoncode.com/article/make-screen-recorder-python 
    raw = cv2.VideoWriter(timeStr+"_raw.mp4", cv2.VideoWriter_fourcc(*"mp4v"), 30, tuple(pyautogui.size()))
    
    frames = []
    
    t = time.time()
    
    for i in range(0, len(shots)):
        frame = np.array(shots[i])
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frames.append(frame)
    
    for i in range(0, len(shots)):
        raw.write(frames[i])
    raw.release()
    
    #######################################################################
    
    print("OVERALL RAW MAKE TIME: " + str(time.time() - t))
    t = time.time()
    
    while(not os.path.exists(timeStr+"_raw.mp4")):
        pass
    
    inVid = VideoFileClip(timeStr+"_raw.mp4") #raw input clip
    
    clips = [None]*len(times) #list of clips to be combined
    for i in range(0, len(times)-1): #for all speed changes excluding the last
        if(times[i][1] != 0): #if not a pause
            if(i > 0 and times[i-1][1] == 0): #if a previous change exists and it is a pause
                prevPause = True
            else: #if previous change is not a pause or none exists
                prevPause = False
                
            if(times[i+1][1] == 0): #if next speed change is a pause
                nextPause = True
            else: #if next change is not a pause
                nextPause = False
            
            if(prevPause and nextPause): #pause before and after current clip
                clipstart = min(times[i][0]+unpauseOffset, times[i+1][0]-pauseOffset)
                clipend = max(times[i+1][0]-pauseOffset, times[i][0]+unpauseOffset) 
            elif(prevPause): #pause only before current clip
                clipstart = min(times[i][0]+unpauseOffset, times[i+1][0]) 
                clipend = times[i+1][0]
            elif(nextPause): #pause only after current clip
                clipstart = times[i][0]
                clipend = max(times[i+1][0]-pauseOffset, times[i][0])
            else: #no pause before or after current clip
                clipstart = times[i][0]
                clipend = times[i+1][0]
            
            clipstart = max(clipstart, 0)
            clipend = max(clipend, 0)
            
            clipstart = min(clipstart, inVid.duration)
            clipend = min(clipend, inVid.duration)
            
            clip = inVid.subclip(clipstart, clipend)
            if(times[i][1] != 1):
                clip = clip.fx(vfx.speedx, 1/times[i][1])
            clips[i] = clip
    
    #once all but the last clip are accounted for
    
    if(times[-1][1] != 0): #if last time change is not a pause
        if(len(times) > 1 and times[-2][1] == 0): #if second to last speed change exists and is a pause
            clipstart = min(times[-1][0]+unpauseOffset, inVid.duration)
        else:
            clipstart = min(times[-1][0], inVid.duration)
        
        clip = inVid.subclip(clipstart, inVid.duration)
        if(times[-1][1] != 1):
            clip = clip.fx(vfx.speedx, 1/times[-1][1])
        clips[-1] = clip

    print("CLIPS MAKE TIME: " + str(time.time() - t))
    t = time.time()
    
    clipsNoPauses = []
    for i in range(0, len(times)):
        if(times[i][1] != 0):
            clipsNoPauses.append(clips[i])
    
    outVid = concatenate_videoclips(clipsNoPauses) #combine clips into one
    outVid.write_videofile(timeStr+"_out.mp4", fps=30) #output final mp4

    print("OUT MAKE TIME: " + str(time.time() - t))
    t = time.time()

main() #run main