"""Admin utilities"""
from functools import wraps
from flask import abort, flash, redirect, url_for
from flask_login import current_user
import pandas as pd
import logging

logger = logging.getLogger(__name__)


def admin_required(f):
    """Decorator to require admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if current_user.role != 'admin':
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


def super_admin_required(f):
    """Decorator to require super admin (initial admin only)"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if current_user.role != 'admin':
            abort(403)
        if not current_user.check_is_super_admin:
            flash('Only the super admin can access this feature.', 'danger')
            return redirect(url_for('admin.dashboard'))
        return f(*args, **kwargs)
    return decorated_function


def parse_excel_file(file):
    """Parse Excel or CSV file and return DataFrame
    
    Args:
        file: FileStorage object from Flask request
    
    Returns:
        tuple: (DataFrame, error_message) or (None, error_message)
    """
    try:
        filename = file.filename.lower()
        
        if filename.endswith('.xlsx') or filename.endswith('.xls'):
            df = pd.read_excel(file)
        elif filename.endswith('.csv'):
            df = pd.read_csv(file)
        else:
            return None, "Invalid file format. Use .xlsx or .csv"
        
        return df, None
    
    except Exception as e:
        logger.error(f"Error parsing file: {str(e)}")
        return None, f"Error parsing file: {str(e)}"


def validate_candidate_data(row, row_num):
    """Validate a single candidate row from Excel
    
    Args:
        row: Pandas Series containing candidate data
        row_num: Row number for error reporting
    
    Returns:
        tuple: (is_valid, error_message, cleaned_data)
    """
    errors = []
    
    # Check required fields
    required_fields = ['Name', 'Email', 'Department', 'Year']
    for field in required_fields:
        if field not in row or pd.isna(row[field]) or str(row[field]).strip() == '':
            errors.append(f"Missing {field}")
    
    if errors:
        return False, f"Row {row_num}: {', '.join(errors)}", None
    
    # Clean and prepare data
    cleaned_data = {
        'name': str(row['Name']).strip(),
        'email': str(row['Email']).strip().lower(),
        'phone': str(row.get('Phone', '')).strip() if not pd.isna(row.get('Phone')) else '',
        'department': str(row['Department']).strip(),
        'year': str(row['Year']).strip(),
        'skills': str(row.get('Skills', '')).strip() if not pd.isna(row.get('Skills')) else ''
    }
    
    # Capture extra fields (any column not in standard fields)
    standard_fields = ['Name', 'Email', 'Phone', 'Department', 'Year', 'Skills']
    extra_fields = {}
    
    for col in row.index:
        if col not in standard_fields and not pd.isna(row[col]):
            # Store extra field with its value
            value = str(row[col]).strip()
            if value:  # Only store non-empty values
                extra_fields[col] = value
    
    cleaned_data['extra_fields'] = extra_fields if extra_fields else None
    
    # Basic email validation
    if '@' not in cleaned_data['email']:
        return False, f"Row {row_num}: Invalid email format", None
    
    return True, None, cleaned_data
