from django.contrib import admin
from .models import Owner, Pet, MedicalRecord

class OwnerAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone', 'created_at')
    search_fields = ('name', 'email')
    
    # Creates distinct field boxes on the Owner form
    fieldsets = (
        ('Owner Information', {
            'fields': ('name', 'email', 'phone')
        }),
    )
admin.site.register(Owner,OwnerAdmin)

class PetAdmin(admin.ModelAdmin):
    list_display = ('name', 'species', 'breed', 'age', 'owner', 'is_vaccinated')
    list_filter = ('species', 'is_vaccinated')
    search_fields = ('name', 'breed')
    
    # Divides the Pet form into 3 distinct field boxes
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'species', 'breed', 'age')
        }),
        ('Ownership', {
            'fields': ('owner',)
        }),
        ('Health & Vaccination', {
            'fields': ('is_vaccinated',)
        }),
    )
admin.site.register(Pet,PetAdmin)

class MedicalRecordAdmin(admin.ModelAdmin):
    list_display = ('pet', 'treatment', 'vet_name', 'date')
    list_filter = ('date', 'vet_name')
    search_fields = ('treatment', 'vet_name', 'notes')
    
    # Creates distinct field boxes on the Medical Record form
    fieldsets = (
        ('Treatment Details', {
            'fields': ('pet', 'treatment', 'vet_name', 'date')
        }),
        ('Additional Notes', {
            'fields': ('notes',)
        }),
    )
admin.site.register(MedicalRecord,MedicalRecordAdmin)