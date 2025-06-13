# لقراءة الشرح بالعربية تفضل [README.ar](https://github.com/Abu3safeer/subdl_pyuploader/blob/main/README.ar.md)


# Subdl Uploader (subdl_pyuploader)

A powerful GUI application for easily uploading subtitles to Subdl with advanced features and automated processing.

## Features

### Multi-Tab Interface
- **Upload Tab**: Main interface for managing and uploading subtitles
- **Search Tab**: Search and select TV series from TMDB database
- **Settings Tab**: Configure API keys and default upload preferences

### Series Management
- Advanced TMDB series search with real-time results
- Visual series cards showing:
  - Series poster
  - Title and year
  - Rating and language
  - TMDB ID
  - Series overview
- Automatic series detection from subtitle filenames
- Prevention of mixing subtitles from different series

### File Management
- Drag and drop subtitle files support
- Bulk file selection through file dialog
- Support for .srt, .sub, and .ass subtitle formats
- Recursive folder scanning for subtitle files
- Automatic season and episode detection
- Table view with sortable columns:
  - Season number
  - Episode number
  - Series title
  - Filename
- File reordering with Move Up/Down buttons
- Bulk file deletion

### Upload Features
- Batch upload processing
- Real-time upload progress tracking
- Color-coded status indicators:
  - Yellow: Processing
  - Green: Successfully uploaded
  - Red: Failed
- Pause/Resume upload capability
- Cancel upload functionality
- Upload status monitoring

### Release Name Templates
- Customizable release name templates
- Automatic season/episode number replacement
- Support for both 2 and 3-digit season/episode numbers
- Fallback to original filename if no template

## Setup and Configuration

### Required Settings
1. **API Keys** (Settings Tab):
   - TMDB API Key: Required for series search
   - Subdl API Key: Required for subtitle uploads

2. **Default Upload Settings**:
   - **Language**: Select default subtitle language
   - **Framerate**: Choose from available options:
     - 0 (default)
     - 23.976
     - 23.980
     - 24.000
     - 25.000
     - 29.970
     - 30.000
   - **Default Comment**: Template for upload comments
   - **Release Templates**: Format for release names
     - Use S00E00 as placeholder (e.g., `Show.Name.S00E00.1080p.WEB-DL`)
     - One template per line
     - Supports multiple templates

## Usage Guide

### Basic Workflow

1. **Configure Settings**:
   - Open Settings tab
   - Enter API keys
   - Set default language and framerate
   - Configure default comment
   - Set up release templates

2. **Select TV Series**:
   - Click Search tab
   - Enter series name
   - Select correct series from results
   - Series info will appear in Upload tab

3. **Add Subtitle Files**:
   - Either drag and drop files/folders
   - Or use "Select Files" button
   - Files are automatically processed for:
     - Season/Episode detection
     - Series consistency check
     - Duplicate prevention

4. **Manage Files**:
   - Reorder using Move Up/Down buttons
   - Remove unwanted files using Delete
   - Verify season and episode numbers

5. **Upload Subtitles**:
   - Click "Upload Subtitles"
   - Monitor progress in real-time
   - Use Pause/Resume if needed
   - Cancel upload if required

### Advanced Features

#### Release Name Templates
```
Series.Name.S00E00.1080p.WEB-DL
Series.Name.S00E00.720p.WEB-DL
```
- Supports multiple formats
- Automatically handles high season/episode numbers
- Maintains consistent naming

#### Bulk Processing
- Handles multiple files simultaneously
- Preserves order of uploads
- Shows individual file progress
- Maintains series consistency

#### Error Handling
- Validates all required settings
- Prevents mixed series uploads
- Shows clear error messages
- Allows error recovery

## File Support

### Supported Formats
- .srt (SubRip)
- .sup (Blu-Ray PGS/SUP file)
- .ass (Advanced SubStation Alpha)

### Directory Structure
- Processes nested folders
- Finds all supported subtitles
- Maintains file organization

## Notes

- Ensure stable internet connection for uploads
- Keep API keys secure and valid
- Verify series selection before upload
- Check release templates format
- Monitor upload progress
- Use pause feature for large batches

## Error Recovery

1. **Invalid API Keys**:
   - Check Settings tab
   - Verify keys are correct
   - Save and retry

2. **Upload Failures**:
   - Check file format
   - Verify series selection
   - Confirm internet connection
   - Retry failed uploads

3. **Series Mismatch**:
   - Clear table
   - Re-add correct files
   - Verify series selection
