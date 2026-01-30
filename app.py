import streamlit as st
import re
from firebase_admin import credentials, firestore, initialize_app
import firebase_admin
from typing import Dict, Optional, Tuple
import json

# ============================================================================
# FIREBASE INITIALIZATION
# ============================================================================

@st.cache_resource
def init_firebase():
    """
    Initialize Firebase Admin SDK using credentials from Streamlit secrets.
    Cached to prevent multiple initializations.
    """
    try:
        # Check if Firebase is already initialized
        firebase_admin.get_app()
    except ValueError:
        # Firebase not initialized, so initialize it
        cred_dict = {
            "type": st.secrets["firebase"]["type"],
            "project_id": st.secrets["firebase"]["project_id"],
            "private_key_id": st.secrets["firebase"]["private_key_id"],
            "private_key": st.secrets["firebase"]["private_key"],
            "client_email": st.secrets["firebase"]["client_email"],
            "client_id": st.secrets["firebase"]["client_id"],
            "auth_uri": st.secrets["firebase"]["auth_uri"],
            "token_uri": st.secrets["firebase"]["token_uri"],
            "auth_provider_x509_cert_url": st.secrets["firebase"]["auth_provider_x509_cert_url"],
            "client_x509_cert_url": st.secrets["firebase"]["client_x509_cert_url"]
        }
        cred = credentials.Certificate(cred_dict)
        initialize_app(cred)
    
    return firestore.client()

# ============================================================================
# VALIDATION FUNCTIONS (REGEX-BASED)
# ============================================================================

