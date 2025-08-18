# Requirements Document

## Introduction

This project involves creating an educational DDoS simulation lab for cybersecurity training. The lab will demonstrate how distributed denial-of-service attacks work in a controlled environment using 30 computers on an internal network. The simulation will use 28 computers as "bots" in a botnet to perform a coordinated attack against 1 target computer, with 1 computer serving as the command and control (C2) server.

## Requirements

### Requirement 1

**User Story:** As a cybersecurity instructor, I want to demonstrate DDoS attack mechanics in a controlled lab environment, so that students can understand how these attacks work and how to defend against them.

#### Acceptance Criteria

1. WHEN the lab is initiated THEN the system SHALL establish a C2 server on one designated computer
2. WHEN bot clients connect THEN the C2 server SHALL register and manage up to 28 bot connections
3. WHEN an attack command is issued THEN all connected bots SHALL coordinate to send traffic to the target
4. IF a bot disconnects THEN the system SHALL continue operating with remaining bots
5. WHEN the simulation ends THEN all bots SHALL cleanly disconnect and stop attack traffic

### Requirement 2

**User Story:** As a student, I want to observe real-time attack metrics and network behavior, so that I can understand the impact and characteristics of DDoS attacks.

#### Acceptance Criteria

1. WHEN an attack is in progress THEN the C2 server SHALL display real-time statistics of connected bots
2. WHEN traffic is being generated THEN the system SHALL show requests per second and bandwidth usage
3. WHEN the target is under attack THEN monitoring tools SHALL display resource utilization
4. IF network congestion occurs THEN the system SHALL log and display network performance metrics

### Requirement 3

**User Story:** As a lab administrator, I want automated deployment across multiple Linux computers, so that I can quickly set up the simulation without manual configuration on each machine.

#### Acceptance Criteria

1. WHEN the deployment script runs THEN it SHALL automatically detect the operating system (Linux)
2. WHEN connecting to a new computer THEN the system SHALL install necessary dependencies
3. WHEN the bot client starts THEN it SHALL automatically connect to the configured C2 server
4. IF the C2 server is unreachable THEN bots SHALL retry connection with exponential backoff
5. WHEN deployment completes THEN all 28 bot computers SHALL be ready to receive commands

### Requirement 4

**User Story:** As a cybersecurity researcher, I want configurable attack parameters, so that I can demonstrate different types of DDoS attacks and their characteristics.

#### Acceptance Criteria

1. WHEN configuring an attack THEN the system SHALL allow setting target IP, port, and protocol
2. WHEN starting an attack THEN the system SHALL support HTTP flood, TCP SYN flood, and UDP flood attacks
3. WHEN setting attack intensity THEN the system SHALL allow configuring requests per second per bot
4. IF attack parameters change THEN all bots SHALL update their behavior in real-time
5. WHEN stopping an attack THEN all bots SHALL immediately cease traffic generation

### Requirement 5

**User Story:** As a network administrator, I want comprehensive logging and safety controls, so that the simulation remains contained within the lab network and doesn't cause unintended damage.

#### Acceptance Criteria

1. WHEN the system starts THEN it SHALL verify all operations are within the designated lab network range
2. WHEN generating attack traffic THEN the system SHALL include safety limits to prevent system crashes
3. WHEN logging events THEN the system SHALL record all bot activities and C2 commands
4. IF traffic exceeds safety thresholds THEN the system SHALL automatically throttle or stop the attack
5. WHEN the lab session ends THEN all logs SHALL be preserved for analysis and all attack traffic SHALL cease

### Requirement 6

**User Story:** As an educator, I want a simple control interface, so that I can easily demonstrate different attack scenarios during class.

#### Acceptance Criteria

1. WHEN accessing the C2 interface THEN it SHALL provide a web-based dashboard for easy control
2. WHEN selecting attack types THEN the interface SHALL offer preset scenarios (low, medium, high intensity)
3. WHEN monitoring the attack THEN the dashboard SHALL show real-time graphs and statistics
4. IF students need to observe THEN the interface SHALL support read-only observer connections
5. WHEN demonstrating defenses THEN the system SHALL allow enabling/disabling mitigation techniques