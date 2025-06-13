import sys
from PyQt6.QtWidgets import QApplication
from window import SubdlUploaderWindow

def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    window = SubdlUploaderWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == '__main__':
    main()