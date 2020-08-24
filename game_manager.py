import os
import time
import shutil
#import glob
import msvcrt
import uuid

CONNECTION_RETRY = 60
FREQUENCY = 30
NUM_BACKUPS = 10

"""
localPath = "C:\\Users\\Evgol\\AppData\\Roaming\\Game Manager\\local manager.txt"
commonPath = "Z:\\game saves\\common manager.txt"
localBackup = "C:\\Users\\Evgol\\AppData\\Roaming\\Game Manager\\local game backups"
commonBackup = "Z:\\game backups"
logFile = "C:\\Users\\Evgol\\AppData\\Roaming\\Game Manager\\local game backups\\log.txt"
"""

localPath = "C:\\Users\\Evgol\\AppData\\Roaming\\Game Manager\\local manager.txt"
commonPath = "Z:\\game saves\\common manager.txt"
localBackup = "C:\\Users\\Evgol\\AppData\\Roaming\\Game Manager\\local game backups"
commonBackup = "Z:\\game backups"
logFile = "C:\\Users\\Evgol\\AppData\\Roaming\\Game Manager\\local game backups\\log.txt"
commonBlockerFile = "Z:\\game saves\\blocker.txt"




def main():
    loop = True
    sync()
    command = ""
    while loop:
        
                #RUN COMMAND
        if sync() == "COMMON DNE":
            writeLog("Connection failed, waiting until reconnect")
            while True:
                try:
                    open(commonPath, "r")
                    writeLog("Connection established, resuming")
                    break
                except FileNotFoundError:
                    print("Connection failed")
                time.sleep(CONNECTION_RETRY)

        for _ in range(0, FREQUENCY * 10):
            if loop:
                time.sleep(0.1)
            #Non blocking input
            if msvcrt.kbhit():
                tmp = msvcrt.getch()
                tmp = str(tmp).split("'")[-2]
                print(tmp, end="", flush=True)
                if tmp == "\\x08":
                    try:
                        command = command[:-2]
                    except IndexError:
                        pass
                else:
                    command += str(tmp)
                try:
                    
                    if command[-2:] == '\\n' or command[-2:] == '\\r':
                        command = command[:-2].strip()
                        print('\n' + command)
                        if command.lower() == "quit" or command.lower() == "exit":
                            loop = False
                        elif command.lower() == "add":
                            addGame(input("In one line input the data about the new game in this format (include the \"|\")\nGame Name|Common Path|Local Path\n"))
                        else:
                            print("Command not recognized")
                        command = ""
                except IndexError:
                    pass

            #print("=")


def sync():
    # Blocker file
    count = 0
    blocked = True
    while blocked:
        while os.path.exists(commonBlockerFile):
            with open(commonBlockerFile, "r") as blockerFile:
                temp = blockerFile.readline().strip()
                print(intToMAC(temp) + " " + intToMAC(uuid.getnode()))
                if temp == str(uuid.getnode()):
                    try:
                        blockerFile.close()
                        os.remove(commonBlockerFile)
                    except PermissionError as e:
                        print(e)
                    
            count += 1
            time.sleep(1)
            if count > 100:
                raise PermissionError("Blocker file exsists for too long")
        # Write mac address to the file
        with open(commonBlockerFile, "w") as f:
            f.write(str(uuid.getnode()))

        time.sleep(1)
        # Test that the file was not written to by another client
        with open(commonBlockerFile, "r") as b:
            text = b.read()
            if text.strip() == str(uuid.getnode()):
                blocked = False
    try:
        print("NEW SYNC " + time.asctime(time.localtime(time.time())))
        local = parseFile(localPath)
        try:
            common = parseFile(commonPath)
        except FileNotFoundError:
            print(commonPath + " does not exist")
            return "COMMON DNE"
        localChanged = False
        commonChanged = False

        # Manger file length comparison
        if len(local) != len(common):
            writeLog("MANAGERS ARE DIFFERENT")

            for game in local:
                if game not in common:
                    common[game] = (0, local[game][1], local[game][2])
                    commonChanged = True
                    writeLog("Added " + game + " to common")
            for game in common:
                if game not in local:
                    newLocalDir = common[game][2]
                    if not getYN("New game: " + game + "\nWould you like to use the same local directory? (Y/N)"):
                        newLocalDir = input("New local directory: ")

                    local[game] = (0, common[game][1], newLocalDir)
                    localChanged = True
                    writeLog("Added " + game + " to local")

        # Detect modifications
        for game in local:
            if float(local[game][0]) < readFolderModTime(local[game][2]):
                writeLog("Modification detected " + game)
                local[game] = (readFolderModTime(local[game][2]),
                            local[game][1], local[game][2])
                localChanged = True

        # time.sleep(100)
        # Compare
        for game in local:
            if common[game][0] > local[game][0]:
                writeLog("[COMMON -> LOCAL] " + game)

                runBackup(game, localBackup, local[game][2])

                overwriteFiles(local[game][1], local[game][2], canDelete=True)
                local[game] = (common[game][0], local[game][1], local[game][2])
                localChanged = True
                writeLog("Done")

            elif common[game][0] < local[game][0]:
                writeLog("[LOCAL -> COMMON] " + game)

                runBackup(game, commonBackup, local[game][2])

                overwriteFiles(local[game][2], local[game][1], canDelete=True)
                common[game] = (local[game][0], common[game][1], common[game][2])
                commonChanged = True
                writeLog("Done")

        if localChanged:
            writeFile(localPath, local)
        if commonChanged:
            writeFile(commonPath, common)
    finally:
        count = 0
        while True:
            count = count + 1
            try:
                os.remove(commonBlockerFile)
                break
            except PermissionError:
                pass
            if count > 100:
                raise PermissionError("Cannot remove blocker file")
            time.sleep(1)
    
    

