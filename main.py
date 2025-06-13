import sys
import os
import logging
import traceback
from datetime import datetime
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import QT_VERSION_STR
from window import SubdlUploaderWindow
import json

def setup_logging():
    """Setup logging configuration"""
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    log_file = os.path.join(log_dir, f"subdl_uploader_error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    
    try:
        with open('settings.json', 'r') as f:
            settings = json.load(f)
            debug_mode = settings.get('debug_mode', False)
    except:
        debug_mode = False
    
    logging.basicConfig(
        level=logging.DEBUG if debug_mode else logging.ERROR,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler() if debug_mode else logging.NullHandler()
        ]
    )
    return log_file

def show_error_dialog(error_msg, log_file):
    """Show error dialog with logging information"""
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Icon.Critical)
    msg.setWindowTitle("Error")
    msg.setText("An unexpected error occurred!")
    msg.setInformativeText(str(error_msg))
    msg.setDetailedText(f"Please report this issue on GitHub with the contents of:\n{log_file}")
    msg.exec()

def exception_handler(exc_type, exc_value, exc_traceback):
    """Handle uncaught exceptions"""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    
    error_msg = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    logging.error(f"Uncaught exception:\n{error_msg}")

def main():
    # Setup logging
    log_file = setup_logging()
    logging.info("Starting Subdl Uploader")
    
    # Set global exception handler
    sys.excepthook = exception_handler
    
    try:
        app = QApplication(sys.argv)
        app.setStyle('Fusion')
        
        window = SubdlUploaderWindow()
        window.show()
        
        # Log application start with correct Qt version
        logging.info(f"Application started with Python {sys.version}")
        logging.info(f"Qt Version: {QT_VERSION_STR}")
        logging.info(f"Operating System: {os.name}")
        
        exit_code = app.exec()
        logging.info("Application closed normally")
        sys.exit(exit_code)
        
    except Exception as e:
        logging.error("Fatal error:", exc_info=True)
        show_error_dialog(str(e), log_file)
        sys.exit(1)

if __name__ == '__main__':
    main()