# -*- coding: utf-8 -*-
"""
Created on Thu May 28 04:15:18 2020

@authors: Jochen, Kristof
"""

import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import serial
import time
import numpy as np
import struct
import csv
import datetime
import sys 
from scipy.spatial.transform import Rotation as R

serport = '/dev/cu.usbmodem2403'

mode = 1
showData = 1
dataCount = 1000000
maxNumModes = 2

singleNode_Id = 0
glove_v1_Id = 1
glove_v2_Id = 2

sensors = ['wrist', 'palm', 'thumb', 'index', 'mid', 'ring', 'pinky']

path = './'

###########################################
# Variables for displaying the information
###########################################
calibrationDataArray = [0] * 7
connectedNodes = ""
sessionID = ""
alignmentImuQuat = [1, 0, 0, 0]     # quaternion #Softwaremapping der Achsen der Basistation
confNodes  = 0                      # Zum Anzeigen der Konfigurierten Nodes
activNodes = 0                      # Zum Anzeigen der aktiven Nodes
updateGloveList = []                # Zum Speichern der IDs bei empfangenen Daten und senden an die BS
lengthConfigData = 6                # Amoutn of Information + End-Byte (Mode, Node, SessionID, UGID, 0xAA)
gloveModes  = ["Quat", "Quat-Lin-Acc"]

initSend            = b'\xab'
sendDataFirstPart   = b'\xcd\x00\x00\x00\xfd\x03' # + 2 Bytes with the Update Data + the end Part
sendDataSecondPart  = b'\xa0\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
doubleUIDRoundOne   = False
doubleUIDRoundTwo   = False
findInactiveNodes   = True

# Write CSV file
def write_CSV(filename, sensorNames, data, mode=0):
    try:
        with open(filename, 'w') as csvfile:
            i = 0
            for sName in sensorNames:
                if mode == 0:
                    csvfile.write("Sensor," + str(i) + ",4," + sName +",Orientation\n")
                elif mode == 1:
                    csvfile.write("Sensor," + str(i) + ",7," + sName +",OrientationAcceleration\n")
                i += 1
                
            csv_writer = csv.writer(csvfile, delimiter=',', lineterminator='\n')
            csv_writer.writerows(data)
    except Exception as e:
        print('Error in write_CSV:')
        print(e)
        return 0
    return 1

# helper functions for quaternion viz:
def rotate_vector(vector, rotation_matrix):
    return np.dot(rotation_matrix, vector)
def calculate_endpoint(start, a, b, c, d):
    rotation_matrix = R.from_quat([a, b, c, d]).as_matrix()
    unit_vector = np.array([0, 0, 1])
    endpoint = rotate_vector(unit_vector, rotation_matrix)
    return start + endpoint
start_point = np.array([0,0,0])

# returns packet data length in bytes (without header bytes)
def getPacketLength(mode, deviceId, packetId):
    if mode == 0:
        if deviceId == singleNode_Id:
            return 8, 1        
        elif deviceId == glove_v1_Id:
            return 18, 3        
        elif deviceId == glove_v2_Id:
            if packetId == 1:
                return 24, 4
            elif packetId == 2:
                return 18, 3            
    elif mode == 1:
        if deviceId == singleNode_Id:
            return 14, 1        
        elif deviceId == glove_v1_Id:
            return 24, 2        
        elif deviceId == glove_v2_Id:
            if packetId == 1:
                return 24, 2
            elif packetId == 2:
                return 30, 3
            elif packetId == 3:
                return 30, 3    
    # if nothing above, input was invalid -> return -1
    return -1

def isPacketValid(mode, deviceId, packetId):
    # for now, only mode = 0 or 1 is allowed. Change this accordingly
    if mode > 1:			# Nur Mode 0 und 1
        return False
    if packetId == 0 or packetId > 3:   # PaketID 1 - 3 Für Alle
        return False
    if deviceId == 0 and packetId > 1:  # Devide Single Node hat nur 1 Paket
        return False
    if mode == 0 and packetId > 2:	# Device Glove V1 und V2 haben im Modus Quat (= Modus 0) nur je 2 Pakete
        return False
    return True

