import os
import argparse
import configparser
import logging
import difflib
import hashlib

from datetime import datetime

class easyGit:
    def __init__(self) -> None:
        # Get current path & repository path
        self.currentPath = os.getcwd()
        self.repoPath = getRepositoryPath(convertToPath(self.currentPath))

        # Return if repository doe not exist
        if self.repoPath is None:
            print("Could not find repository folder, exiting...")
            return

        # Get folders' paths
        self.projectFolderPath = convertToPath(os.path.dirname(self.repoPath))
        self.commitFolderPath = convertToPath(os.path.join(self.repoPath, "commit"))
        self.changeFolderPath = convertToPath(os.path.join(self.repoPath, "changes"))

        # Get files' paths
        self.logFile = convertToPath(os.path.join(self.repoPath, "log", "log.log"))
        self.headFile = convertToPath(os.path.join(self.repoPath, "commit", "HEAD"))

        # Read configuration
        self.config = configparser.ConfigParser()
        self.config.read(os.path.join(self.repoPath, "config.ini"))

        # Set logging level
        loggingLevel = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL,
        }.get(self.config.get("LOG", "logginglevel", fallback = "debug").upper(), logging.DEBUG)

        self.logger = logging.getLogger("easygit")
        self.logger.setLevel(loggingLevel)
        self.logger.addHandler(logging.FileHandler(self.logFile))

    def add(self, targetFilenames: list[str]) -> None:
        """Add file(s) to the staging area"""
        def getAllChildFiles(__targetFolderPath__: os.PathLike) -> list[os.PathLike]:
            filePaths = []
            for path in os.listdir(__targetFolderPath__):
                item = os.path.join(__targetFolderPath__, path)
                if os.path.isfile(item):
                    filePaths.append(item)
                    self.logger.debug(f"[{getTime()}] File located: {item}")
                elif os.path.isdir(item) and item != os.path.join(__targetFolderPath__, ".easygit"):
                    filePaths.extend(getAllChildFiles(item))
            return filePaths

        self.logger.debug(f"[{getTime()}] function add executed")

        # Get path(s)
        if "." in targetFilenames:
            filePaths = getAllChildFiles(self.currentPath)
        else:
            filePaths = []
            for filename in targetFilenames:
                currentFilePath = convertToPath(filename)
                if currentFilePath is None:
                    self.logger.warning(f"[{getTime()}] Cannot find file: {currentFilePath}, ignoring...")
                    continue
                self.logger.debug(f"[{getTime()}] Added file: {currentFilePath}")
                filePaths.append(currentFilePath)

        # Get staging area file
        stagingFilePath = os.path.join(self.repoPath, "stagingCache")

        # Merge paths
        if os.path.exists(stagingFilePath):
            with open(stagingFilePath, "r", encoding = "utf-8") as stagingFileIO:
                mergedFilePaths = set(filePaths)
                for f in stagingFileIO.readlines():
                    mergedFilePaths.add(f.strip("\n"))
        else:
            mergedFilePaths = set(filePaths)

        # Write data
        with open(stagingFilePath, "w", encoding = "utf-8") as stagingFileIO:
            for f in mergedFilePaths:
                if ".easygit" in f:
                    continue
                stagingFileIO.write(f"{f}\n")

    def remove(self, targetFilenames: list[str]) -> None:
        """Remove file(s) from the staging area"""
        def getAllChildFiles(__targetFolderPath__: os.PathLike) -> list[os.PathLike]:
            filePaths = []
            for path in os.listdir(__targetFolderPath__):
                item = os.path.join(__targetFolderPath__, path)
                if os.path.isfile(item):
                    filePaths.append(item)
                    self.logger.debug(f"[{getTime()}] File located: {item}")
                elif os.path.isdir(item) and item != os.path.join(__targetFolderPath__, ".easygit"):
                    filePaths.extend(getAllChildFiles(item))
            return filePaths

        self.logger.debug(f"[{getTime()}] function remove executed")

        # Get staging area file
        stagingFilePath = os.path.join(self.repoPath, "stagingCache")

        # Return if staging area doesn't exist
        if not os.path.exists(stagingFilePath):
            self.logger.error(f"[{getTime()}] staging file not found")
            return

        # Get path(s)
        if "." in targetFilenames:
            filePaths = getAllChildFiles(self.currentPath)
        else:
            filePaths = []
            for filename in targetFilenames:
                currentFilePath = convertToPath(filename)
                if currentFilePath is None:
                    self.logger.warning(f"[{getTime()}] Cannot find file: {currentFilePath}, ignoring...")
                    continue
                self.logger.debug(f"[{getTime()}] Removed file: {currentFilePath}")
                filePaths.append(currentFilePath)

        # Remove paths
        originalFilePaths = set()
        with open(stagingFilePath, "r", encoding = "utf-8") as stagingFileIO:
            for f in stagingFileIO.readlines():
                originalFilePaths.add(f.strip("\n"))
        for f in filePaths:
            try:
                originalFilePaths.remove(f)
            except KeyError:
                self.logger.warning(f"[{getTime()}] File isn\'t included in staging area: {f}")

        # Write data
        if len(originalFilePaths):
            with open(stagingFilePath, "w", encoding = "utf-8") as stagingFileIO:
                for f in originalFilePaths:
                    stagingFileIO.write(f"{f}\n")
        else:
            os.remove(stagingFilePath)

    def commit(self, message: list[str]) -> None:
        """Commit change(s) of the file(s) in the staging area"""
        self.logger.debug(f"[{getTime()}] function commit executed")

        # Get staging area file
        stagingFilePath = os.path.join(self.repoPath, "stagingCache")

        # Return if staging area doesn't exist
        if not os.path.exists(stagingFilePath):
            self.logger.error(f"[{getTime()}] staging file not found")
            return

        # Get file paths
        targetFilePaths = set()
        with open(stagingFilePath, "r", encoding = "utf-8") as stagingFileIO:
            for f in stagingFileIO.readlines():
                targetFilePaths.add(f.strip("\n"))

        # Get the SHA of last commit
        with open(self.headFile, "r", encoding = "utf-8") as headIO:
            lastCommitSHA = headIO.read()

        # Get the SHA of current commit
        currentCommitSHA = SHA1(getTime() + "".join(stagingFilePath))

        # Write the SHA of current commit into head
        with open(self.headFile, "w", encoding = "utf-8") as headIO:
            headIO.write(currentCommitSHA)

        # Make directory to store changes
        os.mkdir(os.path.join(self.changeFolderPath, currentCommitSHA))

        # Commit
        with open(os.path.join(self.commitFolderPath, currentCommitSHA), "w", encoding = "utf-8") as commitIO:
            commitIO.write(f"HEAD:{lastCommitSHA}\n") # First line: SHA of last commit
            commitIO.write(f"Commitment Message:\n=====\n{'\n'.join(message)}\n=====\n")
            for f in targetFilePaths:
                with open(f, "r", encoding = "utf-8") as fileIO:
                    content = fileIO.read()

                    # Get SHA of current file
                    fileSHA = SHA1(f+content)

                    # Write
                    with open(os.path.join(self.changeFolderPath, currentCommitSHA, fileSHA), "w", encoding = "utf-8") as fileChangeIO:
                        fileChangeIO.write(content)

                # Write link in commit
                commitIO.write(f"{f}:::{fileSHA}\n")

    def restore(self, _targetCommitSHA: str = None) -> None:
        """"""
        self.logger.debug(f"[{getTime()}] function restore executed")

        if _targetCommitSHA is None:
            # Get last commit's SHA if target is None
            with open(self.headFile, "r", encoding = "utf-8") as headIO:
                targetCommitSHA = headIO.read().strip("\n")

            if targetCommitSHA == "":
                # Exit if there's no recorded commitment
                self.logger.error(f"[{getTime()}] There\'s no any recorded commitment, exiting...")
                return
        else:
            targetCommitSHA = _targetCommitSHA

        # Exit if commitment not found
        targetCommitSHAFile = os.path.join(self.commitFolderPath, targetCommitSHA)
        if not os.path.exists(targetCommitSHAFile):
            self.logger.error(f"[{getTime()}] Target commitment not found, exiting...")
            return

        with open(targetCommitSHAFile, "r", encoding = "utf-8") as targetCommitSHAIO:
            content = [l.strip("\n") for l in targetCommitSHAIO.readlines()]
            topIndex = content.index("=====")
            startIndex = topIndex + content.index("=====", topIndex + 1)
        for fileSet in content[startIndex::]:
            print(fileSet.split(":::"))
            filePath, fileSHA = fileSet.split(":::")
            os.makedirs(os.path.dirname(filePath), exist_ok = True)
            with open(os.path.join(self.changeFolderPath, targetCommitSHA, fileSHA), "r", encoding = "utf-8") as originalFileIO:
                with open(filePath, "w", encoding = "utf-8") as fileIO:
                    fileIO.write(originalFileIO.read())



    def status(self, targetSHA: str = None, maxDepth: int = 5) -> None:
        """Get the status of the targetSHA"""
        self.logger.debug(f"[{getTime()}] function status executed")
        result = self.search(targetSHA, 0, maxDepth)
        self.logger.info(f"[{getTime()}] {result[0]} <- HEAD")
        if len(result) > 1:
            for SHA in result[1::]:
                self.logger.info(f"[{getTime()}] {SHA}")

    def search(self, targetSHA: str = None, depth: int = 0, maxDepth: int = 5) -> None:
        if depth >= maxDepth:
            return

        if targetSHA is None:
            # Get last commit's SHA if target is None
            with open(self.headFile, "r", encoding = "utf-8") as headIO:
                targetCommitSHA = headIO.read().strip("\n")

            if targetCommitSHA == "":
                # Exit if there's no recorded commitment
                self.logger.error(f"[{getTime()}] There\'s no any recorded commitment, exiting...")
                return
            else:
                # Search from head
                return self.search(targetCommitSHA, 0, maxDepth)
        else:
            targetSHAFile = os.path.join(self.commitFolderPath, targetSHA)

            # Check if the file exists
            if not os.path.exists(targetSHAFile):
                self.logger.error(f"[{getTime()}] Target commit doesn\'t exist, exiting...")
                return

            # Get target commit's SHA
            with open(targetSHAFile, "r", encoding = "utf-8") as lastCommitSHAIO:
                lastCommitSHA = lastCommitSHAIO.readline().strip("\n").split(":")[-1]

            if lastCommitSHA != "":
                recursion = self.search(lastCommitSHA, depth+1, maxDepth)
            else:
                recursion = None

            # Weird recusion
            if recursion is None:
                return [targetSHA]
            else:
                return [targetSHA] + recursion


