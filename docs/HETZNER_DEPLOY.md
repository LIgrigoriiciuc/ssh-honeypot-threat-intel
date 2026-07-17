## Deployment - Hetzner Cloud
Technical reference for the Hetzner VPS this honeypot runs on: key generation, connection commands, sshd configuration, file transfer, process management, and cron. 
SSH key
Generated a dedicated key instead of reusing an existing one, to keep this server's access isolated from other keys.
```
ssh-keygen -t ed25519 -C "hetzner-honeypot" -f ~/.ssh/hetzner_honeypot
```
`-t ed25519`: key algorithm. Elliptic-curve, smaller and faster than RSA, current recommended default for interactive login keys.
`-C`: comment field, embedded in the public key for identification purposes only. No functional effect.
`-f`: explicit output filename. Without it, `ssh-keygen` defaults to `~/.ssh/id_ed25519`, which would have collided with an existing key.
Output: `~/.ssh/hetzner_honeypot` (private, stays local) and `~/.ssh/hetzner_honeypot.pub` (public, uploaded to Hetzner's "Add SSH key" step during server creation).
Connecting
```
ssh -i ~/.ssh/hetzner_honeypot -p 2222 root@<server-ip>
```
`-i`: identity file. Required because the key isn't at the default path, so `ssh` won't pick it up automatically.
`-p 2222`: non-default port (see sshd config section below for why).
File transfer uses the same identity file and port.
```bash
scp -i ~/.ssh/hetzner_honeypot -P 2222 <local-file> root@<server-ip>:/opt/honeypot/
```
sshd configuration - moving off port 22
Port 22 needs to stay free for the honeypot process to bind to, since that's the port scanners target. Real admin SSH access was moved to 2222.
Config file: `/etc/ssh/sshd_config`. Plain text, read by sshd on start. Lines beginning with `#` are comments/disabled defaults, not active settings.
Changed:
```
#Port 2222
```
to:
```
Port 2222
```
Initial assumption was that `systemctl restart sshd` would apply this. That command ran without error but the port didn't change (confirmed with `ss -tlnp`, still showing `:22`). The actual cause was visible directly in the config file itself - `sshd_config` on this Ubuntu 26.04 image contains a comment block above the `Port` line stating:
```
# For changes to take effect, run:
#
#   systemctl daemon-reload
#   systemctl restart ssh.socket
```
Ubuntu 26.04 uses socket activation for SSH: `ssh.socket` owns the listening port and hands connections off to `sshd`, rather than `sshd` binding the port directly and persistently. Restarting `sshd` alone doesn't touch the socket's bound port. Correct sequence:
```
systemctl daemon-reload
systemctl restart ssh.socket
```
Checking listening ports
```
ss -tlnp
```
`-t`: TCP sockets only
`-l`: listening sockets only
`-n`: numeric ports, skip service name resolution
`-p`: show owning process/PID
File layout
`/opt` is a standard top-level Linux directory (sibling of `/root`, `/home`, `/etc`, all direct children of `/`), conventionally used for self-installed, non-package-managed software. Not a hard requirement, just the folder chosen here for organizational clarity.
```
mkdir -p /opt/honeypot
```
Dependencies
```
apt update && apt install python3-pip
pip3 install paramiko 
```
Running as a background process
```
nohup ./honeypot.py >> honeypot.json 2>&1 &
```
`nohup`: causes the process to ignore SIGHUP (the signal sent to child processes when the parent shell/terminal closes). Without this, the process would die on logout.
`&`: backgrounds the process, returns terminal control immediately.
- `>> honeypot.json 2>&1`: append stdout to the log file, redirect stderr into the same stream.
Checking process state:
```
jobs # shows Running/Done status if still in current session
tail -f honeypot.json # live log
```
Cron - hourly log snapshots
```
mkdir -p /opt/honeypot/backups
crontab -e
```
Default crontab opens with a large `#`-commented explanation block (syntax reference, examples). Active entries go on new lines below it.
Added line:
```
0 * * * * cp /opt/honeypot/honeypot.json /opt/honeypot/backups/honeypot_$(date +\%Y\%m\%d_\%H).json
```
- `0 * * * *`: cron time fields are minute, hour, day-of-month, month, day-of-week. `0 * * * *` = minute 0 of every hour = top of every hour.
- `\%`: `%` is escaped with a backslash specifically inside crontab, where an unescaped `%` has special meaning (newline).