def analyzeInformationData(inData):
    global rotM
    global doubleUIDRoundOne
    while len(inData) < 6:
        inData += ser.read(100)
    if inData[0] == 0xFE: ### Lesen und darstellen der Daten von der Basisstation (COMMAND_TYPE = COMMAND_TYPE_BASESTATION_COMMAND)
        if inData[1] == 0x00:  ## Lesen und speichern der Anzahl der Nodes
            inData = inData[2:]
            while len(inData) < 1:
                inData += ser.read(100)
            global connectedNodes
            connectedNodes = str(inData[0])
            #print("Anzahl Nodes: " + str(connectedNodes))

            rotM = np.eye(4)  # identity matrix
            cubeDraw(rotM, "BS, Mode: Amount of connected gloves", str(connectedNodes), "", "", "")

        elif inData[1] == 0x01:  ### Lesen und speichern der SessionID
            inData = inData[2:]
            while len(inData) < 1:
                inData += ser.read(100)
            global sessionID
            sessionID = str(inData[0])
            # inData = inData[1:]
            #print("SessionID: " + str(sessionID))

            rotM = np.eye(4)  # identity matrix
            cubeDraw(rotM, "BS, Mode: SessionID", str(sessionID), "", "", "")

        elif inData[1] == 0x02: ##BNO-Daten darstellen
            if inData[2] == 0x00:
                packetSize = 6      # Nur Quaternionen
                unpackFormat = '<3h'
            elif inData[2] == 0x01:
                packetSize = 12     # Quaternionen und Lin Acc
                unpackFormat = '<6h'
            else:
                return

            inData = inData[3:]
            while len(inData) < packetSize:
                inData += ser.read(100)

            packet = inData[:packetSize]
            rcvd = np.array(struct.unpack(unpackFormat, packet[0:packetSize]))
            quatV = rcvd[:3] / 16384
            if packetSize == 12:
                acc = rcvd[3:] / 100

            sumsq = np.sum(quatV * quatV)
            if sumsq <= 1:
                quatW = np.array([np.sqrt(1.0 - sumsq)])
            else:
                quatW = np.array([0])

            ##### Quaternionen von der Basisstation
            quatTxt = ""
            quatTxt += ' {:+.3f}'.format(quatV[0])
            quatTxt += ' {:+.3f}'.format(-quatV[2])
            quatTxt += ' {:+.3f}'.format(quatV[1])
            quatTxt += ' {:+.3f}'.format(quatW[0])

            headerTxt = "BS, Mode: "

            linAccTxt = ""

            if packetSize == 12:
                linAccTxt += '{:+.3f} '.format(-acc[0])
                linAccTxt += '{:+.3f} '.format(acc[2])
                linAccTxt += '{:+.3f}'.format(-acc[1])
                headerTxt += "Quat-LinAcc"
            else:
                linAccTxt = "0, 0, 0"
                headerTxt += "Quat"

            imuQ = [quatW[0], quatV[0], -quatV[2], quatV[1]]  # quaternion #Softwaremapping der Achsen der Basistation
            global alignmentImuQuat
            alignmentImuQuat = imuQ  # Zur Ausrichtung des Handschuhes an der Basisstation
            rotM[:3, :3] = R.from_quat(imuQ).as_matrix()  # convert to rotation matrix
            
            cubeDraw(rotM, headerTxt, '', '', quatTxt, linAccTxt)

        elif inData[1] == 0x03:  ### Lesen und speichern der konfigurierten Nodes
            inData = inData[2:]
            while len(inData) < 2:
                inData += ser.read(100)
            global confNodes
            confNodes = inData[0] << 8 | inData[1]
            #print("Configured Nodes: " + str(confNodes))

            #rotM = np.eye(4)  # identity matrix
            confNodesTextualPartOne = []
            confNodesTextualPartTwo = []
            for i in range (0, 8):
                if (confNodes & 1<<i):
                    confNodesTextualPartOne.append(i)
            for i in range (8, 16):
                if (confNodes & 1<<i):
                    confNodesTextualPartTwo.append(i)
            cubeDraw(rotM, "BS, Mode: configurated gloves", f"{confNodes:#0{6}x}", ' '.join(map(str, confNodesTextualPartOne)), ' '.join(map(str, confNodesTextualPartTwo)), "")

        elif inData[1] == 0x04:  ### Lesen und speichern der aktiven Nodes
            inData = inData[2:]
            while len(inData) < 2:
                inData += ser.read(100)
            global activNodes
            activNodes = inData[0] << 8 | inData[1]
            # inData = inData[1:]
            #print("Aktive Nodes: " + str(activNodes))

            activeNodesTextualPartOne = []
            activeNodesTextualPartTwo = []
            for i in range (0, 8):
                if (activNodes & 1<<i):
                    activeNodesTextualPartOne.append(i)
            for i in range (8, 16):
                if (activNodes & 1<<i):
                    activeNodesTextualPartTwo.append(i)

            #rotM = np.eye(4)  # identity matrix
            cubeDraw(rotM, "BS, Mode: active gloves", f"{activNodes:#0{6}x}", ' '.join(map(str, activeNodesTextualPartOne)), ' '.join(map(str, activeNodesTextualPartTwo)), "")
    elif inData[0] == 0x7F: ### Command for the Script
        # print("Hello some more ...")
        if inData[1] == 0x00:
            if findInactiveNodes:                   # Inidacte that inactive Nodes should be search and emelminated
                doubleUIDRoundOne = True            # The BS found a double GloveUID and signalised it the skript
            #print("... should be printed now")
    else:
        gloveID = inData[0] >> 4                    # Save GloveID
        deviceID = inData[0] & 0x07;                # Save DeviceID
        #print(f"GloveID: {str(gloveID)}\nDeviceID: {str(deviceID)}\n\n")
        if start_of_activity_control:
            if gloveID not in updateGloveList:      #Update list of active Gloves
                updateGloveList.append(gloveID)

        cmdType = inData[1]                         # Save CMD-Type
        cmd     = inData[2]                         # Save CMD
        #print(f"Befehlstyp: {str(cmdType)}\nBefel: {str(cmd)}\n\n")
        inData = inData[3:]
        if cmdType == 0x02 and cmd == 0x00: # Kalibrierungsdaten
            amountOfSensors = -1
            if deviceID == glove_v1_Id:
                amountOfSensors = 6
            elif deviceID == glove_v2_Id:
                amountOfSensors = 7
            while len(inData) < amountOfSensors:
                inData += ser.read(100)

            #print(f"SensorLänge = {str(amountOfSensors)}")
            for i in range(amountOfSensors):  ### TODO is a simple alternative to if and elif with glove id but not 100% correct
                calibrationDataArray[i] = inData[i]

            cubeDraw(rotM, f'GloveID {str(gloveID)}, Mode: calibraition info',
                     'Calibration System: ' + str((calibrationDataArray[0] >> 6) & 3),
                     'Calibration Gyroscope: ' + str((calibrationDataArray[0] >> 4) & 3),
                     'Calibration Accelerometer: ' + str((calibrationDataArray[0] >> 2) & 3),
                     'Calibration Magnetometer: ' + str(calibrationDataArray[0] & 3))
        if cmdType == 0x02 and cmd == 0x01: # Konfigurationsdaten
            global lengthConfigData
            while len(inData) < lengthConfigData:
                inData += ser.read(100)
            cmdType       = inData[0]
            cmd           = inData[1]
            gloveID       = inData[2]
            sessionID     = inData[3]
            uniqueGloveID = inData[4]
            endByte       = inData[5]
            cubeDraw(rotM, f'GloveID: {str(gloveID)}, Mode: configuration info',
                     'CmdType: ' + str(cmdType),
                     'CMD (Mode): ' + str(cmd),
                     'SessionID: ' + str(sessionID),
                     'UniqueID: ' + str(uniqueGloveID))# +
                     #' EndByte: ' + str(endByte))
            #print("Glove-Info")

