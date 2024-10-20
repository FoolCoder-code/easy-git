# easy-git

Student project<br>
A simple version control tool

## Command

- `add <filepath>` Add the file to the staging area
- `add .` Add every file to the staging area
- `remove <filepath>` Remove the file from the staging area
- `remove .` Remove every file from the staging area
- `commit <message>` Make a commitment with the given message
- `restore <target commitment SHA>` Restore the file back to the commitment of given SHA
- `status {target commitment SHA}` Show SHA of the last 5 commitments. If target is given, then starts from the target
