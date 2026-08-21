import json
import os
import re
from datetime import datetime
from dotenv import load_dotenv
import psycopg2

# --- CONFIGURATION ---
load_dotenv()
DB_CONFIG = {
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432")
}

# --- CLEANING & FORMATTING HELPERS ---

def clean_data(raw_string):
    return str(raw_string).strip() if raw_string else ""

def format_owner(name, email, phone):
    fmt_name = name.title() 
    fmt_email = email.lower() 
    digits_only = re.sub(r'\D', '', phone)
    fmt_phone = f"{digits_only[:3]}-{digits_only[3:6]}-{digits_only[6:]}" if len(digits_only) == 10 else phone
    return fmt_name, fmt_email, fmt_phone

def format_pet(species, age_str, is_vac_str):
    fmt_species = species.lower()
    if fmt_species not in ['dog', 'cat', 'bird', 'other']:
        fmt_species = 'other'
    
    fmt_age = int(age_str) if age_str.isdigit() else 0
    fmt_vac = str(is_vac_str).lower() in ['true', '1', 'yes', 't', 'y']
    return fmt_species, fmt_age, fmt_vac

def format_date(date_str):
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return datetime.today().date()

# --- DIRECT PSYCOPG2 IMPORTERS ---

def import_all_data(file_path):
    print(f"Reading unified data from {file_path}...")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            master_data = json.load(f)
            
        # Connect directly to PostgreSQL
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        owner_count = 0
        pet_count = 0
        med_count = 0

        # Note: Replace 'pages_owner', 'pages_pet', 'pages_medicalrecord' with your actual table names (usually appname_modelname)
        
        # 1. Import Owners
        for row in master_data.get('owners', []):
            name, email, phone = format_owner(
                clean_data(row.get('name')), clean_data(row.get('email')), clean_data(row.get('phone'))
            )
            # Check if email exists, else insert
            cur.execute("SELECT id FROM pages_owner WHERE email = %s;", (email,))
            existing = cur.fetchone()
            if not existing:
                cur.execute(
                    "INSERT INTO pages_owner (name, email, phone) VALUES (%s, %s, %s);",
                    (name, email, phone)
                )
                owner_count += 1
        conn.commit()
        print(f"  -> Imported {owner_count} new Owners.")

        # 2. Import Pets
        for row in master_data.get('pets', []):
            name = clean_data(row.get('name')).title()
            breed = clean_data(row.get('breed'))
            owner_email = clean_data(row.get('owner_email')).lower()
            
            species, age, is_vac = format_pet(
                clean_data(row.get('species')), clean_data(row.get('age')), clean_data(row.get('is_vaccinated'))
            )

            # Find owner ID by email
            cur.execute("SELECT id FROM pages_owner WHERE email = %s;", (owner_email,))
            owner_row = cur.fetchone()
            
            if owner_row:
                owner_id = owner_row[0]
                cur.execute(
                    "SELECT id FROM pages_pet WHERE name = %s AND owner_id = %s;",
                    (name, owner_id)
                )
                if not cur.fetchone():
                    cur.execute(
                        "INSERT INTO pages_pet (name, species, breed, age, is_vaccinated, owner_id) VALUES (%s, %s, %s, %s, %s, %s);",
                        (name, species, breed, age, is_vac, owner_id)
                    )
                    pet_count += 1
        conn.commit()
        print(f"  -> Imported {pet_count} new Pets.")

        # 3. Import Medical Records
        for row in master_data.get('medical_records', []):
            pet_name = clean_data(row.get('pet_name')).title()
            treatment = clean_data(row.get('treatment')).title()
            vet_name = clean_data(row.get('vet_name')).title()
            notes = clean_data(row.get('notes'))
            date = format_date(clean_data(row.get('date')))

            # Find pet ID by name
            cur.execute("SELECT id FROM pages_pet WHERE name = %s;", (pet_name,))
            pet_row = cur.fetchone()
            
            if pet_row:
                pet_id = pet_row[0]
                cur.execute(
                    "SELECT id FROM pages_medicalrecord WHERE pet_id = %s AND treatment = %s AND date = %s;",
                    (pet_id, treatment, date)
                )
                if not cur.fetchone():
                    cur.execute(
                        "INSERT INTO pages_medicalrecord (pet_id, treatment, vet_name, date, notes) VALUES (%s, %s, %s, %s, %s);",
                        (pet_id, treatment, vet_name, date, notes)
                    )
                    med_count += 1
        conn.commit()
        print(f"  -> Imported {med_count} new Medical Records.")

        cur.close()
        conn.close()

    except FileNotFoundError:
        print(f"ERROR: {file_path} not found.")
    except Exception as e:
        print(f"Database Error: {e}")

# --- DIRECT PSYCOPG2 EXPORTER ---

def export_all_to_single_file(output_filename='exported_data.json'):
    print(f"\nExporting all database records into '{output_filename}'...")
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()

        # Fetch Owners
        cur.execute("SELECT id, name, email, phone FROM pages_owner;")
        owners_data = [{"id": r[0], "name": r[1], "email": r[2], "phone": r[3]} for r in cur.fetchall()]

        # Fetch Pets with Owner Names
        cur.execute("""
            SELECT p.id, p.name, p.species, p.age, o.name, p.is_vaccinated 
            FROM pages_pet p 
            LEFT JOIN pages_owner o ON p.owner_id = o.id;
        """)
        pets_data = [{
            "id": r[0], "name": r[1], "species": r[2], "age": r[3], 
            "owner_name": r[4] if r[4] else "None", "is_vaccinated": r[5]
        } for r in cur.fetchall()]

        # Fetch Medical Records with Pet Names
        cur.execute("""
            SELECT m.id, p.name, m.treatment, m.vet_name, m.date, m.notes 
            FROM pages_medicalrecord m 
            JOIN pages_pet p ON m.pet_id = p.id;
        """)
        med_data = [{
            "id": r[0], "pet_name": r[1], "treatment": r[2], 
            "vet_name": r[3], "date": str(r[4]), "notes": r[5]
        } for r in cur.fetchall()]

        cur.close()
        conn.close()

        # Write to JSON file with custom layout
        with open(output_filename, 'w', encoding='utf-8') as f:
            f.write("{\n")
            
            f.write('  "owners": [\n')
            owner_lines = [f"    {json.dumps(item)}" for item in owners_data]
            f.write(",\n".join(owner_lines) + "\n")
            f.write("  ]")
            f.write(",\n\n")
            
            f.write('  "pets": [\n')
            pet_lines = [f"    {json.dumps(item)}" for item in pets_data]
            f.write(",\n".join(pet_lines) + "\n")
            f.write("  ]")
            f.write(",\n\n")
            
            f.write('  "medical_records": [\n')
            med_lines = [f"    {json.dumps(item)}" for item in med_data]
            f.write(",\n".join(med_lines) + "\n")
            f.write("  ]\n")
            f.write("}\n")
            
        print(f"SUCCESS: All records successfully exported to '{output_filename}'.")

    except Exception as e:
        print(f"Export Error: {e}")

# --- MAIN EXECUTION ---
if __name__ == "__main__":
    print("--- Starting Direct Psycopg2 Data Manager ---")
    
    import_all_data('raw_data.json')
    export_all_to_single_file('exported_data.json')

    print("\n--- Process Complete! ---")