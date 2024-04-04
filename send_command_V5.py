class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


receiveData = False

cmdType = -1
cmd = -1
initSend = b''
sendData = b''
recipientByte = 0
recipientList = []
commandDuration = 0
sessionId = 0
bsMode = 0
bsBnoMode = 0
bsUpdateData = []
bsUpdateDataByte = 0
cmdOption = -1


def chooseCommandOption():
    global cmdOption
    while 1:
        print(f"Bitte ein der Optionen auswählen:\n" +
              f"0, zum Ändern des Modus der Basisstation\n" +
              f"1, zum Senden eines Befehls an die Gloves\n" +
              f"2, zum Senden eines Befehls an die Basisstation\n" +
              f"-1, um das Programm zu beenden.")
        cmdOption = int(input(">> "))
        if cmdOption == -1:
            exit()
        if cmdOption in (0, 1, 2):
            print(f"{bcolors.OKGREEN}Ausgewählte Option: {cmdOptionArr[cmdOption]}{bcolors.ENDC}\n")
            break
        else:
            print(f"{bcolors.FAIL}Falsche Eingabe. Bitte erneut versuchen.{bcolors.ENDC}\n")


def chooseBasestationMode():
    global bsMode
    while 1:
        print("Bitte Basestation Modus auswählen:\n" +
              "0 = Basestation in Glove Mode versetzen\n" +
              "1 = Basestation in BS Mode versetzen\n" +
              "-1, um das Programm zu beenden.")
        bsMode = input(">> ")
        bsMode = int(bsMode)
        if bsMode == -1:
            exit()
        if bsMode not in (0, 1):
            print(f"{bcolors.FAIL}Unbekannter Modus. Bitte erneut auswählen.\n{bcolors.ENDC}")
        else:
            print(f"{bcolors.OKGREEN}Ausgewählter Modus: {baseStationMode[bsMode]}\n{bcolors.ENDC}")
            break


def createBasestationModeCommand():
    global bsMode
    global initSend
    global sendData

    ##Byte 0-1 Sync Byte
    initSend = b'\xAB'
    sendData = b'\xCD'
    ##Byte 2 Duration
    sendData += b'\x00'
    ##Byte 3-4 Receiver Byte    #0x00 0x00 means Command which should be executed on the Basestation
    sendData += b'\x00'
    sendData += b'\x00'
    ##Byte 5 CommandType
    sendData += b'\x80'  # CommandType COMMAND_TYPE_CHANGE_BS_MODE
    ##Byte 6 BasestationMode
    sendData += bsMode.to_bytes(1, 'big')
    ##Byte 7 EndByte
    sendData += b'\xA0'

    for i in range(0, 24):
        sendData += b'\x00'


def chooseRecipient():
    global recipientByte
    global recipientList
    while 1:
        print(f"\nBitte (weitere) Empfänger auswählen (0-15).\n" +
              f"-1, um die Eingabe von neuen Nodes zu beenden.\n" +
              f"-2, um alle Nodes auszuwählen.\n" +
              f"Bereits ausgewähtle Empfänger {bcolors.OKCYAN}{recipientList}{bcolors.ENDC}")
        tempReciepient = int(input(">> "))
        if tempReciepient == -1:
            if len(recipientList) != 0:
                break
            else:
                print(f"{bcolors.FAIL}Bitte mindestens einen Empfänger auswählen.{bcolors.ENDC}\n")
        elif tempReciepient == -2:
            recipientList = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]
            break
        if 0 <= tempReciepient and tempReciepient <= 15:
            recipientList.append(tempReciepient)
        else:
            print(f"{bcolors.FAIL}Falsche Eingabe. Bitte erneut versuchen.{bcolors.ENDC}\n")

    recipientList.sort()
    for tempRecipient in recipientList:
        recipientByte |= 1 << tempRecipient

    print(f"{bcolors.OKGREEN}Ausgewählte Empfänger {recipientList} Binär:{hex(recipientByte)}{bcolors.ENDC}\n")


