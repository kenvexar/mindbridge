# Commands Reference

Complete reference for all MindBridge commands.

## Table of Contents

1. [Command Basics](#command-basics)
2. [Basic Commands](#basic-commands)
3. [Obsidian Management](#obsidian-management)
4. [AI Processing](#ai-processing)
5. [Finance Management](#finance-management)
6. [Task Management](#task-management)
7. [System Management](#system-management)
8. [Health Data](#health-data)
9. [Troubleshooting](#troubleshooting)

## 🎯 Command Basics

### Execution Method

1. **Slash Commands**: Start with `/`
2. **Location**: Use in `#commands` channel (recommended)
3. **Permissions**: Available to all server members where bot is present

### Parameter Types

| Symbol | Meaning |
|--------|---------|
| `[required]` | Required parameter |
| `(optional)` | Optional parameter |
| `"text"` | String input |
| `123` | Numeric input |
| `true/false` | Boolean value |

## ⚙️ Basic Commands

### `/help`
Display help information and command list.

**Parameters:**
- `category` (optional): Command category
  - `basic` - Basic commands
  - `obsidian` - Obsidian management
  - `ai` - AI features
  - `finance` - Finance management
  - `tasks` - Task management
  - `system` - System management

**Examples:**
```
/help
/help category:obsidian
```

**Sample Response:**
```
📚 MindBridge Command Help

🔧 Basic Commands:
• /ping - Connection test
• /status - System status check
• /help - Show this help

📝 Obsidian Management:
• /search_notes - Search notes
• /vault_stats - Vault statistics
...
```

### `/ping`
Test bot responsiveness and Discord connection.

**Parameters:** None

**Example:**
```
/ping
```

**Sample Response:**
```
🏓 Pong!
Response time: 245ms
Discord WebSocket latency: 87ms
Bot uptime: 2 days 14 hours 32 minutes
```

### `/status`
Check overall system operational status.

**Parameters:** None

**Example:**
```
/status
```

**Sample Response:**
```
🟢 MindBridge - System Status

📊 Basic Information:
• Status: Running normally
• Uptime: 2 days 14 hours 32 minutes
• Version: 1.0.0
• Environment: production

🤖 Discord Connection:
• Connection: ✅ Normal
• Latency: 87ms
• Servers: 1
• Channels detected: 3

🧠 AI Processing:
• Today's processing: 45/1500 (daily limit)
• Average processing time: 1.23s
• Cache hit rate: 78%

💾 Obsidian:
• Vault status: ✅ Accessible
• Files created today: 12
• Total files: 234

⚡ System Resources:
• CPU usage: 12%
• Memory usage: 35%
• Disk usage: 45%
```

## 📚 Obsidian Management

### `/search_notes`
Search notes in the Obsidian vault.

**Parameters:**
- `query` [required]: Search query
- `folder` (optional): Target folder for search
- `limit` (optional): Result limit (default: 10, max: 50)
- `include_content` (optional): Include content in search (default: false)

**Examples:**
```
/search_notes query:"project"
/search_notes query:"python ai" folder:"10_Knowledge"
/search_notes query:"task" limit:5 include_content:true
```

**Sample Response:**
```
🔍 Search Results: "project" (3 items)

📄 **New Project Plan.md**
📁 11_Projects/
🕒 Created: 2025-01-15
📝 Discussed initial project planning...

📄 **Project Progress Report.md**
📁 11_Projects/
🕒 Created: 2025-01-10
📝 Frontend implementation is delayed...

📄 **Project Retrospective.md**
📁 30_Archive/
🕒 Created: 2025-01-05
📝 Lessons learned from previous project...
```

### `/vault_stats`
Display Obsidian vault statistics.

**Parameters:** None

**Example:**
```
/vault_stats
```

**Sample Response:**
```
📊 Obsidian Vault Statistics

📁 Notes by folder:
• 00_Inbox: 15 files
• 01_DailyNotes: 95 files
• 02_Tasks: 12 files
• 03_Ideas: 31 files
• 10_Knowledge: 45 files
• 11_Projects: 23 files
• 20_Finance: 18 files
• 21_Health: 8 files

📈 Recent activity:
• Today: 5 files created
• This week: 28 files created
• This month: 87 files created

💾 Storage:
• Total files: 239 files
• Total size: 12.3 MB
• Average file size: 52.8 KB

🏷️ Popular tags:
• #project (23)
• #idea (18)
• #learning (15)
• #finance (12)
• #health (8)
```

### `/daily_note`
Create or display daily notes.

**Parameters:**
- `action` [required]: Action to perform
  - `show` - Display note
  - `create` - Create new note
  - `update` - Add content
- `date` (optional): Target date (YYYY-MM-DD format, default: today)
- `content` (optional): Content to add (for update action)

**Examples:**
```
/daily_note action:show
/daily_note action:create date:"2025-01-17"
/daily_note action:update content:"Important meeting today"
```

## 🧠 AI Processing

### `/process`
Manually process text with AI.

**Parameters:**
- `text` [required]: Text to process
- `save_to_obsidian` (optional): Save to Obsidian (default: true)
- `processing_type` (optional): Processing type
  - `standard` - Standard analysis
  - `summary` - Summary focused
  - `detailed` - Detailed analysis

**Examples:**
```
/process text:"Discussed new feature design in today's meeting"
/process text:"Long article content..." processing_type:summary save_to_obsidian:false
```

**Sample Response:**
```
🧠 AI Processing Result

📝 **Summary:**
Meeting discussed new feature design, considering technical challenges and solutions

🏷️ **Tags:**
#meeting #design #feature-planning #development

📂 **Category:** Projects

🔗 **Extracted Keywords:**
• Feature design
• Technical challenges
• Solution discussion

✅ **Saved to Obsidian:** 11_Projects/meeting-feature-design.md

⏱️ **Processing time:** 1.23s
```

### `/summarize`
Generate summary of long text.

**Parameters:**
- `text` [required]: Text to summarize
- `max_length` (optional): Maximum summary length (characters, default: 200)
- `style` (optional): Summary style
  - `bullet` - Bullet points
  - `paragraph` - Paragraph format
  - `keywords` - Keyword extraction

**Examples:**
```
/summarize text:"Long article content..." max_length:150
/summarize text:"Meeting minutes..." style:bullet
```

### `/analyze_url`
Analyze and summarize URL content.

**Parameters:**
- `url` [required]: URL to analyze
- `save_summary` (optional): Save summary to Obsidian (default: true)
- `analysis_depth` (optional): Analysis depth
  - `quick` - Basic information only
  - `standard` - Standard analysis
  - `deep` - Detailed analysis

**Examples:**
```
/analyze_url url:"https://example.com/article"
/analyze_url url:"https://tech-blog.com/post" analysis_depth:deep
```

## 💰 Finance Management

### `/add_expense`
Record an expense.

**Parameters:**
- `amount` [required]: Amount (numeric)
- `description` [required]: Expense description
- `category` (optional): Category
- `date` (optional): Date (YYYY-MM-DD format, default: today)
- `payment_method` (optional): Payment method
- `tags` (optional): Additional tags (comma-separated)

**Examples:**
```
/add_expense amount:1200 description:"lunch" category:"food"
/add_expense amount:3500 description:"tech book" category:"education" payment_method:"credit card"
```

**Sample Response:**
```
💰 Expense recorded

📊 **Record details:**
• Amount: ¥1,200
• Description: lunch
• Category: food
• Date: 2025-01-17
• Payment method: cash

📈 **Monthly statistics:**
• Food total: ¥23,400 / ¥30,000 (budget)
• Today's expenses: ¥3,200
• Monthly expenses: ¥87,650

✅ **Saved to:** 20_Finance/2025-01-expenses.md
```

### `/expense_report`
Generate expense report.

**Parameters:**
- `period` [required]: Period
  - `daily` - Today
  - `weekly` - This week
  - `monthly` - This month
  - `yearly` - This year
- `category` (optional): Specific category only
- `chart` (optional): Show chart (default: true)

**Examples:**
```
/expense_report period:monthly
/expense_report period:weekly category:"food"
```

### `/add_subscription`
Register subscription service.

**Parameters:**
- `name` [required]: Service name
- `amount` [required]: Monthly fee
- `billing_date` [required]: Billing date (1-31)
- `category` (optional): Category
- `description` (optional): Description
- `auto_renew` (optional): Auto renewal (default: true)

**Examples:**
```
/add_subscription name:"Netflix" amount:1980 billing_date:15 category:"entertainment"
/add_subscription name:"Adobe CC" amount:6480 billing_date:1 category:"tools"
```

## ✅ Task Management

### `/add_task`
Create a new task.

**Parameters:**
- `title` [required]: Task title
- `description` (optional): Task details
- `due_date` (optional): Due date (YYYY-MM-DD format)
- `priority` (optional): Priority
  - `low` - Low
  - `medium` - Medium (default)
  - `high` - High
  - `urgent` - Urgent
- `project` (optional): Project name
- `tags` (optional): Tags (comma-separated)

**Examples:**
```
/add_task title:"Create requirements document" due_date:"2025-01-20" priority:high
/add_task title:"Code review" description:"Review new feature PR" project:"WebApp"
```

**Sample Response:**
```
✅ Task created

📋 **Task details:**
• ID: #T-001
• Title: Create requirements document
• Due: 2025-01-20 (in 3 days)
• Priority: 🔴 High
• Status: Pending
• Project: WebApp

⏰ **Reminder:**
• Alert set for 1 day before due date

📊 **Project statistics:**
• WebApp: 5 tasks (pending: 3, in progress: 2)
• Total: 12 active tasks

✅ **Saved to:** 02_Tasks/task-T001-requirements.md
```

### `/list_tasks`
Display task list.

**Parameters:**
- `status` (optional): Filter by status
  - `pending` - Pending
  - `in_progress` - In progress
  - `completed` - Completed
  - `all` - All (default)
- `project` (optional): Filter by project
- `priority` (optional): Filter by priority
- `due_soon` (optional): Due soon only (default: false)

**Examples:**
```
/list_tasks status:pending
/list_tasks project:"WebApp" priority:high
/list_tasks due_soon:true
```

### `/complete_task`
Mark task as completed.

**Parameters:**
- `task_id` [required]: Task ID (#T-001 format)
- `notes` (optional): Completion notes
- `time_spent` (optional): Time spent (minutes)

**Examples:**
```
/complete_task task_id:"T-001" notes:"Successfully completed. Next: request review"
/complete_task task_id:"T-003" time_spent:120
```

## 🔧 System Management

### `/backup_vault`
Create Obsidian vault backup.

**Parameters:**
- `include_media` (optional): Include media files (default: true)
- `compression` (optional): Compression level (1-9, default: 6)

**Examples:**
```
/backup_vault
/backup_vault include_media:false compression:9
```

### `/system_metrics`
Display detailed system metrics.

**Parameters:** None

**Example:**
```
/system_metrics
```

**Sample Response:**
```
📊 System Metrics (Detailed)

🖥️ **System Resources:**
• CPU usage: 12% (2 cores)
• Memory usage: 35% (1.4GB / 4GB)
• Disk usage: 45% (9GB / 20GB)
• Network: 125KB/s (up), 67KB/s (down)

🤖 **Discord Connection:**
• WebSocket latency: 87ms
• Reconnections today: 0
• Processing requests: 2
• Queued: 0

🧠 **AI Processing:**
• Today's processing: 45/1500 (3%)
• Average response time: 1.23s
• Success rate: 98.2%
• Cache hit rate: 78%

💾 **Obsidian Operations:**
• Files created today: 12
• Average file size: 52KB
• Save success rate: 100%
• Search queries: 8
```

### `/cache_info`
Check AI cache status.

**Parameters:** None

**Example:**
```
/cache_info
```

## 🏃 Health Data

### `/garmin_sync`
Sync data from Garmin Connect.

**Parameters:**
- `date` (optional): Date to sync (YYYY-MM-DD, default: yesterday)
- `data_type` (optional): Data type
  - `all` - All data (default)
  - `activities` - Activities only
  - `sleep` - Sleep data only
  - `health` - Health metrics only

**Examples:**
```
/garmin_sync
/garmin_sync date:"2025-01-15" data_type:activities
```

**Sample Response:**
```
🏃 Garmin data sync completed

📊 **Synced data (2025-01-16):**

🏃 **Activities:**
• Running: 5.2km, 28min, avg HR 145bpm
• Walking: 8,432 steps

😴 **Sleep:**
• Bedtime: 23:15
• Wake up: 06:45
• Sleep duration: 7h 30m
• Deep sleep: 1h 45m (23%)

💓 **Health metrics:**
• Resting HR: 58bpm
• Stress level: 25 (low)
• Body Battery: 85/100

✅ **Saved to:** 21_Health/2025-01-16-garmin-data.md

📈 **Weekly trends:**
• Average steps: 7,845 (goal: 8,000)
• Exercise days: 4/7
• Average sleep: 7h 12m
```

### `/health_report`
Generate health data report.

**Parameters:**
- `period` [required]: Period
  - `weekly` - This week
  - `monthly` - This month
  - `quarterly` - Quarter
- `focus` (optional): Focus area
  - `fitness` - Fitness
  - `sleep` - Sleep
  - `heart` - Heart rate
  - `all` - Overall (default)

**Examples:**
```
/health_report period:weekly
/health_report period:monthly focus:sleep
```

## 🔍 Troubleshooting

### `/debug_info`
Display debug information.

**Parameters:** None

**Example:**
```
/debug_info
```

**Sample Response:**
```
🔍 Debug Information

⚙️ **Configuration:**
• Environment: production
• Log level: INFO
• Mock mode: disabled
• Secret Manager: enabled

🔗 **Connection status:**
• Discord: ✅ Connected
• Gemini API: ✅ Normal
• Google Speech: ✅ Normal
• Obsidian Vault: ✅ Accessible

📊 **Channel configuration:**
• memo: configured (123...678)
• notifications: configured (234...789)
• commands: configured (345...890)

🐛 **Recent errors:**
• Errors (past hour): 0
• Warnings (past hour): 2
• Latest error: none

🔧 **System info:**
• Python: 3.13.0
• discord.py: 2.3.2
• uv: 0.1.32
• Uptime: 2 days 14h 32m
```

### `/test_features`
Test main functionality.

**Parameters:**
- `feature` (optional): Feature to test
  - `ai` - AI processing
  - `obsidian` - Obsidian integration
  - `discord` - Discord connection
  - `all` - All features (default)

**Examples:**
```
/test_features
/test_features feature:ai
```

**Sample Response:**
```
🧪 Running feature tests...

✅ **Discord connection test:**
• WebSocket: normal (87ms)
• Command response: normal
• Permissions: normal

✅ **AI processing test:**
• Gemini API connection: normal
• Test analysis: normal (1.23s)
• Cache: normal

✅ **Obsidian integration test:**
• Vault access: normal
• File creation: normal
• Search function: normal

❌ **Voice processing test:**
• Speech API: error (authentication failed)
• Recommended action: Check Google Cloud authentication

📊 **Test results:**
• Successful: 3/4 features
• Failed: 1/4 features
• Total execution time: 5.7s

💡 **Recommended action:**
Check voice processing authentication settings.
```

---

Use this command reference to take full advantage of MindBridge's features. Each command also has detailed help available through the `/help` command.