def initialization() -> None:
    """Initialize Repository"""

    # Get path
    targetRepoPath = convertToPath(os.getcwd())
    if targetRepoPath is None:
        print("Target path is not viable, exiting...")
        return

    # Detect if .easygit already exists
    if getRepositoryPath(targetRepoPath) is not None:
        print("Could not create repository, the target path is already under a repository, exiting...")
        return

    # Make directories
    repoFolderPath = os.path.join(targetRepoPath, ".easygit")
    changesFolderPath = os.path.join(repoFolderPath, "changes")
    commitFolderPath = os.path.join(repoFolderPath, "commit")
    logFolderPath = os.path.join(repoFolderPath, "log")
    for p in [repoFolderPath, changesFolderPath, commitFolderPath, logFolderPath]:
        os.mkdir(p)

    # Make configuration file
    config = configparser.ConfigParser(allow_no_value = True)
    config.add_section("LOG")
    config.set("LOG", "loggingLevel", "debug")
    config.set("LOG", "; {debug, info, warning, error, critical}")
    with open(os.path.join(repoFolderPath, "config.ini"), "w", encoding = "utf-8") as configIO:
        config.write(configIO)

    # Make Head & Log
    for f in [os.path.join(commitFolderPath, "HEAD"), os.path.join(logFolderPath, "log.log")]:
        with open(f, "w", encoding = "utf-8") as headIO:
            pass