def chooseCommandDuration():
    global commandDuration
    while 1:
        print("Bitte die Dauer des Befehls wählen:\n" +
              "0 = Befehl wird dauerhaft gesendet (= Ändern des Befehls/Modus)\n" +
              "1 = Befehl wird einaml gesendet\n" +
              "-1, um das Programm zu beenden.")
        commandDuration = int(input(">> "))
        if commandDuration == -1:
            exit()
        if commandDuration in (0, 1):
            print(f"{bcolors.OKGREEN}Ausgewählte Dauer: {durationArr[commandDuration]}\n{bcolors.ENDC}")
            break
        else:
            print(f"{bcolors.FAIL}Unbekannte Dauer. Bitte erneut auswählen.\n{bcolors.ENDC}")


def chooseBasestationCommandType():
    global cmdType
    while 1:
        print("Bitte Basestation Befehlsart auswählen:\n" +
              "0 = Abfrage von Daten\n" +
              "1 = Update von Informationen\n" +
              "-1, um das Programm zu beenden.")
        cmdType = input(">> ")
        cmdType = int(cmdType)
        if cmdType == -1:
            exit()
        if cmdType not in (0, 1):
            print(f"{bcolors.FAIL}Unbekannte Befehlsart. Bitte erneut auswählen.\n{bcolors.ENDC}")
        else:
            print(f"{bcolors.OKGREEN}Ausgewählte Befehlsart: {baseStationCmdType[cmdType]}\n{bcolors.ENDC}")
            break


