# Unfrazzle - AI-Powered Burnout Prevention & Mental Wellness Platform

#### By: Daeren Kim, Ong Jia Xi, Lee Kai Rong
---
## Our Mission

We noticed that many people are afraid to admit they're experiencing burnout because it's often seen as a sign of incompetency in the workplace. This stigma prevents people from seeking help when they need it most, leading to worse outcomes for both individuals and organizations.

Our AI companion is designed to help you embrace your humanity—recognizing when you're overwhelmed, learning to say no to additional tasks when necessary, and understanding that having limits doesn't make you weak or incapable. We're here to normalize the conversation around workplace stress and help you advocate for your wellbeing without shame.

## Why This Matters

### The Problem We're Solving

Every day, millions of people push through mounting stress without realizing they're approaching burnout. The workplace culture that equates constant availability with competence creates an environment where admitting you're struggling feels like admitting failure. Traditional mental health resources often feel inaccessible, intimidating, or only relevant during crisis moments. Meanwhile, the small daily choices that could prevent burnout—taking breaks, scheduling self-care, recognizing warning signs—get lost in busy schedules.

We saw an opportunity to bridge this gap. What if mental health support could be as natural as getting a calendar reminder? What if preventing burnout was as simple as having a conversation with someone who truly understands your schedule and stress levels? What if saying "I need a break" was seen as self-awareness rather than weakness?

## Core AI Agent System

Unfrazzle operates through a sophisticated multi-agent system, where each AI specialist focuses on a specific aspect of your mental wellness journey:

### 1. Manager Agent - Your Orchestration Hub
**What it does**: Acts as the central coordinator, intelligently routing your needs between all other agents and ensuring a seamless experience across different types of support.

**Why you need it**: Rather than juggling multiple tools or interfaces, you have one intelligent system that understands when you need schedule optimization, emotional support, burnout assessment, or workplace guidance. It creates a unified experience that adapts to your current needs.

**Real impact**: Eliminates the mental overhead of figuring out "what kind of help do I need right now?" and provides the right support at the right time.

### 2. Scheduler Agent - Your Time & Interest Guardian
**What it does**: Analyzes your Google Calendar to identify gaps, patterns, and opportunities for wellness activities. It suggests personalized activities based on your interests and stress levels, fitting them into realistic time slots in your actual schedule.

**Why you need it**: Most people know they should take breaks or pursue hobbies, but can't find the time. This agent doesn't just suggest "exercise more"—it finds the specific 30-minute window on Tuesday when you could actually go for a walk, or identifies that you have back-to-back meetings that need breathing room.

**Key features**:
- Identifies overcommitment patterns and suggests realistic boundaries
- Finds optimal times for restorative activities based on your calendar
- Considers your personal interests (meditation, exercise, social time, creative pursuits)
- Respects your existing commitments while protecting time for wellness
- Analyzes work-life balance patterns and suggests improvements

**Real impact**: Transforms vague wellness intentions into concrete, achievable actions that fit your real life.

### 3. Secretary Agent - Your Burnout Intelligence System
**What it does**: Administers scientifically validated burnout assessment questions developed through clinical research. It tracks your burnout score over time using adaptive questioning that becomes more frequent when scores indicate higher risk.

**Core methodology**: Uses evidence-based burnout measurement scales including questions that assess:
- Emotional exhaustion and energy depletion
- Cynicism and detachment from work
- Sense of personal accomplishment and efficacy
- Work-life balance and boundary issues
- Physical symptoms of chronic stress

**Why you need it**: Many people normalize their stress levels until they're already in crisis. This agent provides objective, scientific measurement of your burnout risk, helping you recognize patterns you might dismiss as "just a busy period."

**Key features**:
- Adaptive questioning frequency based on risk levels
- Tracks burnout score trends over time
- Identifies early warning signs before they become unmanageable
- Provides personalized check-in intervals based on your current stress levels
- Maintains assessment history to show progress or areas of concern

**Real impact**: Gives you objective data about your stress levels, validating your experiences and providing concrete evidence when you need to advocate for changes.

### 4. Advisor Agent - Your Workplace Boundary Specialist
**What it does**: Focuses specifically on helping you navigate workplace dynamics when you're experiencing burnout. Provides practical scripts, strategies, and frameworks for saying no professionally, requesting accommodations, and communicating your needs without appearing incompetent.

