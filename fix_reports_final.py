with open('openroad_gui/app.py', 'r') as f:
    content = f.read()

old = '''    def _open_intelligence_reports(self) -> None:
        """Open the intelligence reports directory."""
        if not HAS_INTELLIGENCE:
            messagebox.showinfo("Intelligence Unavailable", "Intelligence reports not available.")
            return

        # Open the logs/training directory where surrogate results are stored
        try:
            import os
            reports_dir = Path("/content/drive/MyDrive/OpenRoad_Training/intelligence/training/logs")
            if not reports_dir.exists():
                # Try local path
                reports_dir = Path.cwd() / "openroad_gui" / "intelligence" / "training" / "logs"

            if not reports_dir.exists():
                messagebox.showinfo("No Reports", "Intelligence reports not found. Run training first.")
                return

            import os
            if os.uname().sysname == "Darwin":
                subprocess.Popen(["open", str(reports_dir)])
            else:
                subprocess.Popen(["xdg-open", str(reports_dir)])
        else:
            subprocess.Popen(["xdg-open", str(reports_dir)])
        except OSError as exc:
            messagebox.showerror("Open failed", str(exc))'''

new = '''    def _open_intelligence_reports(self) -> None:
        """Open the intelligence reports directory."""
        if not HAS_INTELLIGENCE:
            messagebox.showinfo("Intelligence Unavailable", "Intelligence reports not available.")
            return

        # Open the logs/training directory where surrogate results are stored
        try:
            import os
            reports_dir = Path("/content/drive/MyDrive/OpenRoad_Training/intelligence/training/logs")
            if not reports_dir.exists():
                # Try local path
                reports_dir = Path.cwd() / "openroad_gui" / "intelligence" / "training" / "logs"

            if not reports_dir.exists():
                messagebox.showinfo("No Reports", "Intelligence reports not found. Run training first.")
                return

            import os
            if os.uname().sysname == "Darwin":
                subprocess.Popen(["open", str(reports_dir)])
            else:
                subprocess.Popen(["xdg-open", str(reports_dir)])
        except OSError as exc:
            messagebox.showerror("Open failed", str(exc))'''

with open('openroad_gui/app.py', 'r') as f:
    content = f.read()

if old in content:
    content = content.replace(old, new)
    with open('openroad_gui/app.py', 'w') as f:
        f.write(content)
    print("SUCCESS: Fixed _open_intelligence_reports method")
else:
    print("Could not find method to fix")
    idx = content.find('def _open_intelligence_reports')
    if idx >= 0:
        print("Found at:", idx)
        print(content[idx:idx+300])