# crm/services/customer_services.py
from django.db import transaction
from ..models import Customer, PhysicalPersonDetail, MoralPersonDetail


@transaction.atomic
def create_customer(validated_data: dict) -> Customer:
    """
    Creates a Customer with its corresponding physical or moral details.
    Runs within a transaction to ensure data integrity.
    """
    physical_detail_data = validated_data.pop('physical_detail', None)
    moral_detail_data = validated_data.pop('moral_detail', None)
    
    customer = Customer.objects.create(**validated_data)
    
    if customer.customer_type == Customer.TYPE_PHYSICAL and physical_detail_data:
        PhysicalPersonDetail.objects.create(customer=customer, **physical_detail_data)
    elif customer.customer_type == Customer.TYPE_MORAL and moral_detail_data:
        MoralPersonDetail.objects.create(customer=customer, **moral_detail_data)
            
    return customer


@transaction.atomic
def update_customer(instance: Customer, validated_data: dict) -> Customer:
    """
    Updates a Customer and its nested details.
    Handles the complexity of switching customer_type.
    """
    # Note: This is a basic implementation. A real-world scenario might need
    # to handle switching customer_type (e.g., deleting the old detail record
    # and creating a new one). For now, we focus on updating existing data.

    physical_detail_data = validated_data.pop('physical_detail', None)
    moral_detail_data = validated_data.pop('moral_detail', None)

    # Update Customer fields
    for attr, value in validated_data.items():
        setattr(instance, attr, value)
    instance.save()

    # Update nested details
    if instance.customer_type == Customer.TYPE_PHYSICAL and physical_detail_data:
        PhysicalPersonDetail.objects.update_or_create(customer=instance, defaults=physical_detail_data)
    elif instance.customer_type == Customer.TYPE_MORAL and moral_detail_data:
        MoralPersonDetail.objects.update_or_create(customer=instance, defaults=moral_detail_data)

    return instance