def getRepositoryPath(targetPath: os.PathLike | str) -> os.PathLike | None:
    """Return the .easygit folder path if it exists in the current folder or any of the parent folders; otherwise return None"""
    currentFolder = convertToPath(targetPath)

    if not os.path.exists(currentFolder):
        return None

    repoPath = os.path.join(currentFolder, ".easygit") # Check if .easygit exists in the current folder
    if os.path.isdir(repoPath): # Found .easygit
        return convertToPath(repoPath)
    elif currentFolder == os.path.dirname(currentFolder): # Return none when current folder is disk folder
        return None
    else:
        return getRepositoryPath(os.path.dirname(currentFolder)) # Recurse if .easygit is not found

def convertToPath(targetPath: os.PathLike | str) -> os.PathLike | None:
    """Convert any path-like object or string into path object"""
    if isinstance(targetPath, os.PathLike):
        p = targetPath
    elif isinstance(targetPath, str):
        p = os.path.abspath(targetPath)
    else:
        raise TypeError

    if os.path.exists(p):
        return p
    return None

def SHA1(target: str) -> str:
    """Return SHA1 of the target string"""
    return hashlib.sha1(target.encode()).hexdigest()

def getTime() -> str:
    """Return the time now by the format \"%Y%m%d %H-%M-%S\""""
    return datetime.now().strftime("%Y%m%d %H-%M-%S")


