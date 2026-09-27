import factory
from faker import Faker
from django.contrib.auth.hashers import make_password

from users.models import User

fake = Faker()


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        skip_postgeneration_save = True
        django_get_or_create = ("username",)

    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    username = factory.LazyAttribute(lambda o: f"{o.first_name.lower()}.{o.last_name.lower()}{fake.pyint(1, 100)}")
    email = factory.LazyAttribute(lambda o: f"{o.username}@example.com")
    password = factory.LazyFunction(lambda: make_password("defaultpassword"))
    is_staff = False
    is_superuser = False
    is_active = True
