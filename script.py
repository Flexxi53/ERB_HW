import os
import django
import json
import re
from datetime import datetime

# ==========================================
# INITIALIZE DJANGO ENVIRONMENT
# ==========================================
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from pages.models import Owner, Pet, MedicalRecord

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

# --- IMPORTERS (c. 將資料匯入到 django 資料庫) ---

def import_all_data(file_path):
    print(f"Reading unified data from {file_path}...")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            master_data = json.load(f)
            
        # 1. Import Owners
        owners_raw = master_data.get('owners', [])
        owner_count = 0
        for row in owners_raw:
            name, email, phone = format_owner(
                clean_data(row.get('name')), clean_data(row.get('email')), clean_data(row.get('phone'))
            )
            _, created = Owner.objects.get_or_create(email=email, defaults={'name': name, 'phone': phone})
            if created: owner_count += 1
        print(f"  -> Imported {owner_count} new Owners.")

        # 2. Import Pets
        pets_raw = master_data.get('pets', [])
        pet_count = 0
        for row in pets_raw:
            name = clean_data(row.get('name')).title()
            breed = clean_data(row.get('breed'))
            owner_email = clean_data(row.get('owner_email')).lower()
            
            species, age, is_vac = format_pet(
                clean_data(row.get('species')), clean_data(row.get('age')), clean_data(row.get('is_vaccinated'))
            )

            owner = Owner.objects.filter(email=owner_email).first()
            if owner:
                _, created = Pet.objects.get_or_create(
                    name=name, owner=owner,
                    defaults={'species': species, 'breed': breed, 'age': age, 'is_vaccinated': is_vac}
                )
                if created: pet_count += 1
        print(f"  -> Imported {pet_count} new Pets.")

        # 3. Import Medical Records
        med_raw = master_data.get('medical_records', [])
        med_count = 0
        for row in med_raw:
            pet_name = clean_data(row.get('pet_name')).title()
            treatment = clean_data(row.get('treatment')).title()
            vet_name = clean_data(row.get('vet_name')).title()
            notes = clean_data(row.get('notes'))
            date = format_date(clean_data(row.get('date')))

            pet = Pet.objects.filter(name=pet_name).first()
            if pet:
                _, created = MedicalRecord.objects.get_or_create(
                    pet=pet, treatment=treatment, date=date,
                    defaults={'vet_name': vet_name, 'notes': notes}
                )
                if created: med_count += 1
        print(f"  -> Imported {med_count} new Medical Records.")

    except FileNotFoundError:
        print(f"ERROR: {file_path} not found.")


def export_all_to_single_file(output_filename='exported_data.json'):
    print(f"\nExporting all database records into '{output_filename}'...")
    
    owners_data = [{"id": o.id, "name": o.name, "email": o.email, "phone": o.phone} for o in Owner.objects.all()]
    
    pets_data = [{
        "id": p.id, "name": p.name, "species": p.species, "age": p.age, 
        "owner_name": p.owner.name if p.owner else "None", "is_vaccinated": p.is_vaccinated
    } for p in Pet.objects.all()]

    med_data = [{
        "id": m.id, "pet_name": m.pet.name, "treatment": m.treatment, 
        "vet_name": m.vet_name, "date": str(m.date), "notes": m.notes
    } for m in MedicalRecord.objects.all()]

    with open(output_filename, 'w', encoding='utf-8') as f:
        f.write("{\n")
        
        # 1. Owners block
        f.write('  "owners": [\n')
        owner_lines = [f"    {json.dumps(item)}" for item in owners_data]
        f.write(",\n".join(owner_lines) + "\n")
        f.write("  ]")
        f.write(",\n\n")
        
        # 2. Pets block
        f.write('  "pets": [\n')
        pet_lines = [f"    {json.dumps(item)}" for item in pets_data]
        f.write(",\n".join(pet_lines) + "\n")
        f.write("  ]")
        f.write(",\n\n")
        
        # 3. Medical Records block
        f.write('  "medical_records": [\n')
        med_lines = [f"    {json.dumps(item)}" for item in med_data]
        f.write(",\n".join(med_lines) + "\n")
        f.write("  ]\n")
        f.write("}\n")
        
    print(f"SUCCESS: All records successfully exported to '{output_filename}'.")

# --- MAIN EXECUTION ---
if __name__ == "__main__":
    print("--- Starting Unified Django Data Manager ---")
    
    import_all_data('raw_data.json')
    export_all_to_single_file('exported_data.json')

    print("\n--- Process Complete! ---")
    print("Log into your Django Admin Panel (http://127.0.0.1:8000/admin/) to check the results.")