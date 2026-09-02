from datetime import date

from werkzeug.security import generate_password_hash

from app import create_app
from app.extensions import db
from app.models import Person, Relationship, User


PASSWORD = "testing123"


PEOPLE = [
    {
        "key": "lucas",
        "email": "lucas.soprano@test.local",
        "name": "Lucas Soprano",
        "birth_date": date(2003, 12, 29),
        "gender": "male",
    },
    {
        "key": "tony",
        "email": "tony@sopranos.test",
        "name": "Tony Soprano",
        "gender": "male",
    },
    {
        "key": "carmela",
        "email": "carmela@sopranos.test",
        "name": "Carmela Soprano",
        "gender": "female",
    },
    {
        "key": "meadow",
        "email": "meadow@sopranos.test",
        "name": "Meadow Soprano",
        "gender": "female",
    },
    {
        "key": "aj",
        "email": "aj@sopranos.test",
        "name": "A.J. Soprano",
        "gender": "male",
    },
]


RELATIONSHIPS = [
    # Tony and Carmela
    ("tony", "carmela", "spouse", "spouse"),

    # Tony and Carmela's children
    ("tony", "meadow", "child", "parent"),
    ("carmela", "meadow", "child", "parent"),

    ("tony", "aj", "child", "parent"),
    ("carmela", "aj", "child", "parent"),

    ("tony", "lucas", "child", "parent"),
    ("carmela", "lucas", "child", "parent"),

    # Sibling links
    ("lucas", "meadow", "sibling", "sibling"),
    ("lucas", "aj", "sibling", "sibling"),
    ("meadow", "aj", "sibling", "sibling"),
]


def create_person(data):
    user = User(
        email=data["email"],
        password_hash=generate_password_hash(
            PASSWORD,
            method="pbkdf2:sha256",
        ),
        is_active=True,
    )

    db.session.add(user)
    db.session.flush()

    person = Person(
        user_id=user.id,
        full_name=data["name"],
        birth_date=data.get("birth_date"),
        gender=data.get("gender"),
    )

    db.session.add(person)
    db.session.flush()

    return person


def add_relationship(
    person_a,
    person_b,
    relation_a_to_b,
    relation_b_to_a,
):
    relationship = Relationship(
        person_a_id=person_a.id,
        person_b_id=person_b.id,
        relation_a_to_b=relation_a_to_b,
        relation_b_to_a=relation_b_to_a,
    )

    db.session.add(relationship)


def delete_existing_sopranos_data():
    test_domains = [
        "%@sopranos.test",
        "%@test.local",
        "%@blundetto.test",
    ]

    existing_users = []

    for pattern in test_domains:
        users = db.session.scalars(
            db.select(User).where(
                User.email.like(pattern)
            )
        ).all()

        existing_users.extend(users)

    unique_users = {
        user.id: user
        for user in existing_users
    }.values()

    person_ids = [
        user.person.id
        for user in unique_users
        if user.person is not None
    ]

    if person_ids:
        db.session.execute(
            db.delete(Relationship).where(
                db.or_(
                    Relationship.person_a_id.in_(
                        person_ids
                    ),
                    Relationship.person_b_id.in_(
                        person_ids
                    ),
                )
            )
        )

    for user in unique_users:
        if user.person:
            db.session.delete(user.person)

        db.session.delete(user)

    db.session.flush()


def seed():
    app = create_app()

    with app.app_context():
        try:
            print("Removing previous Sopranos dummy data...")
            delete_existing_sopranos_data()

            print("Creating dummy users...")

            people = {}

            for data in PEOPLE:
                people[data["key"]] = create_person(
                    data
                )

            print("Creating family relationships...")

            for (
                person_a_key,
                person_b_key,
                relation_a_to_b,
                relation_b_to_a,
            ) in RELATIONSHIPS:
                add_relationship(
                    people[person_a_key],
                    people[person_b_key],
                    relation_a_to_b,
                    relation_b_to_a,
                )

            db.session.commit()

            print()
            print("Immediate Soprano family created.")
            print()
            print("ROOT TEST ACCOUNT")
            print("Email: lucas.soprano@test.local")
            print(f"Password: {PASSWORD}")

        except Exception:
            db.session.rollback()
            raise


if __name__ == "__main__":
    seed()