import game_manager


def doAction(cmdParams):
    if cmdParams[0].lower() == "a":
        print(cmdParams)
        game_manager.addGame(cmdParams.split("|", 1)[1])


command = input()
command = "file|Z:\\game saves\\UpdFile.txt"
if command.lower()[0] == "f":
    print("File")
    with open(command.split("|")[1], "r") as reader:
        for line in reader:
            doAction(line)

else:
    doAction(command)