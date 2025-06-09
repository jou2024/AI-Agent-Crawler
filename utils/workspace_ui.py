import os
import json
import threading
import http.server
import socketserver
import webbrowser

dirnow = os.path.dirname(__file__)

class WorkspaceDashboard:
    """
    Simple file-based front-end dashboard for displaying workspace_links and user messages.
    Launches a local HTTP server to serve an HTML dashboard that
    auto-refreshes by polling a JSON data file.

    Usage:
        dash = WorkspaceDashboard(ui_dir='ui', port=8000)
        dash.update(workspace_links, to_user_messages)
    """
    def __init__(self, ui_dir: str = 'ui', port: int = 8000):
        self.ui_dir = os.path.join(dirnow, "..", ui_dir)
        self.port = port
        os.makedirs(self.ui_dir, exist_ok=True)
        self.data_path = os.path.join(self.ui_dir, 'data.json')
        self.html_path = os.path.join(self.ui_dir, 'index.html')
        # Initialize data.json so the dashboard can load on start
        initial_data = {'links': [], 'messages': []}
        with open(self.data_path, 'w', encoding='utf-8') as f:
            json.dump(initial_data, f, indent=2, ensure_ascii=False)
        # Write initial HTML dashboard
        self._write_html()
        # Start HTTP server and open browser
        self._start_server()

    def _write_html(self):
        html = '''<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Workspace Links Dashboard</title>
  <style>
    table { border-collapse: collapse; width: 100%; }
    th, td { border: 1px solid #ddd; padding: 8px; }
    th { background-color: #f2f2f2; }
    .dot { font-size: 1.2em; }
    .green { color: green; }
    .red { color: red; }
  </style>
</head>
<body>
  <h2>Workspace Links</h2>
  <table id="links-table">
    <thead><tr id="table-header"></tr></thead>
    <tbody id="table-body"></tbody>
  </table>
  <h3>Messages</h3>
  <div id="messages"></div>

  <script>
    const fields = [
      'link','platform','is_confirmed','add_to_db',
      'search_info','agent_notes','link_summary','confidence'
    ];
    function renderTable(data) {
      const header = document.getElementById('table-header');
      header.innerHTML = fields.map(f => `<th>${f}</th>`).join('');
      const body = document.getElementById('table-body');
      body.innerHTML = '';
      data.links.forEach(item => {
        const row = document.createElement('tr');
        fields.forEach(key => {
          const td = document.createElement('td');
          const val = item[key];
          if (key === 'is_confirmed' || key === 'add_to_db') {
            const dot = document.createElement('span');
            dot.classList.add('dot', val === true ? 'green' : 'red');
            dot.textContent = '●';
            td.appendChild(dot);
          } else {
            td.textContent = val != null ? val : '';
          }
          row.appendChild(td);
        });
        body.appendChild(row);
      });
      const msgDiv = document.getElementById('messages');
      msgDiv.innerHTML = data.messages.map(m => `<p>${m}</p>`).join('');
    }
    async function fetchData() {
      try {
        const res = await fetch('data.json');
        const data = await res.json();
        renderTable(data);
      } catch (e) {
        console.error('Failed to load data.json:', e);
      }
    }
    window.onload = () => {
      fetchData();
      setInterval(fetchData, 2000);
    };
  </script>
</body>
</html>'''
        with open(self.html_path, 'w', encoding='utf-8') as f:
            f.write(html)

    def _start_server(self):
        """
        Serve the ui_dir over HTTP, suppressing console logs.
        """
        os.chdir(self.ui_dir)
        # Custom handler to disable logging
        class QuietHandler(http.server.SimpleHTTPRequestHandler):
            def log_message(self, format, *args):
                pass
            def log_request(self, code='-', size='-'):
                pass
        self.httpd = socketserver.TCPServer(('127.0.0.1', self.port), QuietHandler)
        thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        thread.start()
        # Open dashboard in default browser
        webbrowser.open(f'http://127.0.0.1:{self.port}/')

    def update(self, workspace_links: dict, messages: list):
        """
        Safely write the current workspace_links and user messages to data.json
        The dashboard will pick up changes automatically.
        """
        # Ensure the data file exists
        if not os.path.isdir(self.ui_dir):
            os.makedirs(self.ui_dir, exist_ok=True)
        if not os.path.isfile(self.data_path):
            with open(self.data_path, 'w', encoding='utf-8') as f:
                json.dump({'links': [], 'messages': []}, f)
        data = {
            'links': list(workspace_links.values()),
            'messages': messages
        }
        with open(self.data_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
