#!/usr/bin/env python3
"""
PTO Chrome Profile Manager
Handles backup, restore, and management of Chrome profiles for PTO scraping.
"""

import os
import json
import shutil
import zipfile
import platform
from pathlib import Path
from datetime import datetime
import getpass

class PTOProfileManager:
    def __init__(self):
        self.system = platform.system().lower()
        self.user_home = Path.home()
        self.backup_dir = Path("pto_profile_backups")
        self.backup_dir.mkdir(exist_ok=True)
        
    def get_profile_path(self):
        """Get the current PTO profile path from config"""
        config_path = Path("config.json")
        if not config_path.exists():
            return None
            
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        return config.get("pto", {}).get("chrome_user_data_dir")
    
    def create_backup(self, profile_path=None, backup_name=None):
        """Create a backup of the PTO Chrome profile"""
        if not profile_path:
            profile_path = self.get_profile_path()
        
        if not profile_path or not os.path.exists(profile_path):
            print("❌ No valid profile path found. Run setup first.")
            return False
        
        if not backup_name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"pto_profile_backup_{timestamp}"
        
        backup_path = self.backup_dir / f"{backup_name}.zip"
        
        try:
            print(f"📦 Creating backup: {backup_name}")
            print(f"📁 Source: {profile_path}")
            print(f"💾 Destination: {backup_path}")
            
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(profile_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, profile_path)
                        zipf.write(file_path, arcname)
            
            print(f"✅ Backup created successfully: {backup_path}")
            
            # Create backup info file
            info = {
                "backup_name": backup_name,
                "created_at": datetime.now().isoformat(),
                "system": self.system,
                "profile_path": profile_path,
                "backup_size": backup_path.stat().st_size
            }
            
            info_path = self.backup_dir / f"{backup_name}_info.json"
            with open(info_path, 'w') as f:
                json.dump(info, f, indent=2)
            
            return True
            
        except Exception as e:
            print(f"❌ Backup failed: {e}")
            return False
    
    def list_backups(self):
        """List all available backups"""
        backups = []
        
        for file in self.backup_dir.glob("*.zip"):
            backup_name = file.stem
            info_file = self.backup_dir / f"{backup_name}_info.json"
            
            if info_file.exists():
                with open(info_file, 'r') as f:
                    info = json.load(f)
                backups.append(info)
            else:
                # Legacy backup without info file
                backups.append({
                    "backup_name": backup_name,
                    "created_at": "Unknown",
                    "system": "Unknown",
                    "backup_size": file.stat().st_size
                })
        
        return sorted(backups, key=lambda x: x.get("created_at", ""), reverse=True)
    
    def restore_backup(self, backup_name):
        """Restore a backup to the current system"""
        backup_path = self.backup_dir / f"{backup_name}.zip"
        
        if not backup_path.exists():
            print(f"❌ Backup not found: {backup_name}")
            return False
        
        # Get target profile directory
        if self.system == "windows":
            target_dir = self.user_home / "AppData" / "Local" / "PTO_Chrome_Profile"
        elif self.system == "darwin":
            target_dir = self.user_home / "Library" / "Application Support" / "PTO_Chrome_Profile"
        else:
            target_dir = self.user_home / ".config" / "PTO_Chrome_Profile"
        
        try:
            print(f"[RESTORE] Restoring backup: {backup_name}")
            print(f"📁 Target directory: {target_dir}")
            
            # Remove existing profile if it exists
            if target_dir.exists():
                print("🗑️ Removing existing profile...")
                shutil.rmtree(target_dir)
            
            # Create target directory
            target_dir.mkdir(parents=True, exist_ok=True)
            
            # Extract backup
            print("📦 Extracting backup...")
            with zipfile.ZipFile(backup_path, 'r') as zipf:
                zipf.extractall(target_dir)
            
            # Update config
            self.update_config(target_dir)
            
            print(f"✅ Backup restored successfully!")
            print(f"📝 Profile path updated in config.json")
            return True
            
        except Exception as e:
            print(f"❌ Restore failed: {e}")
            return False
    
    def update_config(self, profile_dir):
        """Update config.json with the new profile path"""
        config_path = Path("config.json")
        
        if config_path.exists():
            with open(config_path, 'r') as f:
                config = json.load(f)
        else:
            config = {}
        
        if "pto" not in config:
            config["pto"] = {}
        
        config["pto"]["chrome_user_data_dir"] = str(profile_dir)
        config["pto"]["chrome_profile_dir"] = "Default"
        config["pto"]["pto_url"] = "https://picktheodds.app/en/expectedvalue"
        config["pto"]["scraping_interval_seconds"] = 10
        config["pto"]["page_refresh_interval_hours"] = 2.5
        config["pto"]["enable_auto_scraping"] = True
        
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
    
    def export_profile(self, export_path=None):
        """Export current profile to a specified location"""
        profile_path = self.get_profile_path()
        
        if not profile_path or not os.path.exists(profile_path):
            print("❌ No valid profile found to export.")
            return False
        
        if not export_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            export_path = f"pto_profile_export_{timestamp}.zip"
        
        try:
            print(f"📤 Exporting profile to: {export_path}")
            
            with zipfile.ZipFile(export_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(profile_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, profile_path)
                        zipf.write(file_path, arcname)
            
            print(f"✅ Profile exported successfully: {export_path}")
            return True
            
        except Exception as e:
            print(f"❌ Export failed: {e}")
            return False
    
    def import_profile(self, import_path):
        """Import a profile from a specified file"""
        if not os.path.exists(import_path):
            print(f"❌ Import file not found: {import_path}")
            return False
        
        # Get target profile directory
        if self.system == "windows":
            target_dir = self.user_home / "AppData" / "Local" / "PTO_Chrome_Profile"
        elif self.system == "darwin":
            target_dir = self.user_home / "Library" / "Application Support" / "PTO_Chrome_Profile"
        else:
            target_dir = self.user_home / ".config" / "PTO_Chrome_Profile"
        
        try:
            print(f"📥 Importing profile from: {import_path}")
            print(f"📁 Target directory: {target_dir}")
            
            # Remove existing profile if it exists
            if target_dir.exists():
                print("🗑️ Removing existing profile...")
                shutil.rmtree(target_dir)
            
            # Create target directory
            target_dir.mkdir(parents=True, exist_ok=True)
            
            # Extract import
            print("📦 Extracting profile...")
            with zipfile.ZipFile(import_path, 'r') as zipf:
                zipf.extractall(target_dir)
            
            # Update config
            self.update_config(target_dir)
            
            print(f"✅ Profile imported successfully!")
            return True
            
        except Exception as e:
            print(f"❌ Import failed: {e}")
            return False

def main():
    manager = PTOProfileManager()
    
    print("PTO Chrome Profile Manager")
    print("=" * 40)
    print("1. Create backup of current profile")
    print("2. List available backups")
    print("3. Restore backup")
    print("4. Export profile to file")
    print("5. Import profile from file")
    print("6. Exit")
    
    choice = input("\nSelect option (1-6): ").strip()
    
    if choice == "1":
        backup_name = input("Enter backup name (or press Enter for auto): ").strip()
        if not backup_name:
            backup_name = None
        manager.create_backup(backup_name=backup_name)
    
    elif choice == "2":
        backups = manager.list_backups()
        if not backups:
            print("No backups found.")
        else:
            print("\nAvailable backups:")
            print("-" * 60)
            for i, backup in enumerate(backups, 1):
                size_mb = backup.get("backup_size", 0) / (1024 * 1024)
                print(f"{i}. {backup['backup_name']}")
                print(f"   Created: {backup.get('created_at', 'Unknown')}")
                print(f"   System: {backup.get('system', 'Unknown')}")
                print(f"   Size: {size_mb:.1f} MB")
                print()
    
    elif choice == "3":
        backups = manager.list_backups()
        if not backups:
            print("No backups found.")
        else:
            print("\nAvailable backups:")
            for i, backup in enumerate(backups, 1):
                print(f"{i}. {backup['backup_name']}")
            
            try:
                idx = int(input("\nSelect backup number: ")) - 1
                if 0 <= idx < len(backups):
                    manager.restore_backup(backups[idx]['backup_name'])
                else:
                    print("Invalid selection.")
            except ValueError:
                print("Invalid input.")
    
    elif choice == "4":
        export_path = input("Enter export file path (or press Enter for auto): ").strip()
        if not export_path:
            export_path = None
        manager.export_profile(export_path)
    
    elif choice == "5":
        import_path = input("Enter import file path: ").strip()
        if import_path:
            manager.import_profile(import_path)
        else:
            print("No file path provided.")
    
    elif choice == "6":
        print("Goodbye!")
    
    else:
        print("Invalid choice. Please run the script again.")

if __name__ == "__main__":
    main() 