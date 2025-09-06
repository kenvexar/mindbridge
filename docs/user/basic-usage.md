# Basic Usage Guide

Daily usage patterns and best practices for MindBridge.

## Table of Contents

1. [Basic Memo Input](#basic-memo-input)
2. [AI Auto-Classification](#ai-auto-classification)
3. [Voice Memo Processing](#voice-memo-processing)
4. [Common Commands](#common-commands)
5. [Obsidian Integration](#obsidian-integration)
6. [Best Practices](#best-practices)

## 📝 Basic Memo Input

### Simple Text Messages

Post any message to the `#memo` channel and it will be automatically processed and saved to Obsidian.

**Example:**
```
Posted to #memo channel:
Had a great meeting about the new project today. Need to create requirements document by next week. Want to use modern UI design.
```

**Result:**
- AI automatically summarizes, tags, and categorizes content
- Saves to appropriate Obsidian folder (e.g., `11_Projects/`)
- Structured with YAML frontmatter and Markdown

**Generated file example:**
```markdown
---
title: "Project Planning Meeting"
tags: ["project", "meeting", "ui-design", "requirements"]
category: "Projects"
created: "2025-01-15T10:30:00Z"
source: "discord"
---

# Project Planning Meeting

## Summary
Discussion about new project planning with focus on requirements and modern UI design.

## Content
Had a great meeting about the new project today. Need to create requirements document by next week. Want to use modern UI design.

## Extracted Tasks
- [ ] Create requirements document (due: next week)

## Related Keywords
- Project planning
- UI design
- Requirements documentation
```

### URL Processing

Post URLs to `#memo` and the web content will be automatically fetched and summarized.

**Example:**
```
Posted to #memo:
Found interesting article https://example.com/ai-trends-2025
Want to read this later and see if we can apply any insights to our project.
```

**Result:**
- URL content automatically fetched and summarized
- Combined with your message for context
- Auto-tagged based on content analysis

## 🤖 AI Auto-Classification

MindBridge uses AI to automatically categorize all content posted to `#memo`. No need to choose channels manually!

### Classification Examples

**Finance Detection:**
```
Posted: "Lunch $15 at the cafe"
→ Saved to: 20_Finance/
→ Tags: ["expense", "food", "daily-spending"]
```

**Task Detection:**
```
Posted: "TODO: finish the quarterly report by Friday"
→ Saved to: 02_Tasks/
→ Tags: ["task", "deadline", "report"]
```

**Health Tracking:**
```
Posted: "Ran 5km this morning, feeling great!"
→ Saved to: 21_Health/
→ Tags: ["exercise", "running", "wellness"]
```

**Learning Notes:**
```
Posted: "Python async/await finally makes sense after reading the docs"
→ Saved to: 10_Knowledge/
→ Tags: ["programming", "python", "learning"]
```

**Daily Reflection:**
```
Posted: "Great productive day today, completed most of my goals"
→ Saved to: 01_DailyNotes/
→ Tags: ["reflection", "productivity", "daily"]
```

### Full Folder Mapping

| Content Type | Example | → Folder |
|--------------|---------|----------|
| Expenses, budgets | "Coffee $5", "Monthly budget review" | 20_Finance |
| Tasks, TODOs | "TODO: call client", "Project deadline Friday" | 02_Tasks |
| Health, fitness | "Gym workout", "Weight 70kg" | 21_Health |
| Learning, study | "JavaScript notes", "Course completed" | 10_Knowledge |
| Work projects | "Sprint planning", "Client meeting notes" | 11_Projects |
| Daily thoughts | "Today's reflection", "Morning thoughts" | 01_DailyNotes |
| Ideas, inspiration | "App idea", "Creative concept" | 03_Ideas |
| Reference materials | "Useful tutorial", "Documentation link" | 12_Resources |
| General notes | "Random thought", "Miscellaneous memo" | 00_Inbox |

## 🎤 Voice Memo Processing

Upload audio files to `#memo` for automatic transcription and processing.

**Supported formats:** MP3, WAV, FLAC, OGG, M4A, WEBM

### Usage Process

1. Open `#memo` channel
2. Drag & drop or attach audio file
3. Optionally add text comment
4. Wait for automatic processing

**Example:**
```
Upload: meeting_notes.mp3
Comment: "Team standup meeting notes"
```

**Processing:**
- Audio transcribed to text
- Transcription combined with your comment
- AI categorizes based on content
- Saved to appropriate folder (e.g., 11_Projects if work-related)

### Voice Memo Tips

1. **Speak clearly:** Better recognition accuracy
2. **Quiet environment:** Reduce background noise
3. **Optimal length:** 1-5 minutes per file
4. **Organize thoughts:** Brief outline before recording

**Good voice memo examples:**
```
"Today's reflection: Project A is going well.
Challenge is API integration - docs are unclear.
Tomorrow I'll discuss with team for solutions."

"New app idea: AI assistant that learns user behavior
and suggests optimal workflows. Could combine ML
with good UX design principles."
```

## 🎯 Common Commands

### Basic Commands

Use these in the `#commands` channel:

```bash
/help                    # Show help information
/status                  # Check bot operational status
/ping                    # Connection test
```

### Obsidian Management

```bash
/search_notes keyword     # Search notes in Obsidian
/vault_stats             # Show vault statistics
/daily_note              # Show/create today's daily note
```

**Search examples:**
```bash
/search_notes project     # Find notes containing "project"
/search_notes python ai   # Find notes with both "python" AND "ai"
```

### AI Features

```bash
/process text:"analyze this text"        # Manual AI processing
/summarize text:"long text content"      # Generate summary
/analyze_url url:"https://example.com"   # Analyze URL content
```

### Finance Management

```bash
/add_expense amount:1500 description:"book purchase" category:"education"
/expense_report period:monthly           # Monthly expense report
/add_subscription name:"Netflix" amount:1200 billing_date:15
```

### Task Management

```bash
/add_task title:"implement feature" priority:high due_date:"2025-01-20"
/list_tasks status:pending              # List incomplete tasks
/complete_task task_id:123 notes:"implementation done"
```

## 📚 Obsidian Integration

### Folder Structure

Content is automatically organized into this structure:

```
Obsidian Vault/
├── 00_Inbox/              # Uncategorized, general notes
├── 01_DailyNotes/         # Daily reflections, logs
│   └── 2025/
│       └── 01-January/
│           └── 2025-01-15.md
├── 02_Tasks/              # Task management
├── 03_Ideas/              # Ideas, inspiration
├── 10_Knowledge/          # Learning content, study notes
├── 11_Projects/           # Work projects, meetings
├── 12_Resources/          # Reference materials, links
├── 20_Finance/            # Expenses, budgets, finance
├── 21_Health/             # Health tracking, fitness
├── 30_Archive/            # Completed items
├── 80_Attachments/        # Files, images, documents
└── 90_Meta/               # Templates, metadata
```

### Note Structure

**YAML Frontmatter:**
```yaml
---
title: "Note Title"
tags: ["tag1", "tag2", "tag3"]
category: "Projects"
created: "2025-01-15T10:30:00Z"
source: "discord"
channel: "memo"
---
```

**Structured content:**
- AI-generated summary
- Original content
- Extracted tasks (if applicable)
- Related keywords
- Internal links (when relevant notes exist)

### Daily Note Integration

Messages posted to `#memo` are automatically aggregated into daily notes when appropriate.

**Example daily note (`01_DailyNotes/2025/01-January/2025-01-15.md`):**
```markdown
# 2025-01-15

## Summary
Productive day with project meetings and learning activities.

## Key Activities
- Project planning session
- Python async/await study
- Team standup meeting

## Notes Created Today
- [[Project Planning Meeting]]
- [[Python Learning Notes]]
- [[Team Standup - Sprint Planning]]

## Financial Activity
- Lunch expense: $15
- Book purchase: $25

## Task Updates
- ✅ Complete quarterly report
- 📝 New: Create requirements document (due: next week)
```

## 💡 Best Practices

### 1. Effective Tagging

Include hashtags in your messages for better categorization:

```
Today's #reading notes. Learned about #algorithms from this #programming
book. The #datastructures chapter was especially helpful.
Tomorrow I'll work on #implementation.
```

### 2. Voice Memo Scenarios

- **Commuting:** Record ideas during travel
- **Walking:** Capture thoughts during walks
- **Post-meeting:** Immediate reflection and notes
- **After learning:** Verbal summary of new concepts

### 3. Context Clarity

Provide background information for better AI analysis:

```
[Project X Meeting Notes]
Progress review showed frontend implementation is 1 day behind schedule.
Issue is API spec changes. Team will discuss solutions tomorrow.

[Learning Notes - Python Async]
Studied asyncio library usage today.
Key insight: async/await concepts are crucial.
Code examples helped clarify the concepts.
```

### 4. Regular Maintenance

```bash
# Recommended weekly routine
/vault_stats              # Check statistics
/search_notes duplicate   # Find duplicate notes
/daily_note               # Review daily note
```

### 5. Continuous Usage Patterns

- **Morning:** `/daily_note` to check today's activities
- **Ongoing:** Post thoughts immediately to `#memo`
- **Evening:** `/vault_stats` to review day's captures
- **Weekly:** `/expense_report period:weekly` for finance review

## 🔧 Customization

### Template Adjustments

Customize templates in Obsidian's `90_Meta/Templates/` folder:

```markdown
# Custom Memo Template
---
title: "{{title}}"
tags: {{tags}}
category: "{{category}}"
created: "{{timestamp}}"
priority: "{{priority}}"
---

# {{title}}

## 📝 Overview
{{summary}}

## 📋 Details
{{content}}

## 🔗 Related Links
{{related_links}}

## 📌 Action Items
{{action_items}}
```

## 🆘 Troubleshooting

### Common Issues

**Q: Messages not being processed**
A: Check channel names (`memo`, `notifications`, `commands`) and bot permissions

**Q: Voice recognition accuracy is poor**
A: Use quiet environment, speak clearly, break into shorter segments

**Q: Classification not as expected**
A: Include more specific context and background information

**Q: Can't find generated notes**
A: Use `/search_notes` command or check `/vault_stats` for file locations

### Support

- Check [Troubleshooting Guide](../operations/troubleshooting.md)
- Report issues on [GitHub Issues](https://github.com/kenvexar/mindbridge/issues)

## 📚 Next Steps

After mastering basic usage:

1. **[Commands Reference](commands-reference.md)** - Complete command list
2. **[Installation Guide](installation.md)** - Advanced setup options
3. **[Development Guide](../developer/development-guide.md)** - Customization and development

---

Follow this guide to use MindBridge effectively. Post any questions in the support channels.