def validate_email(email: str) -> Tuple[bool, str]:
    """
    Validate email format using regex.
    Returns: (is_valid, error_message)
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not email:
        return False, "Email ID is required"
    if not re.match(pattern, email):
        return False, "Invalid email format (e.g., user@example.com)"
    return True, ""

def validate_enrollment(enrollment: str) -> Tuple[bool, str]:
    """
    Validate enrollment number: exactly 12 digits.
    Returns: (is_valid, error_message)
    """
    pattern = r'^\d{12}$'
    if not enrollment:
        return False, "Enrollment Number is required"
    if not re.match(pattern, enrollment):
        return False, "Enrollment Number must be exactly 12 digits"
    return True, ""

def validate_name(name: str) -> Tuple[bool, str]:
    """
    Validate full name: text only, spaces allowed, no special characters.
    Returns: (is_valid, error_message)
    """
    pattern = r'^[a-zA-Z\s]+$'
    if not name:
        return False, "Full Name is required"
    if not re.match(pattern, name.strip()):
        return False, "Full Name can only contain letters and spaces"
    return True, ""

def validate_contact(contact: str) -> Tuple[bool, str]:
    """
    Validate contact number: exactly 10 digits (Indian standard).
    Returns: (is_valid, error_message)
    """
    pattern = r'^\d{10}$'
    if not contact:
        return False, "Contact Number is required"
    if not re.match(pattern, contact):
        return False, "Contact Number must be exactly 10 digits"
    return True, ""

def validate_project_name(project_name: str) -> Tuple[bool, str]:
    """
    Validate project name: minimum 3 characters.
    Returns: (is_valid, error_message)
    """
    if not project_name:
        return False, "Project Name is required"
    if len(project_name.strip()) < 3:
        return False, "Project Name must be at least 3 characters"
    return True, ""

def validate_url(url: str) -> Tuple[bool, str]:
    """
    Validate URL: must start with http:// or https://
    Returns: (is_valid, error_message)
    """
    pattern = r'^https?://[^\s/$.?#].[^\s]*$'
    if not url:
        return False, "Source URL is required"
    if not re.match(pattern, url, re.IGNORECASE):
        return False, "URL must start with http:// or https://"
    return True, ""

# ============================================================================
# DATABASE OPERATIONS
# ============================================================================

def check_duplicate_fields(db, data: Dict) -> Tuple[bool, str]:
    """
    Check if any of the unique fields already exist in the database.
    Optimized to minimize database reads by checking all fields in one pass.
    
    Returns: (has_duplicate, error_message)
    """
    collection_ref = db.collection('project_submissions')
    
    # Fields to check for uniqueness
    unique_fields = {
        'email': data['email'],
        'enrollment_number': data['enrollment_number'],
        'contact_number': data['contact_number'],
        'project_name': data['project_name'],
        'source_url': data['source_url']
    }
    
    # Check each field for duplicates
    for field_name, field_value in unique_fields.items():
        query = collection_ref.where(field_name, '==', field_value).limit(1)
        docs = query.stream()
        
        # If any document exists, we have a duplicate
        for doc in docs:
            # Map database field names to user-friendly names
            field_display_names = {
                'email': 'Email ID',
                'enrollment_number': 'Enrollment Number',
                'contact_number': 'Contact Number',
                'project_name': 'Project Name',
                'source_url': 'Source URL'
            }
            return True, f"Error: This {field_display_names[field_name]} is already taken."
    
    return False, ""

def save_submission(db, data: Dict) -> bool:
    """
    Save the validated submission to Firestore.
    Returns: True if successful, False otherwise
    """
    try:
        collection_ref = db.collection('project_submissions')
        collection_ref.add(data)
        return True
    except Exception as e:
        st.error(f"Database error: {str(e)}")
        return False

# ============================================================================
# CUSTOM CSS FOR UI POLISH
# ============================================================================

def apply_custom_css():
    """
    Apply custom CSS to hide Streamlit branding and improve UI.
    """
    st.markdown("""
        <style>
        /* Hide Streamlit hamburger menu */
        #MainMenu {visibility: hidden;}
        
        /* Hide Streamlit footer */
        footer {visibility: hidden;}
        
        /* Hide "Deploy" button */
        .stDeployButton {visibility: hidden;}
        
        /* Custom styling for better UX */
        .stTextInput > label, .stTextArea > label {
            font-weight: 600;
            color: #1f1f1f;
        }
        
        /* Submit button styling */
        .stButton > button {
            width: 100%;
            background-color: #0066cc;
            color: white;
            font-weight: 600;
            border-radius: 5px;
            padding: 0.5rem 1rem;
            border: none;
        }
        
        .stButton > button:hover {
            background-color: #0052a3;
        }
        
        /* Warning messages */
        .element-container .stAlert {
            padding: 0.5rem;
            margin-bottom: 0.5rem;
        }
        </style>
    """, unsafe_allow_html=True)

# ============================================================================
# MAIN APPLICATION
# ============================================================================

def main():
    # Apply custom CSS
    apply_custom_css()
    
    # Initialize Firebase
    db = init_firebase()
    
    # Page configuration
    st.title("🎓 DAV Project Submission Portal")
    st.markdown("### Submit your project details below")
    st.markdown("---")
    
    # Initialize session state for form validation
    if 'form_valid' not in st.session_state:
        st.session_state.form_valid = False
    
    # Form inputs with real-time validation
    with st.form("project_submission_form", clear_on_submit=True):
        st.subheader("Personal Information")
        
        # Email ID - always use text input for deployed apps
        email = st.text_input(
            "Email ID",
            placeholder="user@example.com",
            help="Enter your valid email address"
        )
        
        # Enrollment Number
        enrollment = st.text_input(
            "Enrollment Number",
            placeholder="123456789012",
            max_chars=12,
            help="Enter exactly 12 digits"
        )
        
        # Full Name
        full_name = st.text_input(
            "Full Name",
            placeholder="Full Name",
            help="Letters and spaces only"
        )
        
        # Contact Number
        contact = st.text_input(
            "Contact Number",
            placeholder="9876543210",
            max_chars=10,
            help="Enter exactly 10 digits"
        )
        
        st.markdown("---")
        st.subheader("Project Details")
        
        # Project Name
        project_name = st.text_input(
            "Project Name",
            placeholder="My Awesome Project",
            help="Minimum 3 characters"
        )
        
        # Source URL
        source_url = st.text_input(
            "Source URL",
            placeholder="https://github.com/username/project",
            help="Must start with http:// or https://"
        )
        
        st.markdown("---")
        
        # Submit button
        submitted = st.form_submit_button("🚀 Submit Project", use_container_width=True)
        
        if submitted:
            # Validation checks
            validations = [
                validate_email(email),
                validate_enrollment(enrollment),
                validate_name(full_name),
                validate_contact(contact),
                validate_project_name(project_name),
                validate_url(source_url)
            ]
            
            # Check if all validations pass
            all_valid = all(valid for valid, _ in validations)
            
            if not all_valid:
                # Display all validation errors
                st.error("⚠️ Please fix the following errors:")
                for valid, error_msg in validations:
                    if not valid and error_msg:
                        st.warning(f"• {error_msg}")
            else:
                # All validations passed, prepare data
                submission_data = {
                    'email': email.strip().lower(),
                    'enrollment_number': enrollment.strip(),
                    'full_name': full_name.strip(),
                    'contact_number': contact.strip(),
                    'project_name': project_name.strip(),
                    'source_url': source_url.strip()
                }
                
                # Check for duplicates
                with st.spinner("Checking for duplicates..."):
                    has_duplicate, duplicate_msg = check_duplicate_fields(db, submission_data)
                
                if has_duplicate:
                    st.error(duplicate_msg)
                    st.info("💡 Please use unique values for all fields.")
                else:
                    # Save to database
                    with st.spinner("Submitting your project..."):
                        success = save_submission(db, submission_data)
                    
                    if success:
                        st.success("✅ Project submitted successfully!")
                        st.balloons()
                        st.info("Your submission has been recorded. Thank you!")
                    else:
                        st.error("❌ Submission failed. Please try again later.")
    
    # Display validation hints outside the form
    with st.expander("ℹ️ Validation Requirements", expanded=False):
        st.markdown("""
        - **Email ID**: Valid email format (e.g., user@example.com)
        - **Enrollment Number**: Exactly 12 digits
        - **Full Name**: Letters and spaces only, no special characters
        - **Contact Number**: Exactly 10 digits (Indian standard)
        - **Project Name**: Minimum 3 characters
        - **Source URL**: Must start with http:// or https://
        
        **Note**: All fields must be unique across all submissions.
        """)

if __name__ == "__main__":
    main()