def main() -> None:
    logging.basicConfig(level = logging.DEBUG)
    argParser = argparse.ArgumentParser(description = "Easy Git")
    subParser = argParser.add_subparsers(dest = "command", help = "Available commands", required = True)

    # Initialization
    initParser = subParser.add_parser("init", help = "Initialize a repository")

    # Add
    addParser = subParser.add_parser("add", help = "Add file(s) in the current folder to the staging area")
    addParser.add_argument("filenames", default = [], nargs = "+", type = str, help = "Path(s) of the file(s)")

    # Remove
    removeParser = subParser.add_parser("rm", aliases = ["remove"], help = "Remove file(s) in the current folder from the staging area")
    removeParser.add_argument("filenames", default = [], nargs = "+", type = str, help = "Path(s) of the file(s)")

    # Commit
    commitParser = subParser.add_parser("commit", help = "Submit changes in the staging area")
    commitParser.add_argument("messages", default = [], nargs = "+", type = str, help = "Commitment message")

    # Restore
    restoreParser = subParser.add_parser("restore", help = "Restore changes from the given SHA")
    restoreParser.add_argument("-t" ,"--target", default = None, type = str, help = "Target SHA")

    # Status
    statusParser = subParser.add_parser("status", help = "Search last given number amount of commit's SHA (Default 5)")
    statusParser.add_argument("-t" ,"--target", default = None, type = str, help = "Target SHA")
    statusParser.add_argument("-md", "--maxDepth", default = 5, type = int, help = "Max depth of the searching")

    args = argParser.parse_args()

    if args.command == "init":
        initialization()
    else:
        repo = easyGit()
        if args.command == "add":
            repo.add(args.filenames)
        elif args.command == "rm" or args.command == "remove":
            repo.remove(args.filenames)
        elif args.command == "commit":
            repo.commit(args.messages)
        elif args.command == "restore":
            repo.restore(args.target)
        elif args.command == "status":
            repo.status(args.target, args.maxDepth)

if __name__ == "__main__":
    main()