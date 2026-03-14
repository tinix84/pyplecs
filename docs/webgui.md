# PyPLECS Web GUI Guide

Complete guide to the PyPLECS web monitoring interface.

---

## Overview

The PyPLECS Web GUI provides a browser-based interface for:

- 📊 **Real-time monitoring** of simulation queue and status
- 🚀 **Submit simulations** with parameter configuration
- 💾 **Cache management** with statistics and controls
- 📈 **Performance analytics** and speedup tracking
- ⚙️ **Configuration** editing (planned)
- 📡 **Live updates** via WebSocket

Built with FastAPI, Jinja2, and modern web technologies.

---

## Table of Contents

- [Getting Started](#getting-started)
- [Dashboard](#dashboard)
- [Simulations Page](#simulations-page)
- [Cache Page](#cache-page)
- [Settings Page](#settings-page)
- [WebSocket Live Updates](#websocket-live-updates)
- [Keyboard Shortcuts](#keyboard-shortcuts)
- [Troubleshooting](#troubleshooting)

---

## Getting Started

### Starting the Web GUI

```bash
# Method 1: Entry point (recommended)
pyplecs-gui

# Method 2: Direct module
python -m pyplecs.webgui

# Method 3: Python script
python start_webgui.py

# Custom port
pyplecs-gui --port 5001

# Custom host (bind to all interfaces)
pyplecs-gui --host 0.0.0.0
```

**Expected output**:
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:5000
```

### Accessing the Interface

Open your browser to: **http://localhost:5000**

**Supported Browsers**:
- ✅ Chrome/Chromium (recommended)
- ✅ Firefox
- ✅ Edge
- ✅ Safari
- ⚠️ Internet Explorer (not supported)

### First Time Setup

1. **Start PLECS** with XML-RPC enabled
   - PLECS > Preferences > Remote Control > Enable
   - Default port: 1080

2. **Run setup wizard** (if not done already)
   ```bash
   pyplecs-setup
   ```

3. **Start Web GUI**
   ```bash
   pyplecs-gui
   ```

4. **Open browser** to http://localhost:5000

You should see the dashboard with system status.

---

## Dashboard

The main dashboard provides at-a-glance monitoring.

### Layout

```
┌─────────────────────────────────────────────────┐
│  PyPLECS Dashboard                     [Status] │
├─────────────────────────────────────────────────┤
│                                                 │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐│
│  │  Queue     │  │   Cache    │  │  System    ││
│  │  Status    │  │   Stats    │  │  Info      ││
│  └────────────┘  └────────────┘  └────────────┘│
│                                                 │
│  ┌─────────────────────────────────────────────┐│
│  │        Active Simulations (Real-time)       ││
│  │  [====================>        ] 75%        ││
│  │  Task: abc123... | Running | 7.5s elapsed   ││
│  └─────────────────────────────────────────────┘│
│                                                 │
│  ┌─────────────────────────────────────────────┐│
│  │          Recent Completions                 ││
│  │  ✅ Task def456... | Completed | 8.2s       ││
│  │  ✅ Task ghi789... | Completed | 7.9s       ││
│  └─────────────────────────────────────────────┘│
│                                                 │
└─────────────────────────────────────────────────┘
```

### Widgets

#### Queue Status Card
- **Pending**: Tasks waiting in queue
- **Running**: Currently executing simulations
- **Completed**: Successfully finished tasks
- **Failed**: Tasks that encountered errors
- **Avg Duration**: Average simulation time

**Example**:
```
┌──────────────────┐
│  Queue Status    │
├──────────────────┤
│ Pending:     5   │
│ Running:     2   │
│ Completed: 1523  │
│ Failed:     12   │
│ Avg: 8.5s        │
└──────────────────┘
```

#### Cache Stats Card
- **Hit Rate**: Percentage of cache hits
- **Total Entries**: Number of cached simulations
- **Disk Usage**: Cache storage size
- **Speedup**: Performance improvement from caching

**Example**:
```
┌──────────────────┐
│  Cache Stats     │
├──────────────────┤
│ Hit Rate: 76.1%  │
│ Entries:  2001   │
│ Size:    145 MB  │
│ Speedup:  5.2x   │
└──────────────────┘
```

#### System Info Card
- **PLECS**: Connection status
- **Version**: PyPLECS version
- **Uptime**: Server uptime
- **CPU Cores**: Available cores for parallelization

**Example**:
```
┌──────────────────┐
│  System Info     │
├──────────────────┤
│ PLECS: Connected │
│ Version: 1.0.0   │
│ Uptime: 1h 23m   │
│ Cores: 4         │
└──────────────────┘
```

### Real-Time Updates

Dashboard updates automatically via WebSocket:
- ⚡ **Live progress bars** for running simulations
- 🔄 **Auto-refresh** queue statistics
- 📊 **Instant updates** when simulations complete

**Status indicators**:
- 🟢 **Green**: Healthy, PLECS connected
- 🟡 **Yellow**: Warning, high queue depth
- 🔴 **Red**: Error, PLECS disconnected

---

## Simulations Page

Submit and manage simulations.

### Submit New Simulation

**Form Fields**:

1. **Model File** (required)
   - Path to `.plecs` file
   - Can be absolute or relative to working directory
   - Autocomplete suggests recent models

2. **Parameters** (optional)
   - JSON format: `{"Vi": 12.0, "Vo": 5.0, "fsw": 100000}`
   - Or key-value editor:
     ```
     Vi:  12.0
     Vo:  5.0
     fsw: 100000
     ```

3. **Output Variables** (optional)
   - Comma-separated: `Vo, IL, Iin`
   - Leave empty to return all variables

4. **Priority** (optional, default: NORMAL)
   - CRITICAL: Highest priority
   - HIGH: Important simulations
   - NORMAL: Default
   - LOW: Background jobs

5. **Metadata** (optional)
   - Custom JSON: `{"user": "engineer@company.com", "project": "buck_design"}`

**Example**:
```
┌─────────────────────────────────────────────┐
│  Submit Simulation                          │
├─────────────────────────────────────────────┤
│ Model File: [models/buck.plecs         ] 📁 │
│                                             │
│ Parameters:                                 │
│ ┌─────────────────────────────────────────┐ │
│ │ {                                       │ │
│ │   "Vi": 12.0,                           │ │
│ │   "Vo": 5.0                             │ │
│ │ }                                       │ │
│ └─────────────────────────────────────────┘ │
│                                             │
│ Priority: [NORMAL ▼]                        │
│                                             │
│            [Submit Simulation]              │
└─────────────────────────────────────────────┘
```

**After Submission**:
```
✅ Simulation submitted successfully!
Task ID: abc123-def456-ghi789
Status: Queued
Priority: NORMAL

[View Status] [View Results (when ready)]
```

### Batch Submission

For parameter sweeps or multiple simulations:

**Batch Mode**:
```
┌─────────────────────────────────────────────┐
│  Batch Submission                           │
├─────────────────────────────────────────────┤
│ Model File: [models/buck.plecs         ] 📁 │
│                                             │
│ Parameter Sweep:                            │
│ Variable: [Vi            ]                  │
│ Start:    [12            ]                  │
│ Stop:     [48            ]                  │
│ Step:     [6             ]                  │
│                                             │
│ Or paste JSON array:                        │
│ ┌─────────────────────────────────────────┐ │
│ │ [                                       │ │
│ │   {"Vi": 12.0},                         │ │
│ │   {"Vi": 24.0},                         │ │
│ │   {"Vi": 48.0}                          │ │
│ │ ]                                       │ │
│ └─────────────────────────────────────────┘ │
│                                             │
│          [Submit Batch (3 simulations)]     │
└─────────────────────────────────────────────┘
```

**After Batch Submission**:
```
✅ Batch submitted: 3 simulations
Task IDs:
- abc123-def456-ghi789 (Queued)
- jkl012-mno345-pqr678 (Queued)
- stu901-vwx234-yza567 (Queued)

[Monitor All] [Export Results (when ready)]
```

### Simulation Queue View

**Table**:
```
┌─────────────┬──────────┬────────┬──────────┬──────────┬─────────┐
│ Task ID     │ Status   │ Prio   │ Model    │ Started  │ Actions │
├─────────────┼──────────┼────────┼──────────┼──────────┼─────────┤
│ abc123...   │ Running  │ HIGH   │ buck.pl  │ 10:30:05 │ [View]  │
│ def456...   │ Queued   │ NORMAL │ buck.pl  │ --       │ [Cancel]│
│ ghi789...   │ Complete │ HIGH   │ boost.pl │ 10:29:45 │ [View]  │
│ jkl012...   │ Failed   │ LOW    │ buck.pl  │ 10:28:30 │ [Retry] │
└─────────────┴──────────┴────────┴──────────┴──────────┴─────────┘
```

**Filters**:
- Status: All / Queued / Running / Completed / Failed
- Priority: All / CRITICAL / HIGH / NORMAL / LOW
- Model: [Dropdown of recent models]
- Date Range: Last hour / Last day / Last week / Custom

**Actions**:
- **View**: See details and results
- **Cancel**: Cancel queued/running simulation
- **Retry**: Re-submit failed simulation
- **Clone**: Submit similar simulation with modified parameters

---

## Cache Page

Manage simulation result cache.

### Cache Statistics

**Overview**:
```
┌─────────────────────────────────────────────┐
│  Cache Performance                          │
├─────────────────────────────────────────────┤
│  Hit Rate: ████████████░░░░░░░░ 76.1%      │
│                                             │
│  Hits:    1523                              │
│  Misses:   478                              │
│  Total:   2001                              │
│                                             │
│  Disk Usage: 145.7 MB / 1000 MB (14.6%)     │
│                                             │
│  Oldest Entry: 2025-01-20 08:00:00          │
│  Newest Entry: 2025-01-25 10:30:00          │
│                                             │
│  Estimated Speedup: 5.2x                    │
│  Time Saved: 3h 42m                         │
└─────────────────────────────────────────────┘
```

### Cache Entries

**Table**:
```
┌────────────┬─────────┬────────────┬─────────┬───────┐
│ Model      │ Params  │ Created    │ Accessed│ Size  │
├────────────┼─────────┼────────────┼─────────┼───────┤
│ buck.plecs │ Vi=12.0 │ Jan 25 10h │ 5 times │ 72 KB │
│ buck.plecs │ Vi=24.0 │ Jan 25 10h │ 3 times │ 71 KB │
│ boost.plecs│ Vi=48.0 │ Jan 24 15h │ 1 time  │ 68 KB │
└────────────┴─────────┴────────────┴─────────┴───────┘
```

### Cache Management

**Actions**:
```
[Clear All Cache] [Clear Old Entries (>30 days)]
[Export Cache Stats] [Optimize Storage]
```

**Clear Cache Confirmation**:
```
⚠️  Warning: Clear Cache?

This will delete 2001 cache entries (145.7 MB).
Simulations will need to re-run until cache rebuilds.

[Cancel] [Confirm Clear]
```

### Cache Settings

**Configuration Panel**:
```
┌─────────────────────────────────────────────┐
│  Cache Settings                             │
├─────────────────────────────────────────────┤
│ ☑ Caching Enabled                           │
│                                             │
│ Storage Format: [Parquet ▼]                │
│   (parquet, hdf5, csv)                      │
│                                             │
│ Compression: [Snappy ▼]                     │
│   (snappy, gzip, lz4, none)                 │
│                                             │
│ TTL (Time to Live):                         │
│   [24] hours (0 = infinite)                 │
│                                             │
│ Max Cache Size:                             │
│   [1000] MB (0 = unlimited)                 │
│                                             │
│             [Save Settings]                 │
└─────────────────────────────────────────────┘
```

---

## Settings Page

**Note**: Full settings UI is planned for v1.x. Current version: read-only config display.

### Current Implementation

**Configuration Display**:
```
┌─────────────────────────────────────────────┐
│  Configuration                              │
├─────────────────────────────────────────────┤
│  PLECS:                                     │
│    Executable: C:/Program Files/...         │
│    XML-RPC Port: 1080                       │
│                                             │
│  Orchestration:                             │
│    Max Concurrent: 4                        │
│    Batch Size: 4                            │
│    Retry Attempts: 3                        │
│                                             │
│  Cache:                                     │
│    Enabled: Yes                             │
│    Format: Parquet                          │
│    Compression: Snappy                      │
│                                             │
│  [Edit config/default.yml manually]         │
│  [Reload Configuration]                     │
└─────────────────────────────────────────────┘
```

### Planned (v1.x)

**Editable Settings UI**:
- Inline editing of configuration
- Validation before save
- Hot-reload without restart
- Import/export configuration
- Multiple configuration profiles

---

## WebSocket Live Updates

The Web GUI uses WebSocket for real-time updates without polling.

### How It Works

1. **Browser connects** to `ws://localhost:5000/ws`
2. **Server pushes updates** when events occur:
   - Simulation status changes
   - Queue depth changes
   - Cache hit/miss events
   - System status changes
3. **UI updates instantly** without refresh

### Events

**Simulation Status Update**:
```json
{
  "type": "simulation_update",
  "task_id": "abc123-def456-ghi789",
  "status": "running",
  "progress": 0.75,
  "elapsed_seconds": 7.5
}
```

**Queue Update**:
```json
{
  "type": "queue_update",
  "pending": 5,
  "running": 2,
  "completed": 1523
}
```

**Cache Hit**:
```json
{
  "type": "cache_event",
  "event": "hit",
  "task_id": "def456-ghi789-jkl012",
  "speedup": 1000.0
}
```

### Connection Status

**Indicator** (top-right):
- 🟢 **Connected**: Live updates active
- 🟡 **Reconnecting**: Temporary connection loss
- 🔴 **Disconnected**: No live updates (manual refresh needed)

**Auto-reconnect**: Browser automatically reconnects if connection drops.

---

## Keyboard Shortcuts

Navigate faster with keyboard shortcuts:

### Global
- `?` - Show keyboard shortcut help
- `/` - Focus search box
- `Esc` - Close modal/dialog

### Navigation
- `g d` - Go to Dashboard
- `g s` - Go to Simulations page
- `g c` - Go to Cache page
- `g t` - Go to Settings page

### Actions
- `n` - New simulation
- `b` - Batch submission
- `r` - Refresh data
- `Ctrl+Enter` - Submit form

### Table Navigation
- `j` / `↓` - Next row
- `k` / `↑` - Previous row
- `Enter` - View selected

**Enable keyboard shortcuts**: Settings > Keyboard Shortcuts > On

---

## Troubleshooting

### Issue: "Cannot connect to server"

**Symptoms**:
```
⚠️ Connection Error
Unable to connect to PyPLECS server at http://localhost:5000
```

**Solutions**:
1. **Check server is running**:
   ```bash
   pyplecs-gui
   # Should show: Uvicorn running on http://0.0.0.0:5000
   ```

2. **Verify port not in use**:
   ```bash
   # Windows
   netstat -ano | findstr :5000

   # Linux/macOS
   lsof -i :5000
   ```

3. **Try different port**:
   ```bash
   pyplecs-gui --port 5001
   # Then access http://localhost:5001
   ```

---

### Issue: "PLECS disconnected"

**Symptoms**:
- 🔴 Red status indicator
- "PLECS: Disconnected" in system info

**Solutions**:
1. **Start PLECS** manually

2. **Enable XML-RPC** in PLECS:
   - PLECS > Preferences > Remote Control
   - Check "Enable XML-RPC server"
   - Port: 1080 (default)

3. **Check firewall**: Allow port 1080

4. **Verify config**:
   ```yaml
   # config/default.yml
   plecs:
     xmlrpc:
       host: "localhost"
       port: 1080
   ```

---

### Issue: "WebSocket disconnected"

**Symptoms**:
- 🟡 Yellow connection indicator
- No real-time updates

**Solutions**:
1. **Check browser console** (F12):
   - Look for WebSocket errors

2. **Refresh page** (F5)

3. **Clear browser cache**:
   - Ctrl+Shift+Delete
   - Clear cached files

4. **Try different browser**:
   - Chrome/Firefox recommended

5. **Check proxy settings**:
   - WebSocket may be blocked by proxy
   - Try direct connection

---

### Issue: "Simulation not appearing in queue"

**Symptoms**:
- Submitted simulation doesn't show in queue

**Solutions**:
1. **Check for errors** in submission response

2. **Verify model file path** is correct:
   - Use absolute path
   - Check file exists: `ls models/buck.plecs`

3. **Check browser console** (F12) for JavaScript errors

4. **Refresh page** to force update

---

### Issue: "Slow page loading"

**Symptoms**:
- Page takes >5 seconds to load
- Sluggish UI

**Solutions**:
1. **Clear cache** (browser)

2. **Reduce queue size** in config:
   ```yaml
   orchestration:
     queue_size: 100  # Reduce from 1000
   ```

3. **Check system resources**:
   - High CPU/memory usage
   - Close other applications

4. **Disable animations** (if supported in settings)

---

## Performance Tips

### For Best Experience

1. **Use Chrome or Firefox** (best WebSocket performance)

2. **Keep queue manageable** (<1000 tasks)

3. **Clear old cache entries** periodically

4. **Use batch submission** for parameter sweeps (faster than individual submissions)

5. **Monitor in background** while working in other tools

### Remote Access

Access Web GUI from other machines:

1. **Start with external host**:
   ```bash
   pyplecs-gui --host 0.0.0.0
   ```

2. **Open firewall port 5000**

3. **Access from remote machine**:
   ```
   http://<your-ip-address>:5000
   ```

⚠️ **Security Warning**: No authentication in v1.0.0. Use VPN or SSH tunnel for remote access.

**SSH Tunnel** (secure remote access):
```bash
# On remote machine
ssh -L 5000:localhost:5000 user@pyplecs-server

# Then access http://localhost:5000 in browser
```

---

## Advanced Features

### API Integration

Web GUI is built on top of REST API. You can:
- Submit via Web GUI, monitor via API
- Submit via API, monitor via Web GUI
- Mix Web GUI and programmatic access

See [API.md](api.md) for API documentation.

### Custom Dashboards

Web GUI exposes WebSocket endpoint for custom dashboards:

```javascript
// Connect to WebSocket
const ws = new WebSocket('ws://localhost:5000/ws');

// Handle updates
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  updateCustomDashboard(data);
};
```

Build custom monitoring tools using the same data stream.

---

## Configuration

Web GUI settings in `config/default.yml`:

```yaml
webgui:
  host: "0.0.0.0"        # Bind to all interfaces
  port: 5000             # Web GUI port
  debug: false           # Debug mode (auto-reload)
  template_dir: "templates"  # Custom templates
  static_dir: "static"       # Custom static files
```

**Environment Variables**:
```bash
export PYPLECS_WEBGUI_HOST="0.0.0.0"
export PYPLECS_WEBGUI_PORT="5001"
export PYPLECS_WEBGUI_DEBUG="true"

pyplecs-gui
```

---

## Support

- **GitHub Issues**: https://github.com/tinix84/pyplecs/issues
- **Email**: tinix84@gmail.com
- **Documentation**: See [README.md](../README.md)

---

**Monitor your simulations in style with PyPLECS Web GUI!** 🚀
