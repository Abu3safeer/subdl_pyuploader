import json
import os
import requests
from pathlib import Path
from PyQt6.QtGui import QPixmap, QColor
from PyQt6.QtCore import QByteArray, Qt, QThread, pyqtSignal
from pathlib import Path
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QApplication,
                            QPushButton, QDialog, QLineEdit, QFormLayout, QTableWidget,
                            QDialogButtonBox, QLabel, QMessageBox, QTableWidgetItem,
                            QFileDialog, QTabWidget, QListWidget, QListWidgetItem, 
                            QScrollArea, QFrame, QTextEdit, QComboBox, 
                            QSpinBox, QGroupBox, QProgressDialog)  
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QDragEnterEvent, QDropEvent
from guessit import guessit
from subdl_api import SubdlAPI
from tmdb_api import TMDBApi
import logging

class DragDropTable(QTableWidget):
    file_dropped = pyqtSignal(list)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setAcceptDrops(True)
    
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()
            
    def dragMoveEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()
            
    def dropEvent(self, event: QDropEvent) -> None:
        if event.mimeData().hasUrls():
            event.setDropAction(Qt.DropAction.CopyAction)
            files = [url.toLocalFile() for url in event.mimeData().urls()]
            self.file_dropped.emit(files)
            event.accept()
        else:
            event.ignore()

