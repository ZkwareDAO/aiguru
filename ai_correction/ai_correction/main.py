import streamlit as st
import os
import json
import hashlib
from datetime import datetime
import time
import logging
from functions.ai_recognition import ocr_space_file  # Import directly

def setup_logger(log_dir="logs"):
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    log_file = os.path.join(log_dir, "app_debug.log")
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] %(levelname)s @ %(module)s: %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )

# Initialize logger
setup_logger()
logging.info("Starting")

# Configuration
UPLOAD_DIR = "user_uploads"
DATA_FILE = "user_data.json"
TEST_ACCOUNTS = {
    "test_user_1": "password1",
    "test_user_2": "password2"
}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# Initialize storage structure
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump({}, f)

def read_user_data():
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def write_user_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

def migrate_old_data(user_data):
    """Migrate old data structure to new format (only if needed)"""
    if user_data.get('migrated'):
        return user_data

    for user in list(user_data.keys()):
        if isinstance(user_data[user], list):
            user_data[user] = {
                "password": "",  # Empty, force user to change
                "records": user_data[user],
                "migrated": True
            }
    user_data['migrated'] = True  # Mark the entire data as migrated
    return user_data

def account_management():
    """Sidebar account management"""
    with st.sidebar.expander("🔑 Account Management", expanded=True):
        st.subheader("User Information")
        st.write(f"Current User: {st.session_state.current_user}")

        with st.form("Change Password"):
            new_password = st.text_input("New Password", type="password")
            if st.form_submit_button("Update Password"):
                if len(new_password) < 8:
                    st.error("Password must be at least 8 characters long.")
                else:
                    user_data = read_user_data()
                    user_data[st.session_state.current_user]['password'] = new_password
                    write_user_data(user_data)
                    st.success("Password updated successfully.")

def history_panel():
    """Sidebar history query"""
    with st.sidebar.expander("🕒 History", expanded=True):
        user_data = read_user_data()
        user_records = user_data.get(st.session_state.current_user, {}).get('records', [])

        if user_records:
            st.subheader("Recent Uploads")
            num_records = st.slider("Number of records to display", 10, len(user_records), 10)
            for record in user_records[-num_records:]:
                st.caption(f"{record['filename']}")
                st.markdown(f"🗓️ {record['upload_time']}  📏 {record['file_size']}KB")
                st.progress(float(record.get('progress', 0)))
        else:
            st.info("No history found.")

def process_file_ocr(file_path, record, user_data):
    """OCR Processing (Now synchronous)"""
    try:
        # Update record status
        record["processing_result"] = "Processing..."
        record["progress"] = 0.1
        write_user_data(user_data)
        logging.info("Before OCR")
        result = ocr_space_file(file_path)  # Call OCR function directly
        logging.info("OCR Complete")

        # Update record with results
        record["processing_result"] = "Completed"
        record["ocr_result"] = result
        record["progress"] = 1.0
        write_user_data(user_data)
        st.rerun() # Update UI

    except Exception as e:
        logging.error(f"OCR processing error: {e}")
        record["processing_result"] = f"Error: {str(e)}"
        record["progress"] = 0.0
        write_user_data(user_data)
        st.rerun() #Update UI