#def showBastationIMUData():

######################################################################################
def cubeDraw(rotM, headerText, info1Text, info2Text, quatText, linAccText):  # render & rotate a 3D Box according a 4x4 rotation matrix
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glPushMatrix()
    glMultMatrixf(rotM)
    glBegin(GL_QUADS)
    glColor3fv((1.0,1.0,0.0))
    for i in range(len(surf)):
        glColor3fv(colors[i])
        for j in surf[i]:
            glVertex3fv(vertices[j])
    glEnd()
    glPopMatrix()

    headerInfo = font.render(headerText, True, (255, 255, 66, 255), (0, 66, 0, 255))
    textData = pygame.image.tostring(headerInfo, "RGBA", True)
    glWindowPos2d(10, 360)
    glDrawPixels(headerInfo.get_width(), headerInfo.get_height(),
        GL_RGBA, GL_UNSIGNED_BYTE, textData)
    
    ### Infos
    info1 = font.render(info1Text, True, (255, 255, 66, 255), (0, 66, 0, 255))
    info1TextData = pygame.image.tostring(info1, "RGBA", True)
    glWindowPos2d(10, 100)
    glDrawPixels(info1.get_width(), info1.get_height(),
        GL_RGBA, GL_UNSIGNED_BYTE, info1TextData)

    ### Infos 2
    info2 = font.render(info2Text, True, (255, 255, 66, 255), (0, 66, 0, 255))
    info2TextData = pygame.image.tostring(info2, "RGBA", True)
    glWindowPos2d(10, 70)
    glDrawPixels(info2.get_width(), info2.get_height(),
        GL_RGBA, GL_UNSIGNED_BYTE, info2TextData)

    ### Quaternionen
    quat = font.render(quatText, True, (255, 255, 66, 255), (0, 66, 0, 255))
    quatTextData = pygame.image.tostring(quat, "RGBA", True)
    glWindowPos2d(10, 40)
    glDrawPixels(quat.get_width(), quat.get_height(),
        GL_RGBA, GL_UNSIGNED_BYTE, quatTextData)

    ### LinAcc
    linAcc = font.render(linAccText, True, (255, 255, 66, 255), (0, 66, 0, 255))
    linAccTextData = pygame.image.tostring(linAcc, "RGBA", True)
    glWindowPos2d(10, 10)
    glDrawPixels(linAcc.get_width(), linAcc.get_height(),
        GL_RGBA, GL_UNSIGNED_BYTE, linAccTextData)
    
    
    pygame.display.flip()
    pygame.time.wait(1)