class SubdlUploaderWindow(QMainWindow):
    # Add framerate mapping as class attribute
    FRAMERATE_MAP = {
        "0": 0,      # default
        "23.976": 2, 
        "23.980": 6,
        "24.000": 5,
        "25.000": 3,
        "29.970": 4,
        "30.000": 7
    }

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Subdl Uploader")
                
        # Create main widget and tab widget
        self.tab_widget = QTabWidget()
        self.setCentralWidget(self.tab_widget)
        
        # Create tabs
        self.upload_tab = QWidget()
        self.search_tab = QWidget()
        self.settings_tab = QWidget()
        
        # Setup all tabs first (this creates the UI elements)
        self.setup_settings_tab()  # Move this first
        self.setup_upload_tab()
        self.setup_search_tab()
        
        # Add tabs to widget in desired order
        self.tab_widget.addTab(self.upload_tab, "📤 Upload")
        self.tab_widget.addTab(self.search_tab, "🔍 Search")
        self.tab_widget.addTab(self.settings_tab, "⚙️ Settings")
        
        # Initialize other attributes after UI elements exist
        self.settings = self.initialize_settings()
        self.subdl = SubdlAPI()
        self.added_files = set()
        self.tmdb = TMDBApi(self.settings.get('tmdb_api_key', ''))
        self.image_cache = ImageCache()
        self.selected_series = None
        
        # Set window size and position
        self.resize(1200, 600)
        self.setMinimumWidth(1000)
        self.center_on_screen()

    def center_on_screen(self):
        """Center the window on the screen"""
        # Get the screen geometry
        screen = QApplication.primaryScreen().geometry()
        # Get the window geometry
        window = self.geometry()
        # Calculate the center point
        x = (screen.width() - window.width()) // 2
        y = (screen.height() - window.height()) // 2
        # Move the window
        self.move(x, y)

    def setup_search_tab(self):
        """Setup the search tab UI"""
        layout = QVBoxLayout(self.search_tab)
        
        # Search box setup
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Enter TV series name...")
        self.search_input.returnPressed.connect(self.perform_search)
        
        search_button = QPushButton("🔍 Search")
        search_button.clicked.connect(self.perform_search)
        
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(search_button)
        
        # Results area setup
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.results_widget = QWidget()
        self.results_layout = QVBoxLayout(self.results_widget)
        self.results_layout.setSpacing(10)
        self.results_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # Create and style the no results message
        self.no_results_widget = QWidget()
        no_results_layout = QVBoxLayout(self.no_results_widget)
        
        no_results_icon = QLabel("🔍")
        no_results_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        no_results_icon.setStyleSheet("font-size: 24px;")
        
        self.no_results_label = QLabel("No TV series found.\nTry different keywords.")
        self.no_results_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.no_results_label.setStyleSheet("""
            QLabel {
                color: #666;
                font-size: 14px;
                padding: 20px;
            }
        """)
        
        no_results_layout.addWidget(no_results_icon)
        no_results_layout.addWidget(self.no_results_label)
        no_results_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.no_results_widget.setStyleSheet("""
            QWidget {
                background-color: #f5f5f5;
                border-radius: 8px;
                margin: 20px;
            }
        """)
        self.no_results_widget.hide()
        
        self.results_layout.addWidget(self.no_results_widget)
        scroll_area.setWidget(self.results_widget)
        
        layout.addLayout(search_layout)
        layout.addWidget(scroll_area)

    def perform_search(self):
        """Execute TV series search"""
        query = self.search_input.text().strip()
        if not query:
            return
        
        # Clear previous results
        for i in reversed(range(self.results_layout.count())): 
            widget = self.results_layout.itemAt(i).widget()
            if widget != self.no_results_widget:  # Keep the no results widget
                widget.setParent(None)
    
        # Show loading state
        loading_widget = QLabel("🔄 Searching...", self)
        loading_widget.setStyleSheet("""
            QLabel {
                padding: 20px;
                color: #0078d4;
                font-size: 14px;
                font-weight: bold;
                background: #f0f9ff;
                border-radius: 8px;
                margin: 20px;
            }
        """)
        self.results_layout.insertWidget(0, loading_widget)
        self.no_results_widget.hide()
        
        # Create and start search thread (updated line)
        self.search_thread = SearchThread(self.tmdb, query)
        
        def handle_results(results):
            # Remove loading indicator
            loading_widget.setParent(None)
            
            if not results:
                self.no_results_widget.show()
                return
            
            # Hide no results widget and show results
            self.no_results_widget.hide()
            self.series_cards = []
            for show in results:
                card = SeriesCard(show, self.image_cache)
                card.clicked.connect(self.handle_series_selection)
                self.results_layout.addWidget(card)
                self.series_cards.append(card)
    
        # Connect and start thread
        self.search_thread.finished.connect(handle_results)
        self.search_thread.start()

    def handle_series_selection(self, series_data):
        """Handle series card selection"""
        # Deselect all cards
        for card in self.series_cards:
            card.set_selected(False)
            
        # Find and select the clicked card
        clicked_card = self.sender()
        if isinstance(clicked_card, SeriesCard):
            clicked_card.set_selected(True)
    
        # Store selected series info
        self.selected_series = {
            'tmdb_id': series_data['id'],
            'name': series_data['name']
        }
        
        # Update the selected series label
        self.selected_series_label.setText(
            f"Selected Series: {series_data['name']} (TMDB ID: {series_data['id']})"
        )
        
        self.tab_widget.setCurrentWidget(self.upload_tab)

    def setup_upload_tab(self):
        """Setup the upload tab UI"""
        layout = QVBoxLayout(self.upload_tab)
        
        # Add selected series info
        series_info_layout = QHBoxLayout()
        self.selected_series_label = QLabel("No series selected")
        self.selected_series_label.setStyleSheet("""
            QLabel {
                padding: 8px;
                background-color: #f0f9ff;
                border: 1px solid #0078d4;
                border-radius: 4px;
                color: #0078d4;
                font-weight: bold;
            }
        """)
        series_info_layout.addWidget(self.selected_series_label)
        series_info_layout.addStretch()  # Push upload controls to right
    
        # Create upload controls group
        upload_controls = QVBoxLayout()  # Changed to vertical layout
    
        # Upload button at top
        upload_button = QPushButton("📤 Upload Subtitles", self)
        upload_button.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                background-color: #0078d4;
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #006abc;
            }
        """)
        upload_button.clicked.connect(self.upload_subtitles)
        upload_controls.addWidget(upload_button)
        
        # Status and progress under upload button
        self.upload_status = QLabel("Ready")
        self.upload_progress = QLabel("")
        upload_controls.addWidget(self.upload_status)
        upload_controls.addWidget(self.upload_progress)
        
        # Control buttons in a row under status
        control_buttons = QHBoxLayout()
        self.pause_button = QPushButton("⏸️ Pause")
        self.resume_button = QPushButton("▶️ Resume")
        self.cancel_button = QPushButton("⏹️ Cancel")
        
        # Make buttons visible but disabled by default
        self.pause_button.setEnabled(False)
        self.resume_button.setEnabled(False)
        self.cancel_button.setEnabled(False)
        
        control_buttons.addWidget(self.pause_button)
        control_buttons.addWidget(self.resume_button)
        control_buttons.addWidget(self.cancel_button)
        upload_controls.addLayout(control_buttons)
        
        # Add upload controls to series info layout
        series_info_layout.addLayout(upload_controls)
        layout.addLayout(series_info_layout)
        
        # Add control buttons (Delete, Move Up, Move Down)
        button_layout = QHBoxLayout()
        delete_button = QPushButton("🗑️ Delete", self)
        move_up_button = QPushButton("⬆️ Move Up", self)
        move_down_button = QPushButton("⬇️ Move Down", self)
        
        delete_button.clicked.connect(self.delete_selected_rows)
        move_up_button.clicked.connect(self.move_rows_up)
        move_down_button.clicked.connect(self.move_rows_down)
        
        button_layout.addWidget(delete_button)
        button_layout.addWidget(move_up_button)
        button_layout.addWidget(move_down_button)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
        # Add drag-drop hint and select files button
        files_layout = QHBoxLayout()
        self.drag_label = QLabel("📄 Drag and drop subtitle files here", self)
        select_files_button = QPushButton("📁 Select Files", self)
        select_files_button.clicked.connect(self.add_files)
        
        files_layout.addWidget(self.drag_label)
        files_layout.addWidget(select_files_button)
        files_layout.addStretch()
        
        layout.addLayout(files_layout)
        
        # Create and setup table
        self.table = DragDropTable(0, 4, self)  # Changed from 5 to 4 columns
        self.table.setHorizontalHeaderLabels([
            "Season", "Episode", "Title", "Filename"  # Removed Release Group
        ])
        
        # Set column widths
        self.table.setColumnWidth(0, 70)   # Season
        self.table.setColumnWidth(1, 70)   # Episode
        self.table.setColumnWidth(2, 200)  # Title
        self.table.horizontalHeader().setStretchLastSection(True)  # Filename
        
        # Enable multiple selection
        self.table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        self.table.verticalHeader().setVisible(True)
        self.table.file_dropped.connect(self.process_files)
        
        layout.addWidget(self.table)

    def setup_settings_tab(self):
        """Setup the settings tab UI"""
        layout = QFormLayout(self.settings_tab)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # API Settings Group
        api_group = QGroupBox("API Settings")
        api_layout = QFormLayout(api_group)
        
        self.tmdb_api_key = QLineEdit(self)
        self.subdl_api_key = QLineEdit(self)
        api_layout.addRow("TMDB API Key:", self.tmdb_api_key)
        api_layout.addRow("Subdl API Key:", self.subdl_api_key)
        
        # Upload Settings Group
        upload_group = QGroupBox("Upload Settings")
        upload_layout = QFormLayout(upload_group)
        
        # Language selection
        self.default_language = QComboBox()
        for code, name in sorted(SubdlAPI.LANGUAGES.items(), key=lambda x: x[1]):
            self.default_language.addItem(f"{name} ({code})", code)
        
        # Framerate selection with mapped values
        self.default_framerate = QComboBox()
        framerates = ["0", "23.976", "23.980", "24.000", "25.000", "29.970", "30.000"]
        self.default_framerate.addItems(framerates)
        self.default_framerate.setCurrentText("23.976")  # Default to 23.976
        
        # Default comment
        self.default_comment = QTextEdit()
        self.default_comment.setMaximumHeight(100)
        self.default_comment.setPlaceholderText("Enter default comment for uploads...")
        
        upload_layout.addRow("Default Language:", self.default_language)
        upload_layout.addRow("Default Framerate:", self.default_framerate)
        upload_layout.addRow("Default Comment:", self.default_comment)
        
        # Add releases template group
        releases_group = QGroupBox("Release Names Templates")
        releases_layout = QVBoxLayout(releases_group)
        
        # Add description label
        releases_desc = QLabel(
            "Enter release names (one per line). Use S00E00 as placeholder for season/episode.\n"
            "Example: Group.Name.S00E00.1080p"
        )
        releases_desc.setStyleSheet("color: #666;")
        releases_layout.addWidget(releases_desc)
        
        # Add releases text edit
        self.releases_template = QTextEdit()
        self.releases_template.setPlaceholderText("Enter release names...")
        releases_layout.addWidget(self.releases_template)
        
        # Add to main layout
        layout.addWidget(api_group)
        layout.addWidget(upload_group)
        layout.addWidget(releases_group)
        
        # Add save button with styling
        save_button = QPushButton("💾 Save Settings")
        save_button.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                background-color: #0078d4;
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #006abc;
            }
        """)
        save_button.clicked.connect(self.save_settings)
        layout.addWidget(save_button)

    def save_settings(self):
        """Save settings to file"""
        settings = {
            'tmdb_api_key': self.tmdb_api_key.text(),
            'subdl_api_key': self.subdl_api_key.text(),
            'default_language': self.default_language.currentData(),
            'default_framerate': self.default_framerate.currentText(),
            'default_comment': self.default_comment.toPlainText(),
            'releases_template': self.releases_template.toPlainText().splitlines()
        }
        
        with open('settings.json', 'w') as f:
            json.dump(settings, f, indent=4)
        
        QMessageBox.information(self, "Settings Saved", 
                          "Settings have been saved successfully.")

    def initialize_settings(self):
        """Initialize settings from JSON file"""
        default_settings = {
            'tmdb_api_key': '',
            'subdl_api_key': '',
            'default_language': 'EN',
            'default_framerate': '23.976',
            'default_comment': '',
            'releases_template': []
        }
        
        try:
            with open('settings.json', 'r') as f:
                settings = json.load(f)
                
            # Load settings into UI
            self.tmdb_api_key.setText(settings.get('tmdb_api_key', ''))
            self.subdl_api_key.setText(settings.get('subdl_api_key', ''))
            
            # Set default language
            index = self.default_language.findData(settings.get('default_language'))
            if index >= 0:
                self.default_language.setCurrentIndex(index)
                
            self.default_framerate.setCurrentText(settings.get('default_framerate', '23.976'))
            self.default_comment.setText(settings.get('default_comment', ''))
            self.releases_template.setText('\n'.join(settings.get('releases_template', [])))
            
            return settings
            
        except (FileNotFoundError, json.JSONDecodeError):
            return default_settings

    def delete_selected_rows(self):
        """Delete all selected rows from the table"""
        rows = sorted(set(item.row() for item in self.table.selectedItems()), reverse=True)
        for row in rows:
            file_path = self.table.item(row, 3).data(Qt.ItemDataRole.UserRole)
            self.added_files.remove(file_path)  # Remove from tracking set
            self.table.removeRow(row)
            
        # If table is empty, reset series selection
        if self.table.rowCount() == 0:
            self.clear_series_selection()
            self.added_files.clear()  # Clear the tracking set

    def move_rows_up(self):
        """Move selected rows up one position"""
        rows = sorted(set(item.row() for item in self.table.selectedItems()))
        if not rows or rows[0] <= 0:
            return
            
        for row in rows:
            for col in range(self.table.columnCount()):
                current = self.table.takeItem(row, col)
                above = self.table.takeItem(row - 1, col)
                self.table.setItem(row - 1, col, current)
                self.table.setItem(row, col, above)
            
        # Update selection
        self.table.clearSelection()
        for row in rows:
            for col in range(self.table.columnCount()):
                self.table.item(row - 1, col).setSelected(True)

    def move_rows_down(self):
        """Move selected rows down one position"""
        rows = sorted(set(item.row() for item in self.table.selectedItems()), reverse=True)
        if not rows or rows[-1] >= self.table.rowCount() - 1:
            return
            
        for row in rows:
            for col in range(self.table.columnCount()):
                current = self.table.takeItem(row, col)
                below = self.table.takeItem(row + 1, col)
                self.table.setItem(row + 1, col, current)
                self.table.setItem(row, col, below)
            
        # Update selection
        self.table.clearSelection()
        for row in rows:
            for col in range(self.table.columnCount()):
                self.table.item(row + 1, col).setSelected(True)

    def add_files(self):
        """Open file dialog and add selected subtitle files to the table"""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Subtitle Files",
            "",
            "Subtitle Files (*.srt *.sup *.ass);;All Files (*.*)"  
        )
        self.process_files(files)
    
    def process_files(self, files):
        """Process list of files and check for multiple series"""
        all_files = []
        detected_series = set()
        
        # Update file extensions in directory scanning
        for file_path in files:
            if Path(file_path).is_dir():
                all_files.extend([str(f) for f in Path(file_path).rglob('*') 
                                if f.suffix.lower() in ('.srt', '.sup', '.ass')])  
            elif Path(file_path).suffix.lower() in ('.srt', '.sup', '.ass'):  
                all_files.append(file_path)

        # Create progress dialog
        processing_dialog = QProgressDialog("Processing files...", None, 0, 100, self)
        processing_dialog.setWindowTitle("Processing")
        processing_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        processing_dialog.setMinimumDuration(0)
        processing_dialog.setCancelButton(None)
        processing_dialog.setAutoClose(False)
    
        # Create processing thread with config
        self.processing_thread = FileProcessingThread(all_files)
    
        def handle_file_processed(file_path, file_info):
            """Handle each processed file immediately"""
            # First check if we have files in table already
            if self.table.rowCount() > 0:
                existing_series = self.table.item(0, 2).text().lower()  # Get first series title
                new_series = file_info['title'].lower()
                
                # If new file is from a different series, show warning and stop
                if existing_series != new_series:
                    processing_dialog.close()
                    QMessageBox.warning(
                        self,
                        "Different Series Detected",
                        f"Cannot add files from a different series!\n\n"
                        f"Current series: {existing_series}\n"
                        f"New file series: {new_series}",
                        QMessageBox.StandardButton.Ok
                    )
                    return

            # If we get here, either table is empty or series matches
            if file_path not in self.added_files:
                self.add_file_to_table(file_path, file_info)
                self.added_files.add(file_path)

        def handle_detection_complete(series_set):
            """Handle completion of file processing"""
            processing_dialog.close()
            
            # Auto search for series if not already selected
            if not self.selected_series and self.table.rowCount() > 0:
                first_title = self.table.item(0, 2).text()
                if first_title:
                    self.search_input.setText(first_title)
                    self.tab_widget.setCurrentWidget(self.search_tab)
                    self.perform_search()
        
        # Connect signals
        self.processing_thread.progress.connect(
            lambda text, value: (
                processing_dialog.setLabelText(text),
                processing_dialog.setValue(value)
            )
        )
        self.processing_thread.file_processed.connect(handle_file_processed)
        self.processing_thread.detection_complete.connect(handle_detection_complete)
        
        # Start processing
        self.processing_thread.start()
        processing_dialog.exec()

    def add_processed_file(self, file_path, file_info):
        """Add a processed file to the table"""
        if file_path not in self.added_files:
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            # Add items to row
            self.table.setItem(row, 0, QTableWidgetItem(file_info['season']))
            self.table.setItem(row, 1, QTableWidgetItem(file_info['episode']))
            self.table.setItem(row, 2, QTableWidgetItem(file_info['title']))
            
            # Add filename with full path stored in UserRole
            filename_item = QTableWidgetItem(file_info['filename'])
            filename_item.setData(Qt.ItemDataRole.UserRole, file_path)
            self.table.setItem(row, 3, filename_item)
            
            # Auto-resize rows
            self.table.resizeRowsToContents()

    def upload_file(self, file_path, tmdb_id, season, releases, language_id):
        return self.subdl.upload_subtitle(
            file_path, tmdb_id, season, releases, language_id
        )

    def clear_series_selection(self):
        """Clear the selected series"""
        self.selected_series = None
        self.selected_series_label.setText("No series selected")

    def upload_subtitles(self):
        """Handle subtitle upload process with visual feedback"""
        if not self.selected_series or self.table.rowCount() == 0:
            QMessageBox.warning(self, "Error", "No series selected or no subtitles added!")
            return

        # Validate all required settings
        if not self.default_language.currentData():
            if QMessageBox.question(
                self,
                "Missing Language",
                "No default language selected in settings. Would you like to select one now?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            ) == QMessageBox.StandardButton.Yes:
                self.tab_widget.setCurrentWidget(self.settings_tab)
                return
            return

        if not self.default_framerate.currentText():
            if QMessageBox.question(
                self,
                "Missing Framerate",
                "No default framerate selected in settings. Would you like to set it now?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            ) == QMessageBox.StandardButton.Yes:
                self.tab_widget.setCurrentWidget(self.settings_tab)
                return
            return

        if not self.default_comment.toPlainText().strip():
            reply = QMessageBox.question(
                self,
                "Missing Comment",
                "No default comment set in settings. Would you like to add one now?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.tab_widget.setCurrentWidget(self.settings_tab)
                self.default_comment.setFocus()
                return
            return

        # Update controls state
        self.upload_status.setText("Uploading subtitles...")
        self.upload_progress.setText("0/0 files processed")
        self.pause_button.setEnabled(True)
        self.resume_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        
        # Prepare upload data
        files_data = []
        for row in range(self.table.rowCount()):
            file_path = self.table.item(row, 3).data(Qt.ItemDataRole.UserRole)
            season = self.table.item(row, 0).text()
            episode = self.table.item(row, 1).text()
            
            files_data.append({
                'file_path': file_path,
                'tmdb_id': self.selected_series['tmdb_id'],
                'season': season,
                'releases': self.process_release_templates(season, episode, os.path.basename(file_path)),
                'language': self.default_language.currentData(),
                'comment': self.default_comment.toPlainText(),
                'framerate': self.FRAMERATE_MAP[self.default_framerate.currentText()],
                'episode': episode
            })
    
        # Create and setup upload thread
        self.upload_thread = UploadThread(self.subdl, files_data)
    
        def handle_progress(row, status, color):
            self.upload_progress.setText(f"{row + 1}/{len(files_data)} files processed")
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                if item:
                    item.setBackground(QColor(color))
            filename_item = self.table.item(row, 3)
            if filename_item:
                orig_name = os.path.basename(filename_item.data(Qt.ItemDataRole.UserRole))
                filename_item.setText(f"{orig_name} ({status})")
    
        def handle_finished(success):
            # Reset controls state
            self.upload_status.setText("Ready")
            self.upload_progress.setText("")
            self.pause_button.setEnabled(False)
            self.resume_button.setEnabled(False)
            self.cancel_button.setEnabled(False)
            
            if success:
                QMessageBox.information(self, "Success", "All subtitles uploaded successfully!")
            else:
                QMessageBox.warning(self, "Warning", "Some files failed to upload.")
    
        # Connect signals and buttons
        self.upload_thread.progress.connect(handle_progress)
        self.upload_thread.finished.connect(handle_finished)
        
        self.pause_button.clicked.connect(lambda: (
            self.upload_thread.pause(),
            self.pause_button.setEnabled(False),
            self.resume_button.setEnabled(True)
        ))
        
        self.resume_button.clicked.connect(lambda: (
            self.upload_thread.resume(),
            self.pause_button.setEnabled(True),
            self.resume_button.setEnabled(False)
        ))
        
        self.cancel_button.clicked.connect(self.upload_thread.cancel)
        
        # Start upload
        self.upload_thread.start()

    def add_file_to_table(self, file_path, file_info):
        """Add a subtitle file to the table with parsed information"""
        if file_path not in self.added_files:
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            # Add items to row
            self.table.setItem(row, 0, QTableWidgetItem(file_info['season']))
            self.table.setItem(row, 1, QTableWidgetItem(file_info['episode']))
            self.table.setItem(row, 2, QTableWidgetItem(file_info['title']))
            
            # Add filename with full path stored in UserRole
            filename_item = QTableWidgetItem(file_info['filename'])
            filename_item.setData(Qt.ItemDataRole.UserRole, file_path)
            self.table.setItem(row, 3, filename_item)
            
            # Auto-resize rows
            self.table.resizeRowsToContents()

    def process_release_templates(self, season, episode, filename):
        """Process release templates and replace season/episode patterns"""
        templates = self.releases_template.toPlainText().splitlines()
        processed_releases = []
        
        # Format season and episode numbers with proper padding
        season_digits = 3 if int(season) > 99 else 2
        episode_digits = 3 if int(episode) > 99 else 2
        
        season_str = str(season).zfill(season_digits)
        episode_str = str(episode).zfill(episode_digits)
        
        # Define season/episode patterns to replace
        patterns = [
            'S00E00',                    # Basic pattern
            f'S\\d{{2,3}}E\\d{{2,3}}',  # Handles both 2 and 3 digit formats
        ]
        
        for template in templates:
            if template.strip():
                release = template
                # Replace all patterns with actual season/episode
                for pattern in patterns:
                    import re
                    release = re.sub(pattern, f'S{season_str}E{episode_str}', release)
                processed_releases.append(release)
    
        return processed_releases if processed_releases else [filename]  # fallback to filename if no templates

class SeriesCard(QWidget):
    clicked = pyqtSignal(dict)
    
    def __init__(self, series_data, image_cache, parent=None):
        super().__init__(parent)
        self.series_data = series_data
        self.image_cache = image_cache
        self.is_selected = False
        self.is_hovered = False
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Create card frame
        self.frame = QFrame(self)
        self.update_frame_style()
        frame_layout = QHBoxLayout(self.frame)  # Changed to horizontal layout
        frame_layout.setSpacing(15)
        
        # Left side - Poster
        self.poster_label = QLabel()
        self.poster_label.setFixedSize(100, 150)
        self.poster_label.setStyleSheet("""
            border: 1px solid #ccc;
            border-radius: 5px;
            background-color: #f9f9f9;
        """)
        
        # Load poster image
        if poster_path := self.series_data.get('poster_path'):
            if pixmap := self.image_cache.get_image(poster_path):
                scaled_pixmap = pixmap.scaled(
                    self.poster_label.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.poster_label.setPixmap(scaled_pixmap)
        
        # Right side - Details
        details_widget = QWidget()
        details_layout = QVBoxLayout(details_widget)
        details_layout.setSpacing(8)
        
        # Title and year in one row
        title_layout = QHBoxLayout()
        title = self.series_data.get('name', '')
        year = self.series_data.get('first_air_date', '')[:4]
        title_text = f"{title} ({year})" if year else title
        
        title_label = QLabel(title_text)
        title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        title_label.setWordWrap(True)
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        
        # Info row (rating, language, TMDB ID)
        info_layout = QHBoxLayout()
        rating = self.series_data.get('vote_average', 0)
        rating_label = QLabel(f"⭐ {rating:.1f}")
        language = self.series_data.get('original_language', '').upper()
        language_label = QLabel(f"🌐 {language}")
        tmdb_id = self.series_data.get('id', '')
        tmdb_label = QLabel(f"📺 TMDB: {tmdb_id}")
        
        info_layout.addWidget(rating_label)
        info_layout.addWidget(language_label)
        info_layout.addWidget(tmdb_label)
        info_layout.addStretch()
        
        # Overview
        overview = self.series_data.get('overview', '')
        overview_label = QLabel(overview)
        overview_label.setWordWrap(True)
        overview_label.setStyleSheet("color: #666;")
        
        # Add all to details layout
        details_layout.addLayout(title_layout)
        details_layout.addLayout(info_layout)
        details_layout.addWidget(overview_label)
        details_layout.addStretch()
        
        # Add to main frame layout
        frame_layout.addWidget(self.poster_label)
        frame_layout.addWidget(details_widget, 1)  # Stretch factor 1
        
        layout.addWidget(self.frame)
        
        # Make widget clickable
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.frame.mousePressEvent = self.handle_click

    def handle_click(self, event):
        """Handle card click event"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.series_data)

    def update_frame_style(self):
        """Update the frame style based on selection and hover states"""
        if self.is_selected:
            self.frame.setStyleSheet("""
                QFrame {
                    border: 2px solid #0078d4;
                    border-radius: 5px;
                    background-color: #e6f7ff;
                }
            """)
        elif self.is_hovered:
            self.frame.setStyleSheet("""
                QFrame {
                    border: 1px solid #0078d4;
                    border-radius: 5px;
                    background-color: #f0f9ff;
                }
            """)
        else:
            self.frame.setStyleSheet("""
                QFrame {
                    border: 1px solid #ccc;
                    border-radius: 5px;
                    background-color: #f9f9f9;
                }
            """)

    def enterEvent(self, event):
        """Handle mouse enter event"""
        self.is_hovered = True
        self.update_frame_style()
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Handle mouse leave event"""
        self.is_hovered = False
        self.update_frame_style()
        super().leaveEvent(event)

    def set_selected(self, selected):
        """Set the selection state of the card"""
        self.is_selected = selected
        self.update_frame_style()

    def load_poster(self, poster_path):
        """Load and set the poster image"""
        if poster_path:
            # Use cached image if available
            cached_image = self.image_cache.get_image(poster_path)
            if cached_image:
                self.poster_label.setPixmap(cached_image)
            else:
                # Download and cache the image
                self.download_poster(poster_path)
        else:
            self.poster_label.clear()

    def download_poster(self, poster_path):
        """Download the poster image and cache it"""
        def on_success(image_data):
            # Cache the downloaded image
            self.image_cache.cache_image(poster_path, image_data)
            # Set the pixmap from the downloaded data
            self.poster_label.setPixmap(image_data)
        
        def on_error():
            self.poster_label.clear()
        
        # Start asynchronous download
        self.image_cache.download_image(poster_path, on_success, on_error)

    def set_series_data(self, series_data):
        """Set the series data and update the UI"""
        self.series_data = series_data
        self.title_label.setText(series_data.get('name', ''))
        self.release_label.setText(f"First Aired: {series_data.get('first_air_date', '')}")
        self.language_label.setText(f"Language: {series_data.get('original_language', '').upper()}")
        
        # Load the poster image
        poster_path = series_data.get('poster_path')
        self.load_poster(poster_path)

class ImageCache:
    def __init__(self):
        self.cache_dir = Path(__file__).parent / 'posters'
        self.cache_dir.mkdir(exist_ok=True)
        self.base_url = "https://image.tmdb.org/t/p/w342"
        
    def get_image(self, poster_path):
        """Get image from cache or return None"""
        if not poster_path:
            return None
            
        cache_path = self.cache_dir / f"{poster_path.lstrip('/').replace('/', '_')}"
        
        # Check cache first
        if cache_path.exists():
            pixmap = QPixmap(str(cache_path))
            return pixmap if not pixmap.isNull() else None
            
        # Download if not in cache
        try:
            url = f"{self.base_url}{poster_path}"
            response = requests.get(url)
            response.raise_for_status()
            
            # Save to cache
            with open(cache_path, 'wb') as f:
                f.write(response.content)
            
            # Create pixmap
            pixmap = QPixmap()
            pixmap.loadFromData(QByteArray(response.content))
            return pixmap if not pixmap.isNull() else None
            
        except Exception as e:
            print(f"Error downloading image: {e}")
            return None

class LanguageSelector(QDialog):
    # Language flags mapping
    FLAGS = {
        'AR': '🟩',  # Green flag for Arabic
        'BR_PT': '🇧🇷',
        'DA': '🇩🇰',
        'NL': '🇳🇱',
        'EN': '🇬🇧',
        'FA': '🇮🇷',
        'FI': '🇫🇮',
        'FR': '🇫🇷',
        'ID': '🇮🇩',
        'IT': '🇮🇹',
        'NO': '🇳🇴',
        'RO': '🇷🇴',
        'ES': '🇪🇸',
        'SV': '🇸🇪',
        'VI': '🇻🇳',
        'SQ': '🇦🇱',
        'AZ': '🇦🇿',
        'BE': '🇧🇾',
        'BN': '🇧🇩',
        'ZH_BG': '🇨🇳',
        'BS': '🇧🇦',
        'BG': '🇧🇬',
        'BG_EN': '🇧🇬',
        'MY': '🇲🇲',
        'CA': '🏳️',
        'ZH': '🇨🇳',
        'HR': '🇭🇷',
        'CS': '🇨🇿',
        'NL_EN': '🇳🇱',
        'EN_DE': '🇬🇧',
        'EO': '🏳️',
        'ET': '🇪🇪',
        'KA': '🇬🇪',
        'DE': '🇩🇪',
        'EL': '🇬🇷',
        'KL': '🇬🇱',
        'HE': '🇮🇱',
        'HI': '🇮🇳',
        'HU': '🇭🇺',
        'HU_EN': '🇭🇺',
        'IS': '🇮🇸',
        'JA': '🇯🇵',
        'KO': '🇰🇷',
        'KU': '🏳️',
        'LV': '🇱🇻',
        'LT': '🇱🇹',
        'MK': '🇲🇰',
        'MS': '🇲🇾',
        'ML': '🇮🇳',
        'MNI': '🇮🇳',
        'PL': '🇵🇱',
        'PT': '🇵🇹',
        'RU': '🇷🇺',
        'SR': '🇷🇸',
        'SI': '🇱🇰',
        'SK': '🇸🇰',
        'SL': '🇸🇮',
        'TL': '🇵🇭',
        'TA': '🇮🇳',
        'TE': '🇮🇳',
        'TH': '🇹🇭',
        'TR': '🇹🇷',
        'UK': '🇺🇦',
        'UR': '🇵🇰'
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Subtitle Language")
        self.setWindowIcon(parent.windowIcon())
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Add title label
        title_label = QLabel("Select Language for Upload")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #0078d4;
                padding: 5px;
            }
        """)
        layout.addWidget(title_label)
        
        # Add search box
        search_layout = QHBoxLayout()
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Type to search languages...")
        self.search_box.textChanged.connect(self.filter_languages)
        self.search_box.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                border: 1px solid #ccc;
                border-radius: 4px;
                font-size: 13px;
            }
        """)
        search_layout.addWidget(self.search_box)
        layout.addLayout(search_layout)
        
        # Add language list
        self.language_list = QListWidget()
        self.language_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 5px;
            }
            QListWidget::item {
                padding: 8px;
                border-radius: 4px;
            }
            QListWidget::item:selected {
                background-color: #e3f2fd;
                color: #0078d4;
                border: 1px solid #0078d4;
            }
            QListWidget::item:hover {
                background-color: #f0f9ff;
            }
        """)
        
        # Add languages to list
        for code, name in sorted(SubdlAPI.LANGUAGES.items(), key=lambda x: x[1]):
            item = QListWidgetItem(f"{name} ({code})")
            item.setData(Qt.ItemDataRole.UserRole, code)
            self.language_list.addItem(item)
        
        # Double click to select
        self.language_list.itemDoubleClicked.connect(self.accept)
        layout.addWidget(self.language_list)
        
        # Add buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.setMinimumWidth(400)
        self.setMinimumHeight(500)

    def filter_languages(self, text):
        """Filter language list based on search text"""
        search = text.lower()
        for i in range(self.language_list.count()):
            item = self.language_list.item(i)
            item.setHidden(search not in item.text().lower())
    
    def get_selected_language(self):
        """Return selected language code"""
        if selected := self.language_list.currentItem():
            return selected.data(Qt.ItemDataRole.UserRole)
        return None

class UploadOptionsDialog(QDialog):
    def __init__(self, filename, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Upload Options")
        self.filename = filename
        self.setup_ui()
        
    def setup_ui(self):
        layout = QFormLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)

        # Comment field
        self.comment = QTextEdit()
        self.comment.setPlaceholderText("Enter your comment here...")
        self.comment.setMaximumHeight(100)
        layout.addRow("Comment:", self.comment)

        # Framerate combo
        self.framerate = QComboBox()
        framerates = ["0", "23.976", "23.980", "24.000", "25.000", "29.970", "30.000"]
        self.framerate.addItems(framerates)
        self.framerate.setCurrentText("23.976")  # Default
        layout.addRow("Framerate:", self.framerate)

        # Episode range
        episode_layout = QHBoxLayout()
        self.episode_from = QSpinBox()
        self.episode_to = QSpinBox()
        self.episode_from.setRange(0, 999)
        self.episode_to.setRange(0, 999)
        self.episode_from.setSpecialValueText("None")  # Shows "None" when value is 0
        self.episode_to.setSpecialValueText("None")
        episode_layout.addWidget(self.episode_from)
        episode_layout.addWidget(QLabel("to"))
        episode_layout.addWidget(self.episode_to)
        layout.addRow("Episode Range:", episode_layout)

        # Release name (read-only)
        self.release = QLineEdit(self.filename)
        self.release.setReadOnly(True)
        layout.addRow("Release:", self.release)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_data(self):
        return {
            'comment': self.comment.toPlainText(),
            'framerate': self.framerate.currentText(),
            'episode_from': self.episode_from.value() or None,
            'episode_to': self.episode_to.value() or None,
            'release': self.filename
        }

class FileProcessingThread(QThread):
    progress = pyqtSignal(str, int)
    file_processed = pyqtSignal(str, dict)
    detection_complete = pyqtSignal(set)
    
    def __init__(self, files): 
        super().__init__()
        self.files = files
    
    def process_single_file(self, file_path):
        """Process a single file and return its info"""
        filename = os.path.basename(file_path)
        try:
            # Use stored config file
            guess = guessit(filename)
            if title := guess.get('title'):
                file_info = {
                    'season': str(guess.get('season', '')),
                    'episode': str(guess.get('episode', '')),
                    'title': title,
                    'filename': filename
                }
                return title.lower(), file_info
        except Exception as e:
            logging.error(f"Error processing file {filename}: {e}")
        return None, None
        
    def run(self):
        detected_series = set()
        total = len(self.files)
        
        # Process files one by one
        for index, file_path in enumerate(self.files):
            progress = int((index/total) * 100)
            self.progress.emit(f"Processing: {os.path.basename(file_path)}", progress)
            
            series, file_info = self.process_single_file(file_path)
            if series and file_info:
                detected_series.add(series)
                self.file_processed.emit(file_path, file_info)
            
            # Small delay to keep UI responsive
            QThread.msleep(10)
        
        # Emit final series detection results
        self.detection_complete.emit(detected_series)

class UploadThread(QThread):
    progress = pyqtSignal(int, str, str)  # (row, status, color)
    finished = pyqtSignal(bool)  # True if all successful
    
    def __init__(self, subdl, files_data, parent=None):
        super().__init__(parent)
        self.subdl = subdl
        self.files_data = files_data
        self.is_paused = False
        self.is_cancelled = False
        
    def run(self):
        success = True
        for row, data in enumerate(self.files_data):
            # Check if cancelled
            if self.is_cancelled:
                break
                
            # Handle pause
            while self.is_paused and not self.is_cancelled:
                QThread.msleep(100)
            
            # Emit progress - Processing
            self.progress.emit(row, "Processing...", "#FFFDE7")
            
            try:
                # Upload subtitle
                upload_success = self.subdl.upload_subtitle(
                    subtitle_file=data['file_path'],
                    tmdb_id=data['tmdb_id'],
                    season=data['season'],
                    releases=data['releases'],
                    language_id=data['language'],
                    comment=data['comment'],
                    framerate=data['framerate'],
                    episode_from=data['episode'],
                    episode_to=data['episode']
                )
                
                if upload_success:
                    self.progress.emit(row, "Completed ✓", "#E8F5E9")
                else:
                    self.progress.emit(row, "Failed ✗", "#FFEBEE")
                    success = False
                    break
                    
            except Exception as e:
                self.progress.emit(row, f"Error: {str(e)}", "#FFEBEE")
                success = False
                break
        
        self.finished.emit(success)
    
    def pause(self):
        self.is_paused = True
    
    def resume(self):
        self.is_paused = False
    
    def cancel(self):
        self.is_cancelled = True

class SearchThread(QThread):
        finished = pyqtSignal(list)  # Signal to emit search results

        def __init__(self, tmdb_api, query):
            super().__init__()
            self.tmdb_api = tmdb_api
            self.query = query

        def run(self):
            results = self.tmdb_api.search_tv_series(self.query)
            self.finished.emit(results)