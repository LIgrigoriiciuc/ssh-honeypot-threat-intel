## SSH lockout postmortem

Nine days into the honeypot's run, `ssh -i ~/.ssh/hetzner_honeypot -p 2222 root@<ip>` stopped working. 

Symptom timeline

First attempt from WSL returned `Connection refused` immediately on port 2222. Refused (not timeout).

Recovery required booting Hetzner's rescue system (network-booted Debian) and mounting the server's disk at `/mnt` to inspect config offline.

Standard Linux convention: /mnt is where you attach ("mount") disks you want to look at.

When you run mount /dev/sda1 /mnt, you're telling the kernel: "take the raw bytes at /dev/sda1, run them through the ext4 driver to interpret their structure, and expose the resulting file tree at the path /mnt.". /dev/sda1 is a block device: a raw stream of bytes.

Rescue mode filesystem model

Rescue boots its own minimal OS entirely in RAM. The real server's disk is not running, it's just a block device sitting there. Mounting `/dev/sda1` at `/mnt` makes the server's files visible as regular files under `/mnt/*`, but there are no running processes from the server, no active systemd, no bound sockets. `ss -tlnp` inside rescue shows the rescue system's state, not the server's. Only configuration is inspectable, not runtime.

To make commands act as if running inside the real system (so paths, package manager, and eventual `systemctl` calls resolve correctly), bind-mount the pseudo-filesystems and chroot in:

mount --bind /dev /mnt/dev
mount --bind /proc /mnt/proc
mount --bind /sys /mnt/sys
chroot /mnt /bin/bash

Inside the chroot, `/etc/ssh/sshd_config` refers to the server's config, not the rescue system's.

/etc on Ubuntu already exists on the disk as real files. When you mount /dev/sda1 /mnt, /mnt/etc is automatically populated with your Ubuntu's /etc, because it's just files on the ext4 partition. Same for /home, /root, /opt, /var, /usr, /bin, etc. All of those are ordinary directories with ordinary files stored on disk. One mount makes them all appear.

/dev, /proc, /sys are different, they're NOT stored on disk. They're "virtual" filesystems that the kernel generates in RAM at boot time and populates dynamically. If you look at your Ubuntu's disk when nothing's booted from it, /dev, /proc, /sys are just empty folders. There's nothing to mount from the disk, the actual contents only exist when a kernel is running and filling them in

chroot /mnt /bin/bash =

/mnt -> the new root

/bin/bash -> the program to execute inside that new root

mount <device> <path> -> attach a filesystem from a block device (like a disk partition) at a path. Uses a filesystem driver (ext4, ntfs, ...) to interpret raw bytes as files. Example: mount /dev/sda1 /mnt makes disk contents browseable at /mnt.

mount --bind <dir> <path> -> make an existing directory appear at a second path too. No device, no filesystem driver, just a second window onto the same data. Example: mount --bind /dev /mnt/dev makes /dev's contents also visible at /mnt/dev.

Bug 1: socket activation override was never actually written

`sshd_config` on the server correctly had `Port 2222`. But `/etc/systemd/system/ssh.socket.d/` was empty, no override file existed. Meanwhile the base unit at `/lib/systemd/system/ssh.socket` still specified:

[Socket]
ListenStream=0.0.0.0:22
ListenStream=[::]:22
BindIPv6Only=ipv6-only


So the socket was still listening on 22, not 2222. `Port` in `sshd_config` is not what binds the port under socket activation, `ssh.socket`'s `ListenStream=` directives are, and sshd_config is only consulted when sshd is invoked per-connection. Restarting `ssh.socket` without an override just re-binds it to the base unit's port.

The fix required creating `/etc/systemd/system/ssh.socket.d/override.conf`. Second bug: IPv6-only socket refusing IPv4.

External SSH from WSL comes in over IPv4 (the address `167.233.89.21` is IPv4, and WSL2's default routing prefers v4). Nothing was listening for IPv4 -> RST -> `Connection refused` again, this time on 2222 instead of on the missing service.

Working override:

[Socket]
ListenStream=
ListenStream=0.0.0.0:2222
ListenStream=[::]:2222

then:

```
systemctl daemon-reload

systemctl restart ssh.socket
```

Old Ubuntu (pre-22.10) and most other distros: sshd is a normal long-running daemon. It starts at boot, binds the port itself, sits there waiting. One place controls the port: sshd_config's Port line. Simple.

Modern Ubuntu (22.10+): they switched to socket activation for sshd. Now sshd doesn't bind the port. ssh.socket (a systemd feature) binds the port, sits there listening, and only starts sshd when a connection actually comes in. Each incoming connection spawns a fresh sshd@<connection>.service instance that handles just that one session and exits.

This creates the split-config problem:

ssh.socket (the listener) needs to know what port to bind. That's ListenStream= in the socket unit.

sshd (the actual SSH server) still reads sshd_config for its own settings - auth methods, allowed users, ciphers, and a Port line that it uses internally for things like default binding fallback and some log messages.

Older Ubuntu: sshd is still a plain daemon and one config line does it.

Third bug: VPN hanging the SSH handshake

With the server side finally working, `ssh -vvv -p 2222` from WSL now progressed past TCP connect. Banner exchange succeeded (`Remote protocol version 2.0, remote software version OpenSSH_10.2p1 Ubuntu-2ubuntu3.5` — real OpenSSH, not the paramiko honeypot). `SSH2_MSG_KEXINIT` sent and received. Then it hung indefinitely at `expecting SSH2_MSG_KEX_ECDH_REPLY`.

SSH's handshake starts with small messages (banner, KEXINIT - a few hundred bytes) and then sends a much larger one (the key exchange reply, ~1KB+ with the negotiated post-quantum KEX). The small ones fit through the VPN tunnel fine. The large one doesn't: the VPN's own overhead shrinks the effective packet size limit below what SSH is trying to send, and the oversized packet gets silently dropped somewhere on the path with no error returned to either side. Client waits forever for a reply that will never arrive. Server thinks it already sent it.

Diagnostic that identified this as a client-side issue: the same hang happened trying to SSH to a completely unrelated server from the same WSL session. Two independent servers can't both be broken the same way at the same moment - the shared factor was the client and its network path.

Turning off the VPN made SSH work immediately.

> **MTU side note.** MTU = Maximum Transmission Unit = the largest packet size a network link accepts, typically 1500 bytes on Ethernet. VPNs wrap packets in extra headers (encryption, tunneling), so they eat into that budget - the usable size inside the tunnel might be 1400 or less. Normally the network reports "too big, try smaller" via an ICMP message and the sender adjusts (called Path MTU Discovery). But lots of networks drop ICMP, so the feedback never arrives - the packet vanishes silently. This is called an **MTU black hole**. Small SSH messages slip through unnoticed; the first big one falls in. Fix is either drop the VPN or lower the WSL interface's MTU manually (`ip link set dev eth0 mtu 1280`).
