# Network Security - Raspberry Pi Setup

## Risk Assessment

### Current Setup (Home Network)
- Raspberry Pi on same network as laptop/phone
- No port forwarding (Pi not accessible from internet)
- NAT provides basic isolation from external attacks

### Threat Model

| Threat | Likelihood | Impact | Mitigation |
|--------|------------|--------|------------|
| External attack on Pi | Low | High | NAT, no open ports |
| Malicious code in our scripts | Very Low | High | Code review, we wrote it |
| API key leak | Medium | Medium | File permissions, .gitignore |
| Pivot from Pi to LAN | Low | Very High | Network segmentation |
| Supply chain (pip packages) | Low | High | Pin versions, review deps |

## Recommended Setup (Choose One)

### Option 1: Guest Network (Easy)
Most routers have a "guest network" feature that isolates devices.

```
Main Network: Laptop, Phone, NAS
Guest Network: Raspberry Pi only
```

Benefits:
- Pi cannot see other devices
- Pi has internet access
- Zero configuration on Pi
- If Pi is compromised, attacker is isolated

How to enable:
1. Router settings → Guest Network → Enable
2. Connect Pi to guest network WiFi
3. Done

### Option 2: VLAN (Advanced)
If your router supports VLANs:

```
VLAN 1 (Main): 192.168.1.0/24 - Laptop, Phone
VLAN 2 (IoT):  192.168.2.0/24 - Raspberry Pi

Firewall rules:
- VLAN 2 → Internet: ALLOW
- VLAN 2 → VLAN 1: DENY
- VLAN 1 → VLAN 2: ALLOW (for SSH management)
```

### Option 3: Pi Firewall (Minimal)
If you can't change network, at least lock down Pi:

```bash
# On Raspberry Pi
sudo apt install ufw

# Default deny incoming
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow SSH only from your laptop
sudo ufw allow from 192.168.1.100 to any port 22

# Enable
sudo ufw enable
```

### Option 4: Separate Physical Network (Paranoid)
- Buy cheap router (~50 PLN)
- Connect: Modem → Cheap Router → Pi
- Pi has internet but is on completely separate network

## What We're Actually Doing

Our scripts:
1. Make HTTPS requests to external APIs (Moltbook, OpenRouter)
2. Write to local SQLite database
3. Generate static files
4. No incoming connections needed

This means:
- Pi doesn't need any open ports
- Pi doesn't need to be reachable from internet
- All connections are outbound only

## Practical Recommendation

**For your situation:**

1. **Use Guest Network** - easiest, very effective
2. Keep Pi updated: `sudo apt update && sudo apt upgrade`
3. Use strong SSH password or key-based auth
4. Don't store sensitive data on Pi (API keys only, no personal files)
5. If worried: backup important laptop files to cloud, not local NAS

## What CANNOT Happen

Even if Pi is completely compromised:
- Attacker cannot access your Google/Microsoft/Apple accounts (2FA)
- Attacker cannot access files behind passwords
- Attacker cannot access encrypted drives

What CAN happen:
- Attacker scans network, finds unpatched devices
- Attacker uses Pi as crypto miner
- Attacker uses your internet for attacks (IP gets flagged)

## Summary

| Setup | Effort | Security | Recommendation |
|-------|--------|----------|----------------|
| Same network, no changes | 0 | ★★☆☆☆ | Not recommended |
| Guest network | ★☆☆☆☆ | ★★★★☆ | **Best balance** |
| VLAN | ★★★☆☆ | ★★★★★ | If router supports |
| Pi firewall only | ★★☆☆☆ | ★★★☆☆ | Minimum if no guest |
| Separate router | ★★☆☆☆ | ★★★★★ | Overkill but safe |

**TL;DR: Put Pi on guest network. 5 minutes setup, problem solved.**
