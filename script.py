import os
import django
import csv
import re

# ==========================================
# INITIALIZE DJANGO ENVIRONMENT
# Required to access models outside of manage.py
# ==========================================
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

# Import the model AFTER setting up django
from pages.models import Owner


def clean_data(raw_string):
    """a). 清理原始資料 (Clean original data): Removes leading/trailing whitespace."""
    if not raw_string:
        return ""
    return str(raw_string).strip()


def format_data(name, email, phone):
    """b). 格式化資料集 (Format data set): Standardizes casing and phone numbers."""
    # Format: Title Case for names
    formatted_name = name.title() 
    
    # Format: Lowercase for emails
    formatted_email = email.lower() 
    
    # Format: Standardize phone numbers to XXX-XXX-XXXX format
    digits_only = re.sub(r'\D', '', phone)
    if len(digits_only) == 10:
        formatted_phone = f"{digits_only[:3]}-{digits_only[3:6]}-{digits_only[6:]}"
    else:
        formatted_phone = phone  # Fallback if the number isn't exactly 10 digits
        
    return formatted_name, formatted_email, formatted_phone


def import_data_from_csv(file_path):
    """c). 將資料匯入到 django 資料庫 (Import data to DB)"""
    print(f"Importing data from {file_path}...")
    try:
        with open(file_path, mode='r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            import_count = 0
            
            for row in reader:
                # 1. Clean the raw data
                raw_name = clean_data(row.get('name', ''))
                raw_email = clean_data(row.get('email', ''))
                raw_phone = clean_data(row.get('phone', ''))

                # 2. Format the dataset
                fmt_name, fmt_email, fmt_phone = format_data(raw_name, raw_email, raw_phone)

                # 3. Import to Django DB (Using get_or_create to prevent duplicate emails)
                owner, created = Owner.objects.get_or_create(
                    email=fmt_email,
                    defaults={'name': fmt_name, 'phone': fmt_phone}
                )
                if created:
                    import_count += 1
                    
        print(f"SUCCESS: Imported {import_count} new records into the database.")
    except FileNotFoundError:
        print(f"ERROR: Could not find {file_path}. Please create the file first.")


def export_data_to_csv(file_path):
    """c). 將資料匯出到 django 資料庫 (Export data from DB)"""
    print(f"Exporting database records to {file_path}...")
    owners = Owner.objects.all()
    
    with open(file_path, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        # Write CSV Headers
        writer.writerow(['ID', 'Name', 'Email', 'Phone', 'Created At']) 
        
        # Write Database Rows
        for owner in owners:
            writer.writerow([
                owner.id,
                owner.name,
                owner.email,
                owner.phone,
                owner.created_at.strftime("%Y-%m-%d %H:%M:%S")
            ])
            
    print(f"SUCCESS: Exported {owners.count()} records to {file_path}.")


if __name__ == "__main__":
    IMPORT_FILE = 'raw_owners.csv'
    EXPORT_FILE = 'exported_owners.csv'

    print("--- Starting Django Data Manager ---")
    
    # Run the import function (Reads from raw_owners.csv, cleans, formats, and saves to DB)
    import_data_from_csv(IMPORT_FILE)

    # Run the export function (Queries DB and generates exported_owners.csv)
    export_data_to_csv(EXPORT_FILE)

    # d). 最終結果可以在django管理面板下檢查
    print("--- Process Complete! ---")
    print("Log into your Django Admin Panel (http://127.0.0.1:8000/admin/) to check the results.")