def parseFile(filePath):  # file gameName|time|commonPath|localPath
    ret = dict()
    with open(filePath, "r") as reader:
        for line in reader:
            data = line.split("|")
            if len(data) < 3:
                return ret
            ret[data[0]] = (float(data[1]), data[2], data[3].strip("\n"))
    return ret  # ret[gameName] = (time, commonPath, localPath)


def writeFile(filePath, data):
    with open(filePath, "w") as writer:
        for line in sorted(data):
            writer.write(
                line + "|" + str(data[line][0]) + "|" + data[line][1] + "|" + data[line][2] + "\n")


def readFolderModTime(folderPath):
    ret = os.path.getmtime(folderPath)
    if os.path.isdir(folderPath):
        for p in os.listdir(folderPath):
            ret = max(readFolderModTime(folderPath + "\\" + p), ret)
    else:
        ret = os.path.getmtime(folderPath)
    return ret


def overwriteFiles(source, destination, canDelete=False):
    src = source.rstrip("\n").rstrip("\\")
    dst = destination.rstrip("\n").rstrip("\\")
    if os.path.exists(src):
        if os.path.exists(dst) and canDelete:
            writeLog("Replaced " + dst)
            shutil.rmtree(dst)
        elif not canDelete:
            raise FileExistsError
        try:
            shutil.copytree(src, dst)
        except shutil.Error as e:
            print(e + "\nTrying again after 5 sec")
            time.sleep(5)
            shutil.copytree(src, dst)
    else:
        raise FileNotFoundError


def writeLog(text, writeTime=True, end="\n"):
    with open(logFile, "a") as l:
        if writeTime:
            s = time.asctime(time.localtime(time.time())) + ": " + text + end
        else:
            s = text + end
        l.write(s)
        print(s, end="")


def addGame(parameters):
    newGame = parameters.split("|")
    if len(newGame) != 3:
        print("Invalid input")
        return
    d = parseFile(localPath)
    try:
        ti = readFolderModTime(newGame[1])
    except FileNotFoundError:
        ti = time.time()

    d[newGame[0]] = (ti, newGame[1], newGame[2].rstrip("\n"))
    writeFile(localPath, d)


def runBackup(gameBackupName, backupLocation, actualGamePath):
    """
     for i in range(NUM_BACKUPS, 0, -1): #BACKUP
        try:
            overwriteFiles(localBackup + "\\" + game + "\\" + str(i-1), localBackup + "\\" + game + "\\" + str(i), canDelete=True)
        except FileNotFoundError:
            print(i)
        if i == 1:
            overwriteFiles(local[game][2], localBackup + "\\" + game + "\\0", canDelete=True)
    """

    try:
        shutil.rmtree(backupLocation + "\\" +
                      gameBackupName + "\\" + str(NUM_BACKUPS))
    except FileNotFoundError:
        pass

    for i in range(NUM_BACKUPS, 0, -1):
        if os.path.exists((backupLocation + "\\" + gameBackupName + "\\" + str(i-1))):
            os.rename(backupLocation + "\\" + gameBackupName + "\\" + str(i-1),
                      backupLocation + "\\" + gameBackupName + "\\" + str(i))
            print(str(i-1) + " -> " + str(i))

    overwriteFiles(actualGamePath, backupLocation +
                   "\\" + gameBackupName + "\\0", canDelete=True)

def getYN(prompt):
    ret = ""
    while ret != 'y' and ret != 'n':
        ret = input(prompt)
        ret = ret.strip().lower()
    if ret == 'y':
        return True
    return False

def intToMAC(number):
    ret = [""]*6
    number = str(hex(int(number))[2:])
    for i in range(0, 6):
        ret[i] = number[i*2:(i*2)+2]
    return (":".join(ret)).upper()

if __name__ == "__main__":
    try:
        main() 
        #print(intToMAC(uuid.getnode()))
    except Exception as e:
        writeLog(e.__str__())
        raise e
    writeLog("Program exited successfully")
    #print( time.asctime(time.localtime(readFolderModTime("D:\\tst"))))