######################################################################################
    

##################################
# Graphics viz
##################################
pygame.init()
pygame.display.set_caption('Palm')
display = (400, 400)
pygame.display.set_mode(display, DOUBLEBUF|OPENGL)
glEnable(GL_DEPTH_TEST) 
glMatrixMode(GL_PROJECTION)
gluPerspective(45, (display[0]/display[1]), 0.1, 50.0)
glLoadIdentity()
aspect_ratio = display[0]/display[1]
near_clip = 0.1
far_clip = 50.0
fov = 50.0 # 45.0
##################################
# perspective projection matrix:
f = 1.0 / np.tan(np.radians(fov)/2.0)
projM = np.array( [ [f/aspect_ratio, 0, 0, 0], [0, f, 0, 0], 
		    [0, 0, (far_clip+near_clip)/(near_clip-far_clip), -1], 
		    [0, 0, 2*far_clip*near_clip/(near_clip-far_clip), 0] ], dtype=np.float32)
glMultMatrixf(projM)
##################################
# modelview matrix:
glMatrixMode(GL_MODELVIEW)
glLoadIdentity()
glTranslatef(0.0, 0.0, -10.0)
# create 3D box:
vertices = ( ( 1, -1, -1), ( 1,  1, -1), (-1,  1, -1), (-1, -1, -1),
             ( 1, -1,  1), ( 1,  1,  1), (-1, -1,  1), (-1,  1,  1) )