def chooseBasestationCommand():
    global cmdType
    global cmd
    global bsBnoMode
    global sessionId
    global bsUpdateData
    global bsUpdateDataByte

    if cmdType == 0:
        while 1:
            print("Bitte die Informationen auswählen, welche Abgefragt werden sollen:\n" +
                  "0 = Abfrage der Anzahl der Nodes\n" +
                  "1 = Abfragen der SessionID\n" +
                  "2 = Abfragen der BNO-Daten\n" +
                  "3 = Abfragen der konfigurierten Gloves\n" +
                  "4 = Abfragen der aktiven Gloves\n" +
                  "-1, um das Programm zu beenden.")
            cmd = input(">> ")
            cmd = int(cmd)
            if cmd == -1:
                exit()
            if cmd not in (0, 1, 2, 3, 4):
                print(f"{bcolors.FAIL}Unbekannte Informationsart. Bitte erneut auswählen.\n{bcolors.ENDC}")
            else:
                print(f"{bcolors.OKGREEN}Ausgewählte Informationsart: {baseStationDataCmd[cmd]}\n{bcolors.ENDC}")

                if cmd == 2:
                    while 1:
                        print("Bitte BNO-Daten-Modus auswählen:\n" +
                              "0 = Quat\n" +
                              "1 = Quat-LinAcc\n" +
                              "-1, um das Programm zu beenden.")
                        bsBnoMode = input(">> ")
                        bsBnoMode = int(bsBnoMode)
                        if bsBnoMode == -1:
                            exit()
                        if bsBnoMode not in (0, 1):
                            print(f"{bcolors.FAIL}Unbekannter BNO-Daten-Modus. Bitte erneut auswählen.\n{bcolors.ENDC}")
                        else:
                            print(
                                f"{bcolors.OKGREEN}Ausgewählter BNO-Daten-Modus: {baseStationBNOMode[bsBnoMode]}\n{bcolors.ENDC}")
                            break
                break

    elif cmdType == 1:
        while 1:
            print("Bitte auswählen, welche Daten geupdatet werden sollen:\n" +
                  "0 = Updaten der SessionId\n" +
                  "1 = Updaten der konfigurierten Gloves\n" +
                  "2 = Updaten der aktiven Gloves\n" +
                  "3 = Finden inaktiver Nodes\n" +
                  "-1, um das Programm zu beenden.")
            cmd = input(">> ")
            cmd = int(cmd)
            if cmd == -1:
                exit()
            if cmd not in (0, 1, 2, 3):
                print(f"{bcolors.FAIL}Unbekannte Auswahl. Bitte erneut auswählen.\n{bcolors.ENDC}")
            else:
                print(f"{bcolors.OKGREEN}Ausgewählte Informationswahl, was geupdatet werden soll: {baseStationUpdateCmd[cmd]}\n{bcolors.ENDC}")
                break

        if cmd == 0:    # Update session ID
            while 1:
                print("\nBitte neue SessionId eingeben (0-255):\n" +
                      "-1, um das Programm zu beenden.\n")
                sessionId = input(">> ")
                sessionId = int(sessionId)
                if (sessionId == -1):
                    exit()
                if (0 <= sessionId and sessionId <= 255):
                    print(f"{bcolors.OKGREEN}{'Ausgewählte SessionID:': <25} {sessionId}\n")
                    break
                else:
                    print(f"{bcolors.FAIL}\nFalsche Eingabe. Bitte eine ID zwischen 0 und 255 eingeben.{bcolors.ENDC}\n")

        elif cmd == 1 or cmd == 2:  # Update Configured Gloves or Update Active Gloves
            while 1:
                if cmd == 1:
                    print(f"\nBitte zu konfigurierende Gloves auswählen (0-15).\n" +
                          f"-1, um die Eingabe von neuen Gloves zu beenden.\n" +
                          f"-2, um alle Gloves auszuwählen.\n" +
                          f"Bereits ausgewähtle Gloves {bcolors.OKCYAN}{bsUpdateData}{bcolors.ENDC}")
                elif cmd == 2:
                    print(f"\nBitte zu aktivierende Gloves auswählen (0-15).\n" +
                          f"-1, um die Eingabe von neuen Gloves zu beenden.\n" +
                          f"-2, um alle Gloves auszuwählen.\n" +
                          f"Bereits ausgewähtle Gloves {bcolors.OKCYAN}{bsUpdateData}{bcolors.ENDC}")
                tempGlove = int(input(">> "))
                if tempGlove == -1:
                    if len(bsUpdateData) != 0:
                        break
                    else:
                        print(f"{bcolors.FAIL}Bitte mindestens einen Glove auswählen.{bcolors.ENDC}\n")
                elif tempGlove == -2:
                    bsUpdateData = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]
                    break
                if 0 <= tempGlove and tempGlove <= 15:
                    bsUpdateData.append(tempGlove)
                else:
                    print(f"{bcolors.FAIL}Falsche Eingabe. Bitte erneut versuchen.{bcolors.ENDC}\n")

            bsUpdateData.sort()
            for tempGlove in bsUpdateData:
                bsUpdateDataByte |= 1 << tempGlove

            if cmd == 1:
                print(f"{bcolors.OKCYAN}Konfigurierte Gloves {bsUpdateData}{bcolors.ENDC}\n")
            elif cmd == 2:
                print(f"{bcolors.OKCYAN}Aktive Gloves {bsUpdateData}{bcolors.ENDC}\n")

        elif cmd == 3: # Update Gloves (find inactive gloves an eliminate them)
            while 1:
                print(f"\nNur zu Testzwecken. Auswählen der zu elemenierenden Gloves.\n" +
                          f"-1, um die Eingabe von neuen Gloves zu beenden.\n" +
                          f"-2, um alle Gloves auszuwählen.\n" +
                          f"Bereits ausgewähtle Gloves {bcolors.OKCYAN}{bsUpdateData}{bcolors.ENDC}")
                tempGlove = int(input(">> "))
                if tempGlove == -1:
                    if len(bsUpdateData) != 0:
                        break
                    else:
                        print(f"{bcolors.FAIL}Bitte mindestens einen Glove auswählen.{bcolors.ENDC}\n")
                elif tempGlove == -2:
                    bsUpdateData = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]
                    break
                if 0 <= tempGlove and tempGlove <= 15:
                    bsUpdateData.append(tempGlove)
                else:
                    print(f"{bcolors.FAIL}Falsche Eingabe. Bitte erneut versuchen.{bcolors.ENDC}\n")

            bsUpdateData.sort()
            for tempGlove in bsUpdateData:
                bsUpdateDataByte |= 1 << tempGlove

            print(f"{bcolors.OKCYAN}Zu elemenierende Gloves {bsUpdateData}{bcolors.ENDC}\n")

def chooseBasestationCommandDuration():
    global cmdType
    global commandDuration

    if cmdType != 1: # if the Command is no update CMD than it could also executed only once
        while 1:
            print("Bitte die Dauer des Befehls wählen:\n" +
                  "0 = Befehl wird dauerhaft auf der BS ausgeführt (= Ändern des Befehls/Modus)\n" +
                  "1 = Befehl wird einaml ausgeführt\n" +
                  "-1, um das Programm zu beenden.")
            commandDuration = int(input(">> "))
            if commandDuration == -1:
                exit()
            if commandDuration in (0, 1):
                print(f"{bcolors.OKGREEN}Ausgewählte Dauer: {durationArr[commandDuration]}\n{bcolors.ENDC}")
                break
            else:
                print(f"{bcolors.FAIL}Unbekannte Dauer. Bitte erneut auswählen.\n{bcolors.ENDC}")
        pass