**Why you need it**: The fear of seeming incapable often prevents people from addressing burnout. This agent specializes in helping you embrace the reality of your limits while maintaining professional relationships and career progress.

**Key features**:
- Professional communication templates for setting boundaries
- Strategies for declining additional work without damaging relationships
- Guidance on when and how to request workplace accommodations
- Scripts for conversations with managers about workload concerns
- Reframing burnout from personal failure to normal human response
- Building confidence in self-advocacy

**Real impact**: Empowers you to protect your wellbeing professionally and confidently, reducing the shame and fear around admitting you're overwhelmed.

### 5. Therapist Agent - Your 24/7 Emotional Support Companion
**What it does**: Provides immediate therapeutic-style support using evidence-based approaches for processing difficult emotions, managing stress, and developing coping strategies. Available whenever you need to talk through challenges or emotional responses.

**Why you need it**: Mental health crises don't happen during business hours, and waiting weeks for therapy appointments can feel impossible when you're struggling. This agent provides immediate support while encouraging professional care when needed.

**Key features**:
- Active listening and emotional validation
- Cognitive-behavioral techniques for managing stress and negative thought patterns
- Crisis support and safety planning
- Gentle guidance toward professional resources when appropriate
- Processing work stress, relationship issues, and life transitions
- Mindfulness and grounding techniques for acute anxiety

**Real impact**: Provides immediate emotional relief and coping strategies, preventing escalation of mental health symptoms while building resilience skills.

## User Experience Features

### Personalized Theming
Choose between **dark mode** for comfortable evening use or **light mode** for daytime clarity. Your visual comfort matters for sustained engagement with wellness practices.

### Day-by-Day Activity Approval
Instead of overwhelming you with a week's worth of changes, we present suggested activities three days at a time. You maintain complete control over what gets added to your schedule, building confidence in boundary-setting while creating sustainable habits.

### Integrated Calendar Management
Seamless Google Calendar integration means your wellness practices become part of your actual schedule, not just good intentions. Real calendar blocks for self-care make these activities as important as any meeting.

## Real-World Impact

### For Individuals
- Objective measurement of burnout risk using scientific assessment tools
- Personalized schedule optimization that fits your actual life and interests
- Professional boundary-setting skills that protect your career while preserving your wellbeing
- 24/7 emotional support that bridges gaps between professional therapy sessions
- Confidence to advocate for your needs without shame or fear of appearing incompetent

### For Workplaces
- Employees who can communicate needs and boundaries professionally
- Reduced burnout-related turnover through early intervention
- Data-informed conversations about workload and wellness
- Culture shift toward viewing stress management as professional competence

### For Healthcare Systems
- Prevention-focused approach that reduces demand on crisis mental health services
- Continuity support that maintains progress between therapy sessions
- Clear guidance on when professional intervention is needed

## Technical Architecture

- **Frontend**: React-based responsive web application with dark/light mode support
- **Backend**: Python Flask with specialized AI agent orchestration
- **AI Integration**: Claude 4-powered multi-agent system with domain-specific expertise
- **Calendar Integration**: Secure Google Calendar OAuth with intelligent schedule analysis
- **Privacy**: Local token storage with minimal data retention and HIPAA-conscious design

## Getting Started

### What You'll Experience
1. **Connect your Google Calendar** for intelligent schedule analysis
2. **Complete a scientifically-validated burnout assessment** 
3. **Review personalized activity suggestions** tailored to your interests and available time
4. **Approve or modify recommendations** day by day with full autonomy
5. **Access specialized support** whenever you need boundary-setting guidance or emotional support

### Installation & Setup

#### Prerequisites
- Python 3.8+
- Node.js 16+
- Google Cloud Console project with Calendar API enabled

#### Backend and Frontend Setup to run on your local machine
```bash
# Clone repository
git clone [repository-url]

# Install Python dependencies
cd backend
pip install -r requirements.txt

# Set environment variables
export AWS_REGION=us-east-1
export BEDROCK_MODEL_SCHEDULER=your-model-id
export GOOGLE_CREDENTIALS_PATH=./credentials.json

# Start OAuth server (Terminal 1)
cd backend
python oauth_webserver.py

# Start unified Flask server (Terminal 2)
cd backend
python flask_server.py

# Start frontend (Terminal 3)
cd frontend
npm install
npm run dev