surf = ((0, 1, 2, 3), (3, 2, 7, 6), (6, 7, 5, 4), (4, 5, 1, 0), (1, 5, 7, 2), (4, 0, 3, 6))
colors = ((1, 0, 0), (0, 1, 0), (1, 0.5, 0), (1, 1, 0), (0, 1, 1), (0, 0, 1))
# text from the sensors below:
font = pygame.font.SysFont('courier', 17)
# init the cube:
rotM = np.eye(4)  # identity matrix
cubeDraw(rotM, "initialized", "initialized", "initialized", "initialized", "initialized")



#################################
# open serial port and log file
#################################
ser = serial.Serial()
ser.baudrate = 500000
ser.port = serport
ser.timeout = 0 # = None means wait forever, = 0 means do not wait
ser.open()
# iteration variables for storing to a log file:
count = 0
nextTs = 1000
# helper variables:
syncBytes = b'\xAB\xCD'
#syncBytes = b'\x80\x80'
doSync = False
# object to store all data
data = np.zeros((dataCount,9))
filename = 'log.csv'

try:
    ser.reset_input_buffer()
    
    inData = b""
    mode = -1
    
    glove_v2_sample_5_pos = -1
    
    print("start synchronizing")
    
    # initial synchronization step. Done before starting the timer to not mess up time stamps
    while ser.is_open:
        inData += ser.read(100)
        syncPos = inData.find(syncBytes)
        if syncPos >= 0:
            inData = inData[syncPos+2:]
            break
    
    # start timer
    t = time.perf_counter()
    start_time = time.time()
    start_of_activity_control = False    #start checking the activity of the gloves
    
    print("start receive loop, press q to quit")
    # receive loop
    while ser.is_open:

        if findInactiveNodes and doubleUIDRoundOne:   # Bs detected double use of glove uid and send it to the script
            doubleUIDRoundOne = False
            start_of_activity_control = True
            start_time = time.time()
            doubleUIDRoundTwo = True

        end_time = time.time()
        if findInactiveNodes and not start_of_activity_control and ((end_time - start_time) > 60):                # 60 Sekunden vergangen ##If time is passed the finding of active Gloves is started
            updateGloveList = []
            print(f"Zeit 1: {end_time - start_time}")
            start_time = time.time()                                                        # Neue Startzeit
            start_of_activity_control = True

        if findInactiveNodes and start_of_activity_control and ((end_time - start_time) > 60):                    # 60 Sekunden vergangen ##If time is passed the finding of the active Gloves is finished
            #updateGloveList = list(set(updateGloveList))                                    # Remove duplicates
            print(updateGloveList)                                                          # Ausgabe der IDs von aktiven Gloves beim letzten ActivityCheck
            ####### Start sending command for finding inactive Gloves
            #### Build Command
            updateGloveByte = 0
            for tempGlove in updateGloveList:
                updateGloveByte |= (1 << tempGlove)
            print(updateGloveByte)
            cmd = sendDataFirstPart + updateGloveByte.to_bytes(2, 'big') + sendDataSecondPart
            #### Build of Command finished
            ser.write(initSend)
            time.sleep(0.1)
            print("Anzahl an gesendeten Bytes: " + str(ser.write(cmd)))
            ####### Edn of sending command for finding inactive Gloves
            print(f"Zeit 2: {end_time - start_time}")
            start_time = time.time()                                                        # Neue Startzeit
            if not doubleUIDRoundTwo:                                                       # Start normal Time if no double ID was detected and no second round is needed
                start_of_activity_control = False
            else:
                doubleUIDRoundTwo = False
                updateGloveList = []
    
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q:
                    sys.exit()  # TODO: nicer exit
                    
        # if requested: do synchronization
        if doSync:
            while ser.is_open:
                inData += ser.read(100)
                syncPos = inData.find(syncBytes)
                if syncPos >= 0:
                    inData = inData[syncPos+2:]
                    doSync = False
                    break
        
        # time stamp
        ts = int((time.perf_counter() - t)*1000)
        
        inData += ser.read(100)
        if len(inData) < 4:
            continue
        
        # read header (might be sync bytes)
        header = inData[:2]
        if header == syncBytes:
            header = inData[2:4]
            inData = inData[4:]
            if header[0] == 0xFF and header[1] == 0xFF:  # Wenn Konfigurationsdaten / Informationen übertragen werden sollen
                analyzeInformationData(inData)
                doSync = True
                continue
            # header always has packetId = 1 after sync
            if header[1] & 0x03 != 1:
                print("got invalid sync sequence. Skip to next sync point")
                doSync = True
                continue
        else:
            # strip header data from inData
            inData = inData[2:]
            
        if header[0] == 0xFF and header[1] == 0xFF:
            analyzeInformationData(inData)
            doSync = True
            continue
        if header[0] & 0x08 or header[1] & 0x10:  # 5 Bit im zweiten header nutzen für SessionId zum prüfen ob diese gesndet, empfangen und gesetzt wurde
            print("Received invalid packet header: Control bits invalid. Header is:")
            print(header)
            print("Skip to next sync point...")
            doSync = True
            continue
        
        # get header data
        gloveId = header[0] >> 4
        deviceId = header[0] & 0x07
        mode = header[1] >> 5
        sampleId = (header[1] >> 2) & 0x03
        packetId = header[1] & 0x03
        
        # do some basic header check
        if not isPacketValid(mode, deviceId, packetId):
            print("Received invalid packet header: Mode, deviceId, or packetId invalid.")
            print(f"Mode:     {mode}")
            print(f"DeviceID: {deviceId}")
            print(f"PacketId: {packetId}")
            print("Skip to next sync point...")
            doSync = True
            continue

        if start_of_activity_control:
            if gloveId not in updateGloveList:
                updateGloveList.append(gloveId)
            
        # Todo: do some more sanity check with header data
        # i.e. check sampleID and packetID not equal to the one before etc.
        
        packetLength, numSamples = getPacketLength(mode, deviceId, packetId)        
        
        # ensure we already received the whole packet, otherwise wait until it arrives
        while len(inData) < packetLength:
            inData += ser.read(100)
        
        packet = inData[:packetLength]
        inData = inData[packetLength:]        
        
        if mode == 0:
            if deviceId == singleNode_Id:
                #packetLength = 8, 1
                quat = np.array(struct.unpack('<4h', packet)) / 16384
                data[count] = [gloveId << 4, ts, quat[1], -quat[3], quat[2], quat[0], 0, 0, 0]
                count += 1
            else:
                #packetLength = 18, 3 or 24, 4
                for i in range(numSamples):
                    quatV = np.array(struct.unpack('<3h', packet[6*i:6*(i+1)])) / 16384
                    # TODO: Below can result in NaN (Runtimewarning sqrt), dirty fix:
                    sumsq = np.sum(quatV*quatV)
                    if sumsq <= 1:
                         quatW = np.array([np.sqrt(1.0 - sumsq)])
                    else:
                         quatW = np.array([0])
                    
                    if deviceId == glove_v2_Id:
                        ID = (gloveId << 4) + 4*(packetId-1) + i
                    else:
                        ID = (gloveId << 4) + numSamples*(packetId-1) + i
                    data[count] = [ID, ts, quatV[0], -quatV[2], quatV[1], quatW[0], 0, 0, 0]
                    
                    #########################################################################################
                    if ID % 16 == 0:  # here we catch the first (thumb) sensor:
                        headerTxt = "Node ID: " + str (gloveId) + " Mode: " + gloveModes[mode]

                        infoText1 = "Connected Nodes: " + str(connectedNodes)

                        infoText2 = "SessionID: " + str(sessionID)

                        quatTxt = str( data[count][1].astype(int) ).zfill(7)
                        for ci in range(4):
                            quatTxt += ' {:+.3f}'.format(data[count][2+ci])

                        ##############
                        imuQ = [-data[count][3], data[count][5], -data[count][4], -data[count][2]]  # quaternion glove
                        imuQRot = R.from_quat(imuQ) * R.from_euler("xyz", [90, 180, 0], degrees=True)

                        alignmentImuQuat = [-alignmentImuQuat[0], -alignmentImuQuat[3], alignmentImuQuat[2], -alignmentImuQuat[1]]  # quaternion bs
                        alignmentImuQuatRot = R.from_quat(alignmentImuQuat) * R.from_euler("xyz", [180, -90, 0], degrees=True)  # quaternion bs

                        product = imuQRot * alignmentImuQuatRot
                        rotM[:3, :3] = product.as_matrix()  # convert to rotation matrix
                        ##############

                        cubeDraw(rotM, headerTxt, infoText1, infoText2, quatTxt, "0, 0, 0")
                        count += 1
                    #########################################################################################
                                                  
        elif mode == 1:
            if deviceId == singleNode_Id:
                # packetLength = 14, 1
                rcvd = np.array(struct.unpack('<7h', packet))
                quat = rcvd[:4] / 16384
                acc = rcvd[4:] / 100
                
                data[count] = [gloveId << 4, ts, quat[1], -quat[3], quat[2], quat[0], -acc[0], acc[2], -acc[1]]
            
            elif deviceId == glove_v1_Id:
                # packetLength = 24, 2
                for i in range(numSamples):
                    rcvd = np.array(struct.unpack('<6h', packet[12*i:12*(i+1)]))
                    quatV = rcvd[:3] / 16384
                    sumsq = np.sum(quatV*quatV)
                    if sumsq <= 1:
                         quatW = np.array([np.sqrt(1.0 - sumsq)])
                    else:
                         quatW = np.array([0])
                    #quatW = np.array([np.sqrt(1.0 - np.sum(quatV*
                    acc = rcvd[3:] / 100
                    
                    ID = (gloveId << 4) + numSamples*(packetId-1) + i
                    data[count] = [ID, ts, quatV[0], -quatV[2], quatV[1], quatW[0], -acc[0], acc[2], -acc[1]]
                    ##count += 1
                    
                 #########################################################################################
                    if ID % 16 == 0:  # here we catch the first (thumb) sensor:
                        headerTxt = "Node ID: " + str (gloveId) + " Mode: " + gloveModes[mode]

                        infoText1 = "Connected Nodes: " + str(connectedNodes)

                        infoText2 = "SessionID: " + str(sessionID)

                        quatTxt = str(data[count][1].astype(int)).zfill(7)
                        for ci in range(4):
                            quatTxt += ' {:+.3f}'.format(data[count][2+ci])
                        linAccTxt = ''
                        for ci in range(3):
                            linAccTxt += ' {:+.3f}'.format(data[count][6+ci])

                        ##############
                        imuQ = [-data[count][3], data[count][5], -data[count][4], -data[count][2]]  # quaternion glove
                        imuQRot = R.from_quat(imuQ) * R.from_euler("xyz", [90, 180, 0], degrees=True)

                        alignmentImuQuat = [-alignmentImuQuat[0], -alignmentImuQuat[3], alignmentImuQuat[2], -alignmentImuQuat[1]]  # quaternion bs
                        alignmentImuQuatRot = R.from_quat(alignmentImuQuat) * R.from_euler("xyz", [180, -90, 0], degrees=True)  # quaternion bs

                        product = imuQRot * alignmentImuQuatRot
                        rotM[:3, :3] = product.as_matrix()  # convert to rotation matrix
                        ##############

                        cubeDraw(rotM, headerTxt, infoText1, infoText2, quatTxt, linAccTxt)
                        count += 1
                    #########################################################################################
            
            elif deviceId == glove_v2_Id:
                if packetId == 1:
                    # packetLength = 24, 2
                    for i in range(numSamples):
                        rcvd = np.array(struct.unpack('<6h', packet[12*i:12*(i+1)]))
                        quatV = rcvd[:3] / 16384
                        quatW = np.array([np.sqrt(1.0 - np.sum(quatV*quatV))])
                        acc = rcvd[3:] / 100
                        
                        ID = (gloveId << 4) + numSamples*(packetId-1) + i
                        data[count] = [ID, ts, quatV[0], -quatV[2], quatV[1], quatW, -acc[0], acc[2], -acc[1]]
                        count += 1
                        
                        # here we need to pay attention for packets 2 and 3 because sample #5
                        # is spread across both packets
                        # When we see packet 1, we invalidate it in case packet 2 or 3 went missing
                        glove_v2_sample_5_pos = -1
                        
                elif packetId == 2:
                    # packetLength = 30, 3
                    for i in range(numSamples):
                        rcvd = np.array(struct.unpack('<6h', packet[12*i:12*(i+1)]))
                        quatV = rcvd[:3] / 16384
                        quatW = np.array([np.sqrt(1.0 - np.sum(quatV*quatV))])
                        acc = rcvd[3:] / 100
                        
                        ID = (gloveId << 4) + numSamples*(packetId-1) + i
                        data[count] = [ID, ts, quatV[0], -quatV[2], quatV[1], quatW, -acc[0], acc[2], -acc[1]]
                        count += 1
                        
                    quatV = np.array(struct.unpack('<3h', packet[24:30])) / 16384
                    quatW = np.array([np.sqrt(1.0 - np.sum(quatV*quatV))])
                    data[count] = [ID, ts, quatV[0], -quatV[2], quatV[1], quatW, 0, 0, 0]
                    
                    glove_v2_sample_5_pos = count
                    count += 1
                    
                elif packetId == 3:
                    # packetLength = 30, 3
                    for i in range(numSamples):
                        rcvd = np.array(struct.unpack('<6h', packet[12*i:12*(i+1)]))
                        quatV = rcvd[:3] / 16384
                        quatW = np.array([np.sqrt(1.0 - np.sum(quatV*quatV))])
                        acc = rcvd[3:] / 100
                        
                        ID = (gloveId << 4) + numSamples*(packetId-1) + i
                        data[count] = [ID, ts, quatV[0], -quatV[2], quatV[1], quatW, -acc[0], acc[2], -acc[1]]
                        count += 1
                        
                    acc = np.array(struct.unpack('<3h', packet[24:30])) / 100
                    
                    if glove_v2_sample_5_pos > 0:
                        data[glove_v2_sample_5_pos][6:9] = [-acc[0], acc[2], -acc[1]]
                        count += 1
                    #else:
                        # packet 2 is missing
        
        
        if ts >= nextTs:
            #print('time: ' + str(ts/1000) + '  count: ' + str(count))
            nextTs += 1000
        
        if 0: #keyboard.is_pressed('escape'):
            if count > 0:
                # adjust data for displaying purposes
                data = data[:count]
                data[:,1] -= np.min(data[:,1])
            
            # set count to zero not write to a file
            count = 0
            break
except Exception as e: 
    print('An error occured during recording')
    print(e)


finally:
    ser.close()


if count > 0:
    # adjust data to write
    data = data[:count]
    data[:,1] -= np.min(data[:,1])
    
    
    print('\nwriting to file...')
    
    if mode == 0:
        dataToWrite = [[int(d[0]), int(round(d[1])), d[2], d[3], d[4], d[5]] for d in data]
    elif mode == 1:
        dataToWrite = [[int(d[0]), int(round(d[1])), d[2], d[3], d[4], d[5], d[6], d[7], d[8]] for d in data]
    
    # write data to file (otherwise recording was aborted)
    if write_CSV(path+filename, sensors, dataToWrite, mode):
        print('written to ' + path + filename)
    
else:
    print('recording aborted or no data available')