def createBasestationCommand():
    global bsMode
    global cmdType
    global cmd
    global bsBnoMode
    global initSend
    global sendData
    global sessionId

    ##Byte 0-1 Sync Byte
    initSend = b'\xAB'
    sendData = b'\xCD'
    ##Byte 2 Duration
    sendData += commandDuration.to_bytes(1, 'big')
    ##Byte 3-4 Receiver Byte
    sendData += b'\x00'
    sendData += b'\x00'
    ##Byte 5 CommandType
    if cmdType == 0:    # AbfrageCommand
        sendData += b'\xFE'  # CommandType COMMAND_TYPE_REQUEST_BS_DATA
    elif cmdType == 1:  # Update Informationen
        sendData += b'\xFD'  # CommandType COMMAND_TYPE_UPDATE_BS_DATA

    ##Byte 6 CMD
    sendData += cmd.to_bytes(1, 'big')

    if (cmdType == 0 and cmd == 2):
        ##Byte 7 Command/BNO-Mode
        sendData += bsBnoMode.to_bytes(1, 'big')

        sendData += b'\xA0'
        for i in range(0, 23):
            sendData += b'\x00'

    elif (cmdType == 1):  #Update Command
        if (cmd == 0): # Update SessionId
            #Byte 7 New SessionID
            sendData += sessionId.to_bytes(1, "big")

            sendData += b'\xA0'
            for i in range(0, 23):
                sendData += b'\x00'

        elif (cmd == 1 or cmd == 2): #Ändern der konfigurierten/aktivierten Gloves
            #Byte 7 and 8 configured/active Nodes
            sendData += bsUpdateDataByte.to_bytes(2, 'big')

            sendData += b'\xA0'
            for i in range(0, 22):
                sendData += b'\x00'

        elif (cmd == 3): #Elemenieren von Glove (Find and eleminate inactive Gloves)
            # Byte 7 and 8 Gloves to be eliminated
            sendData += bsUpdateDataByte.to_bytes(2, 'big')

            sendData += b'\xA0'
            for i in range(0, 22):
                sendData += b'\x00'


    else:
        sendData += b'\xA0'
        for i in range(0, 24):
            sendData += b'\x00'




def printBasestationData():
    pass


def chooseGloveCommandType():
    global cmdType
    while 1:
        print("Bitte Befehlsart auswählen:\n" +
              "0 = General Command\n" +
              "1 = Data-Mode\n" +
              "2 = Info-Mode\n" +
              "3 = Update Command\n" +
              "-1, um das Programm zu beenden.")
        cmdType = input(">> ")
        cmdType = int(cmdType)
        if cmdType == -1:
            exit()
        if cmdType not in (0, 1, 2, 3):
            print(f"{bcolors.FAIL}Unbekannte Befehlsart. Bitte erneut auswählen.\n{bcolors.ENDC}")
        else:
            print(f"{bcolors.OKGREEN}Ausgewählte Befehlsart: {cmdTypeArr[cmdType]}\n{bcolors.ENDC}")
            break


def chooseGloveCommand():
    global cmd
    while 1:
        if (cmdType == 0):  # General Command
            print("Bitte Befehl auswählen:\n" +
                  "0 = Query data\n" +
                  "1 = Idle\n" +
                  "2 = Restart\n" +
                  "3 = Recover Node\n" +
                  # "4 = Configure Node\n" +
                  "5 = Show ID\n" +
                  "-1, um das Programm zu beenden.")
            cmd = input(">> ")
            cmd = int(cmd)
            if cmd == -1:
                exit()
            if cmd not in (0, 1, 2, 3, 5):
                print(f"{bcolors.FAIL}Unbekannter Befehl. Bitte erneut auswählen.\n{bcolors.ENDC}")
            else:
                print(f"{bcolors.OKGREEN}Ausgewählter Befehl: {generalCmd[cmd]}\n{bcolors.ENDC}")
                break

        elif (cmdType == 1):  # BNO-Data Command
            print("Bitte Befehl auswählen:\n" +
                  "0 = Quat\n" +
                  "1 = Quat and Lin Acc\n" +
                  "-1, um das Programm zu beenden.")
            cmd = input(">> ")
            cmd = int(cmd)
            if cmd == -1:
                exit()
            if cmd not in (0, 1):
                print(f"{bcolors.FAIL}Unbekannter Befehl. Bitte erneut auswählen.\n{bcolors.ENDC}")
            else:
                print(f"{bcolors.OKGREEN}Ausgewählter Befehl: {dataModeCmd[cmd]}\n{bcolors.ENDC}")
                break

        elif (cmdType == 2):  # Info-Data Command
            print("Bitte Befehl auswählen:\n" +
                  "0 = Calibration Data\n" +
                  "1 = Glove Config data\n" +
                  "-1, um das Programm zu beenden.")
            cmd = input(">> ")
            cmd = int(cmd)
            if cmd == -1:
                exit()
            if cmd not in (0, 1):
                print(f"{bcolors.FAIL}Unbekannter Befehl. Bitte erneut auswählen.\n{bcolors.ENDC}")
            else:
                print(f"{bcolors.OKGREEN}Ausgewählter Befehl: {infoModeCmd[cmd]}\n{bcolors.ENDC}")
                break

        elif (cmdType == 3):  # Update Command
            print("Bitte Befehl auswählen:\n" +
                  "0 = Session ID Update\n" +
                  "-1, um das Programm zu beenden.")
            cmd = input(">> ")
            cmd = int(cmd)
            if cmd == -1:
                exit()
            if cmd not in (0, -1):
                print(f"{bcolors.FAIL}Unbekannter Befehl. Bitte erneut auswählen.\n{bcolors.ENDC}")
            else:
                print(f"{bcolors.OKGREEN}Ausgewählter Befehl: {updateCmd[cmd]}\n{bcolors.ENDC}")
                break


def createGloveCommand():
    global initSend
    global sendData
    global recipientByte
    global commandDuration
    ##Byte 0-1 Sync Byte
    initSend = b'\xAB'
    sendData = b'\xCD'
    ##Byte 2 Duration
    sendData += commandDuration.to_bytes(1, 'big')
    ##Byte 3-4 Receiver Byte
    sendData += recipientByte.to_bytes(2, 'big')
    # sendData += b'\x01'  # Empfänger 1
    # sendData += b'\x00'  # Empfänger 2

    if cmdType in (0, 1, 2):  # all commandtype except update commands
        ##Byte 5 CommandType
        # sendData += hex(cmdType).encode()
        if cmdType == 0:  # General Command
            sendData += b'\x00'
        elif cmdType == 1:  # BNO-Data Command
            sendData += b'\x01'
        elif cmdType == 2:  # Info-Data Command
            sendData += b'\x02'

        ##Byte 6 Command
        # sendData += hex(cmd).encode()
        if cmd == 0:  # CMD (General Command = Query Data, BNO-Data Command = Quat,        Info-Data Command = Calibration)
            sendData += b'\x00'
        elif cmd == 1:  # CMD (General Command = Idle,       BNO-Data Command = Quat-LinAcc, Info-Data Command = Glove Config)
            sendData += b'\x01'
        elif cmd == 2:  # CMD (General Command = Restart,    BNO-Data Command = -,           Info-Data Command = -)
            sendData += b'\x02'
        elif cmd == 3:  # CMD (General Command = Recover,    BNO-Data Command = -,           Info-Data Command = -)
            sendData += b'\x03'
        # elif cmd == 4:              #CMD (General Command = Configure,  BNO-Data Command = -,           Info-Data Command = -)
        #    sendData += b'\x04'
        elif cmd == 5:  # CMD (General Command = Show ID,    BNO-Data Command = -,           Info-Data Command = -)
            sendData += b'\x05'

        ##Byte 7 End of Command Byte
        sendData += b'\xA0'

        ##Stuff Bytes
        for i in range(0, 24):
            sendData += b'\x00'

    elif cmdType == 3:
        ##Byte 5 CommandType
        sendData += b'\x03'  # Update Command

        ##Byte 6 Command
        # sendData += hex(cmd).encode()
        if cmd == 0:  # CMD (Update Command = SessionID)
            sendData += b'\x00'

        while 1:
            print("\nBitte neue SessionId eingeben (0-255):\n" +
                  "-1, um das Programm zu beenden.\n")
            global sessionId
            sessionId = input(">> ")
            sessionId = int(sessionId)
            if (sessionId == -1):
                exit()
            if (0 <= sessionId and sessionId <= 255):
                ##Byte 7 DataByte (SessionId)
                sendData += sessionId.to_bytes(1, 'big')

                ##Byte 8 End of Command Byte
                sendData += b'\xA0'

                ##Stuff Bytes
                for i in range(0, 23):
                    sendData += b'\x00'

                print(
                    f"{bcolors.OKGREEN}{'Ausgewählte SessionID:': <25} {sessionId}\n{'Binär:': <25} {hex(sessionId)}{bcolors.ENDC}\n")

                break;
            else:
                print(
                    f"{bcolors.FAIL}\nFalsche Eingabe. Bitte eine ID zwischen 0 und 255 eingeben oder{bcolors.ENDC}\n" +
                    f"{bcolors.FAIL}-1, um das Programm zu beenden.{bcolors.ENDC}\n")


def printGloveData():
    # print(f"{bcolors.OKBLUE}{'Ausgewählte Dauer:': <25} {durationArr[commandDuration]}\n{'Binär:': <25} {hex(commandDuration)}{bcolors.ENDC}\n")
    print(
        f"{bcolors.OKBLUE}{'Ausgewählte Dauer:': <25} {durationArr[commandDuration]}\n{'Binär:': <25} {commandDuration:#0{4}x}{bcolors.ENDC}\n")

    # print(f"{bcolors.OKBLUE}{'Ausgewählte Empfänger:': <25} {recipientList}\n{'Binär:': <25} {hex(recipientByte)}{bcolors.ENDC}\n")
    print(
        f"{bcolors.OKBLUE}{'Ausgewählte Empfänger:': <25} {recipientList}\n{'Binär:': <25} {recipientByte:#0{6}x}{bcolors.ENDC}\n")

    # print(f"{bcolors.OKBLUE}{'Ausgewählte Befehlsart:': <25} {cmdTypeArr[cmdType]}.\n{'Binär:': <25} {hex(cmdType)}{bcolors.ENDC}\n")
    print(
        f"{bcolors.OKBLUE}{'Ausgewählte Befehlsart:': <25} {cmdTypeArr[cmdType]}\n{'Binär:': <25} {cmdType:#0{4}x}{bcolors.ENDC}\n")
    if (cmdType == 0):
        # print(f"{bcolors.OKBLUE}{'Ausgewählte Befehl:': <25} {generalCmd[cmd]}.\n{'Binär:': <25} {hex(cmd)}{bcolors.ENDC}\n")
        print(
            f"{bcolors.OKBLUE}{'Ausgewählte Befehl:': <25} {generalCmd[cmd]}\n{'Binär:': <25} {cmd:#0{4}x}{bcolors.ENDC}\n")
    elif (cmdType == 1):
        # print(f"{bcolors.OKBLUE}{'Ausgewählte Befehl:': <25} {dataModeCmd[cmd]}.\n{'Binär:': <25} {hex(cmd)}{bcolors.ENDC}\n")
        print(
            f"{bcolors.OKBLUE}{'Ausgewählte Befehl:': <25} {dataModeCmd[cmd]}\n{'Binär:': <25} {cmd:#0{4}x}{bcolors.ENDC}\n")
    elif (cmdType == 2):
        # print(f"{bcolors.OKBLUE}{'Ausgewählte Befehl:': <25} {infoModeCmd[cmd]}.\n{'Binär:': <25} {hex(cmd)}{bcolors.ENDC}\n")
        print(
            f"{bcolors.OKBLUE}{'Ausgewählte Befehl:': <25} {infoModeCmd[cmd]}\n{'Binär:': <25} {cmd:#0{4}x}{bcolors.ENDC}\n")
    elif (cmdType == 3):
        # print(f"{bcolors.OKBLUE}{'Ausgewählte Befehl:': <25} {updateCmd[cmd]}.\n{'Binär:': <25} {hex(cmd)}{bcolors.ENDC}\n")
        print(
            f"{bcolors.OKBLUE}{'Ausgewählte Befehl:': <25} {updateCmd[cmd]}\n{'Binär:': <25} {cmd:#0{4}x}{bcolors.ENDC}\n")
        if (cmd == 0):
            # print(f"{bcolors.OKBLUE}{'Ausgewählte SessionID:': <25} {sessionId}\n{'Binär:': <25} {hex(sessionId)}{bcolors.ENDC}\n")
            print(
                f"{bcolors.OKBLUE}{'Ausgewählte SessionID:': <25} {sessionId}\n{'Binär:': <25} {sessionId:#0{4}x}{bcolors.ENDC}\n")


import serial
import time

serport = '/dev/cu.usbmodem2403'

try:
    ser = serial.Serial()
    ser.baudrate = 500_000
    ser.port = serport
    ser.timeout = None  # = None means wait forever, = 0 means do not wait
    ser.write_timeout = None
    ser.open()
    ser.reset_input_buffer()

    # Falsche Eingaben werden nicht abgefangen sondern lassen das Programm abstürzen
    cmdTypeArr = ["General Command", "Data Mode", "Info Mode", "Update Command", "Basestation Command"]
    generalCmd = ["Query Data", "Idle", "Restart", "Recover", "Configure", "Show ID"]
    dataModeCmd = ["Quat", "Quat and Lin Acc"]
    infoModeCmd = ["Calibration Data", "Glove Config Data"]
    updateCmd = ["Session ID Update"]
    baseStationMode = ["Set Basestation in Glove Mode", "Set Basestation in Basestation Mode"]
    baseStationCmdType = ["Abfrage von Daten", "Update von Informationen"]
    baseStationDataCmd = ["Number of Gloves", "SessionID", "BNO-Data", "Konfigurierte Glove", "Aktive Gloves"]
    baseStationUpdateCmd = ["Update SessionID", "Update condfigured Gloves", "Update active Gloves", "Eleminate inactive Gloves"]
    baseStationBNOMode = ["Quat-Mode", "Quat-LinAcc-Mode"]
    durationArr = ["Dauerhaft", "Einmalig"]
    cmdOptionArr = ["Ändern des Modus der Basisstation", "Senden eines Befehls zum Glove",
                    "Senden eines Befehls zur Basisstation"]

    while 1:  # ser.is_open: //TODO wieder einkommentieren wenn ser definiert ist
        chooseCommandOption()

        if cmdOption == 0:  # Ändern des Modus der Basisstation
            chooseBasestationMode()
            createBasestationModeCommand()
        elif cmdOption == 1:  # Senden eines Befehls an einen oder mehrere Gloves
            chooseRecipient()
            chooseCommandDuration()
            chooseGloveCommandType()
            chooseGloveCommand()
            createGloveCommand()
            pass
        elif cmdOption == 2:  # Senden eines Befehls an die Basistation
            chooseBasestationCommandType()
            chooseBasestationCommand()
            chooseBasestationCommandDuration() # frag nur dann die Daten ab, wenn es kein Update-Befehl ist, dieser wird sowieso nur einmal ausgeführt.
            createBasestationCommand()

        ### Send Command
        ser.write(initSend)
        time.sleep(0.1)
        print("Anzahl an gesendeten Bytes: " + str(ser.write(sendData)))

        output = initSend + sendData
        print(f"{bcolors.OKGREEN}Folgender Befehl wurde gesendet:\n{output}{bcolors.ENDC}\n\n")

        break

    print(f"\n\n\n{bcolors.UNDERLINE}Ausgabe der Empfangenen Daten:{bcolors.ENDC}\n")

    cnt = 0
    if receiveData:
        while ser.is_open:
            # """
            if cnt == 0:
                print(f"{bcolors.UNDERLINE}Dauer{bcolors.ENDC}")
            if cnt == 1:
                print(f"{bcolors.UNDERLINE}Empfänger{bcolors.ENDC}")
            elif cnt == 3:
                print(f"{bcolors.UNDERLINE}Befehlsart{bcolors.ENDC}")
            elif cnt == 4:
                print(f"{bcolors.UNDERLINE}Befehl{bcolors.ENDC}")
            elif cnt == 5:
                print(f"{bcolors.UNDERLINE}Befehlslänge{bcolors.ENDC}")
            elif cnt == 6:
                print(f"{bcolors.UNDERLINE}Daten{bcolors.ENDC}")
            # """
            inData = ser.read();
            print(inData)
            cnt += 1



except Exception as e:
    print('An error occured during sending')
    print(e)

finally:
    ser.close()