def file_management_page():
    """File upload management page"""
    st.title("📁 File Management Center")

    user_dir = os.path.join(UPLOAD_DIR, st.session_state.current_user)
    os.makedirs(user_dir, exist_ok=True)

    with st.expander("➕ Upload New File", expanded=True):
        uploaded_file = st.file_uploader(
            label="Select a file to upload (Max size: 10MB)",
            type=["pdf", "docx", "xlsx", "jpg", "png"],
            key="main_uploader"
        )

        if uploaded_file and uploaded_file.size <= MAX_FILE_SIZE:
            file_content = uploaded_file.getbuffer()
            file_hash = hashlib.md5(file_content).hexdigest()  # Calculate file hash
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            filename = f"{timestamp}_{uploaded_file.name}"
            save_path = os.path.join(user_dir, filename)

            user_data = read_user_data()
            user_entry = user_data.setdefault(st.session_state.current_user, {
                "password": "",  # Initial password empty
                "records": []
            })

            # Check if the file already exists (based on hash)
            for record in user_entry['records']:
                if record.get("file_hash") == file_hash:
                    st.warning("This file has already been uploaded.")
                    return

            with open(save_path, "wb") as f:
                f.write(file_content)

            logging.info("File saved")
            # Add new record
            new_record = {
                "filename": filename,
                "upload_time": timestamp,
                "file_size": uploaded_file.size // 1024,
                "file_hash": file_hash,  # Save file hash
                "processing_result": "Pending",
                "progress": 0.0,
                "ocr_result": ""  # To store OCR results
            }
            user_entry['records'].append(new_record)
            write_user_data(user_data)

            # Start OCR task (Now synchronous)
            logging.info("Starting OCR processing")
            process_file_ocr(save_path, new_record, user_data)


        elif uploaded_file:
            st.error("File size exceeds the limit (10MB).")

    st.subheader("File List")
    user_data = read_user_data()
    user_records = user_data.get(st.session_state.current_user, {}).get('records', [])

    # Use a dictionary to track delete confirmations
    if 'delete_confirmations' not in st.session_state:
        st.session_state.delete_confirmations = {}

    for record in user_records:
        cols = st.columns([5, 2, 2, 2, 2])
        cols[0].write(record["filename"])
        cols[1].metric("Size", f"{record['file_size']}KB")
        cols[2].write(record["upload_time"])
        cols[3].write(record["processing_result"])
        cols[4].progress(float(record["progress"]))

        if cols[4].button("Delete", key=f"del_{record['filename']}"):
            st.session_state.delete_confirmations[record['filename']] = True  # Set confirmation flag
            st.rerun()

        # Check if confirmation is needed
        if st.session_state.delete_confirmations.get(record['filename']):
            if cols[4].button("Confirm Delete", key=f"confirm_{record['filename']}"):
                file_path = os.path.join(user_dir, record["filename"])
                if os.path.exists(file_path):
                    os.remove(file_path)
                updated_records = [r for r in user_records if r['filename'] != record['filename']]
                user_data[st.session_state.current_user]['records'] = updated_records
                write_user_data(user_data)
                st.session_state.delete_confirmations[record['filename']] = False  # Reset flag
                st.rerun()



def download_page():
    st.title("📥 Download Recognized Files")
    user_data = read_user_data()
    user_records = user_data.get(st.session_state.current_user, {}).get('records', [])

    # Filter records that have completed OCR
    completed_records = [record for record in user_records if record["processing_result"] == "Completed"]

    if completed_records:
        st.subheader("Completed OCR Files")
        for record in completed_records:
            cols = st.columns([5, 2, 2, 2])
            cols[0].write(record["filename"])
            cols[1].metric("Size", f"{record['file_size']}KB")
            cols[2].write(record["upload_time"])

            # Provide download button for OCR result
            ocr_result = record["ocr_result"]
            cols[3].download_button(
                label="Download OCR Result",
                data=ocr_result,
                file_name=f"{record['filename']}_ocr_result.txt",
                mime="text/plain"
            )
    else:
        st.info("No completed OCR files found.")

def main():
    """Main function for Streamlit interaction"""
    if 'logged_in' not in st.session_state:
        st.session_state.update({
            'logged_in': False,
            'current_user': None,
            'page': 'dashboard'
        })

    if not st.session_state.logged_in:
        st.title("🔐 User Login")
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            if st.form_submit_button("Login"):
                user_data = read_user_data()
                user_data = migrate_old_data(user_data)

                if username in TEST_ACCOUNTS:
                    if username not in user_data:
                        user_data[username] = {
                            "password": TEST_ACCOUNTS[username],
                            "records": []
                        }
                        write_user_data(user_data)

                    stored_password = user_data[username]['password']
                    if stored_password == password:
                        st.session_state.logged_in = True
                        st.session_state.current_user = username
                        st.rerun()
                        return
                    else:
                        st.error("Incorrect password.")
                else:
                    st.error("Only test accounts are allowed to log in.")
        return  # If not logged in, return

    st.title(f"Welcome back, {st.session_state.current_user}!")

    with st.sidebar:
        account_management()
        history_panel()

        st.divider()
        page_options = {
            "🏠 Dashboard": "dashboard",
            "📤 File Management": "file_mgmt",
            "📊 Data Analysis": "analytics",
            "📥 Download Recognized Files": "download"
        }
        selected = st.radio("Navigation Menu", page_options.keys())
        st.session_state.page = page_options[selected]

        st.divider()
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.session_state.current_user = None
            st.rerun()
            return

    if st.session_state.page == "dashboard":
        st.write("## System Dashboard")
    elif st.session_state.page == "file_mgmt":
        file_management_page()  # file_management_page now includes synchronous calls
    elif st.session_state.page == "analytics":
        st.write("## Data Analysis Center")
    elif st.session_state.page == "download":
        download_page()

if __name__ == "__main__":
    